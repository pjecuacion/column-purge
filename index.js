const REPORT_FILTERED = "Filtered Issues";
const REPORT_MAPPING = "Story To Parent Mapping";
const REPORT_MISSING_POINTS = "Missing Story Points";
const REPORT_MISSING_PARENT = "Missing Parent";
const REPORT_SPRINT_SUMMARY = "Sprint Summary";
const REPORT_ASSIGNEE = "Assignee Workload";
const REPORT_EPIC_BREAKDOWN = "Epic Breakdown";

const REPORTS = [
  REPORT_FILTERED,
  REPORT_MAPPING,
  REPORT_MISSING_POINTS,
  REPORT_MISSING_PARENT,
  REPORT_SPRINT_SUMMARY,
  REPORT_ASSIGNEE,
  REPORT_EPIC_BREAKDOWN,
];

const WORK_ITEM_TYPES = new Set(["story", "bug", "task", "sub-task", "subtask"]);
const PARENT_CONTAINER_TYPES = new Set(["epic", "feature", "initiative"]);
const PARENT_KIND_OPTIONS = ["All", "Epic", "Feature", "Other Matched Parent", "Unmatched Parent Key", "No Parent Key"];
const QUICK_PRESET_OPTIONS = ["None", "Active Delivery", "Planning Gaps", "Needs Triage", "Ready For Grooming"];
const RECENT_DAYS = 7;
const STALE_DAYS = 14;

const CHECKBOXES = [
  ["exclude-done", "Exclude done"],
  ["only-active", "Only active"],
  ["only-unassigned", "Only unassigned"],
  ["no-sprint-only", "No sprint"],
  ["empty-description-only", "Empty description"],
  ["missing-story-points-only", "Missing story points"],
  ["missing-dev-story-points-only", "Missing dev points"],
  ["missing-test-story-points-only", "Missing test points"],
  ["missing-parent-only", "Missing parent"],
  ["estimate-mismatch-only", "Estimate mismatch"],
  ["exclude-epics-features", "Exclude epics/\nfeatures"],
  ["only-stories", "Only stories"],
  ["only-bugs", "Only bugs"],
  ["only-tasks-subtasks", "Only tasks/sub-tasks"],
  ["backlog-only", "Backlog only"],
  ["critical-only", "Critical / blocker"],
  ["stale-not-done-only", `Stale not done (${STALE_DAYS}d+)`],
  ["recently-updated-only", `Recently updated (${RECENT_DAYS}d)`],
  ["created-recently-only", `Created recently (${RECENT_DAYS}d)`],
  ["multi-sprint-only", "Multi-sprint"],
];

const state = {
  dataset: null,
  currentColumns: [],
  currentRows: [],
  treeAllExpanded: true,
  stem: "jira-report",
};

const $ = (id) => document.getElementById(id);

const refs = {
  file: $("file-input"),
  sample: $("sample-btn"),
  drop: $("dropzone"),
  fileName: $("file-name"),
  summary: $("summary"),
  status: $("status"),
  error: $("error"),
  rows: $("rows-stat"),
  cols: $("cols-stat"),
  issues: $("issues-stat"),
  filtered: $("filtered-stat"),
  exportReport: $("export-report"),
  exportCleaned: $("export-cleaned"),
  reset: $("reset"),
  report: $("report"),
  preset: $("preset"),
  search: $("search"),
  issueType: $("issue-type"),
  issueStatus: $("issue-status"),
  statusCategory: $("status-category"),
  parentKey: $("parent-key"),
  parentKind: $("parent-kind"),
  assignee: $("assignee"),
  sprint: $("sprint"),
  checks: $("checks"),
  resultTitle: $("result-title"),
  resultMeta: $("result-meta"),
  results: $("results"),
  toggleEpics: $("toggle-epics"),
};

init();

function init() {
  CHECKBOXES.forEach(([id, label]) => {
    refs.checks.insertAdjacentHTML(
      "beforeend",
      `<label class="check" for="${id}"><input type="checkbox" id="${id}"><span>${esc(label)}</span></label>`
    );
  });

  fillSelect(refs.report, REPORTS, REPORT_FILTERED);
  fillSelect(refs.preset, QUICK_PRESET_OPTIONS, "None");
  [refs.issueType, refs.issueStatus, refs.statusCategory, refs.parentKey, refs.assignee, refs.sprint].forEach((el) =>
    fillSelect(el, ["All"], "All")
  );
  fillSelect(refs.parentKind, PARENT_KIND_OPTIONS, "All");

  refs.file.addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (file) {
      await loadFile(file);
    }
  });

  refs.sample.addEventListener("click", async () => {
    clearError();
    refs.status.textContent = "Loading demo CSV...";
    try {
      const response = await fetch("sample-jira.csv", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Could not load the demo CSV.");
      }
      loadText(await response.text(), "sample-jira.csv");
    } catch (error) {
      showError(error.message || "Could not load the demo CSV.");
      refs.status.textContent = "Demo load failed";
    }
  });

  [
    refs.report,
    refs.preset,
    refs.issueType,
    refs.issueStatus,
    refs.statusCategory,
    refs.parentKey,
    refs.parentKind,
    refs.assignee,
    refs.sprint,
  ].forEach((el) => el.addEventListener("change", refresh));

  refs.search.addEventListener("input", refresh);
  CHECKBOXES.forEach(([id]) => $(id).addEventListener("change", refresh));
  refs.exportReport.addEventListener("click", exportReport);
  refs.exportCleaned.addEventListener("click", exportCleaned);
  refs.reset.addEventListener("click", resetFilters);
  refs.toggleEpics.addEventListener("click", toggleEpicGroups);

  ["dragenter", "dragover"].forEach((eventName) =>
    refs.drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      refs.drop.classList.add("drag");
    })
  );
  ["dragleave", "dragend", "drop"].forEach((eventName) =>
    refs.drop.addEventListener(eventName, () => refs.drop.classList.remove("drag"))
  );
  refs.drop.addEventListener("drop", async (event) => {
    event.preventDefault();
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
    if (file) {
      await loadFile(file);
    }
  });
}

