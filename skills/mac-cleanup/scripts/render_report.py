#!/usr/bin/env python3
"""Render the mac-cleanup findings JSON into a themed, read-only HTML report.

Usage: python3 render_report.py findings.json [--out report.html] [--open]
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

RISKS = {"safe", "caution", "risky"}
TEMPLATE = pathlib.Path(__file__).with_name("report-template.html")


def validate(data):
    problems = []
    for gi, group in enumerate(data.get("groups", [])):
        for field in ("title", "items"):
            if field not in group:
                problems.append(f"groups[{gi}] is missing '{field}'")
        for ii, item in enumerate(group.get("items", [])):
            where = f"groups[{gi}].items[{ii}]"
            for field in ("name", "size_mb", "risk", "why"):
                if field not in item:
                    problems.append(f"{where} is missing '{field}'")
            if item.get("risk") not in RISKS:
                problems.append(f"{where}.risk must be one of {sorted(RISKS)}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("findings", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--open", action="store_true", help="open the report in the default browser")
    args = parser.parse_args()

    data = json.loads(args.findings.read_text())
    problems = validate(data)
    if problems:
        print("Findings JSON has problems:\n  " + "\n  ".join(problems), file=sys.stderr)
        sys.exit(1)
    data.setdefault("generated", datetime.datetime.now().isoformat(timespec="seconds"))

    # Keep the JSON from closing the <script> tag early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__FINDINGS__*/", payload)

    out = args.out or args.findings.with_name("report.html")
    out.write_text(html)
    print(f"Report written to {out}")
    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
