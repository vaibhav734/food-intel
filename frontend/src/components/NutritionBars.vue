<script setup lang="ts">
defineProps<{
  nutrition: {
    calories_kcal?: number | null
    sugar_g?: number | null
    saturated_fat_g?: number | null
    sodium_mg?: number | null
    protein_g?: number | null
    fiber_g?: number | null
  }
}>();

interface NutrientDef {
  key: string
  label: string
  unit: string
  max: number
  low: number    // below = green (for lowerIsBetter) or red (for higherIsBetter)
  high: number   // above = red (for lowerIsBetter) or green (for higherIsBetter)
  lowerIsBetter: boolean
  icon: string
}

const NUTRIENTS: NutrientDef[] = [
  { key: "calories_kcal",   label: "Calories",        unit: "kcal", max: 600,  low: 150, high: 400, lowerIsBetter: true,  icon: "🔥" },
  { key: "sugar_g",         label: "Sugar",           unit: "g",    max: 50,   low: 5,   high: 22,  lowerIsBetter: true,  icon: "🍬" },
  { key: "saturated_fat_g", label: "Saturated fat",   unit: "g",    max: 20,   low: 1.5, high: 5,   lowerIsBetter: true,  icon: "🧈" },
  { key: "sodium_mg",       label: "Sodium",          unit: "mg",   max: 1500, low: 120, high: 600, lowerIsBetter: true,  icon: "🧂" },
  { key: "protein_g",       label: "Protein",         unit: "g",    max: 30,   low: 5,   high: 10,  lowerIsBetter: false, icon: "💪" },
  { key: "fiber_g",         label: "Fiber",           unit: "g",    max: 15,   low: 1.5, high: 3,   lowerIsBetter: false, icon: "🌾" },
];

function color(def: NutrientDef, value: number): string {
  if (def.lowerIsBetter) {
    if (value <= def.low)  return "#16a34a";
    if (value <= def.high) return "#d97706";
    return "#dc2626";
  } else {
    if (value >= def.high) return "#16a34a";
    if (value >= def.low)  return "#d97706";
    return "#dc2626";
  }
}

function label(def: NutrientDef, value: number): string {
  if (def.lowerIsBetter) {
    if (value <= def.low)  return "Low";
    if (value <= def.high) return "Medium";
    return "High";
  } else {
    if (value >= def.high) return "Good";
    if (value >= def.low)  return "Moderate";
    return "Low";
  }
}

function pct(def: NutrientDef, value: number): number {
  return Math.min((value / def.max) * 100, 100);
}

function fmt(v: number): string {
  return v % 1 === 0 ? String(v) : v.toFixed(1);
}
</script>

<template>
  <div class="nutrition-bars">
    <h4>Nutrition per 100g</h4>
    <p class="legend">Green is better, amber is mixed, red needs attention.</p>
    <div v-for="def in NUTRIENTS" :key="def.key" class="row">
      <div class="row-header">
        <span class="icon">{{ def.icon }}</span>
        <span class="name">{{ def.label }}</span>
        <template v-if="(nutrition as any)[def.key] != null">
          <div class="bar-track">
            <div class="bar-fill"
              :style="{ width: pct(def, (nutrition as any)[def.key]) + '%', background: color(def, (nutrition as any)[def.key]) }"
            ></div>
          </div>
          <span class="value" :style="{ color: color(def, (nutrition as any)[def.key]) }">
            {{ fmt((nutrition as any)[def.key]) }}{{ def.unit }}
          </span>
          <span class="tag" :style="{ background: color(def, (nutrition as any)[def.key]) + '22', color: color(def, (nutrition as any)[def.key]) }">
            {{ label(def, (nutrition as any)[def.key]) }}
          </span>
        </template>
        <template v-else>
          <div class="bar-track"><div class="bar-fill" style="width:0"></div></div>
          <span class="no-data">—</span>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nutrition-bars h4 {
  margin: 0 0 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-fg);
}

.legend {
  margin: 0 0 0.875rem;
  font-size: 0.8125rem;
  color: var(--color-fg-muted);
}

.row { margin-bottom: 0.625rem; }

.row-header {
  display: grid;
  grid-template-columns: 1.25rem 7rem 1fr auto auto;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.icon { text-align: center; }
.name { font-weight: 500; color: var(--color-fg); white-space: nowrap; }

.bar-track {
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.value { font-variant-numeric: tabular-nums; color: var(--color-fg-muted); white-space: nowrap; }
.no-data { color: var(--color-fg-muted); }

.tag {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  white-space: nowrap;
}
</style>
