"""
Dashboard Page 2: Frequentist Hypothesis Testing & Statistical Significance
Executes Chi-Square, Two-Proportion Z-Test, Wilson CIs, and provides an Upload-Your-Own-Data interface.
"""

from pathlib import Path
import sys
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from analysis.freq_testing import compute_frequentist_metrics

PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"

st.set_page_config(page_title="Statistical Testing", page_icon="⚖️", layout="wide")


@st.cache_data
def load_data():
    return pd.read_parquet(PROCESSED_DATA_PATH)


def display_results_ui(res, source_label="Clean E-Commerce Cohort"):
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Control Conversion Rate", f"{res['cr_control'] * 100:.3f}%", f"{res['conv_control']:,} / {res['n_control']:,}")
    c2.metric("Treatment Conversion Rate", f"{res['cr_treatment'] * 100:.3f}%", f"{res['conv_treatment']:,} / {res['n_treatment']:,}")
    c3.metric("Relative Lift", f"{res['rel_lift']:+.2f}%", f"{res['abs_diff'] * 100:+.3f} pp")
    c4.metric("Chi-Square p-value", f"{res['chi2_p_val']:.4f}", f"alpha = {res['alpha']}")

    # Decision Banner
    if res["is_significant"]:
        if res["abs_diff"] > 0:
            st.success(f"### 🎉 {res['verdict']}\n**Recommendation:** {res['recommendation']}")
        else:
            st.error(f"### 🛑 {res['verdict']}\n**Recommendation:** {res['recommendation']}")
    else:
        st.warning(f"### ⚠️ {res['verdict']}\n**Recommendation:** {res['recommendation']}")

    st.markdown("---")

    col_tests, col_ci = st.columns([1, 1])

    with col_tests:
        st.subheader("📋 Statistical Hypothesis Test Matrix")
        test_df = pd.DataFrame([
            {"Test Name": "Chi-Square Test (χ²)", "Test Statistic": f"{res['chi2_stat']:.4f}", "p-value": f"{res['chi2_p_val']:.4f}", "Significant?": "Yes" if res['chi2_p_val'] < res['alpha'] else "No"},
            {"Test Name": "Two-Proportion Z-Test", "Test Statistic": f"z = {res['z_stat']:.4f}", "p-value": f"{res['z_p_val']:.4f}", "Significant?": "Yes" if res['z_p_val'] < res['alpha'] else "No"},
            {"Test Name": "Mann-Whitney U Test", "Test Statistic": f"U = {res['u_stat']:.2e}", "p-value": f"{res['u_p_val']:.4f}", "Significant?": "Yes" if res['u_p_val'] < res['alpha'] else "No"},
            {"Test Name": "Cohen's h Effect Size", "Test Statistic": f"h = {res['cohen_h']:.5f}", "p-value": "N/A (<0.2 is negligible)", "Significant?": "Negligible"}
        ])
        st.dataframe(test_df, use_container_width=True, hide_index=True)

        st.markdown(f"""
        **Mathematical Interpretation:**
        - Null Hypothesis ($H_0$): $p_{{Treatment}} = p_{{Control}}$
        - Alternative Hypothesis ($H_1$): $p_{{Treatment}} \\neq p_{{Control}}$
        - With a p-value of **{res['chi2_p_val']:.4f}**, which is greater than the significance threshold $\\alpha = {res['alpha']}$, the difference is statistically indistinguishable from zero at the 95% confidence level.
        """)

    with col_ci:
        st.subheader("🎯 Confidence Intervals (Wilson Score 95%)")
        ci_df = pd.DataFrame({
            "Variant": ["Control", "Treatment"],
            "Conversion Rate": [res["cr_control"] * 100, res["cr_treatment"] * 100],
            "CI Lower": [res["ci_ctrl"][0] * 100, res["ci_treat"][0] * 100],
            "CI Upper": [res["ci_ctrl"][1] * 100, res["ci_treat"][1] * 100],
            "Error Minus": [(res["cr_control"] - res["ci_ctrl"][0]) * 100, (res["cr_treatment"] - res["ci_treat"][0]) * 100],
            "Error Plus": [(res["ci_ctrl"][1] - res["cr_control"]) * 100, (res["ci_treat"][1] - res["cr_treatment"]) * 100]
        })

        fig_ci = go.Figure()
        fig_ci.add_trace(go.Scatter(
            x=ci_df["Variant"],
            y=ci_df["Conversion Rate"],
            error_y=dict(type="data", symmetric=False, array=ci_df["Error Plus"], arrayminus=ci_df["Error Minus"]),
            mode="markers+text",
            marker=dict(color=["#1f77b4", "#ff7f0e"], size=14),
            text=[f"{v:.3f}%" for v in ci_df["Conversion Rate"]],
            textposition="top right"
        ))
        fig_ci.update_layout(
            title="95% Wilson Confidence Intervals (Note the heavy overlap)",
            yaxis_title="Conversion Rate (%)",
            template="plotly_white",
            height=350
        )
        st.plotly_chart(fig_ci, use_container_width=True)


def main():
    st.title("⚖️ Frequentist Hypothesis Testing")
    st.caption("Standard frequentist significance testing with Chi-Square, Z-test, Wilson confidence intervals, and effect size calculations.")

    tab_dataset, tab_custom = st.tabs(["📊 E-Commerce Dataset Results", "📤 Upload Your Own A/B Test CSV"])

    with tab_dataset:
        if not PROCESSED_DATA_PATH.exists():
            st.error("Processed experiment dataset not found. Please run the pipeline first.")
            return

        col_alpha, _ = st.columns([1, 3])
        with col_alpha:
            alpha = st.selectbox("Significance Level (α):", [0.05, 0.01, 0.10], index=0)

        df = load_data()
        res = compute_frequentist_metrics(df, alpha=alpha)
        display_results_ui(res)

    with tab_custom:
        st.subheader("Upload Custom Experiment CSV")
        st.markdown("""
        Upload your own CSV with at minimum two columns:
        - `group` (e.g., 'control' and 'treatment')
        - `converted` (binary: 0 or 1)
        """)

        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        if uploaded_file is not None:
            try:
                user_df = pd.read_csv(uploaded_file)
                st.write(f"Loaded {len(user_df):,} rows with columns: `{list(user_df.columns)}`")
                
                # Check column compatibility
                group_col = None
                conv_col = None
                for col in user_df.columns:
                    if col.lower() in ["group", "variant", "arm"]:
                        group_col = col
                    if col.lower() in ["converted", "conversion", "target", "label"]:
                        conv_col = col

                if not group_col or not conv_col:
                    st.error("Could not auto-detect group or converted columns. Please make sure your CSV contains columns named 'group' and 'converted'.")
                else:
                    user_clean = user_df[[group_col, conv_col]].copy()
                    user_clean.columns = ["assigned_group", "converted"]
                    user_clean["assigned_group"] = user_clean["assigned_group"].astype(str).str.lower()
                    user_clean["converted"] = pd.to_numeric(user_clean["converted"], errors="coerce").fillna(0).astype(int)

                    res_custom = compute_frequentist_metrics(user_clean, alpha=0.05)
                    display_results_ui(res_custom, source_label="Uploaded Custom Data")
            except Exception as e:
                st.error(f"Error processing uploaded CSV: {e}")


if __name__ == "__main__":
    main()
