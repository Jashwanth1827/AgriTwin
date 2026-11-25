import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRightLeft,
  BadgeCheck,
  Clock,
  Info,
  RefreshCw,
  Scale,
  Sparkles,
  Trash2,
} from "lucide-react";

import { api } from "../lib/api";
import { useCrops, useFarms, useOptions } from "../hooks/useReference";
import { formatCurrency, formatDateTime, formatNumber, formatPercent, titleCase } from "../lib/utils";
import type {
  BuyerEvaluation,
  Decision,
  DecisionFactor,
  DecisionListItem,
} from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/input";
import {
  ActionBadge,
  Alert,
  DemoBadge,
  EmptyState,
  KeyValue,
  LoadingBlock,
  PageHeader,
  Progress,
  RiskBadge,
  Tabs,
} from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

function actionCopy(action: string) {
  if (action === "SELL") return "Sell now through the selected channel.";
  if (action === "WAIT") return "Hold and re-check when the expected price gain beats storage risk.";
  return "Inspect the crop before committing to a sale.";
}

function FactorRow({ factor }: { factor: DecisionFactor }) {
  return (
    <div className="border-b py-2.5 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{titleCase(factor.factor)}</p>
          <p className="text-xs text-muted-foreground">{factor.description}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {factor.value !== null ? (
            <span className="text-xs text-muted-foreground">{formatNumber(factor.value, 2)}</span>
          ) : null}
          <Badge
            variant={
              factor.direction === "increases_risk"
                ? "danger"
                : factor.direction === "reduces_risk"
                  ? "success"
                  : "secondary"
            }
          >
            {factor.direction.replaceAll("_", " ")}
          </Badge>
        </div>
      </div>
      {factor.weight !== null ? (
        <div className="mt-1 flex items-center gap-2">
          <Progress value={factor.weight} className="h-1.5 max-w-48" />
          <span className="text-[11px] text-muted-foreground">
            weight {formatPercent(factor.weight, 0)}
          </span>
        </div>
      ) : null}
    </div>
  );
}

