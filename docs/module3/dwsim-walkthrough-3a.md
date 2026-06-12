# 3A DWSIM Build Walkthrough — Gated Procedure

> Status: ACTIVE, 2026-06-13. Owner executes in DWSIM (Windows); sandbox
> validates exports. Companion spec: `twin-spec-3a.md` (decisions T1–T6).
> HANDOFF protocol: §10 of `docs/HANDOFF.md` is updated at every gate
> below — a gate is not passed until its HANDOFF line is committed.

## Gate map

| gate | deliverable | acceptance | HANDOFF action |
|---|---|---|---|
| G0 | 3A skeleton committed | suite green (263), validate_twin selftest PASS | §10 + changelog updated (done with this commit) |
| G1 | Master case converged | checkpoints C1–C4 inside bands | one-line status + sensor-stage mapping recorded |
| G2 | 16-run grid exported | all runs converged, CSV schema valid | grid status + any non-converged corners noted |
| G3 | Validation PASS | `twin-validation.md` V1–V3 PASS (V4 if profile exported) | validation result + deviations recorded |
| G4 | 3A closeout | twin surface fit (R² > 0.95 reported), case study on twin, ADR-013, results.md §3A | full closeout block, resume = 3B |

Timebox estimate: G1 ≈ 1–2 h (first DWSIM column always costs the most),
G2 ≈ 1–2 h manual (16 runs × ~5 min record), G3 ≈ 15 min, G4 = one
sandbox session. If G2 manual proves painful, stop — plan B is a
`DWSIM.Automation` (pythonnet) script run owner-side; ask and it gets
built next turn.

## Stage-numbering convention (read before touching DWSIM)

DWSIM's rigorous column counts the **condenser as stage 1** and the
**reboiler as the last stage**. The FUG/shortcut N = 8 includes the
reboiler but NOT the total condenser (a total condenser is not an
equilibrium stage). Therefore:

| quantity | value |
|---|---|
| DWSIM "Number of Stages" | **9** (= 8 equilibrium + total condenser) |
| Feed stage (DWSIM numbering) | **5** (= shortcut mid-column stage 4 + condenser offset) |
| Reboiler | DWSIM stage 9 |

All CSV exports use DWSIM numbering; the sensor-stage mapping (G1, C3)
documents the offset explicitly.

## G1 — Master case (R = 1.5, D = 34.5 kmol/h)

### Build steps

1. **New steady-state simulation.** Compounds: *n-Butane*, *n-Hexane*.
   Property package: **Peng-Robinson (PR)**. Leave flash algorithm at
   default (nested loops). Units: kmol/h, °C, bar, kW.
2. **Feed stream** `FEED`: 100 kmol/h; mole fractions nC4 = 0.35,
   nC6 = 0.65; P = 4.8 bar; specify by **P + vapor fraction = 0**
   (bubble-point liquid — DWSIM computes T).
   - **Checkpoint C1:** DWSIM should report FEED T ≈ **83 °C**
     (repo physics: 83.1 °C, ideal-Raoult basis; PR may land ±3 °C).
     If it reads ~20 °C the stream is sub-cooled-spec'd, not VF = 0.
3. **Distillation Column (rigorous)**: 9 stages, total condenser,
   feed `FEED` → stage 5. Condenser P = 4.7 bar, reboiler P = 5.1 bar
   (linear profile). Connect distillate (liquid), bottoms, condenser and
   reboiler energy streams.
4. **Column specifications** (exactly two, the RTO handles):
   - Condenser spec: **Reflux ratio (molar) = 1.5**
   - Reboiler/second spec: **Distillate molar flow = 34.5 kmol/h**
   - Do NOT spec any composition — compositions are outputs here.
5. **Solve.** If it does not converge first try: raise max iterations
   (e.g., 100 → 300), add damping (0.5), or initialize with a
   temperature estimate of 50 °C top / 130 °C bottom. Binary nC4/nC6 at
   these specs is benign; persistent failure usually means a wiring or
   spec-pair mistake, not numerics.

### Convergence checkpoints (record all four)

| # | quantity | expected band | basis |
|---|---|---|---|
| C1 | FEED temperature | 83 ± 3 °C | bubble point z = 0.35 @ 4.8 bar |
| C2 | Condenser T (stage 1) | 45–55 °C | x_C4 ≈ 0.99 @ 4.7 bar → 48.3 °C |
| C2 | Reboiler T (stage 9) | 122–132 °C | x_C4 = 0.02 @ 5.1 bar → 127.7 °C |
| C3 | x_C4 bottoms | 0.006–0.025 | shortcut 0.0124; rigorous vs shortcut band 0.5–2× |
| C3 | x_C4 distillate | > 0.97 | shortcut 0.991 |
| C4 | Reboiler duty | 500–800 kW | analytic 621 kW; rigorous adds sensible/non-CMO effects |

