"""Campaign recorder for IPIS Module 5.

An append-only, structured log of a dynamic-loop campaign. It is the shared substrate
for (a) the horizon-coverage / ACI analysis (increment 2) and (b) the interactive 2D
operations view (visualization track V1): every signal needed to *replay* the operation
is captured per sample, so the same log feeds both the analysis and the viewer.

The recorder is decoupled from the intelligence layer: the plant-output fields are
always present; the M1 / M2 / certificate fields are optional and filled only when the
loop supplies them (``None`` in plant-only runs). ``to_arrays`` returns numpy columns
for analysis and plotting; ``to_records`` returns JSON-serializable rows for the viewer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from ipis.integration.dynamic_plant import DynamicPlantOutput

# Optional intelligence-layer fields the loop may attach to a sample.
_INTEL_FIELDS = frozenset(
    {
        "quality_estimate",
        "quality_half_width",
        "rul_lower_hours",
        "true_rul_hours",
        "health_flag",
        "aci_quantile",
        "s_event",
        "coverage_floor",
    }
)


@dataclass(frozen=True)
class CampaignSample:
    """One recorded sample: plant truth/signals plus optional intelligence outputs."""

    cycle: int
    time_h: float
    applied_reflux: float
    applied_distillate: float
    realized_reflux: float
    realized_distillate: float
    sensor_temp_c: float
    xb_true: float
    xb_measured: float
    severity: float
    gilliland_coord: float
    reflux_flow: float
    # --- intelligence layer (optional; populated by the loop) ---
    quality_estimate: float | None = None
    quality_half_width: float | None = None
    rul_lower_hours: float | None = None
    true_rul_hours: float | None = None
    health_flag: str | None = None
    aci_quantile: float | None = None
    s_event: bool | None = None  # joint safety event S_k satisfied this cycle
    coverage_floor: float | None = None  # certified floor 1 - (a1 + a2) - eps


@dataclass
class CampaignRecorder:
    """Append-only campaign log; the V1 viewer and the ACI analysis both read it."""

    samples: list[CampaignSample] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.samples)

    @property
    def latest(self) -> CampaignSample | None:
        return self.samples[-1] if self.samples else None

    def record(
        self, out: DynamicPlantOutput, *, cycle: int | None = None, **intel: Any
    ) -> CampaignSample:
        """Append one sample from a plant output, with optional intelligence fields."""
        unknown = set(intel) - _INTEL_FIELDS
        if unknown:
            raise TypeError(f"unknown intelligence field(s): {sorted(unknown)}")
        op = out.operating_point
        sample = CampaignSample(
            cycle=cycle if cycle is not None else len(self.samples),
            time_h=out.time_h,
            applied_reflux=out.applied_reflux,
            applied_distillate=out.applied_distillate,
            realized_reflux=out.realized_reflux,
            realized_distillate=out.realized_distillate,
            sensor_temp_c=out.sensor_temp_c,
            xb_true=out.xb_true,
            xb_measured=out.xb_measured,
            severity=out.severity,
            gilliland_coord=op.gilliland_coord,
            reflux_flow=op.reflux_flow,
            **intel,
        )
        self.samples.append(sample)
        return sample

    def to_records(self) -> list[dict[str, Any]]:
        """JSON-serializable rows for the interactive 2D operations viewer (V1)."""
        return [asdict(s) for s in self.samples]

    def to_arrays(self) -> dict[str, np.ndarray]:
        """Columnar arrays for analysis/plotting. ``None`` -> ``nan``; flags stay object."""
        if not self.samples:
            return {}
        cols: dict[str, np.ndarray] = {}
        for name in CampaignSample.__dataclass_fields__:
            vals = [getattr(s, name) for s in self.samples]
            if name == "health_flag":
                cols[name] = np.array(vals, dtype=object)
            else:
                cols[name] = np.array(
                    [np.nan if v is None else float(v) for v in vals], dtype=float
                )
        return cols
