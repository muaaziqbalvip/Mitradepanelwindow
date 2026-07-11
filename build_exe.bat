@echo off
REM build_exe.bat — Builds AI Touch Desktop into a single .exe (Windows only)
REM Run this on a Windows machine with Python installed.

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building AITouchDesktop.exe ...
pyinstaller --noconfirm --onefile --windowed ^
    --name "AITouchDesktop" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --hidden-import PIL._tkinter_finder ^
    main.py

echo.
echo Done. Find your exe at: dist\AITouchDesktop.exe
pause
