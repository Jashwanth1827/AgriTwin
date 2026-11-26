import type { Farm, LiveRatePoint, LiveRatesResponse } from "../types";

export const SOUTH_INDIA_FILTER = "__south_india__";
export const TELANGANA_ANDHRA_FILTER = "__telangana_andhra__";

// Telangana and Andhra Pradesh are listed first because they are the two
// states farmers ask about most often in the south India view.
export const SOUTH_INDIA_STATES = [
  "Telangana",
  "Andhra Pradesh",
  "Karnataka",
  "Tamil Nadu",
  "Kerala",
] as const;

export const TELANGANA_ANDHRA_PRADESH = ["Telangana", "Andhra Pradesh"] as const;

/**
 * Merge one official response per state into a single regional view.
 * State requests are independent, so a state with no rows for the selected
 * crop is simply omitted rather than failing the whole region.
 */
export function mergeLiveRates(
  responses: LiveRatesResponse[],
  states: readonly string[] = SOUTH_INDIA_STATES,
  label = "South India",
): LiveRatesResponse {
  const usable = responses.filter((response) => response.records.length > 0);
  if (usable.length === 0) {
    throw new Error(`No live rates available for ${label}.`);
  }

  const records = usable
    .flatMap((response) => response.records)
    .sort((a, b) => {
      const byDate = b.date.localeCompare(a.date);
      if (byDate !== 0) return byDate;
      const byState = a.state.localeCompare(b.state);
      if (byState !== 0) return byState;
      return b.modal_price - a.modal_price;
    })
    .slice(0, 50);

  const dates = usable
    .map((response) => response.latest_observation_date)
    .filter((value): value is string => Boolean(value));
  const freshness = usable
    .map((response) => response.data_freshness_days)
    .filter((value): value is number => value !== null);
  const fetchedAt = usable
    .map((response) => response.fetched_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  const base = usable[0];
  return {
    ...base,
    state: label,
    market: null,
    records,
    latest_observation_date: dates.sort().at(-1) ?? null,
    data_freshness_days: freshness.length > 0 ? Math.min(...freshness) : null,
    fetched_at: fetchedAt ?? base.fetched_at,
    is_demo: usable.some((response) => response.is_demo),
    is_official: usable.every((response) => response.is_official),
    coverage_note: `${label} (${usable.length}/${states.length} states with live rows): ${states.join(", ")}. ${base.coverage_note}`,
  };
}

/**
 * Show the farmer's own district first, then the rest of the state, then any
 * other mandis returned by the feed. Within each group the best modal price is
 * shown first, but the location grouping always wins.
 */
export function rankLiveRatesByLocation(
  records: LiveRatePoint[],
  farm: Farm | null,
): LiveRatePoint[] {
  if (!farm) {
    return [...records].sort((a, b) => b.modal_price - a.modal_price);
  }

  const wantedDistrict = farm.district.trim().toLowerCase();
  const wantedState = farm.state.trim().toLowerCase();

  const locationScore = (row: LiveRatePoint): number => {
    const rowDistrict = (row.district || "").trim().toLowerCase();
    const rowState = (row.state || "").trim().toLowerCase();
    if (rowDistrict === wantedDistrict && rowState === wantedState) return 0;
    if (rowState === wantedState) return 1;
    return 2;
  };

  return [...records].sort((a, b) => {
    const byLocation = locationScore(a) - locationScore(b);
    if (byLocation !== 0) return byLocation;
    const byPrice = b.modal_price - a.modal_price;
    if (byPrice !== 0) return byPrice;
    return b.date.localeCompare(a.date);
  });
}
