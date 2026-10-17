"""How far the width ratio can stray from the standard-deviation ratio of P3 (pre-registration
Sec. 4).

P3 predicts the ratio of standard deviations of the (theta + 1)-step prediction error and of the
residual. The ratio of 90 % interval widths equals it when the error and the residual share one
standardized distribution, as for Gaussian residuals. This check uses an AR(1) residual with
phi = 0.9 and a one-step horizon, where the error is the innovation itself, and compares the width
ratio with the standard-deviation ratio sqrt(1 - phi^2) for Gaussian, uniform, t5 and Laplace
innovations (2 million steps each).

Run (seconds):
    python scripts\\pilots\\p3_shape_check.py
"""

from __future__ import annotations

import numpy as np
from scipy.signal import lfilter

PHI, N, BURN = 0.9, 2_000_000, 1000


def main() -> None:
    rng = np.random.default_rng(1)
    laws = {
        "gaussian": rng.standard_normal(N),
        "uniform": rng.uniform(-1.0, 1.0, N),
        "t5": rng.standard_t(5, N),
        "laplace": rng.laplace(0.0, 1.0, N),
    }
    for name, e in laws.items():
        e = (e - e.mean()) / e.std()
        r = lfilter([1.0], [1.0, -PHI], e)[BURN:]
        ratio = np.quantile(np.abs(e[BURN:]), 0.9) / np.quantile(np.abs(r), 0.9)
        print(f"{name:8s}: width ratio / sd ratio - 1 = {ratio / np.sqrt(1 - PHI**2) - 1:+.2%}")


if __name__ == "__main__":
    main()
