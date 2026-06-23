# run_zvaried_sweep.py - Feed-z campaign for modules 3B.2/3B.3.
#
# Run:  python scripts/run_zvaried_sweep.py
# Env:  ipis conda (pythonnet 3.1.0; .NET Framework 4.8)
# Output: data/raw/dwsim/twin_runs_zvaried.csv
#
# Grid:  z in {0.30, 0.325, 0.35, 0.375, 0.40}  (feed nC4 mole fraction)
#        R in {0.8, 1.5, 2.2, 3.0}              (reflux ratio)
#        D in {37.0, 36.0, 34.5, 33.0} kmol/h  (distillate flow)
# Nominal: 5 x 4 x 4 = 80 runs; drops expected at high-purity corners.
#
# Quality gates (per-run, applied in order):
#   CONVERGENCE:  solver must return a sane result (xD>xB>0, Q>50 kW).
#   PLATEAU drop: stale-cache guard fires but cannot break plateau
#                 (was_stale AND NOT was_fixed) -> drop, not accept.
#   V2 mass-balance: |(xD*D + xB*B)/(z*F) - 1| > MB_TOL (0.5%) -> drop.
#
# Self-check: z=0.35 rows must reproduce twin_runs.csv (15-row reference).
#   Expected drop at R=3.0 / D=34.5 (genuine solver plateau -> PLATEAU rule).
#
# Column spec keys (confirmed by _probe_specs.py):
#   col.Specs['C']  -> Reflux Ratio (dimensionless)
#   col.Specs['R']  -> Bottoms flow (kmol/h)
#
# Feed composition is set via the stream's InputComposition dict (the GUI-editable
# input field).  Phases[0].Compounds.MoleFraction is a post-Calculate result that
# DWSIM's EqualizeOverallComposition overwrites at every stream recalc; we must
# set InputComposition and then call EqualizeOverallComposition+Calculate.
# Binary nC4/nC6 system; z_nc4 + z_nc6 = 1.

import sys, os, math, csv

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_FILE = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "data", "raw", "dwsim", "debutanizer_3a.dwxmz")
)
CSV_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "raw", "dwsim"))
CSV_OUT = os.path.join(CSV_DIR, "twin_runs_zvaried.csv")
SENSOR_IDX = 5
FEED = 100.0
TOP_P_BAR = 4.7
MB_TOL = 0.005  # V2: 0.5% mass-balance closure tolerance

Z_LIST = [0.30, 0.325, 0.35, 0.375, 0.40]
REFLUX_LIST = [0.8, 1.5, 2.2, 3.0]
D_LIST = [37.0, 36.0, 34.5, 33.0]

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

# --- z=0.35 reference (twin_runs.csv) for self-check ---------------------------
# (R, D) -> (xD, xB, Q_kW, T5_C)   15 rows; (3.0, 34.5) intentionally absent.
Z35_REF = {
    (0.8, 37.0): (0.888962, 0.033466, 517.6, 101.4),
    (0.8, 36.0): (0.900077, 0.040582, 501.2, 99.4),
    (0.8, 34.5): (0.913109, 0.053404, 476.8, 96.7),
    (0.8, 33.0): (0.922184, 0.068177, 453.0, 94.5),
    (1.5, 37.0): (0.924763, 0.012444, 672.7, 111.2),
    (1.5, 36.0): (0.944097, 0.015817, 647.2, 108.7),
    (1.5, 34.5): (0.968368, 0.024291, 609.3, 103.9),
    (1.5, 33.0): (0.982268, 0.038581, 574.4, 98.3),
    (2.2, 37.0): (0.934894, 0.006495, 825.7, 116.5),
    (2.2, 36.0): (0.957362, 0.008364, 790.6, 114.3),
    (2.2, 34.5): (0.985715, 0.015151, 738.0, 107.6),
    (2.2, 33.0): (0.995053, 0.032282, 696.4, 97.1),
    (3.0, 37.0): (0.939307, 0.003903, 1000.8, 119.8),
    (3.0, 36.0): (0.963223, 0.005068, 954.8, 117.9),
    (3.0, 33.0): (0.997939, 0.030860, 839.6, 94.0),
    # (3.0, 34.5) omitted -- genuine solver plateau, expect PLATEAU drop
}


