import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { SignJWT } from "jose";
import { middleware } from "./middleware";

// Matches the fallback middleware.ts uses when SECRET_KEY isn't set in env -
// fine for test purposes, avoids mocking jose internals.
const SECRET = new TextEncoder().encode("your-secret-key-change-me-in-production");

async function makeToken(payload: Record<string, unknown>) {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("1h")
    .sign(SECRET);
}

function makeRequest(path: string, token?: string) {
  const headers = new Headers();
  if (token) headers.set("cookie", `token=${token}`);
  return new NextRequest(new URL(path, "http://localhost:3000"), { headers });
}

describe("middleware route protection", () => {
  it("redirects unauthenticated users away from protected routes", async () => {
    const res = await middleware(makeRequest("/dashboard"));
    expect(res.headers.get("location")).toContain("/login");
  });

  it("redirects non-admin users away from /admin", async () => {
    const token = await makeToken({ sub: "user@example.com", role: "user" });
    const res = await middleware(makeRequest("/admin", token));
    expect(res.headers.get("location")).toContain("/dashboard");
  });

  it("allows admin users through to /admin", async () => {
    const token = await makeToken({ sub: "admin@example.com", role: "admin" });
    const res = await middleware(makeRequest("/admin", token));
    expect(res.headers.get("location")).toBeNull();
  });

  it("redirects authenticated users away from public routes", async () => {
    const token = await makeToken({ sub: "user@example.com", role: "user" });
    const res = await middleware(makeRequest("/login", token));
    expect(res.headers.get("location")).toContain("/dashboard");
  });

  it("allows unauthenticated users to reach public routes", async () => {
    const res = await middleware(makeRequest("/login"));
    expect(res.headers.get("location")).toBeNull();
  });
});
