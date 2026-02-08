from __future__ import annotations

from typing import Any, Dict, List


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_wan_interface(port: Dict[str, Any], name: str) -> bool:
    lowered_name = _text(name).lower()

    # Common explicit boolean markers from various Omada payload shapes.
    for key in ("isWan", "wan", "wanPort", "internetPort", "isInternetPort"):
        raw = port.get(key)
        if isinstance(raw, bool):
            if raw:
                return True
        elif _text(raw).lower() in ("1", "true", "yes", "wan", "internet"):
            return True

    mode_text = _text(port.get("mode")).lower()
    mode_int = _to_int(port.get("mode"))
    if mode_text in ("wan", "internet"):
        return True
    if mode_int == 0:
        # In observed payloads, mode=0 marks WAN mode on WAN/LAN combo ports.
        return True

    ptype_int = _to_int(port.get("type"))
    if ptype_int in (3, 4):
        # 3=dedicated WAN, 4=USB modem in observed payloads.
        return True

    role_text = " ".join(
        _text(port.get(k)).lower()
        for k in ("role", "usage", "purpose", "portType", "interfaceType")
        if _text(port.get(k))
    )
    if "wan" in role_text and "wan/lan" not in role_text and "lan/wan" not in role_text:
        return True

    if "wan" in lowered_name and "wan/lan" not in lowered_name and "lan/wan" not in lowered_name:
        return True
    return False


def _is_selectable_lan_interface(port: Dict[str, Any], name: str, is_wan: bool) -> bool:
    if is_wan:
        return False

    mode_text = _text(port.get("mode")).lower()
    mode_int = _to_int(port.get("mode"))
    if mode_text in ("lan",):
        return True
    if mode_int == 1:
        return True

    ptype_int = _to_int(port.get("type"))
    if ptype_int in (3, 4):
        return False

    lowered_name = _text(name).lower()
    if "wan/lan" in lowered_name or "lan/wan" in lowered_name:
        return True

    return True


def _merge_iface(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key in ("is_wan", "is_selectable"):
            continue
        if _text(merged.get(key)):
            continue
        if _text(value):
            merged[key] = value

    merged["is_wan"] = bool(existing.get("is_wan")) or bool(incoming.get("is_wan"))
    # Keep interface selectable only when both sides consider it selectable.
    merged["is_selectable"] = bool(existing.get("is_selectable", True)) and bool(incoming.get("is_selectable", True))
    return merged


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
        iface_list: List[Dict[str, Any]] = []
        iface_map: Dict[str, Dict[str, Any]] = {}
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
                iid = it.get("portId") or it.get("interfaceId") or it.get("id")
                if not iid:
                    continue
                sid = str(iid)
                if sid not in iface_ids:
                    iface_ids.append(sid)
                iname = str(
                    it.get("name")
                    or it.get("customName")
                    or it.get("alias")
                    or it.get("portName")
                    or it.get("interfaceName")
                    or it.get("ifName")
                    or it.get("displayName")
                    or it.get("ifname")
                    or it.get("port")
                    or sid
                )
                is_wan = _is_wan_interface(it, iname)
                iface = {
                    "id": sid,
                    "name": iname,
                    "port_id": str(it.get("portId") or ""),
                    "display_name": str(it.get("displayName") or ""),
                    "port_name": str(it.get("portName") or ""),
                    "interface_name": str(it.get("interfaceName") or ""),
                    "if_name": str(it.get("ifName") or it.get("ifname") or ""),
                    "alias": str(it.get("alias") or it.get("customName") or ""),
                    "mode": str(it.get("mode") or ""),
                    "type_raw": str(it.get("type") or ""),
                    "is_wan": is_wan,
                    "is_selectable": _is_selectable_lan_interface(it, iname, is_wan),
                }
                if sid in iface_map:
                    iface_map[sid] = _merge_iface(iface_map[sid], iface)
                else:
                    iface_map[sid] = iface
                    iface_list.append(iface_map[sid])
        if not iface_list:
            iface_list = [{"id": sid, "name": sid, "is_wan": False, "is_selectable": True} for sid in iface_ids]

        # Normalize duplicates in interface_ids while preserving first-seen order.
        uniq_iface_ids: List[str] = []
        seen_iids: set[str] = set()
        for iid in iface_ids:
            sid = _text(iid)
            if not sid or sid in seen_iids:
                continue
            seen_iids.add(sid)
            uniq_iface_ids.append(sid)

        catalog.append(
            {
                "name": name or id_tail,
                "label": label,
                "value": dev_id or mac or name,
                "mac": mac,
                "type": dtype,
                "model": model or None,
                "device_id": dev_id or None,
                "interface_ids": uniq_iface_ids,
                "interfaces": iface_list,
            }
        )

    return catalog
