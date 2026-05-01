<script setup lang="ts">
import { computed } from "vue";
import type { Reason } from "@/types/api";

const props = defineProps<{
  reasons: Reason[];
}>();

// Sort reasons by impact magnitude (biggest first) so the most important
// reasons surface at the top regardless of original rule order.
const ordered = computed(() =>
  [...props.reasons].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)),
);

function deltaSign(delta: number): string {
  if (delta > 0) return "+";
  return ""; // negatives include their own minus sign
}

function deltaTier(delta: number): "positive" | "negative" {
  return delta >= 0 ? "positive" : "negative";
}
</script>

<template>
  <div v-if="ordered.length === 0" class="empty">
    No specific rule hits — score reflects baseline.
  </div>
  <ul v-else class="reason-list">
    <li v-for="r in ordered" :key="r.rule_id" class="reason">
      <div class="reason-header">
        <span class="reason-text">{{ r.text }}</span>
        <span class="reason-delta" :data-tier="deltaTier(r.delta)">
          {{ deltaSign(r.delta) }}{{ r.delta.toFixed(2) }}
        </span>
      </div>
      <div class="reason-meta">
        <span class="source-badge" :title="r.source.doc ?? ''">
          {{ r.source.org }}
        </span>
        <span v-if="r.observed_value !== null && r.observed_value !== undefined"
              class="observed">
          observed: {{ r.observed_value }}
        </span>
      </div>
    </li>
  </ul>
</template>

<style scoped>
.empty {
  padding: 1rem;
  text-align: center;
  color: var(--color-fg-muted);
  font-style: italic;
  font-size: 0.9375rem;
}

.reason-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.reason {
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 0.75rem 0.875rem;
}

.reason-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.reason-text {
  font-weight: 500;
  color: var(--color-fg);
  line-height: 1.35;
}

.reason-delta {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: 0.875rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.375rem;
}
.reason-delta[data-tier="negative"] {
  color: #dc2626;
  background: #fef2f2;
}
.reason-delta[data-tier="positive"] {
  color: #16a34a;
  background: #f0fdf4;
}

.reason-meta {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-top: 0.4rem;
  font-size: 0.8125rem;
  color: var(--color-fg-muted);
}

.source-badge {
  display: inline-block;
  padding: 0.0625rem 0.5rem;
  border-radius: 0.25rem;
  background: var(--color-tag-bg);
  color: var(--color-tag-fg);
  font-weight: 500;
  font-size: 0.75rem;
  letter-spacing: 0.02em;
}

.observed {
  font-variant-numeric: tabular-nums;
}
</style>
