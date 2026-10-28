Attribute VB_Name = "ModuleImportCSV"
Option Explicit
'==========================================================================
' Rapport ISTS - Import des CSV et actualisation automatique du rapport
'
' Macros a lancer (Alt+F8) :
'   ImporterCSV          : choisir les 2 CSV puis tout mettre a jour
'   ActualiserRapport    : remettre a jour avec les CSV deja choisis
'   InstallerBoutons     : (une seule fois) ajoute les boutons sur "Accueil"
'
' Le travail d'import est fait par Power Query : la macro cree / met a jour
' les requetes, les charge dans les feuilles, puis ajuste les graphiques.
' Necessite Excel 2016, 2019, 2021 ou Microsoft 365 (Windows).
'==========================================================================

Public Sub ImporterCSV()
    Dim fT As Variant, fR As Variant
    fT = Application.GetOpenFilename("Fichiers CSV (*.csv),*.csv", , "1/2 - Choisissez le CSV TRANSPORT (samples / results)")
    If VarType(fT) = vbBoolean Then Exit Sub
    fR = Application.GetOpenFilename("Fichiers CSV (*.csv),*.csv", , "2/2 - Choisissez le CSV REJECTIONS (Annuler = garder le precedent)")
    ValeurParam("CheminTransport") = CStr(fT)
    If VarType(fR) <> vbBoolean Then ValeurParam("CheminRejets") = CStr(fR)
    ActualiserRapport
End Sub

Public Sub ActualiserRapport()
    Dim cheminT As String, cheminR As String, mois As Variant
    cheminT = CStr(ValeurParam("CheminTransport"))
    cheminR = CStr(ValeurParam("CheminRejets"))
    If cheminT = "" Or Dir(cheminT) = "" Then
        MsgBox "Fichier CSV transport introuvable :" & vbCrLf & cheminT & vbCrLf & vbCrLf & _
               "Utilisez la macro ImporterCSV pour le choisir.", vbExclamation, "Rapport ISTS"
        Exit Sub
    End If
    If cheminR = "" Or Dir(cheminR) = "" Then
        MsgBox "Fichier CSV des rejets introuvable :" & vbCrLf & cheminR & vbCrLf & vbCrLf & _
               "Utilisez la macro ImporterCSV pour le choisir.", vbExclamation, "Rapport ISTS"
        Exit Sub
    End If

    On Error GoTo Erreur
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationAutomatic

    ' Phase 1 : import des CSV et des listes (independant du mois)
    Application.StatusBar = "Rapport ISTS : import des CSV avec Power Query..."
    DefinirToutesLesRequetes ValeurParam("MoisRapport")
    ChargerPhase 1
    Application.CalculateFull

    ' Phase 2 : tables par formation sanitaire pour le mois du rapport
    mois = ThisWorkbook.Names("MoisCur").RefersToRange.Value2
    If Not IsNumeric(mois) Then mois = 0
    If mois < 1 Then Err.Raise vbObjectError + 1, , _
        "Aucune date valide trouvee dans le CSV (colonnes custom_month / date)."
    Application.StatusBar = "Rapport ISTS : tables par formation sanitaire..."
    DefinirRequete "Parametres", M_Parametres(CDate(mois))
    ChargerPhase 2
    Application.CalculateFull

    Application.StatusBar = "Rapport ISTS : mise en forme des tableaux et graphiques..."
    AjusterRapport
    ValeurParam("DerniereMAJ") = Now

    Application.StatusBar = False
    Application.ScreenUpdating = True
    ThisWorkbook.Worksheets("1_Synthese").Activate
    MsgBox "Rapport mis a jour !" & vbCrLf & vbCrLf & _
           "Mois du rapport : " & Format(ValeurParam("MoisCur"), "mmmm yyyy") & vbCrLf & _
           "Lignes transport : " & ValeurParam_Nb("Donnees_Transport") & vbCrLf & _
           "Lignes rejets : " & ValeurParam_Nb("Donnees_Rejets"), vbInformation, "Rapport ISTS"
    Exit Sub

