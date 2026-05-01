<script setup lang="ts">
import { computed } from "vue";
import type { Verdict } from "@/types/api";

const props = defineProps<{
  score: number;
  verdict: Verdict;
}>();

// Map verdict → semantic color tier.
// Excellent + Good = green, Moderate = yellow, Limit = red.
const tier = computed<"green" | "yellow" | "red">(() => {
  switch (props.verdict) {
    case "Excellent":
    case "Good":
      return "green";
    case "Moderate":
      return "yellow";
    case "Limit":
      return "red";
  }
});
</script>

<template>
  <div class="score-display" :data-tier="tier" role="img"
       :aria-label="`Score ${score} out of 10, ${verdict}`">
    <div class="score-circle">
      <span class="score-number">{{ score }}</span>
      <span class="score-out-of">/ 10</span>
    </div>
    <div class="verdict-label">{{ verdict }}</div>
  </div>
</template>

<style scoped>
.score-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
}

.score-circle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 8.5rem;
  height: 8.5rem;
  border-radius: 50%;
  border: 6px solid var(--tier-color);
  background: var(--tier-bg);
  transition: border-color 0.2s ease, background 0.2s ease;
}

.score-number {
  font-size: 3.5rem;
  font-weight: 700;
  line-height: 1;
  color: var(--tier-color);
}

.score-out-of {
  font-size: 0.875rem;
  color: var(--color-fg-muted);
  margin-top: 0.25rem;
}

.verdict-label {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--tier-color);
  letter-spacing: 0.02em;
}

/* Tier colors set on the wrapper so children can pick them up via var() */
.score-display[data-tier="green"] {
  --tier-color: #16a34a;
  --tier-bg: #f0fdf4;
}
.score-display[data-tier="yellow"] {
  --tier-color: #d97706;
  --tier-bg: #fffbeb;
}
.score-display[data-tier="red"] {
  --tier-color: #dc2626;
  --tier-bg: #fef2f2;
}
</style>
