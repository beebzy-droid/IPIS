"""Live monitoring dashboard for the soft-sensor serving API (Phase 1D.3).

A thin Streamlit client over the FastAPI service (1D.2): it drives a sample stream,
calls ``/predict``, posts each sample's label after a configurable delay (mirroring the
real delayed-label flow), and plots the online-validity view — the conformal band with
labels overlaid, the rolling-coverage curve against the target, the drift flag, and
b_t / alpha_t adapting.

Run (two processes; cmd, env ipis, repo root):
    set PYTHONPATH=src
    uvicorn ipis.module1_soft_sensor.serving.main:app --port 8000
    streamlit run src\\ipis\\module1_soft_sensor\\serving\\dashboard.py

Stream sources:
  - Synthetic (default): 3-feature rows matching the committed fixture model; a drift
    toggle inflates the residual scale so you can watch the ACI band widen while
    coverage holds near the target.
  - TEP replay (optional): replay a tep_mode{n} CSV through the physics features; needs
    the gitignored data AND a TEP bundle served (feature dimension must match).

Design note: the pure pieces (``make_synthetic_sample``, ``ServiceClient``) live at module
top and are unit-tested; ``streamlit`` (and ``altair``/``pandas``) are imported lazily
inside ``render`` so this module imports cleanly without Streamlit installed (e.g. in CI).
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import numpy as np
from numpy.typing import NDArray

# Coefficients of the committed synthetic fixture (register_model.py build_fixture_bundle)
# so the streamed residuals match the model's calibration scale -> ~nominal coverage.
DEFAULT_COEF: tuple[float, ...] = (3.0, -1.5, 0.75)
DEFAULT_BASE_URL = "http://localhost:8000"


# --------------------------------------------------------------------------- #
# Pure stream generator (testable)                                            #
# --------------------------------------------------------------------------- #
def make_synthetic_sample(
    rng: np.random.Generator,
    *,
    coef: tuple[float, ...] = DEFAULT_COEF,
    noise_scale: float = 1.0,
    mean_shift: float = 0.0,
) -> tuple[NDArray[np.float64], float]:
    """One (features, y_true) draw. ``noise_scale`` inflates the residual (scale drift);
    ``mean_shift`` offsets the truth (the bias-update should absorb a mean step)."""
    c = np.asarray(coef, dtype=float)
    x = rng.normal(0.0, 1.0, size=c.shape[0])
    y = float(x @ c + mean_shift + rng.normal(0.0, noise_scale))
    return x, y


# --------------------------------------------------------------------------- #
# HTTP client to the serving API (testable via httpx ASGITransport)           #
# --------------------------------------------------------------------------- #
class ServiceClient:
    """Thin client for the FastAPI soft-sensor service.

    ``client`` is injectable: production passes nothing (a real ``httpx.Client`` to
    ``base_url``); tests pass an ``httpx.Client`` bound to an ASGITransport over the app,
    giving a real client<->API round-trip with no network.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def health(self) -> bool:
        try:
            r = self._client.get("/health")
            return r.status_code == 200 and r.json().get("status") == "ok"
        except httpx.HTTPError:
            return False

    def predict(
        self, instances: list[list[float]], sample_ids: list[str] | None = None
    ) -> list[dict]:
        payload: dict = {"instances": instances}
        if sample_ids is not None:
            payload["sample_ids"] = sample_ids
        r = self._client.post("/predict", json=payload)
        r.raise_for_status()
        return r.json()["predictions"]

    def label(self, sample_id: str, y_true: float) -> dict:
        r = self._client.post("/label", json={"sample_id": sample_id, "y_true": y_true})
        r.raise_for_status()
        return r.json()

    def metrics(self) -> dict:
        r = self._client.get("/metrics")
        r.raise_for_status()
        return r.json()

    def state(self) -> dict:
        r = self._client.get("/state")
        r.raise_for_status()
        return r.json()


# --------------------------------------------------------------------------- #
# Optional TEP replay stream (lazy repo imports; needs data + a TEP bundle)   #
# --------------------------------------------------------------------------- #
def tep_feature_stream(
    csv_path: str, transport_lag: int = -1
) -> Iterator[tuple[list[float], float]]:
    """Yield (feature_row, y_true) from a TEP regime CSV via the physics features."""
    from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
    from ipis.module1_soft_sensor.features.tep_physics_features import (
        diagnose_transport_lag,
        make_tep_physics_features,
    )

    df = TEPLoader().load(csv_path)
    lag = diagnose_transport_lag(df) if transport_lag < 0 else transport_lag
    x, y = make_tep_physics_features(df, transport_lag=lag)
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float).ravel()
    for i in range(x_arr.shape[0]):
        yield x_arr[i].tolist(), float(y_arr[i])


