# 3A DWSIM Build Walkthrough — Gated Procedure

> Status: ACTIVE, 2026-06-13. Owner executes in DWSIM (Windows); sandbox
> validates exports. Companion spec: `twin-spec-3a.md` (decisions T1–T6).
> HANDOFF protocol: §10 of `docs/HANDOFF.md` is updated at every gate
> below — a gate is not passed until its HANDOFF line is committed.

## Execution model: Claude Code via DWSIM MCP (2026-06-13)

The twin is driven by **Claude Code** through a **DWSIM MCP server**
(`C:\Users\<user>\.claude.json`, server `dwsim`, 34 tools) — NOT by manual
GUI clicking, with ONE exception below. Sandbox (this assistant) writes the
spec, the gate criteria, and the validation harness; Claude Code executes in
DWSIM; checkpoints are verified against the numbers herein.

**Capability surface (probed 2026-06-13):** session lifecycle; databank
(add_compound, set_property_package, set_binary_interaction_parameter);
flowsheet (add_stream, add_unit, connect, set_object_parameter, list/topology);
standalone flash (flash_tp/ph/ps/stream); run + get_results +
get_stream_properties; **studies (sensitivity_analysis, parameter_sweep,
optimize, export_study_results)**; persistence (load_case, save_case,
export_csv, export_json, generate_report).

**HARD BLOCKER:** `add_unit` supports `unit_type='separator'` ONLY — there is
no distillation-column/ChemSep/rigorous-column type. The rigorous column
therefore **cannot be built from a blank MCP session**. Resolution: the
column is built ONCE in the DWSIM GUI and saved as `.dwxmz` (G1b); everything
else is MCP-automated. (Rejected alternative: cascading `separator` units to
fake a column — reinvents condenser/reboiler/reflux logic, miserable recycle
convergence through MCP. Not worth it.)

**Two MCP affordances that improve the original plan:**
- `flash_tp` enables a full PR-vs-(M1 ideal-Raoult) VLE cross-check across the
  envelope BEFORE any column exists (G1a) — de-risks V1/V4 cheaply.
- `parameter_sweep` + `export_study_results` collapse the G2 grid from ~16
  manual GUI runs to a single study call.

**SI UNIT TRAP:** all MCP tool I/O is SI (mol/s, K, Pa, W); there is no
set-unit-system tool. The CSV schema the harness validates is kmol/h, °C,
bar, kW. Claude Code MUST convert on export. Conversions: kmol/h = mol/s ×
3.6; °C = K − 273.15; bar = Pa / 1e5; kW = W / 1000.

**DELIBERATELY UNUSED — `optimize`:** DWSIM's internal optimizer is NOT used
for the RTO. The RTO lives in GEKKO (surrogate per ADR-006, state_bus per D4,
conformal back-off = the 3B contribution); putting the twin in DWSIM's
optimizer loop bypasses all three and re-slows the loop the surrogate exists
to avoid. At most a later sanity cross-check, never the path.

## Gate map

| gate | deliverable | acceptance | HANDOFF action |
|---|---|---|---|
| G0 | 3A skeleton committed | suite green (263), validate_twin selftest PASS | §10 + changelog updated (done) |
| G1a | PR-vs-Raoult flash check | every \|PR−Raoult\| ≤ 5 °C across envelope; C1 confirmed | deviation table + verdict recorded |
| G1b | Column built + saved (GUI) | converges in GUI; condenser ~48 °C, reboiler ~128 °C | `.dwxmz` path + GUI-config note recorded |
| G1c | Master case via MCP | checkpoints C2–C4 in band; sensor stage identified (C3b) | sensor_stage_dwsim = n, its T and x_C4 recorded |
| G2 | 16-run grid (parameter_sweep) | study completes; CSV schema valid in target units | grid status + any non-converged corners noted |
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

## G1a — PR-vs-Raoult flash validation (Claude Code, no column)

Unblocked now. create_session -> add_compound nC4, nC6 -> set_property_package
Peng-Robinson. Then flash_tp the five envelope points (SI in, report in degC),
comparing DWSIM PR bubble-T to the M1 ideal-Raoult reference:

| x_C4 | P (bar) | P (Pa) | T_raoult (degC) | zone |
|---|---|---|---|---|
| 0.99 | 4.70 | 470000 | 48.3 | condenser/top |
| 0.65 | 4.80 | 480000 | 63.3 | rectifying |
| 0.35 | 4.80 | 480000 | 83.1 | feed = **checkpoint C1** |
| 0.144 | 4.90 | 490000 | 106.0 | sensor band |
| 0.02 | 5.10 | 510000 | 127.7 | reboiler/bottoms |

**Gate:** every |PR - Raoult| <= 5 degC. If exceeded, the envelope mapping
(used by V1/V4) needs review before the column is built - stop and report the
zone. This also pre-confirms C1 (feed bubble point) without a column.

**RESULT (2026-06-13, session 461a5c56): PASS.** PR bubble-T is uniformly
ABOVE Raoult: Delta = +0.2 (0.99), +1.7 (0.65), +3.2 (0.35), +3.2 (0.144),
+0.4 (0.02) degC. Max +3.2 < 5 gate. Zero at pure ends -> pure-Psat bases
agree; max at mid-composition -> mild liquid non-ideality (effective gamma<1,
slight NEGATIVE deviation from Raoult) that ideal-Raoult omits — physically
expected for an asymmetric n-alkane pair at kij=0. CONSEQUENCE: the C1-C3b
bands below were computed on the Raoult basis; read them +offset on PR
(feed ~86 degC not 83). V4 margin re-verified: at the sensor stage the M1
inversion at the PR temperature predicts x_C4~0.121 vs twin 0.144 ->
deviation ~0.023, 6.5x inside the 0.15 threshold. C3b 12-degC window absorbs
the offset (a Raoult-106 stage reads ~109 on PR, still in [100,112]).

