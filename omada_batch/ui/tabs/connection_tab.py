from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omada_batch.ui.shell.app_shell import App


def build_connection_tab(app: "App") -> None:
    frame = ttk.Frame(app.tab_conn, padding=10)
    frame.pack(fill="both", expand=True)

    row = 0
    ttk.Label(frame, text="Saved controller profiles").grid(row=row, column=0, sticky="w")
    app.var_controller_profile = tk.StringVar()
    app.cmb_controller_profiles = ttk.Combobox(frame, textvariable=app.var_controller_profile, width=55, state="readonly")
    app.cmb_controller_profiles.grid(row=row, column=1, sticky="w")
    app.cmb_controller_profiles.bind("<<ComboboxSelected>>", app.on_controller_profile_selected)
    app.btn_remove_profile = ttk.Button(frame, text="Remove profile", command=app.on_remove_controller_profile)
    app.btn_remove_profile.grid(row=row, column=2, sticky="w")
    row += 1

    profile_actions = ttk.Frame(frame)
    profile_actions.grid(row=row, column=1, sticky="w", pady=(4, 0))
    app.btn_save_profile = ttk.Button(profile_actions, text="Save current profile", command=app.on_save_controller_profile)
    app.btn_save_profile.pack(side="left")
    app.btn_import_profiles = ttk.Button(profile_actions, text="Import profiles...", command=app.on_import_controller_profiles)
    app.btn_import_profiles.pack(side="left", padx=(8, 0))
    app.btn_export_profiles = ttk.Button(profile_actions, text="Export profiles...", command=app.on_export_controller_profiles)
    app.btn_export_profiles.pack(side="left", padx=(8, 0))
    row += 1

    ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
    row += 1

    ttk.Label(frame, text="Controller base URL (example: https://omada:8043)").grid(row=row, column=0, sticky="w")
    app.var_url = tk.StringVar(value="https://")
    ttk.Entry(frame, textvariable=app.var_url, width=55).grid(row=row, column=1, sticky="w")
    app.var_verify_ssl = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Verify SSL certificate", variable=app.var_verify_ssl).grid(row=row, column=2, sticky="w")
    row += 1

    ttk.Label(frame, text="OpenAPI Client ID").grid(row=row, column=0, sticky="w")
    app.var_client_id = tk.StringVar()
    ttk.Entry(frame, textvariable=app.var_client_id, width=55).grid(row=row, column=1, sticky="w")
    row += 1

    ttk.Label(frame, text="OpenAPI Client Secret").grid(row=row, column=0, sticky="w")
    app.var_client_secret = tk.StringVar()
    ttk.Entry(frame, textvariable=app.var_client_secret, width=55, show="*").grid(row=row, column=1, sticky="w")
    row += 1

    ttk.Label(frame, text="(Optional) Omada ID (omadacId) - auto-detected via /api/info").grid(row=row, column=0, sticky="w")
    app.var_omada_id = tk.StringVar()
    ttk.Entry(frame, textvariable=app.var_omada_id, width=55).grid(row=row, column=1, sticky="w")
    row += 1

    ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
    row += 1

    app.btn_connect = ttk.Button(frame, text="Connect", command=app.on_connect)
    app.btn_connect.grid(row=row, column=0, sticky="w")

    app.lbl_conn_state = ttk.Label(frame, text="Not connected")
    app.lbl_conn_state.grid(row=row, column=1, sticky="w")

    app.btn_disconnect = ttk.Button(frame, text="Disconnect", command=app.on_disconnect, state="disabled")
    app.btn_disconnect.grid(row=row, column=2, sticky="w")
    row += 1

    ttk.Label(frame, text="Site").grid(row=row, column=0, sticky="w", pady=(10, 0))
    app.var_site = tk.StringVar()
    app.cmb_sites = ttk.Combobox(frame, textvariable=app.var_site, width=52, state="readonly")
    app.cmb_sites.grid(row=row, column=1, sticky="w", pady=(10, 0))
    app.cmb_sites.bind("<<ComboboxSelected>>", app.on_site_selected)

    app.btn_refresh_sites = ttk.Button(frame, text="Refresh sites", command=app.on_refresh_sites, state="disabled")
    app.btn_refresh_sites.grid(row=row, column=2, sticky="w", pady=(10, 0))

    for col in range(3):
        frame.grid_columnconfigure(col, weight=1 if col == 1 else 0)
