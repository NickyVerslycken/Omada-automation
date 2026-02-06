from __future__ import annotations

import json
import queue
import threading
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from omada_batch.api.omada_client import OmadaOpenApiClient
from omada_batch.models.lan import PlannedLan
from omada_batch.services.device_service import (
    extract_interface_catalog_from_networks,
    interface_display_name,
    merge_interface_catalog_names,
)
from omada_batch.services.lan_service import build_interface_catalog
from omada_batch.services.planner import generate_plan
from omada_batch.services.profile_service import normalize_profile
from omada_batch.storage.profile_store import ProfileStore
from omada_batch.ui.dialogs.interface_selector import prompt_interface_selection


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Omada LAN/VLAN Batch Manager (IPv4) — v4")
        self.geometry("1100x720")

        self.client: Optional[OmadaOpenApiClient] = None
        self.sites: List[Dict[str, Any]] = []
        self.gateways: List[Dict[str, str]] = []
        self.selected_site_id: Optional[str] = None
        self.selected_gateway_name: Optional[str] = None
        self.selected_gateway_value: Optional[str] = None
        self.selected_gateway_label: Optional[str] = None
        self.selected_gateway_type: Optional[int] = None
        self.selected_gateway_device_id: Optional[str] = None
        self.selected_gateway_interface_ids: List[str] = []
        self.selected_gateway_interfaces: List[Dict[str, str]] = []
        self.plan: List[PlannedLan] = []
        self.plan_interface_ids: Dict[int, List[str]] = {}
        self.profile_store = ProfileStore()
        self.controller_profiles_path = self.profile_store.path
        self.controller_profiles: List[Dict[str, Any]] = []

        self._q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None

        self._load_controller_profiles()
        self._build_ui()
        self._refresh_controller_profile_combo()
        self.after(150, self._poll_queue)

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_conn = ttk.Frame(nb)
        self.tab_current = ttk.Frame(nb)
        self.tab_batch = ttk.Frame(nb)
        self.tab_logs = ttk.Frame(nb)

        nb.add(self.tab_conn, text="Connection")
        nb.add(self.tab_current, text="Current LAN Networks")
        nb.add(self.tab_batch, text="Batch Create")
        nb.add(self.tab_logs, text="Logs")

        self._build_connection_tab()
        self._build_current_tab()
        self._build_batch_tab()
        self._build_logs_tab()

    def _build_connection_tab(self):
        frame = ttk.Frame(self.tab_conn, padding=10)
        frame.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frame, text="Saved controller profiles").grid(row=row, column=0, sticky="w")
        self.var_controller_profile = tk.StringVar()
        self.cmb_controller_profiles = ttk.Combobox(frame, textvariable=self.var_controller_profile, width=55, state="readonly")
        self.cmb_controller_profiles.grid(row=row, column=1, sticky="w")
        self.cmb_controller_profiles.bind("<<ComboboxSelected>>", self.on_controller_profile_selected)
        self.btn_remove_profile = ttk.Button(frame, text="Remove profile", command=self.on_remove_controller_profile)
        self.btn_remove_profile.grid(row=row, column=2, sticky="w")
        row += 1

        profile_actions = ttk.Frame(frame)
        profile_actions.grid(row=row, column=1, sticky="w", pady=(4, 0))
        self.btn_save_profile = ttk.Button(profile_actions, text="Save current profile", command=self.on_save_controller_profile)
        self.btn_save_profile.pack(side="left")
        self.btn_import_profiles = ttk.Button(profile_actions, text="Import profiles...", command=self.on_import_controller_profiles)
        self.btn_import_profiles.pack(side="left", padx=(8, 0))
        self.btn_export_profiles = ttk.Button(profile_actions, text="Export profiles...", command=self.on_export_controller_profiles)
        self.btn_export_profiles.pack(side="left", padx=(8, 0))
        row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1

        ttk.Label(frame, text="Controller base URL (example: https://omada:8043)").grid(row=row, column=0, sticky="w")
        self.var_url = tk.StringVar(value="https://")
        ttk.Entry(frame, textvariable=self.var_url, width=55).grid(row=row, column=1, sticky="w")
        self.var_verify_ssl = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Verify SSL certificate", variable=self.var_verify_ssl).grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frame, text="OpenAPI Client ID").grid(row=row, column=0, sticky="w")
        self.var_client_id = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_client_id, width=55).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frame, text="OpenAPI Client Secret").grid(row=row, column=0, sticky="w")
        self.var_client_secret = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_client_secret, width=55, show="•").grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frame, text="(Optional) Omada ID (omadacId) - auto-detected via /api/info").grid(row=row, column=0, sticky="w")
        self.var_omada_id = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_omada_id, width=55).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1

        self.btn_connect = ttk.Button(frame, text="Connect", command=self.on_connect)
        self.btn_connect.grid(row=row, column=0, sticky="w")

        self.lbl_conn_state = ttk.Label(frame, text="Not connected")
        self.lbl_conn_state.grid(row=row, column=1, sticky="w")

        self.btn_disconnect = ttk.Button(frame, text="Disconnect", command=self.on_disconnect, state="disabled")
        self.btn_disconnect.grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frame, text="Site").grid(row=row, column=0, sticky="w", pady=(10, 0))
        self.var_site = tk.StringVar()
        self.cmb_sites = ttk.Combobox(frame, textvariable=self.var_site, width=52, state="readonly")
        self.cmb_sites.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.cmb_sites.bind("<<ComboboxSelected>>", self.on_site_selected)

        self.btn_refresh_sites = ttk.Button(frame, text="Refresh sites", command=self.on_refresh_sites, state="disabled")
        self.btn_refresh_sites.grid(row=row, column=2, sticky="w", pady=(10, 0))
        row += 1

        ttk.Label(frame, text="DHCP server").grid(row=row, column=0, sticky="w", pady=(10, 0))
        self.var_gateway = tk.StringVar()
        self.cmb_gateways = ttk.Combobox(frame, textvariable=self.var_gateway, width=52, state="disabled")
        self.cmb_gateways.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.cmb_gateways.bind("<<ComboboxSelected>>", self.on_gateway_selected)

        self.btn_refresh_gateways = ttk.Button(frame, text="Refresh DHCP servers", command=self.on_refresh_gateways, state="disabled")
        self.btn_refresh_gateways.grid(row=row, column=2, sticky="w", pady=(10, 0))

        for c in range(3):
            frame.grid_columnconfigure(c, weight=1 if c == 1 else 0)

    def _load_controller_profiles(self):
        self.controller_profiles = []
        items = self.profile_store.load_raw()
        for idx, item in enumerate(items):
            prof = self._normalize_controller_profile(item, index=idx)
            if prof:
                self.controller_profiles.append(prof)

    def _save_controller_profiles(self):
        self.profile_store.save_raw(self.controller_profiles)

    def _normalize_controller_profile(self, item: Any, index: int = 0) -> Optional[Dict[str, Any]]:
        return normalize_profile(item, index=index)

    def _controller_host_key(self, base_url: str) -> str:
        text = str(base_url or "").strip()
        if not text:
            return ""
        parsed = urlparse(text if "://" in text else f"//{text}")
        host = (parsed.hostname or "").strip().lower()
        if host:
            return host
        rough = text.split("://", 1)[-1].split("/", 1)[0].strip().lower()
        if ":" in rough:
            rough = rough.split(":", 1)[0]
        return rough

    def _refresh_controller_profile_combo(self):
        if not hasattr(self, "cmb_controller_profiles"):
            return
        values = [f"{p.get('name','(unnamed)')}  [{p.get('base_url','')}]" for p in self.controller_profiles]
        self.cmb_controller_profiles["values"] = values
        if not values:
            self.var_controller_profile.set("")
            return
        idx = self.cmb_controller_profiles.current()
        if idx < 0 or idx >= len(values):
            self.cmb_controller_profiles.current(0)
            self.on_controller_profile_selected()

    def _selected_controller_profile_index(self) -> int:
        if not hasattr(self, "cmb_controller_profiles"):
            return -1
        idx = self.cmb_controller_profiles.current()
        if idx < 0 or idx >= len(self.controller_profiles):
            return -1
        return idx

    def on_controller_profile_selected(self, _evt=None):
        idx = self._selected_controller_profile_index()
        if idx < 0:
            return
        p = self.controller_profiles[idx]
        self.var_url.set(str(p.get("base_url") or "https://"))
        self.var_client_id.set(str(p.get("client_id") or ""))
        self.var_client_secret.set(str(p.get("client_secret") or ""))
        self.var_verify_ssl.set(bool(p.get("verify_ssl")))
        self.var_omada_id.set(str(p.get("omada_id") or ""))

    def on_save_controller_profile(self):
        base_url = self.var_url.get().strip()
        client_id = self.var_client_id.get().strip()
        client_secret = self.var_client_secret.get().strip()
        verify_ssl = bool(self.var_verify_ssl.get())
        omada_id = self.var_omada_id.get().strip()
        host_key = self._controller_host_key(base_url)

        if not base_url or base_url == "https://":
            messagebox.showwarning("Missing", "Please enter the controller base URL first.")
            return
        if not client_id or not client_secret:
            messagebox.showwarning("Missing", "Please enter Client ID and Client Secret first.")
            return

        default_name = base_url.replace("https://", "").replace("http://", "") or "Controller"
        selected_idx = self._selected_controller_profile_index()
        if selected_idx >= 0:
            selected = self.controller_profiles[selected_idx]
            if self._controller_host_key(str(selected.get("base_url") or "")) == host_key:
                selected_name = str(selected.get("name") or "").strip()
                if selected_name:
                    default_name = selected_name
        if host_key and default_name == (base_url.replace("https://", "").replace("http://", "") or "Controller"):
            for p in self.controller_profiles:
                if self._controller_host_key(str(p.get("base_url") or "")) == host_key:
                    existing_name = str(p.get("name") or "").strip()
                    if existing_name:
                        default_name = existing_name
                        break

        name = simpledialog.askstring("Save profile", "Profile name:", initialvalue=default_name, parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning("Missing", "Profile name cannot be empty.")
            return

        profile = {
            "name": name,
            "base_url": base_url,
            "client_id": client_id,
            "client_secret": client_secret,
            "verify_ssl": verify_ssl,
            "omada_id": omada_id,
        }

        replace_idx = -1
        for i, p in enumerate(self.controller_profiles):
            pname = str(p.get("name", "")).strip().lower()
            phost = self._controller_host_key(str(p.get("base_url") or ""))
            if pname == name.lower() and phost == host_key:
                replace_idx = i
                break

        if replace_idx >= 0:
            self.controller_profiles[replace_idx] = profile
        else:
            self.controller_profiles.append(profile)

        self._save_controller_profiles()
        self._refresh_controller_profile_combo()
        for i, p in enumerate(self.controller_profiles):
            pname = str(p.get("name", "")).strip().lower()
            phost = self._controller_host_key(str(p.get("base_url") or ""))
            if pname == name.lower() and phost == host_key:
                self.cmb_controller_profiles.current(i)
                break
        self._q.put(("log", f"Profile saved: {name}"))

    def on_remove_controller_profile(self):
        idx = self._selected_controller_profile_index()
        if idx < 0:
            messagebox.showwarning("Missing", "Select a saved profile first.")
            return
        name = str(self.controller_profiles[idx].get("name") or "(unnamed)")
        if not messagebox.askyesno("Confirm removal", f"Remove profile '{name}'?"):
            return
        self.controller_profiles.pop(idx)
        self._save_controller_profiles()
        self._refresh_controller_profile_combo()
        self._q.put(("log", f"Profile removed: {name}"))

    def on_import_controller_profiles(self):
        path = filedialog.askopenfilename(
            title="Import controller profiles JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")
            return

        if isinstance(raw, dict):
            items = raw.get("profiles")
            if not isinstance(items, list):
                items = raw.get("controllers")
            if not isinstance(items, list):
                messagebox.showerror("Error", "Invalid format. Expected list or {'profiles': [...]} format.")
                return
        elif isinstance(raw, list):
            items = raw
        else:
            messagebox.showerror("Error", "Invalid format. Expected list or {'profiles': [...]} format.")
            return

        merged = 0
        for i, item in enumerate(items):
            p = self._normalize_controller_profile(item, index=i)
            if not p:
                continue
            key = str(p.get("name", "")).strip().lower()
            found = False
            for j, cur in enumerate(self.controller_profiles):
                if str(cur.get("name", "")).strip().lower() == key:
                    self.controller_profiles[j] = p
                    found = True
                    break
            if not found:
                self.controller_profiles.append(p)
            merged += 1

        if merged == 0:
            messagebox.showwarning("Import", "No valid profiles found in file.")
            return

        self._save_controller_profiles()
        self._refresh_controller_profile_combo()
        self._q.put(("log", f"Imported {merged} profile(s) from {path}"))

    def on_export_controller_profiles(self):
        if not self.controller_profiles:
            messagebox.showinfo("Nothing", "No profiles to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export controller profiles JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"profiles": self.controller_profiles}, f, indent=2)
        self._q.put(("log", f"Exported {len(self.controller_profiles)} profile(s) to {path}"))

    def _build_current_tab(self):
        frame = ttk.Frame(self.tab_current, padding=10)
        frame.pack(fill="both", expand=True)

        top = ttk.Frame(frame)
        top.pack(fill="x")

        self.btn_fetch_networks = ttk.Button(top, text="Refresh LAN networks", command=self.on_fetch_networks, state="disabled")
        self.btn_fetch_networks.pack(side="left")

        self.btn_export_networks = ttk.Button(top, text="Export JSON…", command=self.on_export_networks, state="disabled")
        self.btn_export_networks.pack(side="left", padx=(8, 0))

        self.lbl_networks_state = ttk.Label(top, text="")
        self.lbl_networks_state.pack(side="left", padx=(10, 0))

        cols = ("name", "vlan", "gatewaySubnet", "dhcp_start", "dhcp_end", "id")
        self.tree_networks = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (220, 70, 170, 120, 120, 260)):
            self.tree_networks.heading(c, text=c)
            self.tree_networks.column(c, width=w, anchor="w")
        self.tree_networks.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(frame, text="Raw JSON (selected row)").pack(anchor="w", pady=(10, 0))
        self.txt_network_raw = tk.Text(frame, height=8)
        self.txt_network_raw.pack(fill="x", expand=False)
        self.tree_networks.bind("<<TreeviewSelect>>", self._on_network_selected)

        self._networks_cache: List[Dict[str, Any]] = []

    def _build_batch_tab(self):
        frame = ttk.Frame(self.tab_batch, padding=10)
        frame.pack(fill="both", expand=True)

        form = ttk.LabelFrame(frame, text="Batch parameters", padding=10)
        form.pack(fill="x")

        r = 0
        ttk.Label(form, text="Name prefix").grid(row=r, column=0, sticky="w")
        self.var_name_prefix = tk.StringVar(value="LAN")
        ttk.Entry(form, textvariable=self.var_name_prefix, width=18).grid(row=r, column=1, sticky="w")

        ttk.Label(form, text="Start subnet IP").grid(row=r, column=2, sticky="w", padx=(15, 0))
        self.var_start_ip = tk.StringVar(value="10.0.0.0")
        ttk.Entry(form, textvariable=self.var_start_ip, width=18).grid(row=r, column=3, sticky="w")
        r += 1

        ttk.Label(form, text="Prefix length (CIDR)").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_prefix = tk.IntVar(value=24)
        ttk.Spinbox(form, from_=8, to=30, textvariable=self.var_prefix, width=6).grid(row=r, column=1, sticky="w", pady=(6, 0))

        ttk.Label(form, text="Number of LANs/VLANs").grid(row=r, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
        self.var_count = tk.IntVar(value=20)
        ttk.Spinbox(form, from_=1, to=200, textvariable=self.var_count, width=8).grid(row=r, column=3, sticky="w", pady=(6, 0))
        r += 1

        ttk.Label(form, text="Start VLAN").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_start_vlan = tk.IntVar(value=100)
        ttk.Spinbox(form, from_=1, to=4090, textvariable=self.var_start_vlan, width=8).grid(row=r, column=1, sticky="w", pady=(6, 0))

        ttk.Label(form, text="DHCP start offset").grid(row=r, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
        self.var_dhcp_start_off = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=2, to=200, textvariable=self.var_dhcp_start_off, width=8).grid(row=r, column=3, sticky="w", pady=(6, 0))
        r += 1

        ttk.Label(form, text="DHCP end offset (from broadcast)").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_dhcp_end_off = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=2, to=200, textvariable=self.var_dhcp_end_off, width=8).grid(row=r, column=1, sticky="w", pady=(6, 0))
        r += 1

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(10, 0))

        self.btn_preview = ttk.Button(btns, text="Generate preview", command=self.on_generate_preview, state="disabled")
        self.btn_preview.pack(side="left")

        self.btn_push = ttk.Button(btns, text="Push to controller", command=self.on_push_plan, state="disabled")
        self.btn_push.pack(side="left", padx=(8, 0))

        self.btn_export_plan = ttk.Button(btns, text="Export preview JSON…", command=self.on_export_plan, state="disabled")
        self.btn_export_plan.pack(side="left", padx=(8, 0))

        self.prog = ttk.Progressbar(btns, mode="determinate")
        self.prog.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.lbl_batch_state = ttk.Label(frame, text="")
        self.lbl_batch_state.pack(anchor="w", pady=(6, 0))

        cols = ("#", "name", "vlan", "subnet", "gateway", "dhcp_start", "dhcp_end")
        self.tree_plan = ttk.Treeview(frame, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (40, 200, 70, 150, 120, 120, 120)):
            self.tree_plan.heading(c, text=c)
            self.tree_plan.column(c, width=w, anchor="w")
        self.tree_plan.pack(fill="both", expand=True, pady=(10, 0))

        for c in range(4):
            form.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0)

    def _build_logs_tab(self):
        frame = ttk.Frame(self.tab_logs, padding=10)
        frame.pack(fill="both", expand=True)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Button(top, text="Clear log", command=self.on_clear_log).pack(side="left")
        self.txt_logs = tk.Text(frame)
        self.txt_logs.pack(fill="both", expand=True)
        self._log("Ready.")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert("end", f"[{ts}] {msg}\n")
        self.txt_logs.see("end")

    def on_clear_log(self):
        self.txt_logs.delete("1.0", "end")
        self._log("Log cleared.")

    def _poll_queue(self):
        try:
            while True:
                typ, payload = self._q.get_nowait()
                if typ == "log":
                    self._log(str(payload))
                elif typ == "connected":
                    self._on_connected(payload)
                elif typ == "sites":
                    self._on_sites(payload)
                elif typ == "networks":
                    self._on_networks(payload)
                elif typ == "gateways":
                    self._on_gateways(payload)
                elif typ == "progress":
                    done, total, text = payload
                    self.prog["maximum"] = max(total, 1)
                    self.prog["value"] = done
                    self.lbl_batch_state.config(text=text)
                elif typ == "error":
                    messagebox.showerror("Error", str(payload))
                elif typ == "info":
                    messagebox.showinfo("Info", str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _run_bg(self, fn, *, disable_buttons: List[ttk.Button]):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        for b in disable_buttons:
            b.config(state="disabled")

        def wrap():
            try:
                fn()
            except Exception as e:
                self._q.put(("error", str(e)))
                self._q.put(("log", f"ERROR: {e}"))
            finally:
                self._q.put(("log", "Operation finished."))
                self._q.put(("connected", "refresh_buttons"))

        self._worker = threading.Thread(target=wrap, daemon=True)
        self._worker.start()

    def on_connect(self):
        url = self.var_url.get().strip()
        cid = self.var_client_id.get().strip()
        csec = self.var_client_secret.get().strip()
        omada_id = self.var_omada_id.get().strip() or None
        verify = bool(self.var_verify_ssl.get())

        if not url or url == "https://":
            messagebox.showwarning("Missing", "Please enter the controller base URL.")
            return
        if not cid or not csec:
            messagebox.showwarning("Missing", "Please enter Client ID and Client Secret.")
            return

        def work():
            self._q.put(("log", f"Connecting to {url} (verify_ssl={verify}) ..."))
            client = OmadaOpenApiClient(url, verify_ssl=verify, logger=lambda m: self._q.put(("log", m)))

            info = client.get_controller_info()
            ver = info.get("result", {}).get("controllerVer") if isinstance(info, dict) else None
            self._q.put(("log", f"/api/info OK; controllerVer={ver}"))

            if omada_id:
                client.omadac_id = omada_id
            elif client.omadac_id:
                self._q.put(("log", f"Detected omadacId={client.omadac_id}"))

            client.get_access_token_client_credentials(cid, csec, omadac_id=client.omadac_id)
            self._q.put(("log", f"Access token OK (expires ~{client.access_token_expiry} UTC)."))

            sites = client.get_sites(page=1, page_size=100)
            self._q.put(("sites", sites))

            self.client = client
            self._q.put(("connected", "connected"))

        self._run_bg(work, disable_buttons=[self.btn_connect])

    def _on_connected(self, status):
        if status == "connected":
            self.lbl_conn_state.config(text="Connected")
            self.btn_refresh_sites.config(state="normal")
            self.btn_fetch_networks.config(state="normal")
            self.btn_export_networks.config(state="normal")
            self.btn_preview.config(state="normal")
            self.btn_refresh_gateways.config(state="normal")
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="normal")
            if self.client and self.client.omadac_id:
                self.var_omada_id.set(self.client.omadac_id)
            self._update_push_state()
        elif status == "refresh_buttons":
            self.btn_connect.config(state="normal")
            if self.client:
                self.btn_refresh_sites.config(state="normal")
                self.btn_fetch_networks.config(state="normal")
                self.btn_export_networks.config(state="normal")
                self.btn_preview.config(state="normal")
                self.btn_refresh_gateways.config(state="normal")
                self.btn_disconnect.config(state="normal")
                self._update_push_state()
            else:
                self.btn_disconnect.config(state="disabled")
                self._update_push_state()

    def on_disconnect(self):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        if self.client:
            try:
                self.client.session.close()
            except Exception:
                pass

        self.client = None
        self.sites = []
        self.selected_site_id = None
        self.gateways = []
        self.selected_gateway_name = None
        self.selected_gateway_value = None
        self.selected_gateway_label = None
        self.selected_gateway_type = None
        self.selected_gateway_device_id = None
        self.selected_gateway_interface_ids = []
        self.selected_gateway_interfaces = []
        self.plan_interface_ids = {}

        self.cmb_sites["values"] = []
        self.var_site.set("")
        self._on_gateways([])

        self._networks_cache = []
        for i in self.tree_networks.get_children():
            self.tree_networks.delete(i)
        self.txt_network_raw.delete("1.0", "end")
        self.lbl_networks_state.config(text="")

        self.lbl_conn_state.config(text="Not connected")
        self.btn_refresh_sites.config(state="disabled")
        self.btn_refresh_gateways.config(state="disabled")
        self.btn_fetch_networks.config(state="disabled")
        self.btn_export_networks.config(state="disabled")
        self.btn_preview.config(state="disabled")
        self.btn_disconnect.config(state="disabled")
        self.btn_connect.config(state="normal")
        self._update_push_state()
        self._q.put(("log", "Disconnected."))

    def on_refresh_sites(self):
        if not self.client:
            return

        def work():
            self._q.put(("log", "Refreshing sites..."))
            sites = self.client.get_sites(page=1, page_size=100)
            self._q.put(("sites", sites))

        self._run_bg(work, disable_buttons=[self.btn_refresh_sites])

    def _on_sites(self, sites):
        self.sites = sites or []
        if not self.sites:
            self.cmb_sites["values"] = []
            self.var_site.set("")
            self.selected_site_id = None
            self._on_gateways([])
            self._q.put(("log", "No sites returned."))
            return

        values = [f"{s.get('name','(no name)')}  [{s.get('siteId')}]" for s in self.sites]
        self.cmb_sites["values"] = values
        self.cmb_sites.current(0)
        self.on_site_selected()

    def on_site_selected(self, _evt=None):
        idx = self.cmb_sites.current()
        if idx < 0 or idx >= len(self.sites):
            self.selected_site_id = None
            return
        self.selected_site_id = self.sites[idx].get("siteId")
        self._q.put(("log", f"Selected siteId={self.selected_site_id}"))
        self._on_gateways([])
        self.after(400, lambda: self.on_refresh_gateways(silent_if_busy=True))

    def on_refresh_gateways(self, silent_if_busy: bool = False):
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

        self._run_bg(work, disable_buttons=[self.btn_refresh_gateways])

    def _build_interface_catalog(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return build_interface_catalog(devices)

    def _on_gateways(self, gateways):
        self.gateways = gateways or []
        self.selected_gateway_name = None
        self.selected_gateway_value = None
        self.selected_gateway_label = None
        self.selected_gateway_type = None
        self.selected_gateway_device_id = None
        self.selected_gateway_interface_ids = []
        self.selected_gateway_interfaces = []

        if not self.gateways:
            self.cmb_gateways["values"] = []
            self.var_gateway.set("")
            self.cmb_gateways.config(state="disabled")
            self._q.put(("log", "No DHCP servers loaded for selected site."))
            self._update_push_state()
            return

        values = [g.get("label", g.get("name", "")) for g in self.gateways]
        self.cmb_gateways["values"] = values
        self.cmb_gateways.config(state="readonly")
        self.cmb_gateways.current(0)
        self.on_gateway_selected()
        self._q.put(("log", f"Loaded {len(self.gateways)} DHCP servers for selected site."))

    def on_gateway_selected(self, _evt=None):
        idx = self.cmb_gateways.current()
        if idx < 0 or idx >= len(self.gateways):
            self.selected_gateway_name = None
            self.selected_gateway_value = None
            self.selected_gateway_label = None
            self.selected_gateway_type = None
            self.selected_gateway_device_id = None
            self.selected_gateway_interface_ids = []
            self._update_push_state()
            return
        self.selected_gateway_name = self.gateways[idx].get("name")
        self.selected_gateway_value = self.gateways[idx].get("value")
        self.selected_gateway_label = self.gateways[idx].get("label")
        self.selected_gateway_type = self.gateways[idx].get("type")
        self.selected_gateway_device_id = self.gateways[idx].get("device_id") or None
        self.selected_gateway_interface_ids = self.gateways[idx].get("interface_ids") or []
        self.selected_gateway_interfaces = self.gateways[idx].get("interfaces") or []
        self._q.put(("log", f"Selected DHCP server={self.selected_gateway_name}"))
        self._update_push_state()

    def on_fetch_networks(self):
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return

        def work():
            self._q.put(("log", "Fetching LAN networks..."))
            nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
            self._q.put(("networks", nets))

        self._run_bg(work, disable_buttons=[self.btn_fetch_networks])

    def _on_networks(self, nets):
        self._networks_cache = nets or []
        for i in self.tree_networks.get_children():
            self.tree_networks.delete(i)

        for n in self._networks_cache:
            name = n.get("name", "")
            vlan = n.get("vlan", "")
            gateway_subnet = n.get("gatewaySubnet", "")
            dhcp = n.get("dhcpSettingsVO") or {}
            pool = (dhcp.get("ipRangePool") or [])
            ds = pool[0].get("ipaddrStart") if pool else ""
            de = pool[0].get("ipaddrEnd") if pool else ""
            nid = n.get("id", "")
            self.tree_networks.insert("", "end", values=(name, vlan, gateway_subnet, ds, de, nid))

        self.lbl_networks_state.config(text=f"{len(self._networks_cache)} networks loaded.")
        self._q.put(("log", f"Loaded {len(self._networks_cache)} LAN networks."))

    def _on_network_selected(self, _evt=None):
        sel = self.tree_networks.selection()
        if not sel:
            return
        idx = self.tree_networks.index(sel[0])
        if idx < 0 or idx >= len(self._networks_cache):
            return
        raw = self._networks_cache[idx]
        self.txt_network_raw.delete("1.0", "end")
        self.txt_network_raw.insert("end", json.dumps(raw, indent=2))

    def on_export_networks(self):
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
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._networks_cache, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_generate_preview(self):
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
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self.plan = plans
        for i in self.tree_plan.get_children():
            self.tree_plan.delete(i)

        for p in self.plan:
            self.tree_plan.insert(
                "",
                "end",
                values=(p.index, p.name, p.vlan_id, p.network.with_prefixlen, str(p.gateway), str(p.dhcp_start), str(p.dhcp_end)),
            )

        if warnings:
            messagebox.showwarning("Plan warnings", "\n".join(warnings))
            for w in warnings:
                self._log(f"WARNING: {w}")

        self._log(f"Preview generated: {len(self.plan)} networks.")
        self._update_push_state()
        self.btn_export_plan.config(state="normal" if self.plan else "disabled")

    def on_export_plan(self):
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
        obj = [{
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
        } for p in self.plan]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_push_plan(self):
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        if not self.selected_gateway_name:
            messagebox.showwarning("Missing", "Select a DHCP server for this site first (Refresh DHCP servers).")
            return
        if not self.plan:
            messagebox.showwarning("Missing", "Generate a preview first.")
            return
        iface_catalog = self.selected_gateway_interfaces
        if not iface_catalog and self.selected_gateway_interface_ids:
            iface_catalog = [{"id": i, "name": i} for i in self.selected_gateway_interface_ids]
        network_iface_catalog: List[Dict[str, str]] = []
        if not iface_catalog or any(str(i.get("name") or "").strip() == str(i.get("id") or "").strip() for i in iface_catalog):
            network_iface_catalog = self._get_interface_catalog_from_networks()
        if not iface_catalog:
            iface_catalog = network_iface_catalog
            if iface_catalog:
                self._q.put(("log", "Using interfaces discovered from existing LAN networks."))
        elif network_iface_catalog:
            iface_catalog = self._merge_interface_catalog_names(iface_catalog, network_iface_catalog)
        if not iface_catalog:
            messagebox.showwarning("Missing", "No LAN interfaces found for this site.")
            return
        if len(iface_catalog) == 1:
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
            gateway_name = self.selected_gateway_name
            assert gateway_name
            gateway_device = self.selected_gateway_device_id or self.selected_gateway_value or gateway_name
            interface_ids = None

            total_steps = len(self.plan)
            done = 0

            for p in self.plan:
                self._q.put(("progress", (done, total_steps, f"Creating {p.name} (VLAN {p.vlan_id})...")))
                iface_ids = self.plan_interface_ids.get(p.index)
                if not iface_ids:
                    raise RuntimeError(f"Interface selection missing for {p.name}.")
                resp = self.client.create_lan_network(site_id, p, gateway_device=gateway_device, interface_ids=iface_ids)
                if resp.get("errorCode") != 0:
                    raise RuntimeError(f"Create LAN failed for {p.name}: {resp.get('errorCode')} {resp.get('msg')}")
                self._q.put(("log", f"LAN created: {p.name} VLAN {p.vlan_id} {p.network.with_prefixlen}"))
                done += 1

            self._q.put(("progress", (total_steps, total_steps, "Done.")))
            self._q.put(("info", "Batch creation completed."))

        self._run_bg(work, disable_buttons=[self.btn_push])

    def _update_push_state(self):
        enabled = bool(self.client and self.selected_site_id and self.selected_gateway_name and len(self.plan) > 0)
        self.btn_push.config(state="normal" if enabled else "disabled")

    def _interface_display_name(self, iface: Dict[str, str]) -> str:
        return interface_display_name(iface)

    def _merge_interface_catalog_names(self, base: List[Dict[str, str]], extra: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return merge_interface_catalog_names(base, extra)

    def _prompt_interface_selection(self, interfaces: List[Dict[str, str]]) -> Optional[Dict[int, List[str]]]:
        return prompt_interface_selection(self, self.plan, interfaces, self._interface_display_name)

    def _get_interface_catalog_from_networks(self) -> List[Dict[str, str]]:
        catalog = extract_interface_catalog_from_networks(self._networks_cache)
        if catalog:
            return catalog
        if self.client and self.selected_site_id:
            try:
                nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
                return extract_interface_catalog_from_networks(nets)
            except Exception as e:
                self._q.put(("log", f"WARNING: Could not fetch interfaceIds from networks: {e}"))
        return []

