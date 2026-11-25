import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FileText,
  Leaf,
  Printer,
  RefreshCw,
  Scale,
  Sparkles,
  Trash2,
  Wheat,
} from "lucide-react";

import { api } from "../lib/api";
import { useCrops, useFarms } from "../hooks/useReference";
import { formatCurrency, formatDate, formatDateTime, formatNumber, formatPercent } from "../lib/utils";
import type { Report } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Select } from "../components/ui/input";
import {
  ActionBadge,
  Alert,
  EmptyState,
  KeyValue,
  LoadingBlock,
  PageHeader,
  RiskBadge,
} from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";

type CropSection = {
  crop: {
    id: number;
    name: string;
    variety: string | null;
    season: string;
    area_hectares: number;
    sowing_date: string;
    expected_harvest_date: string | null;
    status: string;
  };
  harvest_readiness: {
    readiness_status: string;
    estimated_days_remaining: number | null;
    expected_harvest_date: string | null;
    notes: string;
  };
  crop_health: {
    available: boolean;
    label: string | null;
    confidence: number | null;
    is_demo: boolean | null;
    predicted_at: string | null;
  };
  yield: {
    available: boolean;
    predicted_yield_per_hectare: number | null;
    predicted_total_quintals: number | null;
    lower_total_quintals: number | null;
    upper_total_quintals: number | null;
    model_name: string | null;
    interval_method: string | null;
  };
  decision: {
    available: boolean;
    action: string | null;
    selected_buyer_name: string | null;
    net_realization: number | null;
    risk_score: number | null;
    risk_category: string | null;
    explanation: string | null;
  };
};

type MarketSection = {
  crop: string;
  market?: string;
  state?: string;
  latest_modal_price?: number;
  latest_observation_date?: string;
  data_freshness_days?: number;
  source?: string;
  [key: string]: unknown;
};

