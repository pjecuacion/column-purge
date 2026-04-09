from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


REPORT_FILTERED = "Filtered Issues"
REPORT_MAPPING = "Story To Parent Mapping"
REPORT_MISSING_POINTS = "Missing Story Points"
REPORT_MISSING_PARENT = "Missing Parent"
REPORT_SPRINT_SUMMARY = "Sprint Summary"
REPORT_ASSIGNEE = "Assignee Workload"
REPORT_EPIC_BREAKDOWN = "Epic Breakdown"

REPORTS = [
    REPORT_FILTERED,
    REPORT_MAPPING,
    REPORT_MISSING_POINTS,
    REPORT_MISSING_PARENT,
    REPORT_SPRINT_SUMMARY,
    REPORT_ASSIGNEE,
    REPORT_EPIC_BREAKDOWN,
]

WORK_ITEM_TYPES = {"story", "bug", "task", "sub-task", "subtask"}
PARENT_CONTAINER_TYPES = {"epic", "feature", "initiative"}
PARENT_KIND_OPTIONS = ["All", "Epic", "Feature", "Other Matched Parent", "Unmatched Parent Key", "No Parent Key"]
QUICK_PRESET_OPTIONS = ["None", "Active Delivery", "Planning Gaps", "Needs Triage", "Ready For Grooming"]
RECENT_DAYS = 7
STALE_DAYS = 14


@dataclass
class LoadedDataset:
    path: Path
    original_headers: list[str]
    unique_headers: list[str]
    rows: list[dict[str, str]]
    raw_rows: list[list[str]]
    groups: dict[str, list[str]]
    issues: list[dict[str, object]]
    issue_lookup: dict[str, dict[str, object]]


