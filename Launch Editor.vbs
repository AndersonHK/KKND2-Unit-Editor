Option Explicit
Dim shell, files, base, candidate, launcher, command, started, failure
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
base = files.GetParentFolderName(WScript.ScriptFullName)
started = False
' Prefer a local virtual environment, then the Windows Python launcher or PATH.
For Each candidate In Array(base & "\.venv\Scripts\pythonw.exe", "pyw.exe", "pythonw.exe")
    If InStr(candidate, "\") = 0 Or files.FileExists(candidate) Then
        launcher = Chr(34) & candidate & Chr(34)
        If candidate = "pyw.exe" Then launcher = launcher & " -3"
        command = launcher & " " & Chr(34) & base & "\Launch Editor.pyw" & Chr(34)
        On Error Resume Next
        shell.Run command, 0, False
        failure = Err.Number
        Err.Clear
        On Error GoTo 0
        If failure = 0 Then
            started = True
            Exit For
        End If
    End If
Next
If Not started Then
    MsgBox "Python was not found. Install Python 3.9 or newer with Tcl/Tk and the Windows Python launcher, or add Python to PATH. See README.md.", vbExclamation, "KKND2 Unit Editor"
    WScript.Quit 1
End If