function loadText(text, name) {
  const dataset = loadCsvDataset(text);
  state.dataset = dataset;
  state.stem = name.replace(/\.[^.]+$/, "") || "jira-report";
  refs.fileName.textContent = name;
  refs.summary.textContent = "Normalized duplicate Jira headers and prepared report views.";
  refs.status.textContent = `Loaded ${name}`;
  refs.rows.textContent = String(dataset.rawRows.length);
  refs.cols.textContent = String(dataset.originalHeaders.length);
  refs.issues.textContent = String(dataset.issues.length);
  populateDatasetFilters(dataset);
  [refs.exportReport, refs.exportCleaned, refs.reset].forEach((button) => {
    button.disabled = false;
  });
  refresh();
}

function loadCsvDataset(text) {
  const parsed = parseCsv(text);
  if (!parsed.length) {
    throw new Error("The selected CSV file is empty.");
  }

  const header = parsed[0];
  const rawRows = parsed.slice(1).map((row) => padRow(row, header.length));
  const unique = uniqueHeaders(header);
  const groups = {};

  header.forEach((original, index) => {
    const key = (original || "").trim() || "Unnamed";
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(unique[index]);
  });

  const rows = [];
  const issues = [];
  rawRows.forEach((raw) => {
    const row = {};
    unique.forEach((headerName, index) => {
      row[headerName] = raw[index] || "";
    });
    rows.push(row);
    issues.push(normalizeIssue(row, groups));
  });

  const lookup = {};
  issues.forEach((issue) => {
    if (issue.issue_key) {
      lookup[issue.issue_key] = issue;
    }
  });

  issues.forEach((issue) => {
    const parent = lookup[String(issue.parent_key || "")];
    issue.parent_found = Boolean(parent);
    issue.parent_type = parent ? String(parent.issue_type || "") : "";
    issue.parent_kind = parentKindForIssue(issue, lookup);
  });

  return { originalHeaders: header, uniqueHeaders: unique, rows, rawRows, groups, issues, issueLookup: lookup };
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (inQuotes) {
      if (char === "\"") {
        if (text[index + 1] === "\"") {
          field += "\"";
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }

    if (char === "\"") {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char === "\r") {
      if (text[index + 1] === "\n") {
        index += 1;
      }
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }

  return rows.filter((currentRow, index) => index === 0 || currentRow.length > 1 || (currentRow[0] || "").length > 0);
}

function padRow(row, width) {
  return row.length >= width ? row.slice(0, width) : row.concat(Array(width - row.length).fill(""));
}

function uniqueHeaders(headers) {
  const counts = new Map();
  return headers.map((header) => {
    const name = (header || "").trim() || "Unnamed";
    const next = (counts.get(name) || 0) + 1;
    counts.set(name, next);
    return next === 1 ? name : `${name}__${next}`;
  });
}

function firstNonEmpty(values) {
  for (const value of values) {
    const cleaned = String(value || "").trim();
    if (cleaned) {
      return cleaned;
    }
  }
  return "";
}

function distinctNonEmpty(values) {
  const seen = new Set();
  const result = [];
  values.forEach((value) => {
    const cleaned = String(value || "").trim();
    if (cleaned && !seen.has(cleaned)) {
      seen.add(cleaned);
      result.push(cleaned);
    }
  });
  return result;
}

function parsePoints(raw) {
  const cleaned = String(raw || "").trim();
  if (!cleaned) {
    return null;
  }
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

function formatPoints(value) {
  if (value == null || Number.isNaN(value)) {
    return "";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function normalizeStatusBucket(statusCategory) {
  const cleaned = String(statusCategory || "").trim().toLowerCase();
  if (cleaned === "done") {
    return "done";
  }
  if (cleaned === "in progress" || cleaned === "indeterminate") {
    return "in_progress";
  }
  return "todo";
}

function parseJiraDatetime(raw) {
  const cleaned = String(raw || "").trim();
  if (!cleaned) {
    return null;
  }

  let match = cleaned.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4}) (\d{1,2}):(\d{2})$/);
  if (match) {
    return new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]), Number(match[4]), Number(match[5]));
  }

  const months = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };
  match = cleaned.match(/^(\d{1,2})\/([A-Za-z]{3})\/(\d{4}) (\d{1,2}):(\d{2}) ([AP]M)$/);
  if (!match) {
    return null;
  }

  let hour = Number(match[4]);
  if (match[6] === "PM" && hour !== 12) {
    hour += 12;
  }
  if (match[6] === "AM" && hour === 12) {
    hour = 0;
  }

  const month = months[match[2].toLowerCase()];
  return month == null ? null : new Date(Number(match[3]), month, Number(match[1]), hour, Number(match[5]));
}

