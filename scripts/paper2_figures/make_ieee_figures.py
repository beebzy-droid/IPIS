"""IEEE-sized F1/F3/F7 for TCST 26-0876 (v4: F1 boxes AUTO-SIZE around measured text).
F1 7.16in (2-col figure*), F3/F7 3.5in (1-col). >=8pt at final size, 600 dpi."""
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({"font.size": 8, "axes.labelsize": 9, "xtick.labelsize": 8,
                     "ytick.labelsize": 8, "legend.fontsize": 7.5, "mathtext.fontset": "cm"})
BLUE, ORANGE, GREY, INK = "#0072B2", "#D55E00", "#8a8f94", "#222222"
WBB = dict(fc="white", ec="none", alpha=1.0, pad=1.2)
DATA = json.load(open("/tmp/R/docs/module3/paper/evidence/regime_map.json"))
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
alpha = DATA["metadata"]["alpha"]; band = DATA["metadata"]["violation_mc_band"]
realistic = DATA["metadata"]["realistic_sigma_z"]

# ---------------- F3 (3.5in) ----------------
fig, ax = plt.subplots(figsize=(3.5, 2.8))
for m in ORDER:
    xs, ys = series(m, "realized_violation")
    ax.plot(xs, ys, lw=1.5, ms=4.5, **STYLE[m])
    ax.fill_between(xs, [y-band for y in ys], [y+band for y in ys], color=STYLE[m]["color"], alpha=0.10, lw=0)
    for s in infeas(m): ax.plot(s, alpha, marker="x", color=STYLE[m]["color"], ms=7, mew=1.8)
ax.axhline(alpha, color="0.35", lw=0.9)
ax.axvline(realistic, color="0.65", lw=0.8, ls="--")
ax.text(0.0268, 0.148, r"target $\alpha=0.10$", fontsize=8, color="0.25", ha="right", va="bottom", bbox=WBB)
ax.text(0.00642, 0.30, "realistic", rotation=90, fontsize=8, color="0.4", ha="left", va="center", bbox=WBB)
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"realized violation $\hat v(u^\star)$")
ax.set_ylim(0, 0.57); ax.set_xlim(0.0038, 0.0272)
leg = ax.legend(loc="center", bbox_to_anchor=(0.615, 0.50), framealpha=1.0, handlelength=1.9, borderpad=0.35)
leg.get_frame().set_edgecolor("0.7")
fig.tight_layout(pad=0.3)
check(fig, ax, "F3")
fig.savefig("figures/F3_violation_vs_sigma.png", dpi=600); plt.close(fig)

# ---------------- F7 (3.5in) ----------------
xs, ys = series("cqr+apost", "kappa"); inf7 = infeas("cqr+apost"); top = max(ys)
fig, ax = plt.subplots(figsize=(3.5, 2.35))
ax.plot(xs, ys, color=BLUE, marker="s", lw=1.5, ms=4.5)
ax.axhline(1.0, color="0.55", lw=0.8, ls="--")
ax.axvline(realistic, color="0.65", lw=0.8, ls="--")
ax.text(0.00642, 4.1, "realistic", rotation=90, fontsize=8, color="0.4", ha="left", va="center", bbox=WBB)
for s in inf7:
    ax.plot(s, top, marker="x", color=BLUE, ms=8, mew=2)
    ax.text(s - 0.0008, top, "infeasible", fontsize=8, color="0.35", ha="right", va="center", bbox=WBB)
ax.set_xlabel(r"disturbance magnitude $\sigma_z$")
ax.set_ylabel(r"a-posteriori inflation $\kappa^\star$")
ax.set_xlim(0.0038, 0.0272); ax.set_ylim(0.4, 6.6)
fig.tight_layout(pad=0.3)
check(fig, ax, "F7")
fig.savefig("figures/F7_kappa_vs_sigma.png", dpi=600); plt.close(fig)

# ---------------- F1 (7.16in) : AUTO-SIZING boxes ----------------
FS = 8.5
def arrow(ax, p0, p1, *, color=INK, ls="-", lw=1.5, z=1, rad=None):
    cs = f"arc3,rad={rad}" if rad is not None else "arc3,rad=0"
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", connectionstyle=cs, mutation_scale=13,
                 lw=lw, color=color, linestyle=ls, shrinkA=2, shrinkB=2, zorder=z))
