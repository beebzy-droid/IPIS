# Models Directory

This directory holds saved model artifacts. **Contents are gitignored.**

## Structure

- `checkpoints/` — Training checkpoints, intermediate model states
- `production/` — Models promoted to production via MLflow Model Registry

## MLflow Model Registry

Production models are versioned in MLflow. The `production/` directory is a
local mirror for fast inference; the canonical source of truth is the MLflow
registry at `${MLFLOW_TRACKING_URI}`.

## Model promotion workflow

1. Train model → automatically logged to MLflow
2. Evaluate against minimum-viable metrics (see `docs/module1/results.md`)
3. Promote to `Staging` in MLflow Registry
4. Run shadow inference against production for 24 hours
5. Promote to `Production` if metrics hold
6. Sync to `production/` directory for serving

## Naming convention

```
production/
├── soft_sensor_v{major}.{minor}.{patch}/
│   ├── model.pt              # PyTorch state dict
│   ├── config.yaml           # Hydra config used for training
│   ├── conformal_calib.npz   # Conformal prediction calibration
│   └── metadata.json         # Training metrics, dataset hash, git SHA
```
