' MercariBOT Silent Background Launcher for Windows
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Check first if a local virtual environment (.venv) exists
venvPython = currentDir & "\.venv\Scripts\pythonw.exe"

If fso.FileExists(venvPython) Then
    pythonExe = venvPython
Else
    pythonExe = "pythonw.exe"
End If

WshShell.CurrentDirectory = currentDir
WshShell.Run Chr(34) & pythonExe & Chr(34) & " main.py", 0, False
