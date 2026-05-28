"""IPIS Module 1 — Soft Sensor.

A hybrid soft sensor framework with cross-process transfer and drift-aware
deployment. Validated on Debutanizer, Tennessee Eastman, and SECOM.

Architecture: Path B residual hybrid (first-principles baseline +
PINN-regularized residual learner with standard ML fallback).

See: docs/module1/spec.md
"""

__module_id__ = "m1"
__module_name__ = "soft_sensor"
