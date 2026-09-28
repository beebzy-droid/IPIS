"""Does gamma_crit(theta)=2 sin(pi/(4 theta+2)) predict ONSET, and does the linear
boundary predict the PERIOD 4*theta+2? Sequential loop, exact score law, 10 seeds."""
import numpy as np
from dead_time_pilot import run
for theta in (20, 60):
    gc = 2*np.sin(np.pi/(4*theta+2))
    print(f"\ntheta={theta}: gamma_crit={gc:.4f}, predicted boundary period={4*theta+2}")
    print(f"{'g/g_crit':>8s} {'gamma':>7s} {'sd(alpha)':>9s} {'%inf':>6s} {'dominant period':>16s}")
    for ratio in (0.5, 0.8, 0.95, 1.05, 1.25, 2.0):
        g = ratio*gc; sds, infs, pers = [], [], []
        for sd in range(10):
            s, err, a, w = run("sequential", theta, g, T=24000, seed=sd)
            x = a[4000:] - a[4000:].mean(); sds.append(x.std()); infs.append(np.mean(~np.isfinite(w[4000:])))
            f = np.abs(np.fft.rfft(x))**2; fr = np.fft.rfftfreq(len(x)); f[0] = 0
            pers.append(1/fr[np.argmax(f)])
        print(f"{ratio:8.2f} {g:7.4f} {np.mean(sds):9.3f} {100*np.mean(infs):6.1f} {np.median(pers):16.0f}")
