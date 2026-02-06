from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from omada_batch.config import DATA_DIR


DEFAULT_CHANGELOG_PATH = os.path.join(DATA_DIR, "file_changelog.jsonl")


def append_file_change_log(
    action: str,
    target_path: str,
    *,
    changelog_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    log_path = changelog_path or DEFAULT_CHANGELOG_PATH
    os.makedirs(os.path.dirname(log_path) or DATA_DIR, exist_ok=True)
    event: dict[str, Any] = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "action": action,
        "path": os.path.abspath(target_path),
    }
    if details:
        event["details"] = details
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def write_json_with_changelog(
    target_path: str,
    payload: Any,
    *,
    changelog_path: str | None = None,
    details: dict[str, Any] | None = None,
    indent: int = 2,
) -> None:
    existed = os.path.exists(target_path)
    os.makedirs(os.path.dirname(target_path) or DATA_DIR, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent)
    append_file_change_log(
        "edited" if existed else "created",
        target_path,
        changelog_path=changelog_path,
        details=details,
    )


def delete_file_with_changelog(
    target_path: str,
    *,
    changelog_path: str | None = None,
    details: dict[str, Any] | None = None,
    missing_ok: bool = False,
) -> None:
    if not os.path.exists(target_path):
        if missing_ok:
            return
        raise FileNotFoundError(target_path)
    os.remove(target_path)
    append_file_change_log("deleted", target_path, changelog_path=changelog_path, details=details)
