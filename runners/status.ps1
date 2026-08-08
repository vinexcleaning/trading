<#
    status.ps1 - one page for every registered runner on this machine.

    Read-only. It starts nothing, stops nothing, and changes nothing.

    It prints the RECORDERS FIRST, deliberately. On this laptop two recorders
    are collecting data that cannot be re-pulled at any price, and they matter
    more than anything in the registry. If they are not in that first list,
    nothing else on this page is worth reading yet.
#>

[CmdletBinding()]
param([string]$Registry)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if (-not $Registry) { $Registry = Join-Path $here "runners.json" }
$cfg = Get-Content $Registry -Raw | ConvertFrom-Json

$procs = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue)

Write-Host ""
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host " EVERY PYTHON PROCESS ON THIS MACHINE" -ForegroundColor Cyan
Write-Host " The two recorders must be in this list. They matter more than the tests." -ForegroundColor Cyan
Write-Host "===========================================================================" -ForegroundColor Cyan

if ($procs.Count -eq 0) {
    Write-Host "  NOTHING IS RUNNING. If the recorders are meant to be up, that is the" -ForegroundColor Red
    Write-Host "  urgent problem on this page, not anything below." -ForegroundColor Red
} else {
    $procs | ForEach-Object {
        $cmd = $_.CommandLine
        if ($cmd.Length -gt 95) { $cmd = $cmd.Substring(0, 95) }
        $known = $false
        foreach ($r in $cfg.runners) { if ($_.CommandLine.Contains($r.dir)) { $known = $true } }
        $tag = "recorder/other"
        if ($known) { $tag = "registered" }
        [PSCustomObject]@{ Pid = $_.ProcessId; What = $tag; Command = $cmd }
    } | Format-Table -AutoSize
}

Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host " REGISTERED TESTS" -ForegroundColor Cyan
Write-Host "===========================================================================" -ForegroundColor Cyan

$anyDown = $false
foreach ($r in $cfg.runners) {
    if (-not $r.enabled) {
        Write-Host ("  {0,-10} disabled in runners.json" -f $r.name) -ForegroundColor DarkGray
        continue
    }
    $dir = Join-Path $root $r.dir
    $running = @($procs | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains($r.match) -and $_.CommandLine.Contains($r.dir)
    })
    if ($running.Count -gt 0) {
        Write-Host ("  {0,-10} ALIVE   pid {1}" -f $r.name, ($running.ProcessId -join ", ")) -ForegroundColor Green
    } else {
        Write-Host ("  {0,-10} DOWN    - the watchdog starts it within 10 minutes" -f $r.name) -ForegroundColor Yellow
        $anyDown = $true
    }

    # Each project answers "how is it actually doing" in its own words. The
    # registry does not try to understand any of them.
    $ownStatus = Join-Path $dir "src\status.py"
    $exe = Join-Path $dir $r.exe
    if ((Test-Path $ownStatus) -and (Test-Path $exe)) {
        Push-Location $dir
        try {
            $out = & $exe -m src.status 2>&1
            $keep = $out | Select-String -Pattern "LAST TICK|settled matches|ALERTS|\*\*\*|ALL LOGS|at that rate"
            foreach ($line in $keep) { Write-Host ("      " + $line.ToString().Trim()) }
        } catch {
            Write-Host "      (its own status command failed - see that project's logs)"
        }
        Pop-Location
    }
    Write-Host ""
}

Write-Host "==========================================================================="
$task = Get-ScheduledTask -TaskName "TradingRunnersWatchdog" -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName "TradingRunnersWatchdog"
    Write-Host (" WATCHDOG   installed, state {0}, last ran {1}" -f $task.State, $info.LastRunTime)
} else {
    Write-Host " WATCHDOG   NOT INSTALLED - nothing will restart these if they die." -ForegroundColor Red
    Write-Host "            Install:  powershell -ExecutionPolicy Bypass -File runners\install.ps1"
}
Write-Host "==========================================================================="
Write-Host ""
if ($anyDown) { exit 1 }
exit 0