# --------------------------------------------------------------------------- #
# Streamlit UI (lazy imports; not unit-tested — validated by running)         #
# --------------------------------------------------------------------------- #
def render() -> None:  # pragma: no cover - exercised by `streamlit run`, not pytest
    import altair as alt
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="IPIS soft sensor", layout="wide")
    st.title("IPIS soft sensor — live monitor")

    ss = st.session_state
    ss.setdefault("records", [])  # one dict per predicted sample
    ss.setdefault("pending", [])  # [(sample_id, y_true, due_step)]
    ss.setdefault("step", 0)
    ss.setdefault("gid", 0)
    ss.setdefault("rng_state", np.random.default_rng(0).bit_generator.state)

    with st.sidebar:
        st.header("Connection")
        base_url = st.text_input("Service URL", DEFAULT_BASE_URL)
        client = ServiceClient(base_url=base_url)
        ok = client.health()
        # NB: must be a statement, not a bare ternary expression — Streamlit's
        # "magic" echoes bare expression values (a DeltaGenerator repr) into the app.
        if ok:
            st.success("service: healthy")
        else:
            st.error("service: unreachable")

        st.header("Stream")
        source = st.radio("Source", ["Synthetic", "TEP replay"], horizontal=True)
        rate = st.slider("Samples per advance", 1, 50, 10)
        delay = st.slider("Label delay (samples)", 0, 50, 5)
        inject = st.toggle("Inject drift", value=False)
        drift_scale = st.slider("Drift residual scale", 1.0, 6.0, 3.0, disabled=not inject)
        tep_csv = (
            st.text_input("TEP CSV path", "data/raw/tep/tep_mode1.csv")
            if source == "TEP replay"
            else None
        )

        c1, c2 = st.columns(2)
        advance = c1.button("Advance", type="primary", disabled=not ok)
        if c2.button("Reset"):
            for k in ("records", "pending", "step", "gid"):
                ss.pop(k, None)
            ss["rng_state"] = np.random.default_rng(0).bit_generator.state
            st.rerun()

    # --- advance the stream: predict new samples, post any due labels ---
    if advance and ok:
        rng = np.random.default_rng()
        rng.bit_generator.state = ss["rng_state"]
        tep_iter = tep_feature_stream(tep_csv) if source == "TEP replay" else None
        for _ in range(rate):
            try:
                if source == "TEP replay":
                    feats, y_true = next(tep_iter)  # type: ignore[arg-type]
                else:
                    x, y_true = make_synthetic_sample(
                        rng, noise_scale=(drift_scale if inject else 1.0)
                    )
                    feats = x.tolist()
            except StopIteration:
                st.warning("TEP replay exhausted; Reset to restart.")
                break
            sid = f"s{ss['gid']}"
            ss["gid"] += 1
            try:
                row = client.predict([feats], [sid])[0]
            except httpx.HTTPError as exc:
                st.error(f"/predict failed: {exc}")
                break
            ss["records"].append(
                {
                    "t": ss["step"],
                    "sample_id": sid,
                    "y_pred": row["y_pred"],
                    "lower": row["lower"],
                    "upper": row["upper"],
                    "y_true": None,
                    "covered": None,
                }
            )
            ss["pending"].append((sid, y_true, ss["step"] + delay))
            ss["step"] += 1

        # post labels whose delay has elapsed; carry the rest forward
        rec_by_id = {r["sample_id"]: r for r in ss["records"]}
        still: list[tuple[str, float, int]] = []
        for sid, y_true, due in ss["pending"]:
            if due <= ss["step"]:
                try:
                    res = client.label(sid, y_true)
                    r = rec_by_id.get(sid)
                    if r is not None:
                        r["y_true"] = y_true
                        r["covered"] = res["covered"]
                except httpx.HTTPError:
                    pass  # sample may have been evicted from the server buffer; skip
            else:
                still.append((sid, y_true, due))
        ss["pending"] = still
        ss["rng_state"] = rng.bit_generator.state

    # --- metrics strip ---
    # NB: rolling_coverage is NaN server-side until the first label and arrives as
    # null/None through JSON, so every numeric field is formatted None/NaN-safely.
    def _fmt(v: float | None, spec: str = ".3f") -> str:
        return "—" if v is None or v != v else format(v, spec)

    m = client.metrics() if ok else {}
    target = m.get("target_coverage") or 0.9
    rc = m.get("rolling_coverage")
    cols = st.columns(5)
    cols[0].metric("bias b_t", _fmt(m.get("bias")))
    cols[1].metric("alpha_t", _fmt(m.get("alpha_t")))
    cols[2].metric(
        "rolling coverage",
        _fmt(rc),
        delta=None if rc is None or rc != rc else f"{rc - target:+.3f}",
    )
    cols[3].metric("labels", m.get("n_label", 0))
    cols[4].metric("drift", "FLAG" if m.get("drift_flag") else "ok")

    records = ss["records"]
    if not records:
        st.info("Connect the service and press **Advance** to start the stream.")
        return

    window = 300
    df = pd.DataFrame(records[-window:])

    st.subheader("Prediction + conformal band")
    band = (
        alt.Chart(df)
        .mark_area(opacity=0.25, color="#4C78A8")
        .encode(x=alt.X("t:Q", title="sample"), y=alt.Y("lower:Q", title="quality"), y2="upper:Q")
    )
    line = alt.Chart(df).mark_line(color="#4C78A8").encode(x="t:Q", y="y_pred:Q")
    pts = (
        alt.Chart(df.dropna(subset=["y_true"]))
        .mark_point(color="#E45756", filled=True, size=30)
        .encode(x="t:Q", y="y_true:Q")
    )
    st.altair_chart(band + line + pts, use_container_width=True)

    st.subheader(f"Rolling coverage (target {target:.2f})")
    labeled = df.dropna(subset=["covered"]).copy()
    if not labeled.empty:
        labeled["rolling"] = labeled["covered"].astype(float).expanding().mean()
        labeled["target"] = target
        st.line_chart(labeled.set_index("t")[["rolling", "target"]])
    else:
        st.caption("No labels yet — increase the stream or lower the label delay.")


if __name__ == "__main__":
    render()