def tbox(cx, cy, text, ec=INK, lw=1.3):
    return ax.text(cx, cy, text, ha="center", va="center", fontsize=FS, zorder=3, color=INK,
                   bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=ec, lw=lw))
def lbl(x, y, text, **kw):
    kw.setdefault("fontsize", FS); kw.setdefault("bbox", WBB); kw.setdefault("zorder", 2)
    kw.setdefault("va", "bottom")
    return ax.text(x, y, text, ha="center", **kw)

fig, ax = plt.subplots(figsize=(7.16, 3.7))
ax.set_xlim(0, 18); ax.set_ylim(0, 8); ax.axis("off")
B = {}
B["nom"] = tbox(2.7, 6.0, "Nominal model\n" r"$\hat{g}(u)$")
B["bko"] = tbox(2.7, 2.9, "Conformal\nback-off " r"$C(u)$", ec=BLUE)
B["opt"] = tbox(7.7, 4.5, "RTO optimizer\n" r"$\max_u\ \pi(u)$" "\n" r"s.t. $\hat{g}(u){+}C(u)\leq\bar{g}$", lw=1.7)
B["twn"] = tbox(12.6, 4.5, "Debutanizer twin\n(DWSIM,\nPeng-Robinson)")
B["spc"] = tbox(16.2, 4.5, "spec\n" r"$x_B\leq\bar{g}$", ec=BLUE)
fig.canvas.draw()
inv = ax.transData.inverted()
def E(k):
    bb = B[k].get_bbox_patch().get_window_extent()
    (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
    return dict(l=x0, r=x1, b=y0, t=y1, cx=(x0+x1)/2, cy=(y0+y1)/2)
e = {k: E(k) for k in B}
arrow(ax, (e["nom"]["r"], e["nom"]["cy"]), (e["opt"]["l"], e["opt"]["cy"]+0.55))
arrow(ax, (e["bko"]["r"], e["bko"]["cy"]), (e["opt"]["l"], e["opt"]["cy"]-0.55), color=BLUE)
arrow(ax, (e["opt"]["r"], e["opt"]["cy"]), (e["twn"]["l"], e["twn"]["cy"]))
arrow(ax, (e["twn"]["r"], e["twn"]["cy"]), (e["spc"]["l"], e["spc"]["cy"]), color=BLUE)
arrow(ax, (e["twn"]["cx"], 7.0), (e["twn"]["cx"], e["twn"]["t"]), color=ORANGE)
arrow(ax, (e["twn"]["cx"], e["twn"]["b"]-0.15), (e["opt"]["cx"], e["opt"]["b"]-0.15),
      color=GREY, ls="--", lw=1.2, rad=0.3)
top = max(e["opt"]["t"], e["twn"]["t"])
lbl((e["opt"]["r"]+e["twn"]["l"])/2, top+0.30, r"$u^\star=(R,D)$")
lbl((e["twn"]["r"]+e["spc"]["l"])/2, top+0.30, r"$x_B$", color=BLUE)
lbl(e["twn"]["cx"], 7.12, r"$z\sim\mathcal{F}_\sigma$  (unmeasured feed)", color=ORANGE)
lbl(e["bko"]["cx"], e["bko"]["b"]-0.55, r"calibration data $\{(u_i,z_i,g_i)\}_{i=1}^{n}$",
    color=GREY, fontsize=8, va="top")
fbY = min(e["opt"]["b"], e["twn"]["b"]) - 1.05
lbl((e["opt"]["cx"]+e["twn"]["cx"])/2, fbY, "closed-loop soft-sensor feedback (future work)",
    color=GREY, fontsize=8, style="italic", va="center")
gaps = {"bko->opt": e["opt"]["l"]-e["bko"]["r"], "opt->twn": e["twn"]["l"]-e["opt"]["r"],
        "twn->spc": e["spc"]["l"]-e["twn"]["r"]}
print("F1 gaps (must be >0):", {k: round(float(v),2) for k,v in gaps.items()})
check(fig, ax, "F1")
fig.tight_layout(pad=0.2)
fig.savefig("figures/F1_rto_loop.png", dpi=600); plt.close(fig)

from PIL import Image
for f in ["F1_rto_loop.png", "F3_violation_vs_sigma.png", "F7_kappa_vs_sigma.png"]:
    im = Image.open(f"figures/{f}"); print(f, im.size, f"{im.size[0]/600:.2f}in")
