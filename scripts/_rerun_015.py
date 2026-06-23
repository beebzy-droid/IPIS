# Fresh re-run of run_015: R=3.0, D=34.5 (bottoms=65.5 kmol/h).
# Reloads from file so there is no warm-start contamination from run_014.
import sys, os, math

sys.path.insert(0, r"C:\Users\yubyu\AppData\Local\DWSIM")
import clr

clr.AddReference(r"C:\Users\yubyu\AppData\Local\DWSIM\DWSIM.Automation.dll")
from DWSIM.Automation import Automation3

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
CASE_FILE = r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\debutanizer_3a.dwxmz"
SENSOR_IDX = 5

R_TARGET = 3.0
B_TARGET = 65.5  # kmol/h   (D = 34.5)

import System.Reflection as Refl

_BF = Refl.BindingFlags.Public | Refl.BindingFlags.Instance


def rget(obj, pname):
    try:
        p = obj.GetType().GetProperty(pname)
        if p:
            return p.GetValue(obj)
    except:
        pass
    return getattr(obj, pname, None)


def rprop_dict(obj):
    d = {}
    for p in obj.GetType().GetProperties(_BF):
        try:
            d[str(p.Name)] = p.GetValue(obj)
        except:
            pass
    return d


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
        except:
            pass
    return float("nan")


# ---- Load fresh ----
aut = Automation3()
print("Loading fresh: %s" % CASE_FILE)
fs = aut.LoadFlowsheet(CASE_FILE)
print("Loaded.")

# Load concrete column assembly
col = None
dist_s = btms_s = feed_s = None
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

# Discover nc4 name
compound_names = []
for src in (feed_s, dist_s, btms_s):
    if src is None:
        continue
    try:
        phases = rget(src, "Phases")
        cmpds = rget(phases[0], "Compounds")
        compound_names = [str(k) for k in list(cmpds.Keys)]
        break
    except:
        pass
nc4_name = next((c for c in compound_names if "butan" in c.lower()), "N-butane")

# ---- Set specs ----
specs = rget(col, "Specs")
cond_spec = specs["C"]  # reflux ratio
reb_spec = specs["R"]  # bottoms kmol/h

print("\nBEFORE setting:")
print(
    "  specs['C'].SpecValue = %.6f  (reflux,  want %.1f)" % (float(cond_spec.SpecValue), R_TARGET)
)
print("  specs['R'].SpecValue = %.6f  (bottoms, want %.1f)" % (float(reb_spec.SpecValue), B_TARGET))

cond_spec.SpecValue = float(R_TARGET)
reb_spec.SpecValue = float(B_TARGET)

R_back = float(cond_spec.SpecValue)
B_back = float(reb_spec.SpecValue)
print("\nAFTER setting (read-back):")
print("  specs['C'].SpecValue = %.6f  (delta = %+.1e)" % (R_back, R_back - R_TARGET))
print("  specs['R'].SpecValue = %.6f  (delta = %+.1e)" % (B_back, B_back - B_TARGET))

assert abs(R_back - R_TARGET) < 1e-6, "Reflux spec did not take"
assert abs(B_back - B_TARGET) < 1e-4, "Bottoms spec did not take"
print("Specs confirmed.")

# ---- Solve ----
print("\nSolving ...")
errs = aut.CalculateFlowsheet2(fs)
if errs:
    msgs = [str(e) for e in errs if e is not None]
    if msgs:
        print("Solver messages:", msgs[:3])
print("Solve complete.")

# ---- Extract ----
xD = stream_x_nc4(dist_s, nc4_name)
xB = stream_x_nc4(btms_s, nc4_name)

Q_raw = rget(col, "ReboilerDuty")
Q_kW = abs(float(Q_raw) / 1e3) if Q_raw and abs(float(Q_raw)) > 1e4 else abs(float(Q_raw or 0))

T5_C = float(list(rget(col, "Stages"))[SENSOR_IDX].T) - 273.15

print("\n=== run_015 FRESH RESULT (R=3.0, D=34.5, B=65.5) ===")
print("  xB_c4          = %.6f" % xB)
print("  xD_c4          = %.6f" % xD)
print("  reboiler_duty  = %.4f kW" % Q_kW)
print("  tray6_T_C      = %.4f C" % T5_C)

# Compare with stale run_014 values
print("\nDelta vs stale run_014 (R=3.0, D=36.0):")
ref_xB, ref_xD, ref_Q, ref_T5 = 0.005068, 0.963223, 954.7756, 117.9216
print("  xB:   %+.6f  (stale %.6f)" % (xB - ref_xB, ref_xB))
print("  xD:   %+.6f  (stale %.6f)" % (xD - ref_xD, ref_xD))
print("  Q:    %+.4f kW  (stale %.4f)" % (Q_kW - ref_Q, ref_Q))
print("  T5:   %+.4f C   (stale %.4f)" % (T5_C - ref_T5, ref_T5))

# CSV patch values
print("\nCSV patch for run_015:")
print("  xb_c4           = %.6f" % xB)
print("  xd_c4           = %.6f" % xD)
print("  reboiler_duty_kW = %.4f" % Q_kW)
print("  tray6_T_C       = %.4f" % T5_C)
