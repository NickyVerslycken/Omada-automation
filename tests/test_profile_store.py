import json
from pathlib import Path

from omada_batch.storage.file_change_log import delete_file_with_changelog
from omada_batch.storage.profile_store import ProfileStore


def test_profile_store_roundtrip(tmp_path: Path):
    path = tmp_path / "profiles.json"
    changelog = tmp_path / "changes.jsonl"
    store = ProfileStore(str(path), changelog_path=str(changelog))
    data = [{"name": "c1", "base_url": "https://1.2.3.4", "client_id": "id", "client_secret": "sec"}]
    store.save_raw(data)
    store.save_raw(data)
    loaded = store.load_raw()
    assert len(loaded) == 1
    assert loaded[0]["name"] == "c1"
    lines = changelog.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["action"] == "created"
    assert second["action"] == "edited"
    assert first["path"].endswith("profiles.json")


def test_delete_file_with_changelog(tmp_path: Path):
    target = tmp_path / "to_delete.json"
    target.write_text("{}", encoding="utf-8")
    changelog = tmp_path / "changes.jsonl"
    delete_file_with_changelog(str(target), changelog_path=str(changelog))
    assert not target.exists()
    lines = changelog.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "deleted"
    assert entry["path"].endswith("to_delete.json")