function daysBetween(fromDate, toDate) {
  return Math.floor((toDate.getTime() - fromDate.getTime()) / 86400000);
}

function normalizeIssue(row, groups) {
  const values = (label) => (groups[label] || []).map((name) => row[name] || "");
  const issue_key = firstNonEmpty(values("Issue key"));
  const story_points_raw = firstNonEmpty(values("Custom field (Story Points)"));
  const dev_story_points_raw = firstNonEmpty(values("Custom field (Dev Story points)"));
  const test_story_points_raw = firstNonEmpty(values("Custom field (Test Story Points)"));
  const story_points = parsePoints(story_points_raw);
  const dev_story_points = parsePoints(dev_story_points_raw);
  const test_story_points = parsePoints(test_story_points_raw);
  let effective_estimate = story_points;
  let estimate_source = story_points !== null ? "Story Points" : "";
  if (effective_estimate === null && dev_story_points !== null) {
    effective_estimate = dev_story_points;
    estimate_source = "Dev Story Points";
  }
  if (effective_estimate === null && test_story_points !== null) {
    effective_estimate = test_story_points;
    estimate_source = "Test Story Points";
  }

  const sprints = distinctNonEmpty(values("Sprint"));
  const description = firstNonEmpty(values("Description"));
  const created = firstNonEmpty(values("Created"));
  const updated = firstNonEmpty(values("Updated"));
  const created_at = parseJiraDatetime(created);
  const updated_at = parseJiraDatetime(updated);
  const now = new Date();
  const issue_type = firstNonEmpty(values("Issue Type"));
  const issue_type_lower = issue_type.trim().toLowerCase();
  const status = firstNonEmpty(values("Status"));
  const status_category = firstNonEmpty(values("Status Category"));
  const status_bucket = normalizeStatusBucket(status_category);
  const assignee = firstNonEmpty(values("Assignee")) || "Unassigned";
  const priority = firstNonEmpty(values("Priority"));
  const severity = firstNonEmpty(values("Custom field (Severity)"));
  const points = [story_points, dev_story_points, test_story_points].filter((value) => value !== null);
  const distinctPoints = new Set(points.map((value) => Number(value)));

  return {
    issue_key,
    summary: firstNonEmpty(values("Summary")),
    description,
    description_empty: !description,
    issue_type,
    status,
    status_category,
    status_bucket,
    assignee,
    reporter: firstNonEmpty(values("Reporter")),
    parent_key: firstNonEmpty(values("Parent key")),
    parent_summary: firstNonEmpty(values("Parent summary")),
    project_key: firstNonEmpty(values("Project key")),
    created,
    updated,
    created_at,
    updated_at,
    priority,
    severity,
    story_points_raw,
    dev_story_points_raw,
    test_story_points_raw,
    story_points,
    dev_story_points,
    test_story_points,
    effective_estimate,
    estimate_source,
    sprints,
    sprint_display: sprints.join(", "),
    parent_found: false,
    parent_type: "",
    parent_kind: "No Parent Key",
    missing_story_points: !story_points_raw.trim(),
    missing_dev_story_points: !dev_story_points_raw.trim(),
    missing_test_story_points: !test_story_points_raw.trim(),
    estimate_mismatch: distinctPoints.size >= 2,
    is_unassigned: assignee === "Unassigned",
    no_sprint: sprints.length === 0,
    multi_sprint: sprints.length > 1,
    is_container: PARENT_CONTAINER_TYPES.has(issue_type_lower),
    is_story: issue_type_lower === "story",
    is_bug: issue_type_lower === "bug",
    is_task_like: issue_type_lower === "task" || issue_type_lower === "sub-task" || issue_type_lower === "subtask",
    is_done: status_bucket === "done",
    is_active: status_bucket !== "done",
    is_backlog: status.trim().toLowerCase() === "backlog",
    is_critical_or_blocker: priority.trim().toLowerCase() === "blocker" || severity.trim().toLowerCase() === "critical",
    recently_updated: Boolean(updated_at && daysBetween(updated_at, now) <= RECENT_DAYS),
    created_recently: Boolean(created_at && daysBetween(created_at, now) <= RECENT_DAYS),
    stale_not_done: Boolean(updated_at && status_bucket !== "done" && daysBetween(updated_at, now) >= STALE_DAYS),
  };
}

