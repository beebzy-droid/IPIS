#!/usr/bin/env bash
# Run Phase 1A — Hybrid model on Debutanizer
#
# Trains baselines (PLS, XGBoost, LSTM) and the Path B hybrid model on the
# Debutanizer dataset, logging everything to MLflow.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "============================================"
echo "  IPIS Module 1 — Phase 1A"
echo "  Hybrid model on Debutanizer"
echo "============================================"

# Ensure data exists
if [ ! -f "data/raw/debutanizer/debutanizer.dat" ]; then
    echo "ERROR: Debutanizer dataset not found."
    echo "Run: python scripts/download_datasets.py --dataset debutanizer"
    exit 1
fi

# Train all baselines
echo ""
echo ">>> Training PLS baseline..."
python -m ipis.module1_soft_sensor.pipelines.train \
    +dataset=debutanizer +model=pls

echo ""
echo ">>> Training XGBoost baseline..."
python -m ipis.module1_soft_sensor.pipelines.train \
    +dataset=debutanizer +model=xgboost

echo ""
echo ">>> Training LSTM baseline..."
python -m ipis.module1_soft_sensor.pipelines.train \
    +dataset=debutanizer +model=lstm

echo ""
echo ">>> Training Path B hybrid model..."
python -m ipis.module1_soft_sensor.pipelines.train \
    +dataset=debutanizer +model=hybrid_pathb

# Evaluate all models on test set
echo ""
echo ">>> Running evaluation..."
python -m ipis.module1_soft_sensor.pipelines.evaluate \
    +dataset=debutanizer \
    +models=[pls,xgboost,lstm,hybrid_pathb]

echo ""
echo "============================================"
echo "  Phase 1A complete."
echo "  Results: see MLflow UI (mlflow ui --port 5000)"
echo "  Next: update docs/module1/results.md"
echo "============================================"
