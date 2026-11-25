import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

/**
 * Node 22+ ships a `localStorage` global that stays `undefined` unless the
 * process is started with `--localstorage-file`, and that global can shadow
 * jsdom's implementation. Provide a deterministic in-memory Storage so the
 * app code under test always sees a working `localStorage`.
 */
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? (store.get(key) as string) : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  } as Storage;
}

function ensureStorage(name: "localStorage" | "sessionStorage") {
  const existing = (globalThis as Record<string, unknown>)[name];
  const storage = existing instanceof Object ? (existing as Storage) : createMemoryStorage();
  Object.defineProperty(globalThis, name, {
    value: storage,
    configurable: true,
    writable: true,
  });
  if (typeof window !== "undefined") {
    Object.defineProperty(window, name, {
      value: storage,
      configurable: true,
      writable: true,
    });
  }
}

ensureStorage("localStorage");
ensureStorage("sessionStorage");

beforeEach(() => {
  globalThis.localStorage.clear();
  globalThis.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
});
