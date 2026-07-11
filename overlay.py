"""
overlay.py — Floating, always-on-top panel with a logo toggle bubble and
draggable/resizable dots. Matches the Android app's design: tap the bubble
to show/hide the panel + dots; the bubble itself never disappears.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

import storage
import backend_client
import screen_capture
import click_executor

PANEL_BG = "#141E30"
ACCENT = "#22C55E"
ACCENT_LIGHT = "#4ADE80"
LOCKED_COLOR = "#F59E0B"
WHITE = "#FFFFFF"
DANGER = "#F87171"

MIN_DOT_SIZE = 28
MAX_DOT_SIZE = 90


def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


class DotWidget:
    """A single draggable/resizable circular dot rendered as a tiny borderless window."""

    def __init__(self, overlay: "OverlayWindow", dot: dict):
        self.overlay = overlay
        self.dot = dot

        self.win = tk.Toplevel(overlay)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#FF00FF")
        self.win.attributes("-transparentcolor", "#FF00FF")

        self.canvas = tk.Canvas(self.win, bg="#FF00FF", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._redraw()
        self._place()

        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_scroll)

        self._drag_start = None
        self._moved = False

    def _place(self):
        size = self.dot["size"]
        self.win.geometry(f"{size}x{size}+{self.dot['x']}+{self.dot['y']}")

    def _redraw(self):
        size = self.dot["size"]
        self.canvas.config(width=size, height=size)
        self.canvas.delete("all")
        color = LOCKED_COLOR if self.dot.get("locked") else ACCENT
        pad = 2
        # subtle glow ring
        self.canvas.create_oval(0, 0, size, size, fill="", outline=color, width=1)
        self.canvas.create_oval(pad, pad, size - pad, size - pad,
                                 fill=color, outline=WHITE, width=2)
        font_size = max(8, int(size * 0.32))
        self.canvas.create_text(size / 2, size / 2, text=self.dot["name"],
                                 fill=WHITE, font=("Segoe UI", font_size, "bold"))

    def _on_press(self, event):
        self._drag_start = (event.x_root, event.y_root, self.dot["x"], self.dot["y"])
        self._moved = False

    def _on_drag(self, event):
        if self.dot.get("locked") or self._drag_start is None:
            return
        sx, sy, ox, oy = self._drag_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        if abs(dx) > 4 or abs(dy) > 4:
            self._moved = True
        self.dot["x"] = ox + dx
        self.dot["y"] = oy + dy
        self._place()

    def _on_release(self, event):
        if self._moved:
            self.overlay.persist_dots()
        else:
            self.overlay.show_dot_menu(self)
        self._drag_start = None

    def _on_scroll(self, event):
        if self.dot.get("locked"):
            return
        delta = 4 if event.delta > 0 else -4
        new_size = max(MIN_DOT_SIZE, min(MAX_DOT_SIZE, self.dot["size"] + delta))
        self.dot["size"] = new_size
        self._redraw()
        self._place()
        self.overlay.persist_dots()

    def set_visible(self, visible: bool):
        if visible:
            self.win.deiconify()
        else:
            self.win.withdraw()

    def destroy(self):
        self.win.destroy()


class ToggleBubble(tk.Toplevel):
    """Small always-visible floating bubble with the app logo. Tap to
    show/hide the control panel + dots. Never disappears itself, so the
    user always has a way to bring the panel back."""

    def __init__(self, overlay: "OverlayWindow"):
        super().__init__(overlay)
        self.overlay = overlay
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#FF00FF")
        self.attributes("-transparentcolor", "#FF00FF")
        self.geometry("+40+120")

        size = 52
        canvas = tk.Canvas(self, width=size, height=size, bg="#FF00FF", highlightthickness=0)
        canvas.pack()

        canvas.create_oval(2, 2, size - 2, size - 2, fill="#1A2744", outline="#5522C55E", width=2)

        try:
            from PIL import Image, ImageTk
            img = Image.open(resource_path("assets/logo.png")).resize((32, 32))
            self._logo_img = ImageTk.PhotoImage(img)
            canvas.create_image(size / 2, size / 2, image=self._logo_img)
        except Exception:
            canvas.create_text(size / 2, size / 2, text="AI", fill=ACCENT_LIGHT,
                                font=("Segoe UI", 14, "bold"))

        canvas.bind("<Button-1>", self._on_press)
        canvas.bind("<B1-Motion>", self._on_drag)
        canvas.bind("<ButtonRelease-1>", self._on_release)

        self._drag_start = None
        self._moved = False

    def _on_press(self, event):
        self._drag_start = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())
        self._moved = False

    def _on_drag(self, event):
        sx, sy, ox, oy = self._drag_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        if abs(dx) > 4 or abs(dy) > 4:
            self._moved = True
        self.geometry(f"+{ox + dx}+{oy + dy}")

    def _on_release(self, event):
        if not self._moved:
            self.overlay.toggle_panel()
        self._drag_start = None


class OverlayWindow(tk.Toplevel):
    def __init__(self, master, settings: dict):
        super().__init__(master)
        self.settings = settings
        self.dots: list[dict] = list(settings.get("dots", []))
        self.dot_widgets: dict[str, DotWidget] = {}
        self.panel_visible = False
        self.last_description: str | None = None
        self.last_dot_chosen: str | None = None

        self.withdraw()  # this root Toplevel itself stays invisible; it just hosts children

        self.bubble = ToggleBubble(self)
        self.panel_win: tk.Toplevel | None = None

        for d in self.dots:
            self._add_dot_widget(d)
            self.dot_widgets[d["id"]].set_visible(False)

    # ---------------- Panel show/hide ----------------

    def toggle_panel(self):
        if self.panel_visible:
            self._hide_panel()
        else:
            self._show_panel()

    def _show_panel(self):
        if self.panel_win is None or not self.panel_win.winfo_exists():
            self._build_panel()
        self.panel_win.deiconify()
        for w in self.dot_widgets.values():
            w.set_visible(True)
        self.panel_visible = True

    def _hide_panel(self):
        if self.panel_win is not None:
            self.panel_win.withdraw()
        for w in self.dot_widgets.values():
            w.set_visible(False)
        self.panel_visible = False

    def _build_panel(self):
        bx, by = self.bubble.winfo_x(), self.bubble.winfo_y()

        self.panel_win = tk.Toplevel(self)
        self.panel_win.overrideredirect(True)
        self.panel_win.attributes("-topmost", True)
        self.panel_win.configure(bg=PANEL_BG)
        self.panel_win.geometry(f"+{bx}+{by + 62}")

        bar = tk.Frame(self.panel_win, bg=PANEL_BG, padx=8, pady=6,
                        highlightbackground="#3322C55E", highlightthickness=1)
        bar.pack()

        drag_handle = tk.Label(bar, text="⠿", bg=PANEL_BG, fg=ACCENT_LIGHT,
                                font=("Segoe UI", 12), cursor="fleur")
        drag_handle.pack(side="left", padx=(0, 8))
        drag_handle.bind("<Button-1>", self._on_panel_press)
        drag_handle.bind("<B1-Motion>", self._on_panel_drag)

        def icon_btn(text, color, cmd):
            b = tk.Button(bar, text=text, command=cmd, bg=PANEL_BG, fg=color,
                           relief="flat", bd=0, font=("Segoe UI", 12),
                           activebackground="#22314F", cursor="hand2", width=3)
            b.pack(side="left", padx=2)
            return b

        icon_btn("➕", WHITE, self.prompt_new_dot)
        icon_btn("✨", ACCENT_LIGHT, self.run_ai_analysis)
        icon_btn("📊", "#60A5FA", self.show_feedback_dialog)
        icon_btn("✕", DANGER, self.close_overlay)

    def _on_panel_press(self, event):
        self._panel_drag_start = (event.x_root, event.y_root,
                                   self.panel_win.winfo_x(), self.panel_win.winfo_y())

    def _on_panel_drag(self, event):
        sx, sy, ox, oy = self._panel_drag_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        self.panel_win.geometry(f"+{ox + dx}+{oy + dy}")

    def close_overlay(self):
        for w in self.dot_widgets.values():
            w.destroy()
        if self.panel_win:
            self.panel_win.destroy()
        self.bubble.destroy()
        self.destroy()

    # ---------------- Dots ----------------

    def prompt_new_dot(self):
        name = simpledialog.askstring("Naya Dot", "Dot ka naam (max 2 letters):", parent=self.panel_win)
        if name is None:
            return
        name = name.strip()[:2] or "?"
        bx, by = self.bubble.winfo_x(), self.bubble.winfo_y()
        dot = storage.new_dot(name, bx + 30, by + 140)
        self.dots.append(dot)
        self._add_dot_widget(dot)
        self.persist_dots()
        messagebox.showinfo("AI Touch", f"✓ Dot add ho gaya: {name}", parent=self.panel_win)

    def _add_dot_widget(self, dot: dict):
        widget = DotWidget(self, dot)
        widget.set_visible(self.panel_visible)
        self.dot_widgets[dot["id"]] = widget

    def show_dot_menu(self, widget: "DotWidget"):
        dot = widget.dot
        menu = tk.Menu(self, tearoff=0)
        lock_label = "Unlock" if dot.get("locked") else "Lock"
        menu.add_command(label=lock_label, command=lambda: self._toggle_lock(widget))
        menu.add_command(label="Rename", command=lambda: self._rename_dot(widget))
        menu.add_command(label="Delete", command=lambda: self._delete_dot(widget))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _toggle_lock(self, widget: "DotWidget"):
        widget.dot["locked"] = not widget.dot.get("locked", False)
        widget._redraw()
        self.persist_dots()

    def _rename_dot(self, widget: "DotWidget"):
        name = simpledialog.askstring("Naam Badlo", "Naya naam (max 2 letters):",
                                       initialvalue=widget.dot["name"], parent=self.panel_win)
        if name:
            widget.dot["name"] = name.strip()[:2]
            widget._redraw()
            self.persist_dots()

    def _delete_dot(self, widget: "DotWidget"):
        self.dots.remove(widget.dot)
        del self.dot_widgets[widget.dot["id"]]
        widget.destroy()
        self.persist_dots()

    def persist_dots(self):
        self.settings["dots"] = self.dots
        storage.save_settings(self.settings)

    # ---------------- AI Run ----------------

    def run_ai_analysis(self):
        if not self.dots:
            messagebox.showwarning("AI Touch", "Pehle kam az kam ek dot add karein.", parent=self.panel_win)
            return

        was_visible = self.panel_visible
        if self.panel_win:
            self.panel_win.withdraw()
        for w in self.dot_widgets.values():
            w.win.withdraw()

        self.after(150, lambda: self._capture_and_analyze(was_visible))

    def _capture_and_analyze(self, was_visible: bool):
        try:
            img = screen_capture.capture_primary_monitor()
        finally:
            if was_visible and self.panel_win:
                self.panel_win.deiconify()
            for w in self.dot_widgets.values():
                if was_visible:
                    w.win.deiconify()

        threading.Thread(target=self._analyze_worker, args=(img,), daemon=True).start()

    def _analyze_worker(self, img):
        try:
            result = backend_client.analyze(
                backend_url=self.settings["backend_url"],
                groq_key=self.settings["groq_key"],
                pin=self.settings.get("pin", ""),
                dots=self.dots,
                prompt=self.settings.get("prompt", ""),
                screenshot=img,
            )
        except backend_client.BackendError as e:
            self.after(0, lambda: messagebox.showerror("AI Touch", str(e)))
            return

        dot_name = result.get("dot", "")
        debug_raw = result.get("_debug_raw", "")
        self.last_description = result.get("description", "")
        self.last_dot_chosen = dot_name

        def on_main_thread():
            if debug_raw:
                print(f"[AI Touch] AI raw response: {debug_raw}")
            if not dot_name:
                messagebox.showinfo("AI Touch", "ℹ️ AI: koi action nahi")
                return
            target = next((d for d in self.dots if d["name"].lower() == dot_name.lower()), None)
            if target is None:
                messagebox.showwarning("AI Touch", f"❌ Dot '{dot_name}' nahi mila")
                return
            click_executor.click_dot(target)
            print(f"[AI Touch] ✓ Clicked: {dot_name}")

        self.after(0, on_main_thread)

    # ---------------- Feedback ----------------

    def show_feedback_dialog(self):
        if not getattr(self, "last_description", None):
            messagebox.showwarning("AI Touch", "Pehle 'AI Run' se ek analysis karein.")
            return

        win = tk.Toplevel(self.panel_win if self.panel_win else self)
        win.title("Trade Result")
        win.configure(bg=PANEL_BG)
        win.attributes("-topmost", True)
        win.geometry("260x180")

        tk.Label(win, text="Pichle trade ka result:", bg=PANEL_BG, fg=WHITE,
                 font=("Segoe UI", 10, "bold")).pack(pady=(16, 10))

        tk.Button(win, text="✅ Win (profit hua)", bg="#16A34A", fg=WHITE, relief="flat",
                  command=lambda: self._report_result("win", win)).pack(fill="x", padx=20, pady=4)
        tk.Button(win, text="❌ Loss (loss hua)", bg="#DC2626", fg=WHITE, relief="flat",
                  command=lambda: self._report_result("loss", win)).pack(fill="x", padx=20, pady=4)
        tk.Button(win, text="📊 Stats dekhein", bg="#2563EB", fg=WHITE, relief="flat",
                  command=lambda: self._show_stats(win)).pack(fill="x", padx=20, pady=4)

    def _report_result(self, result: str, dialog_win: tk.Toplevel):
        dialog_win.destroy()

        def worker():
            success, error = backend_client.send_feedback(
                backend_url=self.settings["backend_url"],
                pin=self.settings.get("pin", ""),
                description=self.last_description,
                result=result,
                dot=self.last_dot_chosen or "",
            )

            def done():
                if success:
                    label = "✅ Win" if result == "win" else "❌ Loss"
                    messagebox.showinfo("AI Touch", f"{label} save ho gaya — agli baar AI is se seekhega")
                else:
                    messagebox.showerror("AI Touch", error or "Feedback save nahi hua")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _show_stats(self, dialog_win: tk.Toplevel):
        dialog_win.destroy()

        def worker():
            stats = backend_client.fetch_stats(self.settings["backend_url"])

            def done():
                total = stats.get("total", 0)
                if total == 0:
                    msg = "Abhi tak koi feedback record nahi hai."
                else:
                    msg = (f"Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}\n"
                           f"Win Rate: {stats.get('win_rate_percent', 0)}%")
                messagebox.showinfo("Trading Stats", msg)

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
