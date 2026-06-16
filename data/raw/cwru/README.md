# CWRU Bearing Data Center — acquisition note

**Role:** Module 2 **secondary** dataset (clean seeded-fault diagnosis — validates the
physics-anchored fault-frequency layer that FEMTO's naturally-mixed signatures cannot).
See `docs/module2/spec.md` (D2) and ADR-015.

**This directory is gitignored** (`data/raw/*`). Only this README is tracked.

## Source

- Download page: https://engineering.case.edu/bearingdatacenter/download-data-file
- Benchmark/usability paper (Tier-1, in project library): Smith & Randall (2015), *Rolling
  element bearing diagnostics using the Case Western Reserve University data: A benchmark
  study*, MSSP 64–65.

## What to download (12 kHz Drive End + Normal baseline)

The standard benchmark set: Normal baseline plus the three single-component faults
(Inner Race, Ball, Outer Race centred @6 o'clock) at three fault diameters
(0.007″ / 0.014″ / 0.021″), each at motor loads 0/1/2/3 HP (≈1797/1772/1750/1730 rpm).
40 `.mat` files total.

| Category | 0.007″ (0/1/2/3 HP) | 0.014″ | 0.021″ |
|---|---|---|---|
| Normal baseline | 97, 98, 99, 100 | — | — |
| 12k Drive End — Inner Race | 105–108 | 169–172 | 209–212 |
| 12k Drive End — Ball | 118–121 | 185–188 | 222–225 |
| 12k Drive End — Outer Race @6 | 130–133 | 197–200 | 234–237 |

Place all `.mat` files flat in this directory (`data/raw/cwru/`).

## Verification discipline (do not skip)

The file numbers above are the widely-used convention, **not yet pinned**. Smith & Randall
document that several CWRU records are corrupted or mislabelled and should be excluded. The
**verified, usable manifest is produced at Phase 2A by reading Smith & Randall's table** and
dropping every file they flag — no CWRU file is treated as ground truth before that check
(verify-before-load-bearing). If any file number 404s on the site, skip it and note which.

## Format (for the 2A loader)

CWRU files are MATLAB `.mat` containing drive-end (`DE`), fan-end (`FE`), and sometimes base
(`BA`) acceleration vectors plus motor RPM, sampled at 12 kHz (DE fault set).

**Bearing geometry provenance (for BPFO/BPFI/BSF/FTF).** DE bearing = SKF 6205-2RS JEM.
The SKF public datasheet (`skf.com/.../productid-6205`) confirms boundary dims
(25 x 52 x 15 mm) + load ratings, but does **not** publish ball count, ball diameter, or
pitch diameter. The fault-frequency internals (N = 9 balls, ball dia d, pitch dia D,
contact angle phi ~ 0deg) are taken from CWRU's published bearing data cross-checked against
Smith & Randall (2015), and **verified by reproducing CWRU's published defect-frequency
multipliers** (BPFO/BPFI/FTF/BSF as multiples of shaft speed) from the geometry — if computed
multipliers match CWRU's published values, the geometry is confirmed (self-consistency check,
done at 2A). The SKF datasheet is retained as a supporting identity/boundary-geometry source,
not the source of the fault-frequency internals. All pinned against Randall & Antoni (2011).
