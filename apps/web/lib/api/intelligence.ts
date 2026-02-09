import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PriceBenchmark {
  impa_code: string;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  quote_count: number;
  has_data: boolean;
  currency: string;
  period_days: number;
}

export interface BudgetEstimate {
  low: number;
  likely: number;
  high: number;
  items_with_data: number;
  items_without_data: number;
  currency: string;
}

export interface SupplierMatch {
  supplier_id: string;
  organization_id: string;
  organization_name: string;
  tier: string;
  score: number;
  coverage_score: number;
  is_recommended: boolean;
}

export interface SupplierMatchResult {
  total_count: number;
  verified_plus_count: number;
  recommended: SupplierMatch[];
  other: SupplierMatch[];
  single_source_risk: boolean;
}

export interface RiskFlag {
  risk_type: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  message: string;
  details: Record<string, unknown> | null;
}

export interface TimingAdvice {
  recommendation: string;
  optimal_window_days: number;
  vessel_eta: string | null;
  timeline_assessment: "sufficient" | "tight" | "risky";
  avg_response_days: number | null;
}

export interface IntelligenceResponse {
  suppliers: SupplierMatchResult | null;
  price_benchmarks: PriceBenchmark[];
  budget_estimate: BudgetEstimate | null;
  risk_flags: RiskFlag[];
  timing: TimingAdvice | null;
}

// ---------------------------------------------------------------------------
// Query params
// ---------------------------------------------------------------------------

export interface IntelligenceParams {
  delivery_port?: string;
  impa_codes?: string;
  vessel_id?: string;
  delivery_date?: string;
  bidding_deadline?: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

const INTELLIGENCE_BASE = "/api/v1/intelligence";

export async function getCombinedIntelligence(
  params: IntelligenceParams,
): Promise<IntelligenceResponse> {
  return apiClient.get<IntelligenceResponse>(
    INTELLIGENCE_BASE,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export async function getPriceBenchmarks(params: {
  impa_codes: string;
  delivery_port?: string;
  days?: number;
}): Promise<PriceBenchmark[]> {
  return apiClient.get<PriceBenchmark[]>(
    `${INTELLIGENCE_BASE}/price-benchmarks`,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export async function getSupplierMatches(params: {
  delivery_port: string;
  impa_codes?: string;
  min_tier?: string;
}): Promise<SupplierMatchResult> {
  return apiClient.get<SupplierMatchResult>(
    `${INTELLIGENCE_BASE}/suppliers`,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export async function getRiskFlags(params: {
  delivery_port?: string;
  delivery_date?: string;
  vessel_id?: string;
  impa_codes?: string;
  bidding_deadline?: string;
}): Promise<RiskFlag[]> {
  return apiClient.get<RiskFlag[]>(
    `${INTELLIGENCE_BASE}/risks`,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export async function getTimingAdvice(params: {
  delivery_port?: string;
  delivery_date?: string;
  bidding_deadline?: string;
  vessel_id?: string;
}): Promise<TimingAdvice> {
  return apiClient.get<TimingAdvice>(
    `${INTELLIGENCE_BASE}/timing`,
    params as Record<string, string | number | boolean | undefined>,
  );
}
