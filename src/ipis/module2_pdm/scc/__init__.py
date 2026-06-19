"""Similarity-Calibrated Conformal (SCC): dimensionless conformal calibration with a
physics-derived, a-priori coverage certificate for transfer across operating regimes.

- deactivation: controlled catalyst-deactivation testbed (genuine similitude),
- conformal:    SCC scores, naive-vs-SCC coverage, TV distance,
- diagnostic:   3-way similitude verdict (holds / violated / indeterminate).
"""

from ipis.module2_pdm.scc.conformal import (
    coverage_naive,
    coverage_scc,
    nominal_rate,
    one_sided_quantile,
    score_run,
    scores_for,
    tv_distance,
)
from ipis.module2_pdm.scc.deactivation import (
    A_FAIL,
    DeactivationRun,
    R,
    effective_rate,
    life_at,
    simulate_condition,
)
from ipis.module2_pdm.scc.diagnostic import FEMTO_COND, P_EXP, diagnose, l10_ratio

__all__ = [
    "R",
    "A_FAIL",
    "DeactivationRun",
    "effective_rate",
    "life_at",
    "simulate_condition",
    "nominal_rate",
    "score_run",
    "scores_for",
    "one_sided_quantile",
    "coverage_naive",
    "coverage_scc",
    "tv_distance",
    "FEMTO_COND",
    "P_EXP",
    "l10_ratio",
    "diagnose",
]