# --- unit converters -----------------------------------------------------------
def K_to_C(v):
    return float(v) - 273.15


def W_to_kW(v):
    return float(v) / 1e3


# --- reflection helpers (CLR loaded lazily after first clr import) ------------
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


def rset(obj, pname, value):
    """Reflection-safe property setter.  Tries GetProperty first, then setattr."""
    try:
        p = obj.GetType().GetProperty(pname)
        if p and p.CanWrite:
            p.SetValue(obj, float(value))
            return True
    except Exception:
        pass
    try:
        setattr(obj, pname, float(value))
        return True
    except Exception:
        pass
    return False


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


def v2_mb_check(xD, xB, D, z, F=FEED, tol=MB_TOL):
    """V2 mass-balance closure: |(xD*D + xB*(F-D)) / (z*F) - 1| <= tol."""
    B = F - D
    lhs = xD * D + xB * B
    rhs = z * F
    if rhs < 1e-9:
        return False, float("inf")
    err = abs(lhs - rhs) / rhs
    return err <= tol, err


# =============================================================================
# Bootstrap CLR once
# =============================================================================
sys.path.insert(0, DWSIM_DIR)
import clr

clr.AddReference(os.path.join(DWSIM_DIR, "DWSIM.Automation.dll"))
from DWSIM.Automation import Automation3

_aut = Automation3()

_col_asm_loaded = False


# =============================================================================
# Core helpers
# =============================================================================
def _load_twin():
    """Load .dwxmz; return (fs, col, dist_s, btms_s, feed_s, nc4_name, nc6_name)."""
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

    if not _col_asm_loaded:
        col_asm = str(col.GetType().Assembly.GetName().Name)
        dll = os.path.join(DWSIM_DIR, col_asm + ".dll")
        if os.path.isfile(dll):
            clr.AddReference(dll)
        _col_asm_loaded = True

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

    nc4_name = next((c for c in compound_names if "butan" in c.lower()), compound_names[0])
    nc6_name = next(
        (c for c in compound_names if c != nc4_name and "hexan" in c.lower()),
        next((c for c in compound_names if c != nc4_name), None),
    )

    return fs, col, dist_s, btms_s, feed_s, nc4_name, nc6_name


def _find_method(obj, method_name, n_params):
    """Return first public-instance overload of method_name with n_params parameters."""
    for m in obj.GetType().GetMethods(_bf()):
        if str(m.Name) == method_name and len(m.GetParameters()) == n_params:
            return m
    return None


def _rinvoke0(obj, method_name):
    """Reflection-invoke a 0-argument method on obj's concrete type."""
    m = _find_method(obj, method_name, 0)
    if m:
        try:
            m.Invoke(obj, None)
        except Exception as ex:
            print("    [WARN] %s(): %s" % (method_name, str(ex)[:80]))


def _rinvoke1(obj, method_name, arg):
    """Reflection-invoke a 1-argument method on obj's concrete type."""
    m = _find_method(obj, method_name, 1)
    if m:
        try:
            m.Invoke(obj, [arg])
        except Exception as ex:
            print("    [WARN] %s(arg): %s" % (method_name, str(ex)[:80]))