## G1b — Build the column ONCE in the GUI (owner; the one manual step)

The MCP server has no distillation-column unit type, so the rigorous column is
built in the DWSIM GUI and saved. The thermo is already de-risked by G1a, so
this is quick.

1. Drag a **Rigorous Distillation Column** onto the flowsheet (Object Palette
   -> Columns).
2. Add material streams **FEED** (in), **DIST** (distillate), **BTMS**
   (bottoms), plus the condenser/reboiler **energy streams** the column needs.
3. Config: **9 stages**, **total condenser**, feed -> **stage 5**, condenser P
   **4.7 bar**, reboiler P **5.1 bar** (DWSIM numbering - condenser is stage 1;
   see convention block above).
4. FEED: 100 kmol/h, nC4 0.35 / nC6 0.65, 4.8 bar, **VF = 0** (the GUI has the
   vapor-fraction spec the MCP add_stream lacks; T resolves to the G1a value).
5. Two column specs ONLY: **reflux ratio = 1.5**, **distillate rate = 34.5
   kmol/h**. No composition specs.
6. **Solve once in the GUI** to confirm convergence (do not hand Claude Code a
   broken file - wastes file-vs-MCP diagnosis round-trips). Eyeball condenser
   ~48 degC, reboiler ~128 degC.
7. `mkdir data\raw\dwsim` (new directory - flagged), then **Save As**
   `data\raw\dwsim\debutanizer_3a.dwxmz`.

## G1c — Master case via MCP (Claude Code; R = 1.5, D = 34.5)

load_case the `.dwxmz` -> set_object_parameter reflux ratio = 1.5 and
distillate flow = 34.5 kmol/h (SI: 9.5833 mol/s) on the column object -> run ->
get_results / get_stream_properties for C2-C4 and the stage profile for C3b.
Convert all readings to schema units before reporting.

### (legacy) GUI build steps — superseded by G1b for the MCP path

1. **New steady-state simulation.**

1. **New steady-state simulation.** Compounds: *n-Butane*, *n-Hexane*.
   Property package: **Peng-Robinson (PR)**. Leave flash algorithm at
   default (nested loops). Units: kmol/h, °C, bar, kW.
2. **Feed stream** `FEED`: 100 kmol/h; mole fractions nC4 = 0.35,
   nC6 = 0.65; P = 4.8 bar; specify by **P + vapor fraction = 0**
   (bubble-point liquid — DWSIM computes T).
   - **Checkpoint C1:** DWSIM (PR) should report FEED T ≈ **86 °C**
     (repo Raoult basis 83.1 °C + G1a-measured +3.2 °C PR offset).
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
| C1 | FEED temperature | 83 ± 3 °C **(Raoult); ~86 ± 3 on PR — G1a measured** | bubble point z = 0.35 @ 4.8 bar; investigate only if > 89 |
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

## G2 — Case grid via parameter_sweep (Claude Code)

Grid: R ∈ {0.8, 1.5, 2.2, 3.0} × D ∈ {33, 34.5, 36, 37} kmol/h = 16 runs.

With the column loaded (G1c), this is a **single `parameter_sweep`**, not 16
manual runs. variables[] = reflux ratio and distillate flow on the column
object (D in SI: 33→9.1667, 34.5→9.5833, 36→10.0, 37→10.2778 mol/s);
outputs[] = bottoms x_C4, distillate x_C4, reboiler duty, and the sensor-stage
T and liquid x_C4 (the C3b stage from G1c). Then `export_study_results` →
post-process to the harness schema.

Expected behavior: xB_C4 falls with R and with D; duty rises with both. If a
corner fails (most likely R = 0.8, D = 33, the loosest split), it drops from
the study output — 12+/16 converged is sufficient for the surface fit. Note
the gap in the G2 HANDOFF line.

**CSV schema (the harness contract — exact header, target units, one row per
converged run):**

```
run_id,reflux_ratio,distillate_kmol_h,feed_kmol_h,z_c4,tray6_T_C,top_P_bar,xD_c4,xB_c4,reboiler_duty_kW,tray6_x_c4_liq
```

- **Unit conversion is mandatory** (MCP is SI): distillate_kmol_h = mol/s × 3.6;
  tray6_T_C = K − 273.15; top_P_bar = Pa / 1e5 (= 4.7, constant);
  reboiler_duty_kW = W / 1000. Mole fractions are dimensionless.
- `tray6_T_C` / `tray6_x_c4_liq` = the **sensor stage from C3b** (same stage
  every run), liquid phase. The optional last column enables check V4.
- Write to `data\raw\dwsim\twin_runs.csv`.

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
| MCP returns SI; CSV schema is kmol/h/°C/bar/kW | certain | conversion rules in G2; harness fails loud on wrong units (V2) |
| PR (twin) vs ideal-Raoult (M1) VLE offset | med | G1a quantifies it up front; V4 threshold 0.15 budgets for it |
| Column won't converge in GUI (G1b) | low–med | binary at α≈6 is benign; init 50/130 °C, raise iterations, damping 0.5 |
| Sensor stage out of envelope at all stages | low–med | C3b stop-and-report; ΔP or envelope reconciliation as ADR-013 decision |
| parameter_sweep corner non-convergence | med | ≥ 12 rows suffices; record gaps in HANDOFF G2 line |
| Hand Claude Code a broken `.dwxmz` | med | G1b step 6 — solve in GUI before handoff |
| DWSIM/MCP version drift vs these steps | med | steps name quantities + checkpoints, not menu paths/tool internals |
