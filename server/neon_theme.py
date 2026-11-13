"""SatLink Neon theme for the Tkinter windows (agent + relay server).

Call apply_neon(root) after building the UI: it walks every widget and maps the
old colors to the neon palette, and adds hover glow to buttons.
"""

BG = "#05060f"
SURFACE = "#0e1022"
SURFACE_2 = "#161933"
CYAN = "#00f0ff"
MAGENTA = "#ff2bd6"
PURPLE = "#8a5cff"
GREEN = "#39ff88"
RED = "#ff3b6b"
AMBER = "#ffc400"
TEXT = "#e6f1ff"
MUTED = "#8aa0c8"
LABEL = "#b18cff"

_BG_MAP = {
    "#07111f": BG, "#0b1220": BG,
    "#0d1b2f": SURFACE,
}
_FG_MAP = {
    "#4aa3ff": CYAN, "#66d9ff": CYAN,
    "#5ff59a": GREEN,
    "#8ebeff": LABEL,
    "#c7d7ec": MUTED, "#b9c7d8": MUTED,
    "#e6f3ff": TEXT, "#ffffff": TEXT, "white": TEXT,
    "#ffcc66": AMBER,
}
# old button background -> (bg, fg, hover)
_BUTTON_MAP = {
    "#1f6feb": (CYAN, BG, "#7ff8ff"),
    "#164b83": (SURFACE_2, CYAN, "#232850"),
    "#14345a": (SURFACE_2, CYAN, "#232850"),
    "#17263d": (SURFACE_2, CYAN, "#232850"),
    "#6f42c1": (PURPLE, "#ffffff", "#a988ff"),
    "#238636": (GREEN, BG, "#8cffbc"),
    "#145a3a": (GREEN, BG, "#8cffbc"),
    "#792e2e": (RED, "#ffffff", "#ff7096"),
    "#b1442f": (RED, "#ffffff", "#ff7096"),
    "#5a1414": (RED, "#ffffff", "#ff7096"),
    "#5a2b14": (MAGENTA, "#ffffff", "#ff6be3"),
}


def button_colors(old_bg):
    return _BUTTON_MAP.get(str(old_bg).lower(), (SURFACE_2, CYAN, "#232850"))


def style_button(btn, old_bg=None):
    """Applies neon colors to a tk.Button (old_bg = the button's original color)."""
    try:
        bg, fg, hover = button_colors(old_bg or btn.cget("bg"))
        btn.configure(bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                      relief="flat", bd=0, cursor="hand2", highlightthickness=0)
        btn._neon_bg = bg
        btn._neon_hover = hover
        if not getattr(btn, "_neon_bound", False):
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=getattr(b, "_neon_hover", b.cget("bg"))))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=getattr(b, "_neon_bg", b.cget("bg"))))
            btn._neon_bound = True
    except Exception:
        pass


def apply_neon(widget):
    try:
        cls = widget.winfo_class()
    except Exception:
        return
    try:
        if cls == "Button":
            style_button(widget)
        else:
            opts = widget.keys()
            if "bg" in opts:
                bg = str(widget.cget("bg")).lower()
                if bg in _BG_MAP:
                    widget.configure(bg=_BG_MAP[bg])
            if "fg" in opts:
                fg = str(widget.cget("fg")).lower()
                if fg in _FG_MAP:
                    widget.configure(fg=_FG_MAP[fg])
            if "highlightbackground" in opts and int(str(widget.cget("highlightthickness")) or 0) > 0:
                widget.configure(highlightbackground=CYAN, highlightcolor=MAGENTA)
            if cls == "Text":
                widget.configure(bg=BG, fg=MUTED, insertbackground=CYAN)
            if cls in ("Tk", "Toplevel"):
                widget.configure(bg=BG)
    except Exception:
        pass
    for child in widget.winfo_children():
        apply_neon(child)


def neon_line(parent, x, y, width):
    """A thin cyan->magenta glow line (two placed frames)."""
    import tkinter as tk
    half = width // 2
    tk.Frame(parent, bg=CYAN, height=2).place(x=x, y=y, width=half, height=2)
    tk.Frame(parent, bg=MAGENTA, height=2).place(x=x + half, y=y, width=width - half, height=2)
