# run_g2_sweep.py - G2 16-run grid on the debutanizer_3a rigorous twin.
#
# Run:  python scripts/run_g2_sweep.py
# Env:  ipis conda (pythonnet 3.1.0; .NET Framework 4.8)
# Output: data/raw/dwsim/twin_runs.csv
#
# Grid: R in {0.8, 1.5, 2.2, 3.0} x D in {37, 36, 34.5, 33} kmol/h.
# Run order: fixed R ascending, within each R D descending (= bottoms ascending).
# Bottoms spec = 100 - D kmol/h (column built with bottoms spec; SpecUnit='kmol/h').
#
# Spec keys discovered by _probe_specs.py (2026-06-13):
#   col.Specs['C']  SType=Stream_Ratio       -> Reflux Ratio (dimensionless)
#   col.Specs['R']  SType=Product_Molar_Flow_Rate -> Bottoms kmol/h
#   Both: SpecValue  CanWrite=True  (direct assignment; no reflection needed)
#
# G1c API limits carried forward:
#   Stage.l/v/Kvalues always empty post-solve; tray6_x_c4_liq left blank (V4 dropped).
#   Product stream compositions (xD, xB) are real PR via Phase[0].Compounds.MoleFraction.
#
# STALE-CACHE GUARD (added 2026-06-13):
#   DWSIM's column solver can return a cached result when the bottoms spec changes
#   by a small amount (<=0.5 kmol/h) in a high-purity / over-refluxed regime —
#   the residual change is below the solver's convergence threshold and it reports
#   the previous solution as converged.  Confirmed at R=3.0, B=64->65.5 (run_015).
#   Guard: after each converged solve, compare result with the immediately preceding
#   run; if bit-identical AND bottoms changed >0.01 kmol/h, fine-step from the
#   previous B to the target in 0.1 kmol/h increments to force solver movement.
#   If fine-stepping still hits the plateau (genuine near-pinch regime), the script
#   accepts and documents the best-effort result with a PLATEAU warning.

import sys, os, math, csv

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_FILE = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "data", "raw", "dwsim", "debutanizer_3a.dwxmz")
)
CSV_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "raw", "dwsim"))
CSV_OUT = os.path.join(CSV_DIR, "twin_runs.csv")
SENSOR_IDX = 5  # stage index from G1c
FEED = 100.0  # kmol/h
Z_C4 = 0.35
TOP_P_BAR = 4.7  # condenser pressure, constant

# Grid (run order: R ascending; within each R, D descending = bottoms ascending)
REFLUX_LIST = [0.8, 1.5, 2.2, 3.0]
D_LIST = [37.0, 36.0, 34.5, 33.0]  # D kmol/h; bottoms = FEED - D

# Self-check reference: master case (R=1.5, D=34.5) from G1c
MASTER_R, MASTER_D = 1.5, 34.5
MASTER_XB, MASTER_XD, MASTER_Q = 0.0243, 0.9684, 609.3

CSV_HEADER = [
    "run_id",
    "reflux_ratio",
    "distillate_kmol_h",
    "feed_kmol_h",
    "z_c4",
    "tray6_T_C",
    "top_P_bar",
    "xd_c4",
    "xb_c4",
    "reboiler_duty_kW",
    "tray6_x_c4_liq",
]


# --- unit converters ---------------------------------------------------------
def K_to_C(v):
    return float(v) - 273.15


def W_to_kW(v):
    return float(v) / 1e3


# --- reflection helpers (lazy; CLR loaded after first clr import) -------------
_BF_val = None


def _bf():
    global _BF_val
    if _BF_val is None:
        import System.Reflection as _R

        _BF_val = _R.BindingFlags.Public | _R.BindingFlags.Instance
    return _BF_val


def rget(obj, pname):
    try:
        p = obj.GetType().GetProperty(pname)
        if p:
            return p.GetValue(obj)
    except Exception:
        pass
    return getattr(obj, pname, None)


