# Soft-sensor serving image (Phase 1D.2d).
# Lean: installs only requirements-serving.txt (no torch/mlflow/streamlit/...).
# The default model is the synthetic fixture, regenerated INSIDE the image so its
# pickle matches the image's numpy/sklearn versions (no cross-version load issues).
# For a real deployment, mount a bundle and set IPIS_MODEL_BUNDLE, or set
# IPIS_MLFLOW_MODEL to an MLflow artifact URI.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Dependencies first (layer caching).
COPY requirements-serving.txt .
RUN pip install --no-cache-dir -r requirements-serving.txt

# Application code + the fixture builder.
COPY src/ ./src/
COPY scripts/register_model.py ./scripts/register_model.py

# Build the default model bundle in-image (version-consistent; no data needed).
RUN python scripts/register_model.py --fixture

# Drop privileges.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness via stdlib (no curl in slim).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "ipis.module1_soft_sensor.serving.main:app", "--host", "0.0.0.0", "--port", "8000"]
