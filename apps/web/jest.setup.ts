import "@testing-library/jest-dom";

type ResponseInitLike = {
  status?: number;
  statusText?: string;
  headers?: HeadersInit;
};

class PolyfilledResponse {
  body: unknown;
  status: number;
  statusText: string;
  headers: Headers;

  constructor(body?: unknown, init?: ResponseInitLike) {
    this.body = body;
    this.status = init?.status ?? 200;
    this.statusText = init?.statusText ?? "";
    this.headers = new Headers(init?.headers);
  }

  async text(): Promise<string> {
    return typeof this.body === "string" ? this.body : "";
  }

  async json(): Promise<unknown> {
    const raw = await this.text();
    return raw ? JSON.parse(raw) : null;
  }
}

const globalWithResponse = globalThis as unknown as { Response?: unknown };
if (!globalWithResponse.Response) {
  globalWithResponse.Response = PolyfilledResponse;
}
