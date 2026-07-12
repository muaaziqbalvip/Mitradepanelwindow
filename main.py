"""
main.py — AI Touch Desktop (Windows)
--------------------------------------
Entry point: a beautiful dark-themed settings window (backend URL, Groq
key, PIN, AI instruction) matching the Android app's look. Once the PIN
is verified and settings are saved, launches the floating overlay panel
(see overlay.py).
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

import storage
import backend_client
from overlay import OverlayWindow

# ---- Theme (matches the Android app's palette) ----
BG = "#0B1120"
CARD_BG = "#151F35"
CARD_BG_HOVER = "#1A2740"
ACCENT = "#22C55E"
ACCENT_LIGHT = "#4ADE80"
ACCENT_DARK = "#16A34A"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"
INPUT_BG = "#1E293B"
INPUT_BORDER = "#2D3B52"
INPUT_BORDER_FOCUS = "#22C55E"
WHITE = "#FFFFFF"
FOOTER_BG = "#0A0F1C"
WHATSAPP_GREEN = "#25D366"
WHATSAPP_GREEN_HOVER = "#1FAE55"
SCROLLBAR_BG = "#0F172A"
SCROLLBAR_THUMB = "#2D3B52"

FONT_FAMILY = "Segoe UI"

WINDOW_W = 520
WINDOW_H = 720
MIN_W = 400
MIN_H = 480


def resource_path(rel_path: str) -> str:
    """Resolves a bundled resource path, whether running from source or
    from a PyInstaller-built .exe (which unpacks assets to a temp dir)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