Erreur:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    MsgBox "L'actualisation a echoue :" & vbCrLf & Err.Description & vbCrLf & vbCrLf & _
           "Verifiez : 1) le separateur du CSV (feuille Accueil), 2) que le fichier n'est pas ouvert ailleurs, " & _
           "3) que vous utilisez Excel 2016 ou plus recent.", vbCritical, "Rapport ISTS"
End Sub

Public Sub InstallerBoutons()
    Dim ws As Worksheet, b As Object
    Set ws = ThisWorkbook.Worksheets("Accueil")
    On Error Resume Next
    ws.Buttons("btnImporter").Delete
    ws.Buttons("btnActualiser").Delete
    On Error GoTo 0
    With ws.Range("D4")
        Set b = ws.Buttons.Add(.Left, .Top, 230, 32)
    End With
    b.Name = "btnImporter": b.OnAction = "ImporterCSV": b.Caption = "Importer les CSV et generer le rapport"
    b.Font.Bold = True
    With ws.Range("D7")
        Set b = ws.Buttons.Add(.Left, .Top, 230, 26)
    End With
    b.Name = "btnActualiser": b.OnAction = "ActualiserRapport": b.Caption = "Actualiser le rapport (memes CSV)"
    MsgBox "Boutons installes sur la feuille Accueil.", vbInformation, "Rapport ISTS"
End Sub

'--------------------------------------------------------------------------
' Requetes Power Query
'--------------------------------------------------------------------------
Private Sub DefinirToutesLesRequetes(ByVal moisSaisi As Variant)
    If IsDate(moisSaisi) And Not IsEmpty(moisSaisi) Then
        DefinirRequete "Parametres", M_Parametres(CDate(moisSaisi))
    Else
        DefinirRequete "Parametres", M_Parametres(Empty)
    End If
    DefinirRequete "Transport", M_Transport()
    DefinirRequete "Rejets", M_Rejets()
    DefinirRequete "Q_Regions", M_Q_Regions()
    DefinirRequete "Q_Districts", M_Q_Districts()
    DefinirRequete "Q_Couverture", M_Q_Couverture()
    DefinirRequete "Q_FOSA_Total", M_Q_FOSA_Total()
    DefinirRequete "Rejets_FOSA", M_Rejets_FOSA()
    DefinirRequete "Intrants_FOSA", M_Intrants_FOSA()
End Sub

Private Sub DefinirRequete(ByVal nom As String, ByVal formule As String)
    Dim wq As Object
    On Error Resume Next
    Set wq = ThisWorkbook.Queries(nom)
    On Error GoTo 0
    If wq Is Nothing Then
        ThisWorkbook.Queries.Add Name:=nom, Formula:=formule
    ElseIf wq.Formula <> formule Then
        wq.Formula = formule
    End If
End Sub

Private Sub ChargerPhase(ByVal phase As Integer)
    If phase = 1 Then ChargerRequete "Transport", "Donnees_Transport", "A1"
    If phase = 1 Then ChargerRequete "Rejets", "Donnees_Rejets", "A1"
    If phase = 1 Then ChargerRequete "Q_Regions", "Q_Regions", "A1"
    If phase = 1 Then ChargerRequete "Q_Districts", "Q_Districts", "A1"
    If phase = 1 Then ChargerRequete "Q_Couverture", "Q_Couverture", "A1"
    If phase = 1 Then ChargerRequete "Q_FOSA_Total", "Q_FOSA_Total", "A1"
    If phase = 2 Then ChargerRequete "Rejets_FOSA", "9_Rejets_FOSA", "B5"
    If phase = 2 Then ChargerRequete "Intrants_FOSA", "11_Intrants_FOSA", "B5"
End Sub

