import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import SearchPage from "../page"
import { searchProperties, exportPropertiesBySearch } from "@/lib/api"

// Mock the API module
jest.mock("@/lib/api", () => ({
  searchProperties: jest.fn(),
  exportPropertiesBySearch: jest.fn(),
}))

const mockSearchProperties = searchProperties as jest.Mock
const mockExport = exportPropertiesBySearch as jest.Mock

describe("SearchPage", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(global as any).URL = {
      createObjectURL: jest.fn(() => "blob:test"),
      revokeObjectURL: jest.fn(),
    }
    const anchor = document.createElement("a")
    anchor.click = jest.fn()
    document.body.appendChild(anchor)
  })

  it("renders search interface", () => {
    render(<SearchPage />)
    expect(screen.getByText("Find Your Property")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
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
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
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

  it("displays no results message", async () => {
    mockSearchProperties.mockResolvedValueOnce({
      results: [],
      count: 0
    })

    render(<SearchPage />)
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
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
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
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
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
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
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
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
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...");
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
    fireEvent.change(screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')..."), { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /export/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to export");
    });
  })
})
