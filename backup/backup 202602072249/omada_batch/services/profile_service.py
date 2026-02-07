from __future__ import annotations

import os
from typing import Any, Dict

from omada_batch.config import (
    DEFAULT_CLIENT_ID_ENV_VAR,
    DEFAULT_CLIENT_SECRET_ENV_VAR,
    DEFAULT_OMADA_ID_ENV_VAR,
)


def _env_value(name: str) -> str:
    key = str(name or "").strip()
    if not key:
        return ""
    return str(os.getenv(key, "")).strip()


def normalize_profile(item: Any, index: int = 0) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    base_url = str(item.get("base_url") or item.get("url") or item.get("ip") or "").strip()
    client_id_env = str(item.get("client_id_env") or item.get("clientIdEnv") or DEFAULT_CLIENT_ID_ENV_VAR).strip()
    client_secret_env = str(item.get("client_secret_env") or item.get("clientSecretEnv") or DEFAULT_CLIENT_SECRET_ENV_VAR).strip()
    omada_id_env = str(item.get("omada_id_env") or item.get("omadaIdEnv") or DEFAULT_OMADA_ID_ENV_VAR).strip()
    legacy_client_id = str(item.get("client_id") or item.get("clientId") or "").strip()
    legacy_client_secret = str(item.get("client_secret") or item.get("clientSecret") or "").strip()
    client_id = legacy_client_id or _env_value(client_id_env)
    client_secret = legacy_client_secret or _env_value(client_secret_env)
    verify_ssl = bool(item.get("verify_ssl") if "verify_ssl" in item else item.get("verifySsl", False))
    legacy_omada_id = str(item.get("omada_id") or item.get("omadac_id") or item.get("omadacId") or "").strip()
    omada_id = legacy_omada_id or _env_value(omada_id_env)
    name = str(item.get("name") or "").strip()

    if not base_url and not client_id and not client_secret and not client_id_env and not client_secret_env:
        return None
    if not name:
        name = f"Controller {index + 1}"

    return {
        "name": name,
        "base_url": base_url,
        "client_id_env": client_id_env or DEFAULT_CLIENT_ID_ENV_VAR,
        "client_secret_env": client_secret_env or DEFAULT_CLIENT_SECRET_ENV_VAR,
        "verify_ssl": verify_ssl,
        "omada_id_env": omada_id_env or DEFAULT_OMADA_ID_ENV_VAR,
        "client_id": client_id,
        "client_secret": client_secret,
        "omada_id": omada_id,
    }