function parentKindForIssue(issue, lookup) {
  const key = String(issue.parent_key || "");
  if (!key) {
    return "No Parent Key";
  }
  const parent = lookup[key];
  if (!parent) {
    return "Unmatched Parent Key";
  }
  const type = String(parent.issue_type || "").trim().toLowerCase();
  if (type === "epic") {
    return "Epic";
  }
  if (type === "feature") {
    return "Feature";
  }
  return "Other Matched Parent";
}

function matchesPreset(issue, preset) {
  if (preset === "None") {
    return true;
  }
  if (preset === "Active Delivery") {
    return Boolean(issue.is_active);
  }
  if (preset === "Planning Gaps") {
    return Boolean(
      issue.is_active &&
        (issue.missing_story_points ||
          issue.missing_dev_story_points ||
          issue.missing_test_story_points ||
          issue.description_empty ||
          issue.parent_kind === "No Parent Key" ||
          issue.parent_kind === "Unmatched Parent Key")
    );
  }
  if (preset === "Needs Triage") {
    return Boolean(
      issue.is_active &&
        (issue.is_unassigned ||
          issue.is_critical_or_blocker ||
          issue.parent_kind === "Unmatched Parent Key" ||
          issue.description_empty)
    );
  }
  if (preset === "Ready For Grooming") {
    return Boolean(
      issue.is_active &&
        !issue.is_container &&
        issue.status_bucket === "todo" &&
        (issue.missing_story_points ||
          issue.description_empty ||
          issue.parent_kind === "No Parent Key" ||
          issue.parent_kind === "Unmatched Parent Key")
    );
  }
  return true;
}

function populateDatasetFilters(dataset) {
  const issues = dataset.issues;
  const uniq = (key) =>
    Array.from(new Set(issues.map((issue) => String(issue[key] || "")).filter(Boolean))).sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" })
    );

  const sprints = new Set();
  issues.forEach((issue) => issue.sprints.forEach((sprint) => sprints.add(String(sprint))));

  fillSelect(refs.issueType, ["All", ...uniq("issue_type")], "All");
  fillSelect(refs.issueStatus, ["All", ...uniq("status")], "All");
  fillSelect(refs.statusCategory, ["All", ...uniq("status_category")], "All");
  fillSelect(refs.parentKey, ["All", "(None)", ...uniq("parent_key")], "All");
  fillSelect(refs.parentKind, PARENT_KIND_OPTIONS, "All");
  fillSelect(refs.assignee, ["All", ...uniq("assignee")], "All");
  fillSelect(
    refs.sprint,
    ["All", "(None)", ...Array.from(sprints).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))],
    "All"
  );

  refs.report.value = REPORTS.includes(refs.report.value) ? refs.report.value : REPORT_FILTERED;
  refs.preset.value = "None";
  refs.search.value = "";
  CHECKBOXES.forEach(([id]) => {
    $(id).checked = false;
  });
}

function fillSelect(element, values, selected) {
  element.innerHTML = values.map((value) => `<option value="${attr(value)}">${esc(value)}</option>`).join("");
  element.value = values.includes(selected) ? selected : values[0];
}

function currentFilters() {
  return {
    report: refs.report.value,
    preset: refs.preset.value,
    search: refs.search.value,
    issueType: refs.issueType.value,
    status: refs.issueStatus.value,
    statusCategory: refs.statusCategory.value,
    parentKey: refs.parentKey.value,
    parentKind: refs.parentKind.value,
    assignee: refs.assignee.value,
    sprint: refs.sprint.value,
    excludeDone: $("exclude-done").checked,
    onlyActive: $("only-active").checked,
    onlyUnassigned: $("only-unassigned").checked,
    noSprintOnly: $("no-sprint-only").checked,
    emptyDescriptionOnly: $("empty-description-only").checked,
    missingStoryPointsOnly: $("missing-story-points-only").checked,
    missingDevStoryPointsOnly: $("missing-dev-story-points-only").checked,
    missingTestStoryPointsOnly: $("missing-test-story-points-only").checked,
    missingParentOnly: $("missing-parent-only").checked,
    estimateMismatchOnly: $("estimate-mismatch-only").checked,
    excludeEpicsFeatures: $("exclude-epics-features").checked,
    onlyStories: $("only-stories").checked,
    onlyBugs: $("only-bugs").checked,
    onlyTasksSubtasks: $("only-tasks-subtasks").checked,
    backlogOnly: $("backlog-only").checked,
    criticalOnly: $("critical-only").checked,
    staleNotDoneOnly: $("stale-not-done-only").checked,
    recentlyUpdatedOnly: $("recently-updated-only").checked,
    createdRecentlyOnly: $("created-recently-only").checked,
    multiSprintOnly: $("multi-sprint-only").checked,
  };
}

