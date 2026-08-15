param(
    [string]$Org = "com.muhammadtalha"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Mobile = Join-Path $Root "mobile"
$Backup = Join-Path $env:TEMP ("banana_lifeline_mobile_source_" + [guid]::NewGuid().ToString("N"))

Write-Host "Banana Lifeline mobile: $Mobile" -ForegroundColor Green

if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw "Flutter is not on PATH."
}

New-Item -ItemType Directory -Path $Backup | Out-Null

$preserve = @(
    "lib",
    "config",
    "pubspec.yaml",
    "analysis_options.yaml",
    "l10n.yaml"
)

foreach ($item in $preserve) {
    $source = Join-Path $Mobile $item
    if (Test-Path $source) {
        Copy-Item $source -Destination $Backup -Recurse -Force
    }
}

Push-Location $Mobile
try {
    flutter create . `
        --project-name banana_lifeline `
        --org $Org `
        --platforms android,ios

    foreach ($item in $preserve) {
        $source = Join-Path $Backup $item
        $destination = Join-Path $Mobile $item
        if (Test-Path $source) {
            if (Test-Path $destination) {
                Remove-Item $destination -Recurse -Force
            }
            Copy-Item $source -Destination $destination -Recurse -Force
        }
    }

    flutter pub get
    flutter gen-l10n

    Write-Host ""
    Write-Host "Platform wrappers generated." -ForegroundColor Green
    Write-Host "Now add Android/iOS permissions from docs/MOBILE_SETUP.md." -ForegroundColor Yellow
    Write-Host "Then create mobile/config/dev.json and run:" -ForegroundColor Yellow
    Write-Host 'flutter run --dart-define-from-file=config/dev.json'
}
finally {
    Pop-Location
    if (Test-Path $Backup) {
        Remove-Item $Backup -Recurse -Force
    }
}
