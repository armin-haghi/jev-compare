"""Fetch and pin the SEC Standard Industrial Classification list."""
import json
import os
import re
from html import unescape
from pathlib import Path
import requests
from benchmark.config import load_env

URL = "https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list"


def parse(html):
    records = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, flags=re.S):
        cells = [unescape(re.sub("<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.S)]
        if len(cells) >= 3 and cells[0].isdigit():
            records[str(int(cells[0]))] = cells[-1]
    if len(records) < 100:
        raise ValueError("SEC industry table was not found; refusing an incomplete mapping")
    return records


def fetch(agent, path=Path("cases/sec_lines/sic_codes.json")):
    if "@" not in agent or "example.com" in agent:
        raise ValueError("Set SEC_USER_AGENT to your name and real email")
    response = requests.get(URL, headers={"User-Agent": agent}, timeout=60)
    response.raise_for_status()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(parse(response.text), indent=2, sort_keys=True) + "\n")
    print(f"Pinned {len(parse(response.text))} SEC industry descriptions in {path}")
    return path


if __name__ == "__main__":
    load_env()
    fetch(os.environ.get("SEC_USER_AGENT", ""))
