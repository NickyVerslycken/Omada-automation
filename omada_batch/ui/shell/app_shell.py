from __future__ import annotations

import json
import queue
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from omada_batch.storage.profile_store import ProfileStore
from omada_batch.ui.controllers import BatchControllerMixin, ConnectionControllerMixin, NetworksControllerMixin
from omada_batch.ui.state import AppState
from omada_batch.ui.tabs import (
    build_batch_tab,
    build_connection_tab,
    build_current_networks_tab,
    build_developer_tab,
    build_logs_tab,
)


class App(tk.Tk, ConnectionControllerMixin, NetworksControllerMixin, BatchControllerMixin):
    def __init__(self):
        super().__init__()
        self.title("Omada LAN/VLAN Batch Manager (IPv4)")
        self.geometry("1100x720")

        self.state = AppState(profile_store=ProfileStore())
        self.controller_profiles_path = self.profile_store.path

        self._q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._log_line_no = 0
        self._devjson_line_no = 0

        self._load_controller_profiles()
        self._build_ui()
        self._refresh_controller_profile_combo()
        self.after(150, self._poll_queue)

    @property
    def client(self):
        return self.state.client

    @client.setter
    def client(self, value):
        self.state.client = value

    @property
    def sites(self):
        return self.state.sites

    @sites.setter
    def sites(self, value):
        self.state.sites = value

    @property
    def gateways(self):
        return self.state.gateways

    @gateways.setter
    def gateways(self, value):
        self.state.gateways = value

    @property
    def selected_site_id(self):
        return self.state.selected_site_id

    @selected_site_id.setter
    def selected_site_id(self, value):
        self.state.selected_site_id = value

    @property
    def current_gateway_filter_index(self):
        return self.state.current_gateway_filter_index

    @current_gateway_filter_index.setter
    def current_gateway_filter_index(self, value):
        self.state.current_gateway_filter_index = value

    @property
    def batch_gateway_index(self):
        return self.state.batch_gateway_index

    @batch_gateway_index.setter
    def batch_gateway_index(self, value):
        self.state.batch_gateway_index = value

    @property
    def plan(self):
        return self.state.plan

    @plan.setter
    def plan(self, value):
        self.state.plan = value

    @property
    def plan_interface_ids(self):
        return self.state.plan_interface_ids

    @plan_interface_ids.setter
    def plan_interface_ids(self, value):
        self.state.plan_interface_ids = value

    @property
    def controller_profiles(self):
        return self.state.controller_profiles

    @controller_profiles.setter
    def controller_profiles(self, value):
        self.state.controller_profiles = value

    @property
    def _networks_cache_all(self):
        return self.state.networks_cache_all

    @_networks_cache_all.setter
    def _networks_cache_all(self, value):
        self.state.networks_cache_all = value

    @property
    def _networks_cache(self):
        return self.state.networks_cache

    @_networks_cache.setter
    def _networks_cache(self, value):
        self.state.networks_cache = value

    @property
    def profile_store(self):
        return self.state.profile_store

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        self.var_developer_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="Developer mode",
            variable=self.var_developer_mode,
            command=self.on_toggle_developer_mode,
        ).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(8, 10))
        self.nb = nb

        self.tab_conn = ttk.Frame(nb)
        self.tab_current = ttk.Frame(nb)
        self.tab_batch = ttk.Frame(nb)
        self.tab_logs = ttk.Frame(nb)
        self.tab_dev = ttk.Frame(nb)

        nb.add(self.tab_conn, text="Connection")
        nb.add(self.tab_current, text="Current LAN Networks")
        nb.add(self.tab_batch, text="Batch Create")
        nb.add(self.tab_logs, text="Logs")

        build_connection_tab(self)
        build_current_networks_tab(self)
        build_batch_tab(self)
        build_logs_tab(self)
        build_developer_tab(self)
        self._developer_tab_visible = False

    def _truncate(self, text: str, limit: int = 250) -> str:
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."

    def _append_numbered_lines(self, widget: tk.Text, text: str, *, counter_attr: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        lines = text.splitlines() or [text]
        for line in lines:
            next_no = int(getattr(self, counter_attr, 0)) + 1
            setattr(self, counter_attr, next_no)
            widget.insert("end", f"{next_no:06d} [{ts}] {line}\n")
        widget.see("end")

    def _log(self, msg: str) -> None:
        self._append_numbered_lines(self.txt_logs, self._truncate(str(msg)), counter_attr="_log_line_no")

    def on_clear_log(self) -> None:
        self.txt_logs.delete("1.0", "end")
        self._log_line_no = 0
        self._log("Log cleared.")

    def on_clear_devjson(self) -> None:
        self.txt_devjson.delete("1.0", "end")
        self._devjson_line_no = 0
        self._log("Developer JSON output cleared.")

    def on_toggle_developer_mode(self) -> None:
        enabled = bool(self.var_developer_mode.get())
        if enabled and not self._developer_tab_visible:
            self.nb.add(self.tab_dev, text="Developer JSON")
            self._developer_tab_visible = True
            self._log("Developer mode enabled.")
        elif not enabled and self._developer_tab_visible:
            self.nb.forget(self.tab_dev)
            self._developer_tab_visible = False
            self._log("Developer mode disabled.")

    def _devjson_log(self, payload: Any) -> None:
        if not bool(self.var_developer_mode.get()):
            return
        try:
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = str(payload)
        self._append_numbered_lines(self.txt_devjson, text, counter_attr="_devjson_line_no")

    def _poll_queue(self) -> None:
        try:
            while True:
                typ, payload = self._q.get_nowait()
                if typ != "devjson":
                    self._devjson_log({"event": "queue_event", "type": typ, "payload": payload})
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
                elif typ == "devjson":
                    self._devjson_log(payload)
                elif typ == "error":
                    messagebox.showerror("Error", str(payload))
                elif typ == "info":
                    messagebox.showinfo("Info", str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _run_bg(self, fn, *, disable_buttons: List[ttk.Button]) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        for button in disable_buttons:
            button.config(state="disabled")

        def wrap() -> None:
            try:
                fn()
            except Exception as exc:
                self._q.put(("error", str(exc)))
                self._q.put(("log", f"ERROR: {exc}"))
            finally:
                self._q.put(("log", "Operation finished."))
                self._q.put(("connected", "refresh_buttons"))

        self._worker = threading.Thread(target=wrap, daemon=True)
        self._worker.start()
