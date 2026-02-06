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

## File structure
- when changing/creating/deleting a folder name, filename; update the file `info/file_structure.txt`.

## Info docs maintenance
- when code changes (files/classes/functions/dependencies), also update:
  - `info/code_map_with_responsibilities.txt`
  - `info/dependency_relations.txt`
- when files are added/removed/renamed or file line counts change, update:
  - `info/file_structure_with_loc.txt`

## Info to use
- In the folder info you can find the file controller-reate-network.har what is a log when creating networks in the omada controller directly in the controller trough the web interface using my browser, also you can find the file Omada_SDN_Controller_V5.9.9 API Document.html for information about the API but this is possible a bit outdated, if necessary you may search on the web for solutions.
