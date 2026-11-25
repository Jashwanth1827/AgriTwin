import { describe, expect, it } from "vitest";

import { mergeLiveRates, SOUTH_INDIA_STATES } from "../lib/liveRates";
import type { LiveRatesResponse } from "../types";

function response(
  state: string,
  overrides: Partial<LiveRatesResponse> = {},
): LiveRatesResponse {
  return {
    crop: "Tomato",
    state,
    market: null,
    unit: "INR/quintal",
    provider: "data_gov",
    source_name: "Agmarknet / data.gov.in",
    source_url: "https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi",
    license: "Government of India Open Government Data (data.gov.in)",
    commodity_query: "Tomato",
    records: [
      {
        date: "2026-11-25",
        state,
        district: `${state} district`,
        market: `${state} APMC`,
        commodity: "Tomato",
        variety: "Local",
        grade: "FAQ",
        min_price: 2000,
        max_price: 4000,
        modal_price: 3000,
        fetched_at: "2026-11-25T13:00:53Z",
      },
    ],
    latest_observation_date: "2026-11-25",
    data_freshness_days: 0,
    fetched_at: "2026-11-25T13:00:53Z",
    is_demo: false,
    is_official: true,
    disclaimer: "Wholesale mandi prices.",
    coverage_note: "Official feed.",
    ...overrides,
  };
}

describe("mergeLiveRates", () => {
  it("merges per-state responses into one South India view", () => {
    const merged = mergeLiveRates([
      response("Andhra Pradesh"),
      response("Karnataka"),
      response("Kerala", {
        records: [{ ...response("Kerala").records[0], date: "2026-11-24" }],
        latest_observation_date: "2026-11-24",
        data_freshness_days: 1,
      }),
      { ...response("Tamil Nadu"), records: [] },
      response("Telangana"),
    ]);

    expect(merged.state).toBe("South India");
    expect(merged.records.map((row) => row.state)).toEqual([
      "Andhra Pradesh",
      "Karnataka",
      "Telangana",
      "Kerala",
    ]);
    expect(merged.records.map((row) => row.date)).toEqual([
      "2026-11-25",
      "2026-11-25",
      "2026-11-25",
      "2026-11-24",
    ]);
    expect(merged.latest_observation_date).toBe("2026-11-25");
    expect(merged.data_freshness_days).toBe(0);
    expect(merged.is_official).toBe(true);
    expect(merged.is_demo).toBe(false);
    expect(merged.coverage_note).toContain(SOUTH_INDIA_STATES.join(", "));
  });

  it("caps the merged table and keeps warnings visible", () => {
    const many = Array.from({ length: 20 }, (_, index) =>
      response("Karnataka", {
        records: Array.from({ length: 10 }, (__, rowIndex) => ({
          date: `2026-11-${String(25 - (index % 3)).padStart(2, "0")}`,
          state: "Karnataka",
          district: "Bengaluru South",
          market: `Market ${index}-${rowIndex}`,
          commodity: "Tomato",
          variety: "Local",
          grade: "FAQ",
          min_price: 2000,
          max_price: 4000,
          modal_price: 3000 + rowIndex,
          fetched_at: "2026-11-25T13:00:53Z",
        })),
        is_demo: index === 0,
        is_official: index !== 0,
      }),
    );

    const merged = mergeLiveRates(many);
    expect(merged.records).toHaveLength(50);
    expect(merged.is_demo).toBe(true);
    expect(merged.is_official).toBe(false);
  });

  it("throws when no state returned a live row", () => {
    expect(() => mergeLiveRates([{ ...response("Kerala"), records: [] }])).toThrow(
      "No live rates available for South India.",
    );
  });
});
