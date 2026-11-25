import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CloudSun,
  Droplets,
  MapPin,
  Pencil,
  Plus,
  Sprout,
  Thermometer,
  Trash2,
  Wind,
} from "lucide-react";

import { api } from "../lib/api";
import { useOptions, useFarms } from "../hooks/useReference";
import { formatDate, formatNumber, todayIso } from "../lib/utils";
import type { Crop, Farm, WeatherResponse } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select, Textarea } from "../components/ui/input";
import { Alert, DemoBadge, EmptyState, LoadingBlock, PageHeader } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

type FarmFormState = {
  name: string;
  village: string;
  district: string;
  state: string;
  latitude: string;
  longitude: string;
  total_area_hectares: string;
  soil_type: string;
  soil_ph: string;
  nitrogen_kg_per_ha: string;
  phosphorus_kg_per_ha: string;
  potassium_kg_per_ha: string;
  soil_moisture_pct: string;
  notes: string;
};

const emptyFarm: FarmFormState = {
  name: "",
  village: "",
  district: "",
  state: "",
  latitude: "",
  longitude: "",
  total_area_hectares: "",
  soil_type: "",
  soil_ph: "",
  nitrogen_kg_per_ha: "",
  phosphorus_kg_per_ha: "",
  potassium_kg_per_ha: "",
  soil_moisture_pct: "",
  notes: "",
};

function farmToForm(farm: Farm): FarmFormState {
  return {
    name: farm.name,
    village: farm.village ?? "",
    district: farm.district,
    state: farm.state,
    latitude: farm.latitude?.toString() ?? "",
    longitude: farm.longitude?.toString() ?? "",
    total_area_hectares: farm.total_area_hectares.toString(),
    soil_type: farm.soil_type ?? "",
    soil_ph: farm.soil_ph?.toString() ?? "",
    nitrogen_kg_per_ha: farm.nitrogen_kg_per_ha?.toString() ?? "",
    phosphorus_kg_per_ha: farm.phosphorus_kg_per_ha?.toString() ?? "",
    potassium_kg_per_ha: farm.potassium_kg_per_ha?.toString() ?? "",
    soil_moisture_pct: farm.soil_moisture_pct?.toString() ?? "",
    notes: farm.notes ?? "",
  };
}

