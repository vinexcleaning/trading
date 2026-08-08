' watchdog_hidden.vbs - run the watchdog with NO WINDOW AT ALL.
'
' Why this exists. The scheduled task fires every ten minutes. If its action is
' powershell.exe directly, Windows creates a console for it, and -WindowStyle
' Hidden only hides that console AFTER it exists - so a black box flashes on
' screen every ten minutes, forever. That is exactly what the user asked not to
' see.
'
' wscript.exe is a GUI-subsystem program: it never gets a console in the first
' place. It launches PowerShell with window style 0 (hidden) and does not wait.
' Nothing is ever drawn.
'
' It does nothing else. No logic, no decisions - the watchdog is still the only
' thing that thinks.
Dim shell, here, ps
Set shell = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
ps = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "watchdog.ps1"" -Quiet"
shell.Run ps, 0, False
