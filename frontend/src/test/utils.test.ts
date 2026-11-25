import { describe, expect, it } from "vitest";

import {
  cn,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  formatPercent,
  isoDaysFromNow,
  shortLabel,
  titleCase,
  todayIso,
} from "../lib/utils";

describe("cn", () => {
  it("merges conditional classes and resolves Tailwind conflicts", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-sm", false && "hidden", ["font-bold"])).toBe("text-sm font-bold");
    expect(cn()).toBe("");
  });
});

describe("number and currency formatting", () => {
  it("formats Indian currency without decimals by default", () => {
    expect(formatCurrency(1234.5)).toContain("1,235");
    expect(formatCurrency(1234.5, 2)).toContain("1,234.50");
  });

  it("returns an em dash for missing or invalid values", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
    expect(formatCurrency(Number.NaN)).toBe("—");
    expect(formatNumber(null)).toBe("—");
    expect(formatPercent(Number.NaN)).toBe("—");
  });

  it("formats numbers and percentages", () => {
    expect(formatNumber(1234567.891, 2)).toBe("12,34,567.89");
    expect(formatPercent(0.4213, 1)).toBe("42.1%");
    expect(formatPercent(1, 0)).toBe("100%");
  });
});

describe("date formatting", () => {
  it("formats ISO dates for India", () => {
    expect(formatDate("2026-11-04")).toContain("2026");
    expect(formatDate("2026-11-04")).toContain("Nov");
  });

  it("handles missing and invalid input", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  it("returns ISO date strings", () => {
    expect(todayIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(isoDaysFromNow(7) > todayIso()).toBe(true);
  });
});

describe("label helpers", () => {
  it("turns snake_case into title case", () => {
    expect(titleCase("yield_prediction")).toBe("Yield Prediction");
    expect(titleCase("crop-health")).toBe("Crop Health");
  });

  it("truncates long labels with an ellipsis", () => {
    expect(shortLabel("A very long market name that should be cut", 12)).toHaveLength(12);
    expect(shortLabel("A very long market name that should be cut", 12)).toMatch(/…$/);
    expect(shortLabel("Short")).toBe("Short");
    expect(shortLabel(null)).toBe("—");
  });
});
