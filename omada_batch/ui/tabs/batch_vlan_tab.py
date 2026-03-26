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


def build_batch_vlan_subpage(app: "App", parent: ctk.CTkFrame) -> None:
    scroll = ctk.CTkScrollableFrame(parent, fg_color=SURFACE, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=24, pady=16)

    # ── Card 1: VLAN Parameters ───────────────────────────────────
    card1 = _card(scroll)
    card1.pack(fill="x", pady=(0, 16))
    inner1 = ctk.CTkFrame(card1, fg_color="transparent")
    inner1.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    ctk.CTkLabel(
        inner1, text="VLAN Parameters", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(fill="x")
    ctk.CTkLabel(
        inner1, text="Create VLAN-only networks without DHCP. Select gateway ports per VLAN.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0, 16))

    form = ctk.CTkFrame(inner1, fg_color="transparent")
    form.pack(fill="x")
    for col in range(3):
        form.grid_columnconfigure(col, weight=1)

    ctk.CTkLabel(form, text="NAME PREFIX", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 12))
    app.var_vlan_name_prefix = tk.StringVar(value="VLAN")
    ctk.CTkEntry(form, textvariable=app.var_vlan_name_prefix, width=140, font=FONT_BODY, height=34, corner_radius=BTN_CORNER_RADIUS).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="START VLAN", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 12))
    app.var_vlan_start_vlan = tk.IntVar(value=100)
    ttk.Spinbox(form, from_=1, to=4090, textvariable=app.var_vlan_start_vlan, width=8, style="Modern.TSpinbox").grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 10))

    ctk.CTkLabel(form, text="NUMBER OF VLANs", font=FONT_LABEL, text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=2, sticky="w")
    app.var_vlan_count = tk.IntVar(value=10)
    ttk.Spinbox(form, from_=1, to=200, textvariable=app.var_vlan_count, width=8, style="Modern.TSpinbox").grid(row=1, column=2, sticky="w", pady=(0, 10))

    # Gateway device row
    gw_row = ctk.CTkFrame(inner1, fg_color="transparent")
    gw_row.pack(fill="x", pady=(4, 0))

    ctk.CTkLabel(gw_row, text="GATEWAY DEVICE", font=FONT_LABEL, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 8))
    app.var_vlan_gateway = tk.StringVar()
    app.cmb_vlan_gateway = ttk.Combobox(
        gw_row, textvariable=app.var_vlan_gateway,
        width=42, state="disabled", style="Modern.TCombobox",
    )
    app.cmb_vlan_gateway.pack(side="left", padx=(0, 8))
    app.cmb_vlan_gateway.bind("<<ComboboxSelected>>", app.on_vlan_gateway_selected)

    app.btn_vlan_refresh_gateways = ctk.CTkButton(
        gw_row, text="Refresh Devices", command=app.on_refresh_gateways,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_vlan_refresh_gateways.pack(side="left")

    # ── Action buttons ─────────────────────────────────────────────
    btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
    btn_row.pack(fill="x", pady=(0, 12))

    app.btn_vlan_preview = ctk.CTkButton(
        btn_row, text="\u25B6  Generate Preview", command=app.on_vlan_generate_preview,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=PRIMARY, border_width=1, border_color=PRIMARY,
        corner_radius=BTN_CORNER_RADIUS, height=38, font=FONT_BODY_BOLD,
        state="disabled",
    )
    app.btn_vlan_preview.pack(side="left", padx=(0, 8))

    app.btn_vlan_push = ctk.CTkButton(
        btn_row, text="\u26A1  Push to Controller", command=app.on_vlan_push_plan,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=38, font=FONT_BODY_BOLD, state="disabled",
    )
    app.btn_vlan_push.pack(side="left", padx=(0, 8))

    app.vlan_prog = ctk.CTkProgressBar(
        btn_row, progress_color=PRIMARY, fg_color=SURFACE_ALT,
        height=8, corner_radius=4,
    )
    app.vlan_prog.pack(side="right", fill="x", expand=True)
    app.vlan_prog.set(0)

    app.lbl_vlan_batch_state = ctk.CTkLabel(
        scroll, text="", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_vlan_batch_state.pack(anchor="w", pady=(0, 8))

    # ── Card 2: Port Selection ─────────────────────────────────────
    card2 = _card(scroll)
    card2.pack(fill="x", pady=(0, 16))
    inner2 = ctk.CTkFrame(card2, fg_color="transparent")
    inner2.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    ctk.CTkLabel(
        inner2, text="Gateway Port Selection", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(fill="x")

    app.lbl_vlan_port_state = ctk.CTkLabel(
        inner2,
        text="Generate preview and select a gateway device to configure port mapping.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_vlan_port_state.pack(anchor="w", pady=(4, 8))

    port_container = ctk.CTkFrame(inner2, fg_color="transparent")
    port_container.pack(fill="both", expand=True)
    port_container.grid_columnconfigure(0, weight=1)
    port_container.grid_rowconfigure(0, weight=1)

    app.canvas_vlan_port = tk.Canvas(port_container, highlightthickness=0, height=170, bg=SURFACE_CARD)
    app.scr_vlan_port_y = ttk.Scrollbar(port_container, orient="vertical", command=app.canvas_vlan_port.yview)
    app.scr_vlan_port_x = ttk.Scrollbar(port_container, orient="horizontal", command=app.canvas_vlan_port.xview)
    app.frm_vlan_port_inner = ttk.Frame(app.canvas_vlan_port)

    app.canvas_vlan_port.configure(yscrollcommand=app.scr_vlan_port_y.set, xscrollcommand=app.scr_vlan_port_x.set)
    app.canvas_vlan_port.grid(row=0, column=0, sticky="nsew")
    app.scr_vlan_port_y.grid(row=0, column=1, sticky="ns")
    app.scr_vlan_port_x.grid(row=1, column=0, sticky="ew")

    app._vlan_port_canvas_window = app.canvas_vlan_port.create_window((0, 0), window=app.frm_vlan_port_inner, anchor="nw")
    app.frm_vlan_port_inner.bind(
        "<Configure>",
        lambda _e: app.canvas_vlan_port.configure(scrollregion=app.canvas_vlan_port.bbox("all")),
    )

    app._vlan_port_catalog = []
    app._vlan_port_row_vars = {}
    app._vlan_port_apply_all_vars = []

    # ── Card 3: VLAN Plan Preview Table ────────────────────────────
    tree_card = _card(scroll)
    tree_card.pack(fill="both", expand=True, pady=(0, 8))

    tree_header = ctk.CTkFrame(tree_card, fg_color="transparent")
    tree_header.pack(fill="x", padx=CARD_PADDING, pady=(CARD_PADDING, 8))
    ctk.CTkLabel(
        tree_header, text="VLAN Plan Preview", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    ).pack(side="left")
    ctk.CTkLabel(
        tree_header, text="Staged VLAN entries based on your parameters.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(side="left", padx=(12, 0))

    tree_wrap = ctk.CTkFrame(tree_card, fg_color="transparent")
    tree_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    tree_wrap.grid_columnconfigure(0, weight=1)
    tree_wrap.grid_rowconfigure(0, weight=1)

    cols = ("#", "name", "vlan")
    app.tree_vlan_plan = ttk.Treeview(
        tree_wrap, columns=cols, show="headings", height=14,
        style="Modern.Treeview",
    )
    for col, width in zip(cols, (40, 300, 100)):
        app.tree_vlan_plan.heading(col, text=col.upper())
        app.tree_vlan_plan.column(col, width=width, anchor="w")

    app.scr_tree_vlan_y = ttk.Scrollbar(tree_wrap, orient="vertical", command=app.tree_vlan_plan.yview)
    app.scr_tree_vlan_x = ttk.Scrollbar(tree_wrap, orient="horizontal", command=app.tree_vlan_plan.xview)
    app.tree_vlan_plan.configure(yscrollcommand=app.scr_tree_vlan_y.set, xscrollcommand=app.scr_tree_vlan_x.set)

    app.tree_vlan_plan.grid(row=0, column=0, sticky="nsew")
    app.scr_tree_vlan_y.grid(row=0, column=1, sticky="ns")
    app.scr_tree_vlan_x.grid(row=1, column=0, sticky="ew")