function ReportBody({ report }: { report: Report }) {
  const payload = report.payload ?? {};
  const farm = payload.farm as
    | { name: string; district: string; state: string; total_area_hectares: number }
    | null
    | undefined;
  const crops = (payload.crops ?? []) as CropSection[];
  const markets = (payload.market ?? []) as MarketSection[];

  return (
    <div className="space-y-5">
      <div className="rounded-lg bg-secondary/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-lg font-semibold">{report.title}</p>
            <p className="text-sm text-muted-foreground">{report.summary}</p>
          </div>
          <Badge variant="secondary">{report.report_type}</Badge>
        </div>
        {farm ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {farm.name} · {farm.district}, {farm.state} · {formatNumber(farm.total_area_hectares, 1)} ha
          </p>
        ) : null}
        <p className="mt-1 text-xs text-muted-foreground">
          Generated {formatDateTime(report.created_at)}
        </p>
      </div>

      {crops.length === 0 ? (
        <p className="text-sm text-muted-foreground">No crops matched this report scope.</p>
      ) : (
        crops.map((section) => (
          <div key={section.crop.id} className="rounded-lg border p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-semibold">
                  {section.crop.name}
                  {section.crop.variety ? ` · ${section.crop.variety}` : ""}
                </p>
                <p className="text-xs text-muted-foreground">
                  {section.crop.season} · {formatNumber(section.crop.area_hectares, 2)} ha · sown{" "}
                  {formatDate(section.crop.sowing_date)}
                </p>
              </div>
              <Badge variant="outline">{section.harvest_readiness.readiness_status}</Badge>
            </div>

            <div className="mt-3 grid gap-4 md:grid-cols-3">
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
                  <Leaf className="h-3 w-3" /> Crop health
                </p>
                {section.crop_health.available ? (
                  <>
                    <p className="text-sm font-medium">
                      {section.crop_health.label?.replaceAll("_", " ")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      confidence {formatPercent(section.crop_health.confidence)}
                    </p>
                    {section.crop_health.is_demo ? <Badge variant="demo">DEMO</Badge> : null}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">No scan recorded.</p>
                )}
              </div>
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
                  <Wheat className="h-3 w-3" /> Yield
                </p>
                {section.yield.available ? (
                  <>
                    <p className="text-sm font-medium">
                      {formatNumber(section.yield.predicted_total_quintals, 1)} q
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatNumber(section.yield.predicted_yield_per_hectare, 1)} q/ha · 80%{" "}
                      {formatNumber(section.yield.lower_total_quintals, 0)}–
                      {formatNumber(section.yield.upper_total_quintals, 0)} q
                    </p>
                    <p className="text-xs text-muted-foreground">{section.yield.model_name}</p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">No yield prediction.</p>
                )}
              </div>
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
                  <Scale className="h-3 w-3" /> Decision
                </p>
                {section.decision.available ? (
                  <>
                    <div className="flex items-center gap-2">
                      <ActionBadge action={section.decision.action} />
                      <RiskBadge category={section.decision.risk_category} />
                    </div>
                    <p className="mt-1 text-sm font-medium">
                      {formatCurrency(section.decision.net_realization, 0)} via{" "}
                      {section.decision.selected_buyer_name ?? "mandi"}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">No decision recorded.</p>
                )}
              </div>
            </div>

            <div className="mt-3">
              <KeyValue
                label="Harvest window"
                value={formatDate(section.harvest_readiness.expected_harvest_date)}
              />
              <KeyValue
                label="Days remaining"
                value={
                  section.harvest_readiness.estimated_days_remaining === null
                    ? "—"
                    : String(section.harvest_readiness.estimated_days_remaining)
                }
              />
              <KeyValue label="Readiness notes" value={section.harvest_readiness.notes} />
            </div>
            {section.decision.explanation ? (
              <p className="mt-2 rounded-md bg-secondary/50 p-2 text-xs text-muted-foreground">
                {section.decision.explanation}
              </p>
            ) : null}
          </div>
        ))
      )}

      {markets.length > 0 ? (
        <div>
          <p className="mb-2 text-sm font-semibold">Market snapshot</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Crop</TableHead>
                <TableHead>Market</TableHead>
                <TableHead>Latest date</TableHead>
                <TableHead className="text-right">Modal</TableHead>
                <TableHead className="text-right">Age</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {markets.map((row, index) => (
                <TableRow key={`${row.crop}-${index}`}>
                  <TableCell className="font-medium">{row.crop}</TableCell>
                  <TableCell>{row.market ?? "—"}</TableCell>
                  <TableCell>{formatDate(row.latest_observation_date)}</TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(row.latest_modal_price, 0)}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.data_freshness_days === undefined ? "—" : `${row.data_freshness_days}d`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {payload.disclaimer ? (
        <Alert variant="info">{String(payload.disclaimer)}</Alert>
      ) : null}
    </div>
  );
}

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const [farmId, setFarmId] = useState<string>("");
  const [cropId, setCropId] = useState<string>("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const crops = useCrops(farmId ? Number(farmId) : undefined);

  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.get<Report[]>("/system/reports"),
  });

  const detail = useQuery({
    queryKey: ["report", selectedId],
    queryFn: () => api.get<Report>(`/system/reports/${selectedId}`),
    enabled: selectedId !== null,
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<Report>("/system/reports", {
        farm_id: farmId ? Number(farmId) : undefined,
        crop_id: cropId ? Number(cropId) : undefined,
      }),
    onMutate: () => {
      setGenerating(true);
      setError(null);
    },
    onSuccess: (report) => {
      setSelectedId(report.id);
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (err: Error) => setError(err.message),
    onSettled: () => setGenerating(false),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/system/reports/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const shown = detail.data ?? reports.data?.find((row) => row.id === selectedId) ?? null;

  const downloadJson = (report: Report) => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `agritwin-report-${report.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const summary = useMemo(() => {
    const rows = reports.data ?? [];
    const advisory = rows.filter((row) => row.report_type.includes("advisory")).length;
    return { total: rows.length, advisory };
  }, [reports.data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Generate a printable advisory snapshot that combines health, yield, market and decision evidence."
        actions={
          <Button
            size="sm"
            onClick={() => create.mutate()}
            loading={generating}
          >
            <Sparkles className="h-4 w-4" /> Generate report
          </Button>
        }
      />

      {error ? (
        <Alert variant="error" title="Report action failed">
          {error}
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" /> Report scope
              </CardTitle>
              <CardDescription>Leave both blank for a portfolio report.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="Farm">
                <Select
                  value={farmId}
                  onChange={(event) => {
                    setFarmId(event.target.value);
                    setCropId("");
                  }}
                >
                  <option value="">All farms (portfolio)</option>
                  {(farms.data ?? []).map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Crop">
                <Select
                  value={cropId}
                  onChange={(event) => setCropId(event.target.value)}
                  disabled={!farmId}
                >
                  <option value="">All crops in scope</option>
                  {(crops.data ?? []).map((crop) => (
                    <option key={crop.id} value={crop.id}>
                      {crop.crop_name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                className="w-full"
                onClick={() => create.mutate()}
                loading={generating}
              >
                <Sparkles className="h-4 w-4" /> Generate
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div>
                <CardTitle>Saved reports</CardTitle>
                <CardDescription>
                  {summary.total} total · {summary.advisory} advisory
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Refresh reports"
                onClick={() => void reports.refetch()}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="max-h-[420px] space-y-2 overflow-y-auto scrollbar-thin">
              {reports.isLoading ? (
                <LoadingBlock />
              ) : reports.data && reports.data.length > 0 ? (
                reports.data.map((report) => (
                  <button
                    key={report.id}
                    type="button"
                    onClick={() => setSelectedId(report.id)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                      report.id === selectedId
                        ? "border-primary bg-primary/5"
                        : "hover:bg-secondary/40"
                    }`}
                  >
                    <p className="truncate text-sm font-medium">{report.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(report.created_at)}
                    </p>
                    <Badge variant="secondary" className="mt-2">
                      {report.report_type}
                    </Badge>
                  </button>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No reports generated yet.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" /> Report preview
              </CardTitle>
              <CardDescription>
                {shown ? `Report #${shown.id}` : "Select or generate a report"}
              </CardDescription>
            </div>
            {shown ? (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => downloadJson(shown)}>
                  <Download className="h-4 w-4" /> JSON
                </Button>
                <Button variant="outline" size="sm" onClick={() => window.print()}>
                  <Printer className="h-4 w-4" /> Print
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (window.confirm("Delete this report?")) remove.mutate(shown.id);
                  }}
                >
                  <Trash2 className="h-4 w-4" /> Delete
                </Button>
              </div>
            ) : null}
          </CardHeader>
          <CardContent>
            {detail.isLoading ? (
              <LoadingBlock label="Loading report…" />
            ) : shown ? (
              <ReportBody report={shown} />
            ) : (
              <EmptyState
                title="No report selected"
                description="Generate a report or pick one from the saved list to preview it here."
                icon={<FileText className="h-8 w-8" />}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
