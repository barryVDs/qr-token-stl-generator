@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo  ============================================
echo   QR Token STL Generator
echo  ============================================
echo.
echo  HOE WERKT HET:
echo.
echo   1. Zet je JSON-exportbestand in de map "input\"
echo      (wordt automatisch aangemaakt als die niet bestaat)
echo.
echo   2. Kies een preset (token-instellingen)
echo.
echo   3. De STL-bestanden komen in de map "output\[naam]\"
echo.
echo  ============================================
echo.

:: Check venv
if not exist "venv\Scripts\activate.bat" (
    echo  [!] Virtuele omgeving niet gevonden.
    echo      Voer eerst uit:
    echo        python -m venv venv
    echo        venv\Scripts\activate
    echo        pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Maak input map aan als die niet bestaat
if not exist "input\" mkdir input

:: Toon beschikbare presets
echo  Beschikbare presets:
echo  --------------------
set preset_count=0
for %%f in (presets\*.json) do (
    set /a preset_count+=1
    echo   !preset_count!. %%~nf
    set "preset_!preset_count!=%%~nf"
)
echo.

if %preset_count%==0 (
    echo  [!] Geen presets gevonden in presets\ map.
    pause
    exit /b 1
)

:: Kies preset
set /p preset_choice="  Kies preset (nummer): "

set "chosen_preset=!preset_%preset_choice%!"
if "!chosen_preset!"=="" (
    echo  [!] Ongeldige keuze.
    pause
    exit /b 1
)
echo.
echo  Gekozen preset: !chosen_preset!
echo.

:: Toon beschikbare JSON bestanden
echo  Beschikbare JSON bestanden:
echo  ---------------------------
set json_count=0
for %%f in (input\*.json) do (
    set /a json_count+=1
    echo   !json_count!. %%~nxf
    set "json_!json_count!=%%f"
)
echo.

if %json_count%==0 (
    echo  [!] Geen JSON bestanden gevonden in input\ map.
    echo      Zet je JSON-exportbestand in de map "input\" en probeer opnieuw.
    echo.
    pause
    exit /b 1
)

:: Kies JSON
set /p json_choice="  Kies JSON bestand (nummer): "

set "chosen_json=!json_%json_choice%!"
if "!chosen_json!"=="" (
    echo  [!] Ongeldige keuze.
    pause
    exit /b 1
)
echo.

:: Bepaal output mapnaam
for %%f in ("!chosen_json!") do set "json_name=%%~nf"
set "output_dir=output\!json_name!_!chosen_preset!"

echo  ============================================
echo   Samenvatting:
echo  ============================================
echo   Preset:  !chosen_preset!
echo   Input:   !chosen_json!
echo   Output:  !output_dir!\
echo  ============================================
echo.
set /p confirm="  Doorgaan? (j/n): "
if /i not "!confirm!"=="j" (
    echo  Geannuleerd.
    pause
    exit /b 0
)

echo.
echo  Genereren...
echo.

call venv\Scripts\activate.bat

python -m app generate --input "!chosen_json!" --output "!output_dir!" --preset "!chosen_preset!" --zip --verbose

echo.
echo  ============================================
echo   Klaar!
echo   STL bestanden staan in: !output_dir!\
echo   ZIP bestand: !output_dir!\tokens.zip
echo  ============================================
echo.
pause
