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

    body = ttk.Frame(frame)
    body.pack(fill="both", expand=True)
    app.txt_logs = tk.Text(body)
    yscroll = ttk.Scrollbar(body, orient="vertical", command=app.txt_logs.yview)
    app.txt_logs.configure(yscrollcommand=yscroll.set)
    app.txt_logs.pack(side="left", fill="both", expand=True)
    yscroll.pack(side="right", fill="y")
    app._log("Ready.")
