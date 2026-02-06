from __future__ import annotations

from typing import Any, Dict, List


def build_interface_catalog(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for dev in devices or []:
        dtype_raw = dev.get("type") or dev.get("deviceType") or dev.get("role")
        try:
            dtype = int(dtype_raw) if dtype_raw is not None else None
        except Exception:
            dtype = None
        dtype_text = str(dtype_raw or "").strip().lower()
        if dtype is None:
            if "gateway" in dtype_text or "router" in dtype_text:
                dtype = 1
            elif "switch" in dtype_text:
                dtype = 2

        if dtype not in (1, 2):
            continue

        name = str(
            dev.get("name")
            or dev.get("customName")
            or dev.get("deviceName")
            or dev.get("displayName")
            or ""
        ).strip()
        model = str(dev.get("model") or dev.get("deviceModel") or dev.get("modelName") or "").strip()
        dev_id = str(dev.get("deviceId") or dev.get("device_id") or dev.get("id") or "").strip()
        mac = str(dev.get("mac") or dev.get("macAddress") or dev.get("deviceMac") or "").strip()
        if not mac and not dev_id:
            continue

        prefix = "[GATEWAY]" if dtype == 1 else "[SWITCH]"
        id_tail = mac or dev_id
        label = f"{prefix} {name or 'Unknown'} ({model or 'Unknown'}) - {id_tail}"

        unique_key = dev_id or mac
        if unique_key in seen:
            continue
        seen.add(unique_key)

        iface_ids: List[str] = []
        iface_list: List[Dict[str, str]] = []
        raw_iface_ids = dev.get("interfaceIds")
        if isinstance(raw_iface_ids, list):
            for iid in raw_iface_ids:
                if iid:
                    iface_ids.append(str(iid))
        for iface_key in ("interfaces", "ports", "portList", "lanInterfaces"):
            raw_ifaces = dev.get(iface_key)
            if not isinstance(raw_ifaces, list):
                continue
            for it in raw_ifaces:
                if not isinstance(it, dict):
                    continue
                iid = it.get("id") or it.get("interfaceId") or it.get("portId")
                if not iid:
                    continue
                sid = str(iid)
                if sid not in iface_ids:
                    iface_ids.append(sid)
                iname = str(
                    it.get("customName")
                    or it.get("alias")
                    or it.get("portName")
                    or it.get("interfaceName")
                    or it.get("name")
                    or it.get("ifName")
                    or it.get("displayName")
                    or it.get("ifname")
                    or it.get("port")
                    or sid
                )
                iface_list.append(
                    {
                        "id": sid,
                        "name": iname,
                        "display_name": str(it.get("displayName") or ""),
                        "port_name": str(it.get("portName") or ""),
                        "interface_name": str(it.get("interfaceName") or ""),
                        "if_name": str(it.get("ifName") or it.get("ifname") or ""),
                        "alias": str(it.get("alias") or it.get("customName") or ""),
                    }
                )
        if not iface_list:
            iface_list = [{"id": sid, "name": sid} for sid in iface_ids]

        catalog.append(
            {
                "name": name or id_tail,
                "label": label,
                "value": dev_id or mac or name,
                "mac": mac,
                "type": dtype,
                "model": model or None,
                "device_id": dev_id or None,
                "interface_ids": iface_ids,
                "interfaces": iface_list,
            }
        )

    return catalog
