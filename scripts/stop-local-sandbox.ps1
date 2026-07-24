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

foreach ($port in @(8000, 8545)) {
  $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  $seen = @{}
  foreach ($connection in $connections) {
    $seen[[string]$connection.OwningProcess] = $true
    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
      Stop-Process -Id $process.Id -Force
      Write-Host "Stopped process $($process.Id) on port $port."
    }
  }
  $netstatRows = netstat -ano | Select-String ":$port\s+.*LISTENING"
  foreach ($row in $netstatRows) {
    $parts = ($row.Line -replace "^\s+", "") -split "\s+"
    $processId = $parts[-1]
    if ($processId -eq "0" -or $seen.ContainsKey($processId)) { continue }
    $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
    if ($process) {
      Stop-Process -Id $process.Id -Force
      Write-Host "Stopped process $($process.Id) on port $port."
    }
  }
}

Write-Host "FBJ local sandbox processes stopped."