def set_feed_z(feed_s, nc4_name, z_nc4):
    """Set feed nC4/nC6 composition via reflection on the concrete type.

    Probe _probe_feed_z.py (2026-06-14) findings:
      - InputComposition dict has EMPTY keys for this .dwxmz (legacy stream
        spec; new-style only) -> cannot use.
      - SetOverallMolarComposition(Double[]) exists on the concrete type but
        is invisible via ISimulationObject; must call via reflection-invoke.
        Internally it writes Phases[0].Compounds and calls
        NormalizeOverallMoleComposition.
      - Direct Phases[0].Compounds MoleFraction set via reflection also works
        (probe Test G: xB changed from 0.024 -> 0.014 when z 0.35->0.325).
    We use both paths so neither reliance on the interface nor on raw Phases[0]
    alone is a single point of failure.

    Physical verification (PR bubble-point from MCP, 2026-06-14):
      z=0.30: T_bubble(4.7 bar)~90 C  T_feed=87 C subcooled -> VF=0
      z=0.35: T_bubble(4.7 bar)~86 C  T_feed=87 C at bubble -> VF~0
      z=0.40: T_bubble(4.7 bar)~81 C  T_feed=87 C above     -> VF>0
    We log feed VF after re-flash; a shift with z is the functional test
    (readback alone is not sufficient -- run_015 lesson).
    """
    import System

    nc4n = nc4_name.lower().replace("-", "").replace(" ", "")

    # Step 1: Determine compound order from Phases[0]
    phases = rget(feed_s, "Phases")
    if phases is None:
        raise RuntimeError("Feed stream Phases not accessible")
    cmpds = rget(phases[0], "Compounds")
    if cmpds is None:
        raise RuntimeError("Feed stream Phases[0].Compounds not accessible")
    keys = [str(k) for k in list(cmpds.Keys)]
    if len(keys) < 2:
        raise RuntimeError("set_feed_z: expected >=2 compounds, got %s" % keys)

    # Step 2: Build mole-fraction list in compound order
    fracs = []
    for k in keys:
        k_norm = k.lower().replace("-", "").replace(" ", "")
        fracs.append(float(z_nc4) if k_norm == nc4n else float(1.0 - z_nc4))

    # Step 3a: Primary -- call SetOverallMolarComposition via reflection-invoke.
    # Probe Section D confirmed this method exists on the concrete type.
    # Creates a .NET Double[] and invokes the method.
    try:
        double_arr = System.Array.CreateInstance(System.Double, len(fracs))
        for i, f in enumerate(fracs):
            double_arr.SetValue(float(f), i)
        m_somc = feed_s.GetType().GetMethod("SetOverallMolarComposition")
        if m_somc:
            m_somc.Invoke(feed_s, [double_arr])
        else:
            raise RuntimeError("SetOverallMolarComposition method not found")
    except Exception as ex:
        # Step 3b: Fallback -- direct Phases[0].Compounds reflection set.
        # Probe Test G: confirmed this produces the correct column result.
        print("    [INFO] SetOverallMolarComposition fallback: %s" % str(ex)[:80])
        for k, f in zip(keys, fracs):
            p = cmpds[k].GetType().GetProperty("MoleFraction")
            if p and p.CanWrite:
                p.SetValue(cmpds[k], float(f))
            else:
                raise RuntimeError("Cannot set MoleFraction for compound '%s'" % k)

    # Step 4: Do NOT call stream.Calculate(None).
    # Probe Test G confirmed: setting Phases[0] + calling CalculateFlowsheet2 is
    # sufficient.  stream.Calculate(None) can trigger column callbacks that reinitialise
    # the solver state from master-case, causing a stale-cache slip on the first run of
    # a new (z, R) group when Δz is small (e.g., 0.35->0.375 was caught as z375_13
    # returning the master-case Q=609 kW instead of the correct ~960 kW).

    # Step 5: Readback from Phases[0] (SetOverallMolarComposition writes here)
    for k, f in zip(keys, fracs):
        got = rget(cmpds[k], "MoleFraction")
        if got is None or abs(float(got) - f) > 1e-4:
            raise RuntimeError(
                "set_feed_z readback failed for '%s': " "got %s, want %.6f" % (k, got, f)
            )

    # Step 6: Physical check -- VF must shift with z after re-flash.
    try:
        vap_cmpds = rget(phases[2], "Compounds")
        nc4_y = 0.0
        if vap_cmpds is not None:
            for k in list(vap_cmpds.Keys):
                if str(k).lower().replace("-", "").replace(" ", "") == nc4n:
                    v = rget(vap_cmpds[k], "MoleFraction")
                    if v is not None:
                        nc4_y = float(v)
        if nc4_y > 1e-4:
            state = "two-phase y_nC4=%.3f (T=87C > T_bubble)" % nc4_y
        else:
            state = "subcooled VF=0     (T=87C <= T_bubble)"
        print("    [feed-z] z_nC4=%.3f set  readback OK  post-flash: %s" % (z_nc4, state))
    except Exception as ex:
        print(
            "    [feed-z] z_nC4=%.3f set  readback OK  "
            "(VF check err: %s)" % (z_nc4, str(ex)[:50])
        )


