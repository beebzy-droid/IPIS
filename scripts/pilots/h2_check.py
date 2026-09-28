"""Linear stochastic model of the delayed ACI loop in the interior (exact score law =>
E[err|alpha]=alpha): e_{t+1} = e_t - g*(e_{t-th} + eta_{t-th}), var(eta)=a*(1-a).
Predict sd(alpha) via impulse-response energy; predict %inf = Phi(-a*/sd).
Compare with the simulated values measured above."""
import numpy as np
from scipy.stats import norm
A = 0.10; s_eta = np.sqrt(A*(1-A))
def sd_pred(g, th, K=200000):
    e = np.zeros(K); imp = np.zeros(K); imp[0] = 1.0
    for t in range(K-1):
        e[t+1] = e[t] - g*((e[t-th] if t>=th else 0.0) + (imp[t-th] if t>=th else 0.0))
        if t > 20*th and abs(e[t]) < 1e-12 and abs(e[t-th]) < 1e-12: break
    return s_eta*np.sqrt(np.sum(e**2))
meas = {20:[(0.50,.064,6.7),(0.80,.111,20.8),(0.95,.142,28.6)],
        60:[(0.50,.037,0.5),(0.80,.068,8.7),(0.95,.091,16.8)]}
print(f"{'theta':>5s} {'g/gc':>5s} | {'sd pred':>7s} {'sd meas':>7s} {'err%':>5s} | {'%inf pred':>9s} {'%inf meas':>9s}")
for th, rows in meas.items():
    gc = 2*np.sin(np.pi/(4*th+2))
    for r, sdm, im in rows:
        sp = sd_pred(r*gc, th); ip = 100*norm.cdf(-A/sp)
        print(f"{th:5d} {r:5.2f} | {sp:7.3f} {sdm:7.3f} {100*(sp-sdm)/sdm:+5.0f} | {ip:9.1f} {im:9.1f}")
print("\nDesign rule candidate: largest gamma with predicted %inf <= 1%:")
for th in (4, 20, 60, 120, 240):
    gc = 2*np.sin(np.pi/(4*th+2)); gs = np.linspace(0.02, 0.99, 60)*gc
    ok = [g for g in gs if 100*norm.cdf(-A/sd_pred(g, th, K=60000)) <= 1.0]
    print(f"  theta={th:4d}: gamma_crit={gc:.4f}  gamma_1% = {max(ok) if ok else float('nan'):.4f}  (= {max(ok)/gc if ok else float('nan'):.2f} gamma_crit)")
