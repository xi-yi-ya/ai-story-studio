$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
$originalPath = $env:PATH
try {
    $version = & "$root\.venv\Scripts\python.exe" -c 'from studio import __version__; print(__version__)'
    $release = Join-Path $root "releases\v$version"
    if (Test-Path $release) { throw 'Release folder already exists; preserve it and use a new version folder.' }
    # Avoid collecting an unrelated Poppler ICU DLL from the host PATH.
    # Qt 6.12 imports the unsuffixed Windows ICU API, not ICU's _78 symbols.
    $env:PATH = "$root\.venv\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    & "$root\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name XY-Studio --icon "$root\studio\assets\xy-studio.ico" --add-data "$root\studio\assets;studio/assets" --add-data "$root\studio\skills;studio/skills" --hidden-import keyring.backends.Windows --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    New-Item -ItemType Directory -Path $release | Out-Null
    Copy-Item -LiteralPath "$root\dist\XY-Studio" -Destination $release -Recurse
    Copy-Item -LiteralPath "$root\README.md" -Destination $release
} finally { $env:PATH = $originalPath; Pop-Location }
