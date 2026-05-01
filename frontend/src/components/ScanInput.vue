<script setup lang="ts">
import { ref, reactive } from "vue";
import type { AnalyzeRequest, ProductPrefill } from "@/types/api";
import { api, ApiError } from "@/api/client";

type Mode = "manual" | "barcode";

const emit = defineEmits<{
  submitManual: [payload: AnalyzeRequest];
  submitBarcode: [barcode: string];
}>();

const props = defineProps<{
  loading: boolean;
}>();

const mode = ref<Mode>("manual");
const barcode = ref("");
const prefillLoading = ref(false);
const prefillError = ref<string | null>(null);

const form = reactive<{
  name: string;
  sugar_g: string;
  saturated_fat_g: string;
  sodium_mg: string;
  protein_g: string;
  fiber_g: string;
  serving_size_g: string;
  ingredients_raw: string;
  nova_class: string;
  product_type: string;
  barcode: string;
}>({
  name: "",
  sugar_g: "",
  saturated_fat_g: "",
  sodium_mg: "",
  protein_g: "",
  fiber_g: "",
  serving_size_g: "",
  ingredients_raw: "",
  nova_class: "",
  product_type: "food",
  barcode: "",
});

function parseNumber(s: string): number | undefined {
  if (s.trim() === "") return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
}

function applyPrefill(p: ProductPrefill): void {
  form.name = p.name;
  form.barcode = p.barcode;
  form.sugar_g = p.sugar_g != null ? String(p.sugar_g) : "";
  form.saturated_fat_g = p.saturated_fat_g != null ? String(p.saturated_fat_g) : "";
  form.sodium_mg = p.sodium_mg != null ? String(p.sodium_mg) : "";
  form.protein_g = p.protein_g != null ? String(p.protein_g) : "";
  form.fiber_g = p.fiber_g != null ? String(p.fiber_g) : "";
  form.serving_size_g = p.serving_size_g != null ? String(p.serving_size_g) : "";
  form.ingredients_raw = p.ingredients_raw ?? "";
  form.nova_class = p.nova_class != null ? String(p.nova_class) : "";
  form.product_type = p.product_type ?? "food";
}

async function lookupBarcode(): Promise<void> {
  if (!barcode.value.trim()) return;
  prefillLoading.value = true;
  prefillError.value = null;
  try {
    const prefill = await api.prefillProduct(barcode.value.trim());
    applyPrefill(prefill);
    mode.value = "manual";
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      // Not in OFF — fall back to direct barcode submit
      emit("submitBarcode", barcode.value.trim());
    } else {
      prefillError.value = "Could not fetch product data. Try manual entry.";
    }
  } finally {
    prefillLoading.value = false;
  }
}

function handleSubmit(): void {
  if (mode.value === "barcode") {
    lookupBarcode();
    return;
  }

  if (!form.name.trim()) return;

  const novaNum = parseNumber(form.nova_class);
  const payload: AnalyzeRequest = {
    name: form.name.trim(),
    barcode: form.barcode || undefined,
    nutrition: {
      sugar_g: parseNumber(form.sugar_g),
      saturated_fat_g: parseNumber(form.saturated_fat_g),
      sodium_mg: parseNumber(form.sodium_mg),
      protein_g: parseNumber(form.protein_g),
      fiber_g: parseNumber(form.fiber_g),
      serving_size_g: parseNumber(form.serving_size_g),
    },
    ingredients_raw: form.ingredients_raw.trim() || undefined,
    nova_class:
      novaNum !== undefined && novaNum >= 1 && novaNum <= 4 ? novaNum : undefined,
    product_type: form.product_type || "food",
  };
  emit("submitManual", payload);
}

function loadDemo(): void {
  mode.value = "manual";
  form.name = "Sugar-Frosted Corn Cereal";
  form.barcode = "";
  form.sugar_g = "25";
  form.saturated_fat_g = "2";
  form.sodium_mg = "450";
  form.protein_g = "7";
  form.fiber_g = "4";
  form.serving_size_g = "30";
  form.ingredients_raw = "corn, sugar, glucose syrup, salt, color (E150a), BHT";
  form.nova_class = "4";
  form.product_type = "food";
}
</script>

