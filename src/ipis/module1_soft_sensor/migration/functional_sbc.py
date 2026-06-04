"""Yan (2011) functional scale-bias correction -- Bayesian GP model migration.

Verified against the primary: Yan, Hu, Yang, Gao & Chen (2011), Chem. Eng. J.
166, 1095-1103. The migrated model (their Eqs. 12-16):

    y(x) = s(x) * z + delta(x),   z = f_o(x)  (source-model prediction)
    s(x) = beta_0 + sum_j beta_j * x_j        (linear scale function, Eq. 13)
    delta(x) ~ GP(0, C)                        (zero-mean GP bias)

The regression coefficients beta are integrated out with prior beta_j ~ N(0, a)
(their alpha^2), yielding a marginal GP with covariance

    K = a * F F^T + C,   F_row(x) = [z, x_1 z, ..., x_d z]   (Eqs. 15-16)

so the whole thing is a GP whose kernel adds a linear kernel on the
scaled-source features F to a standard kernel C on the inputs. Hyperparameters
(a, and those of C) are fit by maximizing the log marginal likelihood
log N(y | 0, K). Predictive mean and variance follow the standard GP forms with
C -> K. The functional (input-dependent) scale + GP bias is what corrects the
*relationship* error that Lu OSBC's global affine correction cannot, and the GP
posterior variance is native predictive uncertainty (discharges the MAPIE debt
on the transferred model).

Faithful simplifications (documented): C = a0 (constant) + v0*RBF(x; w) +
sigma2*I with an ISOTROPIC RBF (single roughness w) rather than Yan's ARD form;
Kennedy & O'Hagan (cited in Yan) note the richer form is usually unnecessary.
beta is marginalized analytically (the a*FF^T term); the GP hyperparameters are
point-estimated by marginal-likelihood maximization (Yan's Bayesian treatment of
beta with ML-II for the kernel, a standard empirical-Bayes choice).
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler

_JITTER = 1e-8


def _design_matrix(z: np.ndarray, Xs: np.ndarray) -> np.ndarray:
    """F row = [z, x_1 z, ..., x_d z]  (scaled-source features), shape (n, d+1)."""
    return np.column_stack([z, Xs * z[:, None]])


class YanFunctionalSBC:
    """Yan (2011) functional scale-bias correction via a marginal GP.

    Implements the Migrator interface: fit(X, source_pred, y) / predict(X,
    source_pred). After predict, `last_std_` holds the GP posterior std (native
    uncertainty) for the most recent call.
    """

    def __init__(self, n_restarts: int = 8, prior_std: float = 3.0, random_state: int = 0) -> None:
        self.n_restarts = n_restarts
        self.prior_std = prior_std  # log-space hyperparameter prior std (MAP regularization)
        self.random_state = random_state
        self.scaler_: StandardScaler | None = None
        self.Xs_: np.ndarray | None = None
        self.z_: np.ndarray | None = None
        self.F_: np.ndarray | None = None
        self.y_: np.ndarray | None = None
        self.theta_: np.ndarray | None = None  # [log a, log a0, log v0, log w, log s2]
        self._prior_mean: np.ndarray | None = None
        self._L = None
        self._alpha = None
        self.last_std_: np.ndarray | None = None

    # --- kernel pieces ---
    def _sqdist(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        a2 = np.sum(A * A, axis=1)[:, None]
        b2 = np.sum(B * B, axis=1)[None, :]
        return np.maximum(a2 + b2 - 2.0 * A @ B.T, 0.0)

    def _kernel(self, theta: np.ndarray) -> np.ndarray:
        a, a0, v0, w, s2 = np.exp(np.clip(theta, -15.0, 15.0))
        n = self.Xs_.shape[0]
        K = a * (self.F_ @ self.F_.T) + a0
        K = K + v0 * np.exp(-w * self._sqdist(self.Xs_, self.Xs_))
        K = K + (s2 + _JITTER) * np.eye(n)
        return K

    def _nlml(self, theta: np.ndarray) -> float:
        try:
            K = self._kernel(theta)
            L = cho_factor(K, lower=True)
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            return 1e12
        alpha = cho_solve(L, self.y_)
        logdet = 2.0 * np.sum(np.log(np.diag(L[0])))
        n = len(self.y_)
        nll = 0.5 * self.y_ @ alpha + 0.5 * logdet + 0.5 * n * np.log(2 * np.pi)
        # MAP penalty: light Gaussian prior on log-hyperparameters (regularizes
        # the small-sample fit, damping the low-data-fraction GP instability)
        if self._prior_mean is not None and self.prior_std > 0:
            nll = nll + 0.5 * float(np.sum(((theta - self._prior_mean) / self.prior_std) ** 2))
        return float(nll)

    def fit(self, X: np.ndarray, source_pred: np.ndarray, y: np.ndarray) -> YanFunctionalSBC:
        X = np.asarray(X, dtype=float)
        z = np.asarray(source_pred, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if not (X.shape[0] == z.shape[0] == y.shape[0]):
            raise ValueError("X, source_pred, y must share the same number of rows.")
        if X.shape[0] < 3:
            raise ValueError("YanFunctionalSBC needs >= 3 target samples.")
        self.scaler_ = StandardScaler().fit(X)
        self.Xs_ = self.scaler_.transform(X)
        self.z_ = z
        self.y_ = y
        self.F_ = _design_matrix(z, self.Xs_)

        # init from data scales; optimize log-hyperparameters with restarts
        yvar = float(np.var(y)) + 1e-6
        base = np.log(np.array([yvar / max(np.mean(z**2), 1e-6), yvar, yvar, 1.0, 0.1 * yvar]))
        self._prior_mean = base  # MAP prior centered at data-scale-reasonable values
        rng = np.random.default_rng(self.random_state)
        best_theta, best_nlml = None, np.inf
        for r in range(self.n_restarts):
            t0 = base + (0.0 if r == 0 else rng.normal(0, 1.0, size=5))
            res = minimize(
                self._nlml,
                np.clip(t0, -15, 15),
                method="L-BFGS-B",
                bounds=[(-15.0, 15.0)] * 5,
            )
            if res.fun < best_nlml:
                best_nlml, best_theta = res.fun, res.x
        self.theta_ = best_theta
        K = self._kernel(self.theta_)
        self._L = cho_factor(K, lower=True)
        self._alpha = cho_solve(self._L, self.y_)
        return self

    def predict(self, X: np.ndarray, source_pred: np.ndarray) -> np.ndarray:
        if self.theta_ is None:
            raise RuntimeError("YanFunctionalSBC.predict called before fit.")
        Xs = self.scaler_.transform(np.asarray(X, dtype=float))
        zs = np.asarray(source_pred, dtype=float).ravel()
        Fs = _design_matrix(zs, Xs)
        a, a0, v0, w, s2 = np.exp(np.clip(self.theta_, -15.0, 15.0))
        # cross-covariance k*(test, train), shape (m, n)
        kx = a * (Fs @ self.F_.T) + a0 + v0 * np.exp(-w * self._sqdist(Xs, self.Xs_))
        mean = kx @ self._alpha
        # posterior predictive variance for a new OBSERVATION (latent + noise s2)
        kss = a * np.sum(Fs * Fs, axis=1) + a0 + v0 + s2  # prior obs-var at test points
        vsol = cho_solve(self._L, kx.T)  # (n, m)
        var = kss - np.einsum("ij,ji->i", kx, vsol)
        self.last_std_ = np.sqrt(np.maximum(var, 0.0))
        return mean
