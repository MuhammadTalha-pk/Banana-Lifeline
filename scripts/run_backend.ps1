$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Backend = Join-Path $Root "backend"

Push-Location $Backend
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        throw "backend\\.venv is missing. Follow docs/AI_BACKEND_SETUP.md first."
    }
    if (-not (Test-Path ".env")) {
        throw "backend\\.env is missing. Copy .env.example to .env and configure real values."
    }
    & ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
finally {
    Pop-Location
}
