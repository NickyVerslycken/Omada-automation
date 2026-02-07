from __future__ import annotations

import os
import re
from typing import Dict

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_PROFILE_PATH = os.path.join(DATA_DIR, "controller_profiles.json")
LEGACY_PROFILE_PATH = os.path.join(PROJECT_ROOT, "controller_profiles.json")
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")

DEFAULT_CLIENT_ID_ENV_VAR = "OMADA_CLIENT_ID"
DEFAULT_CLIENT_SECRET_ENV_VAR = "OMADA_CLIENT_SECRET"
DEFAULT_OMADA_ID_ENV_VAR = "OMADA_OMADAC_ID"

_ENV_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def _strip_env_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and ((text[0] == text[-1] == '"') or (text[0] == text[-1] == "'")):
        return text[1:-1]
    return text


def load_env_file(path: str = ENV_FILE_PATH, *, override: bool = False) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                match = _ENV_KEY_RE.match(raw)
                if not match:
                    continue
                key, raw_value = match.group(1), match.group(2)
                if not override and key in os.environ:
                    continue
                os.environ[key] = _strip_env_quotes(raw_value)
    except Exception:
        return


def _format_env_value(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if any(ch.isspace() for ch in text) or "#" in text or '"' in text or "'" in text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f"\"{escaped}\""
    return text


def upsert_env_file(values: Dict[str, str], path: str = ENV_FILE_PATH) -> None:
    os.makedirs(os.path.dirname(path) or PROJECT_ROOT, exist_ok=True)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = []

    key_to_line_idx: Dict[str, int] = {}
    for idx, line in enumerate(lines):
        match = _ENV_KEY_RE.match(line)
        if match and match.group(1) not in key_to_line_idx:
            key_to_line_idx[match.group(1)] = idx

    for key, value in values.items():
        if value is None:
            continue
        formatted = _format_env_value(value)
        rendered = f"{key}={formatted}"
        if key in key_to_line_idx:
            lines[key_to_line_idx[key]] = rendered
        else:
            lines.append(rendered)

    body = "\n".join(lines).rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)

    for key, value in values.items():
        if value is not None:
            os.environ[key] = str(value)


load_env_file()
