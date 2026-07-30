param(
  [string]$Output
)

$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
$projectRoot = Join-Path $repoRoot "bilibili-radio"
if (-not $Output) {
  $Output = Join-Path $repoRoot "bilibili-radio-deploy.tar.gz"
}

Set-Location $projectRoot

$dirty = git status --short -- .
if ($dirty) {
  Write-Warning "Working tree has uncommitted project changes; the archive is generated from HEAD only."
  $dirty | ForEach-Object { Write-Warning $_ }
}

git -C $repoRoot archive `
  --format=tar.gz `
  --prefix=bilibili-radio/ `
  --output=$Output `
  HEAD:bilibili-radio

Write-Host "Wrote $Output"
tar -tzf $Output | Select-Object -First 20