<template>
  <form class="scan-input" @submit.prevent="handleSubmit">
    <div class="mode-toggle" role="tablist">
      <button
        type="button"
        role="tab"
        :aria-selected="mode === 'manual'"
        :class="{ active: mode === 'manual' }"
        @click="mode = 'manual'"
      >
        Manual entry
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="mode === 'barcode'"
        :class="{ active: mode === 'barcode' }"
        @click="mode = 'barcode'"
      >
        Barcode
      </button>
    </div>

    <!-- Barcode mode -->
    <div v-if="mode === 'barcode'" class="form-section">
      <label class="field">
        <span>Barcode</span>
        <input
          v-model="barcode"
          type="text"
          inputmode="numeric"
          placeholder="e.g. 5449000000996"
          pattern="\d+"
          required
          :disabled="loading || prefillLoading"
        />
      </label>
      <p v-if="prefillError" class="hint error">{{ prefillError }}</p>
      <p v-else class="hint">
        Looks up the product via Open Food Facts and pre-fills the form.
      </p>
    </div>

    <!-- Manual mode -->
    <div v-else class="form-section">
      <label class="field">
        <span>Product name</span>
        <input
          v-model="form.name"
          type="text"
          placeholder="e.g. Plain Rolled Oats"
          required
          :disabled="loading"
        />
      </label>

      <fieldset>
        <legend>Nutrition (per 100g)</legend>
        <div class="grid">
          <label class="field">
            <span>Sugar (g)</span>
            <input v-model="form.sugar_g" type="number" min="0" step="0.1" :disabled="loading" />
          </label>
          <label class="field">
            <span>Saturated fat (g)</span>
            <input v-model="form.saturated_fat_g" type="number" min="0" step="0.1" :disabled="loading" />
          </label>
          <label class="field">
            <span>Sodium (mg)</span>
            <input v-model="form.sodium_mg" type="number" min="0" step="1" :disabled="loading" />
          </label>
          <label class="field">
            <span>Protein (g)</span>
            <input v-model="form.protein_g" type="number" min="0" step="0.1" :disabled="loading" />
          </label>
          <label class="field">
            <span>Fiber (g)</span>
            <input v-model="form.fiber_g" type="number" min="0" step="0.1" :disabled="loading" />
          </label>
          <label class="field">
            <span>Serving size (g)</span>
            <input v-model="form.serving_size_g" type="number" min="0" step="1" :disabled="loading" />
          </label>
        </div>
      </fieldset>

      <label class="field">
        <span>Ingredients (as printed on label)</span>
        <textarea
          v-model="form.ingredients_raw"
          rows="3"
          placeholder="wheat flour, sugar, palm oil, ..."
          :disabled="loading"
        ></textarea>
      </label>

      <label class="field">
        <span>NOVA classification (optional, 1–4)</span>
        <input
          v-model="form.nova_class"
          type="number"
          min="1"
          max="4"
          step="1"
          placeholder="4 = ultra-processed"
          :disabled="loading"
        />
      </label>
    </div>

    <div class="actions">
      <button type="submit" class="primary" :disabled="loading || prefillLoading">
        {{ prefillLoading ? "Looking up…" : loading ? "Analyzing…" : mode === "barcode" ? "Look up & Fill" : "Analyze" }}
      </button>
      <button v-if="mode === 'manual'" type="button" class="secondary"
              :disabled="loading" @click="loadDemo">
        Load demo data
      </button>
    </div>
  </form>
</template>

<style scoped>
.scan-input {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mode-toggle {
  display: flex;
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 0.25rem;
  gap: 0.25rem;
}

.mode-toggle button {
  flex: 1;
  padding: 0.5rem;
  border: none;
  background: transparent;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-fg-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.mode-toggle button.active {
  background: var(--color-bg);
  color: var(--color-fg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  font-size: 0.875rem;
}

.field span {
  color: var(--color-fg);
  font-weight: 500;
}

input,
textarea {
  font: inherit;
  width: 100%;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--color-border);
  border-radius: 0.375rem;
  background: var(--color-bg);
  color: var(--color-fg);
  box-sizing: border-box;
}

input:focus,
textarea:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
  border-color: var(--color-accent);
}

input:disabled,
textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

textarea {
  resize: vertical;
  min-height: 4.5rem;
  font-family: inherit;
}

fieldset {
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 0.875rem;
  margin: 0;
}

fieldset legend {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-fg);
  padding: 0 0.375rem;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.625rem;
}

.hint {
  font-size: 0.8125rem;
  color: var(--color-fg-muted);
  margin: 0;
}

.hint.error {
  color: #dc2626;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

button.primary,
button.secondary {
  font: inherit;
  padding: 0.625rem 1rem;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
}

button.primary {
  flex: 1;
  background: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
}
button.primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

button.secondary {
  background: var(--color-bg);
  color: var(--color-fg);
  border: 1px solid var(--color-border);
}
button.secondary:hover:not(:disabled) {
  background: var(--color-card-bg);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
