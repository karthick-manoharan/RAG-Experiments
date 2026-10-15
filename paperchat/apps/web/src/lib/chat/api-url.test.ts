import { describe, expect, it } from "vitest";
import { resolveApiBaseUrl } from "./api-url";

describe("API URL configuration", () => {
  it.each([undefined, "", " ", "bad", "https:example.com", "http://api.example.com",
    "https://localhost", "https://app.localhost", "https://127.0.0.1", "https://127.1",
    "https://[::1]", "https://0.0.0.0", "https://user:secret@api.example.com",
    "https://api.example.com?x=1", "https://api.example.com#x", " https://api.example.com",
    "https://api.example.com\\foo"])("rejects invalid production URL %s", (value) => {
    expect(() => resolveApiBaseUrl(value, true)).toThrow("NEXT_PUBLIC_API_BASE_URL");
  });
  it("normalizes valid HTTPS URLs", () => {
    expect(resolveApiBaseUrl("https://api.example.com///", true)).toBe("https://api.example.com");
    expect(resolveApiBaseUrl("https://api.example.com/prefix/", true)).toBe("https://api.example.com/prefix");
  });
  it("retains the development default and explicit local URL", () => {
    expect(resolveApiBaseUrl(undefined, false)).toBe("http://localhost:8000");
    expect(resolveApiBaseUrl("http://localhost:8001/", false)).toBe("http://localhost:8001");
  });
});