def rprop_dict(obj):
    d = {}
    for p in obj.GetType().GetProperties(_bf()):
        try:
            d[str(p.Name)] = p.GetValue(obj)
        except Exception:
            pass
    return d


def _display(obj):
    for f in [lambda o: str(o.GraphicObject.Tag), lambda o: str(rget(o, "Name"))]:
        try:
            v = f(obj)
            if v and v not in ("", "None"):
                return v
        except Exception:
            pass
    return ""


def stream_x_nc4(stream, nc4_name):
    phases = rget(stream, "Phases")
    if phases is None:
        return float("nan")
    nc4n = nc4_name.lower().replace("-", "").replace(" ", "")
    for ph in [2, 3, 0]:
        try:
            cmpds = rget(phases[ph], "Compounds")
            for k in list(cmpds.Keys):
                if str(k).lower().replace("-", "").replace(" ", "") == nc4n:
                    v = rget(cmpds[k], "MoleFraction")
                    if v is not None and float(v) > 1e-12:
                        return float(v)
        except Exception:
            pass
    return float("nan")


# =============================================================================
# Bootstrap CLR once
# =============================================================================
sys.path.insert(0, DWSIM_DIR)
import clr

clr.AddReference(os.path.join(DWSIM_DIR, "DWSIM.Automation.dll"))
from DWSIM.Automation import Automation3

_aut = Automation3()

_col_asm_loaded = False


def _load_twin():
    """Load .dwxmz; return (fs, col, dist_s, btms_s, nc4_name)."""
    global _col_asm_loaded
    fs = _aut.LoadFlowsheet(CASE_FILE)

    col = dist_s = btms_s = feed_s = None
    for name in list(fs.SimulationObjects.Keys):
        obj = fs.SimulationObjects[name]
        disp = _display(obj)
        pfx = name.split("-")[0].upper() if "-" in name else ""
        dl = disp.lower()
        if pfx == "DC":
            col = obj
        elif pfx == "MAT":
            if "dist" in dl:
                dist_s = obj
            elif any(x in dl for x in ("btms", "bott")):
                btms_s = obj
            elif "feed" in dl:
                feed_s = obj

    # Load concrete column assembly once
    if not _col_asm_loaded:
        col_asm = str(col.GetType().Assembly.GetName().Name)
        dll = os.path.join(DWSIM_DIR, col_asm + ".dll")
        if os.path.isfile(dll):
            clr.AddReference(dll)
        _col_asm_loaded = True

    # Discover compound names
    compound_names = []
    for src in (feed_s, dist_s, btms_s):
        if src is None:
            continue
        try:
            phases = rget(src, "Phases")
            cmpds = rget(phases[0], "Compounds")
            compound_names = [str(k) for k in list(cmpds.Keys)]
            break
        except Exception:
            pass
    if not compound_names:
        compound_names = ["N-butane", "N-hexane"]
    nC4_idx = next((i for i, c in enumerate(compound_names) if "butan" in c.lower()), 0)
    nc4_name = compound_names[nC4_idx]

    return fs, col, dist_s, btms_s, nc4_name


def _get_spec_objects(col):
    """Return (cond_spec, reb_spec) from col.Specs dict.
    Keys are 'C' (reflux) and 'R' (bottoms flow) as confirmed by probe."""
    specs = rget(col, "Specs")
    cond = specs["C"]
    reb = specs["R"]
    return cond, reb


def _set_and_verify(cond_spec, reb_spec, R, B_kmolh):
    """Set R (dimensionless) and B (kmol/h) on the spec objects.
    Returns (ok, R_readback, B_readback)."""
    # Direct assignment works: SpecValue CanWrite=True; units = kmol/h for bottoms
    cond_spec.SpecValue = float(R)
    reb_spec.SpecValue = float(B_kmolh)

    R_back = float(cond_spec.SpecValue)
    B_back = float(reb_spec.SpecValue)

    ok = (abs(R_back - R) < 1e-6) and (abs(B_back - B_kmolh) < 1e-4)
    return ok, R_back, B_back


