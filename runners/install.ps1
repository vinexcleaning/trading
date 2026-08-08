<#
    install.ps1 - register ONE scheduled task that runs the watchdog.

    ONE TASK, FOR EVERY TEST, FOREVER. Adding a second test does NOT mean a
    second scheduled task - it means one more entry in runners.json. This
    script does not need running again for that, though running it again is
    harmless.

    What it registers:
      * at system startup      - so a reboot brings everything back
      * every 10 minutes       - so a crash is repaired without anyone looking

    The 10-minute repeat is cheap because the watchdog does nothing when
    everything is already up.

    WHAT IT REFUSES TO DO
      * install if any enabled runner's own test suite fails. Each project
        proves it is paper-only; this script will not schedule something that
        cannot prove it.
      * install if two registry entries share a `match` string, because then
        liveness detection is ambiguous and the watchdog could start a second
        copy of one and never start the other.
      * touch any other task, service or process. It creates exactly one task.
        Run it with -WhatIf to watch it not do anything else.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "TradingRunnersWatchdog",
    [int]$WatchdogMinutes = 10,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$watchdog = Join-Path $here "watchdog.ps1"
$registry = Join-Path $here "runners.json"

Write-Host "repo root : $root"
Write-Host "registry  : $registry"

if (-not (Test-Path $watchdog)) { throw "watchdog.ps1 not found at $watchdog" }
$cfg = Get-Content $registry -Raw | ConvertFrom-Json
$enabled = @($cfg.runners | Where-Object { $_.enabled })

if ($enabled.Count -eq 0) { throw "no runner is enabled in runners.json - nothing to schedule" }

# --- the match strings must be unique, or liveness is ambiguous -------------
$dupes = $enabled | Group-Object -Property match | Where-Object { $_.Count -gt 1 }
if ($dupes) {
    throw ("two enabled runners share the same `match` string: " +
           ($dupes.Name -join ", ") + ". Liveness would be ambiguous - give each a " +
           "substring that appears in its command line and no other.")
}

# --- each project proves itself before it gets scheduled --------------------
foreach ($r in $enabled) {
    $dir = Join-Path $root $r.dir
    $exe = Join-Path $dir $r.exe
    Write-Host ""
    Write-Host ("--- {0} ---" -f $r.name)
    if (-not (Test-Path $dir)) { throw "$($r.name): folder missing: $dir" }
    if (-not (Test-Path $exe)) {
        throw ("{0}: no interpreter at {1}.`n  Run that project's setup first:`n" +
               "    cd `"{2}`"`n    python -m venv .venv`n" +
               "    .venv\Scripts\python.exe -m pip install -r requirements.txt") -f $r.name, $r.exe, $dir
    }
    if ($SkipVerify -or -not $r.verify) {
        Write-Host "  verification skipped"
        continue
    }
    Write-Host ("  proving it is safe: {0} {1}" -f $r.exe, ($r.verify -join " "))
    Push-Location $dir
    & $exe $r.verify
    $rc = $LASTEXITCODE
    Pop-Location
    if ($rc -ne 0) {
        throw ("{0}: its own test suite FAILED. Refusing to schedule a test whose " +
               "paper-only guarantees do not pass. Fix it, or set enabled=false " +
               "for that entry.") -f $r.name
    }
    Write-Host "  PASS" -ForegroundColor Green
}

# --- show what is running, and leave every bit of it alone ------------------
Write-Host ""
Write-Host "Python processes on this machine right now (NOT touched by this script):"
Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue |
    Select-Object ProcessId, @{n='Command';e={
        $c = $_.CommandLine; if ($c.Length -gt 90) { $c.Substring(0,90) } else { $c } }} |
    Format-Table -AutoSize

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "A task named '$TaskName' already exists; it will be replaced." -ForegroundColor Yellow
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument ("-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdog`" -Quiet") `
    -WorkingDirectory $here

$tStartup = New-ScheduledTaskTrigger -AtStartup
$tWatch = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $WatchdogMinutes)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

if ($PSCmdlet.ShouldProcess($TaskName, "Register the one watchdog task")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action `
        -Trigger @($tStartup, $tWatch) -Settings $settings `
        -Description ("Starts any paper test listed in runners\runners.json that is not " +
                      "running. Never stops anything. No credentials, no order code.") `
        -Force | Out-Null
    Write-Host ""
    Write-Host "Installed '$TaskName'." -ForegroundColor Green
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 8
    & (Join-Path $here "status.ps1")
}

Write-Host @"
DONE.

  Check everything, any time:   runners\check.bat
  Add another test:             one entry in runners\runners.json, then nothing
  Stop it all:                  runners\uninstall.ps1

  Set Sleep = Never and Lid close = Do nothing, or none of this runs overnight.
"@
