from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Dict

import customtkinter as ctk

from omada_batch.ui.tabs.batch_networks_tab import build_batch_networks_subpage
from omada_batch.ui.tabs.batch_vlan_tab import build_batch_vlan_subpage
from omada_batch.ui.theme import (
    BORDER_LIGHT,
    BTN_CORNER_RADIUS,
    FONT_BODY_BOLD,
    PRIMARY,
    PRIMARY_HOVER,
    SURFACE,
    SURFACE_ALT,
    SURFACE_CARD,
    TEXT_ON_PRIMARY,
    TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


# Registry of batch sub-pages: key -> (label, builder function).
# Add future batch types here (e.g. "ip_groups", "mac_groups", "acls").
BATCH_SUBPAGES = [
    ("networks", "Networks", build_batch_networks_subpage),
    ("vlans", "VLANs", build_batch_vlan_subpage),
]


def build_batch_tab(app: "App") -> None:
    container = ctk.CTkFrame(app.tab_batch, fg_color=SURFACE, corner_radius=0)
    container.pack(fill="both", expand=True)

    # ── Tab switcher bar ──────────────────────────────────────────
    switcher_bar = ctk.CTkFrame(container, fg_color=SURFACE_CARD, height=52, corner_radius=0)
    switcher_bar.pack(fill="x")
    switcher_bar.pack_propagate(False)

    tab_inner = ctk.CTkFrame(switcher_bar, fg_color="transparent")
    tab_inner.pack(side="left", fill="y", padx=16)

    app._batch_subpage_var = tk.StringVar(value=BATCH_SUBPAGES[0][0])
    app._batch_tab_buttons: Dict[str, ctk.CTkButton] = {}

    for key, label, _ in BATCH_SUBPAGES:
        btn = ctk.CTkButton(
            tab_inner,
            text=label,
            font=FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=SURFACE_ALT,
            text_color=TEXT_SECONDARY,
            corner_radius=BTN_CORNER_RADIUS,
            height=36,
            width=120,
            command=lambda k=key: _switch_subpage(app, k),
        )
        btn.pack(side="left", padx=(0, 6), pady=8)
        app._batch_tab_buttons[key] = btn

    # Bottom border below tab bar
    ctk.CTkFrame(container, height=1, fg_color=BORDER_LIGHT, corner_radius=0).pack(fill="x")

    # ── Sub-page frames ───────────────────────────────────────────
    app._batch_subpages: Dict[str, ctk.CTkFrame] = {}

    subpage_area = ctk.CTkFrame(container, fg_color=SURFACE, corner_radius=0)
    subpage_area.pack(fill="both", expand=True)

    for key, label, builder in BATCH_SUBPAGES:
        frame = ctk.CTkFrame(subpage_area, fg_color=SURFACE, corner_radius=0)
        app._batch_subpages[key] = frame
        builder(app, frame)

    # Show first sub-page
    _switch_subpage(app, BATCH_SUBPAGES[0][0])


def _switch_subpage(app: "App", key: str) -> None:
    app._batch_subpage_var.set(key)
    for k, frame in app._batch_subpages.items():
        if k == key:
            frame.pack(fill="both", expand=True)
            app._batch_tab_buttons[k].configure(
                fg_color=PRIMARY,
                hover_color=PRIMARY_HOVER,
                text_color=TEXT_ON_PRIMARY,
            )
        else:
            frame.pack_forget()
            app._batch_tab_buttons[k].configure(
                fg_color="transparent",
                hover_color=SURFACE_ALT,
                text_color=TEXT_SECONDARY,
            )
