# _probe_feed_z.py - Introspect the feed MaterialStream to find the correct
# input-composition setter (the field the DWSIM GUI edits, not Phases[0] results).
#
# Also tests whether setting that field + re-flashing actually changes xD/xB
# when CalculateFlowsheet2 is called.
import sys, os

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
CASE_FILE = r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\debutanizer_3a.dwxmz"
SENSOR_IDX = 5

sys.path.insert(0, DWSIM_DIR)
import clr

clr.AddReference(os.path.join(DWSIM_DIR, "DWSIM.Automation.dll"))
from DWSIM.Automation import Automation3
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


def stream_x_nc4(stream):
    phases = rget(stream, "Phases")
    for ph in [2, 3, 0]:
        try:
            cmpds = rget(phases[ph], "Compounds")
            for k in list(cmpds.Keys):
                if "butan" in str(k).lower():
                    v = rget(cmpds[k], "MoleFraction")
                    if v is not None and float(v) > 1e-9:
                        return float(v)
        except:
            pass
    return float("nan")


aut = Automation3()
fs = aut.LoadFlowsheet(CASE_FILE)

col = feed_s = dist_s = btms_s = None
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

print("Feed stream concrete type: %s" % feed_s.GetType().FullName)
print()

# =========================================================
# A: All CanWrite properties - look for composition hooks
# =========================================================
COMP_KEYS = [
    "frac",
    "comp",
    "mole",
    "mass",
    "amount",
    "formula",
    "overall",
    "basis",
    "percent",
    "phase0",
    "input",
]
print("=== A: CanWrite properties with composition-related names ===")
for p in feed_s.GetType().GetProperties(_BF):
    if not p.CanWrite:
        continue
    pn = str(p.Name)
    if not any(k in pn.lower() for k in COMP_KEYS):
        continue
    try:
        val = p.GetValue(feed_s)
        vt = val.GetType().FullName if val is not None else "None"
        print("  %-55s  type=%-35s" % (pn, vt[:35]))
    except Exception as e:
        print("  %-55s  (err: %s)" % (pn, str(e)[:50]))

# =========================================================
# B: Current Phases[0].Compounds mole fractions
# =========================================================
print()
print("=== B: Phases[0].Compounds.MoleFraction (baseline z=0.35) ===")
phases = rget(feed_s, "Phases")
cmpds0 = rget(phases[0], "Compounds")
for k in list(cmpds0.Keys):
    mf = rget(cmpds0[k], "MoleFraction")
    print("  %-30s = %s" % (k, mf))

# =========================================================
# C: ComponentMolarFractions / Overallcomposition
# =========================================================
print()
print("=== C: Named dict candidates ===")
for cname in [
    "ComponentMolarFractions",
    "OverallComposition",
    "Overallcomposition",
    "MolarComposition",
    "ComponentMoleFractions",
    "FeedComposition",
]:
    obj = rget(feed_s, cname)
    t = obj.GetType().Name if obj is not None else "None"
    print("  %-40s -> %s" % (cname, t))
    if obj is not None:
        try:
            for k in list(obj.Keys):
                print("      [%s] = %s" % (k, obj[k]))
        except:
            pass

# =========================================================
# D: Methods containing calculate / flash / update / spec
# =========================================================
print()
print("=== D: Methods containing calc/flash/update/set/spec ===")
MKEYS = ["calc", "flash", "update", "set", "spec", "compos"]
seen = set()
for m in feed_s.GetType().GetMethods(_BF):
    mn = str(m.Name)
    if mn in seen or not any(k in mn.lower() for k in MKEYS):
        continue
    seen.add(mn)
    params = ", ".join("%s" % p.ParameterType.Name for p in m.GetParameters())
    print("  %-50s (%s)" % (mn, params[:60]))

# =========================================================
# E: Baseline solve to record xD/xB before changing z
# =========================================================
print()
print("=== E: Baseline column solve (z=0.35 default) ===")
aut.CalculateFlowsheet2(fs)
xD_base = stream_x_nc4(dist_s)
xB_base = stream_x_nc4(btms_s)
print("  xD_nC4 = %.6f   xB_nC4 = %.6f" % (xD_base, xB_base))

