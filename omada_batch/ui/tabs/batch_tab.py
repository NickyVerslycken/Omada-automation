from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict

import customtkinter as ctk

from omada_batch.ui.tabs.batch_networks_tab import build_batch_networks_subpage
from omada_batch.ui.tabs.batch_vlan_tab import build_batch_vlan_subpage
from omada_batch.ui.theme import (
    FONT_BODY_BOLD,
    FONT_LABEL,
    PRIMARY,
    SURFACE,
    SURFACE_ALT,
    SURFACE_CARD,
    TEXT_MUTED,
    TEXT_PRIMARY,
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

    # ── Segmented switcher bar ────────────────────────────────────
    switcher_bar = ctk.CTkFrame(container, fg_color=SURFACE_CARD, height=48, corner_radius=0)
    switcher_bar.pack(fill="x")
    switcher_bar.pack_propagate(False)

    labels = [label for _, label, _ in BATCH_SUBPAGES]
    app._batch_subpage_var = tk.StringVar(value=labels[0])
    seg = ctk.CTkSegmentedButton(
        switcher_bar,
        values=labels,
        variable=app._batch_subpage_var,
        command=lambda val: _switch_subpage(app, val),
        font=FONT_BODY_BOLD,
        selected_color=PRIMARY,
        selected_hover_color=PRIMARY,
        unselected_color=SURFACE_ALT,
        unselected_hover_color=SURFACE_ALT,
        text_color=TEXT_PRIMARY,
        text_color_disabled=TEXT_MUTED,
        corner_radius=6,
        height=34,
    )
    seg.pack(side="left", padx=16, pady=8)

    # ── Sub-page frames ───────────────────────────────────────────
    app._batch_subpages: Dict[str, ctk.CTkFrame] = {}
    app._batch_subpage_label_to_key: Dict[str, str] = {}

    subpage_area = ctk.CTkFrame(container, fg_color=SURFACE, corner_radius=0)
    subpage_area.pack(fill="both", expand=True)

    for key, label, builder in BATCH_SUBPAGES:
        frame = ctk.CTkFrame(subpage_area, fg_color=SURFACE, corner_radius=0)
        app._batch_subpages[key] = frame
        app._batch_subpage_label_to_key[label] = key
        builder(app, frame)

    # Show first sub-page
    _switch_subpage(app, labels[0])


def _switch_subpage(app: "App", label: str) -> None:
    key = app._batch_subpage_label_to_key.get(label, "")
    for k, frame in app._batch_subpages.items():
        if k == key:
            frame.pack(fill="both", expand=True)
        else:
            frame.pack_forget()
