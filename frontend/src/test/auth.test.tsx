import { render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "../lib/auth";
import { getAccessToken, getRefreshToken, setTokens } from "../lib/api";
import type { TokenResponse, User } from "../types";

const USER: User = {
  id: 1,
  email: "demo@agritwin.in",
  full_name: "Demo Farmer",
  phone: null,
  state: "Maharashtra",
  district: "Nashik",
  preferred_language: "en",
  is_demo: true,
  created_at: "2026-11-04T00:00:00Z",
};

const TOKENS: TokenResponse = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  expires_in: 3600,
  user: USER,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function Probe() {
  const { user, loading, login, logout, refreshUser } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user?.email ?? "anonymous"}</span>
      <button onClick={() => void login("demo@agritwin.in", "Demo@12345")}>login</button>
      <button onClick={() => void logout()}>logout</button>
      <button onClick={() => void refreshUser()}>refresh</button>
    </div>
  );
}

function renderAuth() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("settles to anonymous when no tokens are stored", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderAuth();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("anonymous");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("restores the session from a stored token", async () => {
    setTokens("access-1", "refresh-1");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(USER)));

    renderAuth();

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent(USER.email));
    expect(screen.getByTestId("loading")).toHaveTextContent("false");
  });

  it("clears invalid stored tokens when /auth/me fails", async () => {
    setTokens("access-1", "refresh-1");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: "unauthorized", message: "Invalid token" } }, 401),
      ),
    );

    renderAuth();

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("user")).toHaveTextContent("anonymous");
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("logs in, stores tokens and exposes the user", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(TOKENS)));

    renderAuth();
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent(USER.email));
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
  });

  it("logs out locally even when the API call fails", async () => {
    setTokens("access-1", "refresh-1");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(USER))
      .mockRejectedValueOnce(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);

    renderAuth();
    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent(USER.email));

    await act(async () => {
      screen.getByText("logout").click();
    });

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("anonymous"));
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("throws when useAuth is used outside the provider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow("useAuth must be used within AuthProvider");
    consoleError.mockRestore();
  });
});
