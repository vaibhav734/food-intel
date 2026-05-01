FROM python:3.12-slim

WORKDIR /app

# Editable installs need the source tree present at install time
# (pyproject.toml's [tool.setuptools.packages.find] points at src/),
# so we copy the project first, then install.
COPY pyproject.toml ./
COPY src/ ./src/

# `[api]` brings the HTTP server (fastapi, uvicorn, pydantic-settings, httpx).
# To enable LLM-backed explanations, override LLM_PROVIDER + add an SDK:
#   build arg LLM_EXTRA=anthropic  →  installs the anthropic SDK
#   build arg LLM_EXTRA=openai     →  installs the openai SDK
#   build arg LLM_EXTRA=           →  null provider only (default, fully offline)
ARG LLM_EXTRA=""
RUN if [ -n "$LLM_EXTRA" ]; then \
        pip install --no-cache-dir -e ".[api,${LLM_EXTRA}]"; \
    else \
        pip install --no-cache-dir -e ".[api]"; \
    fi

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Bind 0.0.0.0 so the container is reachable from outside
CMD ["uvicorn", "food_intel.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
