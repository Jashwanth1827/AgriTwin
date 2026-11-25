export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  state: string | null;
  district: string | null;
  preferred_language: string;
  is_demo: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Farm {
  id: number;
  user_id: number;
  name: string;
  village: string | null;
  district: string;
  state: string;
  latitude: number | null;
  longitude: number | null;
  total_area_hectares: number;
  soil_type: string | null;
  soil_ph: number | null;
  nitrogen_kg_per_ha: number | null;
  phosphorus_kg_per_ha: number | null;
  potassium_kg_per_ha: number | null;
  soil_moisture_pct: number | null;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface FarmDetail extends Farm {
  crops: Crop[];
}

export interface Crop {
  id: number;
  farm_id: number;
  crop_name: string;
  variety: string | null;
  season: string;
  sowing_date: string;
  expected_harvest_date: string | null;
  growth_stage: string | null;
  area_hectares: number;
  status: string;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Buyer {
  id: number;
  name: string;
  buyer_type: string;
  contact_name: string | null;
  contact_phone: string | null;
  market_name: string | null;
  district: string;
  state: string;
  latitude: number | null;
  longitude: number | null;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Offer {
  id: number;
  buyer_id: number;
  crop: string;
  variety: string | null;
  offered_price_per_quintal: number;
  min_quantity_quintals: number;
  max_quantity_quintals: number | null;
  offer_date: string;
  expiry_date: string;
  conditions: string | null;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
}

export interface BuyerDetail extends Buyer {
  offers: Offer[];
}

export interface Recommendation {
  id: number;
  title: string;
  body: string;
  category: string;
  source: string;
}

export interface CropHealthPrediction {
  id: number;
  farm_id: number;
  crop_id: number;
  file_id: number | null;
  predicted_label: string;
  predicted_crop: string;
  is_healthy: boolean;
  confidence: number;
  severity: number;
  probabilities: Record<string, number>;
  inference_ms: number;
  model_version: string;
  model_mode: string;
  is_demo: boolean;
  notes: string | null;
  predicted_at: string;
  image_url: string | null;
  gradcam_url: string | null;
  recommendations: Recommendation[];
}

export interface CropHealthModelInfo {
  available: boolean;
  model_version: string | null;
  architecture: string | null;
  tta_views: number;
  crop_prior_alpha: number;
  mode: string;
  classes: string[];
  metrics: Record<string, unknown> | null;
  dataset_provenance: string | null;
  message: string | null;
}

export interface CropHealthResponse {
  prediction: CropHealthPrediction;
  model: CropHealthModelInfo;
  disclaimer: string;
}

export interface DiseaseClass {
  id: number;
  crop: string;
  name: string;
  display_name: string;
  is_healthy: boolean;
  description: string | null;
  severity: string | null;
  inspection_steps: string[] | null;
  preventive_practices: string[] | null;
  expert_advice: string | null;
}

export interface HarvestReadiness {
  crop: string;
  sowing_date: string;
  expected_harvest_date: string | null;
  estimated_days_remaining: number | null;
  harvest_window_start: string | null;
  harvest_window_end: string | null;
  readiness_status: string;
  confidence: number;
  notes: string;
  weather_considerations: string[];
  calendar_source: string;
}

export interface YieldModelInfo {
  available: boolean;
  model_version: string | null;
  model_name: string | null;
  metrics: Record<string, number | string | null> | null;
  dataset_provenance: string | null;
  features: string[];
  interval_method: string | null;
  message: string | null;
}

export interface YieldPrediction {
  id: number;
  farm_id: number;
  crop_id: number;
  model_version: string;
  model_name: string;
  predicted_yield_per_hectare: number;
  predicted_total_quintals: number | null;
  lower_yield_per_hectare: number | null;
  upper_yield_per_hectare: number | null;
  lower_total_quintals: number | null;
  upper_total_quintals: number | null;
  interval_method: string;
  interval_coverage: number | null;
  confidence: number;
  input_completeness: number;
  is_experimental: boolean;
  inputs: Record<string, unknown>;
  notes: string | null;
  predicted_at: string;
}

export interface YieldPredictionDetail {
  prediction: YieldPrediction;
  harvest_readiness: HarvestReadiness;
  model: YieldModelInfo;
}

export interface PricePoint {
  date: string;
  min_price: number;
  max_price: number;
  modal_price: number;
}

export interface MarketPricesResponse {
  crop: string;
  market: string | null;
  unit: string;
  points: PricePoint[];
  latest_observation_date: string | null;
  data_freshness_days: number | null;
  source: string | null;
  is_demo: boolean;
  available_markets: string[];
}

export interface LiveRatePoint {
  date: string;
  state: string;
  district: string;
  market: string;
  commodity: string;
  commodity_code?: string | null;
  variety: string;
  grade: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  source?: string | null;
  source_resource_id?: string | null;
  fetched_at: string;
}

export interface LiveSourceInfo {
  resource_id: string;
  name: string;
  url: string;
  record_count: number;
  observation_date: string | null;
}

export interface LiveRatesResponse {
  crop: string;
  state: string | null;
  market: string | null;
  unit: string;
  provider: string;
  source_name: string;
  source_url: string;
  license: string;
  commodity_query: string;
  records: LiveRatePoint[];
  sources?: LiveSourceInfo[];
  latest_observation_date: string | null;
  data_freshness_days: number | null;
  fetched_at: string;
  is_demo: boolean;
  is_official: boolean;
  disclaimer: string;
  coverage_note: string;
}

export interface MarketInfo {
  market: string;
  state: string;
  district: string;
  observations: number;
  latest_date: string;
  latest_modal_price: number | null;
}

export interface MarketCropInfo {
  crop: string;
  observations: number;
  markets: number;
  latest_date: string;
}

export interface ForecastPoint {
  date: string;
  expected_price: number;
  lower_bound: number | null;
  upper_bound: number | null;
}

export interface MarketForecast {
  id: number | null;
  crop: string;
  market: string;
  state: string | null;
  horizon_days: number;
  model_name: string;
  expected_price: number;
  lower_bound: number | null;
  upper_bound: number | null;
  metrics: Record<string, unknown> | null;
  points: ForecastPoint[];
  data_freshness_days: number;
  latest_observation_date: string | null;
  interval_method: string | null;
  is_experimental: boolean;
  is_demo: boolean;
  generated_at: string;
  model_comparison: Record<string, unknown>[];
  disclaimer: string;
}

export interface MarketComparisonRow {
  market: string;
  state: string;
  latest_date: string;
  modal_price: number;
  min_price: number;
  max_price: number;
  observations: number;
}

export interface MarketTrends {
  crop: string;
  rows: MarketComparisonRow[];
  best_market: string | null;
  average_modal_price: number | null;
  unit: string;
  is_demo: boolean;
}

export interface MarketImportResponse {
  inserted: number;
  skipped: number;
  errors: string[];
  source: string;
}

export interface TransportEstimate {
  id: number;
  farm_id: number;
  buyer_id: number | null;
  crop_id: number | null;
  quantity_quintals: number;
  transport_mode: string;
  vehicle_type: string;
  vehicle_capacity_quintals: number;
  trips: number;
  distance_km: number;
  distance_method: string;
  cost_per_km: number;
  fixed_cost: number;
  loading_cost: number;
  unloading_cost: number;
  total_cost: number;
  cost_per_quintal: number;
  cost_per_kg: number;
  is_approximate: boolean;
  provider: string;
  notes: string | null;
  created_at: string;
}

export interface VehicleOption {
  type: string;
  label: string;
  capacity_quintals: number;
  cost_per_km_inr: number;
  fixed_cost_inr: number;
  loading_cost_inr: number;
  unloading_cost_inr: number;
}

export interface DecisionFactor {
  factor: string;
  direction: string;
  weight: number | null;
  value: number | null;
  description: string;
}

export interface BuyerEvaluation {
  buyer_id: number;
  buyer_name: string;
  buyer_is_demo: boolean;
  offer_id: number;
  offered_price_per_quintal: number;
  offer_expiry: string;
  offer_freshness_days: number;
  quantity_quintals: number;
  eligible: boolean;
  ineligibility_reasons: string[];
  distance_km: number | null;
  distance_method: string | null;
  transport_cost: number | null;
  trips: number | null;
  gross_revenue: number | null;
  commission: number | null;
  other_selling_costs: number | null;
  net_realization: number | null;
  net_realization_per_quintal: number | null;
  risk_score: number;
  risk_adjusted_net: number | null;
  rank: number | null;
}

export interface Decision {
  id: number;
  farm_id: number;
  crop_id: number;
  action: "SELL" | "WAIT" | "INSPECT";
  selected_buyer_id: number | null;
  selected_offer_id: number | null;
  selected_buyer_name: string | null;
  expected_yield_quintals: number;
  yield_low_quintals: number | null;
  yield_high_quintals: number | null;
  expected_price_per_quintal: number | null;
  price_low_per_quintal: number | null;
  price_high_per_quintal: number | null;
  gross_revenue: number | null;
  transport_cost: number | null;
  other_costs: number | null;
  net_realization: number | null;
  net_realization_per_quintal: number | null;
  wait_expected_net: number | null;
  risk_score: number;
  risk_category: string;
  data_completeness: number;
  confidence: number;
  policy_version: string;
  explanation: string;
  inputs_snapshot: Record<string, any>;
  outputs: Record<string, any>;
  generated_at: string;
  factors: DecisionFactor[];
  buyer_evaluations: BuyerEvaluation[];
  missing_inputs: string[];
  assumptions: string[];
  data_freshness: Record<string, any>;
}

export interface DecisionListItem {
  id: number;
  action: string;
  farm_id: number;
  crop_id: number;
  selected_buyer_name: string | null;
  net_realization: number | null;
  risk_score: number;
  risk_category: string;
  generated_at: string;
}

export interface DashboardOverview {
  total_farms: number;
  total_area_hectares: number;
  active_crops: number;
  crop_health: {
    available: boolean;
    prediction_id: number | null;
    predicted_label: string | null;
    crop: string | null;
    confidence: number | null;
    severity: number | null;
    is_healthy: boolean | null;
    predicted_at: string | null;
    is_demo: boolean;
  };
  yield_prediction: {
    available: boolean;
    prediction_id: number | null;
    crop: string | null;
    yield_per_hectare: number | null;
    total_quintals: number | null;
    lower_total_quintals: number | null;
    upper_total_quintals: number | null;
    input_completeness: number | null;
    predicted_at: string | null;
  };
  market: {
    available: boolean;
    crop: string | null;
    market: string | null;
    latest_price: number | null;
    forecast_price: number | null;
    lower_bound: number | null;
    upper_bound: number | null;
    latest_observation_date: string | null;
    data_freshness_days: number | null;
    is_demo: boolean;
  };
  decision: {
    available: boolean;
    decision_id: number | null;
    action: string | null;
    selected_buyer_name: string | null;
    net_realization: number | null;
    net_realization_per_quintal: number | null;
    risk_score: number | null;
    risk_category: string | null;
    generated_at: string | null;
  };
  farms: {
    id: number;
    name: string;
    district: string;
    state: string;
    total_area_hectares: number;
    active_crops: number;
    is_demo: boolean;
  }[];
  data_mode: string;
  is_demo: boolean;
  generated_at: string;
  notices: string[];
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  category: string;
  is_read: boolean;
  created_at: string;
}

export interface Report {
  id: number;
  report_type: string;
  title: string;
  summary: string | null;
  payload: Record<string, any>;
  created_at: string;
}

export interface ModelStatus {
  name: string;
  available: boolean;
  mode: string;
  version: string | null;
  message: string | null;
}

export interface SystemStatus {
  app: string;
  version: string;
  environment: string;
  demo_mode: boolean;
  data_mode: string;
  database_backend: string;
  models: ModelStatus[];
  providers: Record<string, { name: string; configured: boolean; requires_key: boolean }>;
  notices: string[];
  server_time: string;
}

export interface SystemOptions {
  crops: string[];
  states: string[];
  seasons: string[];
  growth_stages: string[];
  soil_types: string[];
  buyer_types: string[];
  vehicle_types: string[];
  transport_modes: string[];
  risk_preferences: string[];
  units: Record<string, string>;
  demo_mode: boolean;
}

export interface WeatherDaily {
  date: string;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  rainfall_mm: number | null;
  wind_max_kmh: number | null;
}

export interface WeatherResponse {
  available: boolean;
  source: string;
  latitude: number;
  longitude: number;
  location_source: string;
  coordinates_approximate: boolean;
  current: {
    temperature_c: number | null;
    humidity_pct: number | null;
    rainfall_mm: number | null;
    wind_speed_kmh: number | null;
    observed_at: string | null;
  };
  daily: WeatherDaily[];
  risk_score: number;
  risk_label: string;
  fetched_at: string;
  farm_id: number;
}

export interface DecisionPolicy {
  version: string;
  finance: Record<string, number>;
  risk: Record<string, any>;
  policy: Record<string, any>;
  freshness: Record<string, any>;
  notes: string;
}

export interface YieldHistory {
  crop: string;
  state: string | null;
  years: { year: number; yield_per_hectare: number; production_quintals?: number }[];
  unit: string;
}
