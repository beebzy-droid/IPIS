# Notebooks

Exploration notebooks. **Not production code.**

Notebooks are for:
- Data exploration and EDA
- Quick experiments and prototyping
- One-off analysis tasks
- Visualization development

Anything that needs to be repeated, tested, or deployed moves into `src/ipis/`.

## Conventions

- Number notebooks in the order they're meant to be read: `01_`, `02_`, ...
- Clear all outputs before committing — keep diffs reviewable
- If a notebook is producing important figures, save them to `models/` or `docs/`
- Don't import from other notebooks — import from `src/ipis/`

## Planned notebooks

| Notebook | Status | Purpose |
|---|---|---|
| `01_debutanizer_eda.ipynb` | TODO | Initial Debutanizer data exploration |
| `02_baseline_models.ipynb` | TODO | PLS / XGBoost / LSTM baseline comparison |
| `03_dwsim_validation.ipynb` | TODO | DWSIM Debutanizer column model validation |
| `04_physics_residual_analysis.ipynb` | TODO | Where does the physics model err? |
| `05_pinn_loss_sweep.ipynb` | TODO | λ_physics sensitivity analysis |
| `06_drift_simulation.ipynb` | TODO | Synthetic drift injection and detection |
| `07_tep_transfer_experiment.ipynb` | TODO | Cross-process transfer protocol |
| `08_secom_stress_test.ipynb` | TODO | Framework limits on high-dim data |

## Running notebooks

```bash
# Install Jupyter (already in dev deps)
pip install -e ".[dev]"

# Register the IPIS kernel
python -m ipykernel install --user --name ipis --display-name "IPIS"

# Launch
jupyter lab
```
