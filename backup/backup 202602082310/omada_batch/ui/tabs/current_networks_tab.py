from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_current_networks_tab(app: "App") -> None:
    frame = ttk.Frame(app.tab_current, padding=10)
    frame.pack(fill="both", expand=True)

    top = ttk.Frame(frame)
    top.pack(fill="x")

    app.btn_fetch_networks = ttk.Button(top, text="Refresh LAN networks", command=app.on_fetch_networks, state="disabled")
    app.btn_fetch_networks.pack(side="left")

    ttk.Label(top, text="DHCP server").pack(side="left", padx=(12, 4))
    app.var_gateway_current = tk.StringVar()
    app.cmb_gateways_current = ttk.Combobox(top, textvariable=app.var_gateway_current, width=40, state="disabled")
    app.cmb_gateways_current.pack(side="left")
    app.cmb_gateways_current.bind("<<ComboboxSelected>>", app.on_gateway_selected_current)

    app.btn_refresh_gateways_current = ttk.Button(
        top,
        text="Refresh DHCP servers",
        command=app.on_refresh_gateways,
        state="disabled",
    )
    app.btn_refresh_gateways_current.pack(side="left", padx=(8, 0))

    app.btn_export_networks = ttk.Button(top, text="Export JSON...", command=app.on_export_networks, state="disabled")
    app.btn_export_networks.pack(side="left", padx=(8, 0))

    app.lbl_networks_state = ttk.Label(top, text="")
    app.lbl_networks_state.pack(side="left", padx=(10, 0))

    cols = ("name", "vlan", "gatewaySubnet", "dhcp_start", "dhcp_end", "id")
    app.tree_networks = ttk.Treeview(frame, columns=cols, show="headings", height=18)
    for col, width in zip(cols, (220, 70, 170, 120, 120, 260)):
        app.tree_networks.heading(col, text=col)
        app.tree_networks.column(col, width=width, anchor="w")
    app.tree_networks.pack(fill="both", expand=True, pady=(10, 0))

    ttk.Label(frame, text="Raw JSON (selected row)").pack(anchor="w", pady=(10, 0))
    app.txt_network_raw = tk.Text(frame, height=8)
    app.txt_network_raw.pack(fill="x", expand=False)
    app.tree_networks.bind("<<TreeviewSelect>>", app._on_network_selected)

    app._networks_cache_all = []
    app._networks_cache = []
