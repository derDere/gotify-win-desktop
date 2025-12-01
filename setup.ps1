# Setup script for Gotify Windows Tray Client
# Usage: Run from dist folder or repo root copy.
# If already installed under %LOCALAPPDATA%\Programs\GotifyWinClient, prompts to uninstall.
# Otherwise installs.

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$DistExe = Join-Path $ScriptDir 'GotifyClient.exe'
$InstalledExe = Join-Path $Env:LOCALAPPDATA 'Programs/GotifyWinClient/GotifyClient.exe'

if (!(Test-Path $DistExe)) {
    Write-Host "GotifyClient.exe not found next to setup.ps1: $DistExe" -ForegroundColor Red
    exit 1
}

if (Test-Path $InstalledExe) {
    Write-Host "GotifyClient is already installed at: $InstalledExe" -ForegroundColor Yellow
    $ans = Read-Host "Do you want to uninstall it? (y/N)"
    if ($ans -match '^[Yy]$') {
        Write-Host "Uninstalling using dist executable..." -ForegroundColor Cyan
        # Recommend closing running instance first
        Write-Host "If the tray app is running, please exit it now." -ForegroundColor DarkYellow
        & $DistExe --uninstall
        Write-Host "Uninstall attempt finished. If files remain, close the running app and retry." -ForegroundColor Green
    } else {
        Write-Host "Keeping existing installation." -ForegroundColor Green
    }
} else {
    Write-Host "GotifyClient not installed. Installing..." -ForegroundColor Cyan
    & $DistExe --install
    Write-Host "Install complete." -ForegroundColor Green
}
