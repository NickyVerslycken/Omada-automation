"""Centralized theme constants and helpers for the modernized UI."""
from __future__ import annotations

from tkinter import ttk

# ── Color palette (inspired by design mockups) ─────────────────────
PRIMARY = "#00408f"
PRIMARY_HOVER = "#003374"
PRIMARY_LIGHT = "#0056bd"
SECONDARY = "#00687a"
SECONDARY_LIGHT = "#6ae1ff"

SURFACE = "#f8f9fb"
SURFACE_ALT = "#f3f4f6"
SURFACE_CARD = "#ffffff"
SURFACE_SIDEBAR = "#1a1a2e"
SURFACE_SIDEBAR_HOVER = "#2a2a42"
SURFACE_SIDEBAR_ACTIVE = "#323250"

TEXT_PRIMARY = "#191c1e"
TEXT_SECONDARY = "#434654"
TEXT_ON_PRIMARY = "#ffffff"
TEXT_SIDEBAR = "#b0b3c0"
TEXT_SIDEBAR_ACTIVE = "#ffffff"
TEXT_MUTED = "#9ca3af"

SUCCESS = "#16a34a"
ERROR = "#ba1a1a"
WARNING = "#d97706"
INFO = "#0284c7"

BORDER_LIGHT = "#e5e7eb"

# ── Fonts ──────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_HEADING_LG = (FONT_FAMILY, 20, "bold")
FONT_HEADING_SM = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 11)
FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
FONT_LABEL = (FONT_FAMILY, 10)
FONT_LABEL_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = ("Consolas", 10)

# ── Sidebar ────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 220
SIDEBAR_ICON_SIZE = 18
SIDEBAR_ITEM_PAD_Y = 4
SIDEBAR_ACCENT_WIDTH = 4

# ── Cards ──────────────────────────────────────────────────────────
CARD_CORNER_RADIUS = 10
CARD_PADDING = 16
CARD_BORDER_WIDTH = 0

# ── Buttons ────────────────────────────────────────────────────────
BTN_CORNER_RADIUS = 6
BTN_HEIGHT = 32
BTN_PADDING = (16, 8)

# ── Status bar ─────────────────────────────────────────────────────
STATUSBAR_HEIGHT = 32
STATUS_DOT_CONNECTED = SUCCESS
STATUS_DOT_DISCONNECTED = "#9ca3af"


def configure_treeview_style() -> None:
    """Apply modern styling to ttk.Treeview widgets."""
    style = ttk.Style()

    style.configure(
        "Modern.Treeview",
        background=SURFACE_CARD,
        fieldbackground=SURFACE_CARD,
        foreground=TEXT_PRIMARY,
        rowheight=30,
        borderwidth=0,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Modern.Treeview.Heading",
        background=SURFACE_ALT,
        foreground=TEXT_SECONDARY,
        relief="flat",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(8, 6),
    )
    style.map(
        "Modern.Treeview.Heading",
        background=[("active", SURFACE_ALT)],
        relief=[("active", "flat")],
    )
    style.map(
        "Modern.Treeview",
        background=[("selected", "#dbeafe")],
        foreground=[("selected", PRIMARY)],
    )

    # Modern scrollbar
    style.configure(
        "Modern.Vertical.TScrollbar",
        troughcolor=SURFACE,
        background=BORDER_LIGHT,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Modern.Horizontal.TScrollbar",
        troughcolor=SURFACE,
        background=BORDER_LIGHT,
        borderwidth=0,
        relief="flat",
    )

    # Style comboboxes to blend with the modern look
    style.configure(
        "Modern.TCombobox",
        fieldbackground=SURFACE_CARD,
        background=SURFACE_CARD,
        foreground=TEXT_PRIMARY,
        padding=(8, 4),
    )
    style.map(
        "Modern.TCombobox",
        fieldbackground=[("readonly", SURFACE_CARD)],
        selectbackground=[("readonly", SURFACE_CARD)],
        selectforeground=[("readonly", TEXT_PRIMARY)],
    )

    # Style spinboxes
    style.configure(
        "Modern.TSpinbox",
        fieldbackground=SURFACE_CARD,
        background=SURFACE_CARD,
        foreground=TEXT_PRIMARY,
        padding=(8, 4),
    )
