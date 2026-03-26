from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from omada_batch.services.planner import generate_vlan_plan


class VlanBatchControllerMixin:
    """Controller logic for the Batch Create > VLANs sub-page."""

    # ── Gateway selection for VLAN tab ────────────────────────────

    def on_vlan_gateway_selected(self, _evt=None) -> None:
        idx = self.cmb_vlan_gateway.current()
        self._vlan_gateway_index = idx
        if idx < 0 or idx >= len(self.gateways):
            self._q.put(("log", "VLAN gateway selection: none"))
        else:
            gw = self.gateways[idx]
            self._q.put(("log", f"VLAN gateway={gw.get('name') or gw.get('label') or '(unnamed)'}"))
        self._update_vlan_push_state()
        self._refresh_vlan_port_selection_ui()

    def _vlan_selected_gateway(self) -> Optional[Dict[str, Any]]:
        idx = getattr(self, "_vlan_gateway_index", -1)
        if idx < 0 or idx >= len(self.gateways):
            return None
        return self.gateways[idx]

    # ── Populate gateway dropdown when gateways refresh ───────────

    def _on_vlan_gateways_refreshed(self) -> None:
        """Called from _on_gateways after gateway list updates."""
        if not self.gateways:
            self.cmb_vlan_gateway["values"] = []
            self.var_vlan_gateway.set("")
            self.cmb_vlan_gateway.configure(state="disabled")
            return
        labels = [str(g.get("label") or g.get("name") or "") for g in self.gateways]
        self.cmb_vlan_gateway["values"] = labels
        self.cmb_vlan_gateway.configure(state="readonly")
        if labels:
            self.cmb_vlan_gateway.current(0)
            self._vlan_gateway_index = 0
        self._refresh_vlan_port_selection_ui()
        self._update_vlan_push_state()

    # ── Port catalog from selected gateway ────────────────────────

    def _resolve_vlan_port_catalog(self) -> List[Dict[str, Any]]:
        gateway = self._vlan_selected_gateway()
        if not gateway:
            return []
        interfaces = list(gateway.get("interfaces") or [])
        if not interfaces:
            iface_ids = [str(i) for i in (gateway.get("interface_ids") or []) if i]
            interfaces = [{"id": i, "name": i} for i in iface_ids]
        return interfaces

    def _is_vlan_port_selectable(self, port: Dict[str, Any]) -> bool:
        if "is_selectable" in port:
            return bool(port.get("is_selectable"))
        if "is_wan" in port:
            return not bool(port.get("is_wan"))
        return True

    def _vlan_port_label(self, port: Dict[str, Any]) -> str:
        name = self._interface_display_name(port)
        if not self._is_vlan_port_selectable(port):
            return f"{name}\n(not selectable)"
        return name

    # ── Port selection matrix UI ──────────────────────────────────

    def _clear_vlan_port_selection_ui(self) -> None:
        if not hasattr(self, "frm_vlan_port_inner"):
            return
        for child in self.frm_vlan_port_inner.winfo_children():
            child.destroy()
        self._vlan_port_catalog = []
        self._vlan_port_row_vars = {}
        self._vlan_port_apply_all_vars = []
        if hasattr(self, "canvas_vlan_port"):
            self.canvas_vlan_port.configure(scrollregion=self.canvas_vlan_port.bbox("all"))

    def _refresh_vlan_port_selection_ui(self) -> None:
        if not hasattr(self, "frm_vlan_port_inner"):
            return
        self._clear_vlan_port_selection_ui()

        vlan_plan = getattr(self, "vlan_plan", [])
        if not vlan_plan:
            self.vlan_plan_port_ids = {}
            self.lbl_vlan_port_state.configure(text="Generate preview first to configure port mapping.")
            return

        gateway = self._vlan_selected_gateway()
        if not gateway:
            self.vlan_plan_port_ids = {}
            self.lbl_vlan_port_state.configure(text="Select a gateway device to configure port mapping.")
            return

        port_catalog = self._resolve_vlan_port_catalog()
        self._vlan_port_catalog = port_catalog

        if not port_catalog:
            self.vlan_plan_port_ids = {}
            self.lbl_vlan_port_state.configure(text="No ports resolved for selected gateway.")
            return

        if len(port_catalog) == 1:
            pid = str(port_catalog[0].get("id") or "").strip()
            pname = self._interface_display_name(port_catalog[0])
            if pid and self._is_vlan_port_selectable(port_catalog[0]):
                self.vlan_plan_port_ids = {p.index: [pid] for p in vlan_plan}
                self.lbl_vlan_port_state.configure(text=f"Single port detected ({pname}). It will be used for all VLANs.")
            else:
                self.vlan_plan_port_ids = {}
                self.lbl_vlan_port_state.configure(text=f"Detected port {pname}, but it is not selectable.")
            ttk.Label(self.frm_vlan_port_inner, text=self._vlan_port_label(port_catalog[0])).grid(row=0, column=0, sticky="w")
            return

        self.lbl_vlan_port_state.configure(text="Select gateway ports per VLAN below.")

        previous_mapping = dict(getattr(self, "vlan_plan_port_ids", {}) or {})
        row_vars: Dict[int, List[tk.BooleanVar]] = {}
        apply_all_vars: List[tk.BooleanVar] = []
        selectable_cols = [self._is_vlan_port_selectable(p) for p in port_catalog]

        table = ttk.Frame(self.frm_vlan_port_inner)
        table.grid(row=0, column=0, sticky="nw")

        ttk.Label(table, text="VLAN").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8))
        for c, port in enumerate(port_catalog, start=1):
            header_text = self._vlan_port_label(port)
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
        for col, _port in enumerate(port_catalog):
            var = tk.BooleanVar(value=selectable_cols[col])
            apply_all_vars.append(var)
            cb = ttk.Checkbutton(table, variable=var, command=lambda idx=col: _apply_all_changed(idx))
            if not selectable_cols[col]:
                cb.state(["disabled"])
            cb.grid(row=1, column=col + 1, padx=6, pady=(0, 6))

        for r, p in enumerate(vlan_plan, start=2):
            ttk.Label(table, text=f"{p.name} (VLAN {p.vlan_id})").grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)
            prev_ids = {str(i).strip() for i in (previous_mapping.get(p.index) or []) if str(i).strip()}
            vars_for_row: List[tk.BooleanVar] = []
            for col, port in enumerate(port_catalog):
                pid = str(port.get("id") or "").strip()
                if not selectable_cols[col]:
                    is_selected = False
                else:
                    is_selected = pid in prev_ids if prev_ids else True
                var = tk.BooleanVar(value=is_selected)
                vars_for_row.append(var)
                cb = ttk.Checkbutton(table, variable=var, command=_update_apply_all_states)
                if not selectable_cols[col]:
                    cb.state(["disabled"])
                cb.grid(row=r, column=col + 1, padx=6, pady=2)
            row_vars[p.index] = vars_for_row

        self._vlan_port_row_vars = row_vars
        self._vlan_port_apply_all_vars = apply_all_vars
        _update_apply_all_states()

        mapping = self._collect_vlan_port_selection_mapping(require_selection=False)
        if mapping is not None:
            self.vlan_plan_port_ids = mapping

        if hasattr(self, "canvas_vlan_port"):
            self.canvas_vlan_port.update_idletasks()
            self.canvas_vlan_port.configure(scrollregion=self.canvas_vlan_port.bbox("all"))

    def _collect_vlan_port_selection_mapping(self, *, require_selection: bool) -> Optional[Dict[int, List[str]]]:
        vlan_plan = getattr(self, "vlan_plan", [])
        if not vlan_plan:
            return {}

        port_catalog = list(getattr(self, "_vlan_port_catalog", []) or [])
        if not port_catalog:
            return {p.index: [] for p in vlan_plan}

        if len(port_catalog) == 1:
            pid = str(port_catalog[0].get("id") or "").strip()
            if not pid or not self._is_vlan_port_selectable(port_catalog[0]):
                if require_selection:
                    messagebox.showwarning("Missing", "No selectable port is available.")
                    return None
                return {p.index: [] for p in vlan_plan}
            return {p.index: [pid] for p in vlan_plan}

        row_vars = getattr(self, "_vlan_port_row_vars", {}) or {}
        selectable_cols = [idx for idx, port in enumerate(port_catalog) if self._is_vlan_port_selectable(port)]
        if require_selection and not selectable_cols:
            messagebox.showwarning("Missing", "No selectable LAN port is available for this gateway.")
            return None
        mapping: Dict[int, List[str]] = {}
        for p in vlan_plan:
            vars_for_row: List[tk.BooleanVar] = list(row_vars.get(p.index) or [])
            ids: List[str] = []
            for col, (var, port) in enumerate(zip(vars_for_row, port_catalog)):
                if col not in selectable_cols:
                    continue
                if not var.get():
                    continue
                pid = str(port.get("id") or "").strip()
                if pid:
                    ids.append(pid)
            if require_selection and not ids:
                messagebox.showwarning("Missing", f"Select at least one port for {p.name}.")
                return None
            mapping[p.index] = ids
        return mapping

    # ── Preview / Push ────────────────────────────────────────────

    def on_vlan_generate_preview(self) -> None:
        try:
            plans, warnings = generate_vlan_plan(
                name_prefix=self.var_vlan_name_prefix.get().strip() or "VLAN",
                start_vlan=int(self.var_vlan_start_vlan.get()),
                count=int(self.var_vlan_count.get()),
            )
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.vlan_plan = plans
        for item_id in self.tree_vlan_plan.get_children():
            self.tree_vlan_plan.delete(item_id)

        for p in self.vlan_plan:
            self.tree_vlan_plan.insert("", "end", values=(p.index, p.name, p.vlan_id))

        if warnings:
            messagebox.showwarning("Plan warnings", "\n".join(warnings))
            for w in warnings:
                self._log(f"WARNING: {w}")

        self._log(f"VLAN preview generated: {len(self.vlan_plan)} VLANs.")
        self._update_vlan_push_state()
        self._refresh_vlan_port_selection_ui()

    def on_vlan_push_plan(self) -> None:
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        vlan_plan = getattr(self, "vlan_plan", [])
        if not vlan_plan:
            messagebox.showwarning("Missing", "Generate a preview first.")
            return
        gateway = self._vlan_selected_gateway()
        if not gateway:
            messagebox.showwarning("Missing", "Select a gateway device.")
            return

        mapping = self._collect_vlan_port_selection_mapping(require_selection=True)
        if mapping is None:
            self.lbl_vlan_port_state.configure(text="Please complete port selection before pushing.")
            return
        self.vlan_plan_port_ids = mapping

        device_mac = str(gateway.get("mac") or "").strip()
        if not device_mac:
            messagebox.showwarning("Missing", "Selected gateway has no MAC address.")
            return

        device_type_raw = gateway.get("type")
        try:
            device_type = int(device_type_raw) if device_type_raw is not None else 1
        except Exception:
            device_type = 1

        if not messagebox.askyesno(
            "Confirm push",
            f"This will create {len(vlan_plan)} VLAN networks (no DHCP) on gateway {device_mac}.\n\nContinue?",
        ):
            return

        def work():
            assert self.client
            site_id = self.selected_site_id
            assert site_id
            total_steps = len(vlan_plan)
            done = 0
            for p in vlan_plan:
                self._q.put(("vlan_progress", (done, total_steps, f"Creating {p.name} (VLAN {p.vlan_id})...")))
                port_ids = self.vlan_plan_port_ids.get(p.index, [])
                resp = self.client.create_vlan_network(
                    site_id,
                    p,
                    device_mac=device_mac,
                    device_type=device_type,
                    port_ids=port_ids,
                )
                if resp.get("errorCode") != 0:
                    raise RuntimeError(f"Create VLAN failed for {p.name}: {resp.get('errorCode')} {resp.get('msg')}")
                self._q.put(("log", f"VLAN created: {p.name} VLAN {p.vlan_id}"))
                done += 1

            self._q.put(("vlan_progress", (total_steps, total_steps, "Done.")))
            self._q.put(("info", "Batch VLAN creation completed."))

        self._run_bg(work, disable_buttons=[self.btn_vlan_push])

    def _update_vlan_push_state(self) -> None:
        vlan_plan = getattr(self, "vlan_plan", [])
        gateway = self._vlan_selected_gateway()
        enabled = bool(self.client and self.selected_site_id and len(vlan_plan) > 0 and gateway is not None)
        self.btn_vlan_push.configure(state="normal" if enabled else "disabled")
