// Analysis store — holds the current request lifecycle.
//
// State machine:
//   idle → loading → success
//                  → error
//
// The store owns the "what was requested" and "what came back" so any
// component can read it without re-fetching. Reset on new submissions.

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { AnalyzeRequest, AnalyzeResponse } from "@/types/api";
import { api, ApiError } from "@/api/client";

export type AnalysisStatus = "idle" | "loading" | "success" | "error";

export const useAnalysisStore = defineStore("analysis", () => {
  const status = ref<AnalysisStatus>("idle");
  const result = ref<AnalyzeResponse | null>(null);
  const errorMessage = ref<string | null>(null);
  const errorDetail = ref<string | null>(null);

  const hasResult = computed(() => status.value === "success" && result.value !== null);

  async function analyze(payload: AnalyzeRequest): Promise<void> {
    status.value = "loading";
    errorMessage.value = null;
    errorDetail.value = null;
    result.value = null;
    try {
      result.value = await api.analyze(payload);
      status.value = "success";
    } catch (err) {
      status.value = "error";
      if (err instanceof ApiError) {
        errorMessage.value = err.message;
        errorDetail.value = err.detail ?? null;
      } else {
        errorMessage.value =
          err instanceof Error ? err.message : "An unknown error occurred.";
      }
    }
  }

  async function lookupBarcode(barcode: string): Promise<void> {
    status.value = "loading";
    errorMessage.value = null;
    errorDetail.value = null;
    result.value = null;
    try {
      // Direct backend barcode lookup (fallback when OFF doesn't have the product)
      result.value = await api.getProduct(barcode);
      status.value = "success";
    } catch (err) {
      status.value = "error";
      if (err instanceof ApiError) {
        errorMessage.value = err.status === 404
          ? `No product found for barcode ${barcode}.`
          : err.status === 503
          ? `Product lookup not available. Try manual entry.`
          : err.message;
        errorDetail.value = err.detail ?? null;
      } else {
        errorMessage.value = err instanceof Error ? err.message : "An unknown error occurred.";
      }
    }
  }

  function reset(): void {
    status.value = "idle";
    result.value = null;
    errorMessage.value = null;
    errorDetail.value = null;
  }

  return {
    status,
    result,
    errorMessage,
    errorDetail,
    hasResult,
    analyze,
    lookupBarcode,
    reset,
  };
});
