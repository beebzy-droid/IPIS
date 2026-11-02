"""N1 Phase 1 runner (pre-registration ``docs/module1/PHASE1_PREREGISTRATION.md``, Section 9, step 6).

It implements Sections 5 to 7 and Appendix A of the frozen protocol (tag ``n1-phase1-freeze``) on
the two process datasets: the debutanizer (Fortuna et al. 2007) and the 15 Tennessee Eastman runs
of Section 5.2. ``docs/module1/PHASE1_RUNNER.md`` maps every item of the protocol to the code, and
states each reading where the protocol is silent.

The run has two stages, so that every prediction and every tuned setting is written down before
an evaluation row is read (Section 3F):
- stage A reads the training and calibration rows only. It fits the point models and the
  compensation forecasters, computes the predicted width ratios (P3) and F8's gate, and tunes
  every step size and every baseline. Its evidence is committed before stage B runs;
- stage B reads the evaluation rows, checks that everything stage A computed is reproduced from
  the same files and code, and runs every cell with stage A's settings. The verdicts are then
  computed from the two records.

The library modules of the frozen protocol (``evaluation/delayed_aci.py``,
``delay_compensation.py``, ``inference.py``, ``baselines*.py``) are imported unchanged: their
SHA-256 are recorded in the design-stage evidence, so this package adds code beside them and never
edits them.

Modules:
- ``data``: the datasets, the TEP arms T1 to T3, the segments and the input checks;
- ``models``: the point models (OLS for the debutanizer, ridge with the one-SE rule for TEP, and
  gradient boosting for the estimator-class check);
- ``loops``: the calibration loops of Section 5.3 and their replay tuning;
- ``metrics``: the metrics of Section 5.4 and the persistence measures;
- ``rules``: the decision rules F1 to F8 of Section 6, with the inference of Section 7;
- ``record``: the evidence records, array fingerprints and provenance;
- ``stages``: stage A and stage B;
- ``verdicts``: the F-verdicts from the stage A and stage B records.
"""
