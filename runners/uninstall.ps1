<#
    uninstall.ps1 - remove the watchdog task.

    It removes ONE scheduled task and stops NOTHING. Runners already started
    keep going until they end on their own or you close them; that is
    deliberate, because a script that stops processes is a script that can stop
    a recorder by mistake. To stop a specific test, use that project's own
    uninstall, which knows its own lock file and stops only its own pid.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$TaskName = "TradingRunnersWatchdog")

$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($TaskName, "Unregister the watchdog task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed '$TaskName'. Nothing was stopped and no data was deleted." -ForegroundColor Green
    }
} else {
    Write-Host "No task named '$TaskName'."
}
Write-Host "Anything already running keeps running. Re-install to resume watching."