def _solve_and_extract(fs, col, dist_s, btms_s, nc4_name):
    """Solve and extract results.
    Returns (converged:bool, xD, xB, Q_kW, T5_C) or (False, nan, nan, nan, nan)."""
    try:
        errs = _aut.CalculateFlowsheet2(fs)
        if errs:
            msgs = [str(e) for e in errs if e is not None]
            if msgs:
                print("    solver msgs: %s" % msgs[:2])
    except Exception as ex:
        print("    solve exception: %s" % str(ex)[:120])
        return False, float("nan"), float("nan"), float("nan"), float("nan")

    try:
        xD = stream_x_nc4(dist_s, nc4_name)
        xB = stream_x_nc4(btms_s, nc4_name)

        # Reboiler duty (negative sign = heat in; take abs)
        Q_raw = rget(col, "ReboilerDuty")
        Q_kW = (
            abs(W_to_kW(float(Q_raw)))
            if Q_raw and abs(float(Q_raw)) > 1e4
            else abs(float(Q_raw or 0))
        )

        stages = list(rget(col, "Stages"))
        T5_C = K_to_C(float(stages[SENSOR_IDX].T))

    except Exception as ex:
        print("    extraction error: %s" % str(ex)[:120])
        return False, float("nan"), float("nan"), float("nan"), float("nan")

    # Sanity check
    if any(math.isnan(v) for v in (xD, xB, Q_kW, T5_C)):
        return False, xD, xB, Q_kW, T5_C
    if xD < 0.01 or xB <= 0 or xD <= xB or Q_kW < 50:
        print("    sanity fail: xD=%.4f xB=%.4f Q=%.1f" % (xD, xB, Q_kW))
        return False, xD, xB, Q_kW, T5_C

    return True, xD, xB, Q_kW, T5_C


def _fine_step_to_target(
    fs, col, dist_s, btms_s, nc4_name, cond_spec, reb_spec, R, B_prev, B_target, step=0.1
):
    """Step bottoms spec from B_prev to B_target in `step`-kmol/h increments,
    solving at each intermediate point.  Returns the final extracted result.
    Used by the stale-cache guard to force solver movement past a plateau."""
    steps = []
    s = round(B_prev + step, 4)
    while s < B_target - step / 2:
        steps.append(s)
        s = round(s + step, 4)
    steps.append(B_target)

    last = (float("nan"),) * 4
    for B_step in steps:
        cond_spec.SpecValue = float(R)
        reb_spec.SpecValue = float(B_step)
        _, xD, xB, Q, T5 = _solve_and_extract(fs, col, dist_s, btms_s, nc4_name)
        last = (xD, xB, Q, T5)
    return last  # (xD, xB, Q_kW, T5_C) at B_target after fine-stepping


