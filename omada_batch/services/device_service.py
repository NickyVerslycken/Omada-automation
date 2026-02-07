from __future__ import annotations

import re
from typing import Any, Dict, List


def _is_generic_interface_name(name: str, iid: str) -> bool:
    text = (name or "").strip().lower()
    sid = (iid or "").strip().lower()
    if not text:
        return True
    if sid and text == sid:
        return True
    if text.startswith("interface "):
        return True
    if sid and sid in text and ("[" in text or "(" in text):
        return True
    return False


def _clean_interface_name(name: str, iid: str) -> str:
    text = str(name or "").strip()
    sid = str(iid or "").strip()
    if not text:
        return ""
    if sid:
        text = re.sub(rf"\s*\[{re.escape(sid)}\]\s*$", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(rf"\s*\({re.escape(sid)}\)\s*$", "", text, flags=re.IGNORECASE).strip()
    return text


def interface_display_name(iface: Dict[str, str]) -> str:
    iid = str(iface.get("id") or "").strip()
    for key in ("display_name", "port_name", "interface_name", "if_name", "alias", "name"):
        raw = str(iface.get(key) or "").strip()
        if not raw:
            continue
        cleaned = _clean_interface_name(raw, iid)
        if cleaned and not _is_generic_interface_name(cleaned, iid):
            return cleaned
    name = _clean_interface_name(str(iface.get("name") or ""), iid)
    if name and name != iid:
        return name
    if iid:
        return iid
    return "Interface"


def merge_interface_catalog_names(base: List[Dict[str, Any]], extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for it in extra:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        copied = dict(it)
        copied["id"] = iid
        merged[iid] = copied

    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for it in base:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        seen.add(iid)
        merged_item: Dict[str, Any] = dict(it)
        merged_item["id"] = iid
        extra_item = merged.get(iid, {})
        for key, value in extra_item.items():
            if key == "id":
                continue
            cur = merged_item.get(key)
            if str(cur or "").strip():
                continue
            if str(value or "").strip():
                merged_item[key] = value
        current_best = interface_display_name(merged_item)
        incoming_best = interface_display_name(extra_item) if extra_item else ""
        if _is_generic_interface_name(current_best, iid) and incoming_best and not _is_generic_interface_name(incoming_best, iid):
            merged_item["name"] = incoming_best
        else:
            merged_item["name"] = current_best or str(merged_item.get("name") or iid)
        out.append(merged_item)

    for iid, extra_item in merged.items():
        if iid in seen:
            continue
        copied = dict(extra_item)
        copied["id"] = iid
        copied["name"] = interface_display_name(copied)
        out.append(copied)
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
