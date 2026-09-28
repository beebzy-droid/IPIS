"""Falsification-first pilot: is single-state delayed ACI a dead-time integral loop?
Prediction: for gamma > gamma_crit(theta) = 2 sin(pi/(4 theta + 2)) (Levin-May bound for
x_{n+1} - x_n + g x_{n-k} = 0), alpha_t enters a limit cycle that MARGINAL coverage hides.
A Smith-predictor correction should remove the delay from the loop. Exact score law
(|N(0,s)|) isolates the loop dynamics from quantile-estimation noise."""
import numpy as np
from scipy.stats import norm

A_STAR = 0.10

def q_of(alpha, scale):
    if alpha <= 0: return np.inf
    if alpha >= 1: return 0.0
    return scale * norm.ppf(1 - alpha / 2)          # P(|N(0,scale)| > q) = alpha

def run(kind, theta, gamma, T=20000, shift_at=None, seed=0):
    rng = np.random.default_rng(seed)
    scale = np.ones(T); 
    if shift_at: scale[shift_at:] = 3.0
    s = np.abs(rng.normal(0, 1, T)) * scale
    a = np.full(T + theta + 2, A_STAR); err = np.zeros(T); w = np.zeros(T)
    for t in range(T):
        q = q_of(a[t], 1.0)                          # sensor believes nominal scale
        w[t] = 2 * q; err[t] = float(s[t] > q)
        if kind == "sequential":                     # one state, stale label (what service.py does)
            fb = err[t - theta] if t >= theta else A_STAR
            a[t + 1] = a[t] + gamma * (A_STAR - fb)
        elif kind == "phase":                        # El Halabi & Brandt tau-DACI: alpha_{t+theta} from alpha_t
            if t + theta < len(a): a[t + theta] = a[t] + gamma * (A_STAR - err[t])
            # (phases initialised at A_STAR; a[t+1] for t<theta stays A_STAR)
        elif kind == "smith":                        # Smith predictor: model E[err|alpha]=clip(alpha)
            if t >= theta:
                fb = err[t - theta] - np.clip(a[t - theta], 0, 1) + np.clip(a[t], 0, 1)
            else:
                fb = np.clip(a[t], 0, 1)
            a[t + 1] = a[t] + gamma * (A_STAR - fb)
    return s, err, a[:T], w

def summarize(err, a, w, lo, hi):
    e, al, ww = err[lo:hi], a[lo:hi], w[lo:hi]
    roll = np.convolve(1 - e, np.ones(100) / 100, mode="valid")
    finite = np.isfinite(ww)
    return (1 - e.mean(), al.std(), (~finite).mean(), (ww[finite].mean() if finite.any() else np.nan),
            roll.std(), roll.min())

print(f"{'loop':10s} {'theta':>5s} {'gamma':>6s} {'g_crit':>7s} | {'margCov':>7s} {'sd(a)':>6s} {'%inf':>5s} {'meanW':>6s} {'sdLocal':>7s} {'minLoc':>6s}")
for theta in (4, 60):
    gc = 2 * np.sin(np.pi / (4 * theta + 2))
    for gamma in (0.005, 0.05):
        for kind in ("sequential", "phase", "smith"):
            s, err, a, w = run(kind, theta, gamma)
            m = summarize(err, a, w, 2000, 20000)
            flag = "  <-- above crit" if (kind == "sequential" and gamma > gc) else ""
            print(f"{kind:10s} {theta:5d} {gamma:6.3f} {gc:7.4f} | {m[0]:7.3f} {m[1]:6.3f} {100*m[2]:5.1f} {m[3]:6.2f} {m[4]:7.3f} {m[5]:6.2f}{flag}")
        print()