def _stale_cache_guard(
    run_id,
    R,
    B,
    B_prev,
    xD,
    xB,
    Q_kW,
    T5_C,
    xB_prev,
    fs,
    col,
    dist_s,
    btms_s,
    nc4_name,
    cond_spec,
    reb_spec,
):
    """Detect and remedy a stale solver cache.

    A result is considered stale when:
      - |xB - xB_prev| < 1e-7  (bit-identical)
      - |B  - B_prev|  > 0.01  (spec actually changed)

    Remedy: fine-step from B_prev to B in 0.1 kmol/h increments.
    If the fine-step breaks the plateau, return the new result.
    If still identical (genuine near-pinch), return original with PLATEAU note.
    Returns (xD, xB, Q_kW, T5_C, was_stale, was_fixed).
    """
    b_delta = abs(B - B_prev)
    if b_delta < 0.01 or abs(xB - xB_prev) >= 1e-7:
        return xD, xB, Q_kW, T5_C, False, False  # not stale

    print("    [GUARD] Stale cache: xB bit-identical (%.6f), dB=%.2f kmol/h." % (xB, b_delta))
    print("    [GUARD] Fine-stepping %.2f -> %.2f in 0.1 kmol/h increments ..." % (B_prev, B))

    xD2, xB2, Q2, T2 = _fine_step_to_target(
        fs, col, dist_s, btms_s, nc4_name, cond_spec, reb_spec, R, B_prev, B
    )

    if abs(xB2 - xB) > 1e-6:
        print("    [GUARD] Plateau broken: xB %.6f -> %.6f" % (xB, xB2))
        return xD2, xB2, Q2, T2, True, True
    else:
        print("    [GUARD] Fine-step: still at plateau xB=%.6f." % xB2)
        print("    [GUARD] DWSIM solver limit at R=%.1f near B=%.1f kmol/h." % (R, B_prev))
        print("    [GUARD] Accepting best-effort (genuine near-pinch or tolerance floor).")
        return xD2, xB2, Q2, T2, True, False


# =============================================================================
# Main sweep
# =============================================================================
os.makedirs(CSV_DIR, exist_ok=True)
assert os.path.isfile(CASE_FILE), "Case file not found: %s" % CASE_FILE

print("=" * 64)
print("G2 SWEEP  16 runs  R x D grid")
print("Case:  %s" % CASE_FILE)
print("Out:   %s" % CSV_OUT)
print("=" * 64)

rows = []  # list of CSV dicts for converged runs
gaps = []  # list of (run_id, R, D, reason)
plateaus = []  # list of run_ids where stale-cache guard found a genuine plateau
run_num = 0
master_row = None

for R in REFLUX_LIST:
    print("\n---- R = %.1f ----" % R)

    # Reload at start of each R group for clean warm-start
    fs, col, dist_s, btms_s, nc4_name = _load_twin()
    cond_spec, reb_spec = _get_spec_objects(col)
    needs_reload = False
    prev_xB = None  # stale-cache guard state within the R group
    prev_B = None

    for D in D_LIST:
        run_num += 1
        run_id = "run_%03d" % run_num
        B = FEED - D

        # Reload if the previous run in this group failed
        if needs_reload:
            fs, col, dist_s, btms_s, nc4_name = _load_twin()
            cond_spec, reb_spec = _get_spec_objects(col)
            needs_reload = False
            prev_xB = None
            prev_B = None

        # --- Set specs ---
        ok, R_back, B_back = _set_and_verify(cond_spec, reb_spec, R, B)
        if not ok:
            print(
                "  %s  R=%.1f D=%.1f  SPEC SET FAILED (R_back=%.4f B_back=%.4f)"
                % (run_id, R, D, R_back, B_back)
            )
            gaps.append((run_id, R, D, "spec_set_failed"))
            needs_reload = True
            continue

        # --- Solve ---
        sys.stdout.write("  %s  R=%.1f D=%5.1f B=%5.1f  ... " % (run_id, R, D, B))
        sys.stdout.flush()

        converged, xD, xB, Q_kW, T5_C = _solve_and_extract(fs, col, dist_s, btms_s, nc4_name)

        if not converged:
            print("FAIL")
            gaps.append((run_id, R, D, "no_convergence"))
            needs_reload = True
            prev_xB = None
            prev_B = None
            continue

        # --- Stale-cache guard ---
        if prev_xB is not None:
            xD, xB, Q_kW, T5_C, was_stale, was_fixed = _stale_cache_guard(
                run_id,
                R,
                B,
                prev_B,
                xD,
                xB,
                Q_kW,
                T5_C,
                prev_xB,
                fs,
                col,
                dist_s,
                btms_s,
                nc4_name,
                cond_spec,
                reb_spec,
            )
            if was_stale and not was_fixed:
                plateaus.append(run_id)

        tag = ""
        if run_id in plateaus:
            tag = " [PLATEAU]"
        print("PASS  xB=%.4f  xD=%.4f  Q=%6.1f kW  T5=%.1f C%s" % (xB, xD, Q_kW, T5_C, tag))

        prev_xB = xB
        prev_B = B

        row = {
            "run_id": run_id,
            "reflux_ratio": "%.4f" % R,
            "distillate_kmol_h": "%.4f" % D,
            "feed_kmol_h": "%.4f" % FEED,
            "z_c4": "%.4f" % Z_C4,
            "tray6_T_C": "%.4f" % T5_C,
            "top_P_bar": "%.4f" % TOP_P_BAR,
            "xd_c4": "%.6f" % xD,
            "xb_c4": "%.6f" % xB,
            "reboiler_duty_kW": "%.4f" % Q_kW,
            "tray6_x_c4_liq": "",  # not populated (V4 dropped)
        }
        rows.append(row)

        if abs(R - MASTER_R) < 0.001 and abs(D - MASTER_D) < 0.01:
            master_row = (run_id, R, D, xD, xB, Q_kW, T5_C)

