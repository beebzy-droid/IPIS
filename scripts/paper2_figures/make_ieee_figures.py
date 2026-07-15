"""IEEE-sized regenerations of F1/F3/F7 for TCST 26-0876 resubmission.
Native sizes: F1 7.16in (two-column span), F3/F7 3.5in (single column).
Fonts >=8pt at final size, 600 dpi, no in-figure titles (captions carry them)."""
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({"font.size": 8, "axes.labelsize": 9, "xtick.labelsize": 8,
                     "ytick.labelsize": 8, "legend.fontsize": 8, "mathtext.fontset": "cm"})
BLUE, ORANGE, GREY, INK = "#0072B2", "#D55E00", "#9aa0a6", "#222222"
DATA = json.load(open("/tmp/IPIS_fix/docs/module3/paper/evidence/regime_map.json"))

STYLE = {
    "oracle":      dict(color="#000000", marker="o", ls="--", label="oracle"),
    "cqr+apost":   dict(color=BLUE,      marker="s", ls="-",  label="CQR + a-posteriori (proposed)"),
    "naive-fixed": dict(color="#E69F00", marker="^", ls=":",  label="naive fixed"),
    "naive-adapt": dict(color=ORANGE,    marker="v", ls=":",  label="naive adaptive"),
}
ORDER = ["oracle", "cqr+apost", "naive-fixed", "naive-adapt"]

def series(m, key):
    xs, ys = [], []
    for s in sorted(DATA["regime"], key=float):
        c = DATA["regime"][s][m]
        if c["feasible"] and c[key] is not None:
            xs.append(float(s)); ys.append(c[key])
    return xs, ys

def infeas(m):
    return [float(s) for s in sorted(DATA["regime"], key=float) if not DATA["regime"][s][m]["feasible"]]

# ---------- F3: violation vs sigma (3.5in single column) ----------
alpha = DATA["metadata"]["alpha"]; band = DATA["metadata"]["violation_mc_band"]
realistic = DATA["metadata"]["realistic_sigma_z"]
fig, ax = plt.subplots(figsize=(3.5, 2.75))
for m in ORDER:
    xs, ys = series(m, "realized_violation")
    ax.plot(xs, ys, lw=1.5, ms=4.5, **STYLE[m])
    ax.fill_between(xs, [y-band for y in ys], [y+band for y in ys],
                    color=STYLE[m]["color"], alpha=0.10, lw=0)
    for s in infeas(m):
        ax.plot(s, alpha, marker="x", color=STYLE[m]["color"], ms=7, mew=1.8)
ax.axhline(alpha, color="0.35", lw=0.9)
ax.text(0.0245, alpha+0.012, r"target $\alpha=0.10$", fontsize=8, color="0.25", ha="right")
ax.axvline(realistic, color="0.7", lw=0.8, ls="--")
ax.text(realistic+0.0004, 0.545, "realistic", rotation=90, va="top", fontsize=7.5, color="0.45")
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"realized violation $\hat v(u^\star)$")
ax.set_ylim(0, 0.56); ax.set_xlim(0.004, 0.027)
ax.legend(loc="center right", framealpha=0.95, handlelength=2.2, borderpad=0.4)
fig.tight_layout(pad=0.3)
fig.savefig("figures/F3_violation_vs_sigma.png", dpi=600); plt.close(fig)

# ---------- F7: kappa vs sigma (3.5in single column) ----------
xs, ys = series("cqr+apost", "kappa"); inf7 = infeas("cqr+apost")
fig, ax = plt.subplots(figsize=(3.5, 2.3))
ax.plot(xs, ys, color=BLUE, marker="s", lw=1.5, ms=4.5, label="CQR + a-posteriori")
ax.axhline(1.0, color="0.55", lw=0.8, ls="--")
ax.text(xs[0], 1.12, r"no tightening ($\kappa^\star=1$)", fontsize=8, color="0.35")
top = max(ys)
for s in inf7:
    ax.plot(s, top, marker="x", color=BLUE, ms=8, mew=2)
    ax.annotate("infeasible", xy=(s, top), fontsize=8, color="0.35",
                xytext=(-2, 7), textcoords="offset points", ha="right")
