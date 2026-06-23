# Two-step initialisation fix for run_015:
#   Step 1: from master-case load, solve run_013 (R=3.0, B=63) to enter R=3.0 attractor.
#   Step 2: step B to 65.5 and solve -> correct run_015 result.
# Also tries direct B=63->B=65.5 jump and logs solver messages for each step.
import sys, os, math

sys.path.insert(0, r"C:\Users\yubyu\AppData\Local\DWSIM")
import clr

clr.AddReference(r"C:\Users\yubyu\AppData\Local\DWSIM\DWSIM.Automation.dll")
from DWSIM.Automation import Automation3
import System.Reflection as Refl

_BF = Refl.BindingFlags.Public | Refl.BindingFlags.Instance

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
CASE_FILE = r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\debutanizer_3a.dwxmz"
SENSOR_IDX = 5


def rget(obj, pname):
    try:
        p = obj.GetType().GetProperty(pname)
        if p:
            return p.GetValue(obj)
    except:
        pass
    return getattr(obj, pname, None)


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


def solve_and_report(aut, fs, col, dist_s, btms_s, nc4_name, label):
    errs = aut.CalculateFlowsheet2(fs)
    msgs = [str(e) for e in errs if e is not None] if errs else []
    xD = stream_x_nc4(dist_s, nc4_name)
    xB = stream_x_nc4(btms_s, nc4_name)
    Q_raw = rget(col, "ReboilerDuty")
    Q_kW = abs(float(Q_raw) / 1e3) if Q_raw and abs(float(Q_raw)) > 1e4 else abs(float(Q_raw or 0))
    T5 = float(list(rget(col, "Stages"))[SENSOR_IDX].T) - 273.15
    print(
        "  %-30s  xB=%.6f  xD=%.6f  Q=%7.2f kW  T5=%6.2f C%s"
        % (label, xB, xD, Q_kW, T5, ("  [msgs: %s]" % msgs[:1]) if msgs else "")
    )
    return xB, xD, Q_kW, T5


# ---- Setup ----
aut = Automation3()
print("Loading fresh: %s" % CASE_FILE)
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

specs = rget(col, "Specs")
cond = specs["C"]  # reflux
reb = specs["R"]  # bottoms kmol/h

print(
    "Loaded. Initial specs: R=%.2f  B=%.2f kmol/h\n" % (float(cond.SpecValue), float(reb.SpecValue))
)

print("=== APPROACH A: step through run_013 -> run_014 -> run_015 ===")
for R_set, B_set, label in [
    (3.0, 63.0, "run_013 (R=3.0, B=63)"),
    (3.0, 64.0, "run_014 (R=3.0, B=64)"),
    (3.0, 65.5, "run_015 (R=3.0, B=65.5)"),
]:
    cond.SpecValue = float(R_set)
    reb.SpecValue = float(B_set)
    assert abs(float(cond.SpecValue) - R_set) < 1e-6
    assert abs(float(reb.SpecValue) - B_set) < 1e-4
    solve_and_report(aut, fs, col, dist_s, btms_s, nc4_name, label)

print()
print("=== APPROACH B: reload, then run_013 -> jump directly to run_015 ===")
fs = aut.LoadFlowsheet(CASE_FILE)
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
specs = rget(col, "Specs")
cond = specs["C"]
reb = specs["R"]

for R_set, B_set, label in [
    (3.0, 63.0, "run_013 (R=3.0, B=63)"),
    (3.0, 65.5, "run_015 direct (B=63->65.5)"),
]:
    cond.SpecValue = float(R_set)
    reb.SpecValue = float(B_set)
    solve_and_report(aut, fs, col, dist_s, btms_s, nc4_name, label)

print()
print("=== APPROACH C: reload, fine-step R=3.0, B from 63 to 65.5 ===")
fs = aut.LoadFlowsheet(CASE_FILE)
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
specs = rget(col, "Specs")
cond = specs["C"]
reb = specs["R"]

steps = [63.0, 63.5, 64.0, 64.5, 65.0, 65.5]
for B_set in steps:
    cond.SpecValue = 3.0
    reb.SpecValue = float(B_set)
    solve_and_report(aut, fs, col, dist_s, btms_s, nc4_name, "R=3.0 B=%.1f" % B_set)
