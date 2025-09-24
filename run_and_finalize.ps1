$ErrorActionPreference = "Stop"

# Work in the script's folder
$work = Split-Path -Parent $PSCommandPath
Set-Location $work

# Prefer venv Python, fallback to system
$py = Join-Path $work ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# 1) Generate (idempotent – your script exits if today's video exists)
& $py .\auto_quiz.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2) Normalize only if there's a NEW non-_norm MP4
$src = Get-ChildItem .\out -Filter *.mp4 |
  Where-Object { $_.Name -notmatch '_norm\.mp4$' } |
  Sort-Object LastWriteTime -Desc |
  Select-Object -First 1

if ($src) {
  $dst = Join-Path $src.DirectoryName ($src.BaseName + "_norm" + $src.Extension)
  & $py .\tools\post_lufs_latest.py $src.FullName $dst
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  # Replace original with normalized
  Remove-Item $src.FullName -ErrorAction SilentlyContinue
  Rename-Item $dst $src.FullName
  Write-Host "Finalized: $($src.FullName)" -ForegroundColor Green
} else {
  Write-Host "No raw MP4 found; likely already normalized. Skipping LUFS." -ForegroundColor Yellow
}

# 3) Healthcheck ping (optional)
if ($env:HEALTHCHECK_URL) {
  try { Invoke-WebRequest -Uri $env:HEALTHCHECK_URL -UseBasicParsing | Out-Null } catch {}
}
