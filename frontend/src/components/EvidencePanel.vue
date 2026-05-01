<script setup lang="ts">
import { ref } from "vue";
import type { Scoring } from "@/types/api";

defineProps<{
  scoring: Scoring;
}>();

const expanded = ref(false);
</script>

<template>
  <details class="evidence-panel" :open="expanded" @toggle="expanded = ($event.target as HTMLDetailsElement).open">
    <summary>
      <span>Show evidence and rule details</span>
      <span class="chevron" aria-hidden="true">{{ expanded ? "▲" : "▼" }}</span>
    </summary>

    <div class="content">
      <dl class="meta-grid">
        <dt>Raw score</dt>
        <dd>{{ scoring.raw_score.toFixed(2) }} (before clamp/round)</dd>

        <dt>Rules version</dt>
        <dd>{{ scoring.rules_version }}</dd>

        <dt>Data completeness</dt>
        <dd>{{ Math.round(scoring.completeness * 100) }}%</dd>

        <dt v-if="scoring.missing_fields.length">Missing fields</dt>
        <dd v-if="scoring.missing_fields.length">
          {{ scoring.missing_fields.join(", ") }}
        </dd>
      </dl>

      <p class="disclaimer">
        Scores are based on per-100g comparisons against published guidelines
        from organizations like WHO, FDA, USDA, and EFSA. This tool does not
        provide medical or dietary advice.
      </p>
    </div>
  </details>
</template>

<style scoped>
.evidence-panel {
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-card-bg);
  overflow: hidden;
}

summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0.875rem;
  cursor: pointer;
  user-select: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-fg);
}

summary::-webkit-details-marker {
  display: none;
}

.chevron {
  font-size: 0.625rem;
  color: var(--color-fg-muted);
}

.content {
  padding: 0.25rem 0.875rem 0.875rem;
  border-top: 1px solid var(--color-border);
}

.meta-grid {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.5rem 1rem;
  margin: 0.875rem 0;
  font-size: 0.875rem;
}

.meta-grid dt {
  color: var(--color-fg-muted);
  font-weight: 500;
}

.meta-grid dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg);
}

.disclaimer {
  margin: 0.75rem 0 0;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.75rem;
  color: var(--color-fg-muted);
  line-height: 1.5;
}
</style>
