import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"
import ChatPage from "../page"

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn()

describe("ChatPage", () => {
  beforeEach(() => {
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it("renders chat interface", () => {
    render(<ChatPage />)
    expect(screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument()
  })

  it("displays initial greeting", () => {
    render(<ChatPage />)
    expect(screen.getByText("Hello! I'm your AI Real Estate Assistant. How can I help you find your dream property today?")).toBeInTheDocument()
  })

  it("handles message submission", async () => {
    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Find me a house" } })
    fireEvent.click(sendButton)

    // User message should appear immediately
    expect(screen.getByText("Find me a house")).toBeInTheDocument()
    
    // Input should be cleared
    expect(input).toHaveValue("")

    act(() => {
      jest.runAllTimers()
    })

    // Wait for bot response
    await waitFor(() => {
      expect(screen.getByText("I'm connected to the frontend, but the backend integration is pending. I can help you once I'm fully wired up!")).toBeInTheDocument()
    })
  })

  it("handles loading state", async () => {
    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Hello" } })
    fireEvent.click(sendButton)

    expect(screen.getByLabelText("Loading")).toBeInTheDocument()
    expect(sendButton).toBeDisabled()
    
    act(() => {
      jest.runAllTimers()
    })
    
    await waitFor(() => {
      expect(screen.queryByLabelText("Loading")).not.toBeInTheDocument()
    })
  })
})
