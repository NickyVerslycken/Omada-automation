from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from omada_batch.ui.theme import (
    BORDER_LIGHT,
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
    BTN_CORNER_RADIUS,
    BTN_HEIGHT,
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


def _section_label(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY, anchor="w",
    )


def _field_label(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=FONT_LABEL,
        text_color=TEXT_SECONDARY, anchor="w",
    )


def build_connection_tab(app: "App") -> None:
    scroll = ctk.CTkScrollableFrame(app.tab_conn, fg_color=SURFACE, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=24, pady=16)

    # ── Card 1: Controller Profiles ────────────────────────────────
    card1 = _card(scroll)
    card1.pack(fill="x", pady=(0, 16))
    inner1 = ctk.CTkFrame(card1, fg_color="transparent")
    inner1.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    _section_label(inner1, "Controller Profiles").pack(fill="x")
    ctk.CTkLabel(
        inner1, text="Manage and switch between saved Omada environments.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0, 12))

    profile_row = ctk.CTkFrame(inner1, fg_color="transparent")
    profile_row.pack(fill="x")

    app.var_controller_profile = tk.StringVar()
    app.cmb_controller_profiles = ttk.Combobox(
        profile_row, textvariable=app.var_controller_profile,
        width=50, state="readonly", style="Modern.TCombobox",
    )
    app.cmb_controller_profiles.pack(side="left", fill="x", expand=True, padx=(0, 8))
    app.cmb_controller_profiles.bind("<<ComboboxSelected>>", app.on_controller_profile_selected)

    app.btn_remove_profile = ctk.CTkButton(
        profile_row, text="Remove", command=app.on_remove_controller_profile,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, width=90,
        font=FONT_LABEL,
    )
    app.btn_remove_profile.pack(side="left")

    btn_row = ctk.CTkFrame(inner1, fg_color="transparent")
    btn_row.pack(fill="x", pady=(10, 0))

    app.btn_save_profile = ctk.CTkButton(
        btn_row, text="Save Profile", command=app.on_save_controller_profile,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=BTN_HEIGHT, font=FONT_LABEL_BOLD,
    )
    app.btn_save_profile.pack(side="left", padx=(0, 8))

    app.btn_import_profiles = ctk.CTkButton(
        btn_row, text="Import...", command=app.on_import_controller_profiles,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
    )
    app.btn_import_profiles.pack(side="left", padx=(0, 8))

    app.btn_export_profiles = ctk.CTkButton(
        btn_row, text="Export...", command=app.on_export_controller_profiles,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
    )
    app.btn_export_profiles.pack(side="left")

    # ── Card 2: Endpoint Configuration ─────────────────────────────
    card2 = _card(scroll)
    card2.pack(fill="x", pady=(0, 16))
    inner2 = ctk.CTkFrame(card2, fg_color="transparent")
    inner2.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    _section_label(inner2, "Endpoint Configuration").pack(fill="x")
    ctk.CTkLabel(
        inner2, text="Authentication details for the Omada API Gateway.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0, 16))

    # Two-column form using grid
    form = ctk.CTkFrame(inner2, fg_color="transparent")
    form.pack(fill="x")
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)

    # Row 1: URL + Omada ID
    _field_label(form, "CONTROLLER BASE URL").grid(row=0, column=0, sticky="w", padx=(0, 12))
    app.var_url = tk.StringVar(value="https://")
    ctk.CTkEntry(
        form, textvariable=app.var_url, font=FONT_BODY,
        placeholder_text="https://omada.example.com:8043",
        height=36, corner_radius=BTN_CORNER_RADIUS,
    ).grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

    _field_label(form, "OMADA ID / ORGANIZATION ID").grid(row=0, column=1, sticky="w")
    app.var_omada_id = tk.StringVar()
    ctk.CTkEntry(
        form, textvariable=app.var_omada_id, font=FONT_BODY,
        placeholder_text="Auto-detected via /api/info",
        height=36, corner_radius=BTN_CORNER_RADIUS,
    ).grid(row=1, column=1, sticky="ew", pady=(0, 12))

    # Row 2: Client ID + Client Secret
    _field_label(form, "CLIENT ID").grid(row=2, column=0, sticky="w", padx=(0, 12))
    app.var_client_id = tk.StringVar()
    ctk.CTkEntry(
        form, textvariable=app.var_client_id, font=FONT_BODY,
        height=36, corner_radius=BTN_CORNER_RADIUS,
    ).grid(row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

    _field_label(form, "CLIENT SECRET").grid(row=2, column=1, sticky="w")
    app.var_client_secret = tk.StringVar()
    ctk.CTkEntry(
        form, textvariable=app.var_client_secret, font=FONT_BODY,
        show="*", height=36, corner_radius=BTN_CORNER_RADIUS,
    ).grid(row=3, column=1, sticky="ew", pady=(0, 12))

    # SSL checkbox
    app.var_verify_ssl = tk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        form, text="Verify SSL certificate", variable=app.var_verify_ssl,
        font=FONT_LABEL, text_color=TEXT_SECONDARY,
        checkbox_width=18, checkbox_height=18, corner_radius=4,
    ).grid(row=4, column=0, sticky="w", pady=(0, 4))

    # ── Connection actions ─────────────────────────────────────────
    conn_row = ctk.CTkFrame(inner2, fg_color="transparent")
    conn_row.pack(fill="x", pady=(8, 0))

    app.btn_connect = ctk.CTkButton(
        conn_row, text="\u26A1  Connect to Omada", command=app.on_connect,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=38, font=FONT_BODY_BOLD, width=200,
    )
    app.btn_connect.pack(side="left", padx=(0, 8))

    app.btn_disconnect = ctk.CTkButton(
        conn_row, text="Disconnect", command=app.on_disconnect,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=38, font=FONT_BODY,
        state="disabled",
    )
    app.btn_disconnect.pack(side="left", padx=(0, 16))

    app.lbl_conn_state = ctk.CTkLabel(
        conn_row, text="Not connected", font=FONT_BODY,
        text_color=TEXT_MUTED, anchor="w",
    )
    app.lbl_conn_state.pack(side="left")

    # ── Card 3: Site Selection ─────────────────────────────────────
    card3 = _card(scroll)
    card3.pack(fill="x", pady=(0, 16))
    inner3 = ctk.CTkFrame(card3, fg_color="transparent")
    inner3.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

    _section_label(inner3, "Site Selection").pack(fill="x")
    ctk.CTkLabel(
        inner3, text="Connect to a controller first to list available sites for batch operations.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0, 12))

    site_row = ctk.CTkFrame(inner3, fg_color="transparent")
    site_row.pack(fill="x")

    _field_label(site_row, "SITE").pack(side="left", padx=(0, 8))
    app.var_site = tk.StringVar()
    app.cmb_sites = ttk.Combobox(
        site_row, textvariable=app.var_site,
        width=48, state="readonly", style="Modern.TCombobox",
    )
    app.cmb_sites.pack(side="left", fill="x", expand=True, padx=(0, 8))
    app.cmb_sites.bind("<<ComboboxSelected>>", app.on_site_selected)

    app.btn_refresh_sites = ctk.CTkButton(
        site_row, text="Refresh Sites", command=app.on_refresh_sites,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
        state="disabled",
    )
    app.btn_refresh_sites.pack(side="left")
