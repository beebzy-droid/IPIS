"""Realistic pilot: sliding-window conformal quantile (R=200, repo convention
ceil((1-a)(n+1))-th score; a<=0 -> inf, a>=1 -> 0), and the score of sample t enters the
window only when its label arrives at t+theta. Mirrors ACIConformal + service.py timing."""
import numpy as np, math
from collections import deque

A, R = 0.10, 200
def cq(win, level):
    if level >= 1: return math.inf
    if level <= 0: return 0.0
    s = np.sort(win); k = math.ceil(level * (len(s) + 1))
    return math.inf if k > len(s) else float(s[k - 1])

def run(kind, theta, g, T=16000, shift=None, seed=0):
    rng = np.random.default_rng(seed)
    sc = np.ones(T); sc[shift:] = 3.0 if shift else 1.0
    s = np.abs(rng.normal(0, 1, T)) * sc
    win = deque(np.abs(rng.normal(0, 1, R)), maxlen=R)
    a = np.full(T + theta + 2, A); err = np.zeros(T); w = np.zeros(T)
    for t in range(T):
        q = cq(list(win), 1 - a[t]); w[t] = 2 * q; err[t] = float(s[t] > q)
        if t >= theta: win.append(s[t - theta])                 # delayed score arrival
        if kind == "sequential":
            fb = err[t - theta] if t >= theta else A
            a[t + 1] = a[t] + g * (A - fb)
        elif kind == "phase":
            a[t + theta] = a[t] + g * (A - err[t])
        elif kind == "smith":
            fb = (err[t - theta] - np.clip(a[t - theta], 0, 1) if t >= theta else 0.0) + np.clip(a[t], 0, 1)
            a[t + 1] = a[t] + g * (A - fb)
    return err, a[:T], w

theta = 60; gc = 2 * np.sin(np.pi / (4 * theta + 2))
print(f"theta={theta}  gamma_crit={gc:.4f}  window R={R}  20 seeds each\n")
print("STATIONARY (no shift), t in [2000,16000):")
print(f"{'loop':10s} {'gamma':>6s} | {'margCov':>7s} {'sd(a)':>6s} {'%inf':>5s} {'sdLocal':>7s} {'minLoc':>6s}")
for kind, g in [("sequential",0.005),("sequential",0.05),("phase",0.05),("smith",0.05)]:
    M = []
    for sd in range(20):
        err, a, w = run(kind, theta, g, seed=sd)
        e, al, ww = err[2000:], a[2000:], w[2000:]
        roll = np.convolve(1-e, np.ones(100)/100, "valid")
        M.append([1-e.mean(), al.std(), np.mean(~np.isfinite(ww)), roll.std(), roll.min()])
    m = np.mean(M, 0)
    print(f"{kind:10s} {g:6.3f} | {m[0]:7.3f} {m[1]:6.3f} {100*m[2]:5.1f} {m[3]:7.3f} {m[4]:6.2f}")

print("\nDRIFT (scale 1->3 at t=10000):")
print(f"{'loop':10s} {'gamma':>6s} | {'cov 0-1k':>13s} {'cov 0-3k':>13s} {'steps->0.85':>12s} {'%inf':>5s}")
for kind, g in [("sequential",0.02),("phase",0.05),("smith",0.05)]:
    c1, c3, rec, pi = [], [], [], []
    for sd in range(20):
        err, a, w = run(kind, theta, g, shift=10000, seed=sd)
        p = 1 - err[10000:]; roll = np.convolve(p, np.ones(200)/200, "valid")
        c1.append(p[:1000].mean()); c3.append(p[:3000].mean())
        rec.append(np.argmax(roll >= .85) if (roll >= .85).any() else np.nan)
        pi.append(np.mean(~np.isfinite(w[10000:13000])))
    print(f"{kind:10s} {g:6.3f} | {np.mean(c1):.3f}+/-{np.std(c1):.3f} {np.mean(c3):.3f}+/-{np.std(c3):.3f} "
          f"{np.nanmean(rec):7.0f}+/-{np.nanstd(rec):3.0f} {100*np.mean(pi):5.1f}")
