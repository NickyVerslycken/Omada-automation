from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_batch_tab(app: "App") -> None:
    frame = ttk.Frame(app.tab_batch, padding=10)
    frame.pack(fill="both", expand=True)

    form = ttk.LabelFrame(frame, text="Batch parameters", padding=10)
    form.pack(fill="x")

    row = 0
    ttk.Label(form, text="Name prefix").grid(row=row, column=0, sticky="w")
    app.var_name_prefix = tk.StringVar(value="LAN")
    ttk.Entry(form, textvariable=app.var_name_prefix, width=18).grid(row=row, column=1, sticky="w")

    ttk.Label(form, text="Start subnet IP").grid(row=row, column=2, sticky="w", padx=(15, 0))
    app.var_start_ip = tk.StringVar(value="10.0.0.0")
    ttk.Entry(form, textvariable=app.var_start_ip, width=18).grid(row=row, column=3, sticky="w")
    row += 1

    ttk.Label(form, text="Prefix length (CIDR)").grid(row=row, column=0, sticky="w", pady=(6, 0))
    app.var_prefix = tk.IntVar(value=24)
    ttk.Spinbox(form, from_=8, to=30, textvariable=app.var_prefix, width=6).grid(row=row, column=1, sticky="w", pady=(6, 0))

    ttk.Label(form, text="Number of LANs/VLANs").grid(row=row, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
    app.var_count = tk.IntVar(value=20)
    ttk.Spinbox(form, from_=1, to=200, textvariable=app.var_count, width=8).grid(row=row, column=3, sticky="w", pady=(6, 0))
    row += 1

    ttk.Label(form, text="Start VLAN").grid(row=row, column=0, sticky="w", pady=(6, 0))
    app.var_start_vlan = tk.IntVar(value=100)
    ttk.Spinbox(form, from_=1, to=4090, textvariable=app.var_start_vlan, width=8).grid(row=row, column=1, sticky="w", pady=(6, 0))

    ttk.Label(form, text="DHCP start offset").grid(row=row, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
    app.var_dhcp_start_off = tk.IntVar(value=10)
    ttk.Spinbox(form, from_=2, to=200, textvariable=app.var_dhcp_start_off, width=8).grid(row=row, column=3, sticky="w", pady=(6, 0))
    row += 1

    ttk.Label(form, text="DHCP end offset (from broadcast)").grid(row=row, column=0, sticky="w", pady=(6, 0))
    app.var_dhcp_end_off = tk.IntVar(value=10)
    ttk.Spinbox(form, from_=2, to=200, textvariable=app.var_dhcp_end_off, width=8).grid(row=row, column=1, sticky="w", pady=(6, 0))
    row += 1

    ttk.Label(form, text="DHCP server").grid(row=row, column=0, sticky="w", pady=(6, 0))
    app.var_gateway_batch = tk.StringVar()
    app.cmb_gateways_batch = ttk.Combobox(form, textvariable=app.var_gateway_batch, width=46, state="disabled")
    app.cmb_gateways_batch.grid(row=row, column=1, columnspan=2, sticky="w", pady=(6, 0))
    app.cmb_gateways_batch.bind("<<ComboboxSelected>>", app.on_gateway_selected_batch)

    app.btn_refresh_gateways_batch = ttk.Button(
        form,
        text="Refresh DHCP servers",
        command=app.on_refresh_gateways,
        state="disabled",
    )
    app.btn_refresh_gateways_batch.grid(row=row, column=3, sticky="w", pady=(6, 0))

    btns = ttk.Frame(frame)
    btns.pack(fill="x", pady=(10, 0))

    app.btn_preview = ttk.Button(btns, text="Generate preview", command=app.on_generate_preview, state="disabled")
    app.btn_preview.pack(side="left")

    app.btn_push = ttk.Button(btns, text="Push to controller", command=app.on_push_plan, state="disabled")
    app.btn_push.pack(side="left", padx=(8, 0))

    app.btn_export_plan = ttk.Button(btns, text="Export preview JSON...", command=app.on_export_plan, state="disabled")
    app.btn_export_plan.pack(side="left", padx=(8, 0))

    app.prog = ttk.Progressbar(btns, mode="determinate")
    app.prog.pack(side="right", fill="x", expand=True, padx=(10, 0))

    app.lbl_batch_state = ttk.Label(frame, text="")
    app.lbl_batch_state.pack(anchor="w", pady=(6, 0))

    cols = ("#", "name", "vlan", "subnet", "gateway", "dhcp_start", "dhcp_end")
    app.tree_plan = ttk.Treeview(frame, columns=cols, show="headings", height=14)
    for col, width in zip(cols, (40, 200, 70, 150, 120, 120, 120)):
        app.tree_plan.heading(col, text=col)
        app.tree_plan.column(col, width=width, anchor="w")
    app.tree_plan.pack(fill="both", expand=True, pady=(10, 0))

    for col in range(4):
        form.grid_columnconfigure(col, weight=1 if col in (1, 3) else 0)
