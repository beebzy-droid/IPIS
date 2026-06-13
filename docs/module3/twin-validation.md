# 3A twin validation

Source: `/tmp/twin_15drop.csv` (15 runs). Checks defined in `scripts/validate_twin.py`; envelope from the Module 1 physics bridge.

| check | result | detail |
|---|---|---|
| V1 envelope (feasible region) | PASS | T range [94.0, 119.8] C (env (100.0, 112.0)); 5/15 grid pts in-env; feasible&in-env=3; feasible HOT exits (>112.0 C, 3B flag)=4 |
| V2 mass balance | PASS | worst closure 0.0013% (tol 0.5%); 0 rows over |
| V3 monotonicity | PASS | xB(R) non-increasing, Q(R) increasing at every D |

**Overall: PASS**
