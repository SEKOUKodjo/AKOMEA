Attribute VB_Name = "ImportModule"
Option Explicit
'==========================================================================
' ISTS Report - CSV import and report refresh
'
'   ImportCSV       : select the 2 CSV files, then refresh everything (button)
'   RefreshReport   : refresh again using the settings on the Home sheet
'   InstallButtons  : recreate the buttons on the Home sheet if needed
'
' The import itself is done by Power Query (queries already in the workbook:
' Data > Queries & Connections). This macro only writes the settings
' (CSV paths, month, level) into the "Parameters" query, then refreshes.
'==========================================================================

Public Sub ImportCSV()
    Dim fT As Variant, fR As Variant
    fT = Application.GetOpenFilename("CSV files (*.csv),*.csv", , "1/2 - Select the TRANSPORT CSV (samples / results)")
    If VarType(fT) = vbBoolean Then Exit Sub
    fR = Application.GetOpenFilename("CSV files (*.csv),*.csv", , "2/2 - Select the REJECTIONS CSV (Cancel = keep the previous one)")
    WriteSetting "TransportPath", CStr(fT)
    If VarType(fR) <> vbBoolean Then WriteSetting "RejectionsPath", CStr(fR)
    RefreshReport
End Sub

Public Sub RefreshReport()
    Dim f As Variant
    For Each f In Array("TransportPath", "RejectionsPath")
        If Trim(CStr(ReadSetting(f))) <> "" Then
            If Dir(CStr(ReadSetting(f))) = "" Then
                MsgBox "File not found:" & vbCrLf & ReadSetting(f) & vbCrLf & vbCrLf & _
                       "Click the import button to select the file again.", vbExclamation, "ISTS Report"
                Exit Sub
            End If
        End If
    Next f

    On Error GoTo Failed
    Application.ScreenUpdating = False
    Application.StatusBar = "ISTS Report: importing the CSV files with Power Query..."
    WriteParameters
    RefreshConnections
    Application.CalculateFull
    Application.StatusBar = "ISTS Report: formatting..."
    HideEmptyRows
    WriteSetting "LastUpdate", Now
    Application.StatusBar = False
    Application.ScreenUpdating = True
    ThisWorkbook.Worksheets("1_Summary").Activate
    MsgBox "Report updated!" & vbCrLf & vbCrLf & _
           "Reporting month: " & Format(ReadSetting("CurMonth"), "mmmm yyyy") & vbCrLf & _
           "Transport rows: " & RowCount("Data_Transport") & vbCrLf & _
           "Rejection rows: " & RowCount("Data_Rejections"), vbInformation, "ISTS Report"
    Exit Sub
Failed:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    MsgBox "The refresh failed:" & vbCrLf & Err.Description & vbCrLf & vbCrLf & _
           "Please check: 1) the CSV paths / folder, 2) the separator (Home sheet), " & _
           "3) that the CSV file is not open in another program.", vbCritical, "ISTS Report"
End Sub

' Writes the Power Query "Parameters" query from the Home sheet settings.
Private Sub WriteParameters()
    Dim m As String, sep As String, lvl As String, mon As Variant, q As Object
    sep = Trim(CStr(ReadSetting("Separator")))
    If sep = "" Then sep = ","
    If LCase(sep) = "tab" Then sep = "#(tab)"
    lvl = CStr(ReadSetting("Level"))
    If lvl <> "Region" And lvl <> "District" Then lvl = "Auto"
    mon = ReadSetting("ReportMonth")
    m = "[" & vbCrLf
    m = m & "    Folder = " & MText(ReadSetting("Folder")) & "," & vbCrLf
    m = m & "    TransportFile = " & MText(ReadSetting("TransportPath")) & "," & vbCrLf
    m = m & "    RejectionsFile = " & MText(ReadSetting("RejectionsPath")) & "," & vbCrLf
    m = m & "    Separator = """ & sep & """," & vbCrLf
    If IsDate(mon) And Not IsEmpty(mon) Then
        m = m & "    ReportMonth = #date(" & Year(mon) & ", " & Month(mon) & ", 1)," & vbCrLf
    Else
        m = m & "    ReportMonth = null," & vbCrLf
    End If
    m = m & "    Level = """ & lvl & """" & vbCrLf & "]"
    On Error Resume Next
    Set q = ThisWorkbook.Queries("Parameters")
    On Error GoTo 0
    If q Is Nothing Then
        ThisWorkbook.Queries.Add "Parameters", m
    ElseIf q.Formula <> m Then
        q.Formula = m
    End If
End Sub

' Refreshes every loaded query, one by one, waiting for each to finish.
Private Sub RefreshConnections()
    Dim cn As Object
    For Each cn In ThisWorkbook.Connections
        If cn.Type = 1 Then                       ' 1 = OLE DB connection (Power Query)
            cn.OLEDBConnection.BackgroundQuery = False
            cn.Refresh
        End If
    Next cn
End Sub

' Hidden column A of the report sheets: 1 = data row, 2 = total row, 0 = empty row to hide.
Private Sub HideEmptyRows()
    Dim ws As Object, r As Long, lastRow As Long, v As Long
    For Each ws In ThisWorkbook.Worksheets
        If IsNumeric(Left(ws.Name, 1)) Then
            lastRow = ws.UsedRange.Row + ws.UsedRange.Rows.Count
            For r = 1 To lastRow
                v = RowFlag(ws, r)
                If v >= 0 Then ws.Rows(r).Hidden = (v = 0)
            Next r
        End If
    Next ws
End Sub

Private Function RowFlag(ByVal ws As Object, ByVal r As Long) As Long
    Dim v As Variant
    v = ws.Cells(r, 1).Value
    RowFlag = -1
    If IsError(v) Or IsEmpty(v) Then Exit Function
    If VarType(v) = vbDouble Then RowFlag = CLng(v)
End Function

Public Sub InstallButtons()
    Dim ws As Object, b As Object
    Set ws = ThisWorkbook.Worksheets("Home")
    On Error Resume Next
    ws.Shapes("btnImport").Delete
    ws.Shapes("btnRefresh").Delete
    On Error GoTo 0
    Set b = ws.Buttons.Add(ws.Range("D4").Left, ws.Range("D4").Top, 260, 34)
    b.Name = "btnImport": b.OnAction = "ImportCSV": b.Caption = "Import CSV files and build the report"
    Set b = ws.Buttons.Add(ws.Range("D7").Left, ws.Range("D7").Top, 260, 26)
    b.Name = "btnRefresh": b.OnAction = "RefreshReport": b.Caption = "Refresh report"
End Sub

'--------------------------------------------------------------------------
Private Function ReadSetting(ByVal nm As String) As Variant
    ReadSetting = ThisWorkbook.Names(nm).RefersToRange.Value
End Function

Private Sub WriteSetting(ByVal nm As String, ByVal value As Variant)
    ThisWorkbook.Names(nm).RefersToRange.Value = value
End Sub

Private Function RowCount(ByVal sheetName As String) As Long
    RowCount = Application.WorksheetFunction.CountA(ThisWorkbook.Worksheets(sheetName).Columns(2)) - 1
End Function

' M text literal in quotes, or null when empty.
Private Function MText(ByVal v As Variant) As String
    Dim s As String
    s = Trim(CStr(v))
    If s = "" Then
        MText = "null"
    Else
        MText = """" & Replace(s, """", """""") & """"
    End If
End Function
