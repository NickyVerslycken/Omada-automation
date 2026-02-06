from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ControllerProfile:
    name: str
    base_url: str
    client_id: str
    client_secret: str
    verify_ssl: bool = False
    omada_id: str = ""
