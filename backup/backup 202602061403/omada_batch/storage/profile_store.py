from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from omada_batch.config import DATA_DIR, DEFAULT_PROFILE_PATH, LEGACY_PROFILE_PATH


class ProfileStore:
    def __init__(self, path: str | None = None):
        if path:
            self.path = path
        elif os.path.exists(DEFAULT_PROFILE_PATH):
            self.path = DEFAULT_PROFILE_PATH
        elif os.path.exists(LEGACY_PROFILE_PATH):
            self.path = LEGACY_PROFILE_PATH
        else:
            self.path = DEFAULT_PROFILE_PATH

    def load_raw(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return []

        if isinstance(raw, dict):
            items = raw.get("profiles")
            if not isinstance(items, list):
                items = raw.get("controllers")
            if not isinstance(items, list):
                items = []
        elif isinstance(raw, list):
            items = raw
        else:
            items = []
        return [x for x in items if isinstance(x, dict)]

    def save_raw(self, profiles: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.path) or DATA_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"profiles": profiles}, f, indent=2)
