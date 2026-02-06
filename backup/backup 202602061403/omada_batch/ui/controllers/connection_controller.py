from __future__ import annotations

import json
from urllib.parse import urlparse
from typing import Any, Dict, Optional

from tkinter import filedialog, messagebox, simpledialog

from omada_batch.api.omada_client import OmadaOpenApiClient
from omada_batch.services.profile_service import normalize_profile


class ConnectionControllerMixin:
    def _load_controller_profiles(self) -> None:
        self.controller_profiles = []
        items = self.profile_store.load_raw()
        for idx, item in enumerate(items):
            prof = self._normalize_controller_profile(item, index=idx)
            if prof:
                self.controller_profiles.append(prof)

    def _save_controller_profiles(self) -> None:
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

    def _refresh_controller_profile_combo(self) -> None:
        if not hasattr(self, "cmb_controller_profiles"):
            return
        values = [f"{p.get('name', '(unnamed)')}  [{p.get('base_url', '')}]" for p in self.controller_profiles]
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

    def on_controller_profile_selected(self, _evt=None) -> None:
        idx = self._selected_controller_profile_index()
        if idx < 0:
            return
        profile = self.controller_profiles[idx]
        self.var_url.set(str(profile.get("base_url") or "https://"))
        self.var_client_id.set(str(profile.get("client_id") or ""))
        self.var_client_secret.set(str(profile.get("client_secret") or ""))
        self.var_verify_ssl.set(bool(profile.get("verify_ssl")))
        self.var_omada_id.set(str(profile.get("omada_id") or ""))

    def on_save_controller_profile(self) -> None:
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
            for prof in self.controller_profiles:
                if self._controller_host_key(str(prof.get("base_url") or "")) == host_key:
                    existing_name = str(prof.get("name") or "").strip()
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
        for idx, cur in enumerate(self.controller_profiles):
            pname = str(cur.get("name", "")).strip().lower()
            phost = self._controller_host_key(str(cur.get("base_url") or ""))
            if pname == name.lower() and phost == host_key:
                replace_idx = idx
                break

        if replace_idx >= 0:
            self.controller_profiles[replace_idx] = profile
        else:
            self.controller_profiles.append(profile)

        self._save_controller_profiles()
        self._refresh_controller_profile_combo()
        for idx, cur in enumerate(self.controller_profiles):
            pname = str(cur.get("name", "")).strip().lower()
            phost = self._controller_host_key(str(cur.get("base_url") or ""))
            if pname == name.lower() and phost == host_key:
                self.cmb_controller_profiles.current(idx)
                break
        self._q.put(("log", f"Profile saved: {name}"))

    def on_remove_controller_profile(self) -> None:
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

    def on_import_controller_profiles(self) -> None:
        path = filedialog.askopenfilename(
            title="Import controller profiles JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not read file: {exc}")
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
        for idx, item in enumerate(items):
            profile = self._normalize_controller_profile(item, index=idx)
            if not profile:
                continue
            key = str(profile.get("name", "")).strip().lower()
            found = False
            for j, cur in enumerate(self.controller_profiles):
                if str(cur.get("name", "")).strip().lower() == key:
                    self.controller_profiles[j] = profile
                    found = True
                    break
            if not found:
                self.controller_profiles.append(profile)
            merged += 1

        if merged == 0:
            messagebox.showwarning("Import", "No valid profiles found in file.")
            return

        self._save_controller_profiles()
        self._refresh_controller_profile_combo()
        self._q.put(("log", f"Imported {merged} profile(s) from {path}"))

    def on_export_controller_profiles(self) -> None:
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

    def on_connect(self) -> None:
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
            client = OmadaOpenApiClient(
                url,
                verify_ssl=verify,
                logger=lambda m: self._q.put(("log", m)),
                json_logger=lambda payload: self._q.put(("devjson", payload)),
            )

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

    def _on_connected(self, status) -> None:
        if status == "connected":
            self.lbl_conn_state.config(text="Connected")
            self.btn_refresh_sites.config(state="normal")
            self.btn_fetch_networks.config(state="normal")
            self.btn_export_networks.config(state="normal")
            self.btn_preview.config(state="normal")
            self.btn_refresh_gateways_current.config(state="normal")
            self.btn_refresh_gateways_batch.config(state="normal")
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
                self.btn_refresh_gateways_current.config(state="normal")
                self.btn_refresh_gateways_batch.config(state="normal")
                self.btn_disconnect.config(state="normal")
                self._update_push_state()
            else:
                self.btn_disconnect.config(state="disabled")
                self._update_push_state()

    def on_disconnect(self) -> None:
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
        self.current_gateway_filter_index = -1
        self.batch_gateway_index = -1
        self.plan_interface_ids = {}

        self.cmb_sites["values"] = []
        self.var_site.set("")
        self._on_gateways([])

        self._networks_cache_all = []
        self._networks_cache = []
        for item_id in self.tree_networks.get_children():
            self.tree_networks.delete(item_id)
        self.txt_network_raw.delete("1.0", "end")
        self.lbl_networks_state.config(text="")

        self.lbl_conn_state.config(text="Not connected")
        self.btn_refresh_sites.config(state="disabled")
        self.btn_refresh_gateways_current.config(state="disabled")
        self.btn_refresh_gateways_batch.config(state="disabled")
        self.btn_fetch_networks.config(state="disabled")
        self.btn_export_networks.config(state="disabled")
        self.btn_preview.config(state="disabled")
        self.btn_disconnect.config(state="disabled")
        self.btn_connect.config(state="normal")
        self._update_push_state()
        self._q.put(("log", "Disconnected."))

    def on_refresh_sites(self) -> None:
        if not self.client:
            return

        def work():
            self._q.put(("log", "Refreshing sites..."))
            sites = self.client.get_sites(page=1, page_size=100)
            self._q.put(("sites", sites))

        self._run_bg(work, disable_buttons=[self.btn_refresh_sites])

    def _on_sites(self, sites) -> None:
        self.sites = sites or []
        if not self.sites:
            self.cmb_sites["values"] = []
            self.var_site.set("")
            self.selected_site_id = None
            self._on_gateways([])
            self._q.put(("log", "No sites returned."))
            return

        values = [f"{site.get('name', '(no name)')}  [{site.get('siteId')}]" for site in self.sites]
        self.cmb_sites["values"] = values
        self.cmb_sites.current(0)
        self.on_site_selected()

    def on_site_selected(self, _evt=None) -> None:
        idx = self.cmb_sites.current()
        if idx < 0 or idx >= len(self.sites):
            self.selected_site_id = None
            return
        self.selected_site_id = self.sites[idx].get("siteId")
        self._q.put(("log", f"Selected siteId={self.selected_site_id}"))
        self._on_gateways([])
        self.after(400, lambda: self.on_refresh_gateways(silent_if_busy=True))