def _get_spec_objects(col):
    specs = rget(col, "Specs")
    return specs["C"], specs["R"]  # cond=reflux, reb=bottoms


def _set_and_verify(cond_spec, reb_spec, R, B_kmolh):
    cond_spec.SpecValue = float(R)
    reb_spec.SpecValue = float(B_kmolh)
    R_back = float(cond_spec.SpecValue)
    B_back = float(reb_spec.SpecValue)
    ok = (abs(R_back - R) < 1e-6) and (abs(B_back - B_kmolh) < 1e-4)
    return ok, R_back, B_back


def _solve_and_extract(fs, col, dist_s, btms_s, nc4_name):
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

    if any(math.isnan(v) for v in (xD, xB, Q_kW, T5_C)):
        return False, xD, xB, Q_kW, T5_C
    if xD < 0.01 or xB <= 0 or xD <= xB or Q_kW < 50:
        print("    sanity fail: xD=%.4f xB=%.4f Q=%.1f" % (xD, xB, Q_kW))
        return False, xD, xB, Q_kW, T5_C
    return True, xD, xB, Q_kW, T5_C


def _fine_step_to_target(
    fs, col, dist_s, btms_s, nc4_name, cond_spec, reb_spec, R, B_prev, B_target, step=0.1
):
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
    """Returns (xD, xB, Q_kW, T5_C, was_stale, was_fixed)."""
    b_delta = abs(B - B_prev)
    if b_delta < 0.01 or abs(xB - xB_prev) >= 1e-7:
        return xD, xB, Q_kW, T5_C, False, False

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
        return xD2, xB2, Q2, T2, True, False


# =============================================================================
# Main sweep
# =============================================================================
os.makedirs(CSV_DIR, exist_ok=True)
assert os.path.isfile(CASE_FILE), "Case file not found: %s" % CASE_FILE

n_nominal = len(Z_LIST) * len(REFLUX_LIST) * len(D_LIST)
print("=" * 70)
print("FEED-Z SWEEP  %d nominal runs  z x R x D grid" % n_nominal)
print("Case:  %s" % CASE_FILE)
print("Out:   %s" % CSV_OUT)
print("=" * 70)

rows = []  # accepted rows (dicts)
drops = []  # (run_id, R, D, z, reason) for dropped/failed runs

