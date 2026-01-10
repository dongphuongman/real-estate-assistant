import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import ChatPage from "../page"
import { chatMessage } from "@/lib/api"

// Mock the API module
jest.mock("@/lib/api", () => ({
  chatMessage: jest.fn(),
}))

const mockChatMessage = chatMessage as jest.Mock

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn()

describe("ChatPage", () => {
  beforeEach(() => {
    jest.clearAllMocks()
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
    mockChatMessage.mockResolvedValueOnce({
      response: "This is a real API response",
      sources: [],
      session_id: "123"
    })

    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Find me a house" } })
    fireEvent.click(sendButton)

    // User message should appear immediately
    expect(screen.getByText("Find me a house")).toBeInTheDocument()
    
    // Input should be cleared
    expect(input).toHaveValue("")

    // Wait for bot response
    await waitFor(() => {
      expect(screen.getByText("This is a real API response")).toBeInTheDocument()
    })
  })

  it("handles loading state", async () => {
    // Return a promise that doesn't resolve immediately to test loading state
    mockChatMessage.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
      response: "Delayed response",
      sources: [],
      session_id: "123"
    }), 100)))

    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Hello" } })
    fireEvent.click(sendButton)

    expect(screen.getByLabelText("Loading")).toBeInTheDocument()
    expect(sendButton).toBeDisabled()
    
    await waitFor(() => {
      expect(screen.queryByLabelText("Loading")).not.toBeInTheDocument()
    })
  })

  it("handles error state", async () => {
    mockChatMessage.mockRejectedValueOnce(new Error("API Error"))

    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Error" } })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText("I apologize, but I encountered an error connecting to the server. Please try again later.")).toBeInTheDocument()
    })
  })

  it("does not submit empty message", async () => {
    render(<ChatPage />)
    
    const sendButton = screen.getByRole("button", { name: /send message/i })
    
    fireEvent.click(sendButton)
    
    expect(mockChatMessage).not.toHaveBeenCalled()
  })
})
