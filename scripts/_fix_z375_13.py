# _fix_z375_13.py  -- targeted re-run of z375_13 (z=0.375, R=3.0, D=37.0)
# Root cause: stream.Calculate() caused column callback that reset solver to master-case
# state; at Dz=+0.025 the first-run stale cache passed V2 at 0.4%.
# Fix: set z WITHOUT stream.Calculate(), warm-start at R=2.2 to escape master-case
# basin, then step to R=3.0.  Patch z375_13 row in twin_runs_zvaried.csv.
import sys, os, csv, math

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
CASE_FILE = r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\debutanizer_3a.dwxmz"
CSV_PATH = r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\twin_runs_zvaried.csv"
SENSOR_IDX = 5

sys.path.insert(0, DWSIM_DIR)
import clr

clr.AddReference(os.path.join(DWSIM_DIR, "DWSIM.Automation.dll"))
from DWSIM.Automation import Automation3
import System, System.Reflection as Refl

_BF = Refl.BindingFlags.Public | Refl.BindingFlags.Instance


def rget(obj, pname):
    try:
        p = obj.GetType().GetProperty(pname)
        if p:
            return p.GetValue(obj)
    except:
        pass
    return getattr(obj, pname, None)


def stream_x_nc4(stream, nc4n):
    phases = rget(stream, "Phases")
    if phases is None:
        return float("nan")
    for ph in [2, 3, 0]:
        try:
            cmpds = rget(phases[ph], "Compounds")
            for k in list(cmpds.Keys):
                if str(k).lower().replace("-", "").replace(" ", "") == nc4n:
                    v = rget(cmpds[k], "MoleFraction")
                    if v is not None and float(v) > 1e-12:
                        return float(v)
        except:
            pass
    return float("nan")


aut = Automation3()
fs = aut.LoadFlowsheet(CASE_FILE)

col = dist_s = btms_s = feed_s = None
for name in list(fs.SimulationObjects.Keys):
    obj = fs.SimulationObjects[name]
    pfx = name.split("-")[0].upper() if "-" in name else ""
    try:
        disp = str(obj.GraphicObject.Tag)
    except:
        disp = ""
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

col_asm = str(col.GetType().Assembly.GetName().Name)
clr.AddReference(os.path.join(DWSIM_DIR, col_asm + ".dll"))

# Discover compound keys and nc4 name
phases0 = rget(feed_s, "Phases")
cmpds0 = rget(phases0[0], "Compounds")
keys = [str(k) for k in list(cmpds0.Keys)]
nc4_name = next((c for c in keys if "butan" in c.lower()), keys[0])
nc4n = nc4_name.lower().replace("-", "").replace(" ", "")

m_somc = feed_s.GetType().GetMethod("SetOverallMolarComposition")
Z_TARGET = 0.375


def set_z(z_val):
    """Set feed to z_val via SetOverallMolarComposition, no stream.Calculate()."""
    fracs_ = [
        float(z_val) if k.lower().replace("-", "").replace(" ", "") == nc4n else float(1.0 - z_val)
        for k in keys
    ]
    arr = System.Array.CreateInstance(System.Double, len(fracs_))
    for i, f in enumerate(fracs_):
        arr.SetValue(f, i)
    m_somc.Invoke(feed_s, [arr])
    for k, f in zip(keys, fracs_):
        got = float(rget(cmpds0[k], "MoleFraction") or 0)
        assert abs(got - f) < 1e-4, "set_z readback fail: %s %.4f != %.4f" % (k, got, f)
    print("  z set to %.4f" % z_val)


# Get column specs
specs = rget(col, "Specs")
cond_spec = specs["C"]
reb_spec = specs["R"]


def solve_at(R, B, label):
    cond_spec.SpecValue = float(R)
    reb_spec.SpecValue = float(B)
    aut.CalculateFlowsheet2(fs)
    xD = stream_x_nc4(dist_s, nc4n)
    xB = stream_x_nc4(btms_s, nc4n)
    Q_raw = rget(col, "ReboilerDuty")
    Q_kW = abs(float(Q_raw) / 1e3) if Q_raw and abs(float(Q_raw)) > 1e4 else abs(float(Q_raw or 0))
    stages = list(rget(col, "Stages"))
    T5_C = float(stages[SENSOR_IDX].T) - 273.15
    print("  %-35s  xD=%.5f  xB=%.5f  Q=%7.1f kW  T5=%6.2f C" % (label, xD, xB, Q_kW, T5_C))
    return xD, xB, Q_kW, T5_C


