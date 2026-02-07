from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable

from omada_batch.config import (
    DEFAULT_CLIENT_ID_ENV_VAR,
    DEFAULT_CLIENT_SECRET_ENV_VAR,
    DEFAULT_OMADA_ID_ENV_VAR,
)

PROFILE_ENV_PREFIX = "OMADA_PROFILE"
_PROFILE_ID_RE = re.compile(r"[^a-z0-9]+")


def _env_value(name: str) -> str:
    key = str(name or "").strip()
    if not key:
        return ""
    return str(os.getenv(key, "")).strip()


def normalize_profile_id(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = _PROFILE_ID_RE.sub("_", text).strip("_")
    return text


def suggest_profile_id(name: str, base_url: str, *, index: int = 0) -> str:
    name_token = normalize_profile_id(name)
    url_text = str(base_url or "").strip()
    host_text = url_text.split("://", 1)[-1].split("/", 1)[0].strip().lower()
    if ":" in host_text:
        host_text = host_text.split(":", 1)[0]
    host_token = normalize_profile_id(host_text)

    if name_token and host_token:
        return name_token if host_token in name_token else f"{name_token}_{host_token}"
    if name_token:
        return name_token
    if host_token:
        return host_token
    return f"controller_{index + 1}"


def ensure_unique_profile_id(profile_id: str, existing_ids: Iterable[str]) -> str:
    used = {normalize_profile_id(value) for value in existing_ids if normalize_profile_id(value)}
    base = normalize_profile_id(profile_id) or "controller"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def profile_env_var_names(profile_id: str) -> Dict[str, str]:
    normalized = normalize_profile_id(profile_id)
    if not normalized:
        return {
            "client_id_env": DEFAULT_CLIENT_ID_ENV_VAR,
            "client_secret_env": DEFAULT_CLIENT_SECRET_ENV_VAR,
            "omada_id_env": DEFAULT_OMADA_ID_ENV_VAR,
        }
    token = normalized.upper()
    prefix = f"{PROFILE_ENV_PREFIX}_{token}"
    return {
        "client_id_env": f"{prefix}_CLIENT_ID",
        "client_secret_env": f"{prefix}_CLIENT_SECRET",
        "omada_id_env": f"{prefix}_OMADAC_ID",
    }


def normalize_profile(item: Any, index: int = 0) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    profile_id = normalize_profile_id(item.get("id") or item.get("profile_id") or item.get("profileId") or "")
    generated_keys = profile_env_var_names(profile_id) if profile_id else {}
    base_url = str(item.get("base_url") or item.get("url") or item.get("ip") or "").strip()
    client_id_env = str(item.get("client_id_env") or item.get("clientIdEnv") or generated_keys.get("client_id_env") or DEFAULT_CLIENT_ID_ENV_VAR).strip()
    client_secret_env = str(
        item.get("client_secret_env")
        or item.get("clientSecretEnv")
        or generated_keys.get("client_secret_env")
        or DEFAULT_CLIENT_SECRET_ENV_VAR
    ).strip()
    omada_id_env = str(item.get("omada_id_env") or item.get("omadaIdEnv") or generated_keys.get("omada_id_env") or DEFAULT_OMADA_ID_ENV_VAR).strip()
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
        "id": profile_id,
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
