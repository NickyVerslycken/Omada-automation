from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_logs_tab(app: "App") -> None:
    frame = ttk.Frame(app.tab_logs, padding=10)
    frame.pack(fill="both", expand=True)

    top = ttk.Frame(frame)
    top.pack(fill="x")
    ttk.Button(top, text="Clear log", command=app.on_clear_log).pack(side="left")

    app.txt_logs = tk.Text(frame)
    app.txt_logs.pack(fill="both", expand=True)
    app._log("Ready.")
