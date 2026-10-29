# ISTS Monthly Report: two ready-to-use versions

| File | Contents | Use it when |
|---|---|---|
| `ISTS_REPORT_Macro.zip` | `ISTS_Report_Macro.xlsm`, with the macro and the Power Query queries already embedded. An **Import CSV files** button lets you pick the files. | Macros are allowed on the computer. |
| `ISTS_REPORT_PowerQuery.zip` | `ISTS_Report_PowerQuery.xlsx`, with no macro. It reads the CSV files from a fixed folder and refreshes when opened. | Macros are blocked. |

Each zip contains a `README.txt` with step-by-step instructions, plus two fictitious CSV files (`SAMPLE_DATA`) for a test run.

## Power Query version: folder organisation

Extract `ISTS_REPORT_PowerQuery.zip` directly to `C:\`. You get:

```
C:\ISTS_REPORT\
    ISTS_Report_PowerQuery.xlsx      <- the report
    CSV\TRANSPORT\                   <- put the monthly transport CSV here
    CSV\REJECTIONS\                  <- put the monthly rejections CSV here
    SAMPLE_DATA\                     <- test CSV files
```

In each folder, the most recent CSV file is used.

Every month, drop the two CSV files into their folders and open the report. It refreshes automatically when it opens, or you can use **Data > Refresh All**.

To use another location, go to **Data > Queries & Connections**, right-click **Parameters** and choose **Edit**, then change the `Folder` line.

## Macro version

1. Extract the zip anywhere.
2. Right-click the `.xlsm` > **Properties** > tick **Unblock**.
3. Open the file and click **Enable Content**.
4. Click **Import CSV files and build the report**.
5. Select the transport CSV, then the rejections CSV.

If the macro does not load, use the `BACKUP\` folder. It contains the same workbook without code and the `ImportModule.bas` file, which you import with Alt+F11.

## What the workbooks contain

- **16 embedded Power Query queries.** They import the CSV files, set the column types and work out the month from `custom_month`. They also build the region and district lists, health facility coverage, Tables 11 and 13 (rejections and supplies by health facility) and the chart data by zone. The code is in `PowerQuery_Queries.txt`.
- **Sheets 1_ to 14_** hold Tables 1 to 16 and Figures 1 to 10.
- **Charts by zone** read the Power Query tables, so they resize to the number of regions or districts automatically.
- **Analysis level** is set automatically: by Region if the CSV contains several regions, otherwise by District.
- **Reporting month** is the latest month in the CSV, compared with the previous month.
- **Table 16:** fill in the `Reference` sheet once with the number of PEPFAR-supported health facilities per zone.

Requirements: Excel 2016, 2019, 2021 or Microsoft 365 on Windows.
