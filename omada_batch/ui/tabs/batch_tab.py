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
    FONT_BODY_BOLD,
    FONT_HEADING_SM,
    FONT_LABEL,
    FONT_LABEL_BOLD,
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


def _card(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=SURFACE_CARD,
        corner_radius=CARD_CORNER_RADIUS,
        border_width=1,
        border_color=BORDER_LIGHT,
        **kwargs,
    )


def build_batch_tab(app: "App") -> None:
    scroll = ctk.CTkScrollableFrame(app.tab_batch, fg_color=SURFACE, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=24, pady=16)

    # ── Card 1: Batch Parameters ───────────────────────────────────
    card1 = _card(scroll)
    card1.pack(fill="x", pady=(0, 16))
    inner1 = ctk.CTkFrame(card1, fg_color="transparent")
    inner1.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    ctk.CTkLabel(
        inner1, text="Batch Parameters", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(fill="x")
    ctk.CTkLabel(
        inner1, text="Configure the network range, VLAN, and DHCP settings for batch creation.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0, 16))

    form = ctk.CTkFrame(inner1, fg_color="transparent")
    form.pack(fill="x")
    for col in range(4):
        form.grid_columnconfigure(col, weight=1)

    # Row 0: Name prefix + Start subnet IP
    ctk.CTkLabel(form, text="NAME PREFIX", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 12))
    app.var_name_prefix = tk.StringVar(value="LAN")
    ctk.CTkEntry(form, textvariable=app.var_name_prefix, width=140, font=FONT_BODY, height=34, corner_radius=BTN_CORNER_RADIUS).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="START SUBNET IP", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 12))
    app.var_start_ip = tk.StringVar(value="10.0.0.0")
    ctk.CTkEntry(form, textvariable=app.var_start_ip, width=160, font=FONT_BODY, height=34, corner_radius=BTN_CORNER_RADIUS).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="PREFIX LENGTH (CIDR)", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=2, sticky="w", padx=(0, 12))
    app.var_prefix = tk.IntVar(value=24)
    ttk.Spinbox(form, from_=8, to=30, textvariable=app.var_prefix, width=8, style="Modern.TSpinbox").grid(row=1, column=2, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="NUMBER OF LANs", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=3, sticky="w")
    app.var_count = tk.IntVar(value=20)
    ttk.Spinbox(form, from_=1, to=200, textvariable=app.var_count, width=8, style="Modern.TSpinbox").grid(row=1, column=3, sticky="w", pady=(0, 10))

    # Row 1: VLAN + DHCP offsets
    ctk.CTkLabel(form, text="START VLAN", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 12))
    app.var_start_vlan = tk.IntVar(value=100)
    ttk.Spinbox(form, from_=1, to=4090, textvariable=app.var_start_vlan, width=8, style="Modern.TSpinbox").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="DHCP START OFFSET", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=2, column=1, sticky="w", padx=(0, 12))
    app.var_dhcp_start_off = tk.IntVar(value=10)
    ttk.Spinbox(form, from_=2, to=200, textvariable=app.var_dhcp_start_off, width=8, style="Modern.TSpinbox").grid(row=3, column=1, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="DHCP END OFFSET", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=2, column=2, sticky="w", padx=(0, 12))
    app.var_dhcp_end_off = tk.IntVar(value=10)
    ttk.Spinbox(form, from_=2, to=200, textvariable=app.var_dhcp_end_off, width=8, style="Modern.TSpinbox").grid(row=3, column=2, sticky="w", padx=(0, 12), pady=(0, 10))

    # DHCP server row
    dhcp_row = ctk.CTkFrame(inner1, fg_color="transparent")
    dhcp_row.pack(fill="x", pady=(4, 0))

    ctk.CTkLabel(dhcp_row, text="DHCP SERVER", font=FONT_LABEL, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 8))
    app.var_gateway_batch = tk.StringVar()
    app.cmb_gateways_batch = ttk.Combobox(
        dhcp_row, textvariable=app.var_gateway_batch,
        width=42, state="disabled", style="Modern.TCombobox",
    )
    app.cmb_gateways_batch.pack(side="left", padx=(0, 8))
    app.cmb_gateways_batch.bind("<<ComboboxSelected>>", app.on_gateway_selected_batch)

    app.btn_refresh_gateways_batch = ctk.CTkButton(
        dhcp_row, text="Refresh DHCP", command=app.on_refresh_gateways,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_refresh_gateways_batch.pack(side="left")

    # ── Action buttons ─────────────────────────────────────────────
    btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
    btn_row.pack(fill="x", pady=(0, 12))

    app.btn_preview = ctk.CTkButton(
        btn_row, text="\u25B6  Generate Preview", command=app.on_generate_preview,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=PRIMARY, border_width=1, border_color=PRIMARY,
        corner_radius=BTN_CORNER_RADIUS, height=38, font=FONT_BODY_BOLD,
        state="disabled",
    )
    app.btn_preview.pack(side="left", padx=(0, 8))

    app.btn_push = ctk.CTkButton(
        btn_row, text="\u26A1  Push to Controller", command=app.on_push_plan,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=38, font=FONT_BODY_BOLD, state="disabled",
    )
    app.btn_push.pack(side="left", padx=(0, 8))

    app.btn_export_plan = ctk.CTkButton(
        btn_row, text="Export JSON...", command=app.on_export_plan,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=38, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_export_plan.pack(side="left", padx=(0, 16))

    app.prog = ctk.CTkProgressBar(
        btn_row, progress_color=PRIMARY, fg_color=SURFACE_ALT,
        height=8, corner_radius=4,
    )
    app.prog.pack(side="right", fill="x", expand=True)
    app.prog.set(0)

    app.lbl_batch_state = ctk.CTkLabel(
        scroll, text="", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_batch_state.pack(anchor="w", pady=(0, 8))

    # ── Card 2: LAN Interface Selection ────────────────────────────
    card2 = _card(scroll)
    card2.pack(fill="x", pady=(0, 16))
    inner2 = ctk.CTkFrame(card2, fg_color="transparent")
    inner2.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    ctk.CTkLabel(
        inner2, text="LAN Interface Selection", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(fill="x")

    app.lbl_batch_iface_state = ctk.CTkLabel(
        inner2,
        text="Generate preview and select DHCP server to load interface/port mapping in this tab.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_batch_iface_state.pack(anchor="w", pady=(4, 8))

    iface_container = ctk.CTkFrame(inner2, fg_color="transparent")
    iface_container.pack(fill="both", expand=True)
    iface_container.grid_columnconfigure(0, weight=1)
    iface_container.grid_rowconfigure(0, weight=1)

    app.canvas_batch_iface = tk.Canvas(iface_container, highlightthickness=0, height=170, bg=SURFACE_CARD)
    app.scr_batch_iface_y = ttk.Scrollbar(iface_container, orient="vertical", command=app.canvas_batch_iface.yview)
    app.scr_batch_iface_x = ttk.Scrollbar(iface_container, orient="horizontal", command=app.canvas_batch_iface.xview)
    app.frm_batch_iface_inner = ttk.Frame(app.canvas_batch_iface)

    app.canvas_batch_iface.configure(yscrollcommand=app.scr_batch_iface_y.set, xscrollcommand=app.scr_batch_iface_x.set)
    app.canvas_batch_iface.grid(row=0, column=0, sticky="nsew")
    app.scr_batch_iface_y.grid(row=0, column=1, sticky="ns")
    app.scr_batch_iface_x.grid(row=1, column=0, sticky="ew")

    app._batch_iface_canvas_window = app.canvas_batch_iface.create_window((0, 0), window=app.frm_batch_iface_inner, anchor="nw")
    app.frm_batch_iface_inner.bind(
        "<Configure>",
        lambda _e: app.canvas_batch_iface.configure(scrollregion=app.canvas_batch_iface.bbox("all")),
    )

    app._batch_iface_catalog = []
    app._batch_iface_row_vars = {}
    app._batch_iface_apply_all_vars = []

    # ── Card 3: Plan Preview Table ─────────────────────────────────
    tree_card = _card(scroll)
    tree_card.pack(fill="both", expand=True, pady=(0, 8))

    tree_header = ctk.CTkFrame(tree_card, fg_color="transparent")
    tree_header.pack(fill="x", padx=CARD_PADDING, pady=(CARD_PADDING, 8))
    ctk.CTkLabel(
        tree_header, text="Plan Preview", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(side="left")
    ctk.CTkLabel(
        tree_header, text="Staged entries based on your current batch parameters.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(side="left", padx=(12, 0))

    tree_wrap = ctk.CTkFrame(tree_card, fg_color="transparent")
    tree_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    tree_wrap.grid_columnconfigure(0, weight=1)
    tree_wrap.grid_rowconfigure(0, weight=1)

    cols = ("#", "name", "vlan", "subnet", "gateway", "dhcp_start", "dhcp_end")
    app.tree_plan = ttk.Treeview(
        tree_wrap, columns=cols, show="headings", height=14,
        style="Modern.Treeview",
    )
    for col, width in zip(cols, (40, 200, 70, 150, 120, 120, 120)):
        app.tree_plan.heading(col, text=col.upper())
        app.tree_plan.column(col, width=width, anchor="w")

    app.scr_tree_plan_y = ttk.Scrollbar(tree_wrap, orient="vertical", command=app.tree_plan.yview)
    app.scr_tree_plan_x = ttk.Scrollbar(tree_wrap, orient="horizontal", command=app.tree_plan.xview)
    app.tree_plan.configure(yscrollcommand=app.scr_tree_plan_y.set, xscrollcommand=app.scr_tree_plan_x.set)

    app.tree_plan.grid(row=0, column=0, sticky="nsew")
    app.scr_tree_plan_y.grid(row=0, column=1, sticky="ns")
    app.scr_tree_plan_x.grid(row=1, column=0, sticky="ew")

    if hasattr(app, "_refresh_batch_interface_selection_ui"):
        app._refresh_batch_interface_selection_ui()
