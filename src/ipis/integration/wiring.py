"""Production wiring: bind the real Module 1/2/3 services to the integration loop.

Four thin adapters map the deployed services onto the orchestrator's Protocols,
and :func:`build_integrated_orchestrator` assembles the fully-wired closed loop.
The real service types are imported only under ``TYPE_CHECKING`` and duck-typed
at runtime, so this module imports (and its mapping logic tests) in the sandbox;
the live end-to-end run happens on the repo where M1/M2/M3 are importable.

Confirmed interfaces (raw-probed against the repo):
  * M1 ``SoftSensorService.predict(features, sample_id)`` -> dict with
    ``y_pred`` (corrected estimate), ``lower``/``upper`` (ACI interval),
    ``drift_flag``; ``label(sample_id, y_true)`` folds the delayed label.
  * M1 driving inputs are the *normalized* tray-6 temperature and column
    pressure (``physics_bridge.bridge``: T in 100-112 C, P in 4.5-5.5 bar).
  * M2 ``PdMService.observe(equipment_id, features)`` -> dict with
    ``health_score``, ``flag``, and ``rul_hours`` (present only post-FPT).
  * M3 ``LnXbSurface.coef`` is the 6-tuple the §6 NLP optimises; ``EconomicsAnchor``
    supplies the three prices (mapped via :func:`econ_params_from_anchor`).

M1's feature contract is the three physics features
``[bubble_point_c4, rel_volatility, stripping_factor]`` (optionally + raw u5) at a
transport lag, built by ``features.physics_features.add_physics_features`` --
confirmed against the repo. :class:`M1FeatureTransform` reproduces it. Set its
``transport_lag``/``include_raw_u5`` and the normalization ranges to match your
deployed model's ``feature_names`` (read them off the loaded ModelBundle).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from ipis.integration.coverage import HealthRTOAdapter
from ipis.integration.health_rto import EconomicParams
from ipis.integration.orchestrator import (
    ClosedLoopOrchestrator,
    PdMReading,
    SoftSensorReading,
)
from ipis.integration.plant import (
    DebutanizerPlant,
    FeatureSynthesizer,
    FeedSpec,
    PlantOutput,
    PropertyEvaluator,
    PumpDegradation,
    TrayTempSurface,
    XbTruth,
)
from ipis.integration.psi import PsiConfig

if TYPE_CHECKING:  # real services -- never imported at runtime
    from ipis.module1_soft_sensor.serving.service import SoftSensorService
    from ipis.module2_pdm.serving.service import PdMService
    from ipis.module3_rto.economics import EconomicsAnchor
    from ipis.module3_rto.rto_nlp import LnXbSurface

# M1 normalization ranges (mirror physics_bridge.bridge; confirmed on the repo).
TRAY6_T_MIN_C: float = 100.0
TRAY6_T_MAX_C: float = 112.0
COL_P_MIN_BAR: float = 4.5
COL_P_MAX_BAR: float = 5.5


def _clip01(v: float) -> float:
    return min(1.0, max(0.0, v))


class M1FeatureTransform:
    """Plant output -> Module 1's physics-anchored feature vector (Path B).

    Production M1 consumes the three physics features
    ``[bubble_point_c4, rel_volatility, stripping_factor]`` (optionally + raw
    ``u5``) at a transport lag, built by the real
    ``features.physics_features.add_physics_features`` from the normalized
    benchmark inputs u5 (tray-6 T), u2 (column pressure), u3 (reflux flow). This
    transform reproduces that: it normalizes the plant's tray-6 temperature and
    reflux flow R*D, buffers them, and emits the physics features at
    ``transport_lag`` using the repo's own computation.

    Set the ranges, ``transport_lag`` and ``include_raw_u5`` to match your
    deployed model's ``feature_names`` (read them off the loaded ModelBundle).
    u3's scale is absorbed by the model coefficient, so the reflux-flow range
    need only be representative. Pressure is held nominal (the P-GP plant runs at
    fixed pressure); source it from the plant output if that changes.
    """

    def __init__(
        self,
        *,
        t_min_c: float = TRAY6_T_MIN_C,
        t_max_c: float = TRAY6_T_MAX_C,
        p_min_bar: float = COL_P_MIN_BAR,
        p_max_bar: float = COL_P_MAX_BAR,
        col_pressure_bar: float = 5.0,
        reflux_flow_min: float = 26.0,
        reflux_flow_max: float = 111.0,
        transport_lag: int = 15,
        include_raw_u5: bool = True,
    ) -> None:
        self.t_min_c, self.t_max_c = t_min_c, t_max_c
        self.p_min_bar, self.p_max_bar = p_min_bar, p_max_bar
        self.col_pressure_bar = col_pressure_bar
        self.reflux_flow_min, self.reflux_flow_max = reflux_flow_min, reflux_flow_max
        self.transport_lag = transport_lag
        self.include_raw_u5 = include_raw_u5
        self._buf: deque[tuple[float, float, float]] = deque(maxlen=transport_lag + 1)

    def __call__(self, plant_out: PlantOutput) -> npt.NDArray[np.float64]:
        import pandas as pd

        from ipis.module1_soft_sensor.features.physics_features import (
            PHYSICS_FEATURE_COLS,
            add_physics_features,
        )

        op = plant_out.operating_point
        u5 = _clip01((plant_out.sensor_temp_c - self.t_min_c) / (self.t_max_c - self.t_min_c))
        u2 = _clip01((self.col_pressure_bar - self.p_min_bar) / (self.p_max_bar - self.p_min_bar))
        flow = op.R * op.D
        u3 = _clip01((flow - self.reflux_flow_min) / (self.reflux_flow_max - self.reflux_flow_min))
        self._buf.append((u5, u2, u3))
        # lagged sample once the buffer fills; current sample during warm-up
        u5_l, u2_l, u3_l = self._buf[0] if len(self._buf) > self.transport_lag else self._buf[-1]
        df = pd.DataFrame({"u5": [u5_l], "u2": [u2_l], "u3": [u3_l]})
        feat = add_physics_features(df)
        cols = list(PHYSICS_FEATURE_COLS) + (["u5"] if self.include_raw_u5 else [])
        return feat[cols].to_numpy(dtype=float)[0]


class M1Adapter:
    """Wrap ``SoftSensorService`` as the orchestrator's ``SoftSensor``."""

    def __init__(self, service: SoftSensorService) -> None:
        self._svc = service

    def predict(self, features: npt.NDArray[np.float64], sample_id: str) -> SoftSensorReading:
        r = self._svc.predict(features, sample_id)
        if isinstance(r, list):  # batch contract returns a list; we send one row
            r = r[0]
        return SoftSensorReading(
            estimate=float(r["y_pred"]),
            half_width=(float(r["upper"]) - float(r["lower"])) / 2.0,
            drift=bool(r["drift_flag"]),
        )

    def label(self, sample_id: str, y_true: float) -> None:
        self._svc.label(sample_id, float(y_true))


