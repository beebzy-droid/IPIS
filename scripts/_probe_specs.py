# Probe the column Specs dict to find setter path and units before writing run_g2_sweep.py
import sys, os

sys.path.insert(0, r"C:\Users\yubyu\AppData\Local\DWSIM")
import clr

clr.AddReference(r"C:\Users\yubyu\AppData\Local\DWSIM\DWSIM.Automation.dll")
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


def rprop_dict(obj):
    d = {}
    for p in obj.GetType().GetProperties(_BF):
        try:
            d[str(p.Name)] = p.GetValue(obj)
        except:
            pass
    return d


aut = Automation3()
fs = aut.LoadFlowsheet(r"C:\Users\yubyu\Projects\IPIS\data\raw\dwsim\debutanizer_3a.dwxmz")

# Find column
col = None
for name in list(fs.SimulationObjects.Keys):
    if name.startswith("DC-"):
        col = fs.SimulationObjects[name]
        break

# Load concrete type
col_asm = str(col.GetType().Assembly.GetName().Name)
clr.AddReference(os.path.join(r"C:\Users\yubyu\AppData\Local\DWSIM", col_asm + ".dll"))

# Probe Specs
specs = rget(col, "Specs")
print("Specs count:", getattr(specs, "Count", "?"))
print()

for key in list(specs.Keys):
    spec = specs[key]
    sd = rprop_dict(spec)
    print("  key = %r" % str(key))
    for k, v in sorted(sd.items()):
        print("    %-32s = %s" % (k, repr(v)[:100]))
    # Check setters
    for attr in ("SValue", "SpecValue", "Value", "SValue2"):
        p = spec.GetType().GetProperty(attr)
        if p:
            print("    --> Property %r  CanRead=%s  CanWrite=%s" % (attr, p.CanRead, p.CanWrite))
    print()

# Also check if any methods named Set* exist on ColumnSpec
print("--- ColumnSpec Set methods ---")
if specs.Count > 0:
    key0 = list(specs.Keys)[0]
    spec0 = specs[key0]
    for m in sorted(spec0.GetType().GetMethods(_BF), key=lambda x: x.Name):
        n = str(m.Name)
        if n.lower().startswith("set") or "value" in n.lower():
            params = ", ".join(str(p.ParameterType.Name) for p in m.GetParameters())
            print("  [M] %s(%s)" % (n, params))
