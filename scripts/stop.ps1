$ErrorActionPreference = "Stop"

$patterns = @(
  @{ Name = "python.exe"; Match = "*RedbookAuto*publisher\\run_once.py*" },
  @{ Name = "node.exe"; Match = "*RedbookAuto*xhs-mcp-fix*dist\\xhs-mcp.js*" },
  @{ Name = "powershell.exe"; Match = "*RedbookAuto*scripts\\run.ps1*" },
  @{ Name = "powershell.exe"; Match = "*RedbookAuto*scripts\\test.ps1*" },
  @{ Name = "powershell.exe"; Match = "*RedbookAuto*scripts\\login.ps1*" },
  @{ Name = "chrome.exe"; Match = "*puppeteer_dev_chrome_profile*" }
)

$processes = @()
foreach ($pattern in $patterns) {
  $found = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq $pattern.Name -and $_.CommandLine -like $pattern.Match
  }
  if ($found) {
    $processes += $found
  }
}

if (-not $processes) {
  Write-Output "No RedbookAuto process is running."
  exit 0
}

$processes |
  Sort-Object ProcessId -Unique |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Output "Stopped PID $($_.ProcessId) ($($_.Name))"
  }
