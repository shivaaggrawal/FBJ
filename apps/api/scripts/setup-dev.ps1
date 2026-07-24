[CmdletBinding()]
param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$virtualEnvironment = Join-Path $repositoryRoot ".venv"
$python = Join-Path $virtualEnvironment "Scripts\python.exe"
$apiRoot = Join-Path $repositoryRoot "apps\api"
$requirements = Join-Path $repositoryRoot "apps\api\requirements.txt"

if (-not (Test-Path -LiteralPath $python)) {
    & py -3.10 -m venv $virtualEnvironment
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python 3.10 virtual environment. Install Python 3.10 and ensure the py launcher is available."
    }
}

$pythonVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne "3.10") {
    throw "The project virtual environment must use Python 3.10. Remove .venv and run this script again."
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}

& $python -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the pinned API dependencies."
}

if ($RunTests) {
    Push-Location $apiRoot
    try {
        & $python -m pytest -q tests
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

Write-Host "API environment ready. Run .\\apps\\api\\scripts\\setup-dev.ps1 -RunTests to execute the test suite."
