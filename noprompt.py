#!/usr/bin/env python3
"""Generate MediaWiki fixed issues notes from a Jira CSV export."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

CSV_PATH = Path("Jira.csv")
OUTPUT_PATH = Path("output.mw")

# Allowlist of resolutions that should appear in the release notes.
INCLUDED_RESOLUTIONS = {"", "fixed", "done", "completed"}


def load_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    return header, rows


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def natural_key(text: str) -> list[object]:
    parts = re.split(r"(\d+)", text)
    key: list[object] = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.lower())
    return key


def sanitize_cell(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "&mdash;"
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned.replace("\n", "<br/>")


def format_list(values: Sequence[str]) -> str:
    if not values:
        return "&mdash;"
    return ", ".join(values)


def issue_sort_key(issue: dict) -> tuple:
    primary_component = issue["components"][0].lower() if issue["components"] else "zzzz"
    return (primary_component, issue["summary"].lower(), issue["key"].lower())


def collect_issues(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[dict]:
    index = {name: header.index(name) for name in (
        "Summary",
        "Issue key",
        "Issue Type",
        "Status",
        "Resolution",
        "Priority",
        "Description",
    )}
    fix_indexes = [i for i, name in enumerate(header) if name == "Fix versions"]
    component_indexes = [i for i, name in enumerate(header) if name == "Components"]
    label_indexes = [i for i, name in enumerate(header) if name == "Labels"]

    issues: list[dict] = []
    for row in rows:
        summary = row[index["Summary"]].strip()
        if not summary:
            continue

        resolution = row[index["Resolution"]].strip().lower()
        if resolution not in INCLUDED_RESOLUTIONS:
            continue

        fix_versions = dedupe_preserve_order(row[i] for i in fix_indexes)
        if not fix_versions:
            fix_versions = ["Unscheduled"]

        issue = {
            "summary": summary,
            "key": row[index["Issue key"]].strip(),
            "issue_type": row[index["Issue Type"]].strip(),
            "status": row[index["Status"]].strip(),
            "resolution": row[index["Resolution"]].strip(),
            "priority": row[index["Priority"]].strip(),
            "description": row[index["Description"]],
            "fix_versions": fix_versions,
            "all_fix_versions": fix_versions,
            "components": dedupe_preserve_order(row[i] for i in component_indexes),
            "labels": dedupe_preserve_order(row[i] for i in label_indexes),
        }
        issues.append(issue)

    return issues


def group_by_fix_version(issues: Iterable[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        for version in issue["fix_versions"]:
            grouped[version].append(issue)
    return grouped


def ordered_fix_versions(grouped: dict[str, list[dict]]) -> list[str]:
    versions = list(grouped.keys())
    versions.sort(key=lambda value: (value == "Unscheduled", natural_key(value)))
    return versions


def build_table_rows(issues: Iterable[dict]) -> list[str]:
    rows: list[str] = []
    for issue in sorted(issues, key=issue_sort_key):
        ticket_link = f"[https://splunk.atlassian.net/browse/{issue['key']} {issue['key']}]"
        summary = sanitize_cell(issue["summary"])
        components = format_list(issue["components"])
        priority = sanitize_cell(issue["priority"])
        issue_type = sanitize_cell(issue["issue_type"])
        status = sanitize_cell(issue["status"])
        resolution = sanitize_cell(issue["resolution"])
        labels = format_list(issue["labels"])
        description = sanitize_cell(issue["description"])
        fix_versions = format_list(issue["all_fix_versions"])

        rows.extend([
            "|-",
            f"| {ticket_link}",
            f"| {summary}",
            f"| {components}",
            f"| {fix_versions}",
            f"| {priority}",
            f"| {issue_type}",
            f"| {status}",
            f"| {resolution}",
            f"| {labels}",
            f"| {description}",
        ])
    return rows


def build_release_notes(grouped: dict[str, list[dict]]) -> str:
    lines: list[str] = [
        "= Fixed issues =",
        "This page lists Jira tickets that were marked as fixed and are ready to be published in the release notes.",
        "",
    ]

    for version in ordered_fix_versions(grouped):
        issues = grouped[version]
        lines.append(f"== {version} ==")
        if version == "Unscheduled":
            lines.append("Tickets below do not yet have a scheduled fix version.")
        lines.append("{| class=\"wikitable sortable\"")
        lines.append("! Ticket !! Summary !! Components !! Fix version(s) !! Priority !! Issue type !! Status !! Resolution !! Labels !! Notes")
        lines.extend(build_table_rows(issues))
        lines.append("|}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV file not found: {CSV_PATH}")

    header, rows = load_csv(CSV_PATH)
    issues = collect_issues(header, rows)
    if not issues:
        raise SystemExit("No issues with acceptable resolution were found in the CSV export.")

    grouped = group_by_fix_version(issues)
    release_notes = build_release_notes(grouped)
    OUTPUT_PATH.write_text(release_notes, encoding="utf-8")
    unique_issue_count = len({issue["key"] for issue in issues})
    print(
        f"Wrote {OUTPUT_PATH} with {unique_issue_count} unique issues across {len(grouped)} fix version buckets."
    )


if __name__ == "__main__":
    main()
