from __future__ import annotations

import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_PROFILE_PATH = os.path.join(DATA_DIR, "controller_profiles.json")
LEGACY_PROFILE_PATH = os.path.join(PROJECT_ROOT, "controller_profiles.json")
