param(
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "resources\artygal.ico")) {
    throw "Missing resources\artygal.ico"
}
if (-not (Test-Path "resources\Drafting_the_Final_Gear.mp3")) {
    throw "Missing resources\Drafting_the_Final_Gear.mp3"
}

python tools\make_icon.py
if (Test-Path "role\raichisoft.mp4") {
    python tools\mp4_to_ansi.py --input "role\raichisoft.mp4" --output "resources\intro" --width 64 --fps 10
}
$IconPath = (Resolve-Path "resources\artygal.ico").Path

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

pyinstaller `
    --onefile `
    --clean `
    --noconfirm `
    --name ArtyGal `
    --icon "$IconPath" `
    --add-data "resources;resources" `
    --collect-submodules rich._unicode_data `
    --optimize 2 `
    --exclude-module PIL `
    --exclude-module numpy `
    --exclude-module pandas `
    --exclude-module matplotlib `
    --exclude-module matplotlib_inline `
    --exclude-module IPython `
    --exclude-module ipywidgets `
    --exclude-module ipykernel `
    --exclude-module jupyter_client `
    --exclude-module notebook `
    --exclude-module comm `
    --exclude-module traitlets `
    --exclude-module pytest `
    --exclude-module tkinter `
    --exclude-module PyQt5 `
    --exclude-module PyQt6 `
    --exclude-module PySide2 `
    --exclude-module PySide6 `
    --exclude-module qtpy `
    --exclude-module zmq `
    --exclude-module cryptography `
    --exclude-module bcrypt `
    --exclude-module nacl `
    --exclude-module psutil `
    --exclude-module scipy `
    --exclude-module setuptools `
    --exclude-module pkg_resources `
    galgame.py

New-Item -ItemType Directory -Force -Path release | Out-Null
Copy-Item -LiteralPath dist\ArtyGal.exe -Destination release\ArtyGal.exe -Force

if (-not $SkipZip) {
    Compress-Archive -Path release\ArtyGal.exe -DestinationPath release\ArtyGal_Windows_x64.zip -Force
}

Get-Item release\ArtyGal.exe | Select-Object FullName, Length
if (-not $SkipZip) {
    Get-Item release\ArtyGal_Windows_x64.zip | Select-Object FullName, Length
}