for z in Z_LIST:
    z_code = "%03d" % round(z * 1000)
    z_run = 0  # counter within this z group

    print("\n" + "=" * 70)
    print("z = %.3f  (nC4 mole fraction)" % z)
    print("=" * 70)

    for R in REFLUX_LIST:
        print("\n---- z=%.3f  R=%.1f ----" % (z, R))

        # Reload and set z at the start of every (z, R) group
        fs, col, dist_s, btms_s, feed_s, nc4_name, nc6_name = _load_twin()
        try:
            set_feed_z(feed_s, nc4_name, z)
        except RuntimeError as ex:
            print("  set_feed_z FAILED: %s" % ex)
            for D in D_LIST:
                z_run += 1
                run_id = "z%s_%02d" % (z_code, z_run)
                drops.append((run_id, R, D, z, "set_feed_z_failed"))
            continue

        cond_spec, reb_spec = _get_spec_objects(col)
        needs_reload = False
        prev_xB = None
        prev_B = None

        for D in D_LIST:
            z_run += 1
            run_id = "z%s_%02d" % (z_code, z_run)
            B = FEED - D

            if needs_reload:
                fs, col, dist_s, btms_s, feed_s, nc4_name, nc6_name = _load_twin()
                try:
                    set_feed_z(feed_s, nc4_name, z)
                except RuntimeError as ex:
                    print("  set_feed_z FAILED on reload: %s" % ex)
                    drops.append((run_id, R, D, z, "set_feed_z_failed_reload"))
                    continue
                cond_spec, reb_spec = _get_spec_objects(col)
                needs_reload = False
                prev_xB = None
                prev_B = None

            # --- Set column specs ---
            ok, R_back, B_back = _set_and_verify(cond_spec, reb_spec, R, B)
            if not ok:
                print("  %s  SPEC SET FAILED (R_back=%.4f B_back=%.4f)" % (run_id, R_back, B_back))
                drops.append((run_id, R, D, z, "spec_set_failed"))
                needs_reload = True
                continue

            # --- Solve ---
            sys.stdout.write("  %s  z=%.3f R=%.1f D=%5.1f B=%5.1f  ... " % (run_id, z, R, D, B))
            sys.stdout.flush()

            converged, xD, xB, Q_kW, T5_C = _solve_and_extract(fs, col, dist_s, btms_s, nc4_name)

            if not converged:
                print("FAIL (convergence)")
                drops.append((run_id, R, D, z, "no_convergence"))
                needs_reload = True
                prev_xB = None
                prev_B = None
                continue

            # --- Stale-cache guard ---
            was_stale = was_fixed = False
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

            # --- PLATEAU drop: spec not reached; solver limit at high-purity corner ---
            if was_stale and not was_fixed:
                print("DROP [plateau -- solver spec not reached at R=%.1f B=%.1f]" % (R, B))
                drops.append((run_id, R, D, z, "plateau_solver_limit"))
                needs_reload = True
                prev_xB = None
                prev_B = None
                continue

            # --- V2 mass-balance screen ---
            ok_v2, closure_err = v2_mb_check(xD, xB, D, z)
            if not ok_v2:
                print("DROP [V2 MB closure %.1f%% > %.0f%%]" % (closure_err * 100, MB_TOL * 100))
                drops.append((run_id, R, D, z, "v2_mb_%.1fpct" % (closure_err * 100)))
                needs_reload = True
                prev_xB = None
                prev_B = None
                continue

            print("PASS  xB=%.5f  xD=%.5f  Q=%7.1f kW  T5=%6.2f C" % (xB, xD, Q_kW, T5_C))

            prev_xB = xB
            prev_B = B

            rows.append(
                {
                    "run_id": run_id,
                    "reflux_ratio": "%.4f" % R,
                    "distillate_kmol_h": "%.4f" % D,
                    "feed_kmol_h": "%.4f" % FEED,
                    "z_c4": "%.4f" % z,
                    "tray6_T_C": "%.4f" % T5_C,
                    "top_P_bar": "%.4f" % TOP_P_BAR,
                    "xd_c4": "%.6f" % xD,
                    "xb_c4": "%.6f" % xB,
                    "reboiler_duty_kW": "%.4f" % Q_kW,
                    "tray6_x_c4_liq": "",
                }
            )

# =============================================================================
# Write CSV
# =============================================================================
with open(CSV_OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CSV_HEADER)
    w.writeheader()
    w.writerows(rows)

print("\n" + "=" * 70)
print("CSV written: %s  (%d rows)" % (CSV_OUT, len(rows)))
print("=" * 70)

