import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"
import SearchPage from "../page"

describe("SearchPage", () => {
  beforeEach(() => {
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it("renders search interface", () => {
    render(<SearchPage />)
    expect(screen.getByText("Find Your Property")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("handles search submission", async () => {
    render(<SearchPage />)
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Downtown" } })
    fireEvent.click(searchButton)

    expect(searchButton).toBeDisabled()

    act(() => {
      jest.runAllTimers()
    })

    await waitFor(() => {
      expect(screen.getByText("Modern Apartment")).toBeInTheDocument()
      expect(screen.getByText("$500,000")).toBeInTheDocument()
      expect(screen.getByText("Downtown")).toBeInTheDocument()
    })
  })

  it("displays no results message", async () => {
    render(<SearchPage />)
    
    const input = screen.getByPlaceholderText("Describe what you are looking for (e.g., 'Modern apartment in downtown with 2 bedrooms under $500k')...")
    const searchButton = screen.getByRole("button", { name: /search/i })

    fireEvent.change(input, { target: { value: "Nowhere" } })
    fireEvent.click(searchButton)

    act(() => {
      jest.runAllTimers()
    })

    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeInTheDocument()
    })
  })
})
