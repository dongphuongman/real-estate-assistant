import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import ChatPage from "../page"
import { streamChatMessage } from "@/lib/api"

// Mock the API module
jest.mock("@/lib/api", () => ({
  streamChatMessage: jest.fn(),
}))

const mockStream = streamChatMessage as jest.Mock

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
    mockStream.mockImplementation(async (_req, onChunk) => {
      onChunk("This is a real API response")
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
    mockStream.mockImplementation(
      () =>
        new Promise<void>(resolve =>
          setTimeout(() => {
            resolve()
          }, 100)
        )
    )

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
    mockStream.mockRejectedValueOnce(new Error("Failed to start stream (request_id=req-xyz)"))

    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Error" } })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText("I apologize, but I encountered an error. Please try again.")).toBeInTheDocument()
    })
    expect(screen.getByText("request_id=req-xyz")).toBeInTheDocument()
  })

  it("shows retry button and retries stream", async () => {
    mockStream
      .mockRejectedValueOnce(new Error("Failed to start stream (request_id=req-123)"))
      .mockImplementationOnce(async (_req, onChunk) => {
        onChunk("Recovered response")
      })

    render(<ChatPage />)

    const input = screen.getByPlaceholderText("Ask about properties, market trends, or investment advice...")
    const sendButton = screen.getByRole("button", { name: /send message/i })

    fireEvent.change(input, { target: { value: "Retry test" } })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
    })
    expect(screen.getByText("request_id=req-123")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /retry/i }))

    await waitFor(() => {
      expect(screen.getByText(/Recovered response/)).toBeInTheDocument()
    })
  })

  it("does not submit empty message", async () => {
    render(<ChatPage />)
    
    const sendButton = screen.getByRole("button", { name: /send message/i })
    
    fireEvent.click(sendButton)
    
    expect(mockStream).not.toHaveBeenCalled()
  })
})
