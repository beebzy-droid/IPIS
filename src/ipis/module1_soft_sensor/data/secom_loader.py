"""SECOM loader + screening + virtual-metrology target selection (Phase 1E.1).

UCI SECOM: 1567 samples x 590 anonymized sensor features from a semiconductor line
(2008-07-19 -> 2008-10-17), a pass/fail label (-1 pass, +1 fail; 104 fails = 6.6%),
~4.5% missing cells, 32 features >40% missing, 116 near-constant features. It is the
deliberate stress test: p ~ n, heavy missingness, severe imbalance, and NO physics
anchors — the no-physics negative control for the IPIS pipeline.

Module 1's machinery (ADR-008 bias-update, ADR-010 ACI) is regression, so SECOM is
framed as VIRTUAL METROLOGY (ratified D1): one continuous measurement is held out as
the soft-sensor target, selected by transparent, auditable criteria
(:func:`select_vm_target`), and the pass/fail label is kept as auxiliary validation
only (never as a feature).

File formats (exact UCI):
  - ``secom.data``        — 590 space-separated columns, missing = the token ``NaN``
  - ``secom_labels.data`` — ``label "dd/mm/yyyy HH:MM:SS"`` (quoted datetime)
Timestamps are monotonic but contain duplicates (33 in the canonical file); row order
is preserved and never re-sorted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

N_FEATURES = 590
FAIL_COL = "fail"
TIME_COL = "timestamp"


# --------------------------------------------------------------------------- #
# Loader                                                                      #
# --------------------------------------------------------------------------- #
class SECOMLoader:
    """Load the two UCI SECOM files into one time-ordered DataFrame."""

    def load(self, features_path: str | Path, labels_path: str | Path) -> pd.DataFrame:
        """Return a DataFrame with columns x0..x589 + ``fail`` and a ``timestamp`` column.

        Row order is the file order (already time-ordered); duplicates in the
        timestamp are tolerated and order is NOT re-sorted.
        """
        x = pd.read_csv(features_path, sep=r"\s+", header=None)
        if x.shape[1] != N_FEATURES:
            raise ValueError(f"expected {N_FEATURES} feature columns, got {x.shape[1]}")
        x.columns = [f"x{i}" for i in range(N_FEATURES)]

        lab = pd.read_csv(
            labels_path, sep=" ", header=None, names=["label", "datetime"], quotechar='"'
        )
        if len(lab) != len(x):
            raise ValueError(f"feature rows ({len(x)}) != label rows ({len(lab)})")
        ts = pd.to_datetime(lab["datetime"], format="%d/%m/%Y %H:%M:%S", errors="raise")

        df = x.copy()
        df[FAIL_COL] = lab["label"].astype(int) == 1
        df[TIME_COL] = ts.to_numpy()
        return df


# --------------------------------------------------------------------------- #
# Unsupervised screen (label-free; applied once, before any CV)               #
# --------------------------------------------------------------------------- #
@dataclass
class ScreenResult:
    kept: list[str]
    dropped_missing: list[str] = field(default_factory=list)
    dropped_constant: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"kept {len(self.kept)} / dropped {len(self.dropped_missing)} (missing) "
            f"+ {len(self.dropped_constant)} (near-constant)"
        )


def unsupervised_screen(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    max_missing: float = 0.40,
    min_std: float = 1e-8,
) -> ScreenResult:
    """Drop features by missingness then near-zero variance. LABEL-FREE by design:
    these filters never see ``fail`` or any target, so applying them once on the full
    data introduces no selection leakage. Supervised screening (the elastic net) must
    instead live inside CV folds."""
    cols = feature_cols or [c for c in df.columns if c.startswith("x")]
    miss = df[cols].isna().mean()
    dropped_missing = miss[miss > max_missing].index.tolist()
    rest = [c for c in cols if c not in dropped_missing]
    std = df[rest].std(skipna=True)
    dropped_constant = std[(std < min_std) | std.isna()].index.tolist()
    kept = [c for c in rest if c not in dropped_constant]
    return ScreenResult(
        kept=kept, dropped_missing=dropped_missing, dropped_constant=dropped_constant
    )


# --------------------------------------------------------------------------- #
# Virtual-metrology target selection (transparent, auditable)                 #
# --------------------------------------------------------------------------- #
@dataclass
class TargetSelection:
    target: str
    audit: pd.DataFrame  # per-candidate: missing_frac, std, abs_r_fail (sorted)
    criteria: dict


def select_vm_target(
    df: pd.DataFrame,
    candidate_cols: list[str],
    max_missing: float = 0.05,
    top_k: int = 10,
) -> TargetSelection:
    """Choose the virtual-metrology target by stated criteria (ratified D1).

    Criteria, in order: the candidate must be reliably measured (missingness <=
    ``max_missing``) and non-degenerate (std > 0); among those, choose the feature
    with the highest |point-biserial correlation| with the pass/fail label — i.e. the
    continuous measurement most associated with final yield, which is exactly the
    quantity a virtual-metrology sensor would be built to predict and skip measuring.

    The fail label is used ONLY here, to pick the target — it is never a model
    feature, and target selection happens before any model fitting, so this is a
    problem-definition step, not training-time supervision.
    """
    fail = df[FAIL_COL].astype(float)
    rows = []
    for c in candidate_cols:
        s = df[c]
        miss = float(s.isna().mean())
        std = float(s.std(skipna=True))
        if miss > max_missing or not np.isfinite(std) or std <= 0:
            continue
        # point-biserial == Pearson against the 0/1 label, on non-missing rows
        ok = s.notna()
        r = float(np.corrcoef(s[ok].to_numpy(float), fail[ok].to_numpy())[0, 1])
        if not np.isfinite(r):
            continue
        rows.append({"feature": c, "missing_frac": miss, "std": std, "abs_r_fail": abs(r)})
    if not rows:
        raise ValueError("no candidate satisfies the target criteria")
    audit = pd.DataFrame(rows).sort_values("abs_r_fail", ascending=False).reset_index(drop=True)
    return TargetSelection(
        target=str(audit.loc[0, "feature"]),
        audit=audit.head(top_k),
        criteria={"max_missing": max_missing, "rank_by": "abs point-biserial r with fail"},
    )
