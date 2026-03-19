$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$cliPath = Join-Path $projectRoot "xhs-mcp-fix\dist\xhs-mcp.js"
if (-not (Test-Path $cliPath)) {
  throw "xhs-mcp CLI is missing: $cliPath"
}

$loginTimeout = if ($env:REDBOOKAUTO_LOGIN_TIMEOUT) { [int]$env:REDBOOKAUTO_LOGIN_TIMEOUT } else { 120 }

$statusJson = & node $cliPath status --compact
if ($LASTEXITCODE -ne 0) {
  throw "xhs-mcp status failed: $statusJson"
}

$status = $statusJson | ConvertFrom-Json
if (-not $status.loggedIn) {
  Write-Output "XiaoHongShu login is missing. Opening login flow..."
  & node $cliPath login --timeout $loginTimeout
  if ($LASTEXITCODE -ne 0) {
    Write-Output "Login did not complete in time. Please scan the QR code in the browser window and run again."
    exit 1
  }

  $statusJson = & node $cliPath status --compact
  if ($LASTEXITCODE -ne 0) {
    throw "xhs-mcp status failed after login: $statusJson"
  }

  $status = $statusJson | ConvertFrom-Json
  if (-not $status.loggedIn) {
    Write-Output "Login is still incomplete."
    exit 1
  }
}

& python publisher\run_once.py
exit $LASTEXITCODE
