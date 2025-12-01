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
$Sound = Join-Path $RepoRoot 'sound_file.mp3'
if (!(Test-Path $Icon)) { Write-Host "Warning: Icon file not found: $Icon" -ForegroundColor Yellow }
if (!(Test-Path $Sound)) { Write-Host "Warning: Sound file not found: $Sound" -ForegroundColor Yellow }

$PyInstallerArgs = @(
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name=GotifyClient',
    "--icon=$Icon",
    "--add-data=$Icon;.",
    "--add-data=$Sound;.",
    (Join-Path $RepoRoot 'main.py')
)

& $PythonExe -m PyInstaller @PyInstallerArgs

Write-Host 'Copying setup.ps1 into dist...' -ForegroundColor Cyan
$SetupSrc = Join-Path $RepoRoot 'setup.ps1'
$DistDir = Join-Path $RepoRoot 'dist'
if ((Test-Path $SetupSrc) -and (Test-Path $DistDir)) {
    Copy-Item $SetupSrc -Destination (Join-Path $DistDir 'setup.ps1') -Force
    Write-Host 'setup.ps1 copied.' -ForegroundColor Green
} else {
    Write-Host 'setup.ps1 copy skipped (source or dist missing).' -ForegroundColor Yellow
}

Write-Host 'Build complete. See dist/ for output.' -ForegroundColor Green
