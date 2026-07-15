"""IEEE-sized F1/F3/F7 for TCST 26-0876 (v2: collision-free placement).
Native widths: F1 7.16in (2-col figure*), F3/F7 3.5in (1-col). >=8pt at final size, 600 dpi,
opaque label backgrounds, generous diagram gaps, no in-figure titles (captions carry them)."""
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({"font.size": 8, "axes.labelsize": 9, "xtick.labelsize": 8,
                     "ytick.labelsize": 8, "legend.fontsize": 7.5, "mathtext.fontset": "cm"})
BLUE, ORANGE, GREY, INK = "#0072B2", "#D55E00", "#8a8f94", "#222222"
WBB = dict(fc="white", ec="none", alpha=0.9, pad=0.8)   # opaque label backing
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
        if c["feasible"] and c[key] is not None: xs.append(float(s)); ys.append(c[key])
    return xs, ys
def infeas(m):
    return [float(s) for s in sorted(DATA["regime"], key=float) if not DATA["regime"][s][m]["feasible"]]

# ---------- F3 ----------
alpha = DATA["metadata"]["alpha"]; band = DATA["metadata"]["violation_mc_band"]
realistic = DATA["metadata"]["realistic_sigma_z"]
fig, ax = plt.subplots(figsize=(3.5, 2.8))
for m in ORDER:
    xs, ys = series(m, "realized_violation")
    ax.plot(xs, ys, lw=1.5, ms=4.5, **STYLE[m])
    ax.fill_between(xs, [y-band for y in ys], [y+band for y in ys], color=STYLE[m]["color"], alpha=0.10, lw=0)
    for s in infeas(m): ax.plot(s, alpha, marker="x", color=STYLE[m]["color"], ms=7, mew=1.8)
ax.axhline(alpha, color="0.35", lw=0.9)
ax.axvline(realistic, color="0.65", lw=0.8, ls="--")
# target label: far left, above the 0.10 line, in clear space (oracle/cqr sit below at ~0.07)
ax.text(0.00425, 0.128, r"target $\alpha=0.10$", fontsize=8, color="0.25", ha="left", va="center", bbox=WBB)
# realistic label: mid gap between naive-fixed (0.19) and naive-adapt (0.45), just right of the line
ax.text(0.00635, 0.31, "realistic", rotation=90, fontsize=8, color="0.4", ha="left", va="center", bbox=WBB)
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"realized violation $\hat v(u^\star)$")
ax.set_ylim(0, 0.57); ax.set_xlim(0.0038, 0.0272)
leg = ax.legend(loc="center", bbox_to_anchor=(0.60, 0.45), framealpha=0.95, handlelength=2.0, borderpad=0.4)
leg.get_frame().set_edgecolor("0.7")
fig.tight_layout(pad=0.3)
fig.savefig("figures/F3_violation_vs_sigma.png", dpi=600); plt.close(fig)

# ---------- F7 ----------
xs, ys = series("cqr+apost", "kappa"); inf7 = infeas("cqr+apost"); top = max(ys)
fig, ax = plt.subplots(figsize=(3.5, 2.35))
ax.plot(xs, ys, color=BLUE, marker="s", lw=1.5, ms=4.5, label="CQR + a-posteriori")
ax.axhline(1.0, color="0.55", lw=0.8, ls="--")
ax.axvline(realistic, color="0.65", lw=0.8, ls="--")
# kappa=1 label: right end of the dashed line, in clear space between the 0.020 marker and the 0.025 x
ax.text(0.0212, 2.15, r"$\kappa^\star=1$: no tightening", fontsize=7.5, color="0.35", ha="center", va="center", bbox=WBB)
# realistic label: empty upper-left region (line is at 1.5 near x=0.006, spike is far right)
ax.text(0.0063, 4.2, "realistic", rotation=90, fontsize=8, color="0.4", ha="left", va="center", bbox=WBB)
for s in inf7:
    ax.plot(s, top, marker="x", color=BLUE, ms=8, mew=2)
    ax.text(s, top+0.15, "infeasible", fontsize=8, color="0.35", ha="right", va="bottom", bbox=WBB)
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"a-posteriori inflation $\kappa^\star$")
ax.set_xlim(0.0038, 0.0272); ax.set_ylim(0.4, 6.6)
fig.tight_layout(pad=0.3)
fig.savefig("figures/F7_kappa_vs_sigma.png", dpi=600); plt.close(fig)