function resetFilters() {
  if (!state.dataset) {
    showPlaceholder();
    refs.summary.textContent = "Load a Jira CSV export to begin.";
    refs.status.textContent = "Ready";
    return;
  }

  refs.report.value = REPORT_FILTERED;
  refs.preset.value = "None";
  refs.search.value = "";
  refs.issueType.value = "All";
  refs.issueStatus.value = "All";
  refs.statusCategory.value = "All";
  refs.parentKey.value = "All";
  refs.parentKind.value = "All";
  refs.assignee.value = "All";
  refs.sprint.value = "All";
  CHECKBOXES.forEach(([id]) => {
    $(id).checked = false;
  });
  refs.summary.textContent = "Filters reset to defaults.";
  refresh();
}

function refresh() {
  if (!state.dataset) {
    showPlaceholder();
    return;
  }

  clearError();
  const filters = currentFilters();
  const filtered = filterIssues(state.dataset, filters);
  refs.filtered.textContent = String(filtered.length);
  refs.resultTitle.textContent = filters.report;
  refs.resultMeta.textContent = `Filtered issues: ${filtered.length}`;
  refs.status.textContent = `Active report: ${filters.report} | Filtered issues: ${filtered.length}`;

  if (filters.report === REPORT_EPIC_BREAKDOWN) {
    const report = reportEpicBreakdown(state.dataset, filtered);
    state.currentColumns = report.columns;
    state.currentRows = report.rows;
    refs.summary.textContent = report.summary;
    renderEpicBreakdown(report.groups, report.orphans);
    setEpicToggle(true);
    return;
  }

  const report = buildReport(state.dataset, filters.report, filtered);
  state.currentColumns = report.columns;
  state.currentRows = report.rows;
  refs.summary.textContent = report.summary;
  renderTable(report.columns, report.rows);
  setEpicToggle(false);
}

