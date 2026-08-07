param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $Root "py-radio"
$SpecFile = Join-Path $BackendDir "bilibili_radio_backend.spec"
$OutputExe = Join-Path $BackendDir "dist\bilibili-radio-backend.exe"
$VenvDir = Join-Path $BackendDir ".venv-desktop"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
  & $Python -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Push-Location $BackendDir
try {
  & $VenvPython -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  & $VenvPython -m pip install pyinstaller==6.11.1
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  & $VenvPython -m PyInstaller --clean --noconfirm $SpecFile
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  if (-not (Test-Path -LiteralPath $OutputExe)) {
    throw "PyInstaller did not create $OutputExe"
  }
}
finally {
  Pop-Location
}
