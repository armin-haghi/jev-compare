"""SEC Financial Statement Data Sets ingestion, preserving exclusion evidence."""
import hashlib
import json
import os
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from benchmark.config import file_hash, json_write, read_yaml
from benchmark.schemas import BenchmarkRecord
from .features import build_payload, normalize, rules
from .template import NOT_MAPPED, ROOT, candidates, labels, mapping, template


def quarters(start, end):
    sy, sq = int(start[:4]), int(start[-1])
    ey, eq = int(end[:4]), int(end[-1])
    return [f"{n // 4}q{n % 4 + 1}" for n in range(sy * 4 + sq - 1, ey * 4 + eq)]


def download(quarter, raw, user_agent):
    path = raw / f"{quarter}.zip"
    if path.exists() and zipfile.is_zipfile(path):
        return path
    if not user_agent or "@" not in user_agent or "example.com" in user_agent:
        raise ValueError("Set SEC_USER_AGENT to a real requester name and contact email")
    url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
    temp = path.with_suffix(".part")
    for attempt in range(3):
        try:
            with requests.get(url, headers={"User-Agent": user_agent}, stream=True, timeout=120) as response:
                response.raise_for_status()
                with temp.open("wb") as output:
                    for chunk in response.iter_content(1024 * 1024):
                        output.write(chunk)
            if not zipfile.is_zipfile(temp):
                raise ValueError(f"SEC returned a non-ZIP response for {quarter}")
            temp.replace(path)
            time.sleep(0.2)
            return path
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Download exhausted")


def read_table(archive, name, chunksize=None):
    return pd.read_csv(archive.open(f"{name}.txt"), sep="\t", dtype=str,
                       keep_default_na=False, chunksize=chunksize)


def read_quarter(path, config):
    with zipfile.ZipFile(path) as archive:
        sub = read_table(archive, "sub")
        sub = sub[(sub.form == "10-K") & (sub.fp == "FY") & sub.fy.isin([str(y) for y in config["fiscal_years"]])]
        pre = read_table(archive, "pre")
        pre = pre[pre.adsh.isin(sub.adsh) & pre.stmt.isin(["IS", "BS"])]
        tags = read_table(archive, "tag")
        chunks = []
        for chunk in read_table(archive, "num", chunksize=250_000):
            chunk = chunk[chunk.adsh.isin(sub.adsh)]
            if not chunk.empty:
                chunks.append(chunk)
        num = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(
            columns=["adsh", "tag", "version", "ddate", "qtrs", "coreg", "segments", "uom", "value"])
    return records_from_tables(sub, pre, num, tags, config)


