from __future__ import annotations

from typing import Any, Dict, List


def interface_display_name(iface: Dict[str, str]) -> str:
    iid = str(iface.get("id") or "").strip()
    name = str(iface.get("name") or "").strip()
    if name and name != iid:
        return name
    if iid:
        return f"Interface {iid}"
    return "Interface"


def merge_interface_catalog_names(base: List[Dict[str, str]], extra: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for it in extra:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        merged[iid] = {"id": iid, "name": str(it.get("name") or "").strip() or iid}

    out: List[Dict[str, str]] = []
    for it in base:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        cur_name = str(it.get("name") or "").strip()
        if (not cur_name or cur_name == iid) and iid in merged:
            cur_name = merged[iid].get("name") or cur_name
        out.append({"id": iid, "name": cur_name or iid})
    return out


def extract_interface_catalog_from_networks(networks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    iface_map: Dict[str, str] = {}

    def add_iface(iid: Any, name: Any = ""):
        sid = str(iid or "").strip()
        if not sid:
            return
        sname = str(name or "").strip()
        cur = iface_map.get(sid, "")
        if not cur or cur == sid:
            iface_map[sid] = sname or cur or sid

    for n in networks:
        if not isinstance(n, dict):
            continue
        ids = n.get("interfaceIds")
        names = n.get("interfaceNames")
        if isinstance(ids, list):
            for idx, iid in enumerate(ids):
                nm = ""
                if isinstance(names, list) and idx < len(names):
                    nm = names[idx]
                add_iface(iid, nm)

        for key in ("interfaces", "interfaceList", "lanInterfaces", "portList"):
            raw = n.get(key)
            if not isinstance(raw, list):
                continue
            for it in raw:
                if not isinstance(it, dict):
                    continue
                iid = it.get("id") or it.get("interfaceId") or it.get("ifId")
                iname = (
                    it.get("name")
                    or it.get("ifName")
                    or it.get("displayName")
                    or it.get("interfaceName")
                    or it.get("port")
                    or ""
                )
                add_iface(iid, iname)

        add_iface(n.get("interfaceId"), n.get("interfaceName") or n.get("ifName"))

    return [{"id": iid, "name": str(name or iid)} for iid, name in iface_map.items()]
