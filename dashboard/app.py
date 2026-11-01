"""
Main Streamlit Application Entrypoint
A/B Testing & Statistical Experimentation Platform
"""

from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Setup Page Configuration
st.set_page_config(
    page_title="A/B Testing & Statistical Experimentation Platform",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ab_testing.db"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"
SUMMARY_DATA_PATH = BASE_DIR / "data" / "processed" / "experiment_summary.parquet"


@st.cache_data
def load_quick_stats():
    if not PROCESSED_DATA_PATH.exists():
        return None
    df = pd.read_parquet(PROCESSED_DATA_PATH)
    n_total = len(df)
    n_ctrl = (df["group"] == "control").sum()
    n_treat = (df["group"] == "treatment").sum()
    conv_ctrl = df[df["group"] == "control"]["converted"].sum()
    conv_treat = df[df["group"] == "treatment"]["converted"].sum()
    cr_ctrl = conv_ctrl / n_ctrl
    cr_treat = conv_treat / n_treat
    rel_lift = ((cr_treat - cr_ctrl) / cr_ctrl) * 100
    days = df["session_date"].nunique()
    return {
        "n_total": n_total,
        "n_ctrl": n_ctrl,
        "n_treat": n_treat,
        "cr_ctrl": cr_ctrl,
        "cr_treat": cr_treat,
        "rel_lift": rel_lift,
        "days": days
    }


def main():
    st.title("🧪 A/B Testing & Statistical Experimentation Platform")
    st.caption("Production-grade statistical experimentation framework combining Frequentist hypothesis testing, Bayesian Beta-Binomial posterior modeling, and sample size power planning.")

    stats = load_quick_stats()
    if stats is None:
        st.error("Processed experiment dataset not found. Please run the pipeline first.")
        return

    # Top KPI Metrics Row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total User Sessions", f"{stats['n_total']:,}", "Clean Cohort")
    c2.metric("Control CR", f"{stats['cr_ctrl'] * 100:.2f}%", f"{stats['n_ctrl']:,} users")
    c3.metric("Treatment CR", f"{stats['cr_treat'] * 100:.2f}%", f"{stats['n_treat']:,} users")
    c4.metric("Observed Relative Lift", f"{stats['rel_lift']:+.2f}%", "-0.16 pp absolute", delta_color="inverse")
    c5.metric("Experiment Duration", f"{stats['days']} Days", "Full cycle")

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("📌 Executive Experiment Summary & Google-Grade Verdict")
        st.markdown("""
        ### Why this experiment failed to ship:
        1. **Negative Directional Drift:** The new page variant delivered a **-1.31% relative decline** in conversion rate (11.88% vs 12.04%).
        2. **Frequentist p-value (p = 0.1899):** Fails significance testing ($\alpha = 0.05$). The null hypothesis cannot be rejected.
        3. **Bayesian Posterior:** There is a **90.6% probability that Control is superior**, and deploying Treatment carries an expected loss 30× greater than holding Control.
        4. **Power Post-Mortem:** Detecting a tiny 1.3% relative lift requires **>660,000 users per variant**. The experiment was underpowered for effects under 2.8%, but sufficiently powered to rule out any meaningful positive uplift.
        5. **Final Recommendation:** **Do NOT ship the new page.** Maintain the control landing page and re-examine the UX changes.
        """)

        st.info("💡 **Interactive Capabilities:** Use the left navigation to explore Frequentist hypothesis tests, Bayesian posterior simulations, interactive power analysis, or test your own custom datasets.")

    with col_right:
        st.subheader("🏗️ Architecture & Experimentation Stack")
        st.markdown("""
        - **Data Warehouse:** SQLite Star Schema (`dim_users`, `dim_dates`, `fact_sessions`)
        - **Frequentist Suite:** Chi-Square ($\chi^2$), Two-Proportion Z-Test, Mann-Whitney U, Wilson Score 95% CIs
        - **Bayesian Suite:** Beta-Binomial Conjugate Updating, Monte Carlo 100k sampling, ROPE Analysis, Expected Loss
        - **Guardrails:** Automated Sample Ratio Mismatch (SRM) chi-square test & novelty bias detection
        - **Power Modeling:** Two-proportion Z-power solver for sample size and MDE curves
        """)

    st.markdown("---")
    st.subheader("🧭 Explore Dashboard Modules")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("#### 01 · Overview")
        st.caption("Temporal stability trends, cumulative convergence, and daily SRM health checks.")
    with m2:
        st.markdown("#### 02 · Frequentist Tests")
        st.caption("Chi-Square, Z-test, Cohen's h, confidence intervals, plus Upload-Your-Own-Data.")
    with m3:
        st.markdown("#### 03 · Bayesian Posterior")
        st.caption("Beta-Binomial curves, P(Treatment > Control), expected loss, and ROPE analysis.")
    with m4:
        st.markdown("#### 04 · Power Calculator")
        st.caption("Interactive sample size calculator, MDE curves, and post-hoc power diagnosis.")


if __name__ == "__main__":
    main()
