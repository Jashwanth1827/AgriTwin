import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Leaf,
  LineChart,
  RefreshCw,
  Scale,
  Sprout,
  TrendingUp,
  Wheat,
} from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatCurrency, formatDateTime, formatNumber, formatPercent } from "../lib/utils";
import type { DashboardOverview } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { ActionBadge, Alert, DemoBadge, EmptyState, LoadingBlock, PageHeader, Progress, RiskBadge, StatCard } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const overview = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => api.get<DashboardOverview>("/dashboard/overview"),
  });

  if (overview.isLoading) return <LoadingBlock label="Building your farm overview…" />;
  if (overview.isError) {
    return (
      <Alert variant="error" title="Could not load the dashboard">
        {(overview.error as Error).message}
      </Alert>
    );
  }

  const data = overview.data!;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${user?.full_name?.split(" ")[0] ?? "farmer"}`}
        description="A single view of crop health, expected yield, market conditions and the latest sell / wait / inspect decision."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void overview.refetch()}
              loading={overview.isFetching}
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <Button size="sm" onClick={() => navigate("/decisions")}>
              <Scale className="h-4 w-4" />
              Run a decision
            </Button>
          </>
        }
      />

      {data.is_demo ? (
        <Alert variant="warning" title="This workspace contains demo records">
          Demo farms, buyers and offers are labelled in every table. Market prices and
          historical yields are real public data. {data.notices[0] ?? ""}
        </Alert>
      ) : null}

      {data.notices.length > 0 ? (
        <div className="space-y-2">
          {data.notices.map((notice) => (
            <Alert key={notice} variant="info">
              {notice}
            </Alert>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Farms"
          value={data.total_farms}
          hint={`${formatNumber(data.total_area_hectares, 1)} hectares managed`}
          icon={<Sprout className="h-5 w-5" />}
        />
        <StatCard
          label="Active crops"
          value={data.active_crops}
          hint="Across all farms"
          icon={<Wheat className="h-5 w-5" />}
        />
        <StatCard
          label="Latest market price"
          value={
            data.market.available ? formatCurrency(data.market.latest_price, 0) : "No data"
          }
          hint={
            data.market.available
              ? `${data.market.crop} · ${data.market.market}`
              : "Import or seed market prices"
          }
          icon={<LineChart className="h-5 w-5" />}
          badge={
            data.market.data_freshness_days !== null ? (
              <Badge variant={data.market.data_freshness_days > 90 ? "warning" : "success"}>
                {data.market.data_freshness_days} days old
              </Badge>
            ) : null
          }
        />
        <StatCard
          label="Latest decision"
          value={data.decision.available ? data.decision.action : "None yet"}
          hint={
            data.decision.available
              ? `${data.decision.selected_buyer_name ?? "Mandi"} · ${formatCurrency(
                  data.decision.net_realization,
                  0,
                )} net`
              : "Run the decision engine to get started"
          }
          icon={<Scale className="h-5 w-5" />}
          badge={data.decision.available ? <RiskBadge category={data.decision.risk_category} /> : null}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Leaf className="h-4 w-4 text-primary" /> Crop health
              </CardTitle>
              <CardDescription>Most recent AI screening result</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("/crop-health")}>
              Open <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent>
            {data.crop_health.available ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold">
                      {data.crop_health.predicted_label?.replaceAll("_", " ")}
                    </p>
                    <p className="text-sm text-muted-foreground">{data.crop_health.crop}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge variant={data.crop_health.is_healthy ? "success" : "warning"}>
                      {data.crop_health.is_healthy ? "Healthy" : "Needs attention"}
                    </Badge>
                    <DemoBadge show={data.crop_health.is_demo} />
                  </div>
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                    <span>Confidence</span>
                    <span>{formatPercent(data.crop_health.confidence)}</span>
                  </div>
                  <Progress value={data.crop_health.confidence ?? 0} />
                </div>
                <p className="text-xs text-muted-foreground">
                  Scanned {formatDateTime(data.crop_health.predicted_at)}
                </p>
              </div>
            ) : (
              <EmptyState
                title="No crop-health scans yet"
                description="Upload a leaf photo to get a screening result and treatment guidance."
                action={
                  <Button size="sm" onClick={() => navigate("/crop-health")}>
                    Scan a leaf
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" /> Yield &amp; harvest
              </CardTitle>
              <CardDescription>Latest model estimate with uncertainty</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("/yield")}>
              Open <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent>
            {data.yield_prediction.available ? (
              <div className="space-y-3">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <p className="text-2xl font-semibold">
                      {formatNumber(data.yield_prediction.total_quintals, 1)}{" "}
                      <span className="text-sm font-normal text-muted-foreground">quintals</span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {data.yield_prediction.crop} ·{" "}
                      {formatNumber(data.yield_prediction.yield_per_hectare, 1)} q/ha
                    </p>
                  </div>
                  <Badge variant="info">
                    80%: {formatNumber(data.yield_prediction.lower_total_quintals, 0)}–
                    {formatNumber(data.yield_prediction.upper_total_quintals, 0)} q
                  </Badge>
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                    <span>Input completeness</span>
                    <span>{formatPercent(data.yield_prediction.input_completeness)}</span>
                  </div>
                  <Progress value={data.yield_prediction.input_completeness ?? 0} />
                </div>
                <p className="text-xs text-muted-foreground">
                  Predicted {formatDateTime(data.yield_prediction.predicted_at)}
                </p>
              </div>
            ) : (
              <EmptyState
                title="No yield prediction yet"
                description="Generate a yield estimate to size your market and transport decisions."
                action={
                  <Button size="sm" onClick={() => navigate("/yield")}>
                    Predict yield
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div>
            <CardTitle>Farm portfolio</CardTitle>
            <CardDescription>Area, active crops and demo labelling</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate("/farms")}>
            Manage farms
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Farm</TableHead>
                <TableHead>Location</TableHead>
                <TableHead className="text-right">Area (ha)</TableHead>
                <TableHead className="text-right">Active crops</TableHead>
                <TableHead>Data</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.farms.length === 0 ? (
                <TableEmpty colSpan={5} message="No farms yet. Create one to get started." />
              ) : (
                data.farms.map((farm) => (
                  <TableRow key={farm.id}>
                    <TableCell className="font-medium">{farm.name}</TableCell>
                    <TableCell>
                      {farm.district}, {farm.state}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(farm.total_area_hectares, 1)}
                    </TableCell>
                    <TableCell className="text-right">{farm.active_crops}</TableCell>
                    <TableCell>{farm.is_demo ? <DemoBadge show /> : <Badge variant="success">Real</Badge>}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {data.decision.available ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-4 w-4 text-primary" /> Latest recommendation
            </CardTitle>
            <CardDescription>Generated {formatDateTime(data.decision.generated_at)}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <ActionBadge action={data.decision.action} />
              <RiskBadge category={data.decision.risk_category} />
              <span className="text-sm text-muted-foreground">
                via {data.decision.selected_buyer_name ?? "mandi"} · risk{" "}
                {formatNumber(data.decision.risk_score, 2)}
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg bg-secondary/60 p-3">
                <p className="text-xs uppercase text-muted-foreground">Net realisation</p>
                <p className="mt-1 text-lg font-semibold">
                  {formatCurrency(data.decision.net_realization, 0)}
                </p>
              </div>
              <div className="rounded-lg bg-secondary/60 p-3">
                <p className="text-xs uppercase text-muted-foreground">Per quintal</p>
                <p className="mt-1 text-lg font-semibold">
                  {formatCurrency(data.decision.net_realization_per_quintal, 0)}
                </p>
              </div>
              <div className="rounded-lg bg-secondary/60 p-3">
                <p className="text-xs uppercase text-muted-foreground">Decision ID</p>
                <p className="mt-1 text-lg font-semibold">#{data.decision.decision_id}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => navigate("/decisions")}>
              View full explanation <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
