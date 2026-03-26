from __future__ import annotations

import json
import queue
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from omada_batch.storage.profile_store import ProfileStore
from omada_batch.ui.controllers import BatchControllerMixin, ConnectionControllerMixin, NetworksControllerMixin, VlanBatchControllerMixin
from omada_batch.ui.state import AppState
from omada_batch.ui.tabs import (
    build_batch_tab,
    build_connection_tab,
    build_current_networks_tab,
    build_developer_tab,
    build_logs_tab,
)
from omada_batch.ui.theme import (
    BORDER_LIGHT,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_HEADING_LG,
    FONT_HEADING_SM,
    FONT_LABEL,
    FONT_SMALL,
    PRIMARY,
    PRIMARY_HOVER,
    STATUS_DOT_CONNECTED,
    STATUS_DOT_DISCONNECTED,
    STATUSBAR_HEIGHT,
    SURFACE,
    SURFACE_ALT,
    SURFACE_CARD,
    SURFACE_SIDEBAR,
    SURFACE_SIDEBAR_ACTIVE,
    SURFACE_SIDEBAR_HOVER,
    TEXT_MUTED,
    TEXT_ON_PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SIDEBAR,
    TEXT_SIDEBAR_ACTIVE,
    SIDEBAR_WIDTH,
    configure_treeview_style,
)


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# ── Navigation items ───────────────────────────────────────────────
NAV_ITEMS = [
    ("connection", "Connection", "\u2693"),      # ⚓
    ("networks", "Networks", "\U0001F310"),       # 🌐
    ("batch", "Batch Create", "\u2699"),          # ⚙
    ("logs", "Logs", "\U0001F4CB"),               # 📋
]
DEV_NAV_ITEM = ("devjson", "Developer JSON", "\U0001F527")  # 🔧


