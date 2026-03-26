from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from omada_batch.ui.theme import (
    BORDER_LIGHT,
    BTN_CORNER_RADIUS,
    BTN_HEIGHT,
    CARD_CORNER_RADIUS,
    CARD_PADDING,
    FONT_BODY,
    FONT_HEADING_SM,
    FONT_LABEL,
    FONT_LABEL_BOLD,
    FONT_MONO,
    FONT_SMALL,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_ALT,
    SURFACE_CARD,
    TEXT_MUTED,
    TEXT_ON_PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_current_networks_tab(app: "App") -> None:
    frame = ctk.CTkFrame(app.tab_current, fg_color=SURFACE, corner_radius=0)
    frame.pack(fill="both", expand=True, padx=24, pady=16)

    # ── Toolbar ────────────────────────────────────────────────────
    toolbar = ctk.CTkFrame(frame, fg_color="transparent")
    toolbar.pack(fill="x", pady=(0, 12))

    app.btn_fetch_networks = ctk.CTkButton(
        toolbar, text="Refresh LAN Networks", command=app.on_fetch_networks,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=BTN_HEIGHT, font=FONT_LABEL_BOLD, state="disabled",
    )
    app.btn_fetch_networks.pack(side="left", padx=(0, 12))

    ctk.CTkLabel(toolbar, text="DHCP Server", font=FONT_LABEL, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 4))
    app.var_gateway_current = tk.StringVar()
    app.cmb_gateways_current = ttk.Combobox(
        toolbar, textvariable=app.var_gateway_current,
        width=35, state="disabled", style="Modern.TCombobox",
    )
    app.cmb_gateways_current.pack(side="left", padx=(0, 8))
    app.cmb_gateways_current.bind("<<ComboboxSelected>>", app.on_gateway_selected_current)

    app.btn_refresh_gateways_current = ctk.CTkButton(
        toolbar, text="Refresh DHCP", command=app.on_refresh_gateways,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_refresh_gateways_current.pack(side="left", padx=(0, 8))

    app.btn_export_networks = ctk.CTkButton(
        toolbar, text="Export JSON...", command=app.on_export_networks,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_export_networks.pack(side="left", padx=(0, 12))

    app.lbl_networks_state = ctk.CTkLabel(
        toolbar, text="", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_networks_state.pack(side="left")

    # ── Treeview card ──────────────────────────────────────────────
    tree_card = ctk.CTkFrame(
        frame, fg_color=SURFACE_CARD, corner_radius=CARD_CORNER_RADIUS,
        border_width=1, border_color=BORDER_LIGHT,
    )
    tree_card.pack(fill="both", expand=True, pady=(0, 12))

    tree_wrap = ctk.CTkFrame(tree_card, fg_color="transparent")
    tree_wrap.pack(fill="both", expand=True, padx=8, pady=8)
    tree_wrap.grid_columnconfigure(0, weight=1)
    tree_wrap.grid_rowconfigure(0, weight=1)

    cols = ("name", "vlan", "gatewaySubnet", "dhcp_start", "dhcp_end", "id")
    app.tree_networks = ttk.Treeview(
        tree_wrap, columns=cols, show="headings", height=18,
        style="Modern.Treeview",
    )
    for col, width in zip(cols, (220, 70, 170, 120, 120, 260)):
        app.tree_networks.heading(col, text=col.upper())
        app.tree_networks.column(col, width=width, anchor="w")

    app.scr_tree_networks_y = ttk.Scrollbar(tree_wrap, orient="vertical", command=app.tree_networks.yview)
    app.scr_tree_networks_x = ttk.Scrollbar(tree_wrap, orient="horizontal", command=app.tree_networks.xview)
    app.tree_networks.configure(yscrollcommand=app.scr_tree_networks_y.set, xscrollcommand=app.scr_tree_networks_x.set)

    app.tree_networks.grid(row=0, column=0, sticky="nsew")
    app.scr_tree_networks_y.grid(row=0, column=1, sticky="ns")
    app.scr_tree_networks_x.grid(row=1, column=0, sticky="ew")

    # ── Raw JSON viewer ────────────────────────────────────────────
    ctk.CTkLabel(
        frame, text="Raw JSON (selected row)", font=FONT_LABEL_BOLD,
        text_color=TEXT_SECONDARY, anchor="w",
    ).pack(anchor="w", pady=(0, 4))

    raw_card = ctk.CTkFrame(
        frame, fg_color=SURFACE_CARD, corner_radius=CARD_CORNER_RADIUS,
        border_width=1, border_color=BORDER_LIGHT,
    )
    raw_card.pack(fill="x")

    app.txt_network_raw = ctk.CTkTextbox(
        raw_card, height=140, font=FONT_MONO,
        fg_color=SURFACE_CARD, text_color=TEXT_PRIMARY,
        corner_radius=0,
    )
    app.txt_network_raw.pack(fill="x", padx=4, pady=4)

    app.tree_networks.bind("<<TreeviewSelect>>", app._on_network_selected)

    app._networks_cache_all = []
    app._networks_cache = []
