import {
  ModelProviderCatalog,
  MortgageResult,
  NotificationSettings,
} from "../types";
import {
  calculateMortgage,
  chatMessage,
  getModelsCatalog,
  getNotificationSettings,
  searchProperties,
  streamChatMessage,
  updateNotificationSettings,
} from "../api";
import { TextEncoder, TextDecoder } from 'util';

global.fetch = jest.fn();

// Polyfill for TextEncoder/TextDecoder if missing in test env
if (typeof global.TextEncoder === 'undefined') {
    (global as unknown as { TextEncoder?: typeof TextEncoder }).TextEncoder = TextEncoder;
    (global as unknown as { TextDecoder?: typeof TextDecoder }).TextDecoder = TextDecoder;
}

describe("API Client", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
    window.localStorage.clear();
    delete process.env.NEXT_PUBLIC_API_KEY;
  });

  describe("Notification Settings", () => {
    const mockSettings: NotificationSettings = {
      email_digest: true,
      frequency: "weekly",
      expert_mode: false,
      marketing_emails: false,
    };

    it("omits auth headers when no user or API key", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      await getNotificationSettings();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(options.headers["X-API-Key"]).toBeUndefined();
      expect(options.headers["X-User-Email"]).toBeUndefined();
    });

    it("omits user email header when running without window", async () => {
      const globalWithWindow = globalThis as unknown as { window?: unknown };
      const originalWindow = globalWithWindow.window;
      delete globalWithWindow.window;

      process.env.NEXT_PUBLIC_API_KEY = "public-test-key";

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      await getNotificationSettings();

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(options.headers["X-API-Key"]).toBe("public-test-key");
      expect(options.headers["X-User-Email"]).toBeUndefined();

      globalWithWindow.window = originalWindow;
    });

    it("fetches settings", async () => {
      window.localStorage.setItem("userEmail", "user@example.com");
      process.env.NEXT_PUBLIC_API_KEY = "public-test-key";

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      const result = await getNotificationSettings();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "X-API-Key": "public-test-key",
            "X-User-Email": "user@example.com",
          }),
        })
      );
      expect(result).toEqual(mockSettings);
    });

    it("updates settings", async () => {
      window.localStorage.setItem("userEmail", "user@example.com");
      process.env.NEXT_PUBLIC_API_KEY = "public-test-key";

      const newSettings = { ...mockSettings, frequency: "daily" as const };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => newSettings,
      });

      const result = await updateNotificationSettings(newSettings);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "PUT",
          headers: expect.objectContaining({
            "X-API-Key": "public-test-key",
            "X-User-Email": "user@example.com",
          }),
          body: JSON.stringify(newSettings),
        })
      );
      expect(result).toEqual(newSettings);
    });
  });

  describe("calculateMortgage", () => {
    it("calls /tools/mortgage-calculator endpoint", async () => {
      const mockResult: MortgageResult = {
        monthly_payment: 2500,
        total_interest: 400000,
        total_cost: 900000,
        down_payment: 100000,
        loan_amount: 400000,
        breakdown: { principal: 1000, interest: 1500 },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const input = {
        property_price: 500000,
        down_payment_percent: 20,
        interest_rate: 4.5,
        loan_years: 30,
      };

      const result = await calculateMortgage(input);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/tools/mortgage-calculator"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(input),
        })
      );
      expect(result).toEqual(mockResult);
    });
  });

  describe("getModelsCatalog", () => {
    it("calls /settings/models endpoint", async () => {
      window.localStorage.setItem("userEmail", "user@example.com");
      process.env.NEXT_PUBLIC_API_KEY = "public-test-key";

      const mockCatalog: ModelProviderCatalog[] = [
        {
          name: "openai",
          display_name: "OpenAI",
          is_local: false,
          requires_api_key: true,
          models: [],
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCatalog,
      });

      const result = await getModelsCatalog();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/models"),
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "X-API-Key": "public-test-key",
            "X-User-Email": "user@example.com",
          }),
        })
      );
      expect(result).toEqual(mockCatalog);
    });
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
            text: async () => JSON.stringify({ detail: "Invalid query" }),
            json: async () => ({ detail: "Invalid query" }),
        });

        await expect(searchProperties({ query: "" })).rejects.toThrow("Invalid query");
    });
    
    it("throws default error if no detail", async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: false,
            statusText: "Server Error",
            text: async () => "Server Error",
            json: async () => { throw new Error() },
        });

        await expect(searchProperties({ query: "" })).rejects.toThrow("Server Error");
    });

    it("throws fallback error if text is empty", async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: false,
            statusText: "Server Error",
            text: async () => "",
            json: async () => { throw new Error() },
        });

        await expect(searchProperties({ query: "" })).rejects.toThrow("API request failed");
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
              headers: { get: () => "req-xyz" },
              text: async () => "",
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
              headers: { get: () => "req-123" },
              text: async () => "",
              body: null
          });

          await expect(streamChatMessage({ message: "test" }, jest.fn()))
              .rejects.toThrow("Failed to start stream");
      });
  });
});
