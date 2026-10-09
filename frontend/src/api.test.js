import { describe, expect, it, vi } from "vitest";
import { getCompanyId, pollInterval, request, setCompanyId } from "./api";
import { mockApi } from "./test/utils";

describe("request", () => {
  it("returns JSON on success", async () => {
    mockApi({ "GET /tenders": [{ id: 1 }] });
    expect(await request("/tenders")).toEqual([{ id: 1 }]);
  });

  it("throws the backend's detail message", async () => {
    mockApi({ "POST /tenders": { status: 400, body: { detail: "Please upload a PDF file" } } });
    await expect(request("/tenders", { method: "POST" })).rejects.toThrow("Please upload a PDF file");
  });

  it("explains when the server cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(request("/tenders")).rejects.toThrow("Cannot reach the server. Is the backend running?");
  });

  it("sends JSON bodies", async () => {
    const calls = mockApi({ "POST /companies": { id: 3 } });
    await request("/companies", { method: "POST", json: { name: "A" } });
    expect(calls[0].init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(calls[0].init.body)).toEqual({ name: "A" });
  });
});

describe("helpers", () => {
  it("polls only while running", () => {
    expect(pollInterval("running")).toBe(2000);
    expect(pollInterval("awaiting_approval")).toBe(false);
    expect(pollInterval(undefined)).toBe(false);
  });

  it("remembers the company id", () => {
    expect(getCompanyId()).toBeNull();
    setCompanyId(7);
    expect(getCompanyId()).toBe(7);
  });
});