function filterIssues(dataset, filters) {
  const needle = filters.search.trim().toLowerCase();

  return dataset.issues.filter((issue) => {
    if (filters.preset !== "None" && !matchesPreset(issue, filters.preset)) return false;
    if (filters.issueType !== "All" && issue.issue_type !== filters.issueType) return false;
    if (filters.status !== "All" && issue.status !== filters.status) return false;
    if (filters.statusCategory !== "All" && issue.status_category !== filters.statusCategory) return false;
    if (filters.parentKey !== "All") {
      const expected = filters.parentKey === "(None)" ? "" : filters.parentKey;
      if (issue.parent_key !== expected) return false;
    }
    if (filters.parentKind !== "All" && issue.parent_kind !== filters.parentKind) return false;
    if (filters.assignee !== "All" && issue.assignee !== filters.assignee) return false;
    if (filters.sprint !== "All") {
      if (filters.sprint === "(None)") {
        if (issue.sprints.length) return false;
      } else if (!issue.sprints.includes(filters.sprint)) {
        return false;
      }
    }
    if (needle) {
      const haystack = [issue.issue_key, issue.summary, issue.parent_key, issue.parent_summary, issue.assignee].join(" ").toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    if (filters.excludeDone && issue.is_done) return false;
    if (filters.onlyActive && !issue.is_active) return false;
    if (filters.onlyUnassigned && !issue.is_unassigned) return false;
    if (filters.noSprintOnly && !issue.no_sprint) return false;
    if (filters.emptyDescriptionOnly && !issue.description_empty) return false;
    if (filters.missingStoryPointsOnly && !issue.missing_story_points) return false;
    if (filters.missingDevStoryPointsOnly && !issue.missing_dev_story_points) return false;
    if (filters.missingTestStoryPointsOnly && !issue.missing_test_story_points) return false;
    if (filters.missingParentOnly && issue.parent_kind !== "No Parent Key" && issue.parent_kind !== "Unmatched Parent Key") return false;
    if (filters.estimateMismatchOnly && !issue.estimate_mismatch) return false;
    if (filters.excludeEpicsFeatures && issue.is_container) return false;
    if (filters.onlyStories && !issue.is_story) return false;
    if (filters.onlyBugs && !issue.is_bug) return false;
    if (filters.onlyTasksSubtasks && !issue.is_task_like) return false;
    if (filters.backlogOnly && !issue.is_backlog) return false;
    if (filters.criticalOnly && !issue.is_critical_or_blocker) return false;
    if (filters.staleNotDoneOnly && !issue.stale_not_done) return false;
    if (filters.recentlyUpdatedOnly && !issue.recently_updated) return false;
    if (filters.createdRecentlyOnly && !issue.created_recently) return false;
    if (filters.multiSprintOnly && !issue.multi_sprint) return false;
    return true;
  });
}

function buildReport(dataset, reportName, issues) {
  if (reportName === REPORT_MAPPING) return reportMapping(dataset, issues);
  if (reportName === REPORT_MISSING_POINTS) return reportMissingStoryPoints(issues);
  if (reportName === REPORT_MISSING_PARENT) return reportMissingParent(dataset, issues);
  if (reportName === REPORT_SPRINT_SUMMARY) return reportSprintSummary(issues);
  if (reportName === REPORT_ASSIGNEE) return reportAssigneeWorkload(issues);
  return reportFiltered(issues);
}

function reportFiltered(issues) {
  const columns = ["Issue Key", "Summary", "Type", "Status", "Status Category", "Assignee", "Parent Key", "Parent Kind", "Parent Summary", "Sprint", "Story Points", "Dev Story Points", "Test Story Points", "Estimate", "Estimate Source", "Description Empty"];
  const rows = issues.map((issue) => [
    issue.issue_key,
    issue.summary,
    issue.issue_type,
    issue.status,
    issue.status_category,
    issue.assignee,
    issue.parent_key,
    issue.parent_kind,
    issue.parent_summary,
    issue.sprint_display,
    issue.story_points_raw,
    issue.dev_story_points_raw,
    issue.test_story_points_raw,
    formatPoints(issue.effective_estimate),
    issue.estimate_source,
    issue.description_empty ? "Yes" : "No",
  ]);
  return { columns, rows, summary: `Showing ${rows.length} issue rows after filters.` };
}

function reportMapping(dataset, issues) {
  const columns = ["Issue Key", "Summary", "Type", "Status", "Parent Key", "Parent Summary", "Parent Found", "Parent Type", "Parent Kind", "Story Points", "Dev Story Points", "Test Story Points", "Estimate", "Estimate Source"];
  let orphanCount = 0;
  const rows = issues.map((issue) => {
    const key = String(issue.parent_key || "");
    const parent = dataset.issueLookup[key];
    if (!key || !parent) orphanCount += 1;
    return [
      issue.issue_key,
      issue.summary,
      issue.issue_type,
      issue.status,
      key,
      issue.parent_summary,
      parent ? "Yes" : "No",
      parent ? String(parent.issue_type || "") : "",
      issue.parent_kind,
      issue.story_points_raw,
      issue.dev_story_points_raw,
      issue.test_story_points_raw,
      formatPoints(issue.effective_estimate),
      issue.estimate_source,
    ];
  });
  return { columns, rows, summary: `Mapped ${rows.length} issues. ${orphanCount} rows are missing a matched parent.` };
}

function reportMissingStoryPoints(issues) {
  const columns = ["Issue Key", "Summary", "Type", "Status", "Assignee", "Parent Key", "Sprint", "Parent Kind", "Story Points", "Dev Story Points", "Test Story Points", "Description Empty"];
  const rows = [];
  issues.forEach((issue) => {
    const type = String(issue.issue_type || "").trim().toLowerCase();
    if (PARENT_CONTAINER_TYPES.has(type) || type === "epic" || String(issue.story_points_raw || "").trim()) return;
    rows.push([
      issue.issue_key,
      issue.summary,
      issue.issue_type,
      issue.status,
      issue.assignee,
      issue.parent_key,
      issue.sprint_display,
      issue.parent_kind,
      issue.story_points_raw,
      issue.dev_story_points_raw,
      issue.test_story_points_raw,
      issue.description_empty ? "Yes" : "No",
    ]);
  });
  return { columns, rows, summary: `Found ${rows.length} issues without Story Points.` };
}

function reportMissingParent(dataset, issues) {
  const columns = ["Issue Key", "Summary", "Type", "Status", "Assignee", "Parent Key", "Parent Summary", "Parent Kind", "Parent Type", "Parent Status", "Description Empty"];
  const rows = [];
  issues.forEach((issue) => {
    const type = String(issue.issue_type || "").trim().toLowerCase();
    if (PARENT_CONTAINER_TYPES.has(type) || !WORK_ITEM_TYPES.has(type)) return;
    const key = String(issue.parent_key || "");
    const parent = dataset.issueLookup[key];
    if (key && parent) return;
    rows.push([
      issue.issue_key,
      issue.summary,
      issue.issue_type,
      issue.status,
      issue.assignee,
      key,
      issue.parent_summary,
      issue.parent_kind,
      issue.parent_type,
      parent ? String(parent.status || "") : "",
      issue.description_empty ? "Yes" : "No",
    ]);
  });
  return { columns, rows, summary: `Found ${rows.length} work items without a matched parent.` };
}

function reportSprintSummary(issues) {
  const columns = ["Sprint", "Issue Count", "Total Estimate", "To Do", "In Progress", "Done", "Unestimated"];
  const map = new Map();
  issues.forEach((issue) => {
    (issue.sprints.length ? issue.sprints : ["(No Sprint)"]).forEach((sprint) => {
      if (!map.has(sprint)) {
        map.set(sprint, { issue_count: 0, total_estimate: 0, todo: 0, in_progress: 0, done: 0, unestimated: 0 });
      }
      const bucket = map.get(sprint);
      bucket.issue_count += 1;
      if (issue.effective_estimate === null) {
        bucket.unestimated += 1;
      } else {
        bucket.total_estimate += Number(issue.effective_estimate);
      }
      bucket[String(issue.status_bucket)] += 1;
    });
  });
  const rows = Array.from(map.entries())
    .sort((left, right) => left[0].localeCompare(right[0], undefined, { sensitivity: "base" }))
    .map(([sprint, values]) => [
      sprint,
      String(values.issue_count),
      formatPoints(values.total_estimate),
      String(values.todo),
      String(values.in_progress),
      String(values.done),
      String(values.unestimated),
    ]);
  return { columns, rows, summary: `Summarized ${rows.length} sprint buckets from ${issues.length} filtered issues.` };
}

function reportAssigneeWorkload(issues) {
  const columns = ["Assignee", "Issue Count", "Total Estimate", "To Do", "In Progress", "Done", "Unestimated"];
  const map = new Map();
  issues.forEach((issue) => {
    const assignee = String(issue.assignee || "") || "Unassigned";
    if (!map.has(assignee)) {
      map.set(assignee, { issue_count: 0, total_estimate: 0, todo: 0, in_progress: 0, done: 0, unestimated: 0 });
    }
    const bucket = map.get(assignee);
    bucket.issue_count += 1;
    if (issue.effective_estimate === null) {
      bucket.unestimated += 1;
    } else {
      bucket.total_estimate += Number(issue.effective_estimate);
    }
    bucket[String(issue.status_bucket)] += 1;
  });
  const rows = Array.from(map.entries())
    .sort((left, right) => left[0].localeCompare(right[0], undefined, { sensitivity: "base" }))
    .map(([assignee, values]) => [
      assignee,
      String(values.issue_count),
      formatPoints(values.total_estimate),
      String(values.todo),
      String(values.in_progress),
      String(values.done),
      String(values.unestimated),
    ]);
  return { columns, rows, summary: `Summarized workload for ${rows.length} assignees.` };
}

function reportEpicBreakdown(dataset, issues) {
  const byEpic = new Map();
  const orphans = [];

  issues.forEach((issue) => {
    if (issue.is_container) return;
    const key = String(issue.parent_key || "");
    const parent = dataset.issueLookup[key];
    if (parent && parent.is_container) {
      if (!byEpic.has(parent.issue_key)) {
        byEpic.set(parent.issue_key, []);
      }
      byEpic.get(parent.issue_key).push(issue);
    } else {
      orphans.push(issue);
    }
  });

  const childKeys = new Set(byEpic.keys());
  const filteredEpics = new Set(issues.filter((issue) => issue.is_container).map((issue) => String(issue.issue_key)));
  const groups = Array.from(new Set([...childKeys, ...filteredEpics]))
    .sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }))
    .map((key) => (dataset.issueLookup[key] ? { epic: dataset.issueLookup[key], children: byEpic.get(key) || [] } : null))
    .filter(Boolean);

  const childTotal = groups.reduce((sum, group) => sum + group.children.length, 0);
  const summary = `${groups.length} epics | ${childTotal} child issues | ${orphans.length} without matched epic.`;
  const columns = ["Epic Key", "Epic Summary", "Issue Key", "Summary", "Type", "Status", "Assignee", "Sprint", "Estimate"];
  const rows = [];

  groups.forEach((group) => {
    group.children.forEach((child) => {
      rows.push([
        String(group.epic.issue_key || ""),
        String(group.epic.summary || ""),
        String(child.issue_key || ""),
        String(child.summary || ""),
        String(child.issue_type || ""),
        String(child.status || ""),
        String(child.assignee || ""),
        String(child.sprint_display || ""),
        formatPoints(child.effective_estimate),
      ]);
    });
  });

  orphans.forEach((child) => {
    rows.push([
      "",
      "",
      String(child.issue_key || ""),
      String(child.summary || ""),
      String(child.issue_type || ""),
      String(child.status || ""),
      String(child.assignee || ""),
      String(child.sprint_display || ""),
      formatPoints(child.effective_estimate),
    ]);
  });

  return { groups, orphans, summary, columns, rows };
}