function optionalNumber(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

function farmPayload(form: FarmFormState) {
  return {
    name: form.name.trim(),
    village: form.village.trim() || null,
    district: form.district.trim(),
    state: form.state,
    latitude: optionalNumber(form.latitude),
    longitude: optionalNumber(form.longitude),
    total_area_hectares: Number(form.total_area_hectares),
    soil_type: form.soil_type || null,
    soil_ph: optionalNumber(form.soil_ph),
    nitrogen_kg_per_ha: optionalNumber(form.nitrogen_kg_per_ha),
    phosphorus_kg_per_ha: optionalNumber(form.phosphorus_kg_per_ha),
    potassium_kg_per_ha: optionalNumber(form.potassium_kg_per_ha),
    soil_moisture_pct: optionalNumber(form.soil_moisture_pct),
    notes: form.notes.trim() || null,
  };
}

type CropFormState = {
  crop_name: string;
  variety: string;
  season: string;
  sowing_date: string;
  expected_harvest_date: string;
  growth_stage: string;
  area_hectares: string;
  status: string;
  notes: string;
};

const emptyCrop: CropFormState = {
  crop_name: "Rice",
  variety: "",
  season: "Kharif",
  sowing_date: todayIso(),
  expected_harvest_date: "",
  growth_stage: "Sowing/Germination",
  area_hectares: "",
  status: "active",
  notes: "",
};

function cropPayload(form: CropFormState, farmId: number) {
  return {
    farm_id: farmId,
    crop_name: form.crop_name,
    variety: form.variety.trim() || null,
    season: form.season,
    sowing_date: form.sowing_date,
    expected_harvest_date: form.expected_harvest_date || null,
    growth_stage: form.growth_stage || null,
    area_hectares: Number(form.area_hectares),
    status: form.status,
    notes: form.notes.trim() || null,
  };
}

export default function FarmsPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const options = useOptions();
  const [selectedFarmId, setSelectedFarmId] = useState<number | null>(null);
  const [farmDialog, setFarmDialog] = useState<{ open: boolean; farm: Farm | null }>({
    open: false,
    farm: null,
  });
  const [cropDialog, setCropDialog] = useState<{ open: boolean; crop: Crop | null }>({
    open: false,
    crop: null,
  });
  const [farmForm, setFarmForm] = useState<FarmFormState>(emptyFarm);
  const [cropForm, setCropForm] = useState<CropFormState>(emptyCrop);
  const [error, setError] = useState<string | null>(null);
  const [weatherFarmId, setWeatherFarmId] = useState<number | null>(null);

  const activeFarmId = selectedFarmId ?? farms.data?.[0]?.id ?? null;
  const activeFarm = farms.data?.find((farm) => farm.id === activeFarmId) ?? null;

  const crops = useQuery({
    queryKey: ["crops", activeFarmId],
    queryFn: () => api.get<Crop[]>(`/farms/${activeFarmId}/crops`),
    enabled: activeFarmId !== null,
  });

  const weather = useQuery({
    queryKey: ["weather", weatherFarmId],
    queryFn: () => api.get<WeatherResponse>(`/weather/${weatherFarmId}?days=7`),
    enabled: weatherFarmId !== null,
    retry: false,
  });

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["farms"] });
    void queryClient.invalidateQueries({ queryKey: ["crops"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
  }

  const saveFarm = useMutation({
    mutationFn: async () => {
      const payload = farmPayload(farmForm);
      if (farmDialog.farm) {
        return api.patch<Farm>(`/farms/${farmDialog.farm.id}`, payload);
      }
      return api.post<Farm>("/farms", payload);
    },
    onSuccess: (farm) => {
      invalidate();
      setFarmDialog({ open: false, farm: null });
      setSelectedFarmId(farm.id);
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteFarm = useMutation({
    mutationFn: (id: number) => api.delete(`/farms/${id}`),
    onSuccess: () => {
      invalidate();
      setSelectedFarmId(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const saveCrop = useMutation({
    mutationFn: async () => {
      if (activeFarmId === null) throw new Error("Select a farm first");
      const payload = cropPayload(cropForm, activeFarmId);
      if (cropDialog.crop) {
        return api.patch<Crop>(`/crops/${cropDialog.crop.id}`, payload);
      }
      return api.post<Crop>("/crops", payload);
    },
    onSuccess: () => {
      invalidate();
      setCropDialog({ open: false, crop: null });
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteCrop = useMutation({
    mutationFn: (id: number) => api.delete(`/crops/${id}`),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  function openFarmDialog(farm: Farm | null) {
    setError(null);
    setFarmForm(farm ? farmToForm(farm) : emptyFarm);
    setFarmDialog({ open: true, farm });
  }

  function openCropDialog(crop: Crop | null) {
    setError(null);
    setCropForm(
      crop
        ? {
            crop_name: crop.crop_name,
            variety: crop.variety ?? "",
            season: crop.season,
            sowing_date: crop.sowing_date,
            expected_harvest_date: crop.expected_harvest_date ?? "",
            growth_stage: crop.growth_stage ?? "",
            area_hectares: crop.area_hectares.toString(),
            status: crop.status,
            notes: crop.notes ?? "",
          }
        : emptyCrop,
    );
    setCropDialog({ open: true, crop });
  }

  if (farms.isLoading) return <LoadingBlock label="Loading farms…" />;
  if (farms.isError) {
    return <Alert variant="error">{(farms.error as Error).message}</Alert>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Farms & crops"
        description="Manage the fields and standing crops that feed every prediction and decision."
        actions={
          <Button size="sm" onClick={() => openFarmDialog(null)}>
            <Plus className="h-4 w-4" /> Add farm
          </Button>
        }
      />

      {error ? (
        <Alert variant="error" title="Action failed">
          {error}
        </Alert>
      ) : null}

      {farms.data!.length === 0 ? (
        <EmptyState
          title="No farms yet"
          description="Create a farm with its district, area and optional soil data to start using AgriTwin."
          icon={<Sprout className="h-8 w-8" />}
          action={<Button onClick={() => openFarmDialog(null)}>Add your first farm</Button>}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <div className="space-y-3">
            {farms.data!.map((farm) => (
              <button
                key={farm.id}
                type="button"
                onClick={() => {
                  setSelectedFarmId(farm.id);
                  setWeatherFarmId(null);
                }}
                className={`w-full rounded-lg border p-4 text-left transition-colors ${
                  farm.id === activeFarmId
                    ? "border-primary bg-primary/5"
                    : "bg-card hover:bg-secondary/40"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{farm.name}</p>
                  {farm.is_demo ? <DemoBadge show /> : null}
                </div>
                <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  {farm.village ? `${farm.village}, ` : ""}
                  {farm.district}, {farm.state}
                </p>
                <p className="mt-2 text-sm">
                  {formatNumber(farm.total_area_hectares, 1)} ha ·{" "}
                  {farm.soil_type ?? "soil not set"}
                </p>
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {activeFarm ? (
              <>
                <Card>
                  <CardHeader className="flex-row items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {activeFarm.name} {activeFarm.is_demo ? <DemoBadge show /> : null}
                      </CardTitle>
                      <CardDescription>
                        {activeFarm.village ? `${activeFarm.village}, ` : ""}
                        {activeFarm.district}, {activeFarm.state} ·{" "}
                        {formatNumber(activeFarm.total_area_hectares, 1)} ha
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={() => openFarmDialog(activeFarm)}>
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setWeatherFarmId(activeFarm.id)}
                        loading={weather.isFetching && weatherFarmId === activeFarm.id}
                      >
                        <CloudSun className="h-3.5 w-3.5" /> Weather
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (window.confirm(`Delete ${activeFarm.name} and all its crops?`)) {
                            deleteFarm.mutate(activeFarm.id);
                          }
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Delete
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {[
                        ["Soil type", activeFarm.soil_type ?? "—"],
                        ["Soil pH", activeFarm.soil_ph ?? "—"],
                        ["Nitrogen", activeFarm.nitrogen_kg_per_ha ? `${activeFarm.nitrogen_kg_per_ha} kg/ha` : "—"],
                        ["Phosphorus", activeFarm.phosphorus_kg_per_ha ? `${activeFarm.phosphorus_kg_per_ha} kg/ha` : "—"],
                        ["Potassium", activeFarm.potassium_kg_per_ha ? `${activeFarm.potassium_kg_per_ha} kg/ha` : "—"],
                        ["Soil moisture", activeFarm.soil_moisture_pct ? `${activeFarm.soil_moisture_pct}%` : "—"],
                        ["Coordinates", activeFarm.latitude !== null ? `${activeFarm.latitude}, ${activeFarm.longitude}` : "Not set"],
                        ["Created", formatDate(activeFarm.created_at)],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-lg bg-secondary/50 p-3">
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
                          <p className="mt-1 text-sm font-medium">{value}</p>
                        </div>
                      ))}
                    </div>
                    {activeFarm.notes ? (
                      <p className="mt-3 text-sm text-muted-foreground">{activeFarm.notes}</p>
                    ) : null}
                  </CardContent>
                </Card>

                {weatherFarmId === activeFarm.id ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <CloudSun className="h-4 w-4 text-primary" /> Live weather
                      </CardTitle>
                      <CardDescription>
                        Open-Meteo forecast for the farm coordinates (or geocoded district).
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {weather.isLoading ? (
                        <LoadingBlock label="Fetching forecast…" />
                      ) : weather.isError ? (
                        <Alert variant="warning">{weather.error.message}</Alert>
                      ) : weather.data ? (
                        <div className="space-y-4">
                          <div className="grid gap-3 sm:grid-cols-4">
                            <div className="rounded-lg border p-3">
                              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Thermometer className="h-3 w-3" /> Temperature
                              </p>
                              <p className="mt-1 text-lg font-semibold">
                                {formatNumber(weather.data.current.temperature_c, 1)} °C
                              </p>
                            </div>
                            <div className="rounded-lg border p-3">
                              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Droplets className="h-3 w-3" /> Humidity
                              </p>
                              <p className="mt-1 text-lg font-semibold">
                                {formatNumber(weather.data.current.humidity_pct, 0)}%
                              </p>
                            </div>
                            <div className="rounded-lg border p-3">
                              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Droplets className="h-3 w-3" /> Rain now
                              </p>
                              <p className="mt-1 text-lg font-semibold">
                                {formatNumber(weather.data.current.rainfall_mm, 1)} mm
                              </p>
                            </div>
                            <div className="rounded-lg border p-3">
                              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Wind className="h-3 w-3" /> Wind
                              </p>
                              <p className="mt-1 text-lg font-semibold">
                                {formatNumber(weather.data.current.wind_speed_kmh, 0)} km/h
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={
                                weather.data.risk_label === "high"
                                  ? "danger"
                                  : weather.data.risk_label === "moderate"
                                    ? "warning"
                                    : "success"
                              }
                            >
                              {weather.data.risk_label} operational risk
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              score {formatNumber(weather.data.risk_score, 2)} ·{" "}
                              {weather.data.coordinates_approximate
                                ? "district-level coordinates"
                                : "farm coordinates"}
                            </span>
                          </div>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead className="text-right">Max °C</TableHead>
                                <TableHead className="text-right">Min °C</TableHead>
                                <TableHead className="text-right">Rain mm</TableHead>
                                <TableHead className="text-right">Wind km/h</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {weather.data.daily.map((day) => (
                                <TableRow key={day.date}>
                                  <TableCell>{formatDate(day.date)}</TableCell>
                                  <TableCell className="text-right">{formatNumber(day.temperature_max_c, 1)}</TableCell>
                                  <TableCell className="text-right">{formatNumber(day.temperature_min_c, 1)}</TableCell>
                                  <TableCell className="text-right">{formatNumber(day.rainfall_mm, 1)}</TableCell>
                                  <TableCell className="text-right">{formatNumber(day.wind_max_kmh, 0)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                ) : null}

                <Card>
                  <CardHeader className="flex-row items-center justify-between">
                    <div>
                      <CardTitle>Standing crops</CardTitle>
                      <CardDescription>Each crop can be scanned, modelled and sold.</CardDescription>
                    </div>
                    <Button size="sm" onClick={() => openCropDialog(null)}>
                      <Plus className="h-4 w-4" /> Add crop
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Crop</TableHead>
                          <TableHead>Season</TableHead>
                          <TableHead>Sowing</TableHead>
                          <TableHead>Harvest</TableHead>
                          <TableHead>Stage</TableHead>
                          <TableHead className="text-right">Area (ha)</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {crops.isLoading ? (
                          <TableRow>
                            <TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                              Loading crops…
                            </TableCell>
                          </TableRow>
                        ) : crops.data && crops.data.length > 0 ? (
                          crops.data.map((crop) => (
                            <TableRow key={crop.id}>
                              <TableCell>
                                <p className="font-medium">{crop.crop_name}</p>
                                <p className="text-xs text-muted-foreground">{crop.variety ?? "—"}</p>
                              </TableCell>
                              <TableCell>{crop.season}</TableCell>
                              <TableCell>{formatDate(crop.sowing_date)}</TableCell>
                              <TableCell>{formatDate(crop.expected_harvest_date)}</TableCell>
                              <TableCell>{crop.growth_stage ?? "—"}</TableCell>
                              <TableCell className="text-right">{formatNumber(crop.area_hectares, 2)}</TableCell>
                              <TableCell>
                                <Badge variant={crop.status === "active" ? "success" : "secondary"}>
                                  {crop.status}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="flex justify-end gap-1">
                                  <Button variant="ghost" size="icon" onClick={() => openCropDialog(crop)} aria-label="Edit crop">
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => {
                                      if (window.confirm(`Delete ${crop.crop_name}?`)) deleteCrop.mutate(crop.id);
                                    }}
                                    aria-label="Delete crop"
                                  >
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableEmpty colSpan={8} message="No crops on this farm yet." />
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </>
            ) : null}
          </div>
        </div>
      )}

      <Dialog
        open={farmDialog.open}
        onClose={() => setFarmDialog({ open: false, farm: null })}
        title={farmDialog.farm ? "Edit farm" : "Add farm"}
        description="District and state are required. Coordinates enable distance-based transport and live weather."
        footer={
          <>
            <Button variant="outline" onClick={() => setFarmDialog({ open: false, farm: null })}>
              Cancel
            </Button>
            <Button
              onClick={() => saveFarm.mutate()}
              loading={saveFarm.isPending}
              disabled={!farmForm.name || !farmForm.district || !farmForm.state || !farmForm.total_area_hectares}
            >
              {farmDialog.farm ? "Save changes" : "Create farm"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Farm name" className="sm:col-span-2">
            <Input value={farmForm.name} onChange={(event) => setFarmForm({ ...farmForm, name: event.target.value })} />
          </Field>
          <Field label="Village">
            <Input value={farmForm.village} onChange={(event) => setFarmForm({ ...farmForm, village: event.target.value })} />
          </Field>
          <Field label="District">
            <Input value={farmForm.district} onChange={(event) => setFarmForm({ ...farmForm, district: event.target.value })} />
          </Field>
          <Field label="State">
            <Select value={farmForm.state} onChange={(event) => setFarmForm({ ...farmForm, state: event.target.value })}>
              <option value="">Select state</option>
              {(options.data?.states ?? []).map((state) => (
                <option key={state} value={state}>{state}</option>
              ))}
            </Select>
          </Field>
          <Field label="Total area (hectares)">
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={farmForm.total_area_hectares}
              onChange={(event) => setFarmForm({ ...farmForm, total_area_hectares: event.target.value })}
            />
          </Field>
          <Field label="Latitude (optional)">
            <Input
              type="number"
              step="any"
              value={farmForm.latitude}
              onChange={(event) => setFarmForm({ ...farmForm, latitude: event.target.value })}
            />
          </Field>
          <Field label="Longitude (optional)">
            <Input
              type="number"
              step="any"
              value={farmForm.longitude}
              onChange={(event) => setFarmForm({ ...farmForm, longitude: event.target.value })}
            />
          </Field>
          <Field label="Soil type">
            <Select value={farmForm.soil_type} onChange={(event) => setFarmForm({ ...farmForm, soil_type: event.target.value })}>
              <option value="">Not set</option>
              {(options.data?.soil_types ?? []).map((soil) => (
                <option key={soil} value={soil}>{soil}</option>
              ))}
            </Select>
          </Field>
          <Field label="Soil pH">
            <Input
              type="number"
              step="0.1"
              value={farmForm.soil_ph}
              onChange={(event) => setFarmForm({ ...farmForm, soil_ph: event.target.value })}
            />
          </Field>
          <Field label="Nitrogen (kg/ha)">
            <Input type="number" step="0.1" value={farmForm.nitrogen_kg_per_ha} onChange={(event) => setFarmForm({ ...farmForm, nitrogen_kg_per_ha: event.target.value })} />
          </Field>
          <Field label="Phosphorus (kg/ha)">
            <Input type="number" step="0.1" value={farmForm.phosphorus_kg_per_ha} onChange={(event) => setFarmForm({ ...farmForm, phosphorus_kg_per_ha: event.target.value })} />
          </Field>
          <Field label="Potassium (kg/ha)">
            <Input type="number" step="0.1" value={farmForm.potassium_kg_per_ha} onChange={(event) => setFarmForm({ ...farmForm, potassium_kg_per_ha: event.target.value })} />
          </Field>
          <Field label="Soil moisture (%)">
            <Input type="number" step="0.1" value={farmForm.soil_moisture_pct} onChange={(event) => setFarmForm({ ...farmForm, soil_moisture_pct: event.target.value })} />
          </Field>
          <Field label="Notes" className="sm:col-span-2">
            <Textarea value={farmForm.notes} onChange={(event) => setFarmForm({ ...farmForm, notes: event.target.value })} />
          </Field>
        </div>
      </Dialog>

      <Dialog
        open={cropDialog.open}
        onClose={() => setCropDialog({ open: false, crop: null })}
        title={cropDialog.crop ? "Edit crop" : "Add crop"}
        description="Sowing date and area drive harvest readiness, yield and revenue estimates."
        footer={
          <>
            <Button variant="outline" onClick={() => setCropDialog({ open: false, crop: null })}>
              Cancel
            </Button>
            <Button
              onClick={() => saveCrop.mutate()}
              loading={saveCrop.isPending}
              disabled={!cropForm.crop_name || !cropForm.sowing_date || !cropForm.area_hectares}
            >
              {cropDialog.crop ? "Save changes" : "Create crop"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Crop">
            <Select value={cropForm.crop_name} onChange={(event) => setCropForm({ ...cropForm, crop_name: event.target.value })}>
              {(options.data?.crops ?? []).map((crop) => (
                <option key={crop} value={crop}>{crop}</option>
              ))}
            </Select>
          </Field>
          <Field label="Variety">
            <Input value={cropForm.variety} onChange={(event) => setCropForm({ ...cropForm, variety: event.target.value })} />
          </Field>
          <Field label="Season">
            <Select value={cropForm.season} onChange={(event) => setCropForm({ ...cropForm, season: event.target.value })}>
              {(options.data?.seasons ?? []).map((season) => (
                <option key={season} value={season}>{season}</option>
              ))}
            </Select>
          </Field>
          <Field label="Growth stage">
            <Select value={cropForm.growth_stage} onChange={(event) => setCropForm({ ...cropForm, growth_stage: event.target.value })}>
              <option value="">Not set</option>
              {(options.data?.growth_stages ?? []).map((stage) => (
                <option key={stage} value={stage}>{stage}</option>
              ))}
            </Select>
          </Field>
          <Field label="Sowing date">
            <Input type="date" value={cropForm.sowing_date} onChange={(event) => setCropForm({ ...cropForm, sowing_date: event.target.value })} />
          </Field>
          <Field label="Expected harvest date">
            <Input type="date" value={cropForm.expected_harvest_date} onChange={(event) => setCropForm({ ...cropForm, expected_harvest_date: event.target.value })} />
          </Field>
          <Field label="Area (hectares)">
            <Input type="number" min="0.01" step="0.01" value={cropForm.area_hectares} onChange={(event) => setCropForm({ ...cropForm, area_hectares: event.target.value })} />
          </Field>
          <Field label="Status">
            <Select value={cropForm.status} onChange={(event) => setCropForm({ ...cropForm, status: event.target.value })}>
              <option value="active">active</option>
              <option value="harvested">harvested</option>
              <option value="failed">failed</option>
            </Select>
          </Field>
          <Field label="Notes" className="sm:col-span-2">
            <Textarea value={cropForm.notes} onChange={(event) => setCropForm({ ...cropForm, notes: event.target.value })} />
          </Field>
        </div>
      </Dialog>
    </div>
  );
}
