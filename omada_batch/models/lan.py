from __future__ import annotations

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedLan:
    index: int
    name: str
    vlan_id: int
    network: ipaddress.IPv4Network
    gateway: ipaddress.IPv4Address
    dhcp_start: ipaddress.IPv4Address
    dhcp_end: ipaddress.IPv4Address


@dataclass(frozen=True)
class PlannedVlan:
    index: int
    name: str
    vlan_id: int