function EvaluationTable({ rows }: { rows: BuyerEvaluation[] }) {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No buyer offers were evaluated. The mandi channel is used as the fallback.
      </p>
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Rank</TableHead>
          <TableHead>Buyer</TableHead>
          <TableHead className="text-right">Offer</TableHead>
          <TableHead className="text-right">Distance</TableHead>
          <TableHead className="text-right">Transport</TableHead>
          <TableHead className="text-right">Net / q</TableHead>
          <TableHead className="text-right">Risk</TableHead>
          <TableHead>Eligibility</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={`${row.buyer_id}-${row.offer_id}`}>
            <TableCell className="font-medium">{row.rank ?? "—"}</TableCell>
            <TableCell>
              <p className="font-medium">{row.buyer_name}</p>
              {row.buyer_is_demo ? <DemoBadge show /> : null}
            </TableCell>
            <TableCell className="text-right">
              {formatCurrency(row.offered_price_per_quintal, 0)}
            </TableCell>
            <TableCell className="text-right">
              {row.distance_km === null ? "—" : `${formatNumber(row.distance_km, 0)} km`}
            </TableCell>
            <TableCell className="text-right">
              {formatCurrency(row.transport_cost, 0)}
            </TableCell>
            <TableCell className="text-right font-medium">
              {formatCurrency(row.net_realization_per_quintal, 0)}
            </TableCell>
            <TableCell className="text-right">{formatNumber(row.risk_score, 2)}</TableCell>
            <TableCell>
              {row.eligible ? (
                <Badge variant="success">eligible</Badge>
              ) : (
                <div className="space-y-1">
                  <Badge variant="secondary">ineligible</Badge>
                  <p className="max-w-48 text-[11px] text-muted-foreground">
                    {row.ineligibility_reasons.join("; ")}
                  </p>
                </div>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DecisionDetail({ decision }: { decision: Decision }) {
  const channel = (decision.outputs?.channel as string | undefined) ?? "mandi";
  const wait = decision.outputs?.wait_scenario as
    | { expected_net?: number; relative_change?: number; horizon_days?: number }
    | undefined;
  const freshness = decision.data_freshness ?? {};

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <ActionBadge action={decision.action} />
              <RiskBadge category={decision.risk_category} />
              <Badge variant="outline">confidence {formatPercent(decision.confidence)}</Badge>
              <Badge variant="secondary">policy {decision.policy_version}</Badge>
            </div>
            <CardTitle className="mt-3 text-xl">
              {actionCopy(decision.action)}
            </CardTitle>
            <CardDescription>
              Generated {formatDateTime(decision.generated_at)} · decision #{decision.id}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{decision.explanation}</p>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border bg-primary/5 p-4">
              <p className="text-xs uppercase text-muted-foreground">Net realisation</p>
              <p className="mt-1 text-2xl font-semibold">
                {formatCurrency(decision.net_realization, 0)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatCurrency(decision.net_realization_per_quintal, 0)}/quintal
              </p>
            </div>
            <div className="rounded-xl border p-4">
              <p className="text-xs uppercase text-muted-foreground">Channel</p>
              <p className="mt-1 truncate text-lg font-semibold">
                {decision.selected_buyer_name ?? "Mandi"}
              </p>
              <p className="text-xs text-muted-foreground">
                {channel === "buyer" ? "buyer offer" : "mandi sale"}
              </p>
            </div>
            <div className="rounded-xl border p-4">
              <p className="text-xs uppercase text-muted-foreground">Expected yield</p>
              <p className="mt-1 text-2xl font-semibold">
                {formatNumber(decision.expected_yield_quintals, 1)} q
              </p>
              <p className="text-xs text-muted-foreground">
                {formatNumber(decision.yield_low_quintals, 0)}–{formatNumber(decision.yield_high_quintals, 0)} q (80%)
              </p>
            </div>
            <div className="rounded-xl border p-4">
              <p className="text-xs uppercase text-muted-foreground">Risk score</p>
              <p className="mt-1 text-2xl font-semibold">{formatNumber(decision.risk_score, 2)}</p>
              <p className="text-xs text-muted-foreground">
                data completeness {formatPercent(decision.data_completeness)}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Money flow</p>
              <KeyValue label="Gross revenue" value={formatCurrency(decision.gross_revenue, 0)} />
              <KeyValue label="Transport cost" value={formatCurrency(decision.transport_cost, 0)} />
              <KeyValue label="Other selling costs" value={formatCurrency(decision.other_costs, 0)} />
              <KeyValue
                label="Net realisation"
                value={formatCurrency(decision.net_realization, 0)}
              />
              <KeyValue
                label="Price basis"
                value={`${formatCurrency(decision.expected_price_per_quintal, 0)}/q (${formatCurrency(
                  decision.price_low_per_quintal,
                  0,
                )}–${formatCurrency(decision.price_high_per_quintal, 0)})`}
              />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
                Wait scenario
              </p>
              {wait ? (
                <>
                  <KeyValue
                    label="Expected net if waiting"
                    value={formatCurrency(wait.expected_net ?? decision.wait_expected_net, 0)}
                  />
                  <KeyValue
                    label="Forecast relative move"
                    value={
                      wait.relative_change === undefined
                        ? "—"
                        : `${(wait.relative_change * 100).toFixed(1)}%`
                    }
                  />
                  <KeyValue label="Horizon" value={`${wait.horizon_days ?? "—"} days`} />
                </>
              ) : (
                <p className="py-2 text-sm text-muted-foreground">
                  No forecast-backed wait scenario was computed for this run.
                </p>
              )}
              <p className="mb-1 mt-4 text-xs font-semibold uppercase text-muted-foreground">
                Data freshness
              </p>
              <KeyValue
                label="Market age"
                value={
                  freshness.market_age_days !== undefined
                    ? `${freshness.market_age_days} days`
                    : "—"
                }
              />
              <KeyValue
                label="Price source"
                value={String(freshness.price_source ?? "—")}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-4 w-4 text-primary" /> Risk factors
            </CardTitle>
            <CardDescription>Weighted contributions to the final risk score</CardDescription>
          </CardHeader>
          <CardContent>
            {decision.factors.length > 0 ? (
              decision.factors.map((factor) => <FactorRow key={factor.factor} factor={factor} />)
            ) : (
              <p className="text-sm text-muted-foreground">No factor breakdown available.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-4 w-4 text-primary" /> Assumptions & missing inputs
            </CardTitle>
            <CardDescription>What the engine had to assume</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {decision.assumptions.length > 0 ? (
              <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                {decision.assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No assumptions recorded.</p>
            )}
            {decision.missing_inputs.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  Missing inputs
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {decision.missing_inputs.map((item) => (
                    <Badge key={item} variant="warning">
                      {titleCase(item)}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ArrowRightLeft className="h-4 w-4 text-primary" /> Buyer channel comparison
          </CardTitle>
          <CardDescription>
            Net realisation after transport, commission and other selling costs. Ineligible offers are
            shown but never selected.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <EvaluationTable rows={decision.buyer_evaluations} />
        </CardContent>
      </Card>
    </div>
  );
}

export default function DecisionsPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const options = useOptions();
  const [farmId, setFarmId] = useState<number | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [risk, setRisk] = useState("medium");
  const [quantity, setQuantity] = useState("");
  const [marketName, setMarketName] = useState("");
  const [vehicleType, setVehicleType] = useState("truck");
  const [tab, setTab] = useState("new");
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [created, setCreated] = useState<Decision | null>(null);

  const activeFarmId = farmId ?? farms.data?.[0]?.id ?? null;
  const crops = useCrops(activeFarmId ?? undefined);
  const activeCropId = cropId ?? crops.data?.[0]?.id ?? null;

  const decisions = useQuery({
    queryKey: ["decisions"],
    queryFn: () => api.get<DecisionListItem[]>("/decisions"),
  });

  const detail = useQuery({
    queryKey: ["decision", selectedId],
    queryFn: () => api.get<Decision>(`/decisions/${selectedId}`),
    enabled: selectedId !== null,
  });

  const create = useMutation({
    mutationFn: () => {
      if (activeFarmId === null || activeCropId === null) {
        throw new Error("Select a farm and crop");
      }
      return api.post<Decision>("/decisions", {
        farm_id: activeFarmId,
        crop_id: activeCropId,
        risk_preference: risk,
        quantity_quintals: quantity.trim() ? Number(quantity) : undefined,
        market_name: marketName.trim() || undefined,
        vehicle_type: vehicleType,
      });
    },
    onSuccess: (data) => {
      setCreated(data);
      setSelectedId(data.id);
      setError(null);
      setTab("detail");
      void queryClient.invalidateQueries({ queryKey: ["decisions"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/decisions/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      void queryClient.invalidateQueries({ queryKey: ["decisions"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const shown = detail.data ?? created;

  const farmName = useMemo(() => {
    const map = new Map((farms.data ?? []).map((farm) => [farm.id, farm.name]));
    return (id: number) => map.get(id) ?? `Farm #${id}`;
  }, [farms.data]);

  if (farms.isLoading) return <LoadingBlock label="Loading decision workspace…" />;
  if (farms.isError) return <Alert variant="error">{(farms.error as Error).message}</Alert>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Decisions"
        description="The central engine: deterministic, explainable SELL / WAIT / INSPECT with money arithmetic and risk decomposition."
        actions={
          <Tabs
            tabs={[
              { value: "new", label: "New decision" },
              { value: "detail", label: "Detail" },
              { value: "history", label: "History" },
            ]}
            value={tab}
            onChange={setTab}
          />
        }
      />

      {error ? (
        <Alert variant="error" title="Decision request failed">
          {error}
        </Alert>
      ) : null}

      {tab === "new" ? (
        <div className="grid gap-4 lg:grid-cols-[400px_1fr]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" /> Run the engine
              </CardTitle>
              <CardDescription>
                The engine auto-computes yield, market forecast and transport when inputs are missing.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="Farm">
                <Select
                  value={activeFarmId ?? ""}
                  onChange={(event) => {
                    setFarmId(Number(event.target.value));
                    setCropId(null);
                  }}
                >
                  {(farms.data ?? []).map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Crop">
                <Select
                  value={activeCropId ?? ""}
                  onChange={(event) => setCropId(Number(event.target.value))}
                >
                  {(crops.data ?? []).map((crop) => (
                    <option key={crop.id} value={crop.id}>
                      {crop.crop_name} · {crop.area_hectares} ha
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Risk preference" hint="Caps the risk-adjusted ranking and wait tolerance.">
                <Select value={risk} onChange={(event) => setRisk(event.target.value)}>
                  {(options.data?.risk_preferences ?? ["low", "medium", "high"]).map((value) => (
                    <option key={value} value={value}>
                      {titleCase(value)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Quantity override (quintals)" hint="Leave blank to use the yield estimate.">
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  placeholder="Auto from yield model"
                />
              </Field>
              <Field label="Market override" hint="Optional mandi name for price comparison.">
                <Input
                  value={marketName}
                  onChange={(event) => setMarketName(event.target.value)}
                  placeholder="Auto-select from crop data"
                />
              </Field>
              <Field label="Vehicle">
                <Select
                  value={vehicleType}
                  onChange={(event) => setVehicleType(event.target.value)}
                >
                  {(options.data?.vehicle_types ?? ["truck"]).map((value) => (
                    <option key={value} value={value}>
                      {titleCase(value)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                className="w-full"
                size="lg"
                onClick={() => create.mutate()}
                loading={create.isPending}
                disabled={activeCropId === null}
              >
                <Scale className="h-4 w-4" /> Generate decision
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BadgeCheck className="h-4 w-4 text-primary" /> How the engine decides
              </CardTitle>
              <CardDescription>Ordered, deterministic rules from the JSON policy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="rounded-lg border p-3">
                <p className="font-medium text-foreground">1 · INSPECT first</p>
                <p>
                  If crop health is poor, confidence is low, harvest is not ready, or data is stale
                  beyond the freshness threshold, the engine refuses to recommend a sale.
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="font-medium text-foreground">2 · WAIT next</p>
                <p>
                  If the forecast-backed wait scenario beats the immediate net by more than the
                  policy margin — and the expected move is large enough — it recommends waiting.
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="font-medium text-foreground">3 · SELL otherwise</p>
                <p>
                  Otherwise it selects the higher of the best eligible buyer offer and the mandi net
                  realisation, after transport and selling costs.
                </p>
              </div>
              <Alert variant="info">
                Money is computed with Decimal half-up rounding. Every factor and assumption is
                persisted with the decision so the output can be audited later.
              </Alert>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "detail" ? (
        shown ? (
          <DecisionDetail decision={shown} />
        ) : (
          <EmptyState
            title="No decision selected"
            description="Generate a decision or open one from history to see its full explanation."
            icon={<Scale className="h-8 w-8" />}
          />
        )
      ) : null}

      {tab === "history" ? (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-primary" /> Decision history
              </CardTitle>
              <CardDescription>Every engine run is stored with its inputs snapshot.</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void decisions.refetch()}
              loading={decisions.isFetching}
            >
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Farm</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead className="text-right">Risk</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {decisions.data && decisions.data.length > 0 ? (
                  decisions.data.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDateTime(row.generated_at)}
                      </TableCell>
                      <TableCell>{farmName(row.farm_id)}</TableCell>
                      <TableCell>
                        <ActionBadge action={row.action} />
                      </TableCell>
                      <TableCell>{row.selected_buyer_name ?? "Mandi"}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(row.net_realization, 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        <RiskBadge category={row.risk_category} />
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedId(row.id);
                              setCreated(null);
                              setTab("detail");
                            }}
                          >
                            View
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete decision"
                            onClick={() => {
                              if (window.confirm("Delete this decision?")) remove.mutate(row.id);
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableEmpty colSpan={7} message="No decisions yet." />
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
              <BadgeCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium">SELL</p>
              <p className="text-xs text-muted-foreground">Move now through the best net channel.</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-amber-100 p-2 text-amber-700">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium">WAIT</p>
              <p className="text-xs text-muted-foreground">Forecast gain exceeds policy margin.</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-sky-100 p-2 text-sky-700">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium">INSPECT</p>
              <p className="text-xs text-muted-foreground">Health, readiness or data quality blocks a sale.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
