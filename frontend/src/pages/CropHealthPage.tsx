import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Camera, ImageIcon, Leaf, ShieldAlert, Trash2, Upload } from "lucide-react";

import { api } from "../lib/api";
import { useCrops, useFarms } from "../hooks/useReference";
import { formatDateTime, formatPercent, titleCase } from "../lib/utils";
import type {
  CropHealthModelInfo,
  CropHealthPrediction,
  CropHealthResponse,
  DiseaseClass,
} from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/input";
import { Alert, DemoBadge, EmptyState, LoadingBlock, PageHeader, Progress, Tabs } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

function PredictionCard({ prediction }: { prediction: CropHealthPrediction }) {
  const top = useMemo(
    () =>
      Object.entries(prediction.probabilities ?? {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5),
    [prediction.probabilities],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={prediction.is_healthy ? "success" : "warning"}>
          {prediction.is_healthy ? "Healthy" : "Disease / pest suspected"}
        </Badge>
        <Badge variant="outline">severity {formatPercent(prediction.severity)}</Badge>
        <Badge variant="info">confidence {formatPercent(prediction.confidence)}</Badge>
        {prediction.is_demo ? <DemoBadge show /> : <Badge variant="success">Trained model</Badge>}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <div className="overflow-hidden rounded-lg border bg-secondary/40">
            {prediction.image_url ? (
              <img
                src={prediction.image_url}
                alt="Uploaded crop leaf"
                className="aspect-video w-full object-contain"
              />
            ) : (
              <div className="flex aspect-video items-center justify-center text-muted-foreground">
                <ImageIcon className="h-8 w-8" />
              </div>
            )}
          </div>
          {prediction.gradcam_url ? (
            <div className="overflow-hidden rounded-lg border bg-secondary/40">
              <img
                src={prediction.gradcam_url}
                alt="Grad-CAM explanation"
                className="aspect-video w-full object-contain"
              />
              <p className="border-t px-3 py-2 text-xs text-muted-foreground">
                Grad-CAM highlights the regions that influenced the prediction.
              </p>
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Predicted label</p>
            <p className="mt-1 text-lg font-semibold">
              {prediction.predicted_label.replaceAll("_", " ")}
            </p>
            <p className="text-sm text-muted-foreground">
              {prediction.predicted_crop} · {prediction.model_version} · {prediction.inference_ms.toFixed(0)} ms
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top probabilities</p>
            {top.map(([label, value]) => (
              <div key={label}>
                <div className="mb-1 flex justify-between gap-2 text-xs">
                  <span className="truncate">{label.replaceAll("_", " ")}</span>
                  <span className="font-medium">{formatPercent(value, 1)}</span>
                </div>
                <Progress value={value} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {prediction.recommendations.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm font-semibold">Recommended next steps</p>
          <div className="grid gap-3 md:grid-cols-2">
            {prediction.recommendations.map((item) => (
              <div key={item.id} className="rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{titleCase(item.category)}</Badge>
                  <span className="text-xs text-muted-foreground">{item.source}</span>
                </div>
                <p className="mt-2 text-sm font-medium">{item.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function CropHealthPage() {
  const queryClient = useQueryClient();
  const farms = useFarms();
  const [farmId, setFarmId] = useState<number | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CropHealthResponse | null>(null);
  const [tab, setTab] = useState("scan");

  const activeFarmId = farmId ?? farms.data?.[0]?.id ?? null;
  const crops = useCrops(activeFarmId ?? undefined);
  const activeCropId = cropId ?? crops.data?.[0]?.id ?? null;

  const model = useQuery({
    queryKey: ["crop-health-model"],
    queryFn: () => api.get<CropHealthModelInfo>("/crop-health/model"),
  });

  const history = useQuery({
    queryKey: ["crop-health-history"],
    queryFn: () => api.get<CropHealthPrediction[]>("/crop-health/predictions"),
  });

  const classes = useQuery({
    queryKey: ["disease-classes"],
    queryFn: () => api.get<DiseaseClass[]>("/crop-health/classes"),
    enabled: tab === "classes",
  });

  const predict = useMutation({
    mutationFn: async () => {
      if (activeFarmId === null || activeCropId === null) throw new Error("Select a farm and crop");
      if (!file) throw new Error("Choose a leaf image");
      const form = new FormData();
      form.append("farm_id", String(activeFarmId));
      form.append("crop_id", String(activeCropId));
      form.append("file", file);
      return api.upload<CropHealthResponse>("/crop-health/predict", form);
    },
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["crop-health-history"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/crop-health/predictions/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["crop-health-history"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const [classFilter, setClassFilter] = useState("all");
  const filteredClasses = useMemo(() => {
    const rows = classes.data ?? [];
    return classFilter === "all" ? rows : rows.filter((row) => row.crop === classFilter);
  }, [classes.data, classFilter]);
  const classCrops = useMemo(
    () => Array.from(new Set((classes.data ?? []).map((row) => row.crop))).sort(),
    [classes.data],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Crop health"
        description="Upload a leaf photo for AI-assisted screening, Grad-CAM evidence and treatment guidance."
        actions={<Tabs tabs={[{ value: "scan", label: "Scan" }, { value: "history", label: "History" }, { value: "classes", label: "Disease library" }]} value={tab} onChange={setTab} />}
      />

      {model.data ? (
        <Alert variant={model.data.mode === "demo" ? "warning" : "success"} title={model.data.mode === "demo" ? "Crop-health model is running in labelled DEMO mode" : `Trained model available (${model.data.model_version})`}>
          {model.data.message ??
            `Architecture: ${model.data.architecture}${model.data.tta_views > 1 ? ` with ${model.data.tta_views}-view TTA` : ""}${model.data.crop_prior_alpha > 0 ? ` and crop prior α=${model.data.crop_prior_alpha}` : ""}. Dataset: ${model.data.dataset_provenance ?? "PlantVillage"}.`}
          {model.data.mode === "demo"
            ? " The heuristic checks colour and texture only; it is not a diagnosis."
            : ""}
        </Alert>
      ) : null}

      {error ? <Alert variant="error" title="Scan failed">{error}</Alert> : null}

      {tab === "scan" ? (
        <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-primary" /> New scan
              </CardTitle>
              <CardDescription>JPEG or PNG up to the configured upload limit.</CardDescription>
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
                    <option key={farm.id} value={farm.id}>{farm.name}</option>
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
                      {crop.crop_name} · {crop.variety ?? "—"}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Leaf image" hint="A close, well-lit photo of a single affected leaf works best.">
                <Input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </Field>
              <Button
                className="w-full"
                onClick={() => predict.mutate()}
                loading={predict.isPending}
                disabled={!file || activeCropId === null}
              >
                <Upload className="h-4 w-4" /> Analyse image
              </Button>
              <p className="text-xs text-muted-foreground">
                Results are screening aids, not laboratory diagnoses. Confirm before applying
                any chemical treatment.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Leaf className="h-4 w-4 text-primary" /> Result
              </CardTitle>
              <CardDescription>
                {result
                  ? `Scanned ${formatDateTime(result.prediction.predicted_at)}`
                  : "Your latest scan result will appear here."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result ? (
                <>
                  <PredictionCard prediction={result.prediction} />
                  <Alert variant="info" className="mt-4">
                    {result.disclaimer}
                  </Alert>
                </>
              ) : (
                <EmptyState
                  title="No scan in this session"
                  description="Select a farm and crop, upload a leaf image, and run the analysis."
                  icon={<ShieldAlert className="h-8 w-8" />}
                />
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "history" ? (
        <Card>
          <CardHeader>
            <CardTitle>Scan history</CardTitle>
            <CardDescription>All crop-health predictions saved to your account.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {history.isLoading ? (
              <LoadingBlock />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Label</TableHead>
                    <TableHead>Crop</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead className="text-right">Confidence</TableHead>
                    <TableHead className="text-right">Severity</TableHead>
                    <TableHead>Mode</TableHead>
                    <TableHead>Scanned</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.data && history.data.length > 0 ? (
                    history.data.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium">{row.predicted_label.replaceAll("_", " ")}</TableCell>
                        <TableCell>{row.predicted_crop}</TableCell>
                        <TableCell>
                          <Badge variant={row.is_healthy ? "success" : "warning"}>
                            {row.is_healthy ? "healthy" : "diseased"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{formatPercent(row.confidence, 1)}</TableCell>
                        <TableCell className="text-right">{formatPercent(row.severity, 0)}</TableCell>
                        <TableCell>
                          {row.is_demo ? <DemoBadge show /> : <Badge variant="success">{row.model_mode}</Badge>}
                        </TableCell>
                        <TableCell>{formatDateTime(row.predicted_at)}</TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setResult({
                                  prediction: row,
                                  model: model.data ?? {
                                    available: false,
                                    model_version: null,
                                    architecture: null,
                                    tta_views: 1,
                                    crop_prior_alpha: 0,
                                    mode: row.model_mode,
                                    classes: [],
                                    metrics: null,
                                    dataset_provenance: null,
                                    message: null,
                                  },
                                  disclaimer:
                                    "This is an AI-assisted screening result, not a laboratory diagnosis.",
                                });
                                setTab("scan");
                              }}
                            >
                              View
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Delete prediction"
                              onClick={() => {
                                if (window.confirm("Delete this prediction?")) remove.mutate(row.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableEmpty colSpan={8} message="No scans yet." />
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}

      {tab === "classes" ? (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-primary" /> Disease library
              </CardTitle>
              <CardDescription>
                {classes.data?.length ?? 0} PlantVillage classes with inspection and prevention guidance.
              </CardDescription>
            </div>
            <Select className="w-56" value={classFilter} onChange={(event) => setClassFilter(event.target.value)}>
              <option value="all">All crops</option>
              {classCrops.map((crop) => (
                <option key={crop} value={crop}>{crop}</option>
              ))}
            </Select>
          </CardHeader>
          <CardContent>
            {classes.isLoading ? (
              <LoadingBlock />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {filteredClasses.map((row) => (
                  <details key={row.id} className="rounded-lg border p-3">
                    <summary className="cursor-pointer list-none">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{row.display_name}</span>
                        <Badge variant={row.is_healthy ? "success" : "warning"}>
                          {row.is_healthy ? "healthy" : row.severity ?? "disease"}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{row.crop}</p>
                    </summary>
                    <div className="mt-3 space-y-2 text-sm">
                      {row.description ? <p>{row.description}</p> : null}
                      {row.inspection_steps && row.inspection_steps.length > 0 ? (
                        <div>
                          <p className="text-xs font-semibold uppercase text-muted-foreground">Inspect</p>
                          <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
                            {row.inspection_steps.map((step) => <li key={step}>{step}</li>)}
                          </ul>
                        </div>
                      ) : null}
                      {row.preventive_practices && row.preventive_practices.length > 0 ? (
                        <div>
                          <p className="text-xs font-semibold uppercase text-muted-foreground">Prevent</p>
                          <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
                            {row.preventive_practices.map((step) => <li key={step}>{step}</li>)}
                          </ul>
                        </div>
                      ) : null}
                      {row.expert_advice ? (
                        <p className="rounded-md bg-secondary/60 p-2 text-xs">{row.expert_advice}</p>
                      ) : null}
                    </div>
                  </details>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
