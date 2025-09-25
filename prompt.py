#!/usr/bin/env python3
"""Generate a MediaWiki table via the OpenAI API using a trimmed Jira CSV export."""
from __future__ import annotations

import csv
import os
import sys
from itertools import islice
from pathlib import Path
from typing import Iterable

from openai import OpenAI

CSV_PATH = Path("Jira.csv")
OUTPUT_PATH = Path("openairesponse.mw")
MAX_ISSUES = 10
MAX_DESCRIPTION_CHARS = 600


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


def normalize_description(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_DESCRIPTION_CHARS:
        return text
    return text[:MAX_DESCRIPTION_CHARS].rstrip() + "…"


def load_issues(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"CSV file not found: {path}")

    issues: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in islice(reader, limit):
            summary = row.get("Summary", "").strip()
            key = row.get("Issue key", "").strip()
            if not summary or not key:
                continue

            fix_versions = dedupe(value for name, value in row.items() if name.startswith("Fix versions"))
            components = dedupe(value for name, value in row.items() if name.startswith("Components"))
            labels = dedupe(value for name, value in row.items() if name.startswith("Labels"))

            issues.append(
                {
                    "key": key,
                    "summary": summary,
                    "priority": row.get("Priority", "").strip(),
                    "status": row.get("Status", "").strip(),
                    "resolution": row.get("Resolution", "").strip(),
                    "issue_type": row.get("Issue Type", "").strip(),
                    "fix_versions": fix_versions,
                    "components": components,
                    "labels": labels,
                    "description": normalize_description(row.get("Description", "")),
                }
            )
    if not issues:
        raise SystemExit("No issues found in the CSV.")
    return issues


def build_prompt(issues: list[dict]) -> str:
    lines = [
        "Convert the following Jira issues into a MediaWiki table suitable for release notes.",
        "Each row should include the ticket key, summary, components, fix versions, priority, issue type, status, resolution, labels, and description.",
        "Use concise text and keep the table valid MediaWiki syntax.",
        "",
    ]

    for idx, issue in enumerate(issues, start=1):
        line = (
            f"Issue {idx}: {issue['key']} | Summary: {issue['summary']} | Priority: {issue['priority']} | "
            f"Status: {issue['status']} | Resolution: {issue['resolution']} | Type: {issue['issue_type']} | "
            f"Fix Versions: {', '.join(issue['fix_versions']) or 'None'} | Components: {', '.join(issue['components']) or 'None'} | "
            f"Labels: {', '.join(issue['labels']) or 'None'} | Description: {issue['description']}"
        )
        lines.append(line)

    lines.append("")
    lines.append("Return only the MediaWiki markup.")
    return "\n".join(lines)


def call_openai(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4o",
        input=prompt,
    )
    return response.output_text


def process_file(csv_path: Path, output_path: Path) -> None:
    issues = load_issues(csv_path, MAX_ISSUES)
    prompt = build_prompt(issues)
    response_text = call_openai(prompt)
    output_path.write_text(response_text, encoding="utf-8")
    print(f"Wrote MediaWiki output for {len(issues)} issues to {output_path}.")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "-batch":
        if len(sys.argv) < 3:
            print("Error: Missing directory path for batch mode.")
            sys.exit(1)
        directory = Path(sys.argv[2])
        if not directory.is_dir():
            print(f"Error: {directory} is not a directory.")
            sys.exit(1)

        csv_files = sorted(directory.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in {directory}.")
            return

        default_csv = CSV_PATH.resolve()
        for csv_file in csv_files:
            output_path = OUTPUT_PATH if csv_file.resolve() == default_csv else csv_file.with_suffix(OUTPUT_PATH.suffix)
            process_file(csv_file, output_path)
    else:
        process_file(CSV_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()
