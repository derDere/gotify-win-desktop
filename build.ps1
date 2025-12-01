# Build script for gotify-win-desktop (Windows)
# - Creates venv if missing
# - Installs deps including PyInstaller
# - Builds single-file, windowed EXE with icon
# - Places artifact under dist/

$ErrorActionPreference = 'Stop'

# Paths
$RepoRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
$VenvPath = Join-Path $RepoRoot '.venv'
$PythonExe = Join-Path $VenvPath 'Scripts/python.exe'
$PipExe = Join-Path $VenvPath 'Scripts/pip.exe'

# Ensure venv
if (!(Test-Path $PythonExe)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Cyan
    python -m venv $VenvPath
}

# Activate venv for this session
& $PythonExe -c "import sys; print('Using Python', sys.version)"

# Install requirements + pyinstaller
Write-Host 'Installing dependencies...' -ForegroundColor Cyan
& $PipExe install --upgrade pip
& $PipExe install -r (Join-Path $RepoRoot 'requirements.txt')
& $PipExe install pyinstaller

# Build exe
Write-Host 'Building EXE with PyInstaller (GotifyClient.exe)...' -ForegroundColor Cyan
$Icon = Join-Path $RepoRoot 'notify_client.ico'
if (!(Test-Path $Icon)) { Write-Host "Warning: Icon file not found: $Icon" -ForegroundColor Yellow }

$PyInstallerArgs = @(
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name=GotifyClient',
    "--icon=$Icon",
    "--add-data=$Icon;.",
    (Join-Path $RepoRoot 'main.py')
)

& $PythonExe -m PyInstaller @PyInstallerArgs

Write-Host 'Build complete. See dist/ for output.' -ForegroundColor Green