class M2Adapter:
    """Wrap ``PdMService`` as the orchestrator's ``PdM``."""

    def __init__(self, service: PdMService) -> None:
        self._svc = service

    def observe(self, equipment_id: str, features: npt.NDArray[np.float64]) -> PdMReading:
        r = self._svc.observe(equipment_id, features)
        rul = r.get("rul_hours")
        return PdMReading(
            health_score=float(r["health_score"]),
            flag=str(r["flag"]),
            rul_hours=None if rul is None else float(rul),
        )


def econ_params_from_anchor(anchor: EconomicsAnchor) -> EconomicParams:
    """Map an ``EconomicsAnchor`` (three prices) to ``EconomicParams`` for the §6
    NLP, pulling the latent-heat and molar-mass constants from Module 3. Repo-only
    (imports Module 3); build it once and pass the result to the factory."""
    from ipis.module3_rto.column_model import DHVAP_C6_KJ_PER_KMOL
    from ipis.module3_rto.economics import M_C4_KG_PER_KMOL, M_C6_KG_PER_KMOL

    return EconomicParams(
        c4_value_usd_per_kg=anchor.c4_value_usd_per_kg,
        gasoline_value_usd_per_kg=anchor.gasoline_value_usd_per_kg,
        energy_cost_usd_per_gj=anchor.energy_cost_usd_per_gj,
        dhvap_kj_per_kmol=DHVAP_C6_KJ_PER_KMOL,
        m_lk_kg_per_kmol=M_C4_KG_PER_KMOL,
        m_hk_kg_per_kmol=M_C6_KG_PER_KMOL,
    )


def build_integrated_orchestrator(
    *,
    soft_sensor: SoftSensorService,
    pdm: PdMService,
    ln_xb_surface: LnXbSurface,
    econ: EconomicParams,
    xb_truth: XbTruth,
    tray_temp: TrayTempSurface,
    properties: PropertyEvaluator,
    degradation: PumpDegradation,
    feature_synthesizer: FeatureSynthesizer,
    psi_cfg: PsiConfig,
    feed: FeedSpec,
    equipment_id: str = "reflux_pump_P101",
    quality_key: str = "C4_bottom",
    spec_xb_c4: float = 0.02,
    eps: float = 0.05,
    seed_setpoints: tuple[float, float] = (1.9, 35.0),
    label_delay: int = 0,
    col_pressure_bar: float = 5.0,
    transport_lag: int = 15,
    include_raw_u5: bool = True,
    alpha1: float = 0.10,
    alpha2: float = 0.10,
    r_bounds: tuple[float, float] = (0.8, 3.0),
    d_bounds: tuple[float, float] = (33.0, 37.0),
) -> ClosedLoopOrchestrator:
    """Assemble the closed loop over the real M1/M2/M3 services.

    ``econ`` is built once via :func:`econ_params_from_anchor`; ``xb_truth`` /
    ``tray_temp`` are the GP twin surfaces (the plant/truth), and
    ``ln_xb_surface`` is the fitted quadratic the RTO optimises against.
    """
    plant = DebutanizerPlant(
        xb_truth=xb_truth,
        tray_temp=tray_temp,
        properties=properties,
        feed=feed,
        degradation=degradation,
        synthesizer=feature_synthesizer,
        feed_z=feed.z_lk,
    )
    rto = HealthRTOAdapter(
        surface_coef=ln_xb_surface.coef,
        econ=econ,
        psi_cfg=psi_cfg,
        eps=eps,
        spec_xb_c4=spec_xb_c4,
        r_bounds=r_bounds,
        d_bounds=d_bounds,
        feed_kmol_h=feed.F,
    )
    return ClosedLoopOrchestrator(
        plant=plant,
        feature_fn=M1FeatureTransform(
            col_pressure_bar=col_pressure_bar,
            transport_lag=transport_lag,
            include_raw_u5=include_raw_u5,
        ),
        soft_sensor=M1Adapter(soft_sensor),
        rto_solver=rto,
        pdm=M2Adapter(pdm),
        equipment_id=equipment_id,
        quality_key=quality_key,
        seed_setpoints=seed_setpoints,
        label_delay=label_delay,
        psi_config=psi_cfg,
        eps=eps,
        alpha1=alpha1,
        alpha2=alpha2,
    )
