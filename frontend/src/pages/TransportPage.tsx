import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  IndianRupee,
  MapPinned,
  Package,
  Route,
  Truck,
  Weight,
} from "lucide-react";

import { api } from "../lib/api";
import { useBuyers, useCrops, useFarms } from "../hooks/useReference";
import { formatCurrency, formatDate, formatNumber } from "../lib/utils";
import type { TransportEstimate, VehicleOption } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/input";
import { Alert, EmptyState, KeyValue, LoadingBlock, PageHeader } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

export default function TransportPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const buyers = useBuyers();
  const [farmId, setFarmId] = useState<number | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [buyerId, setBuyerId] = useState<number | null>(null);
  const [quantity, setQuantity] = useState("100");
  const [vehicleType, setVehicleType] = useState("truck");
  const [useRouting, setUseRouting] = useState(true);
  const [costPerKm, setCostPerKm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TransportEstimate | null>(null);

  const activeFarmId = farmId ?? farms.data?.[0]?.id ?? null;
  const crops = useCrops(activeFarmId ?? undefined);
  const activeCropId = cropId ?? crops.data?.[0]?.id ?? null;
  const activeBuyerId = buyerId ?? buyers.data?.[0]?.id ?? null;

  const vehicles = useQuery({
    queryKey: ["transport-vehicles"],
    queryFn: () =>
      api.get<{ vehicles: VehicleOption[]; notes: string }>("/transport/vehicles"),
  });

  const estimates = useQuery({
    queryKey: ["transport-estimates", activeFarmId],
    queryFn: () =>
      api.get<TransportEstimate[]>(
        `/transport/estimates${activeFarmId ? `?farm_id=${activeFarmId}` : ""}`,
      ),
  });

  const selectedVehicle = useMemo(
    () => vehicles.data?.vehicles.find((row) => row.type === vehicleType) ?? null,
    [vehicles.data, vehicleType],
  );

  const estimate = useMutation({
    mutationFn: () => {
      if (activeFarmId === null) throw new Error("Select a farm");
      if (activeBuyerId === null) throw new Error("Select a buyer");
      return api.post<TransportEstimate>("/transport/estimate", {
        farm_id: activeFarmId,
        buyer_id: activeBuyerId,
        crop_id: activeCropId ?? undefined,
        quantity_quintals: Number(quantity),
        vehicle_type: vehicleType,
        transport_mode: "road",
        cost_per_km: costPerKm.trim() ? Number(costPerKm) : undefined,
        use_routing: useRouting,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["transport-estimates"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const tripPreview = selectedVehicle
    ? Math.ceil(Number(quantity || "0") / selectedVehicle.capacity_quintals)
    : null;

  if (farms.isLoading) return <LoadingBlock label="Loading transport workspace…" />;
  if (farms.isError) return <Alert variant="error">{(farms.error as Error).message}</Alert>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transport"
        description="Estimate road distance, trips and landed transport cost before choosing a sales channel."
        actions={
          <Button
            size="sm"
            onClick={() => estimate.mutate()}
            loading={estimate.isPending}
            disabled={activeFarmId === null || activeBuyerId === null}
          >
            <Truck className="h-4 w-4" /> Estimate cost
          </Button>
        }
      />

      <Alert variant="info" title="Planning defaults, not freight quotes">
        {vehicles.data?.notes ??
          "Vehicle rates are configurable assumptions. OSRM road distance is used when available, otherwise a geodesic detour estimate."}
      </Alert>

      {error ? (
        <Alert variant="error" title="Estimate failed">
          {error}
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Route className="h-4 w-4 text-primary" /> Shipment
            </CardTitle>
            <CardDescription>Farm to buyer or mandi.</CardDescription>
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
            <Field label="Crop (optional)">
              <Select
                value={activeCropId ?? ""}
                onChange={(event) => setCropId(Number(event.target.value))}
              >
                <option value="">Not specified</option>
                {(crops.data ?? []).map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.crop_name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Destination buyer">
              <Select
                value={activeBuyerId ?? ""}
                onChange={(event) => setBuyerId(Number(event.target.value))}
              >
                <option value="">Select buyer</option>
                {(buyers.data ?? []).map((buyer) => (
                  <option key={buyer.id} value={buyer.id}>
                    {buyer.name} · {buyer.district}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Quantity (quintals)">
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                />
              </Field>
              <Field label="Vehicle">
                <Select
                  value={vehicleType}
                  onChange={(event) => setVehicleType(event.target.value)}
                >
                  {(vehicles.data?.vehicles ?? []).map((vehicle) => (
                    <option key={vehicle.type} value={vehicle.type}>
                      {vehicle.label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Cost per km override (optional)">
              <Input
                type="number"
                min="1"
                step="0.5"
                placeholder={
                  selectedVehicle ? `Default ₹${selectedVehicle.cost_per_km_inr}/km` : "Default rate"
                }
                value={costPerKm}
                onChange={(event) => setCostPerKm(event.target.value)}
              />
            </Field>
            <Field label="Routing">
              <Select
                value={useRouting ? "yes" : "no"}
                onChange={(event) => setUseRouting(event.target.value === "yes")}
              >
                <option value="yes">Use OSRM road distance when available</option>
                <option value="no">Use geodesic detour estimate</option>
              </Select>
            </Field>

            {selectedVehicle ? (
              <div className="rounded-lg bg-secondary/50 p-3">
                <KeyValue
                  label="Capacity"
                  value={`${formatNumber(selectedVehicle.capacity_quintals, 0)} q`}
                />
                <KeyValue
                  label="Rate"
                  value={`₹${formatNumber(selectedVehicle.cost_per_km_inr, 0)}/km`}
                />
                <KeyValue
                  label="Trips needed"
                  value={tripPreview === null ? "—" : String(tripPreview)}
                />
                <KeyValue
                  label="Fixed + handling"
                  value={formatCurrency(
                    selectedVehicle.fixed_cost_inr +
                      selectedVehicle.loading_cost_inr +
                      selectedVehicle.unloading_cost_inr,
                    0,
                  )}
                />
              </div>
            ) : null}

            <Button
              className="w-full"
              onClick={() => estimate.mutate()}
              loading={estimate.isPending}
              disabled={activeFarmId === null || activeBuyerId === null || !quantity}
            >
              <Truck className="h-4 w-4" /> Estimate transport
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {result ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <IndianRupee className="h-4 w-4 text-primary" /> Estimate result
                </CardTitle>
                <CardDescription>
                  {result.transport_mode} · {result.vehicle_type} ·{" "}
                  {formatDate(result.created_at)}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border bg-primary/5 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Total cost</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatCurrency(result.total_cost, 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatCurrency(result.cost_per_quintal, 2)}/quintal
                    </p>
                  </div>
                  <div className="rounded-xl border p-4">
                    <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
                      <MapPinned className="h-3 w-3" /> Distance
                    </p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatNumber(result.distance_km, 1)} km
                    </p>
                    <p className="text-xs text-muted-foreground">{result.distance_method}</p>
                  </div>
                  <div className="rounded-xl border p-4">
                    <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
                      <Package className="h-3 w-3" /> Load
                    </p>
                    <p className="mt-1 text-2xl font-semibold">
                      {formatNumber(result.quantity_quintals, 0)} q
                    </p>
                    <p className="text-xs text-muted-foreground">{result.trips} trip(s)</p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <KeyValue
                      label="Line-haul"
                      value={formatCurrency(
                        result.cost_per_km * result.distance_km * result.trips,
                        0,
                      )}
                    />
                    <KeyValue label="Fixed cost" value={formatCurrency(result.fixed_cost, 0)} />
                    <KeyValue label="Loading" value={formatCurrency(result.loading_cost, 0)} />
                    <KeyValue label="Unloading" value={formatCurrency(result.unloading_cost, 0)} />
                  </div>
                  <div>
                    <KeyValue
                      label="Cost per kg"
                      value={formatCurrency(result.cost_per_kg, 2)}
                    />
                    <KeyValue label="Provider" value={result.provider} />
                    <KeyValue
                      label="Approximate"
                      value={
                        result.is_approximate ? (
                          <Badge variant="warning">yes</Badge>
                        ) : (
                          <Badge variant="success">no</Badge>
                        )
                      }
                    />
                    <KeyValue label="Vehicle capacity" value={`${result.vehicle_capacity_quintals} q`} />
                  </div>
                </div>

                {result.notes ? <p className="text-sm text-muted-foreground">{result.notes}</p> : null}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-16">
                <EmptyState
                  title="No estimate in this session"
                  description="Choose a farm and buyer, then estimate to see distance, trips and landed cost."
                  icon={<Truck className="h-8 w-8" />}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Weight className="h-4 w-4 text-primary" /> Vehicle reference
              </CardTitle>
              <CardDescription>Configurable planning defaults</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Vehicle</TableHead>
                    <TableHead className="text-right">Capacity</TableHead>
                    <TableHead className="text-right">₹/km</TableHead>
                    <TableHead className="text-right">Fixed</TableHead>
                    <TableHead className="text-right">Loading</TableHead>
                    <TableHead className="text-right">Unloading</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(vehicles.data?.vehicles ?? []).map((vehicle) => (
                    <TableRow key={vehicle.type}>
                      <TableCell className="font-medium">{vehicle.label}</TableCell>
                      <TableCell className="text-right">{vehicle.capacity_quintals} q</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(vehicle.cost_per_km_inr, 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(vehicle.fixed_cost_inr, 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(vehicle.loading_cost_inr, 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(vehicle.unloading_cost_inr, 0)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ArrowRight className="h-4 w-4 text-primary" /> Saved estimates
          </CardTitle>
          <CardDescription>Recent transport estimates for your farms</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Created</TableHead>
                <TableHead>Farm</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Distance</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">₹/q</TableHead>
                <TableHead>Method</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {estimates.data && estimates.data.length > 0 ? (
                estimates.data.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(row.created_at)}
                    </TableCell>
                    <TableCell>
                      {farms.data?.find((farm) => farm.id === row.farm_id)?.name ??
                        `Farm #${row.farm_id}`}
                    </TableCell>
                    <TableCell>
                      {row.buyer_id
                        ? buyers.data?.find((buyer) => buyer.id === row.buyer_id)?.name ??
                          `Buyer #${row.buyer_id}`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(row.quantity_quintals, 0)} q
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(row.distance_km, 1)} km
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(row.total_cost, 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(row.cost_per_quintal, 0)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={row.is_approximate ? "warning" : "success"}>
                        {row.distance_method}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableEmpty colSpan={8} message="No transport estimates yet." />
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
