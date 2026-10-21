"""Baselines at the label horizon for claim N1'' (pre-registration Sec. 5.3 and Appendix A).

One import point for the two baselines: conformal PID control (``baselines_pid``) and SPCI
(``baselines_spci``). Each module states its sources, timing convention and modes.
``source_sha256`` gives the SHA-256 of the three files, which the evidence scripts record with
their results so that each result names the code that produced it.
"""

import hashlib
from pathlib import Path

from ipis.module1_soft_sensor.evaluation.baselines_pid import (
    MODES,
    PID_C_SAT_AUTHORS,
    PID_DELTA,
    PID_K_FACTORS,
    PID_M_GRID,
    PID_QR_LAGS,
    PID_SCORECAST_MIN,
    PID_WARM_ROWS,
    PID_WINDOW,
    conformal_pid_intervals,
    conformal_pid_side,
    gaussian_width_factor,
    matched_scorecasts,
    pid_c_sat,
    pid_c_sat_grid,
    pid_c_sat_purpose,
    pid_integrator,
    pid_scorecasts,
    pid_tan,
    pid_tune_pooled,
    qr_scorecasts,
    select_pid_config,
    theta_forecast_table,
    uninformative_width,
)
from ipis.module1_soft_sensor.evaluation.baselines_spci import (
    SPCI_BINS,
    SPCI_TRAIN_ELECTRIC,
    SPCI_WINDOW,
    QuantileForest,
    _weighted_quantile_presorted,
    spci_block,
    spci_fit_predict,
    spci_quantile_levels,
    spci_rolling,
    spci_window,
)

SOURCES = ("baselines.py", "baselines_pid.py", "baselines_spci.py")


def source_sha256() -> dict[str, str]:
    """SHA-256 of the baseline source files as they are on disk, keyed by their path in the
    repository."""
    here = Path(__file__).resolve().parent
    return {
        f"src/ipis/module1_soft_sensor/evaluation/{name}": hashlib.sha256(
            (here / name).read_bytes()
        ).hexdigest()
        for name in SOURCES
    }


__all__ = [
    "MODES",
    "PID_C_SAT_AUTHORS",
    "PID_DELTA",
    "PID_K_FACTORS",
    "PID_M_GRID",
    "PID_QR_LAGS",
    "PID_SCORECAST_MIN",
    "PID_WARM_ROWS",
    "PID_WINDOW",
    "QuantileForest",
    "SOURCES",
    "SPCI_BINS",
    "SPCI_TRAIN_ELECTRIC",
    "SPCI_WINDOW",
    "_weighted_quantile_presorted",
    "conformal_pid_intervals",
    "conformal_pid_side",
    "gaussian_width_factor",
    "matched_scorecasts",
    "pid_c_sat",
    "pid_c_sat_grid",
    "pid_c_sat_purpose",
    "pid_integrator",
    "pid_scorecasts",
    "pid_tan",
    "pid_tune_pooled",
    "qr_scorecasts",
    "select_pid_config",
    "source_sha256",
    "spci_block",
    "spci_fit_predict",
    "spci_quantile_levels",
    "spci_rolling",
    "spci_window",
    "theta_forecast_table",
    "uninformative_width",
]
