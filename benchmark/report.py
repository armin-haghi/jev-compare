"""Fill the generated blocks of a study's documents from a run's saved results.

Documents mark generated content as `<!-- begin NAME ARGS -->` ... `<!-- end -->`.
Everything outside those markers is written by hand and left untouched.
"""
import json
import re
from pathlib import Path

import pandas as pd

from benchmark.config import json_write, load_case, read_yaml
from benchmark.metrics import compute, first_answers, is_model

BLOCK = re.compile(r"(<!-- begin (\S+)(.*?) -->\n).*?(<!-- end -->)", re.S)
MODELS = {"openai/gpt-5-mini": "GPT-5 mini", "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6", "typesafe-ai/jev": "Jev", "rules-v1": "Rules"}
STATEMENTS = {"IS": "income statement", "BS": "balance sheet"}
LIGHT = {"bg": "#fcfcfb", "ink": "#0b0b0b", "muted": "#52514e", "grid": "#e1e0d9", "axis": "#c3c2b7", "s0": "#2a78d6", "s1": "#eb6834"}
DARK = {"bg": "#1a1a19", "ink": "#ffffff", "muted": "#c3c2b7", "grid": "#2c2c2a", "axis": "#383835", "s0": "#3987e5", "s1": "#d95926"}


def n(value):
    return f"{value:,}"


def usd(value):
    return f"${value:g}"


def pct(part, whole):
    return f"{part / whole:.1%}" if whole else "–"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]) + "\n", {"header": header, "rows": rows}


