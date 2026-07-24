param(
  [switch]$SkipApi
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Blockchain = Join-Path $Root "Blockchain"
$Api = Join-Path $Root "apps\api"
$Sandbox = Join-Path $Root ".sandbox"
$LocalEnvPath = Join-Path $Sandbox "local-sandbox.env"
$NodeLog = Join-Path $Sandbox "hardhat-node.log"
$NodeErrorLog = Join-Path $Sandbox "hardhat-node.err.log"
$DeployLog = Join-Path $Sandbox "local-deploy.log"
$PidPath = Join-Path $Sandbox "hardhat-node.pid"
$ApiLog = Join-Path $Sandbox "api.log"
$ApiErrorLog = Join-Path $Sandbox "api.err.log"
$ApiPidPath = Join-Path $Sandbox "api.pid"

$HardhatPrivateKey = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

$ProcessEnvironment = [Environment]::GetEnvironmentVariables()
if ($ProcessEnvironment.Contains("Path") -and $ProcessEnvironment.Contains("PATH")) {
  [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
}

function Set-EnvValue {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Value
  )
  $line = "$Key=$Value"
  if (-not (Test-Path $Path)) {
    Write-EnvFileWithRetry $Path $line
    return
  }
  $content = Get-Content -LiteralPath $Path
  $updated = $false
  $next = foreach ($item in $content) {
    if ($item -match "^$([regex]::Escape($Key))=") {
      $updated = $true
      $line
    } else {
      $item
    }
  }
  if (-not $updated) {
    $next = @($next) + $line
  }
  Write-EnvFileWithRetry $Path $next
}

function Write-EnvFileWithRetry {
  param(
    [string]$Path,
    [object]$Value
  )
  for ($attempt = 0; $attempt -lt 8; $attempt += 1) {
    try {
      Set-Content -LiteralPath $Path -Value $Value
      return
    } catch [System.IO.IOException] {
      Start-Sleep -Milliseconds 250
    }
  }
  Set-Content -LiteralPath $Path -Value $Value
}

function Test-RpcReady {
  try {
    $body = @{ jsonrpc = "2.0"; id = 1; method = "eth_chainId"; params = @() } | ConvertTo-Json -Compress
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8545" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 2
    return $response.result -eq "0x7a69"
  } catch {
    return $false
  }
}

function Test-ApiReady {
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    return $health.status -eq "ok"
  } catch {
    return $false
  }
}

function Stop-PidFileProcess {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return }
  $processId = Get-Content -LiteralPath $Path | Select-Object -First 1
  if (-not $processId) { return }
  $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $process.Id -Force
    Start-Sleep -Milliseconds 500
  }
  Remove-Item -LiteralPath $Path -Force
}

function Stop-LocalPortProcess {
  param([int]$Port)
  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  $seen = @{}
  foreach ($connection in $connections) {
    $seen[[string]$connection.OwningProcess] = $true
    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
      Stop-Process -Id $process.Id -Force
      Start-Sleep -Milliseconds 500
    }
  }
  $netstatRows = netstat -ano | Select-String ":$Port\s+.*LISTENING"
  foreach ($row in $netstatRows) {
    $parts = ($row.Line -replace "^\s+", "") -split "\s+"
    $processId = $parts[-1]
    if ($processId -eq "0" -or $seen.ContainsKey($processId)) { continue }
    $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
    if ($process) {
      Stop-Process -Id $process.Id -Force
      Start-Sleep -Milliseconds 500
    }
  }
}

New-Item -ItemType Directory -Force -Path $Sandbox | Out-Null

if (-not (Test-RpcReady)) {
  Stop-PidFileProcess $PidPath
  Stop-LocalPortProcess 8545
  $nodeProcess = Start-Process -FilePath "npm.cmd" -ArgumentList @("exec", "--", "hardhat", "node") -WorkingDirectory $Blockchain -WindowStyle Hidden -RedirectStandardOutput $NodeLog -RedirectStandardError $NodeErrorLog -PassThru
  Set-Content -LiteralPath $PidPath -Value $nodeProcess.Id
  for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
    if (Test-RpcReady) { break }
    Start-Sleep -Seconds 1
  }
}

