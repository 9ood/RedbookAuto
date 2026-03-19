$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

function Require-Command($name) {
  $command = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $command) {
    throw "$name is not installed."
  }
}

Require-Command "python"
Require-Command "node"

$cliPath = Join-Path $projectRoot "xhs-mcp-fix\dist\xhs-mcp.js"
if (-not (Test-Path $cliPath)) {
  throw "xhs-mcp CLI is missing: $cliPath"
}

$pendingDir = Join-Path $projectRoot "queue\pending"
$pendingItems = @(Get-ChildItem $pendingDir -Directory -ErrorAction SilentlyContinue)
if ($pendingItems.Count -eq 0) {
  throw "No pending queue items found."
}

$statusJson = & node $cliPath status --compact
if ($LASTEXITCODE -ne 0) {
  throw "xhs-mcp status failed: $statusJson"
}

$status = $statusJson | ConvertFrom-Json
if (-not $status.loggedIn) {
  Write-Output "XiaoHongShu login is required before publishing."
  exit 1
}

Write-Output "Environment check passed"
Write-Output "Pending items: $($pendingItems.Count)"
Write-Output "XiaoHongShu login: ready"