ax.axvline(realistic, color="0.7", lw=0.8, ls="--")
ax.text(realistic+0.0004, top*0.98, "realistic", rotation=90, va="top", fontsize=7.5, color="0.45")
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"a-posteriori inflation $\kappa^\star$")
ax.set_xlim(0.004, 0.027)
fig.tight_layout(pad=0.3)
fig.savefig("figures/F7_kappa_vs_sigma.png", dpi=600); plt.close(fig)

# ---------- F1: RTO loop (7.16in double-column span) ----------
def box(ax, xy, w, h, text, *, fc="white", ec=INK, fs=9, lw=1.3, z=2):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=lw, zorder=z))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=z+1, color=INK)

def arrow(ax, p0, p1, *, color=INK, ls="-", lw=1.5, z=1, rad=None):
    cs = f"arc3,rad={rad}" if rad is not None else "arc3,rad=0"
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", connectionstyle=cs,
                 mutation_scale=13, lw=lw, color=color, linestyle=ls, shrinkA=2, shrinkB=2, zorder=z))

fig, ax = plt.subplots(figsize=(7.16, 3.55))
ax.set_xlim(0, 13.5); ax.set_ylim(0, 7.5); ax.axis("off")
box(ax, (1.9, 5.4), 3.3, 1.0, r"Nominal model  $\hat{g}(u)$", fs=9)
box(ax, (1.9, 2.8), 3.3, 1.3, "Conformal back-off  $C(u)$\n(fixed / normalized / CQR)", ec=BLUE, fs=9)
ax.text(1.9, 1.95, r"$\uparrow$ calibration data $\{(u_i,z_i,g_i)\}_{i=1}^{n}$",
        ha="center", va="top", fontsize=8, color=GREY)
box(ax, (5.7, 4.1), 3.1, 2.1, "RTO optimizer\n\n" r"$\max_u\ \pi(u)$" "\n" r"s.t. $\hat{g}(u){+}C(u)\leq\bar{g}$", lw=1.7, fs=9)
box(ax, (9.4, 4.1), 3.4, 2.1, "Debutanizer twin\n(DWSIM, Peng-Robinson)\n9 stages, binary nC4/nC6", fs=9)
box(ax, (12.45, 4.1), 1.6, 1.1, "spec\n" r"$x_B\leq\bar{g}$", ec=BLUE, fs=9)
arrow(ax, (3.55, 5.4), (4.2, 4.65))
arrow(ax, (3.55, 2.9), (4.2, 3.55), color=BLUE)
arrow(ax, (7.25, 4.1), (7.7, 4.1))
ax.text(7.45, 4.55, r"$u^\star=(R,D)$", ha="center", va="bottom", fontsize=9)
arrow(ax, (9.4, 6.7), (9.4, 5.15), color=ORANGE)
ax.text(9.4, 6.85, r"$z\sim\mathcal{F}_\sigma$ (unmeasured feed composition)",
        ha="center", va="bottom", fontsize=9, color=ORANGE)
arrow(ax, (11.1, 4.1), (11.65, 4.1), color=BLUE)
ax.text(11.37, 4.5, r"$x_B$", ha="center", va="bottom", fontsize=9, color=BLUE)
ax.text(11.37, 3.7, "unmeasured", ha="center", va="top", fontsize=7.5, color=GREY, style="italic")
arrow(ax, (9.4, 3.05), (5.7, 3.05), color=GREY, ls="--", lw=1.2, rad=0.25)
ax.text(7.55, 1.55, "closed-loop soft-sensor feedback (future work)",
        ha="center", fontsize=8, color=GREY, style="italic")
fig.tight_layout(pad=0.2)
fig.savefig("figures/F1_rto_loop.png", dpi=600); plt.close(fig)

from PIL import Image
for f in ["F1_rto_loop.png", "F3_violation_vs_sigma.png", "F7_kappa_vs_sigma.png"]:
    im = Image.open(f"figures/{f}"); print(f, im.size, f"{im.size[0]/600:.2f}in @600dpi")
