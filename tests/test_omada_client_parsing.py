from omada_batch.api.omada_client import OmadaOpenApiClient
from omada_batch.services.device_service import merge_interface_catalog_names
from omada_batch.services.lan_service import build_interface_catalog


def test_client_init_sets_base_url_without_trailing_slash():
    c = OmadaOpenApiClient("https://example.com/")
    assert c.base_url == "https://example.com"


def test_build_interface_catalog_prefers_port_id_and_name():
    devices = [
        {
            "type": "gateway",
            "mac": "24-2F-D0-4E-1E-BB",
            "name": "ER707-M2",
            "ports": [
                {
                    "id": 2,
                    "portId": "2_f3fbb5ef53a7470ebd05ff327b166f20",
                    "name": "2.5G WAN/LAN2",
                    "mode": 1,
                }
            ],
        }
    ]
    catalog = build_interface_catalog(devices)
    assert len(catalog) == 1
    interfaces = catalog[0]["interfaces"]
    assert interfaces[0]["id"] == "2_f3fbb5ef53a7470ebd05ff327b166f20"
    assert interfaces[0]["name"] == "2.5G WAN/LAN2"


def test_merge_interface_catalog_names_keeps_rich_fields():
    base = [{"id": "2_abc", "name": "2_abc", "display_name": "2.5G WAN/LAN2"}]
    extra = [{"id": "2_abc", "name": "Port2"}]
    merged = merge_interface_catalog_names(base, extra)
    assert merged[0]["id"] == "2_abc"
    assert merged[0]["display_name"] == "2.5G WAN/LAN2"
    assert merged[0]["name"] == "2.5G WAN/LAN2"
