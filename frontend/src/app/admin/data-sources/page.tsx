"use client";

import { useState } from "react";
import {
  FileUp,
  Loader2,
  Upload,
  AlertCircle,
  FileSpreadsheet,
  CheckCircle2,
  Table,
  Database,
} from "lucide-react";
import { ingestData, getExcelSheets, ApiError } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

interface ErrorState {
  message: string;
  requestId?: string;
}

interface SheetInfo {
  name: string;
  rowCount: number;
}

export default function DataSourcesPage() {
  const [fileUrl, setFileUrl] = useState<string>("");
  const [sourceName, setSourceName] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  // Excel sheets state
  const [loadingSheets, setLoadingSheets] = useState(false);
  const [sheets, setSheets] = useState<SheetInfo[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [headerRow, setHeaderRow] = useState<number>(0);

  const isExcelFile = (url: string): boolean => {
    const lowerUrl = url.toLowerCase();
    return lowerUrl.endsWith(".xlsx") || lowerUrl.endsWith(".xls") || lowerUrl.endsWith(".ods");
  };

  const extractErrorState = (err: unknown): ErrorState => {
    let message = "Unknown error";
    let requestId: string | undefined = undefined;

    if (err instanceof ApiError) {
      message = err.message;
      requestId = err.request_id;
    } else if (err instanceof Error) {
      message = err.message;
    } else {
      message = String(err);
    }

    return { message, requestId };
  };

  const onLoadSheets = async () => {
    const url = fileUrl.trim();
    if (!url) {
      setError({ message: "Please enter a file URL first." });
      return;
    }

    if (!isExcelFile(url)) {
      setError({ message: "URL must point to an Excel file (.xlsx, .xls, or .ods)." });
      return;
    }

    setLoadingSheets(true);
    setError(null);
    setSheets([]);

    try {
      const res = await getExcelSheets({ file_url: url });
      const sheetInfo: SheetInfo[] = res.sheet_names.map((name) => ({
        name,
        rowCount: res.row_count[name] || 0,
      }));
      setSheets(sheetInfo);
      if (res.default_sheet) {
        setSelectedSheet(res.default_sheet);
      }
    } catch (e: unknown) {
      setError(extractErrorState(e));
    } finally {
      setLoadingSheets(false);
    }
  };

  const onIngest = async () => {
    const url = fileUrl.trim();
    if (!url) {
      setError({ message: "Please enter a file URL." });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request = {
        file_urls: [url],
        sheet_name: isExcelFile(url) ? selectedSheet || undefined : undefined,
        header_row: headerRow,
        source_name: sourceName.trim() || undefined,
      };
      const res = await ingestData(request);
      setResult(res);
    } catch (e: unknown) {
      setError(extractErrorState(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <div className="flex flex-col space-y-2 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
        <p className="text-muted-foreground">
          Import property data from CSV or Excel files. Supports sheet selection for Excel files.
        </p>
      </div>

      <div className="grid gap-8">
        {/* File URL Input Section */}
        <section className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Import from URL</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="fileUrl" className="block text-sm font-medium mb-2">
                File URL
              </label>
              <input
                id="fileUrl"
                className="border p-2 w-full rounded"
                type="text"
                placeholder="https://example.com/data.xlsx"
                value={fileUrl}
                onChange={(e) => setFileUrl(e.target.value)}
                disabled={loading}
                aria-label="File URL"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Supports CSV (.csv) and Excel (.xlsx, .xls, .ods) files
              </p>
            </div>

            <div>
              <label htmlFor="sourceName" className="block text-sm font-medium mb-2">
                Source Name (optional)
              </label>
              <input
                id="sourceName"
                className="border p-2 w-full rounded"
                type="text"
                placeholder="e.g., Q1 2024 Properties"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                disabled={loading}
                aria-label="Source Name"
              />
            </div>

            {/* Excel-specific options */}
            {isExcelFile(fileUrl) && (
              <div className="border-t pt-4 mt-4">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4" />
                  Excel Options
                </h3>

                <div className="grid gap-4">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="px-4 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 disabled:opacity-50"
                      onClick={onLoadSheets}
                      disabled={loadingSheets || loading}
                    >
                      {loadingSheets ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Loading sheets...
                        </>
                      ) : (
                        <>
                          <Table className="w-4 h-4 mr-2" />
                          Load Sheets
                        </>
                      )}
                    </button>
                  </div>

                  {sheets.length > 0 && (
                    <>
                      <div>
                        <label htmlFor="sheetSelect" className="block text-sm font-medium mb-2">
                          Select Sheet
                        </label>
                        <select
                          id="sheetSelect"
                          className="border p-2 w-full rounded"
                          value={selectedSheet}
                          onChange={(e) => setSelectedSheet(e.target.value)}
                          disabled={loading}
                        >
                          {sheets.map((sheet) => (
                            <option key={sheet.name} value={sheet.name}>
                              {sheet.name} ({sheet.rowCount} rows)
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label htmlFor="headerRow" className="block text-sm font-medium mb-2">
                          Header Row (0-indexed)
                        </label>
                        <input
                          id="headerRow"
                          className="border p-2 w-full rounded"
                          type="number"
                          min="0"
                          value={headerRow}
                          onChange={(e) => setHeaderRow(parseInt(e.target.value) || 0)}
                          disabled={loading}
                        />
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            <button
              type="button"
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
              onClick={onIngest}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Import Data
                </>
              )}
            </button>
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Error</p>
                <p className="text-sm">{error.message}</p>
                {error.requestId && (
                  <p className="text-xs mt-1">Request ID: {error.requestId}</p>
                )}
              </div>
            </div>
          )}

          {/* Success Display */}
          {result && (
            <div className="flex items-start gap-3 p-4 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100 rounded">
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Import Successful</p>
                <p className="text-sm">{result.message}</p>
                <p className="text-xs mt-1">
                  Properties processed: {result.properties_processed}
                </p>
                {result.source_type && (
                  <p className="text-xs">Source type: {result.source_type}</p>
                )}
                {result.source_name && (
                  <p className="text-xs">Source name: {result.source_name}</p>
                )}
                {result.errors.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer">
                      Warnings ({result.errors.length})
                    </summary>
                    <ul className="text-xs mt-1 list-disc list-inside">
                      {result.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Info Section */}
        <section className="border rounded-lg p-6 bg-muted/50">
          <div className="flex items-center gap-2 mb-4">
            <FileUp className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Supported File Formats</h2>
          </div>
          <div className="space-y-2 text-sm">
            <p>
              <strong>CSV:</strong> Comma-separated values file
            </p>
            <p>
              <strong>Excel (.xlsx):</strong> Modern Excel format with openpyxl
            </p>
            <p>
              <strong>Excel (.xls):</strong> Legacy Excel format with xlrd
            </p>
            <p>
              <strong>ODF Spreadsheet (.ods):</strong> OpenDocument format with odfpy
            </p>
          </div>
          <div className="mt-4 pt-4 border-t">
            <h3 className="font-semibold mb-2">Tips for Excel files:</h3>
            <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
              <li>Click &quot;Load Sheets&quot; to see available sheets and row counts</li>
              <li>Select the sheet containing property data</li>
              <li>Specify the header row (default is 0 for the first row)</li>
              <li>Ensure your data has a &quot;city&quot; column for proper validation</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
