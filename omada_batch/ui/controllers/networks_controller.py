from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from tkinter import filedialog, messagebox

from omada_batch.services.device_service import (
    extract_interface_catalog_from_networks,
    interface_display_name,
    merge_interface_catalog_names,
)
from omada_batch.services.lan_service import build_interface_catalog
from omada_batch.storage.file_change_log import write_json_with_changelog


class NetworksControllerMixin:
    def on_refresh_gateways(self, silent_if_busy: bool = False) -> None:
        if not self.client or not self.selected_site_id:
            if not silent_if_busy:
                messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        if self._worker and self._worker.is_alive():
            if not silent_if_busy:
                messagebox.showwarning("Busy", "An operation is already running.")
            return

        def work():
            assert self.client
            assert self.selected_site_id
            self._q.put(("log", f"Fetching network devices for siteId={self.selected_site_id} ..."))
            devices = self.client.get_site_devices(self.selected_site_id)
            gateways = self._build_interface_catalog(devices)
            self._q.put(("gateways", gateways))

        self._run_bg(work, disable_buttons=[self.btn_refresh_gateways_current, self.btn_refresh_gateways_batch])

    def _build_interface_catalog(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return build_interface_catalog(devices)

    def _on_gateways(self, gateways) -> None:
        raw_gateways = gateways or []
        filtered: List[Dict[str, Any]] = []
        for gateway in raw_gateways:
            dtype_raw = gateway.get("type")
            try:
                dtype = int(dtype_raw) if dtype_raw is not None else None
            except Exception:
                dtype = None
            if dtype == 1:
                filtered.append(gateway)
                continue
            label_text = str(gateway.get("label") or "").strip().lower()
            if "[gateway]" in label_text:
                filtered.append(gateway)
        self.gateways = filtered
        dropped = len(raw_gateways) - len(filtered)
        if dropped > 0:
            self._q.put(("log", f"Skipped {dropped} non-gateway device(s) from DHCP server selection list."))
        self.current_gateway_filter_index = -1
        self.batch_gateway_index = -1

        if not self.gateways:
            self.cmb_gateways_current["values"] = []
            self.var_gateway_current.set("")
            self.cmb_gateways_current.configure(state="disabled")
            self.cmb_gateways_batch["values"] = []
            self.var_gateway_batch.set("")
            self.cmb_gateways_batch.configure(state="disabled")
            self._q.put(("log", "No DHCP servers loaded for selected site."))
            self._apply_network_filter()
            self._update_push_state()
            return

        labels = [str(g.get("label") or g.get("name") or "") for g in self.gateways]
        self.cmb_gateways_current["values"] = ["All"] + labels
        self.cmb_gateways_current.configure(state="readonly")
        self.cmb_gateways_current.current(0)
        self.current_gateway_filter_index = -1

        self.cmb_gateways_batch["values"] = labels
        self.cmb_gateways_batch.configure(state="readonly")
        self.cmb_gateways_batch.current(0)
        self.batch_gateway_index = 0

        self._apply_network_filter()
        self._q.put(("log", f"Loaded {len(self.gateways)} DHCP servers for selected site."))
        self._q.put(("log", f"Batch DHCP server={self._batch_gateway_name() or '(none)'}"))
        self._update_push_state()
        self._refresh_batch_interface_selection_ui()

    def _current_gateway(self) -> Optional[Dict[str, Any]]:
        idx = self.current_gateway_filter_index
        if idx < 0 or idx >= len(self.gateways):
            return None
        return self.gateways[idx]

    def _batch_gateway(self) -> Optional[Dict[str, Any]]:
        idx = self.batch_gateway_index
        if idx < 0 or idx >= len(self.gateways):
            return None
        return self.gateways[idx]

    def _batch_gateway_name(self) -> Optional[str]:
        gateway = self._batch_gateway()
        if not gateway:
            return None
        return str(gateway.get("name") or "").strip() or None

    def on_gateway_selected_current(self, _evt=None) -> None:
        idx = self.cmb_gateways_current.current()
        self.current_gateway_filter_index = idx - 1
        gateway = self._current_gateway()
        if gateway:
            self._q.put(("log", f"Current-tab DHCP filter={gateway.get('name') or gateway.get('label') or '(unnamed)'}"))
        else:
            self._q.put(("log", "Current-tab DHCP filter=All"))
        self._apply_network_filter()

    def on_gateway_selected_batch(self, _evt=None) -> None:
        idx = self.cmb_gateways_batch.current()
        self.batch_gateway_index = idx
        gateway = self._batch_gateway()
        if gateway:
            self._q.put(("log", f"Batch DHCP server={gateway.get('name') or gateway.get('label') or '(unnamed)'}"))
        self._update_push_state()
        self._refresh_batch_interface_selection_ui()

    def on_fetch_networks(self) -> None:
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return

        def work():
            self._q.put(("log", "Fetching LAN networks..."))
            nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
            self._q.put(("networks", nets))

        self._run_bg(work, disable_buttons=[self.btn_fetch_networks])

    def _on_networks(self, nets) -> None:
        self._networks_cache_all = nets or []
        self._apply_network_filter()

    def _apply_network_filter(self) -> None:
        selected = self._current_gateway()
        if selected is None:
            self._networks_cache = list(self._networks_cache_all)
        else:
            self._networks_cache = [n for n in self._networks_cache_all if self._network_matches_gateway(n, selected)]

        for item_id in self.tree_networks.get_children():
            self.tree_networks.delete(item_id)

        for network in self._networks_cache:
            name = network.get("name", "")
            vlan = network.get("vlan", "")
            gateway_subnet = network.get("gatewaySubnet", "")
            dhcp = network.get("dhcpSettingsVO") or {}
            pool = dhcp.get("ipRangePool") or []
            ds = pool[0].get("ipaddrStart") if pool else ""
            de = pool[0].get("ipaddrEnd") if pool else ""
            nid = network.get("id", "")
            self.tree_networks.insert("", "end", values=(name, vlan, gateway_subnet, ds, de, nid))

        total = len(self._networks_cache_all)
        shown = len(self._networks_cache)
        if selected is None:
            self.lbl_networks_state.configure(text=f"{shown} networks loaded.")
            self._q.put(("log", f"Loaded {shown} LAN networks."))
        else:
            gname = str(selected.get("name") or selected.get("label") or "(unnamed)")
            self.lbl_networks_state.configure(text=f"{shown}/{total} networks shown (DHCP server: {gname}).")
            self._q.put(("log", f"Filtered networks for DHCP server {gname}: {shown}/{total} shown."))

    def _on_network_selected(self, _evt=None) -> None:
        sel = self.tree_networks.selection()
        if not sel:
            return
        idx = self.tree_networks.index(sel[0])
        if idx < 0 or idx >= len(self._networks_cache):
            return
        raw = self._networks_cache[idx]
        self.txt_network_raw.delete("1.0", "end")
        self.txt_network_raw.insert("end", json.dumps(raw, indent=2))

    def on_export_networks(self) -> None:
        if not self._networks_cache:
            messagebox.showinfo("Nothing", "No networks loaded.")
            return
        path = filedialog.asksaveasfilename(
            title="Export LAN networks JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        write_json_with_changelog(
            path,
            self._networks_cache,
            details={"source": "NetworksControllerMixin.on_export_networks", "record_count": len(self._networks_cache)},
        )
        messagebox.showinfo("Exported", f"Saved to {path}")

    def _network_matches_gateway(self, network: Dict[str, Any], gateway: Dict[str, Any]) -> bool:
        if not isinstance(network, dict):
            return False

        def _variants(v: Any) -> set[str]:
            raw = str(v or "").strip().lower()
            if not raw:
                return set()
            compact = "".join(ch for ch in raw if ch.isalnum())
            out = {raw}
            if compact and compact != raw:
                out.add(compact)
            return out

        gateway_tokens: set[str] = set()
        for v in (
            gateway.get("device_id"),
            gateway.get("value"),
            gateway.get("name"),
            gateway.get("label"),
            gateway.get("mac"),
        ):
            gateway_tokens.update(_variants(v))

        net_tokens: set[str] = set()
        for v in (
            network.get("gateway"),
            network.get("gatewayId"),
            network.get("gatewayDeviceId"),
            network.get("gatewayName"),
            network.get("gatewayMac"),
            network.get("dhcpServer"),
            network.get("dhcpServerId"),
            network.get("assignIpDevice"),
            network.get("assignIpDeviceId"),
            network.get("assignIpDeviceMac"),
            network.get("serverId"),
            network.get("deviceMac"),
            network.get("mac"),
        ):
            net_tokens.update(_variants(v))
        dhcp = network.get("dhcpSettingsVO") or {}
        if isinstance(dhcp, dict):
            for v in (
                dhcp.get("gateway"),
                dhcp.get("gatewayId"),
                dhcp.get("gatewayMac"),
                dhcp.get("dhcpServer"),
                dhcp.get("dhcpServerId"),
                dhcp.get("assignIpDevice"),
                dhcp.get("assignIpDeviceId"),
                dhcp.get("assignIpDeviceMac"),
                dhcp.get("deviceMac"),
                dhcp.get("mac"),
            ):
                net_tokens.update(_variants(v))
        dhcp2 = network.get("dhcpSettings") or {}
        if isinstance(dhcp2, dict):
            for v in (
                dhcp2.get("gateway"),
                dhcp2.get("gatewayId"),
                dhcp2.get("gatewayMac"),
                dhcp2.get("dhcpServer"),
                dhcp2.get("dhcpServerId"),
                dhcp2.get("assignIpDevice"),
                dhcp2.get("assignIpDeviceId"),
                dhcp2.get("assignIpDeviceMac"),
                dhcp2.get("deviceMac"),
                dhcp2.get("mac"),
            ):
                net_tokens.update(_variants(v))

        if gateway_tokens and net_tokens and (gateway_tokens & net_tokens):
            return True

        gateway_ifaces = {str(i).strip() for i in (gateway.get("interface_ids") or []) if str(i).strip()}
        net_ifaces = (
            {str(i).strip() for i in (network.get("interfaceIds") or []) if str(i).strip()}
            if isinstance(network.get("interfaceIds"), list)
            else set()
        )
        if gateway_ifaces and net_ifaces and (gateway_ifaces & net_ifaces):
            return True

        return False

    def _interface_display_name(self, iface: Dict[str, str]) -> str:
        return interface_display_name(iface)

    def _merge_interface_catalog_names(self, base: List[Dict[str, str]], extra: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return merge_interface_catalog_names(base, extra)

    def _get_interface_catalog_from_networks(self, gateway: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        source = self._networks_cache_all
        if gateway is not None:
            source = [n for n in self._networks_cache_all if self._network_matches_gateway(n, gateway)]
        catalog = extract_interface_catalog_from_networks(source)
        if catalog:
            return catalog
        if self.client and self.selected_site_id:
            try:
                nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
                if gateway is not None:
                    filtered = [n for n in nets if self._network_matches_gateway(n, gateway)]
                    nets = filtered
                return extract_interface_catalog_from_networks(nets)
            except Exception as exc:
                self._q.put(("log", f"WARNING: Could not fetch interfaceIds from networks: {exc}"))
        return []
