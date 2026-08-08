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

# ---------------------------------------------------------------------------
#  VERIFY, DO NOT ANNOUNCE.  The first version of this script printed
#  "registered scheduled task 'mlb-paper'" while Register-ScheduledTask had
#  actually failed with Access Denied -- the CIM error is non-terminating and
#  slipped past $ErrorActionPreference. A script that reports success it did not
#  achieve is worse than one that crashes: GUARDS #13, assert the CONTENT, not
#  the call. Every path below reads the task back before saying anything.
# ---------------------------------------------------------------------------
$registered = $false
$why = ""
try {
  Register-ScheduledTask -TaskName $TaskName `
    -Action $action -Trigger @($trigStart, $trigDaily) `
    -Settings $settings -Principal $principal -Force `
    -Description "mlb-paper: PAPER-ONLY forward test of five MLB mentalities on Kalshi. No credentials, no order endpoint, no money." `
    -ErrorAction Stop | Out-Null
} catch { $why = $_.Exception.Message }
$registered = [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)

if (-not $registered) {
  Write-Host ""
  Write-Host "SCHEDULED TASK NOT REGISTERED: $why" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "On this machine Task Scheduler refuses a non-elevated register."
  Write-Host "That is a MACHINE POLICY, not a fault in this package, and the"
  Write-Host "README used to claim admin was not needed. It is."
  Write-Host ""
  Write-Host "TWO WAYS FORWARD, both fine:"
  Write-Host "  1. Right-click PowerShell -> 'Run as administrator', then run"
  Write-Host "     this script again. Gives you restart-on-failure and a run"
  Write-Host "     that continues whether or not you are logged in."
  Write-Host "  2. Do nothing. A Startup shortcut is installed below instead."
  Write-Host "     It brings the runner back at every logon, which covers a"
  Write-Host "     reboot, a shutdown and a hibernate. It does NOT restart the"
  Write-Host "     runner if it dies while you stay logged in."
}

# The no-admin fallback, installed either way so there are two nets.
$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup 'mlb-paper.lnk'
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$sc.TargetPath = $bat
$sc.WorkingDirectory = $proj
$sc.WindowStyle = 7
$sc.Description = 'mlb-paper PAPER-ONLY forward test'
$sc.Save()
if (-not (Test-Path $lnk)) { throw "could not create the Startup shortcut either" }
Write-Host ""
Write-Host "VERIFIED  startup shortcut : $lnk"
if ($registered) {
  Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  $t = Get-ScheduledTask -TaskName $TaskName
  Write-Host "VERIFIED  scheduled task   : $($t.TaskName), state=$($t.State)"
  Write-Host "          triggers at startup and daily 06:00; restarts every 5 min"
} else {
  Write-Host "NOT PRESENT  scheduled task (see above) -- the shortcut is doing the work"
}
Write-Host ""
Write-Host "check it with:  deploy\check.bat"
