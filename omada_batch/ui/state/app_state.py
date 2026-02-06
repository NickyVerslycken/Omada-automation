from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from omada_batch.api.omada_client import OmadaOpenApiClient
from omada_batch.models.lan import PlannedLan
from omada_batch.storage.profile_store import ProfileStore


@dataclass
class AppState:
    client: Optional[OmadaOpenApiClient] = None
    sites: List[Dict[str, Any]] = field(default_factory=list)
    gateways: List[Dict[str, Any]] = field(default_factory=list)
    selected_site_id: Optional[str] = None
    current_gateway_filter_index: int = -1
    batch_gateway_index: int = -1
    plan: List[PlannedLan] = field(default_factory=list)
    plan_interface_ids: Dict[int, List[str]] = field(default_factory=dict)
    controller_profiles: List[Dict[str, Any]] = field(default_factory=list)
    networks_cache_all: List[Dict[str, Any]] = field(default_factory=list)
    networks_cache: List[Dict[str, Any]] = field(default_factory=list)
    profile_store: ProfileStore = field(default_factory=ProfileStore)