# =========================================================
# F: Try ComponentMolarFractions setter -> resolve -> check
# =========================================================
print()
print("=== F: Test ComponentMolarFractions setter (set z=0.30) ===")
cmf = rget(feed_s, "ComponentMolarFractions")
if cmf is not None:
    print("  Found ComponentMolarFractions (%s)" % cmf.GetType().Name)
    # Set nC4=0.30, nC6=0.70
    for k in list(cmf.Keys):
        if "butan" in str(k).lower():
            cmf[k] = float(0.30)
            print("  Set  cmf[%s] = 0.30" % k)
        else:
            cmf[k] = float(0.70)
            print("  Set  cmf[%s] = 0.70" % k)
    # Readback
    for k in list(cmf.Keys):
        print("  Read cmf[%s] = %s" % (k, cmf[k]))
    # Try stream-level Calculate if available
    stream_calc_ok = False
    for mn in ["Calculate", "CalculateFlow", "Flashcalc", "Update", "Solve"]:
        m = feed_s.GetType().GetMethod(mn, _BF)
        if m:
            params = m.GetParameters()
            if len(params) == 0:
                try:
                    m.Invoke(feed_s, None)
                    stream_calc_ok = True
                    print("  Called stream.%s() -> OK" % mn)
                    break
                except Exception as e:
                    print("  stream.%s() failed: %s" % (mn, str(e)[:60]))
    # Full flowsheet solve
    aut.CalculateFlowsheet2(fs)
    xD_f = stream_x_nc4(dist_s)
    xB_f = stream_x_nc4(btms_s)
    print("  xD after z=0.30: %.6f  (was %.6f,  delta=%+.4f)" % (xD_f, xD_base, xD_f - xD_base))
    print("  xB after z=0.30: %.6f  (was %.6f,  delta=%+.4f)" % (xB_f, xB_base, xB_f - xB_base))
    if abs(xB_f - xB_base) > 1e-4:
        print("  VERDICT: ComponentMolarFractions SETTER WORKS -- xB changed")
    else:
        print("  VERDICT: no change -- this setter does NOT propagate")
else:
    print("  ComponentMolarFractions not found on this stream type")

# =========================================================
# G: Fall-back: try Phases[0].Compounds setter -> resolve -> check
# =========================================================
print()
print("=== G: Test Phases[0].Compounds setter (set z=0.325, fresh load) ===")
# Reload to clear F's state
fs2 = aut.LoadFlowsheet(CASE_FILE)
col2 = feed2 = dist2 = btms2 = None
for name in list(fs2.SimulationObjects.Keys):
    obj = fs2.SimulationObjects[name]
    pfx = name.split("-")[0].upper() if "-" in name else ""
    try:
        disp = str(obj.GraphicObject.Tag)
    except:
        disp = ""
    dl = disp.lower()
    if pfx == "DC":
        col2 = obj
    elif pfx == "MAT":
        if "dist" in dl:
            dist2 = obj
        elif any(x in dl for x in ("btms", "bott")):
            btms2 = obj
        elif "feed" in dl:
            feed2 = obj

# Baseline solve on fs2
aut.CalculateFlowsheet2(fs2)
xD_g0 = stream_x_nc4(dist2)
xB_g0 = stream_x_nc4(btms2)
print("  Baseline xD=%.6f xB=%.6f" % (xD_g0, xB_g0))

# Set via Phases[0]
ph2 = rget(feed2, "Phases")
c2 = rget(ph2[0], "Compounds")
for k in list(c2.Keys):
    cmpd = c2[k]
    p_mf = cmpd.GetType().GetProperty("MoleFraction")
    if "butan" in str(k).lower():
        p_mf.SetValue(cmpd, float(0.325))
    else:
        p_mf.SetValue(cmpd, float(0.675))

aut.CalculateFlowsheet2(fs2)
xD_g1 = stream_x_nc4(dist2)
xB_g1 = stream_x_nc4(btms2)
print(
    "  After Phases[0] set z=0.325: xD=%.6f xB=%.6f (delta xB=%+.4f)"
    % (xD_g1, xB_g1, xB_g1 - xB_g0)
)
if abs(xB_g1 - xB_g0) > 1e-4:
    print("  VERDICT: Phases[0].Compounds setter WORKS")
else:
    print("  VERDICT: Phases[0].Compounds setter does NOT propagate")

print()
print("Probe complete.")