# =============================================================================
# Results table
# =============================================================================
print(
    "\n%-14s  %5s  %6s  %6s  %8s  %8s  %8s  %6s"
    % ("run_id", "z", "R", "D", "xB_c4", "xD_c4", "duty_kW", "T5_C")
)
print("-" * 75)
for row in rows:
    print(
        "%-14s  %5s  %5s  %6s  %8s  %8s  %8s  %6s"
        % (
            row["run_id"],
            row["z_c4"],
            row["reflux_ratio"],
            row["distillate_kmol_h"],
            row["xb_c4"],
            row["xd_c4"],
            row["reboiler_duty_kW"],
            row["tray6_T_C"],
        )
    )

# Per-z summary
print()
for z in Z_LIST:
    z_code = "%03d" % round(z * 1000)
    z_rows = [r for r in rows if abs(float(r["z_c4"]) - z) < 0.001]
    z_drops = [d for d in drops if abs(d[3] - z) < 0.001]
    print("  z=%.3f: %2d passed  %d dropped" % (z, len(z_rows), len(z_drops)))

if drops:
    print("\nDropped runs (%d total):" % len(drops))
    for rid, R, D, z_val, reason in drops:
        print("  %-14s  z=%.3f R=%.1f D=%.1f  %s" % (rid, z_val, R, D, reason))

# =============================================================================
# Self-check: z=0.35 rows vs twin_runs.csv reference
# =============================================================================
print("\n" + "=" * 70)
print("Self-check: z=0.35 rows vs twin_runs.csv (15-row reference)")
print("=" * 70)

z35 = {
    (round(float(r["reflux_ratio"]), 1), round(float(r["distillate_kmol_h"]), 1)): r
    for r in rows
    if abs(float(r["z_c4"]) - 0.35) < 0.001
}

all_ok = True
n_checked = 0
TOLS = {"xD": 0.01, "xB": 0.05, "Q": 0.05, "T5": 0.02}

for R_ref, D_ref in sorted(Z35_REF.keys()):
    xD_ref, xB_ref, Q_ref, T5_ref = Z35_REF[(R_ref, D_ref)]
    key = next(((r, d) for (r, d) in z35 if abs(r - R_ref) < 0.05 and abs(d - D_ref) < 0.1), None)
    if key is None:
        print("  MISS   R=%.1f D=%.1f  (not found in z=0.35 results)" % (R_ref, D_ref))
        all_ok = False
        continue
    row = z35[key]
    got = {
        "xD": float(row["xd_c4"]),
        "xB": float(row["xb_c4"]),
        "Q": float(row["reboiler_duty_kW"]),
        "T5": float(row["tray6_T_C"]),
    }
    ref = {"xD": xD_ref, "xB": xB_ref, "Q": Q_ref, "T5": T5_ref}
    devs = {k: abs(got[k] - ref[k]) / max(abs(ref[k]), 1e-6) for k in got}
    fails = [k for k in devs if devs[k] > TOLS[k]]
    status = "ok  " if not fails else "FAIL"
    if fails:
        all_ok = False
    n_checked += 1
    print(
        "  %s  R=%.1f D=%.1f  xD=%.5f(%+.2f%%)  xB=%.5f(%+.2f%%)  Q=%.1f(%+.2f%%)"
        % (
            status,
            R_ref,
            D_ref,
            got["xD"],
            (got["xD"] - xD_ref) / xD_ref * 100,
            got["xB"],
            (got["xB"] - xB_ref) / xB_ref * 100,
            got["Q"],
            (got["Q"] - Q_ref) / Q_ref * 100,
        )
    )

# Confirm that (3.0, 34.5) was dropped
rd_plateau = next(((r, d) for (r, d) in z35 if abs(r - 3.0) < 0.05 and abs(d - 34.5) < 0.1), None)
if rd_plateau is None:
    print("  ok    R=3.0 D=34.5  correctly dropped (solver plateau -- expected)")
