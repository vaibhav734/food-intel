<script setup lang="ts">
import { useAnalysisStore } from "@/stores/analysis";
import ScanInput from "@/components/ScanInput.vue";
import ResultView from "@/views/ResultView.vue";
import type { AnalyzeRequest } from "@/types/api";

const store = useAnalysisStore();

function onSubmitManual(payload: AnalyzeRequest): void {
  void store.analyze(payload);
}

function onSubmitBarcode(barcode: string): void {
  void store.lookupBarcode(barcode);
}
</script>

<template>
  <div class="scan-view">
    <header class="page-header">
      <h1>Food Intelligence</h1>
      <p>
        Analyze packaged food using ingredient and nutrition data. Scores are
        rule-based and source-cited — never medical advice.
      </p>
    </header>

    <main class="layout">
      <section class="panel input-panel">
        <h2 class="panel-title">Enter product</h2>
        <ScanInput
          :loading="store.status === 'loading'"
          @submit-manual="onSubmitManual"
          @submit-barcode="onSubmitBarcode"
        />
      </section>

      <section class="panel result-panel">
        <h2 class="panel-title">Result</h2>
        <ResultView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.scan-view {
  max-width: 64rem;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  color: var(--color-fg);
}

.page-header p {
  margin: 0;
  color: var(--color-fg-muted);
  font-size: 0.9375rem;
  line-height: 1.5;
  max-width: 36rem;
  margin: 0 auto;
}

.layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 56rem) {
  .layout {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: start;
  }
}

.panel {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 1.25rem;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 1rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-fg);
}
</style>