if (-not (Test-RpcReady)) {
  throw "Hardhat local RPC did not start on http://127.0.0.1:8545. Check $NodeLog."
}

$deployOutput = & npm.cmd --prefix $Blockchain run deploy:local-sandbox 2>&1
$deployOutput | Set-Content -LiteralPath $DeployLog
$marker = $deployOutput | Where-Object { $_ -like "FBJ_LOCAL_SANDBOX=*" } | Select-Object -Last 1
if (-not $marker) {
  throw "Local sandbox deployment did not print the expected marker. Check $DeployLog."
}
$deployment = ($marker -replace "^FBJ_LOCAL_SANDBOX=", "") | ConvertFrom-Json

Set-EnvValue $LocalEnvPath "APP_ENV" "development"
Set-EnvValue $LocalEnvPath "FIXTURE_MODE" "false"
Set-EnvValue $LocalEnvPath "DATABASE_MODE" "memory"
Set-EnvValue $LocalEnvPath "AMOY_RPC_URL" "http://127.0.0.1:8545"
Set-EnvValue $LocalEnvPath "CHAIN_ID" $deployment.chainId
Set-EnvValue $LocalEnvPath "DEFAULT_REWARD_TOKEN" $deployment.rewardToken
Set-EnvValue $LocalEnvPath "REWARD_TOKEN_ADDRESS" $deployment.rewardToken
Set-EnvValue $LocalEnvPath "BOUNTY_ESCROW_ADDRESS" $deployment.bountyEscrow
Set-EnvValue $LocalEnvPath "VERDICT_REGISTRY_ADDRESS" $deployment.verdictRegistry
Set-EnvValue $LocalEnvPath "DISPUTE_MANAGER_ADDRESS" $deployment.disputeManager
Set-EnvValue $LocalEnvPath "DEPLOYER_PRIVATE_KEY" $HardhatPrivateKey
Set-EnvValue $LocalEnvPath "RELAYER_PRIVATE_KEY" $HardhatPrivateKey
Set-EnvValue $LocalEnvPath "DISPUTE_RESOLVER_PRIVATE_KEY" $HardhatPrivateKey
Set-EnvValue $LocalEnvPath "IPFS_PROVIDER" "fixture"
Set-EnvValue $LocalEnvPath "AI_PROVIDER" "fixture"
Set-EnvValue $LocalEnvPath "GITHUB_WEBHOOK_SECRET" "local-sandbox-secret"

if (-not $SkipApi) {
  Stop-PidFileProcess $ApiPidPath
  Stop-LocalPortProcess 8000
  $apiPython = Join-Path $Api ".venv\Scripts\python.exe"
  $apiEnv = "FBJ_ENV_FILE=$LocalEnvPath"
  $apiProcess = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "set `"$apiEnv`" && cd /d `"$Api`" && `"$apiPython`" -m uvicorn app.main:app --port 8000") -WindowStyle Hidden -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErrorLog -PassThru
  Set-Content -LiteralPath $ApiPidPath -Value $apiProcess.Id
  for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
    if (Test-ApiReady) { break }
    Start-Sleep -Seconds 1
  }
  if (-not (Test-ApiReady)) {
    throw "API did not start on http://127.0.0.1:8000."
  }
}

Write-Host "FBJ local sandbox is ready."
Write-Host "RPC: http://127.0.0.1:8545"
Write-Host "Dashboard: http://127.0.0.1:8000/app/"
Write-Host "Chain ID: $($deployment.chainId)"
Write-Host "Deployer: $($deployment.deployer)"
Write-Host "Reward token: $($deployment.rewardToken)"
Write-Host "BountyEscrow: $($deployment.bountyEscrow)"
Write-Host "VerdictRegistry: $($deployment.verdictRegistry)"
Write-Host "DisputeManager: $($deployment.disputeManager)"
Write-Host "API config: $LocalEnvPath"
Write-Host "Logs: $Sandbox"
