import {
  calculateMortgage,
  searchProperties,
  chatMessage,
  exportPropertiesBySearch,
} from "../api";

global.fetch = jest.fn(async (input: RequestInfo | URL) => {
  const url = typeof input === "string" ? input : String(input);
  if (url.includes("/export/properties")) {
    const headers = new Headers({ "Content-Disposition": 'attachment; filename="properties.csv"' });
    const blob = new Blob(["id,price\n1,100"], { type: "text/csv" });
    const response = new Response(blob, { status: 200, headers });
    return response;
  }
  const response = new Response(JSON.stringify({}), {
    status: 200,
    headers: new Headers(),
  });
  return response;
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
