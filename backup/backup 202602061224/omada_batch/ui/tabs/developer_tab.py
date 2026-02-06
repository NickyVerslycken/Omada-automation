from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_developer_tab(app: "App") -> None:
    frame = ttk.Frame(app.tab_dev, padding=10)
    frame.pack(fill="both", expand=True)

    top = ttk.Frame(frame)
    top.pack(fill="x")
    ttk.Button(top, text="Clear output", command=app.on_clear_devjson).pack(side="left")

    app.txt_devjson = tk.Text(frame, wrap="none")
    app.txt_devjson.pack(fill="both", expand=True)
