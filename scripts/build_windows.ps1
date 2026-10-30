$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "Installing the optional GUI and packaging dependencies..."
python -m pip install --upgrade pip
python -m pip install -e ".[desktop-build]"

$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
$AppDir = Join-Path $DistDir "HumanBenchmarkBot"
$ZipPath = Join-Path $DistDir "HumanBenchmarkBot-Windows-x64.zip"

if (Test-Path $BuildDir) {
    Remove-Item $BuildDir -Recurse -Force
}
if (Test-Path $DistDir) {
    Remove-Item $DistDir -Recurse -Force
}

Write-Host "Building the one-folder Windows desktop application..."
python -m PyInstaller --noconfirm --clean --windowed --name HumanBenchmarkBot --collect-all PySide6 --collect-all shiboken6 run_desktop.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$Executable = Join-Path $AppDir "HumanBenchmarkBot.exe"
if (-not (Test-Path $Executable)) {
    throw "Expected executable was not produced: $Executable"
}

Copy-Item (Join-Path $ProjectRoot "README.md") $AppDir
Copy-Item (Join-Path $ProjectRoot "LICENSE") $AppDir

$FirstRun = @'
HumanBenchmarkBot — Windows portable build

1. Extract the entire ZIP archive to a normal folder.
2. Run HumanBenchmarkBot.exe.
3. Open Calibration, capture the screen, and select the full game viewport.
4. Configure a game and run Preflight before starting.
5. Preview is safe and does not send mouse or keyboard input.
6. Actual desktop automation requires the in-app safety acknowledgement.

Important:
- Keep the intended Human Benchmark browser tab visible and active while a run executes.
- The routines are experimental and require supervised verification.
- Calibration only limits the allowed viewport; it does not automatically detect game coordinates.
- Verbal Memory additionally requires Tesseract OCR installed on Windows.
- Use the included README.md for full instructions and safety limitations.
- Do not delete individual files from the extracted application folder.
'@
Set-Content -Path (Join-Path $AppDir "README-FIRST.txt") -Value $FirstRun -Encoding UTF8

Write-Host "Creating portable ZIP..."
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -CompressionLevel Optimal -Force
if ($LASTEXITCODE -ne 0) { throw "Compress-Archive failed" }

Write-Host "Build completed:"
Write-Host "  Executable: $Executable"
Write-Host "  Portable ZIP: $ZipPath"
