<#
    uninstall_task.ps1 - remove the scheduled task and stop the runner.

    Removes exactly one task and stops exactly one process: the one whose pid
    is written in this project's own lock file. It does not enumerate, signal
    or stop anything else, so the recorders on this laptop are untouched.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$TaskName = "TennisPaperForward")

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $here
$lock = Join-Path $proj "data\.runner.lock"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($TaskName, "Unregister scheduled task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'." -ForegroundColor Green
    }
} else {
    Write-Host "No scheduled task named '$TaskName'."
}

if (Test-Path $lock) {
    $pidToStop = (Get-Content $lock -Raw | ConvertFrom-Json).pid
    $p = Get-Process -Id $pidToStop -ErrorAction SilentlyContinue
    if ($p -and $PSCmdlet.ShouldProcess("pid $pidToStop", "Stop the forward-test runner")) {
        Write-Host "Stopping the runner (pid $pidToStop): $($p.ProcessName)"
        Stop-Process -Id $pidToStop
        Start-Sleep -Seconds 2
    }
    Remove-Item $lock -ErrorAction SilentlyContinue
}

Write-Host @"

Stopped. NOTHING WAS DELETED. The logs, briefs and state are still in:
    $proj\logs
    $proj\data

Re-running install_task.ps1 resumes from exactly where it stopped.
"@
