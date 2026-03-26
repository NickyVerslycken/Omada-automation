from __future__ import annotations
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from omada_batch.services.planner import generate_plan
from omada_batch.storage.file_change_log import write_json_with_changelog


class BatchControllerMixin:
    def _set_batch_interface_selection_state(self, text: str) -> None:
        if hasattr(self, "lbl_batch_iface_state"):
            self.lbl_batch_iface_state.configure(text=text)

    def _clear_batch_interface_selection_ui(self) -> None:
        if not hasattr(self, "frm_batch_iface_inner"):
            return
        for child in self.frm_batch_iface_inner.winfo_children():
            child.destroy()
        self._batch_iface_catalog = []
        self._batch_iface_row_vars = {}
        self._batch_iface_apply_all_vars = []
        if hasattr(self, "canvas_batch_iface"):
            self.canvas_batch_iface.configure(scrollregion=self.canvas_batch_iface.bbox("all"))

    def _is_interface_selectable(self, iface: Dict[str, Any]) -> bool:
        if "is_selectable" in iface:
            return bool(iface.get("is_selectable"))
        if "is_wan" in iface:
            return not bool(iface.get("is_wan"))
        return True

    def _interface_label_with_state(self, iface: Dict[str, Any]) -> str:
        name = self._interface_display_name(iface)
        if not self._is_interface_selectable(iface):
            return f"{name}\n(WAN - disabled)"
        return name

    def _dedupe_batch_interface_catalog(self, interfaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        ordered_ids: List[str] = []
        for iface in interfaces or []:
            iid = str(iface.get("id") or "").strip()
            if not iid:
                continue
            normalized = dict(iface)
            normalized["id"] = iid
            if iid not in merged:
                merged[iid] = normalized
                ordered_ids.append(iid)
                continue
            current = merged[iid]
            for key, value in normalized.items():
                if key in ("is_wan", "is_selectable"):
                    continue
                if str(current.get(key) or "").strip():
                    continue
                if str(value or "").strip():
                    current[key] = value
            current["is_wan"] = bool(current.get("is_wan")) or bool(normalized.get("is_wan"))
            current["is_selectable"] = bool(current.get("is_selectable", True)) and bool(normalized.get("is_selectable", True))
        return [merged[iid] for iid in ordered_ids]

    def _resolve_batch_interface_catalog(self) -> List[Dict[str, Any]]:
        gateway = self._batch_gateway()
        if not gateway:
            return []

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
            base_ids = {str(i.get("id") or "").strip() for i in iface_catalog if str(i.get("id") or "").strip()}
            merged = self._merge_interface_catalog_names(iface_catalog, network_iface_catalog)
            iface_catalog = [it for it in merged if str(it.get("id") or "").strip() in base_ids]

        return self._dedupe_batch_interface_catalog(iface_catalog)

    def _collect_batch_interface_selection_mapping(self, *, require_selection: bool) -> Optional[Dict[int, List[str]]]:
        if not self.plan:
            return {}

        iface_catalog = list(getattr(self, "_batch_iface_catalog", []) or [])
        if not iface_catalog:
            return {p.index: [] for p in self.plan}

        if len(iface_catalog) == 1:
            iid = str(iface_catalog[0].get("id") or "").strip()
            if not iid or not self._is_interface_selectable(iface_catalog[0]):
                if require_selection:
                    messagebox.showwarning("Missing", "No selectable LAN interface is available.")
                    return None
                return {p.index: [] for p in self.plan}
            return {p.index: [iid] for p in self.plan}

        row_vars = getattr(self, "_batch_iface_row_vars", {}) or {}
        selectable_cols = [idx for idx, iface in enumerate(iface_catalog) if self._is_interface_selectable(iface)]
        if require_selection and not selectable_cols:
            messagebox.showwarning("Missing", "No selectable LAN interface is available. WAN interfaces are disabled.")
            return None
        mapping: Dict[int, List[str]] = {}
        for p in self.plan:
            vars_for_row: List[tk.BooleanVar] = list(row_vars.get(p.index) or [])
            ids: List[str] = []
            for col, (var, iface) in enumerate(zip(vars_for_row, iface_catalog)):
                if col not in selectable_cols:
                    continue
                if not var.get():
                    continue
                iid = str(iface.get("id") or "").strip()
                if iid:
                    ids.append(iid)
            if require_selection and not ids:
                messagebox.showwarning("Missing", f"Select at least one interface for {p.name}.")
                return None
            mapping[p.index] = ids
        return mapping

    def _refresh_batch_interface_selection_ui(self) -> None:
        if not hasattr(self, "frm_batch_iface_inner"):
            return

        self._clear_batch_interface_selection_ui()

        if not self.plan:
            self.plan_interface_ids = {}
            self._set_batch_interface_selection_state("Generate preview first to configure LAN interfaces.")
            return

        gateway = self._batch_gateway()
        if not gateway:
            self.plan_interface_ids = {p.index: [] for p in self.plan}
            self._set_batch_interface_selection_state(
                "DHCP disabled \u2014 no interface selection needed. Networks will be created without DHCP server."
            )
            return

        iface_catalog = self._resolve_batch_interface_catalog()
        self._batch_iface_catalog = iface_catalog

        if not iface_catalog:
            self.plan_interface_ids = {p.index: [] for p in self.plan}
            self._set_batch_interface_selection_state(
                "No LAN interfaces resolved for selected DHCP server. Networks will be created without interfaceIds."
            )
            ttk.Label(
                self.frm_batch_iface_inner,
                text="No LAN interfaces available for this DHCP server.",
            ).grid(row=0, column=0, sticky="w")
            return

        if len(iface_catalog) == 1:
            iid = str(iface_catalog[0].get("id") or "").strip()
            if not iid:
                self.plan_interface_ids = {p.index: [] for p in self.plan}
                self._set_batch_interface_selection_state("Single interface found but its interface ID is empty.")
                return
            iface_name = self._interface_display_name(iface_catalog[0])
            if self._is_interface_selectable(iface_catalog[0]):
                self.plan_interface_ids = {p.index: [iid] for p in self.plan}
                self._set_batch_interface_selection_state(
                    f"Single LAN interface detected ({iface_name}). It will be used for all planned networks."
                )
            else:
                self.plan_interface_ids = {p.index: [] for p in self.plan}
                self._set_batch_interface_selection_state(
                    f"Detected interface {iface_name}, but it is WAN and cannot be selected."
                )
            ttk.Label(
                self.frm_batch_iface_inner,
                text=self._interface_label_with_state(iface_catalog[0]),
            ).grid(row=0, column=0, sticky="w")
            return

        self._set_batch_interface_selection_state(
            "Select one or more LAN interfaces per network below. This replaces the old popup."
        )

        previous_mapping = dict(self.plan_interface_ids or {})
        row_vars: Dict[int, List[tk.BooleanVar]] = {}
        apply_all_vars: List[tk.BooleanVar] = []
        selectable_cols = [self._is_interface_selectable(iface) for iface in iface_catalog]

        table = ttk.Frame(self.frm_batch_iface_inner)
        table.grid(row=0, column=0, sticky="nw")

        ttk.Label(table, text="Network").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8))
        for c, iface in enumerate(iface_catalog, start=1):
            header_text = self._interface_label_with_state(iface)
            if selectable_cols[c - 1]:
                ttk.Label(table, text=header_text, justify="center").grid(row=0, column=c, padx=6, pady=(0, 8), sticky="n")
            else:
                tk.Label(table, text=header_text, justify="center", fg="#808080").grid(row=0, column=c, padx=6, pady=(0, 8), sticky="n")

        def _update_apply_all_states() -> None:
            for col, var in enumerate(apply_all_vars):
                if not selectable_cols[col]:
                    var.set(False)
                    continue
                var.set(all(vars_for_row[col].get() for vars_for_row in row_vars.values()))

        def _apply_all_changed(col: int) -> None:
            if not selectable_cols[col]:
                apply_all_vars[col].set(False)
                return
            val = apply_all_vars[col].get()
            for vars_for_row in row_vars.values():
                vars_for_row[col].set(val)

        ttk.Label(table, text="Apply to all").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 6))
        for col, _iface in enumerate(iface_catalog):
            var = tk.BooleanVar(value=selectable_cols[col])
            apply_all_vars.append(var)
            cb = ttk.Checkbutton(table, variable=var, command=lambda idx=col: _apply_all_changed(idx))
            if not selectable_cols[col]:
                cb.state(["disabled"])
            cb.grid(row=1, column=col + 1, padx=6, pady=(0, 6))

        for r, p in enumerate(self.plan, start=2):
            ttk.Label(table, text=f"{p.name} (VLAN {p.vlan_id})").grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)

            prev_ids = {str(i).strip() for i in (previous_mapping.get(p.index) or []) if str(i).strip()}
            vars_for_row: List[tk.BooleanVar] = []
            for col, iface in enumerate(iface_catalog):
                iid = str(iface.get("id") or "").strip()
                if not selectable_cols[col]:
                    is_selected = False
                else:
                    is_selected = iid in prev_ids if prev_ids else True
                var = tk.BooleanVar(value=is_selected)
                vars_for_row.append(var)
                cb = ttk.Checkbutton(table, variable=var, command=_update_apply_all_states)
                if not selectable_cols[col]:
                    cb.state(["disabled"])
                cb.grid(row=r, column=col + 1, padx=6, pady=2)
            row_vars[p.index] = vars_for_row

        self._batch_iface_row_vars = row_vars
        self._batch_iface_apply_all_vars = apply_all_vars
        _update_apply_all_states()

        mapping = self._collect_batch_interface_selection_mapping(require_selection=False)
        if mapping is not None:
            self.plan_interface_ids = mapping

        if hasattr(self, "canvas_batch_iface"):
            self.canvas_batch_iface.update_idletasks()
            self.canvas_batch_iface.configure(scrollregion=self.canvas_batch_iface.bbox("all"))

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
        self._refresh_batch_interface_selection_ui()
        self.btn_export_plan.configure(state="normal" if self.plan else "disabled")

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
        write_json_with_changelog(
            path,
            obj,
            details={"source": "BatchControllerMixin.on_export_plan", "record_count": len(obj)},
        )
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_push_plan(self) -> None:
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        if not self.plan:
            messagebox.showwarning("Missing", "Generate a preview first.")
            return

        gateway = self._batch_gateway()
        dhcp_enabled = gateway is not None

        if dhcp_enabled:
            mapping = self._collect_batch_interface_selection_mapping(require_selection=True)
            if mapping is None:
                self._set_batch_interface_selection_state("Please complete interface selection in this tab before pushing.")
                return
        else:
            mapping = {p.index: [] for p in self.plan}
        self.plan_interface_ids = mapping

        dhcp_text = "with DHCP enabled" if dhcp_enabled else "without DHCP (no DHCP server)"
        if not messagebox.askyesno("Confirm push", f"This will create {len(self.plan)} LAN networks {dhcp_text}.\n\nContinue?"):
            return

        def work():
            assert self.client
            site_id = self.selected_site_id
            assert site_id
            if gateway:
                gateway_name = str(gateway.get("name") or "")
                gateway_device = str(gateway.get("device_id") or gateway.get("value") or gateway_name)
            else:
                gateway_device = None

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
                    dhcp_enabled=dhcp_enabled,
                )
                if resp.get("errorCode") != 0:
                    raise RuntimeError(f"Create LAN failed for {p.name}: {resp.get('errorCode')} {resp.get('msg')}")
                self._q.put(("log", f"LAN created: {p.name} VLAN {p.vlan_id} {p.network.with_prefixlen}"))
                done += 1

            self._q.put(("progress", (total_steps, total_steps, "Done.")))
            self._q.put(("info", "Batch creation completed."))

        self._run_bg(work, disable_buttons=[self.btn_push])

    def _update_push_state(self) -> None:
        enabled = bool(self.client and self.selected_site_id and len(self.plan) > 0)
        self.btn_push.configure(state="normal" if enabled else "disabled")
