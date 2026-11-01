"""
Analysis Module: Frequentist Statistical Hypothesis Testing
Implements Chi-Square test, Two-Proportion Z-Test, Mann-Whitney U,
Confidence Intervals (Wilson & Wald), and Cohen's h Effect Size.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ab_testing.db"


def compute_frequentist_metrics(df: pd.DataFrame = None, alpha: float = 0.05):
    """
    Computes complete frequentist statistical analysis on experiment cohorts.
    Accepts either an input DataFrame or loads from the SQLite warehouse.
    """
    if df is None:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT u.assigned_group, f.converted
            FROM fact_sessions f
            JOIN dim_users u ON f.user_id = u.user_id
        """, conn)
        conn.close()

    group_col = "assigned_group" if "assigned_group" in df.columns else "group"
    control_mask = df[group_col] == "control"
    treatment_mask = df[group_col] == "treatment"

    n_control = int(control_mask.sum())
    n_treatment = int(treatment_mask.sum())
    conv_control = int(df.loc[control_mask, "converted"].sum())
    conv_treatment = int(df.loc[treatment_mask, "converted"].sum())

    cr_control = conv_control / n_control if n_control > 0 else 0.0
    cr_treatment = conv_treatment / n_treatment if n_treatment > 0 else 0.0

    abs_diff = cr_treatment - cr_control
    rel_lift = (abs_diff / cr_control) * 100 if cr_control > 0 else 0.0

    # 1. Two-proportion Z-test
    count = np.array([conv_treatment, conv_control])
    nobs = np.array([n_treatment, n_control])
    z_stat, z_p_val = proportions_ztest(count, nobs, alternative="two-sided")

    # 2. Chi-Square Test
    non_conv_control = n_control - conv_control
    non_conv_treatment = n_treatment - conv_treatment
    contingency = [[conv_treatment, non_conv_treatment],
                   [conv_control, non_conv_control]]
    chi2_stat, chi2_p_val, dof, expected = stats.chi2_contingency(contingency, correction=False)

    # 3. Mann-Whitney U test (non-parametric validation)
    u_stat, u_p_val = stats.mannwhitneyu(
        df.loc[treatment_mask, "converted"],
        df.loc[control_mask, "converted"],
        alternative="two-sided"
    )

    # 4. Confidence Intervals (Wilson Score for single proportions)
    ci_ctrl_low, ci_ctrl_high = proportion_confint(conv_control, n_control, alpha=alpha, method="wilson")
    ci_treat_low, ci_treat_high = proportion_confint(conv_treatment, n_treatment, alpha=alpha, method="wilson")

    # Difference standard error & 95% CI
    se_diff = np.sqrt((cr_control * (1 - cr_control) / n_control) + (cr_treatment * (1 - cr_treatment) / n_treatment))
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_diff_low = abs_diff - z_crit * se_diff
    ci_diff_high = abs_diff + z_crit * se_diff

    # 5. Cohen's h effect size for proportions
    phi_treatment = 2 * np.arcsin(np.sqrt(cr_treatment))
    phi_control = 2 * np.arcsin(np.sqrt(cr_control))
    cohen_h = phi_treatment - phi_control

    # 6. Verdict and Interpretation
    is_significant = bool(chi2_p_val < alpha)
    if is_significant:
        if abs_diff > 0:
            verdict = "REJECT H0 - Treatment shows statistically significant positive uplift."
            recommendation = "Roll out new page version to 100% of user traffic."
        else:
            verdict = "REJECT H0 - Treatment shows statistically significant negative decline."
            recommendation = "Halt rollout immediately and maintain control version."
    else:
        verdict = "FAIL TO REJECT H0 - Insufficient statistical evidence of a difference."
        recommendation = "Do not roll out treatment. The observed difference is consistent with random chance."

    results = {
        "n_control": n_control,
        "n_treatment": n_treatment,
        "conv_control": conv_control,
        "conv_treatment": conv_treatment,
        "cr_control": cr_control,
        "cr_treatment": cr_treatment,
        "abs_diff": abs_diff,
        "rel_lift": rel_lift,
        "z_stat": float(z_stat),
        "z_p_val": float(z_p_val),
        "chi2_stat": float(chi2_stat),
        "chi2_p_val": float(chi2_p_val),
        "u_stat": float(u_stat),
        "u_p_val": float(u_p_val),
        "ci_ctrl": (float(ci_ctrl_low), float(ci_ctrl_high)),
        "ci_treat": (float(ci_treat_low), float(ci_treat_high)),
        "ci_diff": (float(ci_diff_low), float(ci_diff_high)),
        "se_diff": float(se_diff),
        "cohen_h": float(cohen_h),
        "is_significant": is_significant,
        "verdict": verdict,
        "recommendation": recommendation,
        "alpha": alpha
    }

    return results


def print_summary(res):
    print("\n" + "=" * 80)
    print("FREQUENTIST HYPOTHESIS TESTING REPORT")
    print("=" * 80)
    print(f"Sample Sizes: Control = {res['n_control']:,} | Treatment = {res['n_treatment']:,}")
    print(f"Conversions:  Control = {res['conv_control']:,} | Treatment = {res['conv_treatment']:,}")
    print(f"Rates:        Control = {res['cr_control'] * 100:.3f}% | Treatment = {res['cr_treatment'] * 100:.3f}%")
    print(f"Relative Lift: {res['rel_lift']:+.2f}% (Absolute: {res['abs_diff'] * 100:+.3f} pp)")
    print(f"95% CI Lift:   [{res['ci_diff'][0] * 100:+.3f}%, {res['ci_diff'][1] * 100:+.3f}%]")
    print("-" * 80)
    print(f"Two-Proportion Z-Test:  z = {res['z_stat']:.4f}, p = {res['z_p_val']:.4f}")
    print(f"Chi-Square Test:       chi2 = {res['chi2_stat']:.4f}, p = {res['chi2_p_val']:.4f}")
    print(f"Mann-Whitney U Test:   U = {res['u_stat']:.2e}, p = {res['u_p_val']:.4f}")
    print(f"Cohen's h Effect Size: {res['cohen_h']:.5f} (Negligible < 0.2)")
    print("-" * 80)
    print(f"Decision Verdict: {res['verdict']}")
    print(f"Business Action:  {res['recommendation']}")
    print("=" * 80)


if __name__ == "__main__":
    results = compute_frequentist_metrics()
    print_summary(results)
