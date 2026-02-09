## Backup policy (mandatory)
- **Before modifying any existing file**, create a backup copy of the file’s *current* contents.
- Backups live in: `<repo_root>/backup/backup YYYYMMDDHHmm/`
  - Timestamp format is **YYYYMMDDHHmm** (24h clock), based on **local system time**.
  - Example folder: `backup/backup 202602052248/`
- If `backup/` does not exist, **create it**.
- For a single run where multiple files are changed, **use one single timestamp folder** for all backups in that run.
  - Generate the timestamp **once at the start of the run** and reuse it.
- Inside the timestamp folder, **preserve the original relative paths** of the files.
  - Example: backing up `src/app/main.py` goes to `backup/backup 202602052248/src/app/main.py`
- For operations:
  - **Edit**: backup the file *before* writing changes.
  - **Delete**: backup the file *before* deleting it.
  - **Rename/Move**: backup the *source file* before renaming/moving.
  - **New files**: no backup required.
- If the timestamp folder already exists (e.g., same minute), **reuse it** (do not fail).
- The `backup/` folder (including `backup/file_changelog.jsonl`) is for local developer use only and must not be committed or pushed to GitHub.

## Changelog policy (mandatory)
- **Whenever a file is created, edited, deleted, or moved/renamed, append a changelog entry**.
- Changelog file location: `<repo_root>/backup/file_changelog.jsonl` (JSON Lines format, one event per line).
- Required fields per changelog entry:
  - timestamp (local ISO-8601 with timezone offset),
  - action (`created`, `edited`, `deleted`, `moved`),
  - project-relative path of the affected file in format `Omada-automation/...`,
  - rollback instructions (clear and concrete steps to undo that specific change, with exact backup file path when a backup exists),
  - details with practical context (source function/flow, counts, error context when relevant).
- For `edited` and `deleted` actions, include `details.backup_path` with the exact timestamped backup file path, for example: `backup/backup 202602061522/README.md`.
- Never store full machine/network absolute paths in changelogs or other project files.
- Use forward slashes (`/`) in paths, never backslashes (`\` or `\\`).
- For move/rename, log at least source and destination paths in details.
- Changelog writes are required for every run, same as backups; do not skip logging for bulk operations.

## File structure
- when changing/creating/deleting a folder name, filename; update the file `info/file_structure.txt`.

## Info docs maintenance
- when code changes (files/classes/functions/dependencies), also update:
  - `info/code_map_with_responsibilities.txt`
  - `info/dependency_relations.txt`
- when files are added/removed/renamed or file line counts change, update:
  - `info/file_structure_with_loc.txt`

## Info to use
- In the folder info you can find files like *.har what is a log when configuring the omada controller directly in trough the web interface using my browser, also you can find here API information, for information about the API but this is possible a bit outdated, if necessary you may search on the web for solutions.

## API fallback and logging (general)
- When using OpenAPI versioned endpoints, implement fallback in this order where possible: **v3 -> v2 -> v1**.
- For each fallback attempt, log clearly:
  - what endpoint/version is being attempted,
  - what failed (including error details),
  - what succeeded (including selected version and basic result info).
- Do not truncate log messages below 250 characters; keep full detail where practical.