class RoundedCard(tk.Frame):
    """A card-style container with padding, mimicking the Android app's card_bg."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=CARD_BG, highlightbackground="#243247",
                          highlightcolor="#243247", highlightthickness=1, **kwargs)


class ScrollableFrame(tk.Frame):
    """A properly working scrollable container.

    Fixes the previous version's bugs:
      - mousewheel scroll speed/direction now matches Windows (delta units of 120)
      - inner frame width is kept perfectly in sync with the canvas width on resize,
        so content never gets clipped or misaligned
      - scrolling works no matter where the mouse is over the window (bind_all is
        scoped/unbound correctly so it doesn't leak to other Tk windows)
      - a slim, theme-matched scrollbar instead of the default OS-grey one
    """

    def __init__(self, master, bg=BG):
        super().__init__(master, bg=bg)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview,
            bg=SCROLLBAR_BG, troughcolor=SCROLLBAR_BG,
            activebackground=SCROLLBAR_THUMB, bd=0,
            width=10, elementborderwidth=0,
        )
        self.body = tk.Frame(self.canvas, bg=bg)

        self._window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel: only active while the cursor is over this widget tree,
        # so it never fights with other windows (e.g. the overlay panel).
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_body_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._maybe_hide_scrollbar()

    def _on_canvas_configure(self, event):
        # Keep the inner frame exactly as wide as the visible canvas.
        self.canvas.itemconfig(self._window_id, width=event.width)

    def _maybe_hide_scrollbar(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        content_h = bbox[3] - bbox[1]
        visible_h = self.canvas.winfo_height()
        if content_h <= visible_h:
            self.vbar.pack_forget()
        else:
            if not self.vbar.winfo_ismapped():
                self.vbar.pack(side="right", fill="y")

    def _bind_mousewheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux scroll events (harmless on Windows if unused)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        # Windows sends delta in multiples of 120 per notch.
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        step = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(step, "units")


class SettingsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Touch — Desktop")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(MIN_W, MIN_H)
        self.configure(bg=BG)
        self.resizable(True, True)

        try:
            self.iconbitmap(resource_path("assets/icon.ico"))
        except Exception:
            pass

        self.settings = storage.load_settings()
        self.overlay: OverlayWindow | None = None
        self._logo_photo = None  # keep a reference so it isn't garbage-collected

        self._build_ui()

    # ---------------- UI construction ----------------

    def _build_ui(self):
        scroller = ScrollableFrame(self, bg=BG)
        scroller.pack(fill="both", expand=True)
        scroll_body = scroller.body

        self._build_header(scroll_body)
        self._build_backend_card(scroll_body)
        self._build_prompt_card(scroll_body)
        self._build_pin_card(scroll_body)
        self._build_save_button(scroll_body)
        self._build_start_button(scroll_body)
        self._build_status(scroll_body)
        self._build_help_card(scroll_body)
        self._build_footer(scroll_body)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", padx=24, pady=(24, 18))

        try:
            from PIL import Image, ImageTk
            img = Image.open(resource_path("assets/logo.png")).resize((56, 56))
            self._logo_photo = ImageTk.PhotoImage(img)
            tk.Label(header, image=self._logo_photo, bg=BG).pack(side="left", padx=(0, 14))
        except Exception:
            badge = tk.Frame(header, bg=ACCENT, width=56, height=56)
            badge.pack_propagate(False)
            badge.pack(side="left", padx=(0, 14))
            tk.Label(badge, text="✨", font=(FONT_FAMILY, 22), bg=ACCENT, fg=WHITE).pack(
                expand=True)

        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text="AI Touch", font=(FONT_FAMILY, 21, "bold"),
                 bg=BG, fg=WHITE).pack(anchor="w")
        tk.Label(title_box, text="Screen automation, powered by AI",
                 font=(FONT_FAMILY, 9), bg=BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(2, 0))

        divider = tk.Frame(parent, bg="#1E2A42", height=1)
        divider.pack(fill="x", padx=24, pady=(0, 4))

    def _section_title(self, card, emoji, text):
        row = tk.Frame(card, bg=CARD_BG)
        row.pack(fill="x", pady=(0, 14))
        icon_wrap = tk.Frame(row, bg="#1B2E22", width=28, height=28)
        icon_wrap.pack_propagate(False)
        icon_wrap.pack(side="left", padx=(0, 10))
        tk.Label(icon_wrap, text=emoji, font=(FONT_FAMILY, 12), bg="#1B2E22",
                 fg=WHITE).pack(expand=True)
        tk.Label(row, text=text, font=(FONT_FAMILY, 13, "bold"),
                 bg=CARD_BG, fg=ACCENT_LIGHT).pack(side="left")

    def _labeled_entry(self, card, label, initial="", show=None):
        tk.Label(card, text=label, font=(FONT_FAMILY, 8, "bold"),
                 bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 5))

        wrap = tk.Frame(card, bg=INPUT_BORDER)
        wrap.pack(fill="x", pady=(0, 14))

        entry = tk.Entry(wrap, bg=INPUT_BG, fg=WHITE, relief="flat",
                          insertbackground=WHITE, font=(FONT_FAMILY, 10),
                          highlightthickness=0, show=show, bd=0)
        entry.insert(0, initial)
        entry.pack(fill="x", ipady=10, padx=1, pady=1)

        def on_focus_in(_e):
            wrap.configure(bg=INPUT_BORDER_FOCUS)

        def on_focus_out(_e):
            wrap.configure(bg=INPUT_BORDER)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        return entry

    def _build_backend_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=18)
        card.pack(fill="x", padx=24, pady=8)
        self._section_title(card, "🌐", "Backend Connection")
        self.entry_url = self._labeled_entry(
            card, "HF SPACE BACKEND URL",
            self.settings.get("backend_url", storage.DEFAULT_BACKEND_URL),
        )
        self.entry_groq = self._labeled_entry(
            card, "GROQ API KEY", self.settings.get("groq_key", ""), show="•",
        )

    def _build_prompt_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=18)
        card.pack(fill="x", padx=24, pady=8)
        self._section_title(card, "🧠", "AI Instruction")
        tk.Label(card, text="Ek baar likh dein — AI hamesha yaad rakhega",
                 font=(FONT_FAMILY, 8), bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 8))

        text_wrap = tk.Frame(card, bg=INPUT_BORDER)
        text_wrap.pack(fill="x")
        self.text_prompt = tk.Text(text_wrap, height=5, bg=INPUT_BG, fg=WHITE,
                                    relief="flat", insertbackground=WHITE,
                                    font=(FONT_FAMILY, 10), wrap="word",
                                    highlightthickness=0, bd=0, padx=10, pady=8)
        self.text_prompt.insert("1.0", self.settings.get("prompt", ""))
        self.text_prompt.pack(fill="x", padx=1, pady=1)

        def on_focus_in(_e):
            text_wrap.configure(bg=INPUT_BORDER_FOCUS)

        def on_focus_out(_e):
            text_wrap.configure(bg=INPUT_BORDER)

        self.text_prompt.bind("<FocusIn>", on_focus_in)
        self.text_prompt.bind("<FocusOut>", on_focus_out)

    def _build_pin_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=18)
        card.pack(fill="x", padx=24, pady=8)
        self._section_title(card, "🔑", "Access PIN")
        self.entry_pin = self._labeled_entry(
            card, "HF SPACE PAR SET ACCESS_PIN DAALEIN",
            self.settings.get("pin", ""), show="•",
        )

    def _hover_button(self, btn, normal_bg, hover_bg):
        btn.bind("<Enter>", lambda _e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda _e: btn.config(bg=normal_bg))

    def _build_save_button(self, parent):
        btn = tk.Button(
            parent, text="💾  Settings Save Karo", font=(FONT_FAMILY, 11, "bold"),
            bg=INPUT_BG, fg=WHITE, relief="flat", height=2, bd=0,
            activebackground=INPUT_BORDER, activeforeground=WHITE, cursor="hand2",
            command=self._save_settings,
        )
        btn.pack(fill="x", padx=24, pady=(10, 10))
        self._hover_button(btn, INPUT_BG, INPUT_BORDER)

    def _build_start_button(self, parent):
        self.start_btn = tk.Button(
            parent, text="🚀  PANEL START KARO", font=(FONT_FAMILY, 12, "bold"),
            bg=ACCENT, fg=WHITE, relief="flat", height=2, bd=0,
            activebackground=ACCENT_DARK, activeforeground=WHITE, cursor="hand2",
            command=self._start_panel,
        )
        self.start_btn.pack(fill="x", padx=24, pady=(0, 16))
        self._hover_button(self.start_btn, ACCENT, ACCENT_LIGHT)

    def _build_status(self, parent):
        self.status_label = tk.Label(
            parent, text="", font=(FONT_FAMILY, 9), bg=BG, fg=TEXT_SECONDARY,
            justify="left", wraplength=460,
        )
        self.status_label.pack(fill="x", padx=24, pady=(0, 8))

    def _build_help_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=18)
        card.pack(fill="x", padx=24, pady=8)
        self._section_title(card, "💬", "Help & Support")
        tk.Label(card, text="Maloomat ya donation ke liye WhatsApp karein:",
                 font=(FONT_FAMILY, 9), bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 10))
        wa_btn = tk.Button(
            card, text="💬  WhatsApp: 0306-2015326", font=(FONT_FAMILY, 10, "bold"),
            bg=WHATSAPP_GREEN, fg=WHITE, relief="flat", height=2, bd=0,
            activebackground=WHATSAPP_GREEN_HOVER, activeforeground=WHITE,
            cursor="hand2", command=self._open_whatsapp,
        )
        wa_btn.pack(fill="x")
        self._hover_button(wa_btn, WHATSAPP_GREEN, WHATSAPP_GREEN_HOVER)

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=FOOTER_BG)
        footer.pack(fill="x", pady=(20, 0))
        tk.Label(footer, text="Developed by Muaaz Iqbal", font=(FONT_FAMILY, 10, "bold"),
                  bg=FOOTER_BG, fg=ACCENT_LIGHT).pack(pady=(14, 2))
        tk.Label(footer, text="Muslim Islam Organization", font=(FONT_FAMILY, 8),
                  bg=FOOTER_BG, fg=TEXT_SECONDARY).pack(pady=(0, 14))

    # ---------------- Actions ----------------

    def _open_whatsapp(self):
        import webbrowser
        webbrowser.open("https://wa.me/923062015326")

    def _collect_settings(self) -> dict:
        return {
            **self.settings,
            "backend_url": self.entry_url.get().strip(),
            "groq_key": self.entry_groq.get().strip(),
            "prompt": self.text_prompt.get("1.0", "end").strip(),
            "pin": self.entry_pin.get().strip(),
        }

    def _save_settings(self):
        self.settings = self._collect_settings()
        storage.save_settings(self.settings)
        self._set_status("✓ Settings save ho gayin.")

    def _start_panel(self):
        self.settings = self._collect_settings()
        storage.save_settings(self.settings)

        if not self.settings["backend_url"]:
            messagebox.showerror("AI Touch", "Backend URL zaroori hai.")
            return
        if not self.settings["groq_key"]:
            messagebox.showerror("AI Touch", "Groq API Key zaroori hai.")
            return

        self._set_status("PIN verify ho raha hai...")
        self.start_btn.config(state="disabled", text="Checking...")
        self.after(50, self._verify_and_launch)

    def _verify_and_launch(self):
        valid, error = backend_client.verify_pin(
            self.settings["backend_url"], self.settings["pin"]
        )
        self.start_btn.config(state="normal", text="🚀  PANEL START KARO")

        if not valid:
            messagebox.showerror("AI Touch", error or "Galat PIN")
            self._set_status("❌ PIN verify nahi hua.")
            return

        self._set_status("✓ PIN verified. Panel shuru ho raha hai...")

        if self.overlay is None or not self.overlay.winfo_exists():
            self.overlay = OverlayWindow(self, self.settings)
        else:
            self.overlay.deiconify()
            self.overlay.lift()

    def _set_status(self, msg: str):
        self.status_label.config(text=msg)


if __name__ == "__main__":
    app = SettingsApp()
    app.mainloop()
