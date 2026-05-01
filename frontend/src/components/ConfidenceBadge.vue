<script setup lang="ts">
import { computed } from "vue";
import type { Confidence } from "@/types/api";

const props = defineProps<{
  confidence: Confidence;
  completeness: number;        // 0..1
  missingFields: string[];
}>();

const label = computed(() => {
  switch (props.confidence) {
    case "high":   return "High confidence";
    case "medium": return "Medium confidence";
    case "low":    return "Low confidence";
  }
});

const tooltip = computed(() => {
  const pct = Math.round(props.completeness * 100);
  if (props.missingFields.length === 0) {
    return `${pct}% of expected data fields were provided.`;
  }
  return `${pct}% of expected data fields were provided. Missing: ${props.missingFields.join(", ")}.`;
});
</script>

<template>
  <div class="confidence-badge" :data-level="confidence" :title="tooltip">
    <span class="dot" aria-hidden="true"></span>
    <span class="label">{{ label }}</span>
  </div>
</template>

<style scoped>
.confidence-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.8125rem;
  font-weight: 500;
  border: 1px solid var(--badge-border);
  background: var(--badge-bg);
  color: var(--badge-fg);
}

.dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--badge-fg);
}

.confidence-badge[data-level="high"] {
  --badge-bg: #f0fdf4;
  --badge-border: #bbf7d0;
  --badge-fg: #166534;
}
.confidence-badge[data-level="medium"] {
  --badge-bg: #fffbeb;
  --badge-border: #fde68a;
  --badge-fg: #92400e;
}
.confidence-badge[data-level="low"] {
  --badge-bg: #fef2f2;
  --badge-border: #fecaca;
  --badge-fg: #991b1b;
}
</style>
