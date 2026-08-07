<#
    install_task.ps1 - register the forward test with Windows Task Scheduler.

    WHAT IT CREATES
      One task, "TennisPaperForward". Two triggers:
        * at system startup, so a reboot brings it back
        * every 10 minutes, forever, as a watchdog

      The 10-minute repeat is safe because run_forward.bat exits immediately
      when a live runner already holds the lock. So the normal case is a
      no-op that costs a few milliseconds, and the abnormal case - the runner
      died at 3am - is repaired within ten minutes without anybody looking.

    WHAT IT DOES NOT DO, DELIBERATELY
      It creates exactly one task and touches nothing else. It does not stop,
      start, query, restart or reconfigure any other task, service or
      process. The two recorders running on this laptop are never referenced.
      Run it with -WhatIf first if you want to see that for yourself.

    IT CANNOT PLACE A TRADE. The task runs a paper-only package with no
    credentials, no order endpoint and a GET-only host allowlist.

    USAGE (PowerShell, "Run as administrator" NOT required for a user task):
        cd C:\Users\<you>\trading\tennis-paper-forward\deploy
        powershell -ExecutionPolicy Bypass -File .\install_task.ps1
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "TennisPaperForward",
    [int]$WatchdogMinutes = 10
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $here
$bat  = Join-Path $here "run_forward.bat"
$py   = Join-Path $proj ".venv\Scripts\python.exe"

Write-Host "project : $proj"
Write-Host "wrapper : $bat"

if (-not (Test-Path $bat)) { throw "run_forward.bat not found at $bat" }
if (-not (Test-Path $py))  {
    throw "No interpreter at $py. Create it first:`n" +
          "  cd `"$proj`"`n" +
          "  python -m venv .venv`n" +
          "  .venv\Scripts\python.exe -m pip install -r requirements.txt"
}

# --- refuse to run if the paper-only guards do not pass --------------------
Write-Host "`nRunning the paper-only guards before installing anything..."
& $py -m pytest (Join-Path $proj "tests") -q
if ($LASTEXITCODE -ne 0) {
    throw "The test suite failed. Refusing to install a scheduled task for a " +
          "package whose paper-only guards do not pass."
}
Write-Host "Guards pass." -ForegroundColor Green

# --- show what else is running, and leave it alone -------------------------
Write-Host "`nPython processes currently on this machine (NOT touched by this script):"
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Select-Object ProcessId, CreationDate,
        @{n='Command';e={ $_.CommandLine.Substring(0, [Math]::Min(100, $_.CommandLine.Length)) }} |
    Format-Table -AutoSize

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "`nA task named '$TaskName' already exists; it will be replaced." -ForegroundColor Yellow
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$bat`"" -WorkingDirectory $proj

$tStartup = New-ScheduledTaskTrigger -AtStartup
$tWatch   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $WatchdogMinutes)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task")) {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action -Trigger @($tStartup, $tWatch) -Settings $settings `
        -Description ("Tennis paper-only forward test. Reads public Kalshi and " +
                      "GitHub data, places no orders, holds no credentials. " +
                      "Watchdog: the wrapper exits at once if a runner is alive.") `
        -Force | Out-Null

    Write-Host "`nInstalled '$TaskName'." -ForegroundColor Green
    Write-Host "Starting it now..."
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 3
    Get-ScheduledTask -TaskName $TaskName |
        Select-Object TaskName, State | Format-Table -AutoSize
}

Write-Host @"

DONE.

  Check on it any time, from anywhere:
      $here\check.bat

  Stop it for good:
      powershell -ExecutionPolicy Bypass -File "$here\uninstall_task.ps1"

  The results, once matches accumulate:
      cd "$proj"
      .venv\Scripts\python.exe -m src.analyse

  ALSO: set Power and battery to Sleep = Never (both plugged in and on
  battery) and Lid close action = Do nothing. If the laptop sleeps, this
  test records nothing and the gap cannot be filled afterwards - Kalshi
  publishes no historical order-book endpoint.
"@