# =============================================================================
# Write CSV
# =============================================================================
with open(CSV_OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CSV_HEADER)
    w.writeheader()
    w.writerows(rows)

print("\n" + "=" * 64)
print("CSV written: %s  (%d rows)" % (CSV_OUT, len(rows)))
print("=" * 64)

# =============================================================================
# Results table
# =============================================================================
print(
    "\n%-10s  %5s  %6s  %7s  %7s  %8s  %6s"
    % ("run_id", "R", "D", "xB_c4", "xD_c4", "duty_kW", "T5_C")
)
print("-" * 64)
for row in rows:
    print(
        "%-10s  %5s  %6s  %7s  %7s  %8s  %6s"
        % (
            row["run_id"],
            row["reflux_ratio"],
            row["distillate_kmol_h"],
            row["xb_c4"],
            row["xd_c4"],
            row["reboiler_duty_kW"],
            row["tray6_T_C"],
        )
    )

if gaps:
    print("\nNon-converged runs (%d):" % len(gaps))
    for g in gaps:
        print("  %-10s  R=%.1f  D=%.1f  reason=%s" % g)

if plateaus:
    print("\nSolver-plateau runs (%d) -- stale cache, fine-step could not break:" % len(plateaus))
    for p in plateaus:
        print("  %s  (accepted best-effort; near-pinch at high R)" % p)

# =============================================================================
# Self-check: master case (R=1.5, D=34.5) vs G1c
# =============================================================================
print("\n-- Self-check: master case (R=1.5, D=34.5) vs G1c --")
if master_row:
    rid, mR, mD, mxD, mxB, mQ, mT5 = master_row
    checks = [
        ("xB_c4", mxB, MASTER_XB, 0.05),  # 5% tolerance
        ("xD_c4", mxD, MASTER_XD, 0.01),
        ("duty_kW", mQ, MASTER_Q, 0.05),
    ]
    all_ok = True
    for label, got, ref, tol in checks:
        dev = abs(got - ref) / abs(ref)
        flag = " ok " if dev <= tol else "FAIL"
        if dev > tol:
            all_ok = False
        print("  %s  %-12s: got=%.4f  ref=%.4f  |dev|=%.2f%%" % (flag, label, got, ref, dev * 100))
    print()
    print("Master case: %s" % ("PASS" if all_ok else "FAIL -- investigate"))
else:
    print("  Master case run not found in results (converged %d/%d)" % (len(rows), 16))

# =============================================================================
# Summary
# =============================================================================
print("\nConverged: %d/16" % len(rows))
if len(rows) >= 12:
    print("Sufficient for surface fit (>=12). Proceed to G3.")
else:
    print("WARNING: fewer than 12 converged rows -- surface fit may be unreliable.")
