"""Data-fraction sweep harness for Phase-1C migration (method-agnostic).

Quantifies the central 1C claim: a migrated source model reaches full-retrain
target accuracy with <30% of the target data a from-scratch model needs.

Protocol (all curves evaluated on the SAME held-out target test block):
  - bar = from-scratch (same model class) trained on the FULL target pool.
  - migrated(f) = source model + migrator, the migrator fit on the first f% of
    the target pool (time-ordered).
  - from_scratch_same(f), from_scratch_generic(f) = comparator curves trained on
    the same f% slice (same physics features, and the generic lagged features).
  - crossover = smallest f where migrated(f) >= bar.

Per-split feature building (each slice/test built independently) avoids
cross-split lag-alignment issues. source_predict(df) must apply the fixed source
model on the SAME physics features used here, so its output aligns with y.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from ipis.module1_soft_sensor.evaluation.bias_update import apply_bias_update
from ipis.module1_soft_sensor.migration.sbc import Migrator

FeatureBuilder = Callable[[pd.DataFrame], tuple[pd.DataFrame, pd.Series]]
SourcePredict = Callable[[pd.DataFrame], np.ndarray]
EstimatorFactory = Callable[[], object]  # returns an unfitted sklearn-like estimator


@dataclass
class SweepResult:
    fractions: list[float]
    migrated_r2: list[float]
    from_scratch_same_r2: list[float]
    from_scratch_generic_r2: list[float] = field(default_factory=list)
    bar_same_r2: float = float("nan")  # from-scratch same-class at 100% pool
    bar_generic_r2: float = float("nan")
    crossover_fraction: float | None = None  # min f where migrated >= bar_same
    migrated_r2_std: list[float] = field(default_factory=list)  # std over repeats
    migrated_coverage: list[float] = field(default_factory=list)  # 95% interval coverage
    migrated_width: list[float] = field(default_factory=list)  # mean 95% interval width
    target_level: float = 0.90  # fraction of the bar used as the target performance
    migrated_data_fraction: float | None = None  # f for migrated to reach target
    from_scratch_data_fraction: float | None = None  # f for from-scratch to reach target
    data_efficiency: float | None = None  # fs_fraction / migrated_fraction (>1 = migration wins)

    def summary(self) -> str:
        lines = [f"  from-scratch (same class) @100% pool = bar: R2 {self.bar_same_r2:+.3f}"]
        if not np.isnan(self.bar_generic_r2):
            lines.append(
                f"  from-scratch (generic)    @100% pool:     R2 {self.bar_generic_r2:+.3f}"
            )
        has_cov = bool(self.migrated_coverage)
        lines.append(
            "  f%    migrated   fs-same   fs-generic" + ("   cover  width" if has_cov else "")
        )
        for i, f in enumerate(self.fractions):
            g = (
                f"{self.from_scratch_generic_r2[i]:+.3f}"
                if self.from_scratch_generic_r2
                else "   -  "
            )
            row = (
                f"  {f*100:4.0f}  {self.migrated_r2[i]:+.3f}    "
                f"{self.from_scratch_same_r2[i]:+.3f}    {g}"
            )
            if self.migrated_r2_std and self.migrated_r2_std[i] > 0:
                row = (
                    f"  {f*100:4.0f}  {self.migrated_r2[i]:+.3f}±{self.migrated_r2_std[i]:.2f}  "
                    f"{self.from_scratch_same_r2[i]:+.3f}    {g}"
                )
            if has_cov:
                row += f"   {self.migrated_coverage[i]*100:4.0f}%  {self.migrated_width[i]:.2f}"
            lines.append(row)
        xo = "none" if self.crossover_fraction is None else f"{self.crossover_fraction*100:.0f}%"
        lines.append(f"  => crossover (migrated >= from-scratch-100%): {xo}")
        # robust headline: data efficiency to reach target_level of the bar
        tgt = self.target_level * self.bar_same_r2
        mf = (
            "none"
            if self.migrated_data_fraction is None
            else f"{self.migrated_data_fraction*100:.0f}%"
        )
        ff = (
            "none"
            if self.from_scratch_data_fraction is None
            else f"{self.from_scratch_data_fraction*100:.0f}%"
        )
        eff = "n/a" if self.data_efficiency is None else f"{self.data_efficiency:.1f}x"
        lines.append(
            f"  => to reach {self.target_level*100:.0f}% of bar (R2 {tgt:+.3f}): "
            f"migrated {mf} vs from-scratch {ff}  => {eff} data efficiency"
        )
        if has_cov:
            lines.append(
                "  (cover/width = migrated 95% GP-posterior interval coverage & mean width)"
            )
        return "\n".join(lines)


def _r2_clip(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """R^2 with extreme negatives clipped (off-scale extrapolation is uninformative)."""
    r = r2_score(y_true, y_pred)
    return float(max(r, -10.0))


def _score(y_true: np.ndarray, y_pred: np.ndarray, bias_update: tuple[float, int] | None) -> float:
    """R^2, optionally after the online Shardt bias-update (two-layer composition).

    When bias_update=(lam, theta) is given, the prediction stream is corrected
    online using only delayed labels before scoring -- removing within-mode drift
    from EVERY curve so the comparison isolates regime transfer.
    """
    if bias_update is not None:
        lam, theta = bias_update
        y_pred, _ = apply_bias_update(y_true, y_pred, lam=lam, delay=theta)
    return _r2_clip(y_true, y_pred)


def data_fraction_sweep(
    pool_df: pd.DataFrame,
    test_df: pd.DataFrame,
    source_predict: SourcePredict,
    physics_builder: FeatureBuilder,
    migrator_factory: Callable[[], Migrator],
    fractions: Sequence[float],
    *,
    same_class_factory: EstimatorFactory,
    generic_builder: FeatureBuilder | None = None,
    generic_factory: EstimatorFactory | None = None,
    bias_update: tuple[float, int] | None = None,
    n_repeats: int = 1,
    random_state: int = 0,
    target_level: float = 0.90,
    source_fn=None,
) -> SweepResult:
    """Run the data-fraction sweep for one migration method on one target regime.

    If bias_update=(lam, theta) is given, the 1B online bias-update is applied to
    every prediction stream (migrated, from-scratch, bars) before scoring -- the
    migration(offline) + bias-update(online) two-layer composition.

    n_repeats=1 uses the first f% of the (time-ordered) pool -- the realistic
    "data collected so far" view. n_repeats>1 instead averages over that many
    RANDOM f%-sized subsets of the pool and reports mean +/- std, giving honest
    error bars on small-fraction estimates (where a single draw is high-variance).
    """
    Xte, yte = physics_builder(test_df)
    yte = np.asarray(yte, dtype=float).ravel()
    sp_te = np.asarray(source_predict(test_df), dtype=float).ravel()

    # bar: from-scratch same-class on the full pool
    Xpool, ypool = physics_builder(pool_df)
    bar_model = same_class_factory().fit(Xpool, np.asarray(ypool).ravel())
    bar_same = _score(yte, bar_model.predict(Xte), bias_update)

    bar_generic = float("nan")
    Xte_g = yte_g = None
    if generic_builder is not None and generic_factory is not None:
        Xpool_g, ypool_g = generic_builder(pool_df)
        Xte_g, yte_g = generic_builder(test_df)
        yte_g = np.asarray(yte_g, dtype=float).ravel()
        gmodel = generic_factory().fit(Xpool_g, np.asarray(ypool_g).ravel())
        bar_generic = _score(yte_g, gmodel.predict(Xte_g), bias_update)

    migrated, fs_same, fs_generic = [], [], []
    migrated_std, mig_cov, mig_width = [], [], []
    n_pool = len(pool_df)
    rng = np.random.default_rng(random_state)
    use_generic = generic_builder is not None and generic_factory is not None

    def _eval_slice(slice_df: pd.DataFrame) -> tuple[float, float, float, float, float]:
        """Fit migration + from-scratch on one slice; return their test scores."""
        Xs, ys = physics_builder(slice_df)
        ys = np.asarray(ys, dtype=float).ravel()
        sp_s = np.asarray(source_predict(slice_df), dtype=float).ravel()
        mig = migrator_factory().fit(np.asarray(Xs), sp_s, ys, source_fn=source_fn)
        mig_pred = mig.predict(np.asarray(Xte), sp_te, source_fn=source_fn)
        r_mig = _score(yte, mig_pred, bias_update)
        std = getattr(mig, "last_std_", None)
        if std is not None:
            std = np.asarray(std, dtype=float).ravel()
            cov = float(np.mean(np.abs(yte - mig_pred) <= 1.96 * std))
            wid = float(np.mean(2 * 1.96 * std))
        else:
            cov = wid = float("nan")
        r_same = _score(yte, same_class_factory().fit(Xs, ys).predict(Xte), bias_update)
        r_gen = float("nan")
        if use_generic:
            Xsg, ysg = generic_builder(slice_df)
            r_gen = _score(
                yte_g,
                generic_factory().fit(Xsg, np.asarray(ysg).ravel()).predict(Xte_g),
                bias_update,
            )
        return r_mig, r_same, r_gen, cov, wid

    for f in fractions:
        n = max(2, int(round(f * n_pool)))
        if n_repeats <= 1:
            slices = [pool_df.iloc[:n]]  # realistic "first f% collected so far"
        else:
            slices = [
                pool_df.iloc[np.sort(rng.choice(n_pool, size=n, replace=False))]
                for _ in range(n_repeats)
            ]
        rows = np.array([_eval_slice(s) for s in slices], dtype=float)  # (reps, 5)
        migrated.append(float(np.nanmean(rows[:, 0])))
        migrated_std.append(float(np.nanstd(rows[:, 0])) if n_repeats > 1 else 0.0)
        fs_same.append(float(np.nanmean(rows[:, 1])))
        if use_generic:
            fs_generic.append(float(np.nanmean(rows[:, 2])))
        if not np.isnan(rows[:, 3]).all():
            mig_cov.append(float(np.nanmean(rows[:, 3])))
            mig_width.append(float(np.nanmean(rows[:, 4])))

    crossover = next((f for f, r in zip(fractions, migrated, strict=True) if r >= bar_same), None)

    # robust metric: data fraction to reach target_level of the bar (avoids the
    # knife-edge "exceed the ceiling" crossover when ceilings coincide)
    def _frac_to_reach(curve: list[float], target: float) -> float | None:
        return next((f for f, r in zip(fractions, curve, strict=True) if r >= target), None)

    mig_frac = fs_frac = efficiency = None
    if bar_same > 0:
        target = target_level * bar_same
        mig_frac = _frac_to_reach(migrated, target)
        fs_frac = _frac_to_reach(fs_same, target)
        if mig_frac is not None and fs_frac is not None and mig_frac > 0:
            efficiency = float(fs_frac / mig_frac)

    return SweepResult(
        fractions=list(fractions),
        migrated_r2=migrated,
        from_scratch_same_r2=fs_same,
        from_scratch_generic_r2=fs_generic,
        bar_same_r2=bar_same,
        bar_generic_r2=bar_generic,
        crossover_fraction=crossover,
        migrated_r2_std=migrated_std,
        migrated_coverage=mig_cov,
        migrated_width=mig_width,
        target_level=target_level,
        migrated_data_fraction=mig_frac,
        from_scratch_data_fraction=fs_frac,
        data_efficiency=efficiency,
    )
