"""Validate DWSIM installation and Python bridge.

Checks:
1. DWSIM is installed at the expected location
2. CoolProp is available
3. The DWSIM Python bridge (if applicable) can be imported

Usage:
    python scripts/validate_dwsim_install.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ipis.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


def check_dwsim_path() -> bool:
    """Check whether DWSIM is installed at the expected path."""
    dwsim_path = os.getenv("DWSIM_PATH", "")
    if not dwsim_path:
        logger.warning(
            "dwsim_path_not_set",
            message="DWSIM_PATH environment variable is not set. Set it in .env.",
        )
        return False

    path = Path(dwsim_path)
    if not path.exists():
        logger.error("dwsim_path_invalid", path=dwsim_path)
        return False

    logger.info("dwsim_path_found", path=dwsim_path)
    return True


def check_coolprop() -> bool:
    """Verify CoolProp can compute a basic property."""
    try:
        from CoolProp.CoolProp import PropsSI

        # Water saturation pressure at 100 C ~= 101325 Pa
        p_sat = PropsSI("P", "T", 373.15, "Q", 0, "Water")
        if abs(p_sat - 101325.0) / 101325.0 < 0.01:
            logger.info("coolprop_ok", p_sat_water_100C=p_sat)
            return True
        logger.error("coolprop_value_unexpected", p_sat=p_sat)
        return False
    except ImportError:
        logger.error("coolprop_not_installed")
        return False
    except Exception as e:
        logger.error("coolprop_error", error=str(e))
        return False


def check_gekko() -> bool:
    """Verify GEKKO can solve a trivial optimization."""
    try:
        from gekko import GEKKO

        m = GEKKO(remote=False)
        x = m.Var(value=0, lb=0, ub=10)
        m.Obj((x - 3.0) ** 2)
        m.options.SOLVER = 1
        m.solve(disp=False)

        if abs(x.value[0] - 3.0) < 1e-3:
            logger.info("gekko_ok", solution=x.value[0])
            return True
        logger.error("gekko_wrong_solution", solution=x.value[0])
        return False
    except ImportError:
        logger.error("gekko_not_installed")
        return False
    except Exception as e:
        logger.error("gekko_error", error=str(e))
        return False


def main() -> int:
    """Entry point."""
    configure_logging(json_format=False)

    print("\nValidating IPIS physics layer dependencies...\n")

    checks = {
        "DWSIM path": check_dwsim_path(),
        "CoolProp": check_coolprop(),
        "GEKKO": check_gekko(),
    }

    print("\n" + "=" * 50)
    for name, passed in checks.items():
        status = "OK  " if passed else "FAIL"
        print(f"  [{status}]  {name}")
    print("=" * 50 + "\n")

    if all(checks.values()):
        print("All checks passed.\n")
        return 0
    print("Some checks failed. See logs above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
