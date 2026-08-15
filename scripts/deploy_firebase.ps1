$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$FirebaseDir = Join-Path $Root "firebase"

if (-not (Get-Command firebase -ErrorAction SilentlyContinue)) {
    throw "Firebase CLI is not on PATH."
}

Push-Location $FirebaseDir
try {
    firebase deploy --only "firestore:rules,firestore:indexes,storage"
}
finally {
    Pop-Location
}
