"""
Dashboard Page 4: Power Analysis & Sample Size Planning Calculator
Interactive experiment sizing, MDE sensitivity curves, and post-hoc statistical power diagnostics.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from analysis.power_analysis import (
    calculate_sample_size,
    calculate_achievable_mde,
    calculate_post_hoc_power,
    generate_power_curve_data
)

st.set_page_config(page_title="Power Calculator", page_icon="⚡", layout="wide")


def main():
    st.title("⚡ Statistical Power & Experiment Sizing Calculator")
    st.caption("Pre-experiment sample size planning, Minimum Detectable Effect (MDE) curves, and post-hoc power diagnosis.")

    tab_calc, tab_diagnosis = st.tabs(["🧮 Interactive Sizing Calculator", "🔍 Post-Hoc Experiment Diagnosis"])

    with tab_calc:
        st.subheader("Interactive Sample Size Planner")
        st.markdown("Configure experiment parameters to determine the statistical sample size required to avoid Type I and Type II errors.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            baseline_cr_input = st.number_input("Baseline Conversion Rate (%)", min_value=0.1, max_value=50.0, value=12.04, step=0.5)
            baseline_cr = baseline_cr_input / 100.0
        with col2:
            mde_relative = st.slider("Desired Relative MDE (± %)", min_value=0.5, max_value=15.0, value=2.0, step=0.5)
        with col3:
            alpha = st.selectbox("Significance Level (α)", [0.01, 0.05, 0.10], index=1)
        with col4:
            power = st.selectbox("Statistical Power (1 - β)", [0.80, 0.85, 0.90, 0.95], index=0)

        res = calculate_sample_size(
            baseline_cr=baseline_cr,
            mde_relative_pct=mde_relative,
            alpha=alpha,
            power=power
        )

        abs_mde_pp = (res["treatment_cr"] - baseline_cr) * 100

        c_out1, c_out2, c_out3, c_out4 = st.columns(4)
        c_out1.metric("Required per Variant", f"{res['n_per_variant']:,}", "Users per group")
        c_out2.metric("Total Sample Size", f"{res['total_required']:,}", "Control + Treatment")
        c_out3.metric("Absolute Lift Target", f"{abs_mde_pp:+.3f} pp", f"Target CR: {res['treatment_cr'] * 100:.2f}%")
        c_out4.metric("Cohen's h Effect Size", f"{res['effect_size_h']:.5f}", f"Power: {int(power * 100)}%")

        st.markdown("---")

        # Dynamic Power Curve
        st.subheader("📊 MDE Sensitivity Curve")
        curve_df = generate_power_curve_data(baseline_cr=baseline_cr, alpha=alpha, power=power)

        fig_curve = px.line(
            curve_df,
            x="relative_mde_pct",
            y="n_per_variant",
            title=f"Required Sample Size vs. Minimum Detectable Effect (Baseline CR = {baseline_cr_input:.2f}%, Power = {int(power*100)}%)",
            labels={"relative_mde_pct": "Minimum Detectable Effect (Relative %)", "n_per_variant": "Required Sample Size per Group"}
        )
        # Mark current point
        fig_curve.add_trace(go.Scatter(
            x=[mde_relative],
            y=[res["n_per_variant"]],
            mode="markers+text",
            marker=dict(color="red", size=12),
            text=[f"Target: {res['n_per_variant']:,}"],
            textposition="top right",
            name="Selected Target"
        ))
        fig_curve.update_layout(template="plotly_white", yaxis_tickformat=",")
        st.plotly_chart(fig_curve, use_container_width=True)
        st.caption("Notice the asymptotic hockey-stick curve: attempting to detect tiny effects (< 1%) requires exponential increases in traffic volume.")

    with tab_diagnosis:
        st.subheader("🔍 Post-Hoc Power Diagnosis: Why Did This Test Fail to Reject H0?")
        post_hoc = calculate_post_hoc_power()
        mde_info = calculate_achievable_mde()

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Observed Power", f"{post_hoc['observed_power'] * 100:.1f}%", "Target was 80%", delta_color="inverse")
        d2.metric("Actual Traffic per Arm", f"{145274:,}", "290,584 total")
        d3.metric("Traffic Needed for 80% Power", f"{post_hoc['needed_n_per_variant']:,}", "Per variant", delta_color="inverse")
        d4.metric("True Experiment MDE", f"± {mde_info['achievable_rel_mde_pct']:.2f}%", "With 145k sample")

        st.markdown(f"""
        ### 💡 The Senior Data Analyst's Diagnostic Verdict:
        1. **The Experiment Was Adequately Sized for Normal Product Bets:**
           - With **145,274 visitors per arm**, the experimentation system was capable of reliably detecting any relative change **≥ ±2.83%** (or $\\pm 0.34$ percentage points) at 80% power.
        2. **Why It Failed Significance Testing:**
           - The actual observed difference was tiny: **-1.31% relative** (-0.158 pp).
           - Detecting a difference that minuscule with 80% statistical power requires **662,109 visitors per arm** (over **1.32 Million total visitors**).
        3. **Is It Safe to Reject the Feature?**
           - **Yes!** Even though the p-value (p = 0.1899) is technically "statistically non-significant" in frequentist terms, the Bayesian analysis demonstrates a **90.6% probability that Control is superior**, and our power calculation proves that the new page definitely does *not* possess the promised positive uplift.
           - Rolling back treatment avoids unnecessary tech debt and potential conversion degradation.
        """)


if __name__ == "__main__":
    main()