# Strategy: the loaded flowsheet has z=0.35, R=1.5, B=65.5.
# Step 1: keep z=0.35 and jump directly to R=3.0, B=63 (same as G2 sweep did).
# Step 2: nudge z 0.35 -> 0.375 while holding R=3.0, B=63.
# This avoids the R=2.2 stale attractor that traps the solver when z is set first.

# Strategy: z=0.375 set before any solve. Approach D=37 from below.
# z375_16 (R=3.0, D=33, B=67) converged at Q=826 in main sweep.
# Fine-step B from 67 down to 63 (D from 33 to 37) in 0.5 kmol/h steps.
print("Setting z=0.375 before first solve")
set_z(0.375)

print("\nPhase 1: R=3.0, fine-step B from 67 (D=33) down to 63 (D=37)")
steps = []
b = 67.0
while b >= 63.0 - 1e-9:
    steps.append(round(b, 1))
    b -= 0.5
for B_step in steps:
    D_step = 100.0 - B_step
    xD, xB, Q, T5 = solve_at(3.0, B_step, "R=3.0 D=%.1f B=%.1f" % (D_step, B_step))

# Sanity checks
MB_ERR = abs(xD * 37.0 + xB * 63.0 - Z_TARGET * 100) / (Z_TARGET * 100)
print("\nV2 mass balance error: %.4f%%" % (MB_ERR * 100))
assert MB_ERR < 0.005, "V2 FAIL: %.4f%%" % (MB_ERR * 100)
assert Q > 800, "Q sanity fail: %.1f kW (should be ~950-1000 kW)" % Q
print("Sanity checks: PASS  (Q=%.1f kW, V2=%.3f%%)" % (Q, MB_ERR * 100))

# Stale-cache check: result must NOT match master case
MASTER = dict(xd=0.968368, xb=0.024291, Q=609.2814, T5=103.8565)
assert (
    abs(xD - MASTER["xd"]) > 0.01 or abs(Q - MASTER["Q"]) > 50
), "STALE: result still matches master case!"
print("Stale-cache check: PASS  (Q differs from master by %.0f kW)" % abs(Q - MASTER["Q"]))

# --- Patch CSV ---
with open(CSV_PATH, newline="") as f:
    rows = list(csv.DictReader(f))
fieldnames = rows[0].keys() if rows else []

patched = False
for row in rows:
    if row["run_id"] == "z375_13":
        old_Q = row["reboiler_duty_kW"]
        old_xD = row["xd_c4"]
        row["tray6_T_C"] = "%.4f" % T5
        row["xd_c4"] = "%.6f" % xD
        row["xb_c4"] = "%.6f" % xB
        row["reboiler_duty_kW"] = "%.4f" % Q
        patched = True
        print("\nCSV patch: z375_13")
        print("  Q:  %.4f -> %.4f kW" % (float(old_Q), Q))
        print("  xD: %s -> %.6f" % (old_xD, xD))
        break

if not patched:
    print("WARNING: z375_13 not found in CSV; appending new row")
    new_row = {
        "run_id": "z375_13",
        "reflux_ratio": "3.0000",
        "distillate_kmol_h": "37.0000",
        "feed_kmol_h": "100.0000",
        "z_c4": "0.3750",
        "tray6_T_C": "%.4f" % T5,
        "top_P_bar": "4.7000",
        "xd_c4": "%.6f" % xD,
        "xb_c4": "%.6f" % xB,
        "reboiler_duty_kW": "%.4f" % Q,
        "tray6_x_c4_liq": "",
    }
    rows.append(new_row)

with open(CSV_PATH, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("CSV written: %s  (%d rows)" % (CSV_PATH, len(rows)))
