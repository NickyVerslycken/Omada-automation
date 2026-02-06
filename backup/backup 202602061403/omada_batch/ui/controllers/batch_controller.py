from __future__ import annotations

import json
from typing import Dict, List

from tkinter import filedialog, messagebox

from omada_batch.services.planner import generate_plan


class BatchControllerMixin:
    def on_generate_preview(self) -> None:
        try:
            plans, warnings = generate_plan(
                name_prefix=self.var_name_prefix.get().strip() or "LAN",
                start_ip=self.var_start_ip.get().strip(),
                prefix_len=int(self.var_prefix.get()),
                count=int(self.var_count.get()),
                start_vlan=int(self.var_start_vlan.get()),
                dhcp_start_offset=int(self.var_dhcp_start_off.get()),
                dhcp_end_offset=int(self.var_dhcp_end_off.get()),
            )
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.plan = plans
        for item_id in self.tree_plan.get_children():
            self.tree_plan.delete(item_id)

        for p in self.plan:
            self.tree_plan.insert(
                "",
                "end",
                values=(p.index, p.name, p.vlan_id, p.network.with_prefixlen, str(p.gateway), str(p.dhcp_start), str(p.dhcp_end)),
            )

        if warnings:
            messagebox.showwarning("Plan warnings", "\n".join(warnings))
            for warning in warnings:
                self._log(f"WARNING: {warning}")

        self._log(f"Preview generated: {len(self.plan)} networks.")
        self._update_push_state()
        self.btn_export_plan.config(state="normal" if self.plan else "disabled")

    def on_export_plan(self) -> None:
        if not self.plan:
            messagebox.showinfo("Nothing", "No preview generated.")
            return
        path = filedialog.asksaveasfilename(
            title="Export preview JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        obj = [
            {
                "index": p.index,
                "name": p.name,
                "vlan": p.vlan_id,
                "gatewaySubnet_candidates": [
                    f"{p.gateway}/{p.network.prefixlen}",
                    f"{p.network.network_address}/{p.network.prefixlen}",
                    f"{p.gateway}/{p.network.netmask}",
                    f"{p.network.network_address}/{p.network.netmask}",
                ],
                "dhcpStart": str(p.dhcp_start),
                "dhcpEnd": str(p.dhcp_end),
            }
            for p in self.plan
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_push_plan(self) -> None:
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        gateway = self._batch_gateway()
        if not gateway:
            messagebox.showwarning("Missing", "Select a DHCP server for this site first (Refresh DHCP servers).")
            return
        if not self.plan:
            messagebox.showwarning("Missing", "Generate a preview first.")
            return

        iface_catalog = list(gateway.get("interfaces") or [])
        gateway_interface_ids = [str(i) for i in (gateway.get("interface_ids") or []) if i]
        if not iface_catalog and gateway_interface_ids:
            iface_catalog = [{"id": i, "name": i} for i in gateway_interface_ids]

        network_iface_catalog: List[Dict[str, str]] = []
        if not iface_catalog or any(str(i.get("name") or "").strip() == str(i.get("id") or "").strip() for i in iface_catalog):
            network_iface_catalog = self._get_interface_catalog_from_networks(gateway)

        if not iface_catalog:
            iface_catalog = network_iface_catalog
            if iface_catalog:
                self._q.put(("log", "Using interfaces discovered from existing LAN networks."))
        elif network_iface_catalog:
            iface_catalog = self._merge_interface_catalog_names(iface_catalog, network_iface_catalog)

        if not iface_catalog:
            self._q.put(("log", "WARNING: No LAN interfaces resolved for selected DHCP server. Creating networks without interfaceIds."))
            self.plan_interface_ids = {p.index: [] for p in self.plan}
        elif len(iface_catalog) == 1:
            iid = iface_catalog[0].get("id")
            if not iid:
                messagebox.showwarning("Missing", "No LAN interface ID available.")
                return
            self.plan_interface_ids = {p.index: [str(iid)] for p in self.plan}
        else:
            mapping = self._prompt_interface_selection(iface_catalog)
            if mapping is None:
                return
            self.plan_interface_ids = mapping

        if not messagebox.askyesno("Confirm push", f"This will create {len(self.plan)} LAN networks.\n\nContinue?"):
            return

        def work():
            assert self.client
            site_id = self.selected_site_id
            assert site_id
            gateway_name = str(gateway.get("name") or "")
            assert gateway_name
            gateway_device = str(gateway.get("device_id") or gateway.get("value") or gateway_name)

            total_steps = len(self.plan)
            done = 0
            for p in self.plan:
                self._q.put(("progress", (done, total_steps, f"Creating {p.name} (VLAN {p.vlan_id})...")))
                iface_ids = self.plan_interface_ids.get(p.index, [])
                resp = self.client.create_lan_network(
                    site_id,
                    p,
                    gateway_device=gateway_device,
                    interface_ids=(iface_ids or None),
                )
                if resp.get("errorCode") != 0:
                    raise RuntimeError(f"Create LAN failed for {p.name}: {resp.get('errorCode')} {resp.get('msg')}")
                self._q.put(("log", f"LAN created: {p.name} VLAN {p.vlan_id} {p.network.with_prefixlen}"))
                done += 1

            self._q.put(("progress", (total_steps, total_steps, "Done.")))
            self._q.put(("info", "Batch creation completed."))

        self._run_bg(work, disable_buttons=[self.btn_push])

    def _update_push_state(self) -> None:
        enabled = bool(self.client and self.selected_site_id and self._batch_gateway() and len(self.plan) > 0)
        self.btn_push.config(state="normal" if enabled else "disabled")
