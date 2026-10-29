Attribute VB_Name = "ModuleImportCSV"
Option Explicit
'==========================================================================
' Rapport ISTS - Import des CSV et actualisation du rapport
'
'   ImporterCSV        : choisir les 2 CSV puis tout mettre a jour (bouton)
'   ActualiserRapport  : remettre a jour avec les parametres de la feuille Accueil
'   InstallerBoutons   : recree les boutons de la feuille Accueil si besoin
'
' L'import est fait par Power Query (requetes deja presentes dans le classeur :
' Donnees > Requetes et connexions). La macro ecrit seulement les parametres
' (chemins des CSV, mois, niveau) dans la requete "Parametres", puis actualise.
'==========================================================================

Public Sub ImporterCSV()
    Dim fT As Variant, fR As Variant
    fT = Application.GetOpenFilename("Fichiers CSV (*.csv),*.csv", , "1/2 - Choisissez le CSV TRANSPORT (samples / results)")
    If VarType(fT) = vbBoolean Then Exit Sub
    fR = Application.GetOpenFilename("Fichiers CSV (*.csv),*.csv", , "2/2 - Choisissez le CSV REJECTIONS (Annuler = garder le precedent)")
    EcrireParam "CheminTransport", CStr(fT)
    If VarType(fR) <> vbBoolean Then EcrireParam "CheminRejets", CStr(fR)
    ActualiserRapport
End Sub

Public Sub ActualiserRapport()
    Dim f As Variant
    For Each f In Array("CheminTransport", "CheminRejets")
        If Trim(CStr(LireParam(f))) <> "" Then
            If Dir(CStr(LireParam(f))) = "" Then
                MsgBox "Fichier introuvable :" & vbCrLf & LireParam(f) & vbCrLf & vbCrLf & _
                       "Cliquez sur le bouton d'import pour choisir le fichier.", vbExclamation, "Rapport ISTS"
                Exit Sub
            End If
        End If
    Next f

    On Error GoTo Erreur
    Application.ScreenUpdating = False
    Application.StatusBar = "Rapport ISTS : import des CSV avec Power Query..."
    DefinirParametres
    RafraichirConnexions
    Application.CalculateFull
    Application.StatusBar = "Rapport ISTS : mise en forme..."
    MasquerLignesVides
    EcrireParam "DerniereMAJ", Now
    Application.StatusBar = False
    Application.ScreenUpdating = True
    ThisWorkbook.Worksheets("1_Synthese").Activate
    MsgBox "Rapport mis a jour !" & vbCrLf & vbCrLf & _
           "Mois du rapport : " & Format(LireParam("MoisCur"), "mmmm yyyy") & vbCrLf & _
           "Lignes transport : " & NbLignes("Donnees_Transport") & vbCrLf & _
           "Lignes rejets : " & NbLignes("Donnees_Rejets"), vbInformation, "Rapport ISTS"
    Exit Sub
Erreur:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    MsgBox "L'actualisation a echoue :" & vbCrLf & Err.Description & vbCrLf & vbCrLf & _
           "Verifiez : 1) les chemins / le dossier des CSV, 2) le separateur (feuille Accueil), " & _
           "3) que le CSV n'est pas ouvert dans un autre programme.", vbCritical, "Rapport ISTS"
End Sub

' Ecrit la requete Power Query "Parametres" a partir de la feuille Accueil.
Private Sub DefinirParametres()
    Dim m As String, sep As String, niv As String, mois As Variant, q As Object
    sep = Trim(CStr(LireParam("Separateur")))
    If sep = "" Then sep = ","
    If LCase(sep) = "tab" Then sep = "#(tab)"
    niv = CStr(LireParam("Niveau"))
    If Left(niv, 1) = "R" Then niv = "Region" Else If niv <> "District" Then niv = "Auto"
    mois = LireParam("MoisRapport")
    m = "[" & vbCrLf
    m = m & "    Dossier = " & TexteM(LireParam("Dossier")) & "," & vbCrLf
    m = m & "    FichierTransport = " & TexteM(LireParam("CheminTransport")) & "," & vbCrLf
    m = m & "    FichierRejets = " & TexteM(LireParam("CheminRejets")) & "," & vbCrLf
    m = m & "    Separateur = """ & sep & """," & vbCrLf
    If IsDate(mois) And Not IsEmpty(mois) Then
        m = m & "    MoisRapport = #date(" & Year(mois) & ", " & Month(mois) & ", 1)," & vbCrLf
    Else
        m = m & "    MoisRapport = null," & vbCrLf
    End If
    m = m & "    Niveau = """ & niv & """" & vbCrLf & "]"
    On Error Resume Next
    Set q = ThisWorkbook.Queries("Parametres")
    On Error GoTo 0
    If q Is Nothing Then
        ThisWorkbook.Queries.Add "Parametres", m
    ElseIf q.Formula <> m Then
        q.Formula = m
    End If
End Sub

' Actualise toutes les requetes chargees, une par une, en attendant la fin de chacune.
Private Sub RafraichirConnexions()
    Dim cn As Object
    For Each cn In ThisWorkbook.Connections
        If cn.Type = 1 Then                       ' 1 = connexion OLE DB (Power Query)
            cn.OLEDBConnection.BackgroundQuery = False
            cn.Refresh
        End If
    Next cn
End Sub

' Colonne A (masquee) des feuilles du rapport : 1 = donnees, 2 = total, 0 = ligne vide a masquer.
Private Sub MasquerLignesVides()
    Dim ws As Object, r As Long, derniere As Long, v As Long
    For Each ws In ThisWorkbook.Worksheets
        If IsNumeric(Left(ws.Name, 1)) Then
            derniere = ws.UsedRange.Row + ws.UsedRange.Rows.Count
            For r = 1 To derniere
                v = Indicateur(ws, r)
                If v >= 0 Then ws.Rows(r).Hidden = (v = 0)
            Next r
        End If
    Next ws
End Sub

Private Function Indicateur(ByVal ws As Object, ByVal r As Long) As Long
    Dim v As Variant
    v = ws.Cells(r, 1).Value
    Indicateur = -1
    If IsError(v) Or IsEmpty(v) Then Exit Function
    If VarType(v) = vbDouble Then Indicateur = CLng(v)
End Function

Public Sub InstallerBoutons()
    Dim ws As Object, b As Object
    Set ws = ThisWorkbook.Worksheets("Accueil")
    On Error Resume Next
    ws.Shapes("btnImporter").Delete
    ws.Shapes("btnActualiser").Delete
    On Error GoTo 0
    Set b = ws.Buttons.Add(ws.Range("D4").Left, ws.Range("D4").Top, 260, 34)
    b.Name = "btnImporter": b.OnAction = "ImporterCSV": b.Caption = "Importer les CSV et generer le rapport"
    Set b = ws.Buttons.Add(ws.Range("D7").Left, ws.Range("D7").Top, 260, 26)
    b.Name = "btnActualiser": b.OnAction = "ActualiserRapport": b.Caption = "Actualiser le rapport"
End Sub

'--------------------------------------------------------------------------
Private Function LireParam(ByVal nom As String) As Variant
    LireParam = ThisWorkbook.Names(nom).RefersToRange.Value
End Function

Private Sub EcrireParam(ByVal nom As String, ByVal valeur As Variant)
    ThisWorkbook.Names(nom).RefersToRange.Value = valeur
End Sub

Private Function NbLignes(ByVal feuille As String) As Long
    NbLignes = Application.WorksheetFunction.CountA(ThisWorkbook.Worksheets(feuille).Columns(2)) - 1
End Function

' Texte M entre guillemets, ou null si vide.
Private Function TexteM(ByVal v As Variant) As String
    Dim s As String
    s = Trim(CStr(v))
    If s = "" Then
        TexteM = "null"
    Else
        TexteM = """" & Replace(s, """", """""") & """"
    End If
End Function
