from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from omada_batch.ui.theme import (
    BORDER_LIGHT,
    BTN_CORNER_RADIUS,
    BTN_HEIGHT,
    FONT_LABEL,
    FONT_MONO,
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


def build_logs_tab(app: "App") -> None:
    frame = ctk.CTkFrame(app.tab_logs, fg_color=SURFACE, corner_radius=0)
    frame.pack(fill="both", expand=True, padx=24, pady=16)

    top = ctk.CTkFrame(frame, fg_color="transparent")
    top.pack(fill="x", pady=(0, 8))

    ctk.CTkButton(
        top, text="Clear Log", command=app.on_clear_log,
        fg_color="transparent", hover_color=SURFACE_ALT,
        text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_LIGHT,
        corner_radius=BTN_CORNER_RADIUS, height=BTN_HEIGHT, font=FONT_LABEL,
    ).pack(side="left")

    log_card = ctk.CTkFrame(
        frame, fg_color=SURFACE_CARD, corner_radius=10,
        border_width=1, border_color=BORDER_LIGHT,
    )
    log_card.pack(fill="both", expand=True)

    app.txt_logs = ctk.CTkTextbox(
        log_card, font=FONT_MONO, fg_color=SURFACE_CARD,
        text_color=TEXT_PRIMARY, corner_radius=0,
        wrap="none",
    )
    app.txt_logs.pack(fill="both", expand=True, padx=4, pady=4)

    app._log("Ready.")
