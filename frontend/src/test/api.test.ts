import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  api,
  apiRequest,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "../lib/api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("token storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores, reads and clears both tokens", () => {
    expect(getAccessToken()).toBeNull();
    setTokens("access-1", "refresh-1");
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

describe("apiRequest", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("attaches the bearer token and parses JSON", async () => {
    setTokens("access-1", "refresh-1");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.get<{ ok: boolean }>("/farms");

    expect(result).toEqual({ ok: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/farms");
    expect((init as RequestInit).headers).toMatchObject({
      Accept: "application/json",
      Authorization: "Bearer access-1",
    });
  });

  it("serialises JSON bodies and sets the content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await api.post("/farms", { name: "Test" });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "Test" }));
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("returns undefined for empty and 204 responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await api.delete("/farms/1")).toBeUndefined();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 200 })));
    expect(await api.get("/empty")).toBeUndefined();
  });

  it("parses the backend error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: "not_found", message: "Farm not found", details: null } },
          404,
        ),
      ),
    );

    const error = await api.get("/farms/99").catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).code).toBe("not_found");
    expect((error as ApiError).message).toBe("Farm not found");
  });

  it("surfaces the first validation detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "validation_error",
              message: "Request validation failed",
              details: [{ field: "body.email", message: "Invalid email" }],
            },
          },
          422,
        ),
      ),
    );

    const error = (await api.post("/auth/login", {}).catch((err: unknown) => err)) as ApiError;

    expect(error.message).toBe("body.email: Invalid email");
    expect(error.status).toBe(422);
  });

  it("falls back to status text for non-JSON errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("gateway down", { status: 502 })),
    );

    const error = (await api.get("/x").catch((err: unknown) => err)) as ApiError;

    expect(error.status).toBe(502);
    expect(error.message).toBe("Request failed with status 502");
    expect(error.code).toBe("http_error");
  });

  it("refreshes once on 401 and retries the original request", async () => {
    setTokens("expired-access", "refresh-1");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: { code: "unauthorized" } }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "fresh-access", refresh_token: "refresh-2" }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: 7 }));

    vi.stubGlobal("fetch", fetchMock);

    const result = await api.get<{ id: number }>("/farms/7");

    expect(result).toEqual({ id: 7 });
    expect(getAccessToken()).toBe("fresh-access");
    expect(getRefreshToken()).toBe("refresh-2");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/refresh");
    const retryInit = fetchMock.mock.calls[2][1] as RequestInit;
    expect((retryInit.headers as Record<string, string>).Authorization).toBe(
      "Bearer fresh-access",
    );
  });

  it("clears tokens when the refresh fails", async () => {
    setTokens("expired-access", "bad-refresh");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: { code: "unauthorized" } }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: { code: "unauthorized" } }, 401));

    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get("/farms")).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("does not refresh when auth is disabled", async () => {
    setTokens("expired-access", "refresh-1");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: false }, 401));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest("/public", { auth: false }).catch((err: unknown) => Promise.reject(err)),
    ).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uploads FormData without a JSON content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 3 }, 201));
    vi.stubGlobal("fetch", fetchMock);
    const form = new FormData();
    form.append("farm_id", "1");

    await api.upload("/crop-health/predict", form);

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(form);
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });
});
