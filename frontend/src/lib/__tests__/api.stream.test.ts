import { streamChatMessage } from "../api";
import type { ChatRequest } from "../types";

describe("streamChatMessage", () => {
  const g = global as unknown as { fetch: typeof fetch; TextDecoder: typeof TextDecoder };
  const originalFetch = g.fetch;
  const originalTextDecoder = g.TextDecoder;

  beforeEach(() => {
    jest.resetAllMocks();
  });

  afterEach(() => {
    g.fetch = originalFetch;
    g.TextDecoder = originalTextDecoder;
  });

  function createMockReadable(chunks: string[]) {
    const encoded = chunks.map(c => Uint8Array.from(Buffer.from(c, "utf-8")));
    let index = 0;
    return {
      getReader() {
        return {
          async read() {
            if (index < encoded.length) {
              const value = encoded[index++];
              return { done: false, value };
            }
            return { done: true, value: undefined };
          }
        };
      }
    } as unknown as ReadableStream;
  }

  it("parses SSE data chunks and calls onChunk", async () => {
    class FakeTextDecoder {
      decode(u: Uint8Array) {
        return Buffer.from(u).toString("utf-8");
      }
    }
    g.TextDecoder = FakeTextDecoder as unknown as typeof TextDecoder;
    const chunks = ["data: Hello\n\n", "data: world\n\n", "data: [DONE]\n\n"];
    g.fetch = jest.fn().mockResolvedValue({
      ok: true,
      body: createMockReadable(chunks),
      headers: { get: (name: string) => (name === "X-Request-ID" ? "req-456" : null) },
    }) as unknown as typeof fetch;

    const received: string[] = [];
    let startedWith: string | undefined;

    await streamChatMessage(
      { message: "hi" } as ChatRequest,
      (chunk) => received.push(chunk),
      ({ requestId }) => {
        startedWith = requestId;
      }
    );

    expect(received.join("")).toBe("Helloworld");
    expect(startedWith).toBe("req-456");
  });

  it("propagates errors with request_id if present", async () => {
    g.fetch = jest.fn().mockResolvedValue({
      ok: false,
      text: () => Promise.resolve("Stream error"),
      headers: { get: (name: string) => (name === "X-Request-ID" ? "req-999" : null) },
    }) as unknown as typeof fetch;

    await expect(
      streamChatMessage({ message: "x" } as ChatRequest, () => {})
    ).rejects.toThrow(/request_id=req-999/);
  });
});
