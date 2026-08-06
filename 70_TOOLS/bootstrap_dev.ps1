<#
Create the local development environment after a clean clone.

Examples:
  .\70_TOOLS\bootstrap_dev.ps1
  .\70_TOOLS\bootstrap_dev.ps1 -Verify

This script creates only ignored local files: .test-venv and Playwright browser cache.
#>
[CmdletBinding()]
param([switch]$Verify)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Program {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "실행 실패: $Program $($Arguments -join ' ')"
    }
}

$pythonProgram = $null
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notmatch '\\WindowsApps\\python(?:3)?\.exe$') {
    $pythonProgram = $pythonCommand.Source
}

if (-not $pythonProgram) {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        $pythonProgram = $pythonLauncher.Source
    }
}

if (-not $pythonProgram) {
    $codexPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $codexPython) {
        $pythonProgram = $codexPython
    }
}

if (-not $pythonProgram) {
    throw 'Python 3.11 이상을 설치한 뒤 다시 실행하세요: https://www.python.org/downloads/'
}

$pythonVersion = & $pythonProgram -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]'3.11') {
    throw "Python 3.11 이상이 필요합니다. 현재 버전: $pythonVersion"
}

$venvPython = Join-Path $projectRoot '.test-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    Invoke-Program $pythonProgram @('-m', 'venv', (Join-Path $projectRoot '.test-venv'))
}

Invoke-Program $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Program $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $projectRoot 'requirements-dev.txt'))
Invoke-Program $venvPython @('-m', 'playwright', 'install', 'chromium')

if ($Verify) {
    Invoke-Program $venvPython @('-X', 'utf8', (Join-Path $projectRoot '70_TOOLS\make_manifest.py'), '--check')
    Invoke-Program $venvPython @('-X', 'utf8', (Join-Path $projectRoot '70_TOOLS\run_all_tests.py'), '--jobs', '1')
}

Write-Host '준비 완료: .test-venv와 Chromium 검사 브라우저를 만들었습니다.'
