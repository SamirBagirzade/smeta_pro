Dim WshShell, ScriptDir, RepoDir, VenvPython, PyEntry

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Configuration
RepoDir = ScriptDir & "\REPO"
VenvPython = RepoDir & "\.venv\Scripts\pythonw.exe"
PyEntry = RepoDir & "\pyqt_crud_mongodb.py"

' Run the batch file hidden to update/setup (0 = hidden, True = wait for it to finish)
WshShell.Run Chr(34) & ScriptDir & "\launcher.bat" & Chr(34), 0, True

' Now run Python directly without any window
If FSO.FileExists(VenvPython) Then
    WshShell.Run Chr(34) & VenvPython & Chr(34) & " " & Chr(34) & PyEntry & Chr(34), 0, False
Else
    ' Fallback to system Python
    WshShell.Run "pythonw.exe " & Chr(34) & PyEntry & Chr(34), 0, False
End If
