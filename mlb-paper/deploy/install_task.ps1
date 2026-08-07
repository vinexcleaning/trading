# =============================================================================
#  Register the mlb-paper runner as a Windows scheduled task.
#
#  It starts at boot, restarts itself if it ever exits, and runs whether or not
#  anyone is logged in. That combination is the whole point: bot-hunt's recorder
#  died for 2.5 hours with zero bytes in its error log because it had been
#  launched from a shell and died with it.
#
#  PAPER ONLY. This registers a task that runs `src\run.py`, which reads no
#  credential and has no order path. `tests\test_paper_only.py` enforces that.
#
#  Run it:   right-click this file -> "Run with PowerShell"
#  Remove:   .\install_task.ps1 -Uninstall
# =============================================================================
[CmdletBinding()]
param(
  [switch]$Uninstall,
  [string]$TaskName = "mlb-paper"
)

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$bat  = Join-Path $PSScriptRoot "run_mlb_paper.bat"

if ($Uninstall) {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "removed scheduled task '$TaskName'"
  } else {
    Write-Host "no scheduled task '$TaskName' to remove"
  }
  return
}

if (-not (Test-Path $bat)) { throw "missing $bat" }
if (-not (Test-Path (Join-Path $proj ".venv\Scripts\python.exe"))) {
  throw "no virtual environment. Run deploy\setup.bat first."
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" `
            -Argument "/c `"$bat`"" -WorkingDirectory $proj

# Two triggers, deliberately. AtStartup covers a reboot; a daily trigger is the
# belt to that braces -- if the task somehow ends without the restart policy
# catching it, it comes back within a day rather than staying dead.
$trigStart = New-ScheduledTaskTrigger -AtStartup
$trigDaily = New-ScheduledTaskTrigger -Daily -At 06:00

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 5) `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit ([TimeSpan]::Zero)

# S4U runs without a stored password and without a visible window. It does NOT
# need admin rights and it does NOT need the user logged in.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
               -LogonType S4U -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName `
  -Action $action -Trigger @($trigStart, $trigDaily) `
  -Settings $settings -Principal $principal `
  -Description "mlb-paper: PAPER-ONLY forward test of five MLB mentalities on Kalshi. No credentials, no order endpoint, no money." | Out-Null

Write-Host "registered scheduled task '$TaskName'"
Write-Host "  runs      : $bat"
Write-Host "  triggers  : at startup, and daily at 06:00"
Write-Host "  restarts  : every 5 minutes, up to 999 times, if it ever exits"
Write-Host ""
Write-Host "starting it now..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName $TaskName |
  Select-Object TaskName, State |
  Format-Table -AutoSize
Write-Host "check it with:  deploy\check.bat"
