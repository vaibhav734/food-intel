// Thin typed wrapper around the backend API.
// In dev, requests go via the Vite proxy at /api/* → http://localhost:8000.
// In prod, set VITE_API_BASE to the full URL of the deployed API.

import type { AnalyzeRequest, AnalyzeResponse, ProductPrefill } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    // Network-level error — server unreachable, DNS failure, CORS blocked, etc.
    throw new ApiError(
      "Could not reach the analysis server.",
      0,
      err instanceof Error ? err.message : String(err),
    );
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail =
        typeof body?.detail === "string"
          ? body.detail
          : JSON.stringify(body?.detail ?? body);
    } catch {
      // Response was not JSON — leave detail undefined
    }
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

export const api = {
  analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
    return request<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },
  getProduct(barcode: string): Promise<AnalyzeResponse> {
    const safe = encodeURIComponent(barcode);
    return request<AnalyzeResponse>(`/product/${safe}`);
  },
  prefillProduct(barcode: string): Promise<ProductPrefill> {
    const safe = encodeURIComponent(barcode);
    return request<ProductPrefill>(`/product/prefill/${safe}`);
  },
  health(): Promise<{ status: string }> {
    return request<{ status: string }>("/health");
  },
};
