from omada_batch.services.profile_service import (
    ensure_unique_profile_id,
    normalize_profile,
)


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


def test_normalize_profile_uses_profile_id_based_env_keys(monkeypatch):
    monkeypatch.setenv("OMADA_PROFILE_LAB_OC300_CLIENT_ID", "lab-id")
    monkeypatch.setenv("OMADA_PROFILE_LAB_OC300_CLIENT_SECRET", "lab-secret")
    monkeypatch.setenv("OMADA_PROFILE_LAB_OC300_OMADAC_ID", "lab-omada")

    profile = normalize_profile(
        {
            "id": "lab-oc300",
            "name": "lab",
            "base_url": "https://192.168.1.99",
        }
    )

    assert profile is not None
    assert profile["id"] == "lab_oc300"
    assert profile["client_id_env"] == "OMADA_PROFILE_LAB_OC300_CLIENT_ID"
    assert profile["client_secret_env"] == "OMADA_PROFILE_LAB_OC300_CLIENT_SECRET"
    assert profile["omada_id_env"] == "OMADA_PROFILE_LAB_OC300_OMADAC_ID"
    assert profile["client_id"] == "lab-id"
    assert profile["client_secret"] == "lab-secret"
    assert profile["omada_id"] == "lab-omada"


def test_ensure_unique_profile_id_appends_suffix():
    profile_id = ensure_unique_profile_id("home_controller", ["home_controller", "other", "home_controller_2"])
    assert profile_id == "home_controller_3"
