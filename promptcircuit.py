#!/usr/bin/env python3
"""Call Cisco GPT endpoint to generate MediaWiki release notes from Jira CSV."""
from __future__ import annotations

import csv
import os
from itertools import islice
from pathlib import Path
from typing import Iterable

import requests

CSV_PATH = Path("Jira.csv")
OUTPUT_PATH = Path("circuitresponse.mw")
API_URL = "https://chat-ai.cisco.com/openai/deployments/gpt-4o-mini/chat/completions"
API_USER_FIELD = '{"appkey":"egai-prd-ther-020122487-coding-1758642862113"}'
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


def call_cisco_api(prompt: str) -> str:
    api_key = os.environ.get("CISCO_API_KEY")
    if not api_key:
        raise SystemExit("CISCO_API_KEY environment variable is not set.")

    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "user": API_USER_FIELD,
        "stop": ["<|im_end|>"],
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "api-key": api_key,
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise SystemExit(f"Unexpected response structure: {data}") from exc


def main() -> None:
    issues = load_issues(CSV_PATH, MAX_ISSUES)
    prompt = build_prompt(issues)
    response_text = call_cisco_api(prompt)
    OUTPUT_PATH.write_text(response_text, encoding="utf-8")
    print(f"Wrote MediaWiki output for {len(issues)} issues to {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