class Study:
    def __init__(self, folder, destination):
        self.folder, self.destination = Path(folder), Path(destination)
        self.evidence = compute(folder)
        self.rows = pd.read_parquet(self.folder / "predictions.parquet")
        case = read_yaml(self.folder / "resolved_config.yaml")["case"]
        self.labels = getattr(load_case(case), "labels", dict)()
        split_file = self.folder / "label_splits.parquet"
        self.splits = pd.read_parquet(split_file) if split_file.exists() else None
        self.evidence["tables"] = {}

    # Shared lookups -------------------------------------------------------
    def regime(self, args):
        return self.evidence["regimes"][args[0] if args else "with_context"]

    def models(self, r):
        return sorted((m for m in r["methods"] if is_model(m)), key=lambda m: (m != "jev_direct", m))

    def name(self, r, method):
        return MODELS.get(r["methods"][method]["model"], r["methods"][method]["model"])

    def label(self, category):
        return self.labels.get(category, category.replace("_", " ").capitalize())

    # Result tables ----------------------------------------------------------
    def results(self, args):
        r = self.regime(args)
        return table(["Model", "Correct", "Cost per 1,000 records", "Median response"], [
            [self.name(r, m), f"{n(x['correct'])} of {n(x['records'])} ({pct(x['correct'], x['records'])})",
             f"${x['cost_per_1000_usd']:.3f}" if x["cost_per_1000_usd"] is not None else "Unknown", f"{x['median_seconds']:.2f}s"]
            for m in self.models(r) for x in [r["methods"][m]]])

    def rules(self, args):
        x = self.regime(args)["methods"]["rules_baseline"]
        return table(["Records", "Answered by rules", "Correct among answered", "Left unanswered"],
                     [[n(x["records"]), n(x["answered"]), f"{n(x['answered_correct'])} of {n(x['answered'])}", n(x["records"] - x["answered"])]])

    def pairs(self, args):
        r = self.regime(args)
        return table(["Comparison", "Both correct", "Both incorrect", "Only Jev correct", "Only the other model correct"], [
            [f"Jev and {self.name(r, m)}", n(p["both_correct"]), n(p["both_incorrect"]), n(p["left_only_correct"]), n(p["right_only_correct"])]
            for m, p in r["pairs"].items()])

    def context(self, args):
        regimes = self.evidence["regimes"]
        r = regimes["with_context"]
        return table(["Model", "Wording only", "Wording with context"], [
            [self.name(r, m)] + [f"{n(regimes[k]['methods'][m]['correct'])} of {n(regimes[k]['methods'][m]['records'])}"
                                 for k in ("label_only", "with_context")] for m in self.models(r)])

    def cutoffs(self, args):
        r = self.regime(args)
        models = self.models(r)
        header = ["Confidence at or above"] + [f"{self.name(r, m)}: {h}" for m in models for h in ("answers", "incorrect")]
        rows = []
        for i, point in enumerate(r["confidence"][models[0]]["cutoffs"]):
            cells = [f"{point['cutoff']:.2f}" if point["cutoff"] else "Any (all answers)"]
            for m in models:
                p = r["confidence"][m]["cutoffs"][i]
                cells += [n(p["answers"]), f"{n(p['incorrect'])} ({pct(p['incorrect'], p['answers'])})"]
            rows.append(cells)
        return table(header, rows)

    def calibration(self, args):
        r = self.regime(args)
        rows = []
        for m in self.models(r):
            c = r["confidence"][m]
            rows += [[self.name(r, m), f"{b['from']:.1f}–{b['to']:.1f}", n(b["answers"]), f"{b['mean_confidence']:.2f}",
                      pct(b["correct"], b["answers"])] for b in c["bands"]]
            rows.append([self.name(r, m), "All answers: average gap", "", "", f"{c['calibration_gap'] * 100:.1f} points"])
        return table(["Model", "Stated confidence", "Answers", "Average stated", "Share correct"], rows)

    def routing(self, args):
        r = self.regime(args)
        return table(["Jev confidence below", "Records", "Jev correct", "Other model", "Other model correct"], [
            [f"{x['cutoff']:.2f}", n(x["records"]), n(x["jev_correct"]), self.name(r, m), n(x["other_correct"])]
            for m, points in r["routing"].items() for x in points])

    def categories(self, args, errors_only=False):
        r = self.regime(args)
        models = self.models(r)
        cats = r["categories"][models[0]]
        wrong = {c: [r["categories"][m][c][0] - r["categories"][m][c][1] for m in models] for c in cats}
        order = sorted(cats, key=lambda c: (-sum(wrong[c]), c))
        if errors_only:
            order = [c for c in order if any(wrong[c])]
        shown = order[:int(args[1])] if len(args) > 1 else order
        rows = [[self.label(c), n(cats[c][0])] + [n(w) if errors_only else n(r["categories"][m][c][1]) for m, w in zip(models, wrong[c])]
                for c in shown]
        if errors_only:
            rest = [c for c in cats if c not in shown]
            if rest:
                rows.append([f"Other {len(rest)} categories", n(sum(cats[c][0] for c in rest))] +
                            [n(sum(wrong[c][i] for c in rest)) for i in range(len(models))])
            rows.append(["All categories", n(sum(v[0] for v in cats.values()))] + [n(sum(w[i] for w in wrong.values())) for i in range(len(models))])
        return table(["Category", "Records"] + [f"{self.name(r, m)} {'incorrect' if errors_only else 'correct'}" for m in models], rows)

    def errors(self, args):
        return self.categories(args, errors_only=True)

    def wording(self, args):
        r = self.regime(args)
        names = {"usual": "The usual choice of other companies using the wording",
                 "unusual": "Different from the usual choice", "new": "Wording no other company uses"}
        models = [m for m in self.models(r) if m in r["wording"]["groups"]]
        return table(["The company's tag for its wording is", "Records"] + [f"{self.name(r, m)} correct" for m in models], [
            [names[k], n(r["wording"]["groups"][models[0]][k][0])] +
            [f"{n(r['wording']['groups'][m][k][1])} ({pct(r['wording']['groups'][m][k][1], r['wording']['groups'][m][k][0])})" for m in models]
            for k in names])

    def agreement(self, args):
        consistency = self.evidence["dataset"]["answer_key_consistency"]
        w = self.regime(args)["wording"]
        return table(["Comparison", "Cases", "Same category"], [
            ["Same company, same wording, different filings", n(consistency["company_wordings_in_several_filings"]),
             pct(consistency["company_wordings_in_several_filings"] - consistency["changed_category"], consistency["company_wordings_in_several_filings"])],
            ["Two different companies, same wording", f"{n(w['records_with_other_companies'])} sampled records",
             f"{w['other_company_agreement']:.1%}"]])

    def consistency(self, args):
        regimes = self.evidence["regimes"]
        r = regimes["with_context"]
        rows = []
        for check, title in (("repeats", "Asked twice"), ("reorders", "Options reordered")):
            for m in self.models(r):
                rows.append([title, self.name(r, m)] + [
                    f"{n(regimes[k]['methods'][m][check]['changed'])} of {n(regimes[k]['methods'][m][check]['records'])}"
                    for k in ("label_only", "with_context")])
        return table(["Check", "Model", "Changed, wording only", "Changed, with context"], rows)

    def tokens(self, args):
        r = self.regime(args)
        prices = {p["model"]: p for p in self.evidence["prices"]}
        return table(["Model", "Input tokens per call", "Output tokens per call", "Price per million input tokens",
                      "Price per million output tokens", "Cost per 1,000 records"], [
            [self.name(r, m), f"{x['input_tokens_per_call']:,.0f}", f"{x['output_tokens_per_call']:,.0f}",
             usd(prices[x['model']]['input_per_million']), usd(prices[x['model']]['output_per_million']), f"${x['cost_per_1000_usd']:.3f}"]
            for m in self.models(r) for x in [r["methods"][m]]])

    def speed(self, args):
        r = self.regime(args)
        return table(["Model", "Median response", "95th percentile"], [
            [self.name(r, m), f"{x['median_seconds']:.2f}s", f"{x['p95_seconds']:.2f}s"] for m in self.models(r) for x in [r["methods"][m]]])

    def prices(self, args):
        return table(["Model", "Per million input tokens", "Per million output tokens", "Price date", "Source"], [
            [MODELS.get(p["model"], p["model"]), usd(p["input_per_million"]), usd(p["output_per_million"]), p["effective_date"], p["source_url"]]
            for p in self.evidence["prices"]])

    def scope(self, args):
        s = self.evidence["dataset"]["scope"]
        return table(["Step", "Lines", "Share of all lines"], [
            [step, n(s[k]), pct(s[k], s["all_lines"])] for step, k in (
                ("Income-statement and balance-sheet lines in the selected filings", "all_lines"),
                ("In scope: tag on the template list, standard taxonomy, one consolidated USD value", "in_scope_before_repeats"),
                ("After removing repeats of the same wording by the same company", "in_scope"),
                ("Sampled for this run", "sampled"))])

    def sample(self, args):
        d = self.evidence["dataset"]
        cats = self.regime(args)["categories"]["jev_direct"]
        sizes = sorted({v[0] for v in cats.values()})
        return table(["Property", "Value"], [
            ["Records", n(d["scope"]["sampled"])],
            ["Categories", f"{len(cats)}; {n(sizes[0]) if len(sizes) == 1 else f'{n(sizes[0])}–{n(sizes[-1])}'} records each"],
            ["Companies", n(d["companies"])], ["Fiscal years", ", ".join(d["fiscal_years"])],
            ["Statements", "; ".join(f"{n(v)} {STATEMENTS.get(k, k)} lines" for k, v in d["statements"].items())],
            ["Consistency checks", f"{n(d['repeat_records'])} records asked twice; {n(d['reorder_records'])} with reordered options"]])

    def run(self, args):
        rows = []
        for regime, r in self.evidence["regimes"].items():
            for m, x in sorted(r["methods"].items()):
                rows.append([m, MODELS.get(x["model"], x["model"]), regime.replace("_", " "), n(x["records"]), n(x["correct"]),
                             n(x["requests"]), f"${x['cost_per_1000_usd']:.3f}" if x["cost_per_1000_usd"] is not None else "–"])
        return table(["Method", "Model", "Input", "Records", "Correct", "Requests", "Cost per 1,000 records"], rows)

    # Records ------------------------------------------------------------------
    def answers(self, regime="with_context"):
        first = first_answers(self.rows[self.rows.context_regime == regime])
        return {m: g.set_index("record_id") for m, g in first.groupby("method") if is_model(m)}

    def records(self, args):
        answers = self.answers()
        models = sorted(answers, key=lambda m: (m != "jev_direct", m))
        r = self.evidence["regimes"]["with_context"]
        rows = []
        for prefix in args:
            matches = [i for i in answers["jev_direct"].index if i.startswith(prefix)]
            if len(matches) != 1:
                raise ValueError(f"Record prefix must match exactly one record: {prefix}")
            record_id = matches[0]
            row = answers["jev_direct"].loc[record_id]
            line, source = json.loads(row.input_json), json.loads(row.source_json)
            context = line.get("lines_above", [])[-1:] + [f"**{line['label']}**"] + line.get("lines_below", [])[:1]
            rows.append([f"{source['name']} {source['fy']}: " + " → ".join(context), self.label(row.reference)] +
                        [f"{'✓' if a.correct else '✗'} {self.label(a.prediction)} ({a.confidence:.2f})"
                         for m in models for a in [answers[m].loc[record_id]]])
        return table(["Company: line in context", "Answer key"] + [self.name(r, m) for m in models], rows)

    def worked(self, args):
        statement, wording = args[0], " ".join(args[1:])
        answers = self.answers()
        models = sorted(answers, key=lambda m: (m != "jev_direct", m))
        r = self.evidence["regimes"]["with_context"]
        jev = answers["jev_direct"]
        chosen = [i for i, row in jev.iterrows() if json.loads(row.groups_json).get("normalized_label") == wording
                  and json.loads(row.groups_json).get("statement") == statement]
        split = self.splits[(self.splits.statement == statement) & (self.splits.normalized_label == wording)].set_index("reference")
        rows = []
        for category in split.sort_values("filers", ascending=False).index:
            ids = [i for i in chosen if jev.loc[i].reference == category]
            rows.append([self.label(category), f"{n(int(split.loc[category].filers))} ({split.loc[category].share:.0%})", n(len(ids))] +
                        [n(int(answers[m].loc[ids].correct.sum())) for m in models])
        return table(["Filed as", "Companies using this wording", "Records in sample"] + [f"{self.name(r, m)} correct" for m in models], rows)

    # Charts -------------------------------------------------------------------
    def svg(self, name, alt, body, width=640, height=360):
        style = lambda p: "".join(f".{k}{{{'stroke' if k in ('grid', 'axis') else 'fill'}:{v}}}" for k, v in p.items() if not k.startswith("s")) + \
            "".join(f".{k}{{stroke:{v};fill:{v}}}.{k}l{{stroke:{v};fill:none}}" for k, v in p.items() if k.startswith("s")) + f".ring{{stroke:{p['bg']}}}"
        text = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="12">'
                f"<style>{style(LIGHT)}@media (prefers-color-scheme: dark){{{style(DARK)}}}</style>"
                f'<rect class="bg" width="{width}" height="{height}"/>{body}</svg>\n')
        (self.destination / "charts").mkdir(exist_ok=True)
        (self.destination / "charts" / f"{name}.svg").write_text(text)
        return f"![{alt}](charts/{name}.svg)\n", None

    def line_chart(self, name, alt, series, x_label, y_label, x_axis, y_axis, x_fmt, y_fmt, diagonal=False, notes=()):
        """x_axis and y_axis are (low, high, step); notes are (x, y, text) labels placed beside points."""
        left, right, top, bottom = 72, 600, 44, 300
        sx = lambda v: left + (v - x_axis[0]) / (x_axis[1] - x_axis[0]) * (right - left)
        sy = lambda v: bottom - (v - y_axis[0]) / (y_axis[1] - y_axis[0]) * (bottom - top)
        ticks = lambda low, high, step: [low + step * i for i in range(round((high - low) / step) + 1)]
        body = [f'<line class="grid" x1="{left}" x2="{right}" y1="{sy(y):.1f}" y2="{sy(y):.1f}"/>'
                f'<text class="muted" x="{left - 8}" y="{sy(y) + 4:.1f}" text-anchor="end">{y_fmt(y)}</text>' for y in ticks(*y_axis)]
        body += [f'<text class="muted" x="{sx(x):.1f}" y="{bottom + 18}" text-anchor="middle">{x_fmt(x)}</text>' for x in ticks(*x_axis)]
        body.append(f'<line class="axis" x1="{left}" x2="{right}" y1="{bottom}" y2="{bottom}"/>')
        if diagonal:
            low, high = max(x_axis[0], y_axis[0]), min(x_axis[1], y_axis[1])
            body.append(f'<line class="axis" x1="{sx(low):.1f}" y1="{sy(low):.1f}" x2="{sx(high):.1f}" y2="{sy(high):.1f}"/>'
                        f'<line class="axis" x1="{left + 308}" x2="{left + 326}" y1="18" y2="18" stroke-width="2"/>'
                        f'<text class="ink" x="{left + 332}" y="22">Stated confidence = share correct</text>')
        for i, (label, points) in enumerate(series):
            path = " ".join(f"{'M' if j == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}" for j, (x, y) in enumerate(points))
            body.append(f'<path class="s{i}l" d="{path}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
            body += [f'<circle class="s{i} ring" cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" stroke-width="2"/>' for x, y in points]
            body.append(f'<rect class="s{i}" x="{left + 8 + 150 * i}" y="12" width="12" height="12" rx="2"/>'
                        f'<text class="ink" x="{left + 26 + 150 * i}" y="22">{label}</text>')
        body += [f'<text class="ink" x="{sx(x) - 8:.1f}" y="{sy(y) - 10:.1f}" text-anchor="end">{text}</text>' for x, y, text in notes]
        body.append(f'<text class="muted" x="{(left + right) / 2}" y="{bottom + 40}" text-anchor="middle">{x_label}</text>'
                    f'<text class="muted" transform="translate(18 {(top + bottom) / 2}) rotate(-90)" text-anchor="middle">{y_label}</text>')
        return self.svg(name, alt, "".join(body))

    def chart_cutoffs(self, args):
        r = self.regime(args)
        marked = float(args[1]) if len(args) > 1 else .9
        series, notes = [], []
        for m in self.models(r):
            points = [(p["cutoff"], p["answers"] / r["methods"][m]["records"] * 100, p["incorrect"] / p["answers"] * 100)
                      for p in r["confidence"][m]["cutoffs"] if p["answers"]]
            series.append((self.name(r, m), [(x, y) for _, x, y in points]))
            notes += [(x, y, f"cut-off {c:.2f}") for c, x, y in points if c == marked]
        peak = max(y for _, points in series for _, y in points)
        step = next(s for s in (.5, 1, 2, 2.5, 5, 10, 25) if peak / s <= 5)
        return self.line_chart("confidence-cutoffs", "Line chart: for each confidence cut-off, the share of answers at or above it and the share of those that are incorrect, per model", series, "Share of answers at or above the confidence cut-off",
                               "Share of those answers that are incorrect", (0, 100, 25), (0, step * max(1, -(-peak // step)), step),
                               lambda v: f"{v:.0f}%", lambda v: f"{v:g}%", notes=notes)

    def chart_calibration(self, args):
        r = self.regime(args)
        series = [(self.name(r, m), [(b["mean_confidence"], b["correct"] / b["answers"]) for b in r["confidence"][m]["bands"] if b["answers"] >= 20])
                  for m in self.models(r)]
        return self.line_chart("calibration", "Line chart: stated confidence against the share of answers that were correct, per model, with the line where they are equal", series, "Stated confidence (bands with at least 20 answers)", "Share correct",
                               (.5, 1, .1), (.5, 1, .1), lambda v: f"{v:.1f}", lambda v: f"{v:.0%}", diagonal=True)

    def chart_errors(self, args):
        r = self.regime(args)
        models = self.models(r)
        cats = r["categories"][models[0]]
        wrong = {c: [r["categories"][m][c][0] - r["categories"][m][c][1] for m in models] for c in cats}
        top = sorted((c for c in wrong if any(wrong[c])), key=lambda c: (-sum(wrong[c]), c))[:int(args[1]) if len(args) > 1 else 6]
        left, right, top_y, band = 290, 600, 44, 44
        scale = max(max(wrong[c]) for c in top) or 1
        body = []
        for i, m in enumerate(models):
            body.append(f'<rect class="s{i}" x="{left + 150 * i}" y="12" width="12" height="12" rx="2"/>'
                        f'<text class="ink" x="{left + 18 + 150 * i}" y="22">{self.name(r, m)}</text>')
        for row, c in enumerate(top):
            y0 = top_y + row * band
            body.append(f'<text class="ink" x="{left - 10}" y="{y0 + 22}" text-anchor="end">{self.label(c)}</text>')
            for i, value in enumerate(wrong[c]):
                y, w = y0 + 4 + i * 18, (right - left) * value / scale
                if w:
                    body.append(f'<path class="s{i}" d="M{left},{y} H{left + max(w - 4, 0):.1f} Q{left + w:.1f},{y} {left + w:.1f},{y + 4} '
                                f'V{y + 12} Q{left + w:.1f},{y + 16} {left + max(w - 4, 0):.1f},{y + 16} H{left} Z"/>')
                body.append(f'<text class="muted" x="{left + w + 6:.1f}" y="{y + 12}">{value}</text>')
        body.append(f'<line class="axis" x1="{left}" x2="{left}" y1="{top_y}" y2="{top_y + band * len(top)}"/>')
        return self.svg("incorrect-by-category", "Bar chart: incorrect answers per category for each model, categories with the most incorrect answers first", "".join(body), height=top_y + band * len(top) + 16)

    # Rendering ----------------------------------------------------------------
    BLOCKS = ("results", "rules", "pairs", "context", "cutoffs", "calibration", "routing", "categories", "errors", "wording",
              "agreement", "consistency", "tokens", "speed", "prices", "scope", "sample", "run", "records", "worked",
              "chart-cutoffs", "chart-calibration", "chart-errors")

    def block(self, name, args):
        if name not in self.BLOCKS:
            raise ValueError(f"Unknown generated block: {name}")
        markdown, data = getattr(self, name.replace("-", "_"))(args)
        if data is not None:
            self.evidence["tables"][" ".join([name, *args])] = data
        return markdown

    def render(self, text):
        return BLOCK.sub(lambda m: m.group(1) + self.block(m.group(2), m.group(3).split()) + m.group(4), text)


def publish(folder, destination):
    """Refresh every generated block in the destination's documents and write their evidence file."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    study = Study(folder, destination)
    for document in sorted(destination.glob("*.md")):
        document.write_text(study.render(document.read_text()))
    json_write(destination / "evidence.json", study.evidence)
    return study.evidence
