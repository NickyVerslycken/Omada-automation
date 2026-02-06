from pathlib import Path

from omada_batch.storage.profile_store import ProfileStore


def test_profile_store_roundtrip(tmp_path: Path):
    path = tmp_path / "profiles.json"
    store = ProfileStore(str(path))
    data = [{"name": "c1", "base_url": "https://1.2.3.4", "client_id": "id", "client_secret": "sec"}]
    store.save_raw(data)
    loaded = store.load_raw()
    assert len(loaded) == 1
    assert loaded[0]["name"] == "c1"
