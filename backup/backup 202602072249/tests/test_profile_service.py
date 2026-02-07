import os

from omada_batch.services.profile_service import normalize_profile


def test_normalize_profile_resolves_env_credentials(monkeypatch):
    monkeypatch.setenv("OMADA_CLIENT_ID", "id-from-env")
    monkeypatch.setenv("OMADA_CLIENT_SECRET", "secret-from-env")
    monkeypatch.setenv("OMADA_OMADAC_ID", "omada-from-env")

    profile = normalize_profile(
        {
            "name": "controller-a",
            "base_url": "https://192.168.1.10",
            "client_id_env": "OMADA_CLIENT_ID",
            "client_secret_env": "OMADA_CLIENT_SECRET",
            "omada_id_env": "OMADA_OMADAC_ID",
        }
    )

    assert profile is not None
    assert profile["client_id"] == "id-from-env"
    assert profile["client_secret"] == "secret-from-env"
    assert profile["omada_id"] == "omada-from-env"


def test_normalize_profile_keeps_legacy_credentials_without_env(monkeypatch):
    monkeypatch.delenv("OMADA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OMADA_CLIENT_SECRET", raising=False)

    profile = normalize_profile(
        {
            "name": "legacy-controller",
            "base_url": "https://192.168.1.20",
            "client_id": "legacy-id",
            "client_secret": "legacy-secret",
        }
    )

    assert profile is not None
    assert profile["client_id"] == "legacy-id"
    assert profile["client_secret"] == "legacy-secret"
    assert profile["client_id_env"] == "OMADA_CLIENT_ID"
    assert profile["client_secret_env"] == "OMADA_CLIENT_SECRET"
