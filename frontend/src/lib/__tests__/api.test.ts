import { searchProperties, chatMessage, streamChatMessage } from "../api";
import { TextEncoder, TextDecoder } from 'util';

global.fetch = jest.fn();

// Polyfill for TextEncoder/TextDecoder if missing in test env
if (typeof global.TextEncoder === 'undefined') {
    (global as any).TextEncoder = TextEncoder;
    (global as any).TextDecoder = TextDecoder;
}

describe("API Client", () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  describe("searchProperties", () => {
    it("calls /search endpoint", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });

      await searchProperties({ query: "test" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/search"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ query: "test" }),
        })
      );
    });

    it("throws error on failure", async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: false,
            statusText: "Bad Request",
            json: async () => ({ detail: "Invalid query" }),
        });

        await expect(searchProperties({ query: "" })).rejects.toThrow("Invalid query");
    });
    
    it("throws default error if no detail", async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: false,
            statusText: "Server Error",
            json: async () => { throw new Error() },
        });

        await expect(searchProperties({ query: "" })).rejects.toThrow("API Error: Server Error");
    });
  });

  describe("chatMessage", () => {
    it("calls /chat endpoint", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: "Hello" }),
      });

      await chatMessage({ message: "hi" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/chat"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ message: "hi" }),
        })
      );
    });
  });

  describe("streamChatMessage", () => {
      it("handles streaming response", async () => {
          const encoder = new TextEncoder();
          const mockReader = {
              read: jest.fn()
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: Chunk 1\n\n") })
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: Chunk 2\n\n") })
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: [DONE]\n\n") })
                  .mockResolvedValueOnce({ done: true, value: undefined })
          };

          (global.fetch as jest.Mock).mockResolvedValueOnce({
              ok: true,
              body: {
                  getReader: () => mockReader
              }
          });

          const onChunk = jest.fn();
          await streamChatMessage({ message: "stream" }, onChunk);

          expect(onChunk).toHaveBeenCalledTimes(2);
          expect(onChunk).toHaveBeenCalledWith("Chunk 1");
          expect(onChunk).toHaveBeenCalledWith("Chunk 2");
      });

      it("throws if body is missing", async () => {
          (global.fetch as jest.Mock).mockResolvedValueOnce({
              ok: true,
              body: null
          });

          await expect(streamChatMessage({ message: "test" }, jest.fn()))
              .rejects.toThrow("Failed to start stream");
      });
  });
});
