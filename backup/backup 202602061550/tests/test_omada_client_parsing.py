from omada_batch.api.omada_client import OmadaOpenApiClient


def test_client_init_sets_base_url_without_trailing_slash():
    c = OmadaOpenApiClient("https://example.com/")
    assert c.base_url == "https://example.com"
