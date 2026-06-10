"""Serving-latency benchmark (Phase 1F.2, claim C11).

Measures wall-clock client-observed latency against a RUNNING service:

    set PYTHONPATH=src
    uvicorn ipis.module1_soft_sensor.serving.main:app --port 8000   (shell 1)
    python scripts\\bench_latency.py --n 10000 --json               (shell 2)

Reports p50/p90/p99 for single-row /predict, batch /predict, and the /label
round-trip. Client-observed = includes HTTP + serialization, which is the honest
deployment number (the model compute itself is microseconds).
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx
import numpy as np


def _percentiles(ms: list[float]) -> dict:
    a = np.asarray(ms, float)
    return {
        "n": int(a.size),
        "p50_ms": float(np.percentile(a, 50)),
        "p90_ms": float(np.percentile(a, 90)),
        "p99_ms": float(np.percentile(a, 99)),
        "mean_ms": float(a.mean()),
    }


def bench(base_url: str, n: int, batch: int, warmup: int = 200) -> dict:
    rng = np.random.default_rng(0)
    out: dict = {}
    with httpx.Client(base_url=base_url, timeout=10.0) as c:
        r = c.get("/health")
        r.raise_for_status()

        def predict_once(rows: int, sid_prefix: str, i: int) -> float:
            payload = {
                "instances": rng.normal(0, 1, (rows, 3)).tolist(),
                "sample_ids": [f"{sid_prefix}{i}_{k}" for k in range(rows)],
            }
            t0 = time.perf_counter()
            c.post("/predict", json=payload).raise_for_status()
            return (time.perf_counter() - t0) * 1e3

        for i in range(warmup):
            predict_once(1, "w", i)

        out["predict_single"] = _percentiles([predict_once(1, "s", i) for i in range(n)])
        n_batch = max(1, n // batch)
        out["predict_batch"] = {
            "batch_size": batch,
            **_percentiles([predict_once(batch, "b", i) for i in range(n_batch)]),
        }

        # /label round-trip against freshly predicted ids (within buffer capacity)
        lab_ms = []
        for i in range(min(n, 2000)):
            sid = f"L{i}"
            c.post("/predict", json={"instances": [[1.0, 0.0, 0.0]], "sample_ids": [sid]})
            t0 = time.perf_counter()
            c.post("/label", json={"sample_id": sid, "y_true": 3.0}).raise_for_status()
            lab_ms.append((time.perf_counter() - t0) * 1e3)
        out["label"] = _percentiles(lab_ms)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Client-observed serving latency.")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--json", action="store_true", help="dump to docs/paper/evidence/")
    args = ap.parse_args()

    res = bench(args.base_url, args.n, args.batch)
    for name, d in res.items():
        extra = f" (batch={d['batch_size']})" if "batch_size" in d else ""
        print(
            f"{name:<16}{extra:<12} p50 {d['p50_ms']:7.2f} ms | p90 {d['p90_ms']:7.2f} | "
            f"p99 {d['p99_ms']:7.2f} | mean {d['mean_ms']:7.2f}  (n={d['n']})"
        )
    if args.json:
        from ipis.shared.evidence import dump_evidence

        print("evidence ->", dump_evidence("serving_latency", res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