else:
    print("  NOTE  R=3.0 D=34.5  present in z=0.35 results (expected drop; investigate)")

print()
print(
    "Self-check z=0.35: %s  (%d/%d reference rows matched)"
    % ("PASS" if all_ok else "FAIL", n_checked, len(Z35_REF))
)

# =============================================================================
# Self-check 2a: xD monotone in z for each (R, D) group
# As z_nC4 increases, more nC4 in feed -> xD and xB both increase.
# Check master column D=34.5 plus any (R,D) group present in all 5 z values.
# =============================================================================
print("\n" + "=" * 70)
print("Self-check 2a: xD monotone increasing in z (for each R,D group)")
print("=" * 70)

sc2a_ok = True
for R_chk in REFLUX_LIST:
    for D_chk in D_LIST:
        pts = []
        for row in rows:
            if (
                abs(float(row["reflux_ratio"]) - R_chk) < 0.05
                and abs(float(row["distillate_kmol_h"]) - D_chk) < 0.1
            ):
                pts.append((float(row["z_c4"]), float(row["xd_c4"]), float(row["xb_c4"])))
        pts.sort(key=lambda t: t[0])
        if len(pts) < 2:
            continue
        bad_xD = [i for i in range(1, len(pts)) if pts[i][1] < pts[i - 1][1] - 1e-4]
        bad_xB = [i for i in range(1, len(pts)) if pts[i][2] < pts[i - 1][2] - 1e-4]
        status = "ok  " if not (bad_xD or bad_xB) else "FAIL"
        if bad_xD or bad_xB:
            sc2a_ok = False
        zvals = " ".join("%.3f" % p[0] for p in pts)
        xd_str = " ".join("%.4f" % p[1] for p in pts)
        print(
            "  %s  R=%.1f D=%.1f  z=[%s]  xD=[%s]%s"
            % (
                status,
                R_chk,
                D_chk,
                zvals,
                xd_str,
                ("  xD_bad@z%s" % pts[bad_xD[0]][0]) if bad_xD else "",
            )
        )
print("Self-check 2a: %s" % ("PASS" if sc2a_ok else "FAIL -- non-monotone xD found"))

# =============================================================================
# Self-check 2b: V2 residual audit on all accepted rows
# Every accepted row must pass the 0.5% MB closure screen.
# =============================================================================
print()
print("Self-check 2b: V2 mass-balance residual on all %d accepted rows" % len(rows))
sc2b_ok = True
max_err = 0.0
n_mb_fail = 0
for row in rows:
    xD_r = float(row["xd_c4"])
    xB_r = float(row["xb_c4"])
    D_r = float(row["distillate_kmol_h"])
    z_r = float(row["z_c4"])
    ok_v, err_v = v2_mb_check(xD_r, xB_r, D_r, z_r)
    if not ok_v:
        print(
            "  FAIL  %-14s  z=%.3f R=%s D=%s  MB=%.3f%%"
            % (row["run_id"], z_r, row["reflux_ratio"], row["distillate_kmol_h"], err_v * 100)
        )
        sc2b_ok = False
        n_mb_fail += 1
    max_err = max(max_err, err_v)
if sc2b_ok:
    print("  ok   all rows pass V2  (max residual = %.4f%%)" % (max_err * 100))
print("Self-check 2b: %s" % ("PASS" if sc2b_ok else "FAIL -- %d rows exceed 0.5%% MB" % n_mb_fail))

# =============================================================================
# Summary
# =============================================================================
print("\nTotal: %d/%d accepted  |  %d dropped" % (len(rows), n_nominal, len(drops)))
if len(rows) >= 60:
    print("Sufficient for surface fit (>=60). Proceed to G3/3B.")
else:
    print("WARNING: fewer than 60 accepted rows -- check drops above.")
