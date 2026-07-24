$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Sandbox = Join-Path $Root ".sandbox"
$PidFiles = @(
  (Join-Path $Sandbox "api.pid"),
  (Join-Path $Sandbox "hardhat-node.pid")
)

foreach ($pidFile in $PidFiles) {
  if (-not (Test-Path $pidFile)) { continue }
  $processId = Get-Content -LiteralPath $pidFile | Select-Object -First 1
  if (-not $processId) { continue }
  $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $process.Id -Force
    Write-Host "Stopped process $($process.Id)."
  }
  Remove-Item -LiteralPath $pidFile -Force
}

Write-Host "FBJ local sandbox processes stopped."
