import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import SearchPage from "../page"
import { searchProperties, exportPropertiesBySearch } from "@/lib/api"

jest.mock("@/lib/api", () => ({
  searchProperties: jest.fn(),
  exportPropertiesBySearch: jest.fn(),
}))

const mockSearchProperties = searchProperties as jest.Mock
const mockExport = exportPropertiesBySearch as jest.Mock

describe("SearchPage", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      value: jest.fn(() => "blob:test"),
      configurable: true,
    })
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      value: jest.fn(),
      configurable: true,
    })
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it("renders search interface", () => {
    render(<SearchPage />)
    expect(screen.getByText("Find Your Property")).toBeInTheDocument()
    expect(screen.getByLabelText("Search query")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows neutral state before the first search", () => {
    render(<SearchPage />)
    expect(screen.getByText("Start searching")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Enter a query, adjust filters if needed, and run a search to see results here."
      )
    ).toBeInTheDocument()
  })

  it("handles search submission", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [
        {
          property: {
            id: "1",
            title: "Modern Apartment",
            price: 500000,
            city: "Downtown",
            country: "US",
            rooms: 2,
            bathrooms: 2,
          },
          score: 0.9
        }
      ],
      count: 1
    })

    render(<SearchPage />)
    
    const input = screen.getByLabelText("Search query")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Downtown" } })
    fireEvent.click(searchButton)

    expect(searchButton).toBeDisabled()

    await waitFor(() => {
      expect(screen.getByText("Modern Apartment")).toBeInTheDocument()
      expect(screen.getByText("$500,000")).toBeInTheDocument()
      expect(screen.getByText("Downtown, US")).toBeInTheDocument()
    })
  })

  it("sends filters and sorting in the search payload", async () => {
    mockSearchProperties.mockResolvedValueOnce({ results: [], count: 0 })

    render(<SearchPage />)

    fireEvent.change(
      screen.getByLabelText("Search query"),
      { target: { value: "Test" } }
    )
    fireEvent.change(screen.getByLabelText("Min Price"), { target: { value: "100" } })
    fireEvent.change(screen.getByLabelText("Max Price"), { target: { value: "200" } })
    fireEvent.change(screen.getByLabelText("Minimum Rooms"), { target: { value: "2" } })
    fireEvent.change(screen.getByLabelText("Property Type"), { target: { value: "apartment" } })
    fireEvent.change(screen.getByLabelText("Sort By"), { target: { value: "price" } })
    fireEvent.change(screen.getByLabelText("Order"), { target: { value: "asc" } })

    fireEvent.click(screen.getByRole("button", { name: /search/i }))

    await waitFor(() => {
      expect(mockSearchProperties).toHaveBeenCalledWith({
        query: "Test",
        sort_by: "price",
        sort_order: "asc",
        filters: {
          min_price: 100,
          max_price: 200,
          rooms: 2,
          property_type: "apartment",
        },
      })
    })
  })

  it("validates min and max price before searching", async () => {
    render(<SearchPage />)

    fireEvent.change(
      screen.getByLabelText("Search query"),
      { target: { value: "Test" } }
    )
    fireEvent.change(screen.getByLabelText("Min Price"), { target: { value: "300" } })
    fireEvent.change(screen.getByLabelText("Max Price"), { target: { value: "200" } })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument()
      expect(screen.getByText("Min price cannot be greater than max price.")).toBeInTheDocument()
    })
    expect(mockSearchProperties).not.toHaveBeenCalled()
  })

  it("shows query validation when submitting with an empty query", async () => {
    render(<SearchPage />)

    fireEvent.submit(screen.getByRole("search"))

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument()
      expect(screen.getByText("Please enter a search query.")).toBeInTheDocument()
    })
    expect(mockSearchProperties).not.toHaveBeenCalled()
  })

  it("displays no results message", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [],
      count: 0
    })

    render(<SearchPage />)
    
    const input = screen.getByLabelText("Search query")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Nowhere" } })
    fireEvent.click(searchButton)

    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeInTheDocument()
    })
  })

  it("displays error message on failure", async () => {
    mockSearchProperties.mockRejectedValueOnce(new Error("API Error"))

    render(<SearchPage />)
    
    const input = screen.getByLabelText("Search query")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Error" } })
    fireEvent.click(searchButton)

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument()
      expect(screen.getByText("Failed to perform search. Please try again.")).toBeInTheDocument()
    })
  })

  it("handles missing property details", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [
        {
          property: {
            id: "2",
            city: "Unknown",
            // Missing title, price, rooms, bathrooms, area_sqm
          },
          score: 0.8
        }
      ],
      count: 1
    })

    render(<SearchPage />)
    
    const input = screen.getByLabelText("Search query")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Cheap" } })
    fireEvent.click(searchButton)

    await waitFor(() => {
      expect(screen.getByText("Untitled Property")).toBeInTheDocument()
      expect(screen.getByText("Price on request")).toBeInTheDocument()
    })
  })

  it("handles missing id and renders area", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [
        {
          property: {
            city: "Anywhere",
            country: "US",
            area_sqm: 55,
          },
          score: 0.8
        }
      ],
      count: 1
    })

    render(<SearchPage />)
    
    const input = screen.getByLabelText("Search query")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Area" } })
    fireEvent.click(searchButton)

    await waitFor(() => {
      expect(screen.getByText("55 m²")).toBeInTheDocument()
    })
  })

  it("exports results using selected format", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [
        { property: { id: "1", title: "A", city: "X", country: "US", price: 10 }, score: 0.9 },
      ],
      count: 1,
    });
    const blob = new Blob(["a"], { type: "text/csv" });
    mockExport.mockResolvedValueOnce({ filename: "properties_test.csv", blob });

    render(<SearchPage />);
    const input = screen.getByLabelText("Search query");
    fireEvent.change(input, { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => {
      expect(screen.getByText("A")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Export format"), { target: { value: "csv" } });
    const exportBtn = screen.getByRole("button", { name: /export/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(mockExport).toHaveBeenCalled();
    });
  })

  it("shows export error on failure", async () => {
    mockExport.mockRejectedValueOnce(new Error("Export failed"));
    render(<SearchPage />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /export/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to export");
    });
  })
})
