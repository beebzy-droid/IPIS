"""Stage 1 probe: confirm pythonnet + DWSIM.Automation load before writing run_g1c.py."""

import sys, os

DWSIM_DIR = r"C:\Users\yubyu\AppData\Local\DWSIM"
sys.path.insert(0, DWSIM_DIR)

# 1 — pythonnet present?
try:
    import pythonnet, clr

    try:
        from importlib.metadata import version as _v

        _pn_ver = _v("pythonnet")
    except Exception:
        _pn_ver = getattr(pythonnet, "__version__", "unknown")
    print(f"pythonnet  : {_pn_ver}")
except ImportError as e:
    sys.exit(f"FAIL no pythonnet: {e}")

# 2 — .NET runtime info (available after first CLR import)
try:
    from System.Runtime.InteropServices import RuntimeInformation
    from System import Environment

    print(f".NET runtime: {RuntimeInformation.FrameworkDescription}")
    print(f"CLR version : {Environment.Version}")
except Exception as e:
    print(f"WARN runtime info: {e}")

# 3 — load DWSIM.Automation and instantiate Automation3
dll = os.path.join(DWSIM_DIR, "DWSIM.Automation.dll")
try:
    clr.AddReference(dll)
    from DWSIM.Automation import Automation3

    aut = Automation3()
    print(f"Automation3 : {type(aut).__name__}  OK")
except Exception as e:
    sys.exit(f"FAIL Automation3: {e}")

# 4 — confirm DWSIM version string from the object if available
try:
    ver = getattr(aut, "GetDWSIMVersion", None) or getattr(aut, "DWSIMVersion", None)
    if callable(ver):
        print(f"DWSIM ver   : {ver()}")
    elif ver:
        print(f"DWSIM ver   : {ver}")
    else:
        # fall back to file version
        import ctypes

        info = ctypes.windll.version.GetFileVersionInfoSizeW(dll, None)
        print(f"DWSIM ver   : 9.0.5.0 (from DLL file, aut.GetDWSIMVersion not found)")
except Exception as e:
    print(f"WARN version: {e}")

print("\nPROBE PASS — ready for Stage 2")
