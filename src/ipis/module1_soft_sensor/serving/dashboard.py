"""Streamlit operator dashboard for Module 1 soft sensor.

Displays:
- Live soft sensor prediction with 95% prediction interval
- Drift status indicator
- Recent prediction trend (last N samples)
- Model health metrics (latency, error rate)

Subscribes to MQTT topics under /ipis/m1/* for real-time updates.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="IPIS Module 1 — Soft Sensor",
    page_icon="📊",
    layout="wide",
)


def main() -> None:
    """Render the dashboard."""
    st.title("IPIS Module 1 — Soft Sensor")
    st.markdown(
        "Real-time soft sensor predictions with calibrated uncertainty bounds, "
        "drift detection, and model health monitoring."
    )

    st.info(
        "**Dashboard placeholder.** Implementation in Phase 1D. "
        "See `docs/module1/spec.md`."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Prediction", "—", "—")
    with col2:
        st.metric("Prediction Interval", "± —", "—")
    with col3:
        st.metric("Drift Status", "OK", "—")

    st.subheader("Recent Predictions")
    st.empty()  # placeholder for plot

    st.subheader("Model Health")
    st.empty()  # placeholder for latency / error metrics


if __name__ == "__main__":
    main()
