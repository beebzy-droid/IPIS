"""SPCI at the label horizon: a baseline for claim N1'' (pre-registration Sec. 5.3 and
Appendix A).

Xu and Xie (ICML 2023): a quantile random forest on windows of past residuals of the compensated
loop's point model, refitted as residuals arrive, with the narrowest interval over a grid of
quantile pairs. A residual is used only once its label has arrived; at the issue of the interval
for sample t the newest is r_{t-h}, with h = theta + 1 (timing of ``delayed_aci``).

Sources (pinned): the paper, and where it is silent the authors' code, hamrel-cxu/SPCI-code at
commit d598dd3, with sklearn-quantile 0.0.29 for the forest. ``spci_block`` reproduces
``SPCI_and_EnbPI.compute_PIs_Ensemble_online(use_SPCI=True)`` given the same residuals and
random state; ``spci_rolling`` is the constant-delay version Phase 1 uses.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from sklearn.ensemble import RandomForestRegressor


def _bootstrap_counts(forest: RandomForestRegressor, n: int) -> list[np.ndarray]:
    """In-bag count of every training sample, per tree, as drawn when the forest was grown.
    scikit-learn >= 1.4 exposes the draws as ``estimators_samples_``; before that, the private
    ``_generate_sample_indices(seed, n_samples, n_samples_bootstrap)`` regenerates them, as
    sklearn-quantile does."""
    samples = getattr(forest, "estimators_samples_", None)
    if samples is None:
        from sklearn.ensemble._forest import _generate_sample_indices

        samples = [_generate_sample_indices(e.random_state, n, n) for e in forest.estimators_]
    return [np.bincount(s, minlength=n) for s in samples]


SPCI_WINDOW = 300  # w: residuals per feature vector (authors' code, electric and wind)
SPCI_TRAIN_ELECTRIC = 2755  # training residuals behind that w (electric data, 80 % split)
SPCI_BINS = 5  # beta grid: linspace(0, alpha, 5)


def spci_window(train_len: int) -> int:
    """Phase 1's w: the authors' ratio of window to training length on the electric data,
    300 / 2755, applied to ``train_len`` (their tutorial: "If there are not so many residuals,
    one can decrease it"). 87 for 800 residuals, 181 for 1660."""
    return max(1, round(SPCI_WINDOW * train_len / SPCI_TRAIN_ELECTRIC))


class QuantileForest:
    """Quantile regression forest (Meinshausen 2006) as computed by sklearn-quantile 0.0.29
    ``RandomForestQuantileRegressor``, the implementation SPCI uses, built on scikit-learn's
    ``RandomForestRegressor`` with the same trees. The conditional quantiles are weighted
    quantiles of the training targets, weighting each by its in-bag count over the size of the
    leaf it shares with the query, summed over trees; the arithmetic follows the library's
    float32 Cython code, so that predictions agree to the bit.
    """

    def __init__(
        self,
        n_estimators: int = 10,
        max_depth: int | None = 2,
        random_state: int | np.random.RandomState | None = None,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state

    def fit(self, X: ArrayLike, y: ArrayLike) -> QuantileForest:
        X32 = np.asarray(X, dtype=np.float32)
        y64 = np.asarray(y, dtype=np.float64)
        n = y64.size
        forest = RandomForestRegressor(
            n_estimators=self.n_estimators,
            criterion="squared_error",
            max_depth=self.max_depth,
            max_features=1.0,
            bootstrap=True,
            random_state=self.random_state,
        )
        forest.fit(X32, y64)
        leaves = forest.apply(X32).T.astype(np.intp)
        weights = np.zeros(leaves.shape, dtype=np.float32)
        counts = _bootstrap_counts(forest, n)
        for i, est in enumerate(forest.estimators_):
            weights[i] = counts[i] / est.tree_.weighted_n_node_samples[leaves[i]]
        leaves[weights == 0] = -1
        order = np.argsort(y64)
        self.forest_ = forest
        self.y_sorted_ = y64.astype(np.float32)[order]
        self.leaves_ = np.ascontiguousarray(leaves[:, order])
        self.weights_ = np.ascontiguousarray(weights[:, order])
        return self

    def predict(self, X: ArrayLike, q: ArrayLike) -> np.ndarray:
        """Quantiles, shape (len(q), n_query), float32."""
        qs = np.atleast_1d(np.asarray(q, dtype=np.float32))
        X32 = np.atleast_2d(np.asarray(X, dtype=np.float32))
        query_leaves = self.forest_.apply(X32).T
        out = np.empty((qs.size, X32.shape[0]), dtype=np.float32)
        for i in range(X32.shape[0]):
            cw = np.zeros(self.y_sorted_.size, dtype=np.float32)
            for e in range(self.n_estimators):
                match = self.leaves_[e] == query_leaves[e, i]
                cw = cw + np.where(match, self.weights_[e], np.float32(0.0))
            keep = cw > 0
            out[:, i] = _weighted_quantile_presorted(self.y_sorted_[keep], qs, cw[keep])
        return out


def _weighted_quantile_presorted(a: np.ndarray, q: np.ndarray, w: np.ndarray) -> np.ndarray:
    """``_weighted_quantile_presorted_1D`` of sklearn-quantile 0.0.29 (linear interpolation):
    float32 running sums, the normalised positions computed in double and stored in float32."""
    n = a.size
    cum = np.cumsum(w, dtype=np.float32)
    total = cum[-1]
    pos = ((cum.astype(np.float64) - 0.5 * w.astype(np.float64)) / np.float64(total)).astype(
        np.float32
    )
    res = np.empty(q.size, dtype=np.float32)
    for j, qj in enumerate(q):
        k = int(np.searchsorted(pos, qj, side="left")) - 1
        if k == -1:
            res[j] = a[0]
        elif k == n - 1:
            res[j] = a[n - 1]
        else:
            frac = np.float32(qj - pos[k]) / np.float32(pos[k + 1] - pos[k])
            res[j] = a[k] + np.float32(frac) * np.float32(a[k + 1] - a[k])
    return res


def spci_quantile_levels(alpha: float, bins: int = SPCI_BINS) -> tuple[np.ndarray, np.ndarray]:
    """beta grid and the 2 * bins levels (beta, then 1 - alpha + beta), as in ``train_QRF``."""
    beta = np.linspace(start=0, stop=alpha, num=bins)
    return beta, np.append(beta, 1 - alpha + beta)


def spci_fit_predict(
    past: np.ndarray,
    horizon: int,
    w: int,
    alpha: float,
    *,
    random_state: int | np.random.RandomState | None,
    bins: int = SPCI_BINS,
) -> tuple[float, float, int]:
    """One SPCI refit on the residual history ``past`` (oldest first).

    Training pairs: each window of w consecutive residuals, with the residual ``horizon`` steps
    after the window's last one as the target (Eq. 13, and Algorithm 3's estimator for that
    horizon). The quantile forest is fitted to them; beta-hat minimises the predicted width at the
    query, the last w residuals (Eq. 11). Returns the lower and upper offsets at the query and
    the index of beta-hat.
    """
    L = past.size
    X = np.lib.stride_tricks.sliding_window_view(past[: L - horizon], w)
    y = past[w - 1 + horizon :]
    _, levels = spci_quantile_levels(alpha, bins)
    forest = QuantileForest(random_state=random_state).fit(X, y)
    pred = forest.predict(past[-w:].reshape(1, -1), levels)[:, 0]
    i_star = int(np.argmin((pred[bins:] - pred[:bins]).flatten()))
    return float(pred[i_star]), float(pred[bins + i_star]), i_star


def spci_rolling(
    residuals: ArrayLike,
    start: int,
    alpha: float,
    horizon: int,
    *,
    w: int = SPCI_WINDOW,
    train_len: int,
    random_state: int | np.random.RandomState | None,
) -> dict[str, np.ndarray]:
    """SPCI at a constant label horizon h (Phase 1, Appendix A).

    For each step t >= start the residuals known at issue time are r_0..r_{t-h}. The forest for
    horizon h is refitted on the ``train_len`` most recent of them and gives the interval offsets
    [lo_t, hi_t] for r_t. Labels arrive every step here, so the forest is refitted every step,
    as Algorithm 1 refits at each t. At h = 1 this is the authors' one-step SPCI.
    """
    r = np.asarray(residuals, dtype=np.float64)
    rs = random_state
    if isinstance(rs, (int, np.integer)):
        rs = np.random.RandomState(int(rs))
    T = r.size
    lo = np.full(T, np.nan)
    hi = np.full(T, np.nan)
    beta_idx = np.full(T, -1)
    for t in range(start, T):
        end = t - horizon + 1
        past = r[max(0, end - train_len) : end]
        if past.size < w + horizon:
            raise ValueError("too few known residuals for the window and horizon")
        lo[t], hi[t], beta_idx[t] = spci_fit_predict(past, horizon, w, alpha, random_state=rs)
    return {"lo": lo, "hi": hi, "beta_index": beta_idx}


def spci_block(
    resid_all: ArrayLike,
    n_train: int,
    alpha: float,
    stride: int,
    *,
    w: int = SPCI_WINDOW,
    random_state: int | np.random.RandomState | None = None,
) -> dict[str, np.ndarray]:
    """The authors' SPCI test loop, ``compute_PIs_Ensemble_online(use_SPCI=True, smallT=False)``,
    with ``stride`` = S (Algorithm 3: labels revealed every S steps).

    ``resid_all``: the n_train training residuals followed by the test residuals. At each block
    start i (a multiple of S) the code refits S forests, one per horizon 1..S, on the n_train
    residuals before test point i, and selects beta-hat at the window ending S - 1 steps before
    the query; the S test points of the block share the query of the block start.
    Returns the lower and upper offsets for every test point.
    """
    r = np.asarray(resid_all, dtype=np.float64)
    n_test = r.size - n_train
    lo = np.empty(n_test)
    hi = np.empty(n_test)
    _, levels = spci_quantile_levels(alpha)
    forests: list[QuantileForest] = []
    stars: list[int] = []
    query = None
    for i in range(n_test):
        k = i % stride
        if k == 0:
            past = r[i : i + n_train]
            num = past.size
            query = past[-w:].reshape(1, -1)
            windows = np.lib.stride_tricks.sliding_window_view(past[: num - stride + 1], w)
            forests, stars = [], []
            for s in range(stride):
                target = past[w + s : num - (stride - s - 1)]
                f = QuantileForest(random_state=random_state).fit(windows[:-1], target)
                sel = f.predict(windows[-1].reshape(1, -1), levels)[:, 0]
                forests.append(f)
                stars.append(int(np.argmin((sel[SPCI_BINS:] - sel[:SPCI_BINS]).flatten())))
        assert query is not None
        pred = forests[k].predict(query, levels)[:, 0]
        lo[i], hi[i] = pred[stars[k]], pred[SPCI_BINS + stars[k]]
    return {"lo": lo, "hi": hi}
