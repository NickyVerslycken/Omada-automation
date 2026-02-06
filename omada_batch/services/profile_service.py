from __future__ import annotations

from typing import Any, Dict


def normalize_profile(item: Any, index: int = 0) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    base_url = str(item.get("base_url") or item.get("url") or item.get("ip") or "").strip()
    client_id = str(item.get("client_id") or item.get("clientId") or "").strip()
    client_secret = str(item.get("client_secret") or item.get("clientSecret") or "").strip()
    verify_ssl = bool(item.get("verify_ssl") if "verify_ssl" in item else item.get("verifySsl", False))
    omada_id = str(item.get("omada_id") or item.get("omadac_id") or item.get("omadacId") or "").strip()
    name = str(item.get("name") or "").strip()

    if not base_url and not client_id and not client_secret:
        return None
    if not name:
        name = f"Controller {index + 1}"

    return {
        "name": name,
        "base_url": base_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "verify_ssl": verify_ssl,
        "omada_id": omada_id,
    }