async function loadFile(file) {
  clearError();
  if (!file.name.toLowerCase().endsWith(".csv")) {
    showError("Please upload a Jira CSV export.");
    return;
  }
  refs.status.textContent = `Loading ${file.name}...`;
  try {
    loadText(await file.text(), file.name);
  } catch (error) {
    showError(error.message || "Failed to read the selected file.");
    refs.status.textContent = "Load failed";
  }
}

function renderTable(columns, rows) {
  if (!rows.length) {
    refs.results.innerHTML = '<div class="placeholder">No rows match the current filters.</div>';
    return;
  }

  const head = `<thead><tr>${columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead>`;
  const body = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${row
          .map((cell, index) => `<td class="${["Summary", "Parent Summary", "Sprint"].includes(columns[index]) ? "w" : ""}">${esc(cell)}</td>`)
          .join("")}</tr>`
    )
    .join("")}</tbody>`;

  refs.results.innerHTML = `<div class="wrap"><table>${head}${body}</table></div>`;
}

function renderEpicBreakdown(groups, orphans) {
  if (!groups.length && !orphans.length) {
    refs.results.innerHTML = '<div class="placeholder">No epic groups match the current filters.</div>';
    return;
  }

  refs.results.innerHTML = `<div class="groups">${groups.map((group) => groupHtml(group.epic, group.children, false)).join("")}${
    orphans.length
      ? groupHtml(
          { issue_key: "(No Epic)", summary: "Issues without a matched epic", issue_type: "", status: "", assignee: "" },
          orphans,
          true
        )
      : ""
  }</div>`;
}

