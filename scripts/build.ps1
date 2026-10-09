$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
$originalPath = $env:PATH
try {
    # Avoid collecting an unrelated Poppler ICU DLL from the host PATH.
    # Qt 6.12 imports the unsuffixed Windows ICU API, not ICU's _78 symbols.
    $env:PATH = "$root\.venv\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    & "$root\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name AI-Story-Studio --hidden-import keyring.backends.Windows --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    $release = Join-Path $root 'releases\v0.1.0'
    if (Test-Path $release) { throw 'Release folder already exists; preserve it and use a new version folder.' }
    New-Item -ItemType Directory -Path $release | Out-Null
    Copy-Item -LiteralPath "$root\dist\AI-Story-Studio" -Destination $release -Recurse
    Copy-Item -LiteralPath "$root\README.md" -Destination $release
} finally { $env:PATH = $originalPath; Pop-Location }
