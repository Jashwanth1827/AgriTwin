import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowUpRight,
  CloudDownload,
  Gauge,
  LineChart as LineChartIcon,
  MapPin,
  Radio,
  RefreshCw,
  Store,
  TrendingUp,
  Upload,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ApiError, api } from "../lib/api";
import {
  mergeLiveRates,
  rankLiveRatesByLocation,
  SOUTH_INDIA_FILTER,
  SOUTH_INDIA_STATES,
  TELANGANA_ANDHRA_FILTER,
  TELANGANA_ANDHRA_PRADESH,
} from "../lib/liveRates";
import { useFarms } from "../hooks/useReference";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  titleCase,
} from "../lib/utils";
import type {
  ForecastPoint,
  LiveRatesResponse,
  MarketCropInfo,
  MarketForecast,
  MarketImportResponse,
  MarketPricesResponse,
  MarketTrends,
} from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select, Textarea } from "../components/ui/input";
import {
  Alert,
  DemoBadge,
  EmptyState,
  LoadingBlock,
  PageHeader,
  Tabs,
} from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

const CHART_COLORS = {
  modal: "#1f7a4d",
  band: "#2f9e68",
  expected: "#c2872a",
};

export default function MarketPage() {
  const [tab, setTab] = useState("live");
  const [crop, setCrop] = useState<string>("");
  const [market, setMarket] = useState<string>("");
  const [liveState, setLiveState] = useState("");
  const [liveNonce, setLiveNonce] = useState(0);
  const [days, setDays] = useState("180");
  const [horizon, setHorizon] = useState("14");
  const [importOpen, setImportOpen] = useState(false);
  const [csv, setCsv] = useState("");
  const [source, setSource] = useState("user_csv");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAllMandis, setShowAllMandis] = useState(false);
  // undefined = use the first farm automatically; null = manual location entry.
  const [farmId, setFarmId] = useState<number | null | undefined>(undefined);
  const [liveDistrict, setLiveDistrict] = useState("");

  const farms = useFarms();
  const crops = useQuery({
    queryKey: ["market-crops"],
    queryFn: () => api.get<{ crops: MarketCropInfo[]; unit: string }>("/market/crops"),
  });

  const activeCrop = crop || crops.data?.crops[0]?.crop || "";
  const activeFarmId = farmId === undefined ? (farms.data?.[0]?.id ?? 0) : farmId;
  const selectedFarm = farms.data?.find((item) => item.id === activeFarmId) ?? null;
  const locationState = selectedFarm?.state || liveState;
  const locationDistrict = selectedFarm?.district || liveDistrict;
  const isSouthIndia = locationState === SOUTH_INDIA_FILTER;
  const isTelanganaAndhra = locationState === TELANGANA_ANDHRA_FILTER;
  const isRegional = isSouthIndia || isTelanganaAndhra;
  const regionStates = isTelanganaAndhra ? TELANGANA_ANDHRA_PRADESH : SOUTH_INDIA_STATES;
  const regionLabel = isTelanganaAndhra ? "Telangana + Andhra Pradesh" : "South India";

  const liveRates = useQuery({
    queryKey: ["market-live-rates", activeCrop, activeFarmId, locationState, locationDistrict, liveNonce],
    queryFn: async () => {
      const refresh = liveNonce > 0;
      if (!isRegional) {
        const fetchForLocation = (district: string) =>
          api.get<LiveRatesResponse>(
            `/market/live-rates?crop=${encodeURIComponent(activeCrop)}&state=${encodeURIComponent(locationState)}${district ? `&district=${encodeURIComponent(district)}` : ""}&limit=100&refresh=${refresh}`,
          );
        try {
          return await fetchForLocation(locationDistrict);
        } catch (error) {
          // A district can legitimately have no rows in the public feed.
          // Fall back to the farmer's state instead of showing a failure.
          if (!(error instanceof ApiError && error.status === 404)) throw error;
          if (!locationDistrict) throw error;
          return fetchForLocation("");
        }
      }

      const perStateLimit = Math.ceil(50 / regionStates.length);
      const settled = await Promise.allSettled(
        regionStates.map((state) =>
          api.get<LiveRatesResponse>(
            `/market/live-rates?crop=${encodeURIComponent(activeCrop)}&state=${encodeURIComponent(state)}&limit=${perStateLimit}&refresh=${refresh}`,
          ),
        ),
      );
      const responses = settled.flatMap((result) =>
        result.status === "fulfilled" ? [result.value] : [],
      );
      if (responses.length === 0) {
        const failure = settled.find((result) => result.status === "rejected");
        throw failure?.reason ?? new Error(`No live rates available for ${regionLabel}.`);
      }
      return mergeLiveRates(responses, regionStates, regionLabel);
    },
    enabled: activeCrop.length > 0 && tab === "live",
    retry: false,
  });

  const prices = useQuery({
    queryKey: ["market-prices", activeCrop, market, days],
    queryFn: () =>
      api.get<MarketPricesResponse>(
        `/market/prices?crop=${encodeURIComponent(activeCrop)}${market ? `&market=${encodeURIComponent(market)}` : ""}&days=${days}`,
      ),
    enabled: activeCrop.length > 0 && tab === "prices",
  });

  const trends = useQuery({
    queryKey: ["market-trends", activeCrop],
    queryFn: () => api.get<MarketTrends>(`/market/trends?crop=${encodeURIComponent(activeCrop)}`),
    enabled: activeCrop.length > 0 && tab === "markets",
  });

  const forecasts = useQuery({
    queryKey: ["market-forecasts", activeCrop],
    queryFn: () => api.get<MarketForecast[]>(`/market/forecasts?crop=${encodeURIComponent(activeCrop)}`),
    enabled: activeCrop.length > 0 && tab === "forecast",
  });

  const forecast = useMutation({
    mutationFn: () =>
      api.post<MarketForecast>("/market/forecast", {
        crop: activeCrop,
        market: market || undefined,
        horizon_days: Number(horizon),
      }),
    onSuccess: () => {
      setError(null);
      setNotice("Forecast generated and saved.");
      void forecasts.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const importPrices = useMutation({
    mutationFn: () =>
      api.post<MarketImportResponse>("/market/import", { csv_content: csv, source }),
    onSuccess: (data) => {
      setImportOpen(false);
      setCsv("");
      setNotice(`Imported ${data.inserted} rows, skipped ${data.skipped}.`);
      void crops.refetch();
      void prices.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const series = useMemo(
    () =>
      (prices.data?.points ?? []).map((point) => ({
        date: point.date,
        modal: point.modal_price,
        low: point.min_price,
        high: point.max_price,
      })),
    [prices.data],
  );

  const latest = series.at(-1);
  const previous = series.at(-2);
  const change =
    latest && previous && previous.modal !== 0
      ? (latest.modal - previous.modal) / previous.modal
      : null;

  const activeForecast = forecast.data ?? forecasts.data?.[0] ?? null;

  const rankedRates = useMemo(
    () => rankLiveRatesByLocation(liveRates.data?.records ?? [], selectedFarm),
    [liveRates.data, selectedFarm],
  );
  const bestRate = rankedRates[0] ?? null;
  const localRateCount = selectedFarm
    ? rankedRates.filter(
        (row) =>
          (row.district || "").trim().toLowerCase() ===
          selectedFarm.district.trim().toLowerCase(),
      ).length
    : 0;
  const locationDescription = selectedFarm
    ? localRateCount > 0
      ? `Using ${selectedFarm.name}: ${localRateCount} mandi row${localRateCount === 1 ? "" : "s"} in ${selectedFarm.district} district shown first.`
      : `Using ${selectedFarm.name}: no rows for ${selectedFarm.district} district in this feed, showing ${selectedFarm.state} mandis instead.`
    : "Choose your farm to show its district first, or enter a state and district manually.";

  const freshnessDays = liveRates.data?.data_freshness_days ?? null;
  const freshnessText =
    freshnessDays === null
      ? "Update time unknown"
      : freshnessDays === 0
        ? "Updated today"
        : freshnessDays === 1
          ? "Updated yesterday"
          : `${freshnessDays} days old`;
  const simpleAdvice =
    freshnessDays === null
      ? "Refresh the prices before you decide where to sell."
      : freshnessDays <= 1
        ? "These are current government mandi rates. Compare the nearest mandi before selling."
        : "These rates are a few days old. Refresh them before selling.";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Market"
        description="Check today’s price, compare mandis, and decide where to sell."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
              <Upload className="h-4 w-4" /> Import CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void crops.refetch()}
              loading={crops.isFetching}
            >
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </>
        }
      />

      {notice ? <Alert variant="success">{notice}</Alert> : null}
      {error ? (
        <Alert variant="error" title="Market request failed">
          {error}
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-end gap-3 rounded-xl border bg-card p-4">
        <Field label="My farm" className="min-w-52">
          <Select
            value={activeFarmId ? String(activeFarmId) : ""}
            onChange={(event) =>
              setFarmId(event.target.value ? Number(event.target.value) : null)
            }
          >
            <option value="">Choose manually</option>
            {(farms.data ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.district}, {item.state}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Crop" className="min-w-44">
          <Select
            value={activeCrop}
            onChange={(event) => {
              setCrop(event.target.value);
              setMarket("");
            }}
          >
            {(crops.data?.crops ?? []).map((row) => (
              <option key={row.crop} value={row.crop}>
                {row.crop} · {row.observations} rows
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Market (optional)" className="min-w-52">
          <Select value={market} onChange={(event) => setMarket(event.target.value)}>
            <option value="">Best available market</option>
            {(prices.data?.available_markets ?? []).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Window (days)" className="w-32">
          <Select value={days} onChange={(event) => setDays(event.target.value)}>
            {["30", "90", "180", "365", "1095"].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </Field>
        <Tabs
          tabs={[
            { value: "live", label: "Today’s price" },
            { value: "prices", label: "Past prices" },
            { value: "markets", label: "Compare mandis" },
            { value: "forecast", label: "Expected price" },
          ]}
          value={tab}
          onChange={setTab}
        />
      </div>

      {tab === "live" ? (
        <Card>
          <CardHeader className="flex-row flex-wrap items-end justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-primary" /> Today’s mandi price
              </CardTitle>
              <CardDescription>
                Government mandi prices for {activeCrop || "your crop"}. Use this before you sell.{" "}
                <span className="font-medium text-foreground">{locationDescription}</span>
                {isRegional ? ` Showing ${regionLabel} mandis together.` : ""}
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <Field label="Your state" className="w-44">
                <Input
                  value={
                    isRegional ? `${regionLabel} (${regionStates.length} states)` : locationState
                  }
                  placeholder="All states"
                  readOnly={isRegional || Boolean(selectedFarm)}
                  onChange={(event) => setLiveState(event.target.value)}
                />
              </Field>
              <Field label="Your district" className="w-44">
                <Input
                  value={isRegional ? "" : locationDistrict}
                  placeholder="All districts"
                  readOnly={isRegional || Boolean(selectedFarm)}
                  onChange={(event) => setLiveDistrict(event.target.value)}
                />
              </Field>
              <Button
                variant={isSouthIndia ? "default" : "outline"}
                onClick={() => {
                  setFarmId(null);
                  setLiveState((current) =>
                    current === SOUTH_INDIA_FILTER ? "" : SOUTH_INDIA_FILTER,
                  );
                }}
                loading={liveRates.isFetching && isSouthIndia}
              >
                South India
              </Button>
              <Button
                variant={isTelanganaAndhra ? "default" : "outline"}
                onClick={() => {
                  setFarmId(null);
                  setLiveState((current) =>
                    current === TELANGANA_ANDHRA_FILTER ? "" : TELANGANA_ANDHRA_FILTER,
                  );
                }}
                loading={liveRates.isFetching && isTelanganaAndhra}
              >
                Telangana + Andhra
              </Button>
              <Button
                variant="outline"
                onClick={() => setLiveNonce((value) => value + 1)}
                loading={liveRates.isFetching}
              >
                <RefreshCw className="h-4 w-4" /> Update prices
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {liveRates.isLoading ? (
              <LoadingBlock label="Fetching live mandi rates…" />
            ) : liveRates.isError ? (
              <>
                <Alert variant="warning" title="Live feed unavailable">
                  {(liveRates.error as Error).message}
                </Alert>
                <p className="text-sm text-muted-foreground">
                  The bundled Agmarknet series in the Prices tab is still available offline.
                </p>
              </>
            ) : liveRates.data && rankedRates.length > 0 ? (
              <>
                <div className="rounded-xl border bg-primary/5 p-4 sm:p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        {selectedFarm ? "Best nearby price today" : "Best price today"}
                      </p>
                      <p className="mt-1 text-3xl font-bold text-primary sm:text-4xl">
                        {formatCurrency((bestRate?.modal_price ?? 0) / 100, 2)} / kg
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {formatCurrency(bestRate?.modal_price ?? 0, 0)} per quintal
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge
                        variant={
                          freshnessDays !== null && freshnessDays <= 7 ? "success" : "warning"
                        }
                      >
                        {freshnessText}
                      </Badge>
                      <Badge variant={liveRates.data.is_official ? "success" : "info"}>
                        {liveRates.data.is_official ? "Government data" : "Public mirror"}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                    <span className="font-medium">{bestRate?.market || "Mandi"}</span>
                    {bestRate?.district ? (
                      <span className="text-muted-foreground">{bestRate.district}</span>
                    ) : null}
                    {bestRate?.state ? (
                      <span className="text-muted-foreground">{bestRate.state}</span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm">{simpleAdvice}</p>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="flex items-center gap-2 font-medium">
                      <MapPin className="h-4 w-4 text-primary" /> Nearby mandis
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAllMandis((value) => !value)}
                    >
                      {showAllMandis
                        ? "Show fewer"
                        : `See all ${rankedRates.length}`}
                    </Button>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                    {(showAllMandis ? rankedRates : rankedRates.slice(0, 3)).map((row, index) => (
                      <div
                        key={`${row.market}-${row.variety}-${row.date}-${index}`}
                        className="rounded-lg border p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate font-medium">{row.market || "Mandi"}</p>
                          <p className="whitespace-nowrap font-semibold text-primary">
                            {formatCurrency(row.modal_price / 100, 2)}/kg
                          </p>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {[row.district, row.state].filter(Boolean).join(", ") ||
                            "Location not listed"}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDate(row.date)} · {row.variety}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <details className="rounded-lg border">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-medium">
                    View data details (sources, full table, licence)
                  </summary>
                  <div className="space-y-4 border-t px-4 py-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border p-3">
                    <p className="text-xs uppercase text-muted-foreground">Data source</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1">
                      <Badge variant={liveRates.data.is_official ? "success" : "info"}>
                        {liveRates.data.is_official ? "Official" : "Keyless mirror"}
                      </Badge>
                      <DemoBadge show={liveRates.data.is_demo} />
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {liveRates.data.source_name}
                    </p>
                    {liveRates.data.sources?.length ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {liveRates.data.sources
                          .map((item) => `${item.name.split(" - ").at(-1)}: ${item.record_count}`)
                          .join(" · ")}
                      </p>
                    ) : null}
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs uppercase text-muted-foreground">Latest modal price</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatCurrency(bestRate?.modal_price ?? 0, 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">{liveRates.data.unit}</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs uppercase text-muted-foreground">Observed date</p>
                    <p className="mt-1 text-lg font-semibold">
                      {formatDate(liveRates.data.latest_observation_date)}
                    </p>
                    <Badge
                      variant={(liveRates.data.data_freshness_days ?? 0) > 7 ? "warning" : "success"}
                    >
                      {liveRates.data.data_freshness_days ?? "—"} days old
                    </Badge>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs uppercase text-muted-foreground">Live observations</p>
                    <p className="mt-1 text-2xl font-semibold">{rankedRates.length}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      Commodity: {liveRates.data.commodity_query}
                    </p>
                  </div>
                </div>

                <div className="overflow-hidden rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {isRegional ? <TableHead>State</TableHead> : null}
                        <TableHead>Market</TableHead>
                        <TableHead>District</TableHead>
                        <TableHead>Variety / grade</TableHead>
                        <TableHead>Observed</TableHead>
                        <TableHead className="text-right">Min</TableHead>
                        <TableHead className="text-right">Modal</TableHead>
                        <TableHead className="text-right">Max</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rankedRates.map((row, index) => (
                        <TableRow key={`${row.market}-${row.variety}-${row.date}-${index}`}>
                          {isRegional ? <TableCell>{row.state || "—"}</TableCell> : null}
                          <TableCell className="font-medium">{row.market || "—"}</TableCell>
                          <TableCell>{row.district || "—"}</TableCell>
                          <TableCell>
                            {row.variety} / {row.grade}
                          </TableCell>
                          <TableCell>{formatDate(row.date)}</TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(row.min_price, 0)}
                          </TableCell>
                          <TableCell className="text-right font-semibold">
                            {formatCurrency(row.modal_price, 0)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(row.max_price, 0)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                <p className="text-xs text-muted-foreground">
                  Source:{" "}
                  <a
                    href={liveRates.data.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline underline-offset-2"
                  >
                    {liveRates.data.source_name}
                  </a>{" "}
                  · Licence: {liveRates.data.license} · Feed updated:{" "}
                  {formatDateTime(liveRates.data.fetched_at)}
                </p>
                <Alert variant="info">
                  {liveRates.data.disclaimer} {liveRates.data.coverage_note}
                </Alert>
                  </div>
                </details>
              </>
            ) : (
              <EmptyState
                title="No live rates"
                description="Select a crop and state, then use Refresh to fetch current mandi rates."
                icon={<Radio className="h-8 w-8" />}
              />
            )}
          </CardContent>
        </Card>
      ) : null}

      {tab === "prices" ? (
        <>
          {prices.isLoading ? (
            <LoadingBlock label="Loading mandi prices…" />
          ) : prices.isError ? (
            <Alert variant="error">{(prices.error as Error).message}</Alert>
          ) : prices.data && prices.data.points.length > 0 ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Latest modal price</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatCurrency(prices.data.points.at(-1)?.modal_price, 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">per quintal</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Latest observation</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatDate(prices.data.latest_observation_date)}
                    </p>
                    <div className="mt-1 flex items-center gap-1 text-xs">
                      <Badge
                        variant={
                          (prices.data.data_freshness_days ?? 0) > 90 ? "warning" : "success"
                        }
                      >
                        {prices.data.data_freshness_days ?? "—"} days old
                      </Badge>
                      <DemoBadge show={prices.data.is_demo} />
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Day-on-day change</p>
                    <p className="mt-1 flex items-center gap-1 text-2xl font-semibold">
                      {change === null ? (
                        "—"
                      ) : change >= 0 ? (
                        <ArrowUpRight className="h-5 w-5 text-emerald-600" />
                      ) : (
                        <ArrowDownRight className="h-5 w-5 text-rose-600" />
                      )}
                      {change === null ? "" : `${(change * 100).toFixed(1)}%`}
                    </p>
                    <p className="text-xs text-muted-foreground">vs previous observation</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Selected market</p>
                    <p className="mt-1 truncate text-lg font-semibold">
                      {prices.data.market ?? "—"}
                    </p>
                    <p className="text-xs text-muted-foreground">{prices.data.source}</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <LineChartIcon className="h-4 w-4 text-primary" /> {prices.data.crop} price series
                  </CardTitle>
                  <CardDescription>
                    Modal price with observed min–max band · {prices.data.unit}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={series}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8e5" />
                        <XAxis
                          dataKey="date"
                          fontSize={11}
                          tickFormatter={(value: string) => formatDate(value)}
                          minTickGap={40}
                        />
                        <YAxis fontSize={11} width={60} />
                        <Tooltip
                          labelFormatter={(value: string) => formatDate(value)}
                          formatter={(value: number, name: string) => [
                            formatCurrency(value, 0),
                            titleCase(name),
                          ]}
                        />
                        <Area
                          type="monotone"
                          dataKey="high"
                          stroke="none"
                          fill={CHART_COLORS.band}
                          fillOpacity={0.12}
                        />
                        <Area
                          type="monotone"
                          dataKey="low"
                          stroke="none"
                          fill="#ffffff"
                          fillOpacity={1}
                        />
                        <Line
                          type="monotone"
                          dataKey="modal"
                          stroke={CHART_COLORS.modal}
                          strokeWidth={2}
                          dot={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {prices.data.points.length} observations. Source: {prices.data.source ?? "Agmarknet"}.
                  </p>
                </CardContent>
              </Card>
            </>
          ) : (
            <EmptyState
              title="No price observations"
              description="Import an Agmarknet CSV to populate market prices for this crop."
              icon={<Store className="h-8 w-8" />}
            />
          )}
        </>
      ) : null}

      {tab === "markets" ? (
        <Card>
          <CardHeader>
            <CardTitle>Market comparison</CardTitle>
            <CardDescription>
              Latest modal price by mandi for {activeCrop}. Best market:{" "}
              {trends.data?.best_market ?? "—"}
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {trends.isLoading ? (
              <LoadingBlock />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Market</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Latest date</TableHead>
                    <TableHead className="text-right">Modal</TableHead>
                    <TableHead className="text-right">Min</TableHead>
                    <TableHead className="text-right">Max</TableHead>
                    <TableHead className="text-right">Obs.</TableHead>
                    <TableHead>Signal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(trends.data?.rows ?? []).length > 0 ? (
                    trends.data!.rows.map((row) => (
                      <TableRow key={`${row.market}-${row.state}`}>
                        <TableCell className="font-medium">{row.market}</TableCell>
                        <TableCell>{row.state}</TableCell>
                        <TableCell>{formatDate(row.latest_date)}</TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(row.modal_price, 0)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(row.min_price, 0)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(row.max_price, 0)}
                        </TableCell>
                        <TableCell className="text-right">{row.observations}</TableCell>
                        <TableCell>
                          {row.market === trends.data?.best_market ? (
                            <Badge variant="success">best price</Badge>
                          ) : trends.data?.average_modal_price &&
                            row.modal_price >= trends.data.average_modal_price ? (
                            <Badge variant="info">above average</Badge>
                          ) : (
                            <Badge variant="secondary">below average</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableEmpty colSpan={8} message="No markets available for this crop." />
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}

      {tab === "forecast" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex-row items-end justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" /> Generate forecast
                </CardTitle>
                <CardDescription>
                  Models are fitted at request time on the chronological series.
                </CardDescription>
              </div>
              <div className="flex items-end gap-2">
                <Field label="Horizon" className="w-28">
                  <Select value={horizon} onChange={(event) => setHorizon(event.target.value)}>
                    {["7", "14", "21", "30", "60"].map((value) => (
                      <option key={value} value={value}>
                        {value}d
                      </option>
                    ))}
                  </Select>
                </Field>
                <Button onClick={() => forecast.mutate()} loading={forecast.isPending}>
                  <CloudDownload className="h-4 w-4" /> Forecast
                </Button>
              </div>
            </CardHeader>
            {forecast.isError ? (
              <CardContent>
                <Alert variant="warning">{(forecast.error as Error).message}</Alert>
              </CardContent>
            ) : null}
          </Card>

          {activeForecast ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Expected price</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatCurrency(activeForecast.expected_price, 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {activeForecast.horizon_days}-day ahead · INR/quintal
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Interval</p>
                    <p className="mt-1 text-lg font-semibold">
                      {formatCurrency(activeForecast.lower_bound, 0)} –{" "}
                      {formatCurrency(activeForecast.upper_bound, 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {activeForecast.interval_method ?? "empirical residual"}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Model</p>
                    <p className="mt-1 text-lg font-semibold">{activeForecast.model_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {activeForecast.is_experimental ? "experimental" : "validated"}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs uppercase text-muted-foreground">Data freshness</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {activeForecast.data_freshness_days}d
                    </p>
                    <p className="text-xs text-muted-foreground">
                      latest {formatDate(activeForecast.latest_observation_date)}
                    </p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Gauge className="h-4 w-4 text-primary" /> Forecast path
                  </CardTitle>
                  <CardDescription>
                    {activeForecast.market} · {activeForecast.crop}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={activeForecast.points}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8e5" />
                        <XAxis
                          dataKey="date"
                          fontSize={11}
                          tickFormatter={(value: string) => formatDate(value)}
                        />
                        <YAxis fontSize={11} width={60} />
                        <Tooltip
                          labelFormatter={(value: string) => formatDate(value)}
                          formatter={(value: number, name: string) => [
                            formatCurrency(value, 0),
                            titleCase(name),
                          ]}
                        />
                        <Area
                          type="monotone"
                          dataKey="upper_bound"
                          stroke="none"
                          fill={CHART_COLORS.band}
                          fillOpacity={0.15}
                        />
                        <Area
                          type="monotone"
                          dataKey="lower_bound"
                          stroke="none"
                          fill="#ffffff"
                          fillOpacity={1}
                        />
                        <Line
                          type="monotone"
                          dataKey="expected_price"
                          stroke={CHART_COLORS.expected}
                          strokeWidth={2}
                          dot={false}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <Alert variant="info" className="mt-3">
                    {activeForecast.disclaimer}
                  </Alert>
                </CardContent>
              </Card>

              {activeForecast.model_comparison.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Model comparison</CardTitle>
                    <CardDescription>Chronological tail validation</CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Model</TableHead>
                          <TableHead className="text-right">MAE</TableHead>
                          <TableHead className="text-right">RMSE</TableHead>
                          <TableHead className="text-right">MAPE</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {activeForecast.model_comparison.map((row, index) => (
                          <TableRow key={String(row.model ?? index)}>
                            <TableCell className="font-medium">
                              {String(row.model ?? "—")}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatNumber(row.mae as number, 2)}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatNumber(row.rmse as number, 2)}
                            </TableCell>
                            <TableCell className="text-right">
                              {row.mape === null || row.mape === undefined
                                ? "—"
                                : `${formatNumber(row.mape as number, 2)}%`}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              ) : null}

              <Card>
                <CardHeader>
                  <CardTitle>Forecast points</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Expected</TableHead>
                        <TableHead className="text-right">Lower</TableHead>
                        <TableHead className="text-right">Upper</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {activeForecast.points.map((point: ForecastPoint) => (
                        <TableRow key={point.date}>
                          <TableCell>{formatDate(point.date)}</TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(point.expected_price, 0)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(point.lower_bound, 0)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(point.upper_bound, 0)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          ) : (
            <EmptyState
              title="No forecast yet"
              description="Choose a crop and horizon, then generate a forecast. At least 21 observations are required."
              icon={<TrendingUp className="h-8 w-8" />}
            />
          )}

          {forecasts.data && forecasts.data.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Saved forecasts</CardTitle>
                <CardDescription>Most recent first</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Market</TableHead>
                      <TableHead className="text-right">Horizon</TableHead>
                      <TableHead className="text-right">Expected</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Generated</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {forecasts.data.slice(0, 10).map((row) => (
                      <TableRow key={row.id ?? `${row.market}-${row.generated_at}`}>
                        <TableCell className="font-medium">{row.market}</TableCell>
                        <TableCell className="text-right">{row.horizon_days}d</TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(row.expected_price, 0)}
                        </TableCell>
                        <TableCell>{row.model_name}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDate(row.generated_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}

      <Dialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Agmarknet CSV"
        description="Columns: crop, market, state, district, price_date, min_price, max_price, modal_price."
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setImportOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => importPrices.mutate()}
              loading={importPrices.isPending}
              disabled={csv.trim().length < 10}
            >
              <Upload className="h-4 w-4" /> Import
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Source label">
            <Input value={source} onChange={(event) => setSource(event.target.value)} />
          </Field>
          <Field
            label="CSV content"
            hint="Paste the CSV text. Rows that fail validation are reported and skipped."
          >
            <Textarea
              className="min-h-56 font-mono text-xs"
              value={csv}
              onChange={(event) => setCsv(event.target.value)}
              placeholder="crop,market,state,district,price_date,min_price,max_price,modal_price"
            />
          </Field>
          <div className="rounded-lg bg-secondary/60 p-3 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Expected schema</p>
            <p className="mt-1 font-mono">
              crop,market,state,district,price_date,min_price,max_price,modal_price
            </p>
            <p className="mt-1">
              Optional: variety, grade, unit. Prices must be INR per quintal.
            </p>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