def unique_headers(headers: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    unique: list[str] = []
    for header in headers:
        name = header.strip() or "Unnamed"
        counts[name] += 1
        suffix = counts[name]
        unique.append(name if suffix == 1 else f"{name}__{suffix}")
    return unique


def csv_rows_from_path(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError("The selected CSV file is empty.")
    header = rows[0]
    data_rows = [pad_row(row, len(header)) for row in rows[1:]]
    return header, data_rows


def pad_row(row: list[str], width: int) -> list[str]:
    if len(row) >= width:
        return row[:width]
    return row + [""] * (width - len(row))


def first_non_empty(values: list[str]) -> str:
    for value in values:
        if value.strip():
            return value.strip()
    return ""


def distinct_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def parse_points(raw: str) -> float | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_points(value: float | None) -> str:
    if value is None:
        return ""
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def normalize_status_bucket(status_category: str) -> str:
    cleaned = status_category.strip().lower()
    if cleaned == "done":
        return "done"
    if cleaned in {"in progress", "indeterminate"}:
        return "in_progress"
    return "todo"


def parse_jira_datetime(raw: str) -> datetime | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%b/%Y %I:%M %p",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def normalize_issue(row: dict[str, str], groups: dict[str, list[str]]) -> dict[str, object]:
    def values(label: str) -> list[str]:
        return [row.get(unique_name, "") for unique_name in groups.get(label, [])]

    issue_key = first_non_empty(values("Issue key"))
    story_points_raw = first_non_empty(values("Custom field (Story Points)"))
    dev_points_raw = first_non_empty(values("Custom field (Dev Story points)"))
    test_points_raw = first_non_empty(values("Custom field (Test Story Points)"))

    story_points = parse_points(story_points_raw)
    dev_points = parse_points(dev_points_raw)
    test_points = parse_points(test_points_raw)

    estimate_value = story_points
    estimate_source = "Story Points" if story_points is not None else ""
    if estimate_value is None and dev_points is not None:
        estimate_value = dev_points
        estimate_source = "Dev Story Points"
    if estimate_value is None and test_points is not None:
        estimate_value = test_points
        estimate_source = "Test Story Points"

    sprint_values = distinct_non_empty(values("Sprint"))
    description = first_non_empty(values("Description"))
    created_raw = first_non_empty(values("Created"))
    updated_raw = first_non_empty(values("Updated"))
    created_at = parse_jira_datetime(created_raw)
    updated_at = parse_jira_datetime(updated_raw)
    now = datetime.now()
    point_values = [value for value in [story_points, dev_points, test_points] if value is not None]
    distinct_points = {float(value) for value in point_values}
    issue_type = first_non_empty(values("Issue Type"))
    issue_type_lower = issue_type.strip().lower()
    status = first_non_empty(values("Status"))
    status_category = first_non_empty(values("Status Category"))
    status_bucket = normalize_status_bucket(status_category)
    assignee = first_non_empty(values("Assignee")) or "Unassigned"
    priority = first_non_empty(values("Priority"))
    severity = first_non_empty(values("Custom field (Severity)"))

    return {
        "issue_key": issue_key,
        "summary": first_non_empty(values("Summary")),
        "description": description,
        "description_empty": not bool(description),
        "issue_type": issue_type,
        "status": status,
        "status_category": status_category,
        "status_bucket": status_bucket,
        "assignee": assignee,
        "reporter": first_non_empty(values("Reporter")),
        "parent_key": first_non_empty(values("Parent key")),
        "parent_summary": first_non_empty(values("Parent summary")),
        "project_key": first_non_empty(values("Project key")),
        "created": created_raw,
        "updated": updated_raw,
        "created_at": created_at,
        "updated_at": updated_at,
        "priority": priority,
        "severity": severity,
        "story_points_raw": story_points_raw,
        "dev_story_points_raw": dev_points_raw,
        "test_story_points_raw": test_points_raw,
        "story_points": story_points,
        "dev_story_points": dev_points,
        "test_story_points": test_points,
        "effective_estimate": estimate_value,
        "estimate_source": estimate_source,
        "sprints": sprint_values,
        "sprint_display": ", ".join(sprint_values),
        "parent_found": False,
        "parent_type": "",
        "parent_kind": "No Parent Key",
        "missing_story_points": not bool(story_points_raw.strip()),
        "missing_dev_story_points": not bool(dev_points_raw.strip()),
        "missing_test_story_points": not bool(test_points_raw.strip()),
        "estimate_mismatch": len(distinct_points) >= 2,
        "is_unassigned": assignee == "Unassigned",
        "no_sprint": not bool(sprint_values),
        "multi_sprint": len(sprint_values) > 1,
        "is_container": issue_type_lower in PARENT_CONTAINER_TYPES,
        "is_story": issue_type_lower == "story",
        "is_bug": issue_type_lower == "bug",
        "is_task_like": issue_type_lower in {"task", "sub-task", "subtask"},
        "is_done": status_bucket == "done",
        "is_active": status_bucket != "done",
        "is_backlog": status.strip().lower() == "backlog",
        "is_critical_or_blocker": priority.strip().lower() == "blocker" or severity.strip().lower() == "critical",
        "recently_updated": bool(updated_at and (now - updated_at).days <= RECENT_DAYS),
        "created_recently": bool(created_at and (now - created_at).days <= RECENT_DAYS),
        "stale_not_done": bool(updated_at and status_bucket != "done" and (now - updated_at).days >= STALE_DAYS),
    }


def parent_kind_for_issue(issue: dict[str, object], issue_lookup: dict[str, dict[str, object]]) -> str:
    parent_key = str(issue["parent_key"])
    if not parent_key:
        return "No Parent Key"
    parent_issue = issue_lookup.get(parent_key)
    if not parent_issue:
        return "Unmatched Parent Key"
    parent_type = str(parent_issue.get("issue_type", "")).strip().lower()
    if parent_type == "epic":
        return "Epic"
    if parent_type == "feature":
        return "Feature"
    return "Other Matched Parent"


def matches_quick_preset(issue: dict[str, object], preset_name: str) -> bool:
    if preset_name == "None":
        return True
    if preset_name == "Active Delivery":
        return bool(issue["is_active"])
    if preset_name == "Planning Gaps":
        return bool(
            issue["is_active"]
            and (
                issue["missing_story_points"]
                or issue["missing_dev_story_points"]
                or issue["missing_test_story_points"]
                or issue["description_empty"]
                or issue["parent_kind"] in {"No Parent Key", "Unmatched Parent Key"}
            )
        )
    if preset_name == "Needs Triage":
        return bool(
            issue["is_active"]
            and (
                issue["is_unassigned"]
                or issue["is_critical_or_blocker"]
                or issue["parent_kind"] == "Unmatched Parent Key"
                or issue["description_empty"]
            )
        )
    if preset_name == "Ready For Grooming":
        return bool(
            issue["is_active"]
            and not issue["is_container"]
            and issue["status_bucket"] == "todo"
            and (
                issue["missing_story_points"]
                or issue["description_empty"]
                or issue["parent_kind"] in {"No Parent Key", "Unmatched Parent Key"}
            )
        )
    return True


class JiraAnalyzer:
    def load_csv(self, file_path: str) -> LoadedDataset:
        path = Path(file_path)
        original_headers, raw_rows = csv_rows_from_path(path)
        uniq_headers = unique_headers(original_headers)
        groups: dict[str, list[str]] = defaultdict(list)
        for original, unique_name in zip(original_headers, uniq_headers):
            groups[original.strip() or "Unnamed"].append(unique_name)

        rows: list[dict[str, str]] = []
        issues: list[dict[str, object]] = []
        for raw_row in raw_rows:
            row = {unique_name: value for unique_name, value in zip(uniq_headers, raw_row)}
            rows.append(row)
            issues.append(normalize_issue(row, groups))

        issue_lookup = {
            issue["issue_key"]: issue
            for issue in issues
            if isinstance(issue.get("issue_key"), str) and issue["issue_key"]
        }

        for issue in issues:
            parent_key = str(issue["parent_key"])
            parent_issue = issue_lookup.get(parent_key)
            issue["parent_found"] = bool(parent_issue)
            issue["parent_type"] = str(parent_issue["issue_type"]) if parent_issue else ""
            issue["parent_kind"] = parent_kind_for_issue(issue, issue_lookup)

        return LoadedDataset(
            path=path,
            original_headers=original_headers,
            unique_headers=uniq_headers,
            rows=rows,
            raw_rows=raw_rows,
            groups=dict(groups),
            issues=issues,
            issue_lookup=issue_lookup,
        )

    def filter_issues(
        self,
        dataset: LoadedDataset,
        issue_type: str,
        status: str,
        status_category: str,
        parent_key: str,
        parent_kind: str,
        assignee: str,
        sprint: str,
        search_text: str,
        quick_preset: str,
        exclude_done: bool,
        only_active: bool,
        only_unassigned: bool,
        no_sprint_only: bool,
        empty_description_only: bool,
        missing_story_points_only: bool,
        missing_dev_story_points_only: bool,
        missing_test_story_points_only: bool,
        missing_parent_only: bool,
        estimate_mismatch_only: bool,
        exclude_epics_features: bool,
        only_stories: bool,
        only_bugs: bool,
        only_tasks_subtasks: bool,
        backlog_only: bool,
        critical_only: bool,
        stale_not_done_only: bool,
        recently_updated_only: bool,
        created_recently_only: bool,
        multi_sprint_only: bool,
    ) -> list[dict[str, object]]:
        filtered: list[dict[str, object]] = []
        needle = search_text.strip().lower()
        for issue in dataset.issues:
            if quick_preset != "None" and not matches_quick_preset(issue, quick_preset):
                continue
            if issue_type != "All" and issue["issue_type"] != issue_type:
                continue
            if status != "All" and issue["status"] != status:
                continue
            if status_category != "All" and issue["status_category"] != status_category:
                continue
            if parent_key != "All":
                expected_parent = "" if parent_key == "(None)" else parent_key
                if issue["parent_key"] != expected_parent:
                    continue
            if parent_kind != "All" and issue["parent_kind"] != parent_kind:
                continue
            if assignee != "All" and issue["assignee"] != assignee:
                continue
            if sprint != "All":
                if sprint == "(None)":
                    if issue["sprints"]:
                        continue
                elif sprint not in issue["sprints"]:
                    continue
            if needle:
                haystack = " ".join(
                    [
                        str(issue["issue_key"]),
                        str(issue["summary"]),
                        str(issue["parent_key"]),
                        str(issue["parent_summary"]),
                        str(issue["assignee"]),
                    ]
                ).lower()
                if needle not in haystack:
                    continue
            if exclude_done and issue["is_done"]:
                continue
            if only_active and not issue["is_active"]:
                continue
            if only_unassigned and not issue["is_unassigned"]:
                continue
            if no_sprint_only and not issue["no_sprint"]:
                continue
            if empty_description_only and not issue["description_empty"]:
                continue
            if missing_story_points_only and not issue["missing_story_points"]:
                continue
            if missing_dev_story_points_only and not issue["missing_dev_story_points"]:
                continue
            if missing_test_story_points_only and not issue["missing_test_story_points"]:
                continue
            if missing_parent_only and issue["parent_kind"] not in {"No Parent Key", "Unmatched Parent Key"}:
                continue
            if estimate_mismatch_only and not issue["estimate_mismatch"]:
                continue
            if exclude_epics_features and issue["is_container"]:
                continue
            if only_stories and not issue["is_story"]:
                continue
            if only_bugs and not issue["is_bug"]:
                continue
            if only_tasks_subtasks and not issue["is_task_like"]:
                continue
            if backlog_only and not issue["is_backlog"]:
                continue
            if critical_only and not issue["is_critical_or_blocker"]:
                continue
            if stale_not_done_only and not issue["stale_not_done"]:
                continue
            if recently_updated_only and not issue["recently_updated"]:
                continue
            if created_recently_only and not issue["created_recently"]:
                continue
            if multi_sprint_only and not issue["multi_sprint"]:
                continue
            filtered.append(issue)
        return filtered

    def report_filtered(self, issues: list[dict[str, object]]) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Issue Key",
            "Summary",
            "Type",
            "Status",
            "Status Category",
            "Assignee",
            "Parent Key",
            "Parent Kind",
            "Parent Summary",
            "Sprint",
            "Story Points",
            "Dev Story Points",
            "Test Story Points",
            "Estimate",
            "Estimate Source",
            "Description Empty",
        ]
        rows = [
            [
                str(issue["issue_key"]),
                str(issue["summary"]),
                str(issue["issue_type"]),
                str(issue["status"]),
                str(issue["status_category"]),
                str(issue["assignee"]),
                str(issue["parent_key"]),
                str(issue["parent_kind"]),
                str(issue["parent_summary"]),
                str(issue["sprint_display"]),
                str(issue["story_points_raw"]),
                str(issue["dev_story_points_raw"]),
                str(issue["test_story_points_raw"]),
                format_points(issue["effective_estimate"]),
                str(issue["estimate_source"]),
                "Yes" if issue["description_empty"] else "No",
            ]
            for issue in issues
        ]
        summary = f"Showing {len(rows)} issue rows after filters."
        return columns, rows, summary

    def report_mapping(
        self, dataset: LoadedDataset, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Issue Key",
            "Summary",
            "Type",
            "Status",
            "Parent Key",
            "Parent Summary",
            "Parent Found",
            "Parent Type",
            "Parent Kind",
            "Story Points",
            "Dev Story Points",
            "Test Story Points",
            "Estimate",
            "Estimate Source",
        ]
        rows: list[list[str]] = []
        orphan_count = 0
        for issue in issues:
            parent_key = str(issue["parent_key"])
            parent_issue = dataset.issue_lookup.get(parent_key)
            parent_found = "Yes" if parent_issue else "No"
            if not parent_key or not parent_issue:
                orphan_count += 1
            rows.append(
                [
                    str(issue["issue_key"]),
                    str(issue["summary"]),
                    str(issue["issue_type"]),
                    str(issue["status"]),
                    parent_key,
                    str(issue["parent_summary"]),
                    parent_found,
                    str(parent_issue["issue_type"]) if parent_issue else "",
                    str(issue["parent_kind"]),
                    str(issue["story_points_raw"]),
                    str(issue["dev_story_points_raw"]),
                    str(issue["test_story_points_raw"]),
                    format_points(issue["effective_estimate"]),
                    str(issue["estimate_source"]),
                ]
            )
        summary = f"Mapped {len(rows)} issues. {orphan_count} rows are missing a matched parent."
        return columns, rows, summary

    def report_missing_story_points(
        self, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Issue Key",
            "Summary",
            "Type",
            "Status",
            "Assignee",
            "Parent Key",
            "Sprint",
            "Parent Kind",
            "Story Points",
            "Dev Story Points",
            "Test Story Points",
            "Description Empty",
        ]
        rows: list[list[str]] = []
        for issue in issues:
            issue_type = str(issue["issue_type"]).strip().lower()
            if issue_type in PARENT_CONTAINER_TYPES or issue_type == "epic":
                continue
            if str(issue["story_points_raw"]).strip():
                continue
            rows.append(
                [
                    str(issue["issue_key"]),
                    str(issue["summary"]),
                    str(issue["issue_type"]),
                    str(issue["status"]),
                    str(issue["assignee"]),
                    str(issue["parent_key"]),
                    str(issue["sprint_display"]),
                    str(issue["parent_kind"]),
                    str(issue["story_points_raw"]),
                    str(issue["dev_story_points_raw"]),
                    str(issue["test_story_points_raw"]),
                    "Yes" if issue["description_empty"] else "No",
                ]
            )
        summary = f"Found {len(rows)} issues without Story Points."
        return columns, rows, summary

    def report_missing_parent(
        self, dataset: LoadedDataset, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Issue Key",
            "Summary",
            "Type",
            "Status",
            "Assignee",
            "Parent Key",
            "Parent Summary",
            "Parent Kind",
            "Parent Type",
            "Parent Status",
            "Description Empty",
        ]
        rows: list[list[str]] = []
        for issue in issues:
            issue_type = str(issue["issue_type"]).strip().lower()
            if issue_type in PARENT_CONTAINER_TYPES:
                continue
            if issue_type not in WORK_ITEM_TYPES:
                continue
            parent_key = str(issue["parent_key"])
            parent_issue = dataset.issue_lookup.get(parent_key)
            if parent_key and parent_issue:
                continue
            rows.append(
                [
                    str(issue["issue_key"]),
                    str(issue["summary"]),
                    str(issue["issue_type"]),
                    str(issue["status"]),
                    str(issue["assignee"]),
                    parent_key,
                    str(issue["parent_summary"]),
                    str(issue["parent_kind"]),
                    str(issue["parent_type"]),
                    str(parent_issue["status"]) if parent_issue else "",
                    "Yes" if issue["description_empty"] else "No",
                ]
            )
        summary = f"Found {len(rows)} work items without a matched parent."
        return columns, rows, summary

    def report_sprint_summary(
        self, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Sprint",
            "Issue Count",
            "Total Estimate",
            "To Do",
            "In Progress",
            "Done",
            "Unestimated",
        ]
        aggregates: dict[str, dict[str, float]] = {}
        for issue in issues:
            sprints = issue["sprints"] or ["(No Sprint)"]
            for sprint in sprints:
                bucket = aggregates.setdefault(
                    str(sprint),
                    {
                        "issue_count": 0,
                        "total_estimate": 0.0,
                        "todo": 0,
                        "in_progress": 0,
                        "done": 0,
                        "unestimated": 0,
                    },
                )
                bucket["issue_count"] += 1
                estimate = issue["effective_estimate"]
                if estimate is None:
                    bucket["unestimated"] += 1
                else:
                    bucket["total_estimate"] += float(estimate)
                bucket[str(issue["status_bucket"])] += 1

        rows = [
            [
                sprint,
                str(int(values["issue_count"])),
                format_points(float(values["total_estimate"])),
                str(int(values["todo"])),
                str(int(values["in_progress"])),
                str(int(values["done"])),
                str(int(values["unestimated"])),
            ]
            for sprint, values in sorted(aggregates.items(), key=lambda item: item[0].lower())
        ]
        summary = f"Summarized {len(rows)} sprint buckets from {len(issues)} filtered issues."
        return columns, rows, summary

    def report_assignee_workload(
        self, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        columns = [
            "Assignee",
            "Issue Count",
            "Total Estimate",
            "To Do",
            "In Progress",
            "Done",
            "Unestimated",
        ]
        aggregates: dict[str, dict[str, float]] = {}
        for issue in issues:
            assignee = str(issue["assignee"]) or "Unassigned"
            bucket = aggregates.setdefault(
                assignee,
                {
                    "issue_count": 0,
                    "total_estimate": 0.0,
                    "todo": 0,
                    "in_progress": 0,
                    "done": 0,
                    "unestimated": 0,
                },
            )
            bucket["issue_count"] += 1
            estimate = issue["effective_estimate"]
            if estimate is None:
                bucket["unestimated"] += 1
            else:
                bucket["total_estimate"] += float(estimate)
            bucket[str(issue["status_bucket"])] += 1

        rows = [
            [
                assignee,
                str(int(values["issue_count"])),
                format_points(float(values["total_estimate"])),
                str(int(values["todo"])),
                str(int(values["in_progress"])),
                str(int(values["done"])),
                str(int(values["unestimated"])),
            ]
            for assignee, values in sorted(aggregates.items(), key=lambda item: item[0].lower())
        ]
        summary = f"Summarized workload for {len(rows)} assignees."
        return columns, rows, summary

    def report_epic_breakdown(
        self, dataset: LoadedDataset, issues: list[dict[str, object]]
    ) -> tuple[list[tuple[dict[str, object], list[dict[str, object]]]], list[dict[str, object]], str]:
        children_by_epic: dict[str, list[dict[str, object]]] = defaultdict(list)
        orphans: list[dict[str, object]] = []

        for issue in issues:
            if issue["is_container"]:
                continue
            parent_key = str(issue["parent_key"])
            parent = dataset.issue_lookup.get(parent_key)
            if parent and parent["is_container"]:
                children_by_epic[str(parent["issue_key"])].append(issue)
            else:
                orphans.append(issue)

        epic_keys_with_children = set(children_by_epic.keys())
        epic_keys_in_filtered = {str(i["issue_key"]) for i in issues if i["is_container"]}
        all_epic_keys = epic_keys_with_children | epic_keys_in_filtered

        groups: list[tuple[dict[str, object], list[dict[str, object]]]] = []
        for epic_key in sorted(all_epic_keys):
            epic_issue = dataset.issue_lookup.get(epic_key)
            if not epic_issue:
                continue
            groups.append((epic_issue, list(children_by_epic.get(epic_key, []))))
        groups.sort(key=lambda g: str(g[0]["issue_key"]).lower())

        child_total = sum(len(c) for _, c in groups)
        summary = f"{len(groups)} epics | {child_total} child issues | {len(orphans)} without matched epic."
        return groups, orphans, summary

    def build_report(
        self, dataset: LoadedDataset, report_name: str, issues: list[dict[str, object]]
    ) -> tuple[list[str], list[list[str]], str]:
        if report_name == REPORT_MAPPING:
            return self.report_mapping(dataset, issues)
        if report_name == REPORT_MISSING_POINTS:
            return self.report_missing_story_points(issues)
        if report_name == REPORT_MISSING_PARENT:
            return self.report_missing_parent(dataset, issues)
        if report_name == REPORT_SPRINT_SUMMARY:
            return self.report_sprint_summary(issues)
        if report_name == REPORT_ASSIGNEE:
            return self.report_assignee_workload(issues)
        return self.report_filtered(issues)

    def cleaned_csv_rows(self, dataset: LoadedDataset) -> list[list[str]]:
        keep_indices: list[int] = []
        total_columns = len(dataset.original_headers)
        for index in range(total_columns):
            if any(index < len(row) and row[index].strip() for row in dataset.raw_rows):
                keep_indices.append(index)
        cleaned = [[dataset.original_headers[index] for index in keep_indices]]
        cleaned.extend(
            [[row[index] if index < len(row) else "" for index in keep_indices] for row in dataset.raw_rows]
        )
        return cleaned


class JiraAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Jira CSV Analyzer")
        self.root.geometry("1400x860")
        self.root.minsize(1100, 700)

        self.analyzer = JiraAnalyzer()
        self.dataset: LoadedDataset | None = None
        self.current_columns: list[str] = []
        self.current_rows: list[list[str]] = []

        self.report_var = tk.StringVar(value=REPORT_FILTERED)
        self.issue_type_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")
        self.status_category_var = tk.StringVar(value="All")
        self.parent_var = tk.StringVar(value="All")
        self.parent_kind_var = tk.StringVar(value="All")
        self.assignee_var = tk.StringVar(value="All")
        self.sprint_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.quick_preset_var = tk.StringVar(value="None")
        self.exclude_done_var = tk.BooleanVar(value=False)
        self.only_active_var = tk.BooleanVar(value=False)
        self.only_unassigned_var = tk.BooleanVar(value=False)
        self.no_sprint_only_var = tk.BooleanVar(value=False)
        self.empty_description_only_var = tk.BooleanVar(value=False)
        self.missing_story_points_only_var = tk.BooleanVar(value=False)
        self.missing_dev_story_points_only_var = tk.BooleanVar(value=False)
        self.missing_test_story_points_only_var = tk.BooleanVar(value=False)
        self.missing_parent_only_var = tk.BooleanVar(value=False)
        self.estimate_mismatch_only_var = tk.BooleanVar(value=False)
        self.exclude_epics_features_var = tk.BooleanVar(value=False)
        self.only_stories_var = tk.BooleanVar(value=False)
        self.only_bugs_var = tk.BooleanVar(value=False)
        self.only_tasks_subtasks_var = tk.BooleanVar(value=False)
        self.backlog_only_var = tk.BooleanVar(value=False)
        self.critical_only_var = tk.BooleanVar(value=False)
        self.stale_not_done_only_var = tk.BooleanVar(value=False)
        self.recently_updated_only_var = tk.BooleanVar(value=False)
        self.created_recently_only_var = tk.BooleanVar(value=False)
        self.multi_sprint_only_var = tk.BooleanVar(value=False)
        self.file_label_var = tk.StringVar(value="No CSV loaded")
        self.summary_var = tk.StringVar(value="Load a Jira CSV export to begin.")
        self.status_var_text = tk.StringVar(value="Ready")
        self.counts_var = tk.StringVar(value="Rows: 0 | Columns: 0 | Issues: 0")

        self._build_ui()
        self._bind_events()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        top = ttk.Frame(self.root, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(4, weight=1)

        ttk.Button(top, text="Load Jira CSV", command=self.load_csv).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(top, text="Export Report", command=self.export_report).grid(row=0, column=1, padx=8)
        ttk.Button(top, text="Export Cleaned CSV", command=self.export_cleaned_csv).grid(row=0, column=2, padx=8)
        ttk.Button(top, text="Reset Filters", command=self.reset_filters).grid(row=0, column=3, padx=8)
        ttk.Label(top, textvariable=self.file_label_var).grid(row=0, column=4, sticky="e")

        summary = ttk.LabelFrame(self.root, text="Dataset", padding=12)
        summary.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        summary.columnconfigure(1, weight=1)
        ttk.Label(summary, textvariable=self.counts_var).grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.summary_var).grid(row=0, column=1, sticky="e")

        filters = ttk.LabelFrame(self.root, text="Filters And Report", padding=12)
        filters.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        for column in range(4):
            filters.columnconfigure(column, weight=1)

        self.report_combo = self._add_combo(filters, "Report", self.report_var, REPORTS, 0, 0)
        self.issue_type_combo = self._add_combo(filters, "Issue Type", self.issue_type_var, ["All"], 0, 1)
        self.status_combo = self._add_combo(filters, "Status", self.status_var, ["All"], 0, 2)
        self.status_category_combo = self._add_combo(
            filters, "Status Category", self.status_category_var, ["All"], 0, 3
        )
        self.parent_combo = self._add_combo(filters, "Parent Key", self.parent_var, ["All"], 2, 0)
        self.parent_kind_combo = self._add_combo(filters, "Parent Kind", self.parent_kind_var, PARENT_KIND_OPTIONS, 2, 1)
        self.assignee_combo = self._add_combo(filters, "Assignee", self.assignee_var, ["All"], 2, 2)
        self.sprint_combo = self._add_combo(filters, "Sprint", self.sprint_var, ["All"], 2, 3)

        ttk.Label(filters, text="Quick Preset").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.quick_preset_combo = ttk.Combobox(
            filters,
            textvariable=self.quick_preset_var,
            values=QUICK_PRESET_OPTIONS,
            state="readonly",
        )
        self.quick_preset_combo.grid(row=5, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(2, 0))
        ttk.Label(
            filters,
            text="Preset bundles for delivery, triage, and grooming views.",
        ).grid(row=5, column=2, columnspan=2, sticky="w", pady=(2, 0))

        ttk.Label(filters, text="Quick Filters").grid(row=6, column=0, sticky="w", pady=(10, 0))
        quick_filters = ttk.Frame(filters)
        quick_filters.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(2, 0))
        quick_filters.columnconfigure(0, weight=1)
        quick_filters.columnconfigure(1, weight=1)
        quick_filters.columnconfigure(2, weight=1)
        quick_filters.columnconfigure(3, weight=1)
        ttk.Checkbutton(
            quick_filters,
            text="Exclude done",
            variable=self.exclude_done_var,
            command=self.refresh_report,
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Only active",
            variable=self.only_active_var,
            command=self.refresh_report,
        ).grid(row=0, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Only unassigned",
            variable=self.only_unassigned_var,
            command=self.refresh_report,
        ).grid(row=0, column=2, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="No sprint",
            variable=self.no_sprint_only_var,
            command=self.refresh_report,
        ).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(
            quick_filters,
            text="Empty descriptions",
            variable=self.empty_description_only_var,
            command=self.refresh_report,
        ).grid(row=1, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Missing story points",
            variable=self.missing_story_points_only_var,
            command=self.refresh_report,
        ).grid(row=1, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Missing dev points",
            variable=self.missing_dev_story_points_only_var,
            command=self.refresh_report,
        ).grid(row=1, column=2, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Missing test points",
            variable=self.missing_test_story_points_only_var,
            command=self.refresh_report,
        ).grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(
            quick_filters,
            text="Missing parent",
            variable=self.missing_parent_only_var,
            command=self.refresh_report,
        ).grid(row=2, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Estimate mismatch",
            variable=self.estimate_mismatch_only_var,
            command=self.refresh_report,
        ).grid(row=2, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Exclude epics/features",
            variable=self.exclude_epics_features_var,
            command=self.refresh_report,
        ).grid(row=2, column=2, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Only stories",
            variable=self.only_stories_var,
            command=self.refresh_report,
        ).grid(row=2, column=3, sticky="w")
        ttk.Checkbutton(
            quick_filters,
            text="Only bugs",
            variable=self.only_bugs_var,
            command=self.refresh_report,
        ).grid(row=3, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Only tasks/sub-tasks",
            variable=self.only_tasks_subtasks_var,
            command=self.refresh_report,
        ).grid(row=3, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Backlog only",
            variable=self.backlog_only_var,
            command=self.refresh_report,
        ).grid(row=3, column=2, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Critical / blocker",
            variable=self.critical_only_var,
            command=self.refresh_report,
        ).grid(row=3, column=3, sticky="w")
        ttk.Checkbutton(
            quick_filters,
            text=f"Stale not done ({STALE_DAYS}d+)",
            variable=self.stale_not_done_only_var,
            command=self.refresh_report,
        ).grid(row=4, column=0, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text=f"Recently updated ({RECENT_DAYS}d)",
            variable=self.recently_updated_only_var,
            command=self.refresh_report,
        ).grid(row=4, column=1, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text=f"Created recently ({RECENT_DAYS}d)",
            variable=self.created_recently_only_var,
            command=self.refresh_report,
        ).grid(row=4, column=2, sticky="w", padx=(0, 16))
        ttk.Checkbutton(
            quick_filters,
            text="Multi-sprint",
            variable=self.multi_sprint_only_var,
            command=self.refresh_report,
        ).grid(row=4, column=3, sticky="w")

        ttk.Label(filters, text="Search").grid(row=8, column=0, sticky="w", pady=(10, 0))
        search_entry = ttk.Entry(filters, textvariable=self.search_var)
        search_entry.grid(row=9, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(2, 0))
        ttk.Label(
            filters,
            text="Searches issue key, summary, parent, and assignee.",
        ).grid(row=9, column=2, columnspan=2, sticky="w", pady=(2, 0))

        results = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        results.grid(row=3, column=0, sticky="nsew")
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(results, columns=(), show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(results, orient="vertical", command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(results, orient="horizontal", command=self.tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        status = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        status.grid(row=4, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status_var_text).grid(row=0, column=0, sticky="w")

    def _add_combo(
        self,
        parent: ttk.Widget,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        row: int,
        column: int,
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w")
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        combo.grid(row=row + 1, column=column, sticky="ew", padx=(0, 12), pady=(2, 6))
        return combo

    def _bind_events(self) -> None:
        for combo in [
            self.report_combo,
            self.issue_type_combo,
            self.status_combo,
            self.status_category_combo,
            self.parent_combo,
            self.parent_kind_combo,
            self.assignee_combo,
            self.sprint_combo,
            self.quick_preset_combo,
        ]:
            combo.bind("<<ComboboxSelected>>", self._handle_filter_event)
        self.root.bind_all("<Control-o>", lambda _event: self.load_csv())
        self.search_var.trace_add("write", self._handle_search_change)

    def _handle_filter_event(self, _event: tk.Event) -> None:
        self.refresh_report()

    def _handle_search_change(self, *_args: object) -> None:
        self.refresh_report()

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Jira CSV Export",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            dataset = self.analyzer.load_csv(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load Failed", str(exc))
            return

        self.dataset = dataset
        self.file_label_var.set(dataset.path.name)
        self.counts_var.set(
            f"Rows: {len(dataset.raw_rows)} | Columns: {len(dataset.original_headers)} | Issues: {len(dataset.issues)}"
        )
        self.status_var_text.set(f"Loaded {dataset.path}")
        self.summary_var.set("Normalized duplicate Jira headers and prepared report views.")
        self._populate_filter_values()
        self.refresh_report()

    def _populate_filter_values(self) -> None:
        if not self.dataset:
            return

        issues = self.dataset.issues
        issue_types = sorted({str(issue["issue_type"]) for issue in issues if issue["issue_type"]})
        statuses = sorted({str(issue["status"]) for issue in issues if issue["status"]})
        categories = sorted({str(issue["status_category"]) for issue in issues if issue["status_category"]})
        parents = sorted({str(issue["parent_key"]) for issue in issues if issue["parent_key"]})
        assignees = sorted({str(issue["assignee"]) for issue in issues if issue["assignee"]})

        sprint_values: set[str] = set()
        for issue in issues:
            sprint_values.update(str(sprint) for sprint in issue["sprints"])
        sprints = sorted(sprint_values)

        self.issue_type_combo["values"] = ["All"] + issue_types
        self.status_combo["values"] = ["All"] + statuses
        self.status_category_combo["values"] = ["All"] + categories
        self.parent_combo["values"] = ["All", "(None)"] + parents
        self.parent_kind_combo["values"] = PARENT_KIND_OPTIONS
        self.assignee_combo["values"] = ["All"] + assignees
        self.sprint_combo["values"] = ["All", "(None)"] + sprints
        self.quick_preset_combo["values"] = QUICK_PRESET_OPTIONS

        self.issue_type_var.set("All")
        self.status_var.set("All")
        self.status_category_var.set("All")
        self.parent_var.set("All")
        self.parent_kind_var.set("All")
        self.assignee_var.set("All")
        self.sprint_var.set("All")
        self.quick_preset_var.set("None")
        self.exclude_done_var.set(False)
        self.only_active_var.set(False)
        self.only_unassigned_var.set(False)
        self.no_sprint_only_var.set(False)
        self.empty_description_only_var.set(False)
        self.missing_story_points_only_var.set(False)
        self.missing_dev_story_points_only_var.set(False)
        self.missing_test_story_points_only_var.set(False)
        self.missing_parent_only_var.set(False)
        self.estimate_mismatch_only_var.set(False)
        self.exclude_epics_features_var.set(False)
        self.only_stories_var.set(False)
        self.only_bugs_var.set(False)
        self.only_tasks_subtasks_var.set(False)
        self.backlog_only_var.set(False)
        self.critical_only_var.set(False)
        self.stale_not_done_only_var.set(False)
        self.recently_updated_only_var.set(False)
        self.created_recently_only_var.set(False)
        self.multi_sprint_only_var.set(False)
        self.report_var.set(self.report_var.get() if self.report_var.get() in REPORTS else REPORT_FILTERED)

    def reset_filters(self) -> None:
        if not self.dataset:
            self._show_placeholder()
            self.summary_var.set("Load a Jira CSV export to begin.")
            self.status_var_text.set("Ready")
            return

        self.report_var.set(REPORT_FILTERED)
        self.issue_type_var.set("All")
        self.status_var.set("All")
        self.status_category_var.set("All")
        self.parent_var.set("All")
        self.parent_kind_var.set("All")
        self.assignee_var.set("All")
        self.sprint_var.set("All")
        self.search_var.set("")
        self.quick_preset_var.set("None")
        self.exclude_done_var.set(False)
        self.only_active_var.set(False)
        self.only_unassigned_var.set(False)
        self.no_sprint_only_var.set(False)
        self.empty_description_only_var.set(False)
        self.missing_story_points_only_var.set(False)
        self.missing_dev_story_points_only_var.set(False)
        self.missing_test_story_points_only_var.set(False)
        self.missing_parent_only_var.set(False)
        self.estimate_mismatch_only_var.set(False)
        self.exclude_epics_features_var.set(False)
        self.only_stories_var.set(False)
        self.only_bugs_var.set(False)
        self.only_tasks_subtasks_var.set(False)
        self.backlog_only_var.set(False)
        self.critical_only_var.set(False)
        self.stale_not_done_only_var.set(False)
        self.recently_updated_only_var.set(False)
        self.created_recently_only_var.set(False)
        self.multi_sprint_only_var.set(False)
        self.summary_var.set("Filters reset to defaults.")
        self.refresh_report()

    def refresh_report(self) -> None:
        if not self.dataset:
            self._show_placeholder()
            return

        filtered = self.analyzer.filter_issues(
            self.dataset,
            self.issue_type_var.get(),
            self.status_var.get(),
            self.status_category_var.get(),
            self.parent_var.get(),
            self.parent_kind_var.get(),
            self.assignee_var.get(),
            self.sprint_var.get(),
            self.search_var.get(),
            self.quick_preset_var.get(),
            self.exclude_done_var.get(),
            self.only_active_var.get(),
            self.only_unassigned_var.get(),
            self.no_sprint_only_var.get(),
            self.empty_description_only_var.get(),
            self.missing_story_points_only_var.get(),
            self.missing_dev_story_points_only_var.get(),
            self.missing_test_story_points_only_var.get(),
            self.missing_parent_only_var.get(),
            self.estimate_mismatch_only_var.get(),
            self.exclude_epics_features_var.get(),
            self.only_stories_var.get(),
            self.only_bugs_var.get(),
            self.only_tasks_subtasks_var.get(),
            self.backlog_only_var.get(),
            self.critical_only_var.get(),
            self.stale_not_done_only_var.get(),
            self.recently_updated_only_var.get(),
            self.created_recently_only_var.get(),
            self.multi_sprint_only_var.get(),
        )
        if self.report_var.get() == REPORT_EPIC_BREAKDOWN:
            groups, orphans, summary = self.analyzer.report_epic_breakdown(self.dataset, filtered)
            self.summary_var.set(summary)
            self.status_var_text.set(f"Active report: {self.report_var.get()} | Filtered issues: {len(filtered)}")
            self._render_epic_tree(groups, orphans)
            return

        columns, rows, summary = self.analyzer.build_report(self.dataset, self.report_var.get(), filtered)
        self.current_columns = columns
        self.current_rows = rows
        self.summary_var.set(summary)
        self.status_var_text.set(f"Active report: {self.report_var.get()} | Filtered issues: {len(filtered)}")
        self._render_table(columns, rows)

    def _show_placeholder(self) -> None:
        self.current_columns = ["Message"]
        self.current_rows = [["Load a Jira CSV export to view reports."]]
        self._render_table(self.current_columns, self.current_rows)

    def _render_table(self, columns: list[str], rows: list[list[str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=columns, show="headings")

        for column in columns:
            self.tree.heading(column, text=column)
            width = 140
            if column in {"Summary", "Parent Summary", "Sprint"}:
                width = 320
            elif column in {"Issue Key", "Type", "Status", "Assignee", "Parent Key", "Parent Kind", "Parent Type"}:
                width = 140
            self.tree.column(column, width=width, minwidth=110, stretch=True)

        for row in rows:
            self.tree.insert("", "end", values=row)

    def _render_epic_tree(
        self,
        groups: list[tuple[dict[str, object], list[dict[str, object]]]],
        orphans: list[dict[str, object]],
    ) -> None:
        columns = ["Type", "Status", "Assignee", "Sprint", "Estimate", "Children"]
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=columns, show="tree headings")

        col_widths = {
            "Type": 110,
            "Status": 120,
            "Assignee": 140,
            "Sprint": 200,
            "Estimate": 90,
            "Children": 80,
        }
        self.tree.heading("#0", text="Epic / Story")
        self.tree.column("#0", width=520, minwidth=260, stretch=True)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 120), minwidth=70, stretch=False)

        flat_columns = ["Epic Key", "Epic Summary", "Issue Key", "Summary", "Type", "Status", "Assignee", "Sprint", "Estimate"]
        flat_rows: list[list[str]] = []

        for epic, children in groups:
            children_with_est = [c for c in children if c["effective_estimate"] is not None]
            total_est_val: float | None = float(sum(float(c["effective_estimate"]) for c in children_with_est)) if children_with_est else None
            epic_row = [
                str(epic["issue_type"]),
                str(epic["status"]),
                str(epic["assignee"]),
                "",
                format_points(total_est_val),
                str(len(children)),
            ]
            parent_id = self.tree.insert(
                "",
                "end",
                text=f"{epic['issue_key']} - {epic['summary']}",
                values=epic_row,
                open=True,
            )
            for child in children:
                child_row = [
                    str(child["issue_type"]),
                    str(child["status"]),
                    str(child["assignee"]),
                    str(child["sprint_display"]),
                    format_points(child["effective_estimate"]),
                    "",
                ]
                self.tree.insert(
                    parent_id,
                    "end",
                    text=f"{child['issue_key']} - {child['summary']}",
                    values=child_row,
                )
                flat_rows.append([
                    str(epic["issue_key"]),
                    str(epic["summary"]),
                    str(child["issue_key"]),
                    str(child["summary"]),
                    str(child["issue_type"]),
                    str(child["status"]),
                    str(child["assignee"]),
                    str(child["sprint_display"]),
                    format_points(child["effective_estimate"]),
                ])

        if orphans:
            orphan_id = self.tree.insert(
                "",
                "end",
                text="(No Epic)",
                values=["", "", "", "", "", str(len(orphans))],
                open=False,
            )
            for child in orphans:
                child_row = [
                    str(child["issue_type"]),
                    str(child["status"]),
                    str(child["assignee"]),
                    str(child["sprint_display"]),
                    format_points(child["effective_estimate"]),
                    "",
                ]
                self.tree.insert(
                    orphan_id,
                    "end",
                    text=f"{child['issue_key']} - {child['summary']}",
                    values=child_row,
                )
                flat_rows.append([
                    "",
                    "",
                    str(child["issue_key"]),
                    str(child["summary"]),
                    str(child["issue_type"]),
                    str(child["status"]),
                    str(child["assignee"]),
                    str(child["sprint_display"]),
                    format_points(child["effective_estimate"]),
                ])

        self.current_columns = flat_columns
        self.current_rows = flat_rows

    def export_report(self) -> None:
        if not self.current_columns or not self.current_rows:
            messagebox.showinfo("Nothing To Export", "There is no active report to export yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Report As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.current_columns)
            writer.writerows(self.current_rows)
        self.status_var_text.set(f"Exported report to {path}")

    def export_cleaned_csv(self) -> None:
        if not self.dataset:
            messagebox.showinfo("Nothing To Export", "Load a CSV file first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Cleaned CSV As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"{self.dataset.path.stem}.cleaned.csv",
        )
        if not path:
            return

        cleaned_rows = self.analyzer.cleaned_csv_rows(self.dataset)
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(cleaned_rows)
        kept = len(cleaned_rows[0]) if cleaned_rows else 0
        removed = len(self.dataset.original_headers) - kept
        self.status_var_text.set(f"Exported cleaned CSV to {path} | Removed {removed} empty columns")


def main() -> None:
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.1)
    except tk.TclError:
        pass
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = JiraAnalyzerApp(root)
    app._show_placeholder()
    root.mainloop()


if __name__ == "__main__":
    main()