function groupHtml(epic, children, isOrphans) {
  const estimatedChildren = children.filter((child) => child.effective_estimate !== null);
  const totalEstimate = estimatedChildren.reduce((sum, child) => sum + Number(child.effective_estimate), 0);
  const estimate = isOrphans ? formatPoints(totalEstimate) : formatPoints(estimatedChildren.length ? totalEstimate : null);

  return `<details class="group" ${state.treeAllExpanded ? "open" : ""}>
    <summary>
      <div class="gtitle">${esc(String(epic.issue_key || ""))} - ${esc(String(epic.summary || ""))}</div>
      <div class="metric"><strong>Type</strong><span>${esc(String(epic.issue_type || ""))}</span></div>
      <div class="metric"><strong>Status</strong><span>${esc(String(epic.status || ""))}</span></div>
      <div class="metric"><strong>Assignee</strong><span>${esc(String(epic.assignee || ""))}</span></div>
      <div class="metric"><strong>Estimate</strong><span>${esc(estimate)}</span></div>
      <div class="metric"><strong>Children</strong><span>${children.length}</span></div>
    </summary>
    <div class="body">
      ${
        children.length
          ? `<div class="wrap"><table><thead><tr><th>Issue Key</th><th>Summary</th><th>Type</th><th>Status</th><th>Assignee</th><th>Sprint</th><th>Estimate</th></tr></thead><tbody>${children
              .map(
                (child) =>
                  `<tr><td>${esc(child.issue_key)}</td><td class="w">${esc(child.summary)}</td><td>${esc(child.issue_type)}</td><td>${esc(child.status)}</td><td>${esc(child.assignee)}</td><td class="w">${esc(child.sprint_display)}</td><td>${esc(formatPoints(child.effective_estimate))}</td></tr>`
              )
              .join("")}</tbody></table></div>`
          : '<div class="placeholder" style="padding:24px">No child issues in this group.</div>'
      }
    </div>
  </details>`;
}

function showPlaceholder() {
  refs.resultTitle.textContent = "Active Report";
  refs.resultMeta.textContent = "Load a Jira CSV export to view reports.";
  refs.results.innerHTML = '<div class="placeholder">Load a Jira CSV export to view reports.</div>';
  refs.filtered.textContent = "0";
  setEpicToggle(false);
}

function setEpicToggle(enabled) {
  refs.toggleEpics.disabled = !enabled;
  refs.toggleEpics.textContent = state.treeAllExpanded ? "Collapse All" : "Expand All";
}

function toggleEpicGroups() {
  if (refs.toggleEpics.disabled) {
    return;
  }
  state.treeAllExpanded = !state.treeAllExpanded;
  refs.results.querySelectorAll("details.group").forEach((element) => {
    element.open = state.treeAllExpanded;
  });
  setEpicToggle(true);
}

function cleanedCsvRows(dataset) {
  const keep = [];
  for (let index = 0; index < dataset.originalHeaders.length; index += 1) {
    if (dataset.rawRows.some((row) => index < row.length && String(row[index] || "").trim())) {
      keep.push(index);
    }
  }
  const output = [keep.map((index) => dataset.originalHeaders[index])];
  dataset.rawRows.forEach((row) => {
    output.push(keep.map((index) => row[index] || ""));
  });
  return output;
}

function exportReport() {
  if (!state.currentColumns.length) {
    showError("There is no active report to export yet.");
    return;
  }
  download(rowsToCsv([state.currentColumns, ...state.currentRows]), `${state.stem}.${slug(refs.report.value)}.csv`, "text/csv;charset=utf-8");
  refs.status.textContent = `Exported ${refs.report.value}`;
}

function exportCleaned() {
  if (!state.dataset) {
    showError("Load a CSV file first.");
    return;
  }
  const rows = cleanedCsvRows(state.dataset);
  download(rowsToCsv(rows), `${state.stem}.cleaned.csv`, "text/csv;charset=utf-8");
  const kept = rows.length ? rows[0].length : 0;
  const removed = state.dataset.originalHeaders.length - kept;
  refs.status.textContent = `Exported cleaned CSV | Removed ${removed} empty columns`;
}

function rowsToCsv(rows) {
  return "\ufeff" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
}

function csvCell(value) {
  const text = String(value == null ? "" : value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, "\"\"")}"` : text;
}

function download(text, name, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function slug(text) {
  return String(text || "report").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "report";
}

function showError(message) {
  refs.error.textContent = message;
  refs.error.classList.add("show");
}

function clearError() {
  refs.error.textContent = "";
  refs.error.classList.remove("show");
}

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function attr(value) {
  return esc(value);
}
