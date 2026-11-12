"""Copy all planning tables into the API catalog without activating legal rules."""
import json
from pathlib import Path
import re
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, default=root / "docs" / "original-plan.md")
text = parser.parse_args().source.read_text(encoding="utf-8")
tables, current, heading = [], [], ""
for line in text.splitlines() + [""]:
    if line.startswith("#"):
        heading = line.lstrip("# ").strip()
    if line.startswith("|"):
        current.append(line)
    elif current:
        tables.append({"id": f"table_{len(tables)+1}", "section": heading,
                       "columns": [c.strip() for c in current[0].strip("|").split("|")],
                       "rows": [[c.strip() for c in r.strip("|").split("|")] for r in current[2:]],
                       "raw_markdown": "\n".join(current)})
        current = []
data = root / "compliance" / "data"
data.mkdir(parents=True, exist_ok=True)
(data / "plan_tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
sources = []
for table in tables:
    for row in table["rows"]:
        if re.fullmatch(r"S\d+", row[0]):
            sources.append({"id": row[0], "reference": row[1], "urls": re.findall(r"\]\((https://[^)]+)\)", row[1]),
                            "purpose": row[2], "legal_approval_status": "not_reviewed"})
(data / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
docs = root / "docs"
docs.mkdir(exist_ok=True)
(docs / "original-plan.md").write_text(text, encoding="utf-8")
prompts = root / "prompts"
prompts.mkdir(exist_ok=True)
fence = chr(96)*3
for match in re.finditer(r"### (R[1-5]) .*?\n\n" + fence + r"text\n(.*?)" + fence, text, re.S):
    (prompts / (match[1]+".txt")).write_text(match[2], encoding="utf-8")
for match in re.finditer(r"### Prompt (\d+) .*?\n\n" + fence + r"text\n(.*?)" + fence, text, re.S):
    (prompts / ("build-"+match[1].zfill(2)+".txt")).write_text(match[2], encoding="utf-8")
print(json.dumps({"tables": len(tables), "rows": sum(len(t["rows"]) for t in tables), "sources": len(sources)}))
