"""Application styling.

The 2022 GUI carried roughly 500 lines of inline ``setStyleSheet`` calls, one
per widget, with gradient strings copy-pasted between screens. Everything
lives in one stylesheet here, so a colour change is a single edit. The blue
and green gradients from the original are preserved deliberately - they were
the project's visual identity.
"""

from __future__ import annotations

# Gradients carried over from the 2022 build.
GRADIENT_BLUE = (
    "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
    "stop:0 rgba(10, 112, 164, 255), stop:0.31 rgba(10, 112, 164, 255), "
    "stop:0.79 rgba(33, 43, 255, 255), stop:1 rgba(33, 43, 255, 255))"
)
GRADIENT_GREEN = (
    "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
    "stop:0 rgba(114, 171, 68, 255), stop:0.31 rgba(114, 171, 68, 255), "
    "stop:0.79 rgba(3, 97, 73, 255), stop:1 rgba(3, 97, 73, 255))"
)
GRADIENT_RED = (
    "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
    "stop:0.29 rgba(170, 0, 0, 255), stop:1 rgba(255, 0, 0, 255))"
)

INK = "#f2f4f8"
MUTED = "#9aa4b2"
SURFACE = "#1b2130"
SURFACE_RAISED = "#232b3c"
BACKDROP = "#121722"
SUCCESS = "#4ade80"
DANGER = "#f87171"
WARNING = "#fbbf24"

STYLESHEET = f"""
QWidget {{
    background-color: {BACKDROP};
    color: {INK};
    font-family: "Segoe UI", "Gadugi", "Inter", sans-serif;
    font-size: 14px;
}}

#Card {{
    background-color: {SURFACE};
    border: 1px solid #2b3446;
    border-radius: 16px;
}}

QLabel#Title {{
    font-size: 30px;
    font-weight: 700;
    color: {INK};
}}

QLabel#Subtitle {{
    font-size: 15px;
    color: {MUTED};
}}

QLabel#FieldLabel {{
    font-size: 13px;
    font-weight: 600;
    color: {MUTED};
}}

QLabel#Success {{ color: {SUCCESS}; font-weight: 600; }}
QLabel#Danger  {{ color: {DANGER};  font-weight: 600; }}
QLabel#Warning {{ color: {WARNING}; font-weight: 600; }}

QLineEdit {{
    background-color: {SURFACE_RAISED};
    border: 1px solid #333d52;
    border-radius: 10px;
    padding: 11px 14px;
    selection-background-color: #2563eb;
}}
QLineEdit:focus {{ border: 1px solid #3b82f6; }}
QLineEdit:disabled {{ color: {MUTED}; }}

QPushButton {{
    background-color: {SURFACE_RAISED};
    border: 1px solid #39445c;
    border-radius: 10px;
    padding: 11px 20px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #2b3446; }}
QPushButton:pressed {{ background-color: #171d29; }}
QPushButton:disabled {{ color: #5b6478; border-color: #2a3245; }}

QPushButton#Primary {{
    background: {GRADIENT_BLUE};
    border: none;
    color: white;
}}
QPushButton#Primary:disabled {{ background: #2a3245; color: #6b7488; }}

QPushButton#Confirm {{
    background: {GRADIENT_GREEN};
    border: none;
    color: white;
}}
QPushButton#Confirm:disabled {{ background: #2a3245; color: #6b7488; }}

QPushButton#Destructive {{
    background: {GRADIENT_RED};
    border: none;
    color: white;
}}

QPushButton#Link {{
    background: transparent;
    border: none;
    color: #7dd3fc;
    text-decoration: underline;
    padding: 4px;
}}

QPushButton#Ghost {{
    background: transparent;
    border: 1px solid #39445c;
}}

QProgressBar {{
    background-color: {SURFACE_RAISED};
    border: none;
    border-radius: 5px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{ border-radius: 5px; background-color: {SUCCESS}; }}

QProgressBar#Weak::chunk   {{ background-color: {DANGER};  }}
QProgressBar#Fair::chunk   {{ background-color: {WARNING}; }}
QProgressBar#Strong::chunk {{ background-color: {SUCCESS}; }}

#CameraFrame {{
    background-color: #0b0f18;
    border: 2px solid #2b3446;
    border-radius: 14px;
}}

QCheckBox {{ color: {MUTED}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border-radius: 5px;
    border: 1px solid #39445c;
    background-color: {SURFACE_RAISED};
}}
QCheckBox::indicator:checked {{ background-color: #3b82f6; border-color: #3b82f6; }}

QToolTip {{
    background-color: {SURFACE_RAISED};
    color: {INK};
    border: 1px solid #39445c;
    padding: 6px;
}}
"""
