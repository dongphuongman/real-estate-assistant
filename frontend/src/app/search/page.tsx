"use client";

import { useState } from "react";
import { Search as SearchIcon, MapPin, Filter, Download } from "lucide-react";
import { searchProperties, exportPropertiesBySearch } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [minPrice, setMinPrice] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [rooms, setRooms] = useState<string>("");
  const [propertyType, setPropertyType] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("relevance");
  const [sortOrder, setSortOrder] = useState<string>("desc");
  const [exportFormat, setExportFormat] = useState<string>("csv");
  const [exportColumns, setExportColumns] = useState<string>("");
  const [exportIncludeHeader, setExportIncludeHeader] = useState<boolean>(true);
  const [csvDelimiter, setCsvDelimiter] = useState<string>(",");
  const [csvDecimal, setCsvDecimal] = useState<string>(".");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const buildFilters = (): { filters?: Record<string, unknown>; error?: string } => {
    const min = minPrice.trim() ? Number(minPrice) : undefined;
    const max = maxPrice.trim() ? Number(maxPrice) : undefined;
    const minRooms = rooms.trim() ? Number(rooms) : undefined;

    if (min !== undefined && Number.isNaN(min)) return { error: "Min price must be a valid number." };
    if (max !== undefined && Number.isNaN(max)) return { error: "Max price must be a valid number." };
    if (minRooms !== undefined && Number.isNaN(minRooms)) {
      return { error: "Minimum rooms must be a valid number." };
    }
    if (min !== undefined && max !== undefined && min > max) {
      return { error: "Min price cannot be greater than max price." };
    }

    const filters: Record<string, unknown> = {};
    if (min !== undefined) filters["min_price"] = min;
    if (max !== undefined) filters["max_price"] = max;
    if (minRooms !== undefined) filters["rooms"] = minRooms;
    if (propertyType.trim()) filters["property_type"] = propertyType;

    return { filters: Object.keys(filters).length ? filters : undefined };
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      if (!query.trim()) {
        setResults([]);
        setError("Please enter a search query.");
        return;
      }

      const { filters, error: filterError } = buildFilters();
      if (filterError) {
        setResults([]);
        setError(filterError);
        return;
      }

      const response = await searchProperties({
        query,
        sort_by: sortBy as "relevance" | "price" | "price_per_sqm" | "area_sqm" | "year_built",
        sort_order: sortOrder as "asc" | "desc",
        filters,
      });
      setResults(response.results);
    } catch {
      setResults([]);
      setError("Failed to perform search. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      if (!query.trim()) {
        setExportError("Please enter a search query.");
        return;
      }

      const { filters, error: filterError } = buildFilters();
      if (filterError) {
        setExportError(filterError);
        return;
      }

      const searchPayload = {
        query,
        limit: Math.max(results.length, 10) || 10,
        sort_by: sortBy as "relevance" | "price" | "price_per_sqm" | "area_sqm" | "year_built",
        sort_order: sortOrder as "asc" | "desc",
        filters,
      };
      const columns = exportColumns
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      const { filename, blob } = await exportPropertiesBySearch(
        searchPayload,
        exportFormat as "csv" | "xlsx" | "json" | "md" | "pdf",
        {
          columns: columns.length ? columns : undefined,
          include_header: exportIncludeHeader,
          csv_delimiter: exportFormat === "csv" ? csvDelimiter : undefined,
          csv_decimal: exportFormat === "csv" ? csvDecimal : undefined,
        }
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setExportError("Failed to export. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8" aria-live="polite">
      <div className="flex flex-col space-y-8">
        {/* Search Header */}
        <div className="flex flex-col space-y-4">
          <h1 className="text-3xl font-bold tracking-tight">Find Your Property</h1>
          <p className="text-muted-foreground">
            Search across thousands of listings using AI-powered semantic search.
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex gap-4" role="search" aria-label="Property search">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Describe what you're looking for (e.g., 2-bed apartment under $500k)..."
              className={[
                "w-full rounded-md border border-input bg-background",
                "pl-10 pr-4 py-2 text-sm ring-offset-background",
                "placeholder:text-muted-foreground focus-visible:outline-none",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                "disabled:cursor-not-allowed disabled:opacity-50",
              ].join(" ")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search query"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className={[
              "inline-flex items-center justify-center rounded-md bg-primary px-8",
              "text-sm font-medium text-primary-foreground shadow transition-colors",
              "hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              "disabled:pointer-events-none disabled:opacity-50",
            ].join(" ")}
            aria-busy={loading ? "true" : "false"}
            aria-label={loading ? "Searching" : "Search"}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Filters & Results Layout */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Sidebar Filters */}
          <div className="space-y-6">
            <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
              <div className="flex items-center gap-2 font-semibold mb-4">
                <Filter className="h-4 w-4" /> Filters
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="sort-by" className="block text-sm font-medium mb-1">
                        Sort By
                      </label>
                      <select
                        id="sort-by"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        aria-label="Sort by"
                      >
                        <option value="relevance">Relevance</option>
                        <option value="price">Price</option>
                        <option value="price_per_sqm">Price per m²</option>
                        <option value="area_sqm">Area (m²)</option>
                        <option value="year_built">Year Built</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="sort-order" className="block text-sm font-medium mb-1">
                        Order
                      </label>
                      <select
                        id="sort-order"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value)}
                        aria-label="Sort order"
                      >
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="min-price" className="block text-sm font-medium mb-1">
                      Min Price
                    </label>
                    <input
                      id="min-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={minPrice}
                      onChange={(e) => setMinPrice(e.target.value)}
                      aria-label="Minimum price"
                    />
                  </div>
                  <div>
                    <label htmlFor="max-price" className="block text-sm font-medium mb-1">
                      Max Price
                    </label>
                    <input
                      id="max-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(e.target.value)}
                      aria-label="Maximum price"
                    />
                  </div>
                  <div>
                    <label htmlFor="rooms" className="block text-sm font-medium mb-1">
                      Minimum Rooms
                    </label>
                    <input
                      id="rooms"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={rooms}
                      onChange={(e) => setRooms(e.target.value)}
                      aria-label="Minimum rooms"
                    />
                  </div>
                  <div>
                    <label htmlFor="property-type" className="block text-sm font-medium mb-1">
                      Property Type
                    </label>
                    <select
                      id="property-type"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={propertyType}
                      onChange={(e) => setPropertyType(e.target.value)}
                      aria-label="Property type"
                    >
                      <option value="">Any</option>
                      <option value="apartment">Apartment</option>
                      <option value="house">House</option>
                      <option value="studio">Studio</option>
                      <option value="loft">Loft</option>
                      <option value="townhouse">Townhouse</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setMinPrice("");
                      setMaxPrice("");
                      setRooms("");
                      setPropertyType("");
                      setSortBy("relevance");
                      setSortOrder("desc");
                    }}
                    className={[
                      "inline-flex items-center justify-center rounded-md border",
                      "px-3 py-2 text-sm hover:bg-muted",
                    ].join(" ")}
                    aria-label="Clear filters"
                  >
                    Clear Filters
                  </button>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div>
                      <label htmlFor="export-format" className="block text-sm font-medium mb-1">
                        Export Format
                      </label>
                      <select
                        id="export-format"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportFormat}
                        onChange={(e) => setExportFormat(e.target.value)}
                        aria-label="Export format"
                      >
                        <option value="csv">CSV</option>
                        <option value="xlsx">Excel</option>
                        <option value="json">JSON</option>
                        <option value="md">Markdown</option>
                        <option value="pdf">PDF</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="export-columns" className="block text-sm font-medium mb-1">
                        Columns (optional)
                      </label>
                      <input
                        id="export-columns"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportColumns}
                        onChange={(e) => setExportColumns(e.target.value)}
                        placeholder="e.g., id, city, price"
                        aria-label="Export columns"
                      />
                    </div>
                    {exportFormat === "csv" ? (
                      <div className="grid grid-cols-2 gap-4 col-span-2">
                        <div>
                          <label htmlFor="csv-delimiter" className="block text-sm font-medium mb-1">
                            CSV Delimiter
                          </label>
                          <select
                            id="csv-delimiter"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDelimiter}
                            onChange={(e) => setCsvDelimiter(e.target.value)}
                            aria-label="CSV delimiter"
                          >
                            <option value=",">Comma (,)</option>
                            <option value=";">Semicolon (;)</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="csv-decimal" className="block text-sm font-medium mb-1">
                            Decimal Separator
                          </label>
                          <select
                            id="csv-decimal"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDecimal}
                            onChange={(e) => setCsvDecimal(e.target.value)}
                            aria-label="CSV decimal separator"
                          >
                            <option value=".">Dot (.)</option>
                            <option value=",">Comma (,)</option>
                          </select>
                        </div>
                        <label className="flex items-center gap-2 text-sm col-span-2">
                          <input
                            type="checkbox"
                            checked={exportIncludeHeader}
                            onChange={(e) => setExportIncludeHeader(e.target.checked)}
                            aria-label="Include CSV header"
                          />
                          Include header row
                        </label>
                      </div>
                    ) : null}
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={handleExport}
                        disabled={exporting || !query.trim()}
                        className={[
                          "inline-flex items-center justify-center rounded-md bg-primary px-3 py-2",
                          "text-sm font-medium text-primary-foreground shadow transition-colors",
                          "hover:bg-primary/90 disabled:opacity-50",
                        ].join(" ")}
                        aria-label={exporting ? "Exporting" : "Export"}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        {exporting ? "Exporting..." : "Export"}
                      </button>
                    </div>
                  </div>
                  {exportError ? (
                    <div className="text-red-500 text-sm" role="alert">{exportError}</div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          {/* Results Grid */}
          <div className="md:col-span-3">
            {results.length === 0 ? (
              <div
                className="flex flex-col items-center justify-center h-64 text-center border rounded-lg border-dashed"
                role="status"
                aria-live="polite"
              >
                <div className="p-4 rounded-full bg-muted/50 mb-4">
                  <MapPin className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-semibold">
                  {loading
                    ? "Searching..."
                    : error
                      ? "Error"
                      : hasSearched
                        ? "No results found"
                        : "Start searching"}
                </h3>
                <p className="text-sm text-muted-foreground max-w-sm mt-2">
                  {error ||
                    (loading
                      ? "Searching for matching properties."
                      : hasSearched
                        ? "Try adjusting your search terms or filters to find what you're looking for."
                        : "Enter a query, adjust filters if needed, and run a search to see results here.")}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {results.map((item, index) => {
                  const prop = item.property;
                  return (
                    <div
                      key={`${prop.id ?? "unknown"}-${index}`}
                      className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden"
                    >
                      <div className="aspect-video w-full bg-muted relative">
                        {/* Placeholder for image */}
                        <div
                          className="absolute inset-0 flex items-center justify-center text-muted-foreground"
                          aria-label="Property image placeholder"
                        >
                          Property image
                        </div>
                      </div>
                      <div className="p-6 space-y-2">
                        <h3 className="text-2xl font-semibold leading-none tracking-tight">
                          {prop.title || "Untitled Property"}
                        </h3>
                        <p className="text-sm text-muted-foreground">{prop.city}, {prop.country}</p>
                        <div className="font-bold text-lg">
                          {prop.price ? `$${prop.price.toLocaleString()}` : "Price on request"}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {[
                            prop.rooms ? `${prop.rooms} beds` : null,
                            prop.bathrooms ? `${prop.bathrooms} baths` : null,
                            prop.area_sqm ? `${prop.area_sqm} m²` : null
                          ].filter(Boolean).join(" • ")}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
