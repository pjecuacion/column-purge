# column-purge

Desktop Jira CSV analyzer for exploring epics, stories, estimates, sprint data, and cleanup exports.

The repo also contains an earlier browser prototype for dropping empty CSV/Markdown columns, but the main working app today is the Python Tkinter tool in `app.py`.

## What It Does

- Loads a Jira CSV export, including exports with duplicate column names.
- Normalizes common Jira fields like issue type, parent key, sprint, assignee, story points, and status category.
- Filters issues by type, status, sprint, assignee, parent, quick presets, and several planning-quality checks.
- Provides report views for:
  - Filtered issues
  - Story to parent mapping
  - Missing story points
  - Missing parent
  - Sprint summary
  - Assignee workload
  - Epic breakdown
- Exports the active report as CSV.
- Exports a cleaned CSV with fully empty columns removed.

## Repo Layout

- `app.py` - main Tkinter desktop application for Jira CSV analysis.
- `cutdown.csv` - sample Jira-style CSV fixture.
- `index.html` - browser prototype for removing empty columns from CSV and Markdown tables.
- `code.html` - visual/reference HTML file.

## Requirements

- Python 3.10+
- Tkinter available in your Python installation

No third-party Python dependencies are required.

## Run The App

Windows PowerShell:

```powershell
python app.py
```

If you are using the local virtual environment in this repo:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

## How To Use

1. Launch the app.
2. Click `Load Jira CSV` and choose your Jira export.
3. Pick a report from the `Report` dropdown.
4. Narrow the dataset with filters such as issue type, status, sprint, assignee, or quick presets.
5. Use `Export Report` to save the current view.
6. Use `Export Cleaned CSV` to save the original dataset with empty columns removed.

## Epic Breakdown View

The `Epic Breakdown` report shows epics in the left tree column and indents child stories, bugs, tasks, and subtasks beneath them.

- Top-level rows are epics.
- Child rows are issues linked to that epic through `Parent key`.
- Issues without a matched epic are grouped under `(No Epic)`.
- Exporting this view writes a flattened CSV with epic columns preserved.

## Jira Fields The App Understands

The analyzer is built around common Jira CSV headers, including these fields when present:

- `Issue key`
- `Summary`
- `Issue Type`
- `Status`
- `Status Category`
- `Parent key`
- `Parent summary`
- `Sprint`
- `Assignee`
- `Description`
- `Created`
- `Updated`
- `Custom field (Story Points)`
- `Custom field (Dev Story points)`
- `Custom field (Test Story Points)`
- `Priority`
- `Custom field (Severity)`

Missing fields do not necessarily prevent loading, but some reports or filters may be less useful if those columns are absent.

## Notes

- Duplicate Jira headers are automatically disambiguated internally.
- Estimate reporting prefers `Story Points`, then falls back to `Dev Story points`, then `Test Story Points`.
- Parent containers are currently recognized as epic, feature, or initiative.
- `index.html` and `code.html` are older browser-side prototype/reference files and are not the main implementation path.


