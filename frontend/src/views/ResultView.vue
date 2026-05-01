<script setup lang="ts">
import { useAnalysisStore } from "@/stores/analysis";
import ScoreDisplay from "@/components/ScoreDisplay.vue";
import ConfidenceBadge from "@/components/ConfidenceBadge.vue";
import ReasonList from "@/components/ReasonList.vue";
import EvidencePanel from "@/components/EvidencePanel.vue";
import NutritionBars from "@/components/NutritionBars.vue";

const store = useAnalysisStore();

function ageLabel(months: number): string {
  if (months < 12) return `${months}m`;
  const y = Math.floor(months / 12);
  const m = months % 12;
  return m ? `${y}y ${m}m` : `${y}y`;
}
</script>

<template>
  <!-- Empty state -->
  <div v-if="store.status === 'idle'" class="empty-state">
    <p>Enter a product on the left to see its score, key reasons, and a
       plain-language explanation.</p>
  </div>

  <!-- Loading state -->
  <div v-else-if="store.status === 'loading'" class="loading-state">
    <div class="spinner" aria-hidden="true"></div>
    <p>Analyzing…</p>
  </div>

  <!-- Error state -->
  <div v-else-if="store.status === 'error'" class="error-state" role="alert">
    <h3>Analysis failed</h3>
    <p>{{ store.errorMessage }}</p>
    <p v-if="store.errorDetail" class="detail">{{ store.errorDetail }}</p>
    <button class="retry" @click="store.reset()">Try again</button>
  </div>

  <!-- Success state -->
  <div v-else-if="store.result" class="result">
    <h3 class="product-name">{{ store.result.product_name }}</h3>

    <!-- No data available -->
    <div v-if="store.result.scoring.data_unavailable" class="no-data">
      <span class="no-data-icon">📭</span>
      <p>No nutrition data available for this product.</p>
      <p class="no-data-hint">Try entering nutrition details manually for a full analysis.</p>
    </div>

    <!-- Normal result -->
    <template v-else>
      <ScoreDisplay
        :score="store.result.scoring.score"
        :verdict="store.result.scoring.verdict"
      />

      <div class="badges">
        <ConfidenceBadge
          :confidence="store.result.scoring.confidence"
          :completeness="store.result.scoring.completeness"
          :missing-fields="store.result.scoring.missing_fields"
        />
      </div>

      <!-- Age safety — only for baby/infant products -->
      <div v-if="store.result.scoring.age_safety"
           class="age-safety"
           :class="store.result.scoring.age_safety.safe ? 'safe' : 'unsafe'">
        <span class="age-icon">{{ store.result.scoring.age_safety.safe ? '✅' : '⚠️' }}</span>
        <div>
          <strong>{{ store.result.scoring.age_safety.label }}</strong>
          <span v-if="store.result.scoring.age_safety.min_age_months != null || store.result.scoring.age_safety.max_age_months != null"
                class="age-range">
            ({{ store.result.scoring.age_safety.min_age_months != null ? ageLabel(store.result.scoring.age_safety.min_age_months) : '0' }}
            –
            {{ store.result.scoring.age_safety.max_age_months != null ? ageLabel(store.result.scoring.age_safety.max_age_months) : '∞' }})
          </span>
        </div>
      </div>

      <NutritionBars :nutrition="store.result.nutrition" />

      <p class="explanation">{{ store.result.explanation }}</p>

      <section class="reasons-section">
        <h4>Key reasons</h4>
        <ReasonList :reasons="store.result.scoring.reasons" />
      </section>

      <EvidencePanel :scoring="store.result.scoring" />
    </template>
  </div>
</template>

<style scoped>
.empty-state,
.loading-state,
.error-state {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-fg-muted);
}

.empty-state p {
  margin: 0;
  line-height: 1.5;
  font-size: 0.9375rem;
}

.loading-state .spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 0.75rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
}

.error-state h3 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
}

.error-state p {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
}

.error-state .detail {
  font-size: 0.8125rem;
  opacity: 0.8;
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.error-state .retry {
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #991b1b;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.result {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.product-name {
  margin: 0;
  text-align: center;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-fg);
}

.badges {
  display: flex;
  justify-content: center;
}

.explanation {
  margin: 0;
  padding: 0.875rem 1rem;
  background: var(--color-card-bg);
  border-radius: 0.5rem;
  border-left: 3px solid var(--color-accent);
  line-height: 1.55;
  font-size: 0.9375rem;
  color: var(--color-fg);
}

.reasons-section h4 {
  margin: 0 0 0.625rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-fg);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.no-data {
  text-align: center;
  padding: 1.5rem 1rem;
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
}

.no-data-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.75rem;
}

.no-data p {
  margin: 0 0 0.375rem;
  font-weight: 500;
  color: var(--color-fg);
}

.no-data-hint {
  font-size: 0.875rem;
  color: var(--color-fg-muted) !important;
  font-weight: 400 !important;
}

.age-safety {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}
.age-safety.safe   { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.age-safety.unsafe { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
.age-icon { font-size: 1.25rem; }
.age-range { margin-left: 0.25rem; opacity: 0.75; }
</style>
