import {
  calculateMortgage,
  searchProperties,
  chatMessage,
  exportPropertiesBySearch,
} from "../api";

global.fetch = jest.fn(async (input: RequestInfo | URL) => {
  const url = typeof input === "string" ? input : String(input);
  if (url.includes("/export/properties")) {
    const blob = new Blob(["id,price\n1,100"], { type: "text/csv" });
    return {
      ok: true,
      statusText: "OK",
      headers: { get: (name: string) => (name === "Content-Disposition" ? 'attachment; filename="properties.csv"' : null) },
      blob: async () => blob,
      text: async () => "",
      json: async () => ({}),
    } as unknown as Response;
  }
  return {
    ok: true,
    statusText: "OK",
    headers: { get: () => null },
    json: async () => ({}),
    text: async () => "",
  } as unknown as Response;
}) as jest.Mock;

describe("api misc", () => {
  it("calculates mortgage", async () => {
    await calculateMortgage({ property_price: 100000, down_payment_percent: 20, interest_rate: 6, loan_years: 30 });
    expect(global.fetch).toHaveBeenCalled();
  });
  it("searches properties", async () => {
    await searchProperties({ query: "Warsaw", limit: 5, filters: {}, alpha: 0.7 });
    expect(global.fetch).toHaveBeenCalled();
  });
  it("sends chatMessage", async () => {
    await chatMessage({ message: "hi" });
    expect(global.fetch).toHaveBeenCalled();
  });
  it("exports properties by search", async () => {
    const res = await exportPropertiesBySearch({ query: "Warsaw", limit: 5, filters: {}, alpha: 0.7 }, "csv");
    expect(res.filename).toBe("properties.csv");
  });
});