# ---------- F1 (2-col span, roomy gaps, opaque arrow labels) ----------
def box(ax, xy, w, h, text, *, fc="white", ec=INK, fs=9, lw=1.3, z=2):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                 fc=fc, ec=ec, lw=lw, zorder=z))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=z+1, color=INK)
def arrow(ax, p0, p1, *, color=INK, ls="-", lw=1.5, z=1, rad=None):
    cs = f"arc3,rad={rad}" if rad is not None else "arc3,rad=0"
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", connectionstyle=cs, mutation_scale=13,
                 lw=lw, color=color, linestyle=ls, shrinkA=2, shrinkB=2, zorder=z))
fig, ax = plt.subplots(figsize=(7.16, 3.6))
ax.set_xlim(0, 16.5); ax.set_ylim(0, 8); ax.axis("off")
box(ax, (2.1, 6.0), 3.6, 1.0, r"Nominal model  $\hat{g}(u)$", fs=9)
box(ax, (2.1, 3.0), 3.6, 1.35, "Conformal back-off  $C(u)$\n(fixed / normalized / CQR)", ec=BLUE, fs=9)
ax.text(2.1, 2.1, r"calibration data $\{(u_i,z_i,g_i)\}_{i=1}^{n}$", ha="center", va="top", fontsize=8, color=GREY)
box(ax, (7.0, 4.5), 3.2, 2.2, "RTO optimizer\n\n" r"$\max_u\ \pi(u)$" "\n" r"s.t. $\hat{g}(u){+}C(u)\leq\bar{g}$", lw=1.7, fs=9)
box(ax, (11.9, 4.5), 3.6, 2.2, "Debutanizer twin\n(DWSIM, Peng-Robinson)\n9 stages, binary nC4/nC6", fs=9)
box(ax, (15.4, 4.5), 1.7, 1.15, "spec\n" r"$x_B\leq\bar{g}$", ec=BLUE, fs=9)
arrow(ax, (3.9, 6.0), (5.1, 5.05))
arrow(ax, (3.9, 3.1), (5.1, 3.95), color=BLUE)
arrow(ax, (8.6, 4.5), (10.1, 4.5))
ax.text(9.35, 4.95, r"$u^\star=(R,D)$", ha="center", va="center", fontsize=9, bbox=WBB)
arrow(ax, (11.9, 7.05), (11.9, 5.6), color=ORANGE)
ax.text(11.9, 7.2, r"$z\sim\mathcal{F}_\sigma$  (unmeasured feed composition)", ha="center", va="bottom", fontsize=9, color=ORANGE)
arrow(ax, (13.7, 4.5), (14.55, 4.5), color=BLUE)
ax.text(14.12, 4.95, r"$x_B$", ha="center", va="center", fontsize=9, color=BLUE, bbox=WBB)
# feedback routed well below the boxes, label in clear space beneath
arrow(ax, (11.9, 3.15), (7.0, 3.15), color=GREY, ls="--", lw=1.2, rad=0.32)
ax.text(9.45, 1.75, "closed-loop soft-sensor feedback (future work)", ha="center", va="center",
        fontsize=8, color=GREY, style="italic", bbox=WBB)
fig.tight_layout(pad=0.2)
fig.savefig("figures/F1_rto_loop.png", dpi=600); plt.close(fig)

from PIL import Image
for f in ["F1_rto_loop.png", "F3_violation_vs_sigma.png", "F7_kappa_vs_sigma.png"]:
    im = Image.open(f"figures/{f}"); print(f, im.size, f"{im.size[0]/600:.2f}in")