' Charge une requete dans une feuille (la 1re fois : cree la table liee), puis l'actualise.
Private Sub ChargerRequete(ByVal requete As String, ByVal feuille As String, ByVal cellule As String)
    Dim ws As Worksheet, lo As ListObject, nomTable As String
    Set ws = ThisWorkbook.Worksheets(feuille)
    nomTable = "tbl_" & requete
    On Error Resume Next
    Set lo = ws.ListObjects(nomTable)
    On Error GoTo 0
    If lo Is Nothing Then
        ' premiere utilisation : on efface les donnees d'exemple
        ws.Range(ws.Range(cellule), ws.Cells(ws.Rows.Count, ws.Columns.Count)).Clear
        Set lo = ws.ListObjects.Add(SourceType:=0, Source:= _
            "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location=" & requete & _
            ";Extended Properties=""""", Destination:=ws.Range(cellule))
        lo.Name = nomTable
        With lo.QueryTable
            .CommandType = xlCmdSql
            .CommandText = Array("SELECT * FROM [" & requete & "]")
            .RowNumbers = False
            .FillAdjacentFormulas = False
            .PreserveFormatting = True
            .RefreshOnFileOpen = False
            .SavePassword = False
            .SaveData = True
            .AdjustColumnWidth = True
            .PreserveColumnInfo = False
            .RefreshStyle = xlOverwriteCells
        End With
        lo.TableStyle = "TableStyleMedium2"
    End If
    lo.QueryTable.BackgroundQuery = False
    lo.QueryTable.Refresh BackgroundQuery:=False
End Sub

Private Function M_Parametres(ByVal mois As Variant) As String
    Dim m As String, sep As String, site As String
    sep = CStr(ValeurParam("Separateur"))
    If sep = "" Then sep = ","
    If LCase(sep) = "tab" Then sep = "#(tab)"
    site = CStr(ValeurParam("SiteRejets"))
    If site = "Tous" Or site = "" Then site = "*"
    m = "[" & vbCrLf
    m = m & "    CheminTransport = """ & EchapperM(CStr(ValeurParam("CheminTransport"))) & """," & vbCrLf
    m = m & "    CheminRejets = """ & EchapperM(CStr(ValeurParam("CheminRejets"))) & """," & vbCrLf
    m = m & "    Separateur = """ & sep & """," & vbCrLf
    If IsEmpty(mois) Then
        m = m & "    MoisRapport = null," & vbCrLf
    Else
        m = m & "    MoisRapport = #date(" & Year(mois) & ", " & Month(mois) & ", 1)," & vbCrLf
    End If
    m = m & "    SiteRejets = """ & EchapperM(site) & """" & vbCrLf & "]"
    M_Parametres = m
End Function

'--------------------------------------------------------------------------
' Mise en forme apres actualisation
'--------------------------------------------------------------------------
' Colonne A (masquee) des feuilles du rapport : 1 = ligne de donnees, 2 = ligne Total, 0 = ligne vide.
' - les lignes 0 sont masquees ;
' - chaque serie de graphique est redimensionnee au nombre de lignes "1" du tableau source.
Private Sub AjusterRapport()
    Dim ws As Worksheet, r As Long, derniere As Long, v As Variant
    Dim co As ChartObject, s As Object
    For Each ws In ThisWorkbook.Worksheets
        If IsNumeric(Left(ws.Name, 1)) Then
            derniere = ws.UsedRange.Row + ws.UsedRange.Rows.Count
            For r = 1 To derniere
                v = Indicateur(ws, r)
                If v >= 0 Then ws.Rows(r).Hidden = (v = 0)
            Next r
            For Each co In ws.ChartObjects
                For Each s In co.Chart.SeriesCollection
                    RedimensionnerSerie s
                Next s
            Next co
        End If
    Next ws
End Sub

Private Sub RedimensionnerSerie(ByVal s As Object)
    Dim f As String, p() As String, rx As Range, ry As Range, n As Long
    On Error GoTo Fin
    f = s.Formula                                  ' =SERIES(nom,categories,valeurs,ordre)
    f = Mid(f, InStr(f, "(") + 1)
    f = Left(f, Len(f) - 1)
    p = Split(f, ",")
    If UBound(p) < 2 Then Exit Sub
    If p(1) = "" Then Exit Sub
    Set rx = PlageDe(p(1))
    Set ry = PlageDe(p(2))
    n = 0
    Do While Indicateur(rx.Worksheet, rx.Row + n) = 1
        n = n + 1
        If n > 500 Then Exit Do
    Loop
    If n = 0 Then Exit Sub                         ' serie hors tableau par zone : inchangee
    s.XValues = rx.Cells(1, 1).Resize(n, 1)
    s.Values = ry.Cells(1, 1).Resize(n, 1)
Fin:
End Sub

' Indicateur en colonne A : 0, 1, 2, ou -1 si la cellule ne contient pas d'indicateur.
Private Function Indicateur(ByVal ws As Worksheet, ByVal r As Long) As Long
    Dim v As Variant
    v = ws.Cells(r, 1).Value
    Indicateur = -1
    If IsError(v) Or IsEmpty(v) Then Exit Function
    If VarType(v) = vbDouble Then Indicateur = CLng(v)
End Function

Private Function PlageDe(ByVal ref As String) As Range
    Dim i As Long, feuille As String
    i = InStrRev(ref, "!")
    feuille = Left(ref, i - 1)
    If Left(feuille, 1) = "'" Then feuille = Mid(feuille, 2, Len(feuille) - 2)
    feuille = Replace(feuille, "''", "'")
    Set PlageDe = ThisWorkbook.Worksheets(feuille).Range(Mid(ref, i + 1))
End Function

'--------------------------------------------------------------------------
' Outils
'--------------------------------------------------------------------------
Private Property Get ValeurParam(ByVal nom As String) As Variant
    ValeurParam = ThisWorkbook.Names(nom).RefersToRange.Value
End Property

Private Property Let ValeurParam(ByVal nom As String, ByVal valeur As Variant)
    ThisWorkbook.Names(nom).RefersToRange.Value = valeur
End Property

Private Function ValeurParam_Nb(ByVal feuille As String) As Long
    ValeurParam_Nb = Application.WorksheetFunction.CountA(ThisWorkbook.Worksheets(feuille).Columns(2)) - 1
End Function

Private Function EchapperM(ByVal s As String) As String
    EchapperM = Replace(s, """", """""")
End Function

'--------------------------------------------------------------------------
' Code M des requetes (genere - voir Requetes_PowerQuery.txt)
'--------------------------------------------------------------------------

Private Function M_Transport() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    P = Parametres," & vbCrLf
    m = m & "    Source = Csv.Document(File.Contents(P[CheminTransport]), [Delimiter = P[Separateur], Encoding = 65001, QuoteStyle = QuoteStyle.Csv])," & vbCrLf
    m = m & "    Entetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true])," & vbCrLf
    m = m & "    Colonnes = Table.SelectColumns(Entetes, {""region"", ""health_district"", ""health_facility"", ""site"", ""date"", ""vl_samples"", ""eid_samples"", ""tb_samples"", ""vl_results"", ""eid_results"", ""tb_results"", ""trips"", ""other_item_name"", ""other_item_qty"", ""duration_from_collection_days"", ""duration_in_hub1_days"", ""duration_in_hub2_days"", ""duration_reception_to_pickup_days"", ""action"", ""custom_month""}, MissingField.UseNull)," & vbCrLf
    m = m & "    Vides = Table.ReplaceValue(Colonnes, """", null, Replacer.ReplaceValue, Table.ColumnNames(Colonnes))," & vbCrLf
    m = m & "    Textes = Table.TransformColumns(Vides, {{""region"", Text.Trim, type text}, {""health_district"", Text.Trim, type text}, {""health_facility"", Text.Trim, type text}, {""site"", Text.Trim, type text}, {""action"", Text.Trim, type text}, {""custom_month"", Text.Trim, type text}, {""other_item_name"", Text.Trim, type text}})," & vbCrLf
    m = m & "    Nombres = Table.TransformColumnTypes(Textes, List.Transform({""vl_samples"", ""eid_samples"", ""tb_samples"", ""vl_results"", ""eid_results"", ""tb_results"", ""trips"", ""other_item_qty"", ""duration_from_collection_days"", ""duration_in_hub1_days"", ""duration_in_hub2_days"", ""duration_reception_to_pickup_days""}, each {_, type number}), ""en-US"")," & vbCrLf
    m = m & "    Dates = Table.TransformColumns(Nombres, {{""date"", each if _ = null then null else try Date.FromText(Text.Start(Text.From(_), 10), ""en-US"") otherwise null, type date}})," & vbCrLf
    m = m & "    AvecPeriode = Table.AddColumn(Dates, ""Periode"", each" & vbCrLf
    m = m & "        let" & vbCrLf
    m = m & "            cm = if [custom_month] = null then """" else [custom_month]," & vbCrLf
    m = m & "            fin = if Text.Length(cm) >= 10 then (try Date.FromText(Text.End(cm, 10), ""en-US"") otherwise null) else null," & vbCrLf
    m = m & "            ref = if fin <> null then fin else if [date] = null then null else if Date.Day([date]) > 25 then Date.AddMonths([date], 1) else [date]" & vbCrLf
    m = m & "        in" & vbCrLf
    m = m & "            if ref = null then null else Date.StartOfMonth(ref), type date)," & vbCrLf
    m = m & "    Final = Table.SelectColumns(AvecPeriode, {""Periode"", ""region"", ""health_district"", ""health_facility"", ""site"", ""date"", ""vl_samples"", ""eid_samples"", ""tb_samples"", ""vl_results"", ""eid_results"", ""tb_results"", ""trips"", ""other_item_name"", ""other_item_qty"", ""duration_from_collection_days"", ""duration_in_hub1_days"", ""duration_in_hub2_days"", ""duration_reception_to_pickup_days"", ""action"", ""custom_month""})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Transport = m
End Function

Private Function M_Rejets() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    P = Parametres," & vbCrLf
    m = m & "    Source = Csv.Document(File.Contents(P[CheminRejets]), [Delimiter = P[Separateur], Encoding = 65001, QuoteStyle = QuoteStyle.Csv])," & vbCrLf
    m = m & "    Entetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true])," & vbCrLf
    m = m & "    Colonnes = Table.SelectColumns(Entetes, {""region"", ""health_district"", ""health_facility"", ""site"", ""date"", ""vl_rejected"", ""eid_rejected"", ""tb_rejected"", ""total_rejected"", ""reason_haemolysed"", ""reason_insufficient_volume"", ""reason_poorly_conserved"", ""reason_clotted"", ""reason_illegible_label"", ""reason_empty_spilled"", ""reason_no_label"", ""reason_prolonged_storage"", ""reason_no_request_form"", ""reason_analytical_error"", ""reason_poor_packaging"", ""reason_unmatched_info"", ""reason_wrong_code"", ""reason_wrong_form"", ""reason_other_reason"", ""transporter"", ""custom_month""}, MissingField.UseNull)," & vbCrLf
    m = m & "    Vides = Table.ReplaceValue(Colonnes, """", null, Replacer.ReplaceValue, Table.ColumnNames(Colonnes))," & vbCrLf
    m = m & "    Textes = Table.TransformColumns(Vides, {{""region"", Text.Trim, type text}, {""health_district"", Text.Trim, type text}, {""health_facility"", Text.Trim, type text}, {""site"", Text.Trim, type text}, {""transporter"", Text.Trim, type text}, {""custom_month"", Text.Trim, type text}})," & vbCrLf
    m = m & "    Nombres = Table.TransformColumnTypes(Textes, List.Transform({""vl_rejected"", ""eid_rejected"", ""tb_rejected"", ""total_rejected"", ""reason_haemolysed"", ""reason_insufficient_volume"", ""reason_poorly_conserved"", ""reason_clotted"", ""reason_illegible_label"", ""reason_empty_spilled"", ""reason_no_label"", ""reason_prolonged_storage"", ""reason_no_request_form"", ""reason_analytical_error"", ""reason_poor_packaging"", ""reason_unmatched_info"", ""reason_wrong_code"", ""reason_wrong_form"", ""reason_other_reason""}, each {_, type number}), ""en-US"")," & vbCrLf
    m = m & "    Dates = Table.TransformColumns(Nombres, {{""date"", each if _ = null then null else try Date.FromText(Text.Start(Text.From(_), 10), ""en-US"") otherwise null, type date}})," & vbCrLf
    m = m & "    AvecPeriode = Table.AddColumn(Dates, ""Periode"", each" & vbCrLf
    m = m & "        let" & vbCrLf
    m = m & "            cm = if [custom_month] = null then """" else [custom_month]," & vbCrLf
    m = m & "            fin = if Text.Length(cm) >= 10 then (try Date.FromText(Text.End(cm, 10), ""en-US"") otherwise null) else null," & vbCrLf
    m = m & "            ref = if fin <> null then fin else if [date] = null then null else if Date.Day([date]) > 25 then Date.AddMonths([date], 1) else [date]" & vbCrLf
    m = m & "        in" & vbCrLf
    m = m & "            if ref = null then null else Date.StartOfMonth(ref), type date)," & vbCrLf
    m = m & "    Final = Table.SelectColumns(AvecPeriode, {""Periode"", ""region"", ""health_district"", ""health_facility"", ""site"", ""date"", ""vl_rejected"", ""eid_rejected"", ""tb_rejected"", ""total_rejected"", ""reason_haemolysed"", ""reason_insufficient_volume"", ""reason_poorly_conserved"", ""reason_clotted"", ""reason_illegible_label"", ""reason_empty_spilled"", ""reason_no_label"", ""reason_prolonged_storage"", ""reason_no_request_form"", ""reason_analytical_error"", ""reason_poor_packaging"", ""reason_unmatched_info"", ""reason_wrong_code"", ""reason_wrong_form"", ""reason_other_reason"", ""transporter"", ""custom_month""})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Rejets = m
End Function

Private Function M_Q_Regions() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    Col = Table.SelectColumns(Transport, {""region""})," & vbCrLf
    m = m & "    NonVides = Table.SelectRows(Col, each [region] <> null and [region] <> """")," & vbCrLf
    m = m & "    Uniques = Table.Distinct(NonVides, {""region"", Comparer.OrdinalIgnoreCase})," & vbCrLf
    m = m & "    Tri = Table.Sort(Uniques, {{""region"", Order.Ascending}})," & vbCrLf
    m = m & "    Final = Table.RenameColumns(Tri, {{""region"", ""Zone""}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Q_Regions = m
End Function

Private Function M_Q_Districts() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    Col = Table.SelectColumns(Transport, {""health_district""})," & vbCrLf
    m = m & "    NonVides = Table.SelectRows(Col, each [health_district] <> null and [health_district] <> """")," & vbCrLf
    m = m & "    Uniques = Table.Distinct(NonVides, {""health_district"", Comparer.OrdinalIgnoreCase})," & vbCrLf
    m = m & "    Tri = Table.Sort(Uniques, {{""health_district"", Order.Ascending}})," & vbCrLf
    m = m & "    Final = Table.RenameColumns(Tri, {{""health_district"", ""Zone""}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Q_Districts = m
End Function

Private Function M_Q_Couverture() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    F = Table.SelectRows(Transport, each [Periode] <> null and [health_facility] <> null)," & vbCrLf
    m = m & "    G = Table.Group(F, {""Periode"", ""region"", ""health_district"", ""site""}, {{""nb_fosa"", each List.Count(List.Distinct([health_facility], Comparer.OrdinalIgnoreCase)), Int64.Type}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    G" & vbCrLf
    M_Q_Couverture = m
End Function

Private Function M_Q_FOSA_Total() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    F = Table.SelectRows(Transport, each [health_facility] <> null)," & vbCrLf
    m = m & "    G = Table.Group(F, {""region"", ""health_district"", ""site""}, {{""nb_fosa"", each List.Count(List.Distinct([health_facility], Comparer.OrdinalIgnoreCase)), Int64.Type}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    G" & vbCrLf
    M_Q_FOSA_Total = m
End Function

Private Function M_Rejets_FOSA() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    P = Parametres," & vbCrLf
    m = m & "    Raisons = {{""reason_haemolysed"", ""Haemolysed samples""}, {""reason_insufficient_volume"", ""Insufficient sample volume""}, {""reason_poorly_conserved"", ""Poorly conserved samples""}, {""reason_clotted"", ""Clotted samples""}, {""reason_illegible_label"", ""Illegible label""}, {""reason_empty_spilled"", ""Empty sample tubes/spilled sample""}, {""reason_no_label"", ""Sample lacking an identification (MPI) code / no label""}, {""reason_prolonged_storage"", ""Prolonged storage""}, {""reason_no_request_form"", ""No request form""}, {""reason_analytical_error"", ""Analytical / Manipulation error""}, {""reason_poor_packaging"", ""Poor packaging""}, {""reason_unmatched_info"", ""Unmatched information""}, {""reason_wrong_code"", ""Wrong code""}, {""reason_wrong_form"", ""Wrong form""}, {""reason_other_reason"", ""Other reason""}}," & vbCrLf
    m = m & "    F = Table.SelectRows(Rejets, each [Periode] = P[MoisRapport] and (P[SiteRejets] = ""*"" or Text.Upper(if [site] = null then """" else [site]) = Text.Upper(P[SiteRejets])))," & vbCrLf
    m = m & "    G = Table.Group(F, {""region"", ""health_district"", ""health_facility""}, {" & vbCrLf
    m = m & "        {""VL samples"", each List.Sum([vl_rejected]), type nullable number}," & vbCrLf
    m = m & "        {""EID samples"", each List.Sum([eid_rejected]), type nullable number}," & vbCrLf
    m = m & "        {""TB samples"", each List.Sum([tb_rejected]), type nullable number}," & vbCrLf
    m = m & "        {""Total"", each List.Sum([total_rejected]), type nullable number}," & vbCrLf
    m = m & "        {""Reasons for rejection"", (t) => Text.Combine(List.RemoveNulls(List.Transform(Raisons, (r) => let n = List.Sum(Table.Column(t, r{0})) in if n = null or n = 0 then null else r{1} & "" ("" & Text.From(n) & "")"")), ""; ""), type text}})," & vbCrLf
    m = m & "    Tri = Table.Sort(G, {{""region"", Order.Ascending}, {""Total"", Order.Descending}})," & vbCrLf
    m = m & "    Final = Table.RenameColumns(Tri, {{""region"", ""Region""}, {""health_district"", ""District""}, {""health_facility"", ""Health facility""}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Rejets_FOSA = m
End Function

Private Function M_Intrants_FOSA() As String
    Dim m As String
    m = m & "let" & vbCrLf
    m = m & "    P = Parametres," & vbCrLf
    m = m & "    F = Table.SelectRows(Transport, each [Periode] = P[MoisRapport] and [other_item_name] <> null and [other_item_qty] <> null and [other_item_qty] <> 0)," & vbCrLf
    m = m & "    G = Table.Group(F, {""region"", ""health_district"", ""health_facility"", ""other_item_name""}, {{""qty"", each List.Sum([other_item_qty]), type number}})," & vbCrLf
    m = m & "    Articles = List.Sort(List.Distinct(G[other_item_name]))," & vbCrLf
    m = m & "    Pivot = Table.Pivot(G, Articles, ""other_item_name"", ""qty"", List.Sum)," & vbCrLf
    m = m & "    AvecTotal = Table.AddColumn(Pivot, ""Total"", each List.Sum(List.RemoveNulls(Record.ToList(Record.SelectFields(_, Articles)))), type number)," & vbCrLf
    m = m & "    Tri = Table.Sort(AvecTotal, {{""region"", Order.Ascending}, {""health_district"", Order.Ascending}, {""health_facility"", Order.Ascending}})," & vbCrLf
    m = m & "    Final = Table.RenameColumns(Tri, {{""region"", ""Region""}, {""health_district"", ""District""}, {""health_facility"", ""Health facility""}})" & vbCrLf
    m = m & "in" & vbCrLf
    m = m & "    Final" & vbCrLf
    M_Intrants_FOSA = m
End Function