class App(ctk.CTk, ConnectionControllerMixin, NetworksControllerMixin, BatchControllerMixin, VlanBatchControllerMixin):
    def __init__(self):
        super().__init__()
        self.title("Omada Batch Manager")
        self.geometry("1200x780")
        self.minsize(1000, 650)
        self.configure(fg_color=SURFACE)

        self.app_state = AppState(profile_store=ProfileStore())
        self.controller_profiles_path = self.profile_store.path

        self._q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._log_line_no = 0
        self._devjson_line_no = 0

        self._load_controller_profiles()
        self._build_ui()
        self._refresh_controller_profile_combo()
        self.after(150, self._poll_queue)

    # ── State properties (unchanged) ───────────────────────────────
    @property
    def client(self):
        return self.app_state.client

    @client.setter
    def client(self, value):
        self.app_state.client = value

    @property
    def sites(self):
        return self.app_state.sites

    @sites.setter
    def sites(self, value):
        self.app_state.sites = value

    @property
    def gateways(self):
        return self.app_state.gateways

    @gateways.setter
    def gateways(self, value):
        self.app_state.gateways = value

    @property
    def selected_site_id(self):
        return self.app_state.selected_site_id

    @selected_site_id.setter
    def selected_site_id(self, value):
        self.app_state.selected_site_id = value

    @property
    def current_gateway_filter_index(self):
        return self.app_state.current_gateway_filter_index

    @current_gateway_filter_index.setter
    def current_gateway_filter_index(self, value):
        self.app_state.current_gateway_filter_index = value

    @property
    def batch_gateway_index(self):
        return self.app_state.batch_gateway_index

    @batch_gateway_index.setter
    def batch_gateway_index(self, value):
        self.app_state.batch_gateway_index = value

    @property
    def plan(self):
        return self.app_state.plan

    @plan.setter
    def plan(self, value):
        self.app_state.plan = value

    @property
    def plan_interface_ids(self):
        return self.app_state.plan_interface_ids

    @plan_interface_ids.setter
    def plan_interface_ids(self, value):
        self.app_state.plan_interface_ids = value

    @property
    def vlan_plan(self):
        return self.app_state.vlan_plan

    @vlan_plan.setter
    def vlan_plan(self, value):
        self.app_state.vlan_plan = value

    @property
    def vlan_plan_port_ids(self):
        return self.app_state.vlan_plan_port_ids

    @vlan_plan_port_ids.setter
    def vlan_plan_port_ids(self, value):
        self.app_state.vlan_plan_port_ids = value

    @property
    def controller_profiles(self):
        return self.app_state.controller_profiles

    @controller_profiles.setter
    def controller_profiles(self, value):
        self.app_state.controller_profiles = value

    @property
    def _networks_cache_all(self):
        return self.app_state.networks_cache_all

    @_networks_cache_all.setter
    def _networks_cache_all(self, value):
        self.app_state.networks_cache_all = value

    @property
    def _networks_cache(self):
        return self.app_state.networks_cache

    @_networks_cache.setter
    def _networks_cache(self, value):
        self.app_state.networks_cache = value

    @property
    def profile_store(self):
        return self.app_state.profile_store

    # ── UI construction ────────────────────────────────────────────
    def _build_ui(self) -> None:
        configure_treeview_style()

        # Main layout: sidebar | (header + content + statusbar)
        self._sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, fg_color=SURFACE_SIDEBAR, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        right_area = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0)
        right_area.pack(side="left", fill="both", expand=True)

        self._header = ctk.CTkFrame(right_area, height=56, fg_color=SURFACE_CARD, corner_radius=0)
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        # Separator below header
        sep = ctk.CTkFrame(right_area, height=1, fg_color=BORDER_LIGHT, corner_radius=0)
        sep.pack(fill="x")

        self._content = ctk.CTkFrame(right_area, fg_color=SURFACE, corner_radius=0)
        self._content.pack(fill="both", expand=True)

        # Separator above status bar
        sep2 = ctk.CTkFrame(right_area, height=1, fg_color=BORDER_LIGHT, corner_radius=0)
        sep2.pack(fill="x")

        self._statusbar = ctk.CTkFrame(right_area, height=STATUSBAR_HEIGHT, fg_color=SURFACE_CARD, corner_radius=0)
        self._statusbar.pack(fill="x")
        self._statusbar.pack_propagate(False)

        self._build_sidebar()
        self._build_header()
        self._build_statusbar()
        self._build_pages()

        # Show first page
        self._show_page("connection")

    def _build_sidebar(self) -> None:
        # App branding
        brand = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(20, 24))
        ctk.CTkLabel(
            brand, text="Omada Batch", font=FONT_HEADING_SM,
            text_color=TEXT_SIDEBAR_ACTIVE, anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            brand, text="NETWORK MANAGEMENT", font=FONT_SMALL,
            text_color=TEXT_MUTED, anchor="w",
        ).pack(fill="x")

        # Navigation items
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._nav_indicators: Dict[str, ctk.CTkFrame] = {}
        self._current_page = ""

        for key, label, icon in NAV_ITEMS:
            self._create_nav_item(key, label, icon)

        # Spacer
        ctk.CTkFrame(self._sidebar, fg_color="transparent", height=1).pack(fill="x", expand=True)

        # Developer mode toggle at bottom
        dev_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        dev_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.var_developer_mode = tk.BooleanVar(value=False)
        self._dev_switch = ctk.CTkSwitch(
            dev_frame, text="Developer mode",
            variable=self.var_developer_mode,
            command=self.on_toggle_developer_mode,
            font=FONT_SMALL,
            text_color=TEXT_SIDEBAR,
            progress_color=PRIMARY,
            button_color=TEXT_MUTED,
            button_hover_color=TEXT_SIDEBAR_ACTIVE,
            fg_color=SURFACE_SIDEBAR_HOVER,
        )
        self._dev_switch.pack(fill="x")

    def _create_nav_item(self, key: str, label: str, icon: str) -> None:
        item_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent", height=40)
        item_frame.pack(fill="x", pady=2)
        item_frame.pack_propagate(False)

        # Active indicator (left accent bar)
        indicator = ctk.CTkFrame(item_frame, width=4, fg_color="transparent", corner_radius=2)
        indicator.pack(side="left", fill="y")
        self._nav_indicators[key] = indicator

        btn = ctk.CTkButton(
            item_frame,
            text=f"  {icon}   {label}",
            font=FONT_BODY,
            anchor="w",
            fg_color="transparent",
            hover_color=SURFACE_SIDEBAR_HOVER,
            text_color=TEXT_SIDEBAR,
            corner_radius=6,
            height=36,
            command=lambda k=key: self._show_page(k),
        )
        btn.pack(fill="both", expand=True, padx=(4, 12))
        self._nav_buttons[key] = btn

    def _build_header(self) -> None:
        # Left: page title
        self._header_title = ctk.CTkLabel(
            self._header, text="Connection", font=FONT_HEADING_SM,
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self._header_title.pack(side="left", padx=24)

        # Right: page subtitle/breadcrumb
        self._header_subtitle = ctk.CTkLabel(
            self._header, text="", font=FONT_LABEL,
            text_color=TEXT_SECONDARY, anchor="e",
        )
        self._header_subtitle.pack(side="right", padx=24)

    def _build_statusbar(self) -> None:
        # Connection status dot
        self._status_dot = ctk.CTkLabel(
            self._statusbar, text="\u25CF", font=FONT_SMALL,
            text_color=STATUS_DOT_DISCONNECTED, anchor="w",
        )
        self._status_dot.pack(side="left", padx=(16, 4))

        self._status_conn_label = ctk.CTkLabel(
            self._statusbar, text="Not connected", font=FONT_SMALL,
            text_color=TEXT_SECONDARY, anchor="w",
        )
        self._status_conn_label.pack(side="left")

        # Right side: controller info
        self._status_info = ctk.CTkLabel(
            self._statusbar, text="", font=FONT_SMALL,
            text_color=TEXT_MUTED, anchor="e",
        )
        self._status_info.pack(side="right", padx=16)

    def _build_pages(self) -> None:
        self._pages: Dict[str, ctk.CTkFrame] = {}
        page_titles = {
            "connection": "Connection",
            "networks": "Current LAN Networks",
            "batch": "Batch Create",
            "logs": "Logs",
            "devjson": "Developer JSON",
        }

        for key in ("connection", "networks", "batch", "logs", "devjson"):
            page = ctk.CTkFrame(self._content, fg_color=SURFACE, corner_radius=0)
            self._pages[key] = page

        # Alias the page frames to the old attribute names so tab builders work
        self.tab_conn = self._pages["connection"]
        self.tab_current = self._pages["networks"]
        self.tab_batch = self._pages["batch"]
        self.tab_logs = self._pages["logs"]
        self.tab_dev = self._pages["devjson"]

        # Build tab content
        build_connection_tab(self)
        build_current_networks_tab(self)
        build_batch_tab(self)
        build_logs_tab(self)
        build_developer_tab(self)
        self._developer_tab_visible = False

    def _show_page(self, page_name: str) -> None:
        if page_name == self._current_page:
            return

        # Hide all pages
        for frame in self._pages.values():
            frame.pack_forget()

        # Show selected page
        if page_name in self._pages:
            self._pages[page_name].pack(fill="both", expand=True)

        # Update sidebar indicators
        for key, indicator in self._nav_indicators.items():
            if key == page_name:
                indicator.configure(fg_color=PRIMARY)
                self._nav_buttons[key].configure(
                    fg_color=SURFACE_SIDEBAR_ACTIVE,
                    text_color=TEXT_SIDEBAR_ACTIVE,
                )
            else:
                indicator.configure(fg_color="transparent")
                self._nav_buttons[key].configure(
                    fg_color="transparent",
                    text_color=TEXT_SIDEBAR,
                )

        # Update header
        titles = {
            "connection": "Connection",
            "networks": "Current LAN Networks",
            "batch": "Batch Create",
            "logs": "Logs",
            "devjson": "Developer JSON",
        }
        self._header_title.configure(text=titles.get(page_name, page_name))
        self._current_page = page_name

    # ── Logging ────────────────────────────────────────────────────
    def _truncate(self, text: str, limit: int = 250) -> str:
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."

    def _append_numbered_lines(self, widget, text: str, *, counter_attr: str) -> None:
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
            # Add dev nav item to sidebar
            self._create_nav_item(*DEV_NAV_ITEM)
            self._developer_tab_visible = True
            self._log("Developer mode enabled.")
        elif not enabled and self._developer_tab_visible:
            # Remove dev nav item from sidebar
            key = DEV_NAV_ITEM[0]
            if key in self._nav_buttons:
                btn = self._nav_buttons.pop(key)
                btn.master.destroy()
                self._nav_indicators.pop(key, None)
            if self._current_page == key:
                self._show_page("connection")
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

    # ── Status bar updates ─────────────────────────────────────────
    def update_status_bar(self, connected: bool = False, info_text: str = "") -> None:
        if connected:
            self._status_dot.configure(text_color=STATUS_DOT_CONNECTED)
            self._status_conn_label.configure(text="Connected")
        else:
            self._status_dot.configure(text_color=STATUS_DOT_DISCONNECTED)
            self._status_conn_label.configure(text="Not connected")
        if info_text:
            self._status_info.configure(text=info_text)

    # ── Queue polling ──────────────────────────────────────────────
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
                    max_val = max(total, 1)
                    self.prog.set(done / max_val)
                    self.lbl_batch_state.configure(text=text)
                elif typ == "vlan_progress":
                    done, total, text = payload
                    max_val = max(total, 1)
                    self.vlan_prog.set(done / max_val)
                    self.lbl_vlan_batch_state.configure(text=text)
                elif typ == "devjson":
                    self._devjson_log(payload)
                elif typ == "error":
                    messagebox.showerror("Error", str(payload))
                elif typ == "info":
                    messagebox.showinfo("Info", str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _run_bg(self, fn, *, disable_buttons: list) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        for button in disable_buttons:
            button.configure(state="disabled")

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
