<script setup lang="ts">
import ScanView from "@/views/ScanView.vue";
</script>

<template>
  <ScanView />
</template>

<!-- Global CSS — design tokens + reset. Not scoped on purpose. -->
<style>
:root {
  --color-bg: #ffffff;
  --color-card-bg: #f8fafc;
  --color-fg: #0f172a;
  --color-fg-muted: #64748b;
  --color-border: #e2e8f0;
  --color-accent: #2563eb;
  --color-accent-hover: #1d4ed8;
  --color-tag-bg: #e0e7ff;
  --color-tag-fg: #3730a3;

  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  color-scheme: light;
}

* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  background: var(--color-card-bg);
  color: var(--color-fg);
  min-height: 100vh;
}

#app {
  min-height: 100vh;
}

button {
  font-family: inherit;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f172a;
    --color-card-bg: #1e293b;
    --color-fg: #f1f5f9;
    --color-fg-muted: #94a3b8;
    --color-border: #334155;
    --color-accent: #3b82f6;
    --color-accent-hover: #2563eb;
    --color-tag-bg: #1e3a8a;
    --color-tag-fg: #bfdbfe;
    color-scheme: dark;
  }
}
</style>
