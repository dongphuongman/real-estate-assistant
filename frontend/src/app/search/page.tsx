"use client";

import { useState } from "react";
import { Search as SearchIcon, MapPin, Filter } from "lucide-react";
import { searchProperties } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await searchProperties({ query });
      setResults(response.results);
      console.log("Search results:", response);
    } catch (err) {
      console.error("Search failed:", err);
      setError("Failed to perform search. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-8">
        {/* Search Header */}
        <div className="flex flex-col space-y-4">
          <h1 className="text-3xl font-bold tracking-tight">Find Your Property</h1>
          <p className="text-muted-foreground">
            Search across thousands of listings using AI-powered semantic search.
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')..."
              className="w-full rounded-md border border-input bg-background pl-10 pr-4 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
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
                 {/* TODO: Add Price Range, Room Count, Property Type filters */}
                 <div className="text-sm text-muted-foreground">Filters coming soon...</div>
              </div>
            </div>
          </div>

          {/* Results Grid */}
          <div className="md:col-span-3">
            {results.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center border rounded-lg border-dashed">
                <div className="p-4 rounded-full bg-muted/50 mb-4">
                  <MapPin className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold">{error ? "Error" : "No results found"}</h3>
                <p className="text-sm text-muted-foreground max-w-sm mt-2">
                  {error || "Try adjusting your search terms or filters to find what you're looking for."}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {results.map((item) => {
                  const prop = item.property;
                  return (
                    <div key={prop.id || Math.random().toString()} className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
                      <div className="aspect-video w-full bg-muted relative">
                        {/* Placeholder for image */}
                        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                          Image
                        </div>
                      </div>
                      <div className="p-6 space-y-2">
                        <h3 className="text-2xl font-semibold leading-none tracking-tight">{prop.title || "Untitled Property"}</h3>
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
