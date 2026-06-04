"""Model-migration methods for Phase 1C (within-TEP regime transfer).

Verified against the primary (source-map Tier-1): Lu & Gao (2008a),
Ind. Eng. Chem. Res. 47(6) 1967 -- the scale-and-bias-correction (SBC) lineage,
core form y_new = S_O * f_o(S_I * x + B_I) + B_O. This module implements the
output-only special case (OSBC):

    y_new(x) = S_O * f_o(x) + B_O

fit by least squares on the target-regime data, where f_o is the source-regime
model. OSBC corrects a global affine offset/scale between regimes with TWO
parameters -- the fewest-data, interpretable floor of the migration study. If the
regime difference is offset-dominated (TEP modes differ mainly by product-G
level), OSBC alone recovers most of the transfer gap.

The Migrator protocol is method-agnostic: fit(X, source_pred, y) / predict(X,
source_pred). OSBC uses only source_pred; the upcoming Yan functional SBC
(s(x)*f_o + GP bias) and Luo matrix SBC use X as well -- same interface, so the
data-fraction sweep harness is shared across all three methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Migrator(Protocol):
    """Common interface for migration methods (OSBC, functional SBC, matrix SBC)."""

    def fit(
        self, X: np.ndarray, source_pred: np.ndarray, y: np.ndarray, source_fn=None
    ) -> Migrator:
        """Fit the correction from target features, source predictions, target labels."""
        ...

    def predict(self, X: np.ndarray, source_pred: np.ndarray, source_fn=None) -> np.ndarray:
        """Apply the fitted correction to source predictions on target features."""
        ...


@dataclass
class OSBCParams:
    """Fitted output-only scale-and-bias parameters."""

    scale: float  # S_O
    bias: float  # B_O


class LuOSBC:
    """Lu & Gao (2008a) output-only scale-and-bias correction.

    y_new = S_O * f_o(x) + B_O, least-squares fit of target labels on source
    predictions. Ignores X (the correction is a function of the source output
    only); kept in the signature for Migrator-interface compatibility.
    """

    def __init__(self) -> None:
        self.params_: OSBCParams | None = None

    def fit(self, X: np.ndarray, source_pred: np.ndarray, y: np.ndarray, source_fn=None) -> LuOSBC:
        sp = np.asarray(source_pred, dtype=float).ravel()
        yt = np.asarray(y, dtype=float).ravel()
        if sp.shape[0] != yt.shape[0]:
            raise ValueError(f"length mismatch: source_pred {sp.shape[0]} vs y {yt.shape[0]}")
        if sp.shape[0] < 2:
            raise ValueError("OSBC needs >= 2 target samples to fit scale+bias.")
        # least-squares y = S_O * sp + B_O
        A = np.column_stack([sp, np.ones_like(sp)])
        (s_o, b_o), *_ = np.linalg.lstsq(A, yt, rcond=None)
        self.params_ = OSBCParams(scale=float(s_o), bias=float(b_o))
        return self

    def predict(self, X: np.ndarray, source_pred: np.ndarray, source_fn=None) -> np.ndarray:
        if self.params_ is None:
            raise RuntimeError("LuOSBC.predict called before fit.")
        sp = np.asarray(source_pred, dtype=float).ravel()
        return self.params_.scale * sp + self.params_.bias
