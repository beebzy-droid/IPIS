"""Paper figure emitters (Phase 1F.2).

Emitters never recompute science: each reads a small evidence JSON produced by the
corresponding evaluation script's ``--json`` flag and renders deterministically.
Evidence lives in docs/paper/evidence/, figures in docs/paper/figures/ (PNG + PDF).
"""