def records_from_tables(sub, pre, num, tags, config):
    """Pure transformation also exercised with miniature authentic-format tables."""
    tag_map = mapping()
    tag_statement = {line["id"]: line["statement"] for line in template()["lines"]}
    excluded_tags = {r["tag"]: r["reason"] for r in template()["excluded_tags"]}
    sic_path = Path(config.get("sic_file", ROOT / "sic_codes.json"))
    sic = json.loads(sic_path.read_text()) if sic_path.exists() else {}
    submissions = sub.set_index("adsh").to_dict("index")
    tag_defs = tags.drop_duplicates(["tag", "version"]).set_index(["tag", "version"]).to_dict("index")
    nums = defaultdict(list)
    filing_keys = defaultdict(set)
    for row in num.to_dict("records"):
        filing = submissions.get(row["adsh"])
        if filing and str(row["ddate"]) == str(filing["period"]):
            key = (row["adsh"], row["tag"], row["version"], str(row["qtrs"]))
            nums[key].append(row)
            filing_keys[row["adsh"]].add(key)

    def amount(adsh, tag, version, qtrs):
        rows = nums.get((adsh, tag, version, qtrs), [])
        # Empty coreg and segments are essential after SEC's 2024 reprocessing.
        rows = [r for r in rows if not r.get("coreg") and not r.get("segments") and r.get("uom") == "USD"]
        values = {float(r["value"]) for r in rows if r.get("value") not in ("", None)}
        values = {v for v in values if pd.notna(v) and abs(v) != float("inf")}
        if len(values) > 1:
            return None, "ambiguous_value"
        return (next(iter(values)), None) if values else (None, "no_value")

    records, excluded, unmapped = [], [], Counter()
    pre = pre.copy()
    pre["numeric_line"] = pd.to_numeric(pre.line, errors="raise")
    for (adsh, report, statement), group in pre.groupby(["adsh", "report", "stmt"], sort=True):
        filing = submissions[adsh]
        if filing.get("form") != "10-K" or filing.get("fp") != "FY" or int(filing["fy"]) not in config["fiscal_years"]:
            continue
        rows = group.sort_values(["numeric_line", "tag"], kind="stable").to_dict("records")
        # Standard denominators must be unambiguous across possible taxonomy aliases.
        denominator_tags = template()["lines"][0]["tags"] if statement == "IS" else ["Assets"]
        denominator_values = set()
        for a, tag, version, qtrs in filing_keys[adsh]:
            if a == adsh and tag in denominator_tags and version.startswith("us-gaap/") and qtrs == ("4" if statement == "IS" else "0"):
                value, reason = amount(a, tag, version, qtrs)
                if reason is None and value and value > 0:
                    denominator_values.add(value)
        denominator = next(iter(denominator_values)) if len(denominator_values) == 1 else None
        duplicates = Counter(str(r["line"]) for r in rows)
        for index, row in enumerate(rows):
            rid = hashlib.sha256(f"{adsh}|{report}|{row['line']}".encode()).hexdigest()
            tag = row["tag"]
            definition = tag_defs.get((tag, row["version"]), {})
            reference = tag_map.get(tag)
            value, reason = amount(adsh, tag, row["version"], "4" if statement == "IS" else "0")
            if duplicates[str(row["line"])] > 1:
                reason = "duplicate_presentation_line"
            elif not row["plabel"].strip():
                reason = "empty_label"
            elif not row["version"].startswith("us-gaap/") or str(definition.get("custom", "0")) != "0":
                reason = "nonstandard_tag"
            elif tag in excluded_tags:
                reason = "combined_tag"
            elif not reference:
                reason = "unmapped_tag"
                unmapped[tag] += 1
            elif reference != NOT_MAPPED and tag_statement[reference] != statement:
                reason = "statement_mismatch"
            elif not definition.get("tlabel"):
                reason = "missing_tag_definition"
            if reason:
                excluded.append({**row, "record_id": rid, "exclusion_reason": reason})
                continue
            signed = -value if str(row.get("negating")) == "1" else value
            record = BenchmarkRecord(
                record_id=rid, case_id="sec_lines",
                source={key: filing.get(key, "") for key in ["cik", "name", "fy", "sic", "period"]} |
                       {"adsh": adsh, "report": str(report), "line": str(row["line"]), "tag": tag,
                        "version": row["version"], "standard_label": definition["tlabel"]},
                input={"label": row["plabel"], "statement": statement,
                       "lines_above": [r["plabel"] for r in rows[max(0, index-2):index]],
                       "lines_below": [r["plabel"] for r in rows[index+1:index+3]],
                       "sign": "positive" if signed > 0 else "negative" if signed < 0 else "zero",
                       "scale_ratio": abs(signed) / denominator if denominator else None,
                       "sic_description": sic.get(str(filing.get("sic")), "Industry description unavailable")},
                reference=reference,
                groups={"template_line": reference, "statement": statement,
                        "label_differs": str(normalize(row["plabel"]) != normalize(definition["tlabel"])).lower(),
                        "filer_split": "false", "baseline_miss": "false", "fiscal_year": str(filing["fy"])}
            )
            records.append(record)
    return records, excluded, unmapped


def company_consistency(records):
    """How often a company maps the same wording to the same category in different filings.

    Wording that appears more than once in one filing is skipped: those lines differ by position.
    """
    filings = defaultdict(lambda: defaultdict(list))
    for r in records:
        key = (str(r.source["cik"]), r.input["statement"], normalize(r.input["label"]))
        filings[key][r.source["adsh"]].append(r.reference)
    repeated = [f for f in filings.values() if len(f) > 1 and all(len(v) == 1 for v in f.values())]
    return {"company_wordings_in_several_filings": len(repeated),
            "changed_category": sum(len({v[0] for v in f.values()}) > 1 for f in repeated)}


