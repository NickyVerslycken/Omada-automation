from __future__ import annotations

import ipaddress
from typing import List, Tuple

from omada_batch.models.lan import PlannedLan


def generate_plan(
    name_prefix: str,
    start_ip: str,
    prefix_len: int,
    count: int,
    start_vlan: int,
    dhcp_start_offset: int,
    dhcp_end_offset: int,
) -> Tuple[List[PlannedLan], List[str]]:
    warnings: List[str] = []

    if count <= 0:
        raise ValueError("Number of networks must be > 0")
    if not (1 <= prefix_len <= 30):
        raise ValueError("Prefix length must be between 1 and 30")
    if start_vlan < 1 or start_vlan > 4090:
        raise ValueError("Start VLAN must be 1..4090")
    if start_vlan + count - 1 > 4090:
        raise ValueError("VLAN range exceeds 4090 (controller API limit)")

    ip = ipaddress.IPv4Address(start_ip)
    net0 = ipaddress.IPv4Network((ip, prefix_len), strict=False)
    if ip != net0.network_address:
        warnings.append(f"Start IP {ip} is not a network boundary for /{prefix_len}. Using {net0.network_address} as the first subnet.")

    block_size = net0.num_addresses
    plans: List[PlannedLan] = []

    for i in range(count):
        net_addr_int = int(net0.network_address) + i * block_size
        n = ipaddress.IPv4Network((ipaddress.IPv4Address(net_addr_int), prefix_len), strict=True)

        gw = ipaddress.IPv4Address(int(n.network_address) + 1)
        first_usable = ipaddress.IPv4Address(int(n.network_address) + 2)
        last_usable = ipaddress.IPv4Address(int(n.broadcast_address) - 1)

        ds = ipaddress.IPv4Address(int(n.network_address) + dhcp_start_offset)
        de = ipaddress.IPv4Address(int(n.broadcast_address) - dhcp_end_offset)

        if ds < first_usable:
            ds = first_usable
        if de > last_usable:
            de = last_usable
        if ds >= de:
            warnings.append(f"DHCP range invalid for {n.with_prefixlen}; adjusted to {first_usable}-{last_usable}")
            ds, de = first_usable, last_usable

        vlan = start_vlan + i
        name = f"{name_prefix}-{vlan}"

        plans.append(
            PlannedLan(
                index=i + 1,
                name=name,
                vlan_id=vlan,
                network=n,
                gateway=gw,
                dhcp_start=ds,
                dhcp_end=de,
            )
        )

    return plans, warnings
