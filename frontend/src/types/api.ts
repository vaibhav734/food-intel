// API response types — mirror backend/api/schemas.py.
// Keep this file in sync with that one. When the backend bumps its API
// version, this is the file that should change first to drive the UI updates.

export type Verdict = "Excellent" | "Good" | "Moderate" | "Limit";
export type Confidence = "high" | "medium" | "low";
export type SourceType = "guideline" | "label-derived" | "computed";

export interface Source {
  org: string;
  type: SourceType;
  doc?: string | null;
}

export interface Reason {
  rule_id: string;
  text: string;
  delta: number;
  source: Source;
  observed_value?: number | null;
  threshold?: number | null;
}

export interface Scoring {
  score: number;
  raw_score: number;
  verdict: Verdict;
  reasons: Reason[];
  confidence: Confidence;
  completeness: number;
  missing_fields: string[];
  rules_version: string;
  data_unavailable: boolean;
  age_safety?: AgeSafety | null;
}

export interface AgeSafety {
  min_age_months?: number | null
  max_age_months?: number | null
  label: string
  safe: boolean
}

export interface AnalyzeResponse {
  product_name: string;
  barcode?: string | null;
  scoring: Scoring;
  explanation: string;
  nutrition: NutritionInput;
}

// Request shape — used by the form
export interface NutritionInput {
  calories_kcal?: number;
  sugar_g?: number;
  saturated_fat_g?: number;
  sodium_mg?: number;
  protein_g?: number;
  fiber_g?: number;
  serving_size_g?: number;
}

export interface AnalyzeRequest {
  name: string;
  barcode?: string;
  nutrition: NutritionInput;
  ingredients_raw?: string;
  nova_class?: number;
  product_type?: string;
}

export interface ProductPrefill {
  name: string;
  barcode: string;
  calories_kcal?: number | null;
  sugar_g?: number | null;
  saturated_fat_g?: number | null;
  sodium_mg?: number | null;
  protein_g?: number | null;
  fiber_g?: number | null;
  serving_size_g?: number | null;
  ingredients_raw?: string | null;
  nova_class?: number | null;
  product_type: string;
}
