from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from omada_batch.ui.theme import (
    BORDER_LIGHT,
    BTN_CORNER_RADIUS,
    BTN_HEIGHT,
    CARD_CORNER_RADIUS,
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


def prompt_interface_selection(
    parent: tk.Misc,
    plan: List[Any],
    interfaces: List[Dict[str, str]],
    display_name_fn: Callable[[Dict[str, str]], str],
) -> Optional[Dict[int, List[str]]]:
    if not interfaces:
        messagebox.showwarning("Missing", "No LAN interfaces are available.")
        return None

    win = ctk.CTkToplevel(parent)
    win.title("Select LAN Interfaces")
    win.transient(parent)
    win.grab_set()
    win.geometry("700x500")
    win.configure(fg_color=SURFACE)

    # Header
    header = ctk.CTkFrame(win, fg_color=SURFACE_CARD, height=48, corner_radius=0)
    header.pack(fill="x")
    header.pack_propagate(False)
    ctk.CTkLabel(
        header, text="Select LAN Interfaces", font=FONT_HEADING_SM,
        text_color=TEXT_PRIMARY,
    ).pack(side="left", padx=16)

    ctk.CTkLabel(
        win, text="Choose LAN interfaces per network. Top row applies to all networks.",
        font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w",
    ).pack(fill="x", padx=16, pady=(12, 8))

    # Scrollable content
    container = ctk.CTkFrame(win, fg_color=SURFACE_CARD, corner_radius=CARD_CORNER_RADIUS,
                              border_width=1, border_color=BORDER_LIGHT)
    container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

    canvas = tk.Canvas(container, highlightthickness=0, bg=SURFACE_CARD)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Table header
    header_frame = ttk.Frame(inner)
    header_frame.grid(row=0, column=0, sticky="w")
    ttk.Label(header_frame, text="Network").grid(row=0, column=0, sticky="w", padx=(8, 10))

    apply_all_vars: List[tk.BooleanVar] = []
    for c, iface in enumerate(interfaces, start=1):
        ttk.Label(header_frame, text=display_name_fn(iface)).grid(row=0, column=c, padx=6, sticky="w")

    row_vars: Dict[int, List[tk.BooleanVar]] = {}

    apply_row = ttk.Frame(inner)
    apply_row.grid(row=1, column=0, sticky="w", pady=(4, 8))
    ttk.Label(apply_row, text="Apply to all").grid(row=0, column=0, sticky="w", padx=(8, 10))

    def apply_all_changed(col: int):
        val = apply_all_vars[col].get()
        for vars_ in row_vars.values():
            vars_[col].set(val)

    for c, _iface in enumerate(interfaces):
        v = tk.BooleanVar(value=True)
        apply_all_vars.append(v)
        ttk.Checkbutton(apply_row, variable=v, command=lambda col=c: apply_all_changed(col)).grid(row=0, column=c + 1, padx=6)

    for r, p in enumerate(plan, start=2):
        row = ttk.Frame(inner)
        row.grid(row=r, column=0, sticky="w", pady=2)
        ttk.Label(row, text=f"{p.name} (VLAN {p.vlan_id})").grid(row=0, column=0, sticky="w", padx=(8, 10))
        vars_for_row: List[tk.BooleanVar] = []
        for c, _iface in enumerate(interfaces):
            v = tk.BooleanVar(value=True)
            vars_for_row.append(v)
            ttk.Checkbutton(row, variable=v).grid(row=0, column=c + 1, padx=6)
        row_vars[p.index] = vars_for_row

    # Action buttons
    btns = ctk.CTkFrame(win, fg_color="transparent")
    btns.pack(fill="x", padx=16, pady=(0, 12))

    result: Dict[str, Any] = {"ok": False, "mapping": None}

    def on_ok():
        mapping: Dict[int, List[str]] = {}
        for p in plan:
            vars_ = row_vars.get(p.index, [])
            ids: List[str] = []
            for var, iface in zip(vars_, interfaces):
                if var.get():
                    iid = iface.get("id")
                    if iid:
                        ids.append(str(iid))
            if not ids:
                messagebox.showwarning("Missing", f"Select at least one interface for {p.name}.")
                return
            mapping[p.index] = ids
        result["ok"] = True
        result["mapping"] = mapping
        win.destroy()

    def on_cancel():
        win.destroy()

    ctk.CTkButton(
        btns, text="Cancel", command=on_cancel,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
    ).pack(side="right", padx=(8, 0))

    ctk.CTkButton(
        btns, text="OK", command=on_ok,
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
        text_color=TEXT_ON_PRIMARY, corner_radius=BTN_CORNER_RADIUS,
        height=BTN_HEIGHT, font=FONT_BODY_BOLD, width=80,
    ).pack(side="right")

    win.wait_window()
    if result["ok"]:
        return result["mapping"]
    return None
