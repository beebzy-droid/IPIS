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

The one item to confirm before the live run: that the deployed ``point_predict``
(the 1D.2c-loaded model) consumes ``[t_norm, p_norm]``. If it instead expects a
richer feature vector, replace :class:`M1FeatureTransform` with that builder --
it is the only piece inferred rather than read.
"""

from __future__ import annotations

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
    """Plant tray-6 temperature (+ a nominal column pressure) -> M1's normalized
    driving inputs ``[t_norm, p_norm]``.

    The P-GP plant runs at fixed pressure, so ``col_pressure_bar`` is held at the
    nominal value; if the plant ever varies pressure, source it from the plant
    output instead. ASSUMES the deployed ``point_predict`` consumes
    ``[t_norm, p_norm]`` -- the one inferred contract (see module docstring).
    """

    def __init__(self, col_pressure_bar: float = 5.0) -> None:
        self.col_pressure_bar = col_pressure_bar

    def __call__(self, plant_out: PlantOutput) -> npt.NDArray[np.float64]:
        t_norm = _clip01(
            (plant_out.sensor_temp_c - TRAY6_T_MIN_C) / (TRAY6_T_MAX_C - TRAY6_T_MIN_C)
        )
        p_norm = _clip01((self.col_pressure_bar - COL_P_MIN_BAR) / (COL_P_MAX_BAR - COL_P_MIN_BAR))
        return np.array([t_norm, p_norm], dtype=float)


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
        feature_fn=M1FeatureTransform(col_pressure_bar),
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
