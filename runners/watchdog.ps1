<#
    watchdog.ps1 - start any registered runner that is not currently running.

    IT KNOWS NOTHING ABOUT TENNIS, OR BASEBALL, OR ANY TEST.
    It reads runners.json, looks for each entry's `match` string in the process
    list, and starts the ones it cannot find. Adding a test is an entry in that
    file; this script never changes.

    THE TWO THINGS IT WILL NOT DO, BOTH ENFORCED BY A TEST
      1. It NEVER stops, kills or signals a process. Not a stale one, not a
         duplicate, not anything. `tests/test_watchdog_cannot_stop.py` greps this
         file for Stop-Process / taskkill / .Kill( and fails if one appears.
         That is what keeps the two recorders on this laptop safe: a script with
         no stopping code cannot stop a recorder by mistake.
      2. It NEVER touches a process that is not in the registry. The only thing
         it can act on is an entry it was given.

    WHY IT CAN AFFORD TO BE THIS DUMB
      Every runner already holds its own single-instance lock and refuses to
      start twice. So the worst case if this script is wrong about liveness is a
      process that starts, sees the lock, prints "already running" and exits.
      The smart half lives in the runner; the watchdog stays stupid on purpose.

    Run it as often as you like. When everything is up it does nothing and costs
    a few hundred milliseconds.
#>

[CmdletBinding()]
param(
    [string]$Registry,
    [switch]$WhatIfOnly,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if (-not $Registry) { $Registry = Join-Path $here "runners.json" }

function Say($msg) { if (-not $Quiet) { Write-Host $msg } }

if (-not (Test-Path $Registry)) { throw "registry not found: $Registry" }
$cfg = Get-Content $Registry -Raw | ConvertFrom-Json

# One process-table read for all entries, rather than one per entry.
$procs = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue)

$started = 0
$alive = 0
$skipped = 0

foreach ($r in $cfg.runners) {
    if (-not $r.enabled) {
        Say ("  {0,-10} disabled in the registry - ignored" -f $r.name)
        $skipped++
        continue
    }

    $dir = Join-Path $root $r.dir
    $exe = Join-Path $dir $r.exe

    if (-not (Test-Path $dir)) {
        Say ("  {0,-10} FOLDER MISSING: {1}" -f $r.name, $dir)
        continue
    }
    if (-not (Test-Path $exe)) {
        Say ("  {0,-10} NO INTERPRETER at {1} - run its setup first" -f $r.name, $r.exe)
        continue
    }

    # Liveness by command line, not by lock file. A lock can be stale; a running
    # process cannot be. `match` must be unique across entries - install.ps1
    # refuses a registry where two entries share one.
    $running = @($procs | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains($r.match) -and $_.CommandLine.Contains($r.dir)
    })

    if ($running.Count -gt 0) {
        Say ("  {0,-10} ALIVE   pid {1}" -f $r.name, ($running.ProcessId -join ", "))
        $alive++
        continue
    }

    if ($WhatIfOnly) {
        Say ("  {0,-10} would START" -f $r.name)
        continue
    }

    $logPath = Join-Path $dir $r.log
    $logDir = Split-Path -Parent $logPath
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }

    # Start-Process REPLACES the redirect target rather than appending, so the
    # previous wrapper log is kept as .prev before it is overwritten. This file
    # only ever catches catastrophic startup failure - an import error that dies
    # before the runner's own logging exists - and that is exactly the case where
    # losing the previous copy would cost the diagnosis. Each project's real log
    # (`logs/runner.log`) is written by the runner itself and is untouched here.
    if (Test-Path $logPath) { Move-Item $logPath ($logPath + ".prev") -Force }
    if (Test-Path ($logPath + ".err")) { Move-Item ($logPath + ".err") ($logPath + ".err.prev") -Force }

    # Never inherit exchange credentials into a paper process. Each project
    # refuses to start if it finds one; clearing them here fails faster and
    # louder, and costs nothing when they were never set.
    foreach ($v in @("KALSHI_KEY_ID","KALSHI_KEY_PATH","KALSHI_API_KEY","KALSHI_PRIVATE_KEY")) {
        if (Test-Path "env:$v") { Remove-Item "env:$v" }
    }

    Start-Process -FilePath $exe -ArgumentList $r.args -WorkingDirectory $dir `
        -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError ($logPath + ".err")
    Say ("  {0,-10} STARTED" -f $r.name)
    $started++
}

Say ("watchdog: {0} alive, {1} started, {2} disabled" -f $alive, $started, $skipped)
exit 0
