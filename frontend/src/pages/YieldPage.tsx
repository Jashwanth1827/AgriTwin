import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  Gauge,
  History,
  LineChart as LineChartIcon,
  Sparkles,
  Wheat,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "../lib/api";
import { useCrops, useFarms } from "../hooks/useReference";
import { formatDate, formatNumber, formatPercent, titleCase } from "../lib/utils";
import type {
  HarvestReadiness,
  YieldHistory,
  YieldModelInfo,
  YieldPrediction,
  YieldPredictionDetail,
} from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Select } from "../components/ui/input";
import { Alert, EmptyState, KeyValue, LoadingBlock, PageHeader, Progress } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

function readinessVariant(status: string) {
  if (status === "ready" || status === "in_window") return "success" as const;
  if (status === "late" || status === "past_window") return "danger" as const;
  if (status === "approaching") return "warning" as const;
  return "secondary" as const;
}

function ReadinessCard({ readiness }: { readiness: HarvestReadiness }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-primary" /> Harvest readiness
        </CardTitle>
        <CardDescription>{readiness.calendar_source}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={readinessVariant(readiness.readiness_status)}>
            {titleCase(readiness.readiness_status)}
          </Badge>
          <Badge variant="outline">confidence {formatPercent(readiness.confidence)}</Badge>
          {readiness.estimated_days_remaining !== null ? (
            <Badge variant="info">{readiness.estimated_days_remaining} days remaining</Badge>
          ) : null}
        </div>
        <div>
          <KeyValue label="Sowing date" value={formatDate(readiness.sowing_date)} />
          <KeyValue label="Expected harvest" value={formatDate(readiness.expected_harvest_date)} />
          <KeyValue
            label="Harvest window"
            value={`${formatDate(readiness.harvest_window_start)} → ${formatDate(readiness.harvest_window_end)}`}
          />
          <KeyValue label="Crop" value={readiness.crop} />
        </div>
        <p className="text-sm text-muted-foreground">{readiness.notes}</p>
        {readiness.weather_considerations.length > 0 ? (
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
            {readiness.weather_considerations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PredictionDetail({
  data,
  model,
}: {
  data: YieldPredictionDetail;
  model: YieldModelInfo | undefined;
}) {
  const prediction = data.prediction;
  const hasInterval =
    prediction.lower_total_quintals !== null && prediction.upper_total_quintals !== null;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-primary/5 p-4 md:col-span-2">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Predicted production</p>
          <p className="mt-1 text-3xl font-semibold">
            {formatNumber(prediction.predicted_total_quintals, 1)}{" "}
            <span className="text-base font-normal text-muted-foreground">quintals</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {formatNumber(prediction.predicted_yield_per_hectare, 1)} quintals/hectare
          </p>
          {hasInterval ? (
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>
                  80% interval: {formatNumber(prediction.lower_total_quintals, 0)} –{" "}
                  {formatNumber(prediction.upper_total_quintals, 0)} q
                </span>
                <span>{prediction.interval_method}</span>
              </div>
              <div className="flex h-2 overflow-hidden rounded-full bg-secondary">
                <div className="h-full flex-1 bg-primary/25" />
                <div className="h-full flex-1 bg-primary" />
                <div className="h-full flex-1 bg-primary/25" />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Empirical coverage {formatPercent(prediction.interval_coverage, 1)} on the
                chronological test year.
              </p>
            </div>
          ) : null}
        </div>
        <div className="space-y-2 rounded-xl border p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Model confidence</p>
          <p className="text-2xl font-semibold">{formatPercent(prediction.confidence)}</p>
          <Progress value={prediction.confidence} />
          <p className="text-xs text-muted-foreground">
            Input completeness {formatPercent(prediction.input_completeness)}
          </p>
          <Progress value={prediction.input_completeness} className="h-1.5" />
          <div className="flex flex-wrap gap-1 pt-2">
            <Badge variant="secondary">{prediction.model_name}</Badge>
            {prediction.is_experimental ? <Badge variant="warning">experimental</Badge> : null}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ReadinessCard readiness={data.harvest_readiness} />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-primary" /> Model card
            </CardTitle>
            <CardDescription>{prediction.model_version}</CardDescription>
          </CardHeader>
          <CardContent>
            {model?.metrics ? (
              <div className="space-y-0">
                {Object.entries(model.metrics).map(([key, value]) => (
                  <KeyValue
                    key={key}
                    label={titleCase(key)}
                    value={typeof value === "number" ? formatNumber(value, 4) : String(value ?? "—")}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No model metrics available.</p>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              {model?.dataset_provenance ?? "Public crop-production statistics."}
            </p>
          </CardContent>
        </Card>
      </div>

      {prediction.notes ? <Alert variant="info">{prediction.notes}</Alert> : null}
    </div>
  );
}

export default function YieldPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const [farmId, setFarmId] = useState<number | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<YieldPredictionDetail | null>(null);
  const [historyCrop, setHistoryCrop] = useState("Rice");

  const activeFarmId = farmId ?? farms.data?.[0]?.id ?? null;
  const crops = useCrops(activeFarmId ?? undefined);
  const activeCropId = cropId ?? crops.data?.[0]?.id ?? null;
  const activeCrop = crops.data?.find((crop) => crop.id === activeCropId) ?? null;

  const model = useQuery({
    queryKey: ["yield-model"],
    queryFn: () => api.get<YieldModelInfo>("/yield/model"),
  });

  const predictions = useQuery({
    queryKey: ["yield-predictions"],
    queryFn: () => api.get<YieldPrediction[]>("/yield/predictions"),
  });

  const history = useQuery({
    queryKey: ["yield-history", historyCrop],
    queryFn: () => api.get<YieldHistory>(`/yield/history?crop=${encodeURIComponent(historyCrop)}`),
    enabled: historyCrop.length > 0,
  });

  const predict = useMutation({
    mutationFn: async () => {
      if (activeFarmId === null || activeCropId === null) {
        throw new Error("Select a farm and crop first");
      }
      return api.post<YieldPredictionDetail>("/yield/predict", {
        farm_id: activeFarmId,
        crop_id: activeCropId,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["yield-predictions"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const historyChart = useMemo(
    () =>
      (history.data?.years ?? []).map((row) => ({
        year: row.year,
        yield: row.yield_per_hectare,
      })),
    [history.data],
  );

  const cropOptions = useMemo(() => {
    const names = new Set<string>();
    (crops.data ?? []).forEach((crop) => names.add(crop.crop_name));
    return Array.from(names).sort();
  }, [crops.data]);

  if (farms.isLoading) return <LoadingBlock label="Loading yield workspace…" />;
  if (farms.isError) return <Alert variant="error">{(farms.error as Error).message}</Alert>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Yield & harvest"
        description="Estimate production with an uncertainty interval, then plan harvest timing."
        actions={
          <Button
            size="sm"
            onClick={() => predict.mutate()}
            loading={predict.isPending}
            disabled={activeCropId === null}
          >
            <Sparkles className="h-4 w-4" /> Predict yield
          </Button>
        }
      />

      {model.data ? (
        <Alert
          variant={model.data.available ? "success" : "warning"}
          title={
            model.data.available
              ? `Yield model ready: ${model.data.model_name} (${model.data.model_version})`
              : "Yield model artifact is unavailable"
          }
        >
          {model.data.message ??
            `Chronological validation with ${model.data.interval_method ?? "split-conformal"} intervals. ${model.data.dataset_provenance ?? ""}`}
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="error" title="Prediction failed">
          {error}
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wheat className="h-4 w-4 text-primary" /> Prediction inputs
            </CardTitle>
            <CardDescription>Uses farm area, soil data and crop calendar.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Farm">
              <Select
                value={activeFarmId ?? ""}
                onChange={(event) => {
                  setFarmId(Number(event.target.value));
                  setCropId(null);
                  setResult(null);
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
                onChange={(event) => {
                  setCropId(Number(event.target.value));
                  setResult(null);
                }}
              >
                {(crops.data ?? []).map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.crop_name} · {crop.area_hectares} ha
                  </option>
                ))}
              </Select>
            </Field>
            {activeCrop ? (
              <div className="space-y-0 rounded-lg bg-secondary/50 p-3">
                <KeyValue label="Area" value={`${formatNumber(activeCrop.area_hectares, 2)} ha`} />
                <KeyValue label="Sowing" value={formatDate(activeCrop.sowing_date)} />
                <KeyValue label="Stage" value={activeCrop.growth_stage ?? "—"} />
                <KeyValue label="Season" value={activeCrop.season} />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Add a crop to the selected farm to run a prediction.
              </p>
            )}
            <Button
              className="w-full"
              onClick={() => predict.mutate()}
              loading={predict.isPending}
              disabled={activeCropId === null}
            >
              <Sparkles className="h-4 w-4" /> Run prediction
            </Button>
          </CardContent>
        </Card>

        <div>
          {result ? (
            <PredictionDetail data={result} model={model.data} />
          ) : (
            <Card className="h-full">
              <CardContent className="flex h-full items-center justify-center py-16">
                <EmptyState
                  title="No prediction in this session"
                  description="Select a farm and crop, then run the model to see expected production and its 80% interval."
                  icon={<Wheat className="h-8 w-8" />}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <History className="h-4 w-4 text-primary" /> Historical yield
              </CardTitle>
              <CardDescription>Public statistics, quintals per hectare</CardDescription>
            </div>
            <Select
              className="w-40"
              value={historyCrop}
              onChange={(event) => setHistoryCrop(event.target.value)}
            >
              {(cropOptions.length > 0 ? cropOptions : ["Rice", "Wheat", "Onion", "Tomato"]).map(
                (crop) => (
                  <option key={crop} value={crop}>
                    {crop}
                  </option>
                ),
              )}
            </Select>
          </CardHeader>
          <CardContent>
            {history.isLoading ? (
              <LoadingBlock label="Loading history…" />
            ) : historyChart.length === 0 ? (
              <EmptyState title="No historical rows" description="This crop is not in the bundled dataset." />
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={historyChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8e5" />
                    <XAxis dataKey="year" fontSize={11} />
                    <YAxis fontSize={11} width={48} />
                    <Tooltip
                      formatter={(value: number) => [`${formatNumber(value, 1)} q/ha`, "Yield"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="yield"
                      stroke="#1f7a4d"
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LineChartIcon className="h-4 w-4 text-primary" /> Prediction history
            </CardTitle>
            <CardDescription>Saved model runs for your account</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Crop</TableHead>
                  <TableHead className="text-right">Total (q)</TableHead>
                  <TableHead className="text-right">80% interval</TableHead>
                  <TableHead className="text-right">Completeness</TableHead>
                  <TableHead>When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {predictions.data && predictions.data.length > 0 ? (
                  predictions.data.slice(0, 8).map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">
                        {crops.data?.find((crop) => crop.id === row.crop_id)?.crop_name ??
                          `Crop #${row.crop_id}`}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(row.predicted_total_quintals, 1)}
                      </TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground">
                        {formatNumber(row.lower_total_quintals, 0)}–{formatNumber(row.upper_total_quintals, 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPercent(row.input_completeness)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(row.predicted_at)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableEmpty colSpan={5} message="No predictions yet." />
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {historyChart.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Yield by year</CardTitle>
            <CardDescription>
              {history.data?.crop} · {history.data?.state ?? "All India"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={historyChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8e5" />
                  <XAxis dataKey="year" fontSize={11} />
                  <YAxis fontSize={11} width={48} />
                  <Tooltip formatter={(value: number) => [`${formatNumber(value, 1)} q/ha`, "Yield"]} />
                  <Bar dataKey="yield" fill="#2f9e68" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
