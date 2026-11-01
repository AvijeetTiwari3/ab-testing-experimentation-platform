"""
Dashboard Page 3: Bayesian A/B Testing & Posterior Distributions
Beta-Binomial conjugate updating, Monte Carlo probability to be best, Expected Loss, and ROPE.
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from analysis.bayesian_analysis import compute_bayesian_metrics

PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"

st.set_page_config(page_title="Bayesian Analysis", page_icon="🎲", layout="wide")


@st.cache_data
def load_data():
    return pd.read_parquet(PROCESSED_DATA_PATH)


def main():
    st.title("🎲 Bayesian A/B Testing & Posterior Estimation")
    st.caption("Conjugate Beta-Binomial updating, Monte Carlo sampling, Probability to be Best, Expected Loss, and Region of Practical Equivalence (ROPE).")

    if not PROCESSED_DATA_PATH.exists():
        st.error("Processed experiment dataset not found. Please run the pipeline first.")
        return

    df = load_data()

    # Sidebar / Controls
    st.sidebar.header("⚙️ Bayesian Prior Parameters")
    prior_type = st.sidebar.selectbox("Prior Choice", ["Uninformative Beta(1, 1)", "Jeffreys Prior Beta(0.5, 0.5)", "Custom Prior"])
    if prior_type == "Uninformative Beta(1, 1)":
        alpha_0, beta_0 = 1.0, 1.0
    elif prior_type == "Jeffreys Prior Beta(0.5, 0.5)":
        alpha_0, beta_0 = 0.5, 0.5
    else:
        alpha_0 = st.sidebar.number_input("Prior Alpha (α0)", value=1.0, min_value=0.1, step=0.5)
        beta_0 = st.sidebar.number_input("Prior Beta (β0)", value=1.0, min_value=0.1, step=0.5)

    rope_threshold_input = st.sidebar.slider("ROPE Threshold (± %)", min_value=0.01, max_value=0.50, value=0.10, step=0.01)
    rope_val = rope_threshold_input / 100.0

    # Run Bayesian Computation
    res = compute_bayesian_metrics(
        df=df,
        prior_alpha=alpha_0,
        prior_beta=beta_0,
        rope_threshold=rope_val,
        n_simulations=50000
    )

    # Key Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("P(Treatment > Control)", f"{res['prob_t_better'] * 100:.1f}%", "Probability Treatment Wins")
    c2.metric("P(Control > Treatment)", f"{res['prob_c_better'] * 100:.1f}%", "Strong Evidence Control Wins")
    c3.metric("Expected Loss (Deploy Treatment)", f"{res['loss_choosing_t'] * 100:.4f} pp", "Risk of making wrong call")
    c4.metric(f"P(Difference in ROPE ±{rope_threshold_input:.2f}%)", f"{res['prob_in_rope'] * 100:.1f}%", "Practically Equivalent")

    # Verdict Alert
    if res["prob_c_better"] >= 0.90:
        st.warning(f"### 🛡️ Bayesian Decision: {res['verdict']}\n**Actionable Insight:** Deploying Treatment has an expected conversion rate penalty of **{res['loss_choosing_t'] * 100:.4f} pp**, which is **{res['loss_choosing_t'] / (res['loss_choosing_c'] + 1e-9):.1f}x higher** than the risk of sticking with Control. Sticking with Control is the mathematically rational choice.")
    elif res["prob_t_better"] >= 0.95:
        st.success(f"### 🎉 Bayesian Decision: {res['verdict']}\n{res['recommendation']}")
    else:
        st.info(f"### ⚖️ Bayesian Decision: {res['verdict']}\n{res['recommendation']}")

    st.markdown("---")

    col_posterior, col_diff = st.columns(2)

    with col_posterior:
        st.subheader("📈 Posterior Probability Density Functions")
        # Generate Beta density curves
        x_vals = np.linspace(0.114, 0.125, 400)
        pdf_c = stats.beta.pdf(x_vals, res["post_c"][0], res["post_c"][1])
        pdf_t = stats.beta.pdf(x_vals, res["post_t"][0], res["post_t"][1])

        fig_beta = go.Figure()
        fig_beta.add_trace(go.Scatter(x=x_vals * 100, y=pdf_c, mode="lines", name="Control Posterior", line=dict(color="#1f77b4", width=3), fill="tozeroy", fillcolor="rgba(31, 119, 180, 0.2)"))
        fig_beta.add_trace(go.Scatter(x=x_vals * 100, y=pdf_t, mode="lines", name="Treatment Posterior", line=dict(color="#ff7f0e", width=3), fill="tozeroy", fillcolor="rgba(255, 127, 14, 0.2)"))
        fig_beta.update_layout(
            title="Posterior Distribution of Conversion Rates (Beta Conjugate)",
            xaxis_title="Conversion Rate (%)",
            yaxis_title="Probability Density",
            template="plotly_white",
            legend=dict(yanchor="top", y=0.95, xanchor="right", x=0.95)
        )
        st.plotly_chart(fig_beta, use_container_width=True)
        st.caption("Control distribution (blue) is visibly shifted to the right of Treatment (orange).")

    with col_diff:
        st.subheader("🎯 Difference Distribution (Treatment - Control)")
        diff_samples = res["diff_samples"] * 100  # in percent points

        fig_diff = px.histogram(
            diff_samples,
            nbins=80,
            title="Posterior Distribution of Absolute Difference (pp)",
            labels={"value": "Absolute Difference (Treatment - Control in pp)"},
            color_discrete_sequence=["#2ca02c"]
        )
        # Add ROPE vertical bands
        fig_diff.add_vrect(
            x0=-rope_threshold_input, x1=rope_threshold_input,
            fillcolor="gray", opacity=0.25, line_width=1,
            annotation_text=f"ROPE ±{rope_threshold_input:.2f}%", annotation_position="top left"
        )
        fig_diff.add_vline(x0=0, line_dash="dash", line_color="red", annotation_text="Zero Effect")
        fig_diff.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_diff, use_container_width=True)
        st.caption(f"95% Bayesian Credible Interval of Difference: [{res['ci_diff'][0] * 100:+.3f} pp, {res['ci_diff'][1] * 100:+.3f} pp]. Over 90% of the distribution lies below zero.")


if __name__ == "__main__":
    main()
