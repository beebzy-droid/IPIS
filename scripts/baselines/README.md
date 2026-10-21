# Baseline reproduction check (pre-registration Appendix A)

These scripts check the two label-horizon baselines of claim N1'' (`baselines_pid.py` and
`baselines_spci.py` in `src/ipis/module1_soft_sensor/evaluation/`, imported through the facade
`baselines.py`) against their authors' code. They also
check that the authors' code reproduces one published result of each paper. The record they produce is
`docs/paper/evidence/baseline_reproduction.json`. Phase 1 itself does not run them.

| Script | Checks |
|---|---|
| `cpid_authors.py` | The authors' conformal PID code reproduces Tables 1 and 2 of Angelopoulos, Candes and Tibshirani (NeurIPS 2023), and writes its q sequences |
| `cpid_ipis.py` | `conformal_pid_side(mode="code")` reproduces those q sequences exactly; `mode="phase1"` on Table 2 |
| `cpid_random.py` | `conformal_pid_side(mode="code")` against the authors' function in 600 random side-runs (ahead 1 to 7, scorecasts or none, saturating integrators) and 12 runs of the in-loop Theta scorecaster; the Theta path stops at ahead 2 and 3 |
| `qrf_ipis.py` | `QuantileForest` gives the same quantiles, to the bit, as sklearn-quantile 0.0.29, the forest SPCI uses (40 random cases) |
| `spci_ipis.py` | The authors' SPCI pipeline on the electric data set (Table 3 of Xu and Xie, ICML 2023); `spci_block` reproduces its intervals exactly for strides 1, 2 and 3, and `spci_rolling` at stride 1 |
| `collect.py` | Merges the outputs, compares the tables with the published values, records versions, commits and SHA-256, and checks that every IPIS-side result names the modules it hashes (each result file records `baselines.source_sha256()`) |

## Sources (pinned)

- Conformal PID: https://github.com/aangelopoulos/conformal-time-series, commit
  `b729c3f5ff633bfc43f0f7ca08199b549c2573ac`
- SPCI: https://github.com/hamrel-cxu/SPCI-code, commit `d598dd32099402bc1b6d636f471a155001c0e54e`

## Reference environment

The environment is Linux with Python 3.11 and these packages: numpy 1.23.5, scipy 1.9.3, pandas 1.5.3, scikit-learn 1.1.3, sklearn-quantile 0.0.29,
statsmodels 0.13.5, matplotlib 3.6.3, seaborn 0.12.2, pyyaml and tqdm.
- SPCI-code passes `criterion="mse"`, which scikit-learn removed in 1.2. Its tutorial pins 1.1.2,
  which has no Python 3.11 wheel; 1.1.3 is the bug-fix release that has one.
- Torch is not installed. `torch_shim/` stands in for the container calls on SPCI's
  random-forest path, and for skranger, which SPCI imports but this check does not use.

## Running (bash; about 1 h on two cores)

```
git clone https://github.com/aangelopoulos/conformal-time-series cpid && git -C cpid checkout b729c3f
git clone https://github.com/hamrel-cxu/SPCI-code spci && git -C spci checkout d598dd3
B=$IPIS/scripts/baselines; SRC=$IPIS/src
(cd cpid/tests && python -I $B/cpid_authors.py $OUT/cpid_authors.json \
  && python -I $B/cpid_ipis.py $OUT/cpid_authors.json $SRC $OUT/cpid_ipis.json)
(cd cpid && python -I $B/cpid_random.py $SRC $OUT/cpid_random.json)
python -I $B/qrf_ipis.py $SRC $OUT/qrf_ipis.json
cd spci
for u in "0 1" "0 2" "0 3" "1 1" "2 1"; do set -- $u
  python -I $B/spci_ipis.py $SRC authors $1 $2 $OUT/t$1_s$2.npz
  python -I $B/spci_ipis.py $SRC ipis $OUT/t$1_s$2.npz $OUT/t$1_s$2.json $([ "$u" = "0 1" ] && echo rolling)
done
cd ..
python -I $B/collect.py --cpid-authors $OUT/cpid_authors.json --cpid-ipis $OUT/cpid_ipis.json \
  --cpid-random $OUT/cpid_random.json --qrf $OUT/qrf_ipis.json --spci $OUT/t0_s1.json $OUT/t0_s2.json $OUT/t0_s3.json \
  $OUT/t1_s1.json $OUT/t2_s1.json --cpid-repo cpid --spci-repo spci --ipis-src $SRC \
  --out $IPIS/docs/paper/evidence/baseline_reproduction.json
```

Each SPCI step writes its own file; after an interruption, rerun only the steps whose file is missing.

`cpid_authors.py` deletes the repository's scorecaster cache (`tests/.cache/scorecaster`) before it
runs, so the Theta scorecasts are refitted rather than reused.
