"""One-off probe (M1 audit A9): TEP transport lag diagnosed on the FULL regime file, as the
old evaluation did, versus the TRAINING split only, as the fixed evaluation does. SAME in
every regime means the leak changed no reported number. Run from the repo root:

    set PYTHONPATH=src
    python scripts\\_tep_lag_compare.py
"""

from pathlib import Path

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
from ipis.module1_soft_sensor.features.tep_physics_features import diagnose_transport_lag

DATA_DIR = Path("data/raw/tep")

for mode in ("mode1", "mode2", "mode3"):
    df = TEPLoader().load(DATA_DIR / f"tep_{mode}.csv")
    full = diagnose_transport_lag(df)
    train = diagnose_transport_lag(time_ordered_split(df).train)
    verdict = "SAME" if full == train else "DIFFERENT: evidence produced with the full-file lag must be regenerated"
    print(f"{mode}: full-file lag = {full:2d} | train-only lag = {train:2d} | {verdict}")
