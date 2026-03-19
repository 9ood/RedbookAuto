$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$cliPath = Join-Path $projectRoot "xhs-mcp-fix\dist\xhs-mcp.js"
if (-not (Test-Path $cliPath)) {
  throw "xhs-mcp CLI is missing: $cliPath"
}

& node $cliPath login --timeout 300
exit $LASTEXITCODE
