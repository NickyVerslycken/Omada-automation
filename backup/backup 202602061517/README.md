# Omada Automation (Python GUI)

Desktop GUI application to automate Omada SDN LAN/VLAN tasks with the Omada OpenAPI.

## What this project does

- Connects to an Omada Controller using OpenAPI client credentials.
- Lists available sites.
- Loads and filters current LAN networks.
- Generates batch LAN/VLAN plans from an IP/VLAN range.
- Pushes planned LAN networks to the selected site.
- Saves, imports, exports, and removes controller connection profiles.
- Exports network and plan JSON files.

## Requirements

- Python 3.11+ (3.12+ recommended).
- Internet/network access from your machine to the Omada Controller URL.
- Omada OpenAPI credentials:
  - `Client ID`
  - `Client Secret`
  - Optional `omadacId` (auto-detected in many setups).
- Python package dependencies (see `requirements.txt`):
  - `requests`
  - `tk` (note: `tkinter` is part of standard Python on many systems; Linux may need OS tkinter package).

## Install

### Windows (PowerShell)

```powershell
# 1) Go to the project folder
cd "C:\path\to\Omada-automation"

# 2) Create and activate virtual environment
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `tkinter` is missing on Windows, reinstall Python from python.org and ensure Tcl/Tk is selected in the installer.

### macOS (zsh/bash)

```bash
# 1) Go to the project folder
cd "/path/to/Omada-automation"

# 2) Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `tkinter` is missing on macOS, install a Python build that includes Tk support (for example, official python.org installer).

### Linux (bash)

```bash
# 1) Go to the project folder
cd "/path/to/Omada-automation"

# 2) Install tkinter support package (example for Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y python3-tk

# 3) Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4) Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Fedora/RHEL-based systems, install `python3-tkinter` with `dnf`.

## Run the app

From activated virtual environment:

```bash
python runners/run_gui.py
```

Alternative launcher:

```bash
python start-omada-app.pyw
```

## Typical workflow

1. Open app and enter controller URL + API credentials.
2. Connect and select target site.
3. Refresh DHCP servers / gateways.
4. Fetch current networks (optional export from Current Networks tab).
5. In Batch tab, generate preview from base network/VLAN parameters.
6. Review plan and push to controller.

## Data and logs

- Controller profiles are stored in `data/controller_profiles.json`.
- File-change audit log is stored in `backup/file_changelog.jsonl`.
- Per-run backups are stored in `backup/backup YYYYMMDDHHmm/`.

## Troubleshooting

- Connection fails:
  - Verify controller base URL is reachable from your machine.
  - Check Client ID / Client Secret.
  - Try setting `omadacId` explicitly if auto-detection fails.
- GUI does not start:
  - Confirm virtual environment is activated.
  - Confirm `tkinter` is installed and importable.
- API errors during push:
  - Check site selection and gateway selection.
  - Review the app Logs tab for detailed request/response fallback behavior.
