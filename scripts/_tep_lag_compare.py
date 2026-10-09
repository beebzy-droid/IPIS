"""One-off probe (M1 audit A9): TEP transport lag diagnosed on the FULL regime file, as the
old evaluation did, versus the TRAINING split only, as the fixed evaluation does. SAME in
every regime means the leak changed no reported number. Run from the repo root:

    set PYTHONPATH=src
    python scripts\\_tep_lag_compare.py --json

``--json`` writes docs/paper/evidence/tep_lag_compare.json, the committed evidence for R4.5.
"""

import argparse
from pathlib import Path

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
from ipis.module1_soft_sensor.features.tep_physics_features import diagnose_transport_lag

DATA_DIR = Path("data/raw/tep")

ap = argparse.ArgumentParser(description="TEP lag: full file vs training split")
ap.add_argument("--json", action="store_true", help="dump evidence to docs/paper/evidence/")
args = ap.parse_args()

modes = {}
for mode in ("mode1", "mode2", "mode3"):
    df = TEPLoader().load(DATA_DIR / f"tep_{mode}.csv")
    full = diagnose_transport_lag(df)
    train = diagnose_transport_lag(time_ordered_split(df).train)
    verdict = (
        "SAME"
        if full == train
        else "DIFFERENT: evidence produced with the full-file lag must be regenerated"
    )
    modes[mode] = {"full_file_lag": full, "train_only_lag": train, "same": full == train}
    print(f"{mode}: full-file lag = {full:2d} | train-only lag = {train:2d} | {verdict}")

if args.json:
    from ipis.shared.evidence import dump_evidence

    payload = {"driver": "XMEAS_3", "max_lag": 40, "modes": modes}
    print("evidence ->", dump_evidence("tep_lag_compare", payload))