Any checkpoint outside band → stop, diagnose (usual suspects: stage
count off by one, feed stage wrong, pressure profile inverted), do not
proceed to the grid with a wrong master case.

### C3b — Sensor-stage identification (the V1-critical step)

Open the converged **temperature and liquid-composition profiles**. Find
the stage whose liquid satisfies **T ∈ [100, 112] °C** — equivalently
x_C4(liq) ≈ **0.10–0.19** (repo physics at 4.9 bar: 112 °C ↔ 0.102,
100 °C ↔ 0.191). Given the profile spans 48 → 128 °C over 9 stages with
the feed at stage 5, this will be a **stripping-section stage (likely
DWSIM 6–8)** — it is identified from the profile, never assumed.

Record: `sensor_stage_dwsim = <n>`, its T and x_C4. This stage plays the
role of the M1 "tray 6" for the V1/V4 checks; the mapping
(DWSIM stage n ↔ model sensor tray) is written into HANDOFF at G1 and
into ADR-013 at closeout. If NO stage lands in-envelope, stop and report
the full profile — the reconciliation (adjust ΔP, or re-derive the
envelope for the twin) is an option-scale decision, not a silent fix.

## G2 — Case grid (16 runs)

Grid: R ∈ {0.8, 1.5, 2.2, 3.0} × D ∈ {33, 34.5, 36, 37} kmol/h.

Procedure per run (manual path): edit the two column specs → solve →
record one CSV row. Order the runs **within a fixed D, ascending R**
(each solution initializes the next; also matches how V3 monotonicity
groups rows). Expected behavior while running: xB_C4 falls with R and
with D; duty rises with R and D. If a corner refuses to converge
(most likely R = 0.8, D = 33 — the loosest split), record it as
non-converged and continue; 14+/16 is sufficient for the surface fit
(needs ≥ 12).

CSV schema (exact header, one row per converged run):

```
run_id,reflux_ratio,distillate_kmol_h,feed_kmol_h,z_c4,tray6_T_C,top_P_bar,xD_c4,xB_c4,reboiler_duty_kW,tray6_x_c4_liq
```

- `tray6_T_C` / `tray6_x_c4_liq` = the **sensor stage from C3b** (same
  stage for every run), liquid phase. The optional last column enables
  check V4.
- `top_P_bar` = condenser pressure (4.7), constant.
- Duty in kW (DWSIM may default to other units — convert before export).

## G3 — Validation

```
python scripts\validate_twin.py twin_runs.csv
```

Writes `docs/module3/twin-validation.md` and prints it. Exit code 0 =
all PASS. Expected friction points:

- **V1 fails on a few rows:** the sensor stage drifts out of [100, 112] °C
  at extreme (R, D) corners. Report which rows; acceptable outcome is a
  documented envelope restriction, not a silent row drop.
- **V2 fails:** a non-converged DWSIM row exported numbers anyway —
  delete the row, note it, re-run.
- **V4 deviation large but < 0.15:** expected; the M1 physics is
  ideal-Raoult, the twin is PR. The number itself goes in the table.

Commit `twin_runs.csv` (to `data/raw/dwsim/` — new directory, needs
`mkdir data\raw\dwsim` first) + `twin-validation.md` + HANDOFF G3 line.

## G4 — Closeout (sandbox turn)

Hand the validated CSV to the sandbox session. It delivers: twin-grid
surface fit (R², ln-residual band vs the shortcut's ×1.74),
`run_case_study` on the twin surface (back-off sweep, profit gradient),
`docs/module1/results.md`-style §3A section, **ADR-013** (T1–T6 +
sensor-stage mapping + any G-gate reconciliations), and the HANDOFF
closeout block with resume = 3B.

## Risk register (live)

| risk | likelihood | mitigation |
|---|---|---|
| Sensor stage out of envelope at all stages | low–med | C3b stop-and-report; ΔP or envelope reconciliation as an ADR-013 decision |
| Grid corner non-convergence | med | ≥ 12 rows suffices; record gaps |
| DWSIM UI differs from steps above (version drift) | med | steps name the *quantities*, not menu paths; checkpoints C1–C4 are version-independent |
| Manual grid tedium / transcription errors | med | V2 catches transcription; plan B automation script on request |
| PR vs ideal-Raoult systematic offset breaks V4 | low | V4 threshold 0.15 abs already budgets for it; the number is reported either way |
