# Omada Automation (Python GUI)

Desktop GUI application to automate Omada SDN LAN/VLAN tasks with the Omada OpenAPI.

## What this project does

- Connects to an Omada Controller using OpenAPI client credentials.
- Lists available sites.
- Loads and filters current LAN networks.
- Generates batch LAN/VLAN plans from an IP/VLAN range.
- Pushes planned LAN networks to the selected site with the selected device as dhcp-server.
- Saves, imports, exports, and removes controller connection profiles.
- Exports network and plan JSON files.

## Requirements

- Python 3.11+ (3.12+ recommended).
- Internet/network access from your machine to the Omada Controller URL.
- Omada OpenAPI credentials:
  - `Client ID`
  - `Client Secret`
  - Optional `omadacId` (auto-detected in many setups).
- Environment file:
  - Copy `data/.env.example` to `data/.env` and set credentials there. Can be done by saving your configuration in the GUI of the application as well.
- Python package dependencies (see `requirements.txt`):
  - `requests`
  - `tk` (note: `tkinter` is part of standard Python on many systems; Linux may need OS tkinter package).

## Install

### Windows (PowerShell)

```powershell
# 1) Go to the project folder
cd "Omada-automation"

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

Or just double click on the start-omada-app.pyw file.

## Credentials in `data/.env`

Profiles in `data/controller_profiles.json` store env variable names (`client_id_env`, `client_secret_env`, `omada_id_env`) instead of raw secrets.

Use `data/.env.example` as template:

```bash
cp data/.env.example data/.env
```

Then set:
- `OMADA_CLIENT_ID`
- `OMADA_CLIENT_SECRET`
- Optional `OMADA_OMADAC_ID`

## Typical workflow

1. Fill `data/.env` with credentials (or enter credentials once in the app and save profile to write `data/.env`).
2. Open app and enter/select controller URL.
3. Connect and select target site.
4. Refresh DHCP servers / gateways if needed.
5. Fetch current networks (optional export from Current Networks tab).
6. In Batch tab, generate preview from base network/VLAN parameters.
7. Review plan and push to controller.

## Data and logs

- Controller profiles are stored in `data/controller_profiles.json` (without raw credentials).
- Runtime credentials are loaded from `data/.env`.

## Changes to software stack

- File-change audit log is stored in `backup/file_changelog.jsonl` when changes are made to the software stack.
- Backups are stored in `backup/backup YYYYMMDDHHmm/` when something is changed to the software stack.

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
  - Enable Developer mode in the top right corner on the first screen to enable a tab that gives full json output of the api actions
