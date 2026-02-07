from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox


def prompt_interface_selection(
    parent: tk.Misc,
    plan: List[Any],
    interfaces: List[Dict[str, str]],
    display_name_fn: Callable[[Dict[str, str]], str],
) -> Optional[Dict[int, List[str]]]:
    if not interfaces:
        messagebox.showwarning("Missing", "No LAN interfaces are available.")
        return None

    win = tk.Toplevel(parent)
    win.title("Select LAN interfaces for networks")
    win.transient(parent)
    win.grab_set()

    info = ttk.Label(win, text="Choose LAN interfaces per network. Top row applies to all networks.")
    info.pack(anchor="w", padx=10, pady=(10, 6))

    container = ttk.Frame(win)
    container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    header = ttk.Frame(inner)
    header.grid(row=0, column=0, sticky="w")
    ttk.Label(header, text="Network").grid(row=0, column=0, sticky="w", padx=(0, 10))

    apply_all_vars: List[tk.BooleanVar] = []
    for c, iface in enumerate(interfaces, start=1):
        ttk.Label(header, text=display_name_fn(iface)).grid(row=0, column=c, padx=6, sticky="w")

    row_vars: Dict[int, List[tk.BooleanVar]] = {}

    apply_row = ttk.Frame(inner)
    apply_row.grid(row=1, column=0, sticky="w", pady=(4, 8))
    ttk.Label(apply_row, text="Apply to all").grid(row=0, column=0, sticky="w", padx=(0, 10))

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
        ttk.Label(row, text=f"{p.name} (VLAN {p.vlan_id})").grid(row=0, column=0, sticky="w", padx=(0, 10))
        vars_for_row: List[tk.BooleanVar] = []
        for c, _iface in enumerate(interfaces):
            v = tk.BooleanVar(value=True)
            vars_for_row.append(v)
            ttk.Checkbutton(row, variable=v).grid(row=0, column=c + 1, padx=6)
        row_vars[p.index] = vars_for_row

    btns = ttk.Frame(win)
    btns.pack(fill="x", padx=10, pady=(0, 10))

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

    ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(6, 0))
    ttk.Button(btns, text="OK", command=on_ok).pack(side="right")

    win.wait_window()
    if result["ok"]:
        return result["mapping"]
    return None
