from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from typing import Any

from omada_batch.config import PROJECT_ROOT


BACKUP_DIR = os.path.join(PROJECT_ROOT, "backup")
DEFAULT_CHANGELOG_PATH = os.path.join(BACKUP_DIR, "file_changelog.jsonl")
PROJECT_NAME = os.path.basename(os.path.normpath(PROJECT_ROOT))


def _to_project_relative_path(path: str) -> str:
    text = str(path or "").strip().replace("\\", "/")
    if not text:
        return f"{PROJECT_NAME}/"
    if text.startswith(f"{PROJECT_NAME}/"):
        return text
    absolute = os.path.abspath(path) if os.path.isabs(path) else os.path.abspath(os.path.join(PROJECT_ROOT, path))
    try:
        rel = os.path.relpath(absolute, PROJECT_ROOT)
    except ValueError:
        return text
    rel_norm = rel.replace("\\", "/")
    if rel_norm.startswith("../"):
        return text
    return f"{PROJECT_NAME}/{rel_norm}"


def _normalize_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(details, dict):
        return details
    out: dict[str, Any] = {}
    for key, value in details.items():
        if key in {"path", "source_path", "destination_path", "backup_path"} and isinstance(value, str):
            out[key] = _to_project_relative_path(value)
        elif isinstance(value, str):
            out[key] = value.replace("\\", "/")
        else:
            out[key] = value
    return out


def _rollback_instructions(action: str, target_path: str, details: dict[str, Any] | None) -> str:
    normalized_target = _to_project_relative_path(target_path)
    backup_path = ""
    if isinstance(details, dict):
        backup_path = str(details.get("backup_path") or "").strip()
        if backup_path:
            backup_path = _to_project_relative_path(backup_path)
    if action == "created":
        return f"Rollback: remove created file '{normalized_target}'."
    if action in {"edited", "deleted"}:
        if backup_path:
            return f"Rollback: restore '{normalized_target}' from backup '{backup_path}'."
        return f"Rollback: restore '{normalized_target}' from the latest backup copy under backup/backup YYYYMMDDHHmm/."
    if action == "moved":
        return f"Rollback: move file back to its original path (see details.source_path and details.destination_path)."
    return f"Rollback: inspect details and restore '{normalized_target}' from backup if needed."


def append_file_change_log(
    action: str,
    target_path: str,
    *,
    changelog_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    log_path = changelog_path or DEFAULT_CHANGELOG_PATH
    os.makedirs(os.path.dirname(log_path) or BACKUP_DIR, exist_ok=True)
    normalized_details = _normalize_details(details)
    event: dict[str, Any] = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "action": action,
        "path": _to_project_relative_path(target_path),
        "rollback": _rollback_instructions(action, target_path, normalized_details),
    }
    if normalized_details:
        event["details"] = normalized_details
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


def _should_skip_git_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return True
    if normalized.startswith("backup/backup "):
        return True
    if normalized == "backup/file_changelog.jsonl":
        return True
    if "/__pycache__/" in f"/{normalized}/":
        return True
    if normalized.endswith((".pyc", ".pyo")):
        return True
    return False


def sync_git_worktree_to_changelog(
    *,
    repo_root: str | None = None,
    changelog_path: str | None = None,
) -> int:
    root = repo_root or PROJECT_ROOT
    proc = subprocess.run(
        ["git", "-C", root, "status", "--porcelain", "-z"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git status failed: {stderr}")

    written = 0
    items = proc.stdout.decode("utf-8", errors="replace").split("\x00")
    i = 0
    while i < len(items):
        raw_line = items[i]
        i += 1
        if not raw_line or len(raw_line) < 3:
            continue

        status = raw_line[:2]
        body = raw_line[3:].strip()
        if not body:
            continue

        is_rename = ("R" in status or "C" in status) and i < len(items)
        if is_rename:
            source_rel = body
            dest_rel = items[i].strip()
            i += 1
            if _should_skip_git_path(source_rel) and _should_skip_git_path(dest_rel):
                continue
            append_file_change_log(
                "moved",
                os.path.join(root, dest_rel),
                changelog_path=changelog_path,
                details={
                    "source": "sync_git_worktree_to_changelog",
                    "source_path": _to_project_relative_path(os.path.join(root, source_rel)),
                    "destination_path": _to_project_relative_path(os.path.join(root, dest_rel)),
                    "git_status": status,
                },
            )
            written += 1
            continue

        if _should_skip_git_path(body):
            continue

        if "D" in status:
            action = "deleted"
        elif "A" in status or status == "??":
            action = "created"
        else:
            action = "edited"

        append_file_change_log(
            action,
            os.path.join(root, body),
            changelog_path=changelog_path,
            details={"source": "sync_git_worktree_to_changelog", "git_status": status},
        )
        written += 1
    return written
