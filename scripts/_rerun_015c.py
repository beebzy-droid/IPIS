# Break the 65.0->65.5 solver plateau via overshoot and ultra-fine stepping.
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


def snap(aut, fs, col, dist_s, btms_s, nc4_name, cond, reb, R_set, B_set):
    cond.SpecValue = float(R_set)
    reb.SpecValue = float(B_set)
    aut.CalculateFlowsheet2(fs)
    xB = stream_x_nc4(btms_s, nc4_name)
    xD = stream_x_nc4(dist_s, nc4_name)
    Q_raw = rget(col, "ReboilerDuty")
    Q = abs(float(Q_raw) / 1e3) if Q_raw and abs(float(Q_raw)) > 1e4 else 0
    T5 = float(list(rget(col, "Stages"))[SENSOR_IDX].T) - 273.15
    return xB, xD, Q, T5


def load():
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
    return aut, fs, col, dist_s, btms_s, nc4_name, specs["C"], specs["R"]


def run_path(label, steps_RB):
    print("\n=== %s ===" % label)
    aut, fs, col, dist_s, btms_s, nc4, cond, reb = load()
    prev_xB = None
    for R_set, B_set in steps_RB:
        xB, xD, Q, T5 = snap(aut, fs, col, dist_s, btms_s, nc4, cond, reb, R_set, B_set)
        stale = " <SAME>" if prev_xB is not None and abs(xB - prev_xB) < 1e-7 else ""
        print(
            "  R=%.1f B=%5.2f  xB=%.6f  xD=%.6f  Q=%7.2f kW  T5=%6.2f C%s"
            % (R_set, B_set, xB, xD, Q, T5, stale)
        )
        prev_xB = xB
    return xB, xD, Q, T5  # last result


# Path A: overshoot to B=66 then return to B=65.5
run_path(
    "JIGGLE: 63->64->65->66->65.5",
    [(3.0, 63.0), (3.0, 64.0), (3.0, 65.0), (3.0, 66.0), (3.0, 65.5)],
)

# Path B: ultra-fine 0.1 step from 65.0 to 65.5
run_path(
    "FINE-STEP 0.1 kmol/h from 65.0 to 65.5",
    [
        (3.0, 63.0),
        (3.0, 64.0),
        (3.0, 65.0),
        (3.0, 65.1),
        (3.0, 65.2),
        (3.0, 65.3),
        (3.0, 65.4),
        (3.0, 65.5),
    ],
)

# Path C: come from R=2.2 at B=65.5, then increase R to 3.0
xB, xD, Q, T5 = run_path("FROM R=2.2 B=65.5 -> R=3.0 B=65.5", [(2.2, 65.5), (3.0, 65.5)])

print()
print("Best candidate for run_015 (R=3.0, B=65.5 / D=34.5):")
print("  xB_c4            = %.6f" % xB)
print("  xD_c4            = %.6f" % xD)
print("  reboiler_duty_kW = %.4f" % Q)
print("  tray6_T_C        = %.4f" % T5)
