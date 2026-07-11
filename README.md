# AI Touch — Desktop (Windows)

Windows version of AI Touch, same dark theme, logo, and layout as the
Android app. Uses the **same HF Space backend** — screenshot in, AI picks
a dot, real mouse click happens.

## Get the .exe automatically (no setup needed)

This repo has a GitHub Actions workflow that builds `AITouchDesktop.exe`
automatically on every push:

1. Push this repo to GitHub.
2. Go to the **Actions** tab → the workflow runs automatically (or click
   "Run workflow" to trigger it manually).
3. Once it finishes (~2-3 min), open the run → under **Artifacts**,
   download `AITouchDesktop-Windows-EXE`.
4. Extract the zip → you get `AITouchDesktop.exe`. Double-click to run —
   no installation, no Python needed on the target PC.

If you push to `main`/`master`, it also auto-creates a GitHub Release with
the .exe attached, so you always have a permanent download link.

## Run from source (for development/testing)

Requires Python 3.10+ on Windows.

```
pip install -r requirements.txt
python main.py
```

## Build the .exe yourself locally

Double-click `build_exe.bat` on a Windows machine, or run:

```
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "AITouchDesktop" --icon "assets/icon.ico" --add-data "assets;assets" --hidden-import PIL._tkinter_finder main.py
```

Output: `dist\AITouchDesktop.exe`

## How to use

1. Launch the app — a beautiful settings window opens (same look as the
   Android app: logo header, cards, gradient buttons, footer credits).
2. Enter your HF Space Backend URL (pre-filled with the default one),
   Groq API Key, AI Instruction, and Access PIN (must match the HF
   Space's `ACCESS_PIN` secret).
3. Click **Settings Save Karo**, then **PANEL START KARO**.
4. A small floating logo bubble appears on screen — tap it to show/hide
   the control panel and dots. The bubble itself never disappears, so you
   always have a way to bring the panel back.
5. Panel buttons:
   - **➕** — add a new dot (2-letter name)
   - **✨** — run AI analysis (captures screen, sends to backend, clicks
     whichever dot the AI picks)
   - **✕** — close everything
6. Drag dots to position them over real buttons on screen. Scroll the
   mouse wheel over a dot to resize it. Click a dot (without dragging) to
   open its menu: Lock / Rename / Delete.

## Notes

- Only the primary monitor is captured for analysis.
- Settings and dots are saved to `%USERPROFILE%\.ai_touch_desktop\settings.json`.
- Reuses the exact same backend contract as the Android app, so backend
  fixes (accuracy, model changes, etc.) apply to both apps automatically.

## Credits

Developed by Muaaz Iqbal — Muslim Islam Organization
WhatsApp: 0306-2015326
