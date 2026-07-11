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
ACCENT = "#22C55E"
ACCENT_LIGHT = "#4ADE80"
TEXT_SECONDARY = "#94A3B8"
INPUT_BG = "#1E293B"
INPUT_BORDER = "#2D3B52"
WHITE = "#FFFFFF"
FOOTER_BG = "#0A0F1C"
WHATSAPP_GREEN = "#25D366"

FONT_FAMILY = "Segoe UI"


def resource_path(rel_path: str) -> str:
    """Resolves a bundled resource path, whether running from source or
    from a PyInstaller-built .exe (which unpacks assets to a temp dir)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


class RoundedCard(tk.Frame):
    """A card-style container with padding, mimicking the Android app's card_bg."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=CARD_BG, highlightbackground="#1F2937",
                          highlightthickness=1, **kwargs)


class SettingsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Touch — Desktop")
        self.geometry("520x780")
        self.configure(bg=BG)
        self.resizable(False, False)

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
        canvas_frame = tk.Frame(self, bg=BG)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_body = tk.Frame(canvas, bg=BG)

        scroll_body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_body, anchor="nw", width=520)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 60), "units"))

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
        header.pack(fill="x", padx=22, pady=(22, 16))

        try:
            from PIL import Image, ImageTk
            img = Image.open(resource_path("assets/logo.png")).resize((56, 56))
            self._logo_photo = ImageTk.PhotoImage(img)
            tk.Label(header, image=self._logo_photo, bg=BG).pack(side="left", padx=(0, 14))
        except Exception:
            tk.Label(header, text="✨", font=(FONT_FAMILY, 22), bg=ACCENT, fg=WHITE,
                     width=2, height=1).pack(side="left", padx=(0, 14))

        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text="AI Touch", font=(FONT_FAMILY, 20, "bold"),
                 bg=BG, fg=WHITE).pack(anchor="w")
        tk.Label(title_box, text="Screen automation, powered by AI",
                 font=(FONT_FAMILY, 9), bg=BG, fg=TEXT_SECONDARY).pack(anchor="w")

    def _section_title(self, card, emoji, text):
        row = tk.Frame(card, bg=CARD_BG)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(row, text=emoji, font=(FONT_FAMILY, 12), bg="#2022C55E",
                 fg=WHITE, width=2, height=1).pack(side="left", padx=(0, 8))
        tk.Label(row, text=text, font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=ACCENT_LIGHT).pack(side="left")

    def _labeled_entry(self, card, label, initial="", show=None):
        tk.Label(card, text=label, font=(FONT_FAMILY, 8),
                 bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 4))
        entry = tk.Entry(card, bg=INPUT_BG, fg=WHITE, relief="flat",
                          insertbackground=WHITE, font=(FONT_FAMILY, 10),
                          highlightbackground=INPUT_BORDER, highlightthickness=1,
                          show=show)
        entry.insert(0, initial)
        entry.pack(fill="x", ipady=9, pady=(0, 12))
        return entry

    def _build_backend_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=16)
        card.pack(fill="x", padx=22, pady=8)
        self._section_title(card, "🌐", "Backend Connection")
        self.entry_url = self._labeled_entry(
            card, "HF Space Backend URL",
            self.settings.get("backend_url", storage.DEFAULT_BACKEND_URL),
        )
        self.entry_groq = self._labeled_entry(
            card, "Groq API Key", self.settings.get("groq_key", ""), show="•",
        )

    def _build_prompt_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=16)
        card.pack(fill="x", padx=22, pady=8)
        self._section_title(card, "🧠", "AI Instruction")
        tk.Label(card, text="Ek baar likh dein — AI hamesha yaad rakhega",
                 font=(FONT_FAMILY, 8), bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 8))
        self.text_prompt = tk.Text(card, height=5, bg=INPUT_BG, fg=WHITE,
                                    relief="flat", insertbackground=WHITE,
                                    font=(FONT_FAMILY, 10), wrap="word",
                                    highlightbackground=INPUT_BORDER, highlightthickness=1)
        self.text_prompt.insert("1.0", self.settings.get("prompt", ""))
        self.text_prompt.pack(fill="x", ipady=6)

    def _build_pin_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=16)
        card.pack(fill="x", padx=22, pady=8)
        self._section_title(card, "🔑", "Access PIN")
        self.entry_pin = self._labeled_entry(
            card, "HF Space par set ACCESS_PIN daalein",
            self.settings.get("pin", ""), show="•",
        )

    def _build_save_button(self, parent):
        tk.Button(
            parent, text="💾  Settings Save Karo", font=(FONT_FAMILY, 11, "bold"),
            bg=ACCENT, fg=WHITE, relief="flat", height=2, bd=0,
            activebackground=ACCENT_LIGHT, cursor="hand2",
            command=self._save_settings,
        ).pack(fill="x", padx=22, pady=(6, 10))

    def _build_start_button(self, parent):
        self.start_btn = tk.Button(
            parent, text="🚀  PANEL START KARO", font=(FONT_FAMILY, 12, "bold"),
            bg=ACCENT, fg=WHITE, relief="flat", height=2, bd=0,
            activebackground=ACCENT_LIGHT, cursor="hand2",
            command=self._start_panel,
        )
        self.start_btn.pack(fill="x", padx=22, pady=(0, 14))

    def _build_status(self, parent):
        self.status_label = tk.Label(
            parent, text="", font=(FONT_FAMILY, 9), bg=BG, fg=TEXT_SECONDARY,
            justify="left", wraplength=470,
        )
        self.status_label.pack(fill="x", padx=22, pady=(0, 8))

    def _build_help_card(self, parent):
        card = RoundedCard(parent, padx=18, pady=16)
        card.pack(fill="x", padx=22, pady=8)
        self._section_title(card, "💬", "Help & Support")
        tk.Label(card, text="Maloomat ya donation ke liye WhatsApp karein:",
                 font=(FONT_FAMILY, 9), bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 10))
        tk.Button(
            card, text="💬  WhatsApp: 0306-2015326", font=(FONT_FAMILY, 10, "bold"),
            bg=WHATSAPP_GREEN, fg=WHITE, relief="flat", height=2, bd=0,
            cursor="hand2", command=self._open_whatsapp,
        ).pack(fill="x")

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=FOOTER_BG)
        footer.pack(fill="x", pady=(20, 0))
        tk.Label(footer, text="Developed by Muaaz Iqbal", font=(FONT_FAMILY, 10, "bold"),
                  bg=FOOTER_BG, fg=ACCENT_LIGHT, pady=10).pack()
        tk.Label(footer, text="Muslim Islam Organization", font=(FONT_FAMILY, 8),
                  bg=FOOTER_BG, fg=TEXT_SECONDARY, pady=(0, 10)).pack()

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
