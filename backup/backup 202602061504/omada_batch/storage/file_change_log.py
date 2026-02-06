from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from omada_batch.config import PROJECT_ROOT


BACKUP_DIR = os.path.join(PROJECT_ROOT, "backup")
DEFAULT_CHANGELOG_PATH = os.path.join(BACKUP_DIR, "file_changelog.jsonl")


def _rollback_instructions(action: str, target_path: str, details: dict[str, Any] | None) -> str:
    backup_path = ""
    if isinstance(details, dict):
        backup_path = str(details.get("backup_path") or "").strip()
    if action == "created":
        return f"Rollback: remove created file '{os.path.abspath(target_path)}'."
    if action in {"edited", "deleted"}:
        if backup_path:
            return f"Rollback: restore '{os.path.abspath(target_path)}' from backup '{backup_path}'."
        return f"Rollback: restore '{os.path.abspath(target_path)}' from the latest backup copy under backup/backup YYYYMMDDHHmm/."
    if action == "moved":
        return f"Rollback: move file back to its original path (see details.source_path and details.destination_path)."
    return f"Rollback: inspect details and restore '{os.path.abspath(target_path)}' from backup if needed."


def append_file_change_log(
    action: str,
    target_path: str,
    *,
    changelog_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    log_path = changelog_path or DEFAULT_CHANGELOG_PATH
    os.makedirs(os.path.dirname(log_path) or BACKUP_DIR, exist_ok=True)
    event: dict[str, Any] = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "action": action,
        "path": os.path.abspath(target_path),
        "rollback": _rollback_instructions(action, target_path, details),
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
    os.makedirs(os.path.dirname(target_path) or PROJECT_ROOT, exist_ok=True)
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
