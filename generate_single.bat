@echo off
echo === QR Token STL Generator ===
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo Venv niet gevonden. Eerst installeren:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python -m app generate --input examples\single_token.json --output out_single --verbose

echo.
echo === Klaar! STL staat in out_single\ ===
pause