def finalise(records, excluded):
    consistency = company_consistency(records)
    # Ties resolve by period, accession and stable id, independent of input order.
    records.sort(key=lambda r: (int(r.source["fy"]), str(r.source["period"]), r.source["adsh"], r.record_id), reverse=True)
    # Keep a company's latest filing for each wording. Lines repeating a wording inside that filing
    # (for example several lines worded "Other") differ by position, so they all stay.
    latest, kept = {}, []
    for record in records:
        key = (str(record.source["cik"]), record.input["statement"], normalize(record.input["label"]))
        if latest.setdefault(key, record.source["adsh"]) == record.source["adsh"]:
            kept.append(record)
        else:
            excluded.append({"record_id": record.record_id, **record.source, "exclusion_reason": "duplicate_filer_label"})
    groups = defaultdict(list)
    for record in kept:
        groups[(record.input["statement"], normalize(record.input["label"]))].append(record)
    splits = []
    for (statement, label), members in sorted(groups.items()):
        # Each company counts once per category it uses for this wording.
        companies = defaultdict(set)
        for r in members:
            companies[r.reference].add(str(r.source["cik"]))
        total = len({str(r.source["cik"]) for r in members})
        flag = total >= 5 and len(companies) >= 2
        for reference, users in sorted(companies.items()):
            splits.append({"statement": statement, "normalized_label": label, "reference": reference,
                           "filers": len(users), "total_filers": total, "share": len(users) / total,
                           "filer_split": flag})
        for record in members:
            record.groups["normalized_label"] = label
            record.groups["filer_split"] = str(flag).lower()
            result = rules(build_payload(record, "with_context", {}), candidates(record, {}), {})
            record.groups["baseline_miss"] = str(result.prediction != record.reference).lower()
    return sorted(kept, key=lambda r: r.record_id), splits, consistency


def save_records(path, records):
    pd.DataFrame([{"record_json": r.model_dump_json()} for r in records],
                 columns=["record_json"]).to_parquet(path, index=False)


def load_records(case_config):
    config = read_yaml(ROOT / "case.yaml") | case_config
    data = pd.read_parquet(Path(config["processed_dir"]) / "eligible_records.parquet")
    return [BenchmarkRecord.model_validate_json(s) for s in data.record_json]


def prepare(case_config):
    config = read_yaml(ROOT / "case.yaml") | case_config
    raw, output = Path(config["raw_dir"]), Path(config["processed_dir"])
    raw.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    sic_path = Path(config["sic_file"])
    if not sic_path.exists():
        from .sic import fetch
        fetch(os.environ.get("SEC_USER_AGENT", ""), sic_path)
    all_records, excluded, unmapped, sources = [], [], Counter(), []
    for quarter in quarters(config["quarter_start"], config["quarter_end"]):
        path = download(quarter, raw, os.environ.get("SEC_USER_AGENT", ""))
        records, rejected, counts = read_quarter(path, config)
        all_records.extend(records)
        excluded.extend(rejected)
        unmapped.update(counts)
        sources.append({"quarter": quarter, "sha256": file_hash(path), "bytes": path.stat().st_size})
        print(f"{quarter}: {len(records)} eligible before deduplication", flush=True)
    records, splits, consistency = finalise(all_records, excluded)
    save_records(output / "eligible_records.parquet", records)
    pd.DataFrame(excluded or [], columns=None if excluded else ["record_id", "exclusion_reason"]).to_parquet(output / "excluded_records.parquet", index=False)
    pd.DataFrame(splits, columns=["statement", "normalized_label", "reference", "filers", "total_filers", "share", "filer_split"]).to_parquet(output / "label_splits.parquet", index=False)
    pd.DataFrame([{"record_id": r.record_id, "payload_json": json.dumps(r.input)} for r in records],
                 columns=["record_id", "payload_json"]).to_parquet(output / "model_inputs.parquet", index=False)
    summary = []
    for category in labels():
        members = [r for r in records if r.reference == category]
        summary.append({"template_line": category, "eligible_records": len(members),
                        "unique_filers": len({r.source["cik"] for r in members}),
                        "unique_labels": len({normalize(r.input["label"]) for r in members}),
                        "share_label_differs": sum(r.groups["label_differs"] == "true" for r in members) / len(members) if members else None,
                        "share_filer_split": sum(r.groups["filer_split"] == "true" for r in members) / len(members) if members else None})
    pd.DataFrame(summary).to_csv(output / "sec_lines_summary.csv", index=False)
    # Proposed additions are an explicit review queue, never automatic ground truth.
    json_write(output / "mapping_review.json", [{"tag": tag, "count": count, "status": "unreviewed"} for tag, count in unmapped.most_common()])
    json_write(output / "dataset_manifest.json", {
        "case": "sec_lines", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources, "filters": config, "records": len(records),
        "excluded": len(excluded), "exclusion_counts": dict(Counter(r["exclusion_reason"] for r in excluded)),
        "answer_key_consistency": consistency,
        "dataset_sha256": file_hash(output / "eligible_records.parquet"),
        "template_sha256": file_hash(ROOT / "template.yaml"), "sic_sha256": file_hash(sic_path),
        "limitations": ["Filed tags are a proxy answer key, not independently audited truth.",
                        "The 2026 Q1 cutoff excludes later filings for fiscal year 2025.",
                        "Only standard mapped tags and consolidated USD values qualify.",
                        "Available SEC presentation rows may omit headings."]})
    return output / "eligible_records.parquet"
