import type { LiveRatesResponse } from "../types";

export const SOUTH_INDIA_FILTER = "__south_india__";

export const SOUTH_INDIA_STATES = [
  "Andhra Pradesh",
  "Karnataka",
  "Kerala",
  "Tamil Nadu",
  "Telangana",
] as const;

/**
 * Merge one official response per South Indian state into a single view.
 * State requests are independent, so a state with no rows for the selected
 * crop is simply omitted rather than failing the whole region.
 */
export function mergeLiveRates(responses: LiveRatesResponse[]): LiveRatesResponse {
  const usable = responses.filter((response) => response.records.length > 0);
  if (usable.length === 0) {
    throw new Error("No live rates available for South India.");
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
    state: "South India",
    market: null,
    records,
    latest_observation_date: dates.sort().at(-1) ?? null,
    data_freshness_days: freshness.length > 0 ? Math.min(...freshness) : null,
    fetched_at: fetchedAt ?? base.fetched_at,
    is_demo: usable.some((response) => response.is_demo),
    is_official: usable.every((response) => response.is_official),
    coverage_note: `South India (${usable.length}/${SOUTH_INDIA_STATES.length} states with live rows): ${SOUTH_INDIA_STATES.join(", ")}. ${base.coverage_note}`,
  };
}
