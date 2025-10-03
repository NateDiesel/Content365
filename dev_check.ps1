# dev_check.ps1
$ErrorActionPreference = "Stop"

# compile critical module
.\.venv\Scripts\python.exe -m py_compile .\utils\pdf_generator.py

# run quick smokes (fast)
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\python.exe .\smoke_test.py | Write-Host
.\.venv\Scripts\python.exe .\premium_test.py | Write-Host
.\.venv\Scripts\python.exe .\legacy_test.py | Write-Host

Write-Host "OK: compile + smokes passed."
