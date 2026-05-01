# Render Deployment Guide

This repo includes a Render Blueprint at [`render.yaml`](../render.yaml).

Use it to deploy:

- `food-intel-api` as a Render web service
- `food-intel-web` as a Render static site

## 1. Prerequisites

- Your code is pushed to GitHub, GitLab, or Bitbucket
- You have a Render account

## 2. Create the Blueprint

In Render:

1. Click `New +`
2. Click `Blueprint`
3. Connect your repo
4. Select this repository
5. Render should detect [`render.yaml`](../render.yaml)

## 3. Services Created

The Blueprint creates:

- `food-intel-api`
- `food-intel-web`

Backend settings come from `backend/`.
Frontend settings come from `frontend/`.
Because the Render service uses `rootDir: frontend`, the static publish path is `dist`.

## 4. Required Environment Variables

During initial setup, Render should prompt you for:

- `FOOD_INTEL_CORS_ORIGINS`
- `VITE_API_BASE`

Use these values:

### `VITE_API_BASE`

Set this to your backend public URL:

```text
https://food-intel-api.onrender.com
```

If Render gives your backend a slightly different name, use that exact URL instead.

Do not add `/api` here. The frontend calls the backend directly on Render.

### `FOOD_INTEL_CORS_ORIGINS`

Set this to your frontend public URL:

```text
https://food-intel-web.onrender.com
```

If Render gives your frontend a slightly different name, use that exact URL instead.

## 5. Default Backend Behavior

The Blueprint sets:

- `FOOD_INTEL_LLM_PROVIDER=null`
- `FOOD_INTEL_ENABLE_OPENFOODFACTS=true`

That means:

- scoring works without an LLM key
- explanations use the deterministic null provider
- barcode lookup remains enabled

If you want LLM-backed explanations later, add one of these in Render:

- `FOOD_INTEL_OPENAI_API_KEY`
- `FOOD_INTEL_ANTHROPIC_API_KEY`

And change:

- `FOOD_INTEL_LLM_PROVIDER=openai`
  or
- `FOOD_INTEL_LLM_PROVIDER=anthropic`

## 6. Verify the Deployment

After deploy finishes:

### Backend

Open:

```text
https://food-intel-api.onrender.com/health
```

Expected response:

```json
{"status":"ok"}
```

You can also check:

```text
https://food-intel-api.onrender.com/docs
```

### Frontend

Open:

```text
https://food-intel-web.onrender.com
```

You should see the Vue app load and analyze requests should go to the backend URL above.

## 7. Common Issue

### Frontend loads but API calls fail

Check:

- `VITE_API_BASE` points to the backend Render URL
- `FOOD_INTEL_CORS_ORIGINS` points to the frontend Render URL

If you update either value, trigger a redeploy for the affected service.

## 8. Mobile App

Before building the Android APK, update:

[`mobile/lib/config.dart`](../mobile/lib/config.dart)

Replace:

```dart
const String kApiBase = 'https://YOUR_DOMAIN/api';
```

With your backend Render URL:

```dart
const String kApiBase = 'https://food-intel-api.onrender.com';
```

Use your actual backend hostname if Render assigned a different one.

This mobile URL should be the backend root URL, not `/api`.
