Set objShell = CreateObject("WScript.Shell")
objShell.Run """" & Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & ".venv\Scripts\pythonw.exe"" """ & Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "main.py""", 0, False

