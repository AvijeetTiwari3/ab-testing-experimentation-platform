"""
Analysis Module: Bayesian A/B Testing & Posterior Estimation
Implements Beta-Binomial conjugate updating, Monte Carlo simulation,
Probability to be Best, Expected Loss, ROPE, and Bayesian Credible Intervals.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ab_testing.db"


def compute_bayesian_metrics(
    df: pd.DataFrame = None,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    rope_threshold: float = 0.001,  # 0.1% practical equivalence threshold
    n_simulations: int = 100000,
    random_seed: int = 42
):
    """
    Computes Bayesian A/B testing metrics using a Beta-Binomial conjugate model.
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

    # Beta posterior parameters
    post_alpha_c = prior_alpha + conv_control
    post_beta_c = prior_beta + (n_control - conv_control)

    post_alpha_t = prior_alpha + conv_treatment
    post_beta_t = prior_beta + (n_treatment - conv_treatment)

    # Analytical means & credible intervals
    mean_c = post_alpha_c / (post_alpha_c + post_beta_c)
    mean_t = post_alpha_t / (post_alpha_t + post_beta_t)

    ci_c_low = stats.beta.ppf(0.025, post_alpha_c, post_beta_c)
    ci_c_high = stats.beta.ppf(0.975, post_alpha_c, post_beta_c)

    ci_t_low = stats.beta.ppf(0.025, post_alpha_t, post_beta_t)
    ci_t_high = stats.beta.ppf(0.975, post_alpha_t, post_beta_t)

    # Monte Carlo simulation for difference distribution
    np.random.seed(random_seed)
    samples_c = np.random.beta(post_alpha_c, post_beta_c, size=n_simulations)
    samples_t = np.random.beta(post_alpha_t, post_beta_t, size=n_simulations)

    diff_samples = samples_t - samples_c
    rel_lift_samples = (diff_samples / samples_c) * 100

    # Probabilities
    prob_t_better = float(np.mean(samples_t > samples_c))
    prob_c_better = 1.0 - prob_t_better

    # Expected Loss (risk in conversion rate pp if wrong decision is taken)
    loss_choosing_t = float(np.mean(np.maximum(samples_c - samples_t, 0)))
    loss_choosing_c = float(np.mean(np.maximum(samples_t - samples_c, 0)))

    # Credible Interval for difference
    ci_diff_low = float(np.percentile(diff_samples, 2.5))
    ci_diff_high = float(np.percentile(diff_samples, 97.5))

    ci_lift_low = float(np.percentile(rel_lift_samples, 2.5))
    ci_lift_high = float(np.percentile(rel_lift_samples, 97.5))

    # ROPE (Region of Practical Equivalence)
    prob_in_rope = float(np.mean(np.abs(diff_samples) < rope_threshold))

    # Verdict
    if prob_t_better >= 0.95:
        verdict = f"High confidence ({prob_t_better * 100:.1f}%) that Treatment is superior."
        recommendation = "Deploy treatment variant with minimal expected risk."
    elif prob_c_better >= 0.95:
        verdict = f"High confidence ({prob_c_better * 100:.1f}%) that Control is superior."
        recommendation = "Maintain control variant. Deploying treatment carries expected loss."
    else:
        verdict = f"Inconclusive: P(Treatment > Control) is {prob_t_better * 100:.1f}%, ROPE is {prob_in_rope * 100:.1f}%."
        recommendation = "Do not deploy. The risk of degrading conversion outweighs potential gain."

    results = {
        "prior": (prior_alpha, prior_beta),
        "post_c": (post_alpha_c, post_beta_c),
        "post_t": (post_alpha_t, post_beta_t),
        "mean_c": float(mean_c),
        "mean_t": float(mean_t),
        "ci_c": (float(ci_c_low), float(ci_c_high)),
        "ci_t": (float(ci_t_low), float(ci_t_high)),
        "ci_diff": (ci_diff_low, ci_diff_high),
        "ci_lift": (ci_lift_low, ci_lift_high),
        "prob_t_better": prob_t_better,
        "prob_c_better": prob_c_better,
        "loss_choosing_t": loss_choosing_t,
        "loss_choosing_c": loss_choosing_c,
        "rope_threshold": rope_threshold,
        "prob_in_rope": prob_in_rope,
        "diff_samples": diff_samples,
        "samples_c": samples_c,
        "samples_t": samples_t,
        "verdict": verdict,
        "recommendation": recommendation
    }

    return results


def print_summary(res):
    print("\n" + "=" * 80)
    print("BAYESIAN EXPERIMENTATION REPORT (BETA-BINOMIAL CONJUGATE)")
    print("=" * 80)
    print(f"Priors: Beta({res['prior'][0]}, {res['prior'][1]}) [Uninformative]")
    print(f"Posterior Control:   Beta(alpha={res['post_c'][0]}, beta={res['post_c'][1]})")
    print(f"Posterior Treatment: Beta(alpha={res['post_t'][0]}, beta={res['post_t'][1]})")
    print("-" * 80)
    print(f"Posterior Mean CR: Control = {res['mean_c'] * 100:.3f}% | Treatment = {res['mean_t'] * 100:.3f}%")
    print(f"95% Credible Interval Control:   [{res['ci_c'][0] * 100:.3f}%, {res['ci_c'][1] * 100:.3f}%]")
    print(f"95% Credible Interval Treatment: [{res['ci_t'][0] * 100:.3f}%, {res['ci_t'][1] * 100:.3f}%]")
    print(f"95% Credible Interval Lift:      [{res['ci_lift'][0]:+.2f}%, {res['ci_lift'][1]:+.2f}%]")
    print("-" * 80)
    print(f"Probability Treatment > Control: {res['prob_t_better'] * 100:.2f}%")
    print(f"Probability Control > Treatment: {res['prob_c_better'] * 100:.2f}%")
    print(f"Expected Loss Choosing Treatment: {res['loss_choosing_t'] * 100:.4f} pp")
    print(f"Expected Loss Choosing Control:   {res['loss_choosing_c'] * 100:.4f} pp")
    print(f"P(Difference in ROPE +/-{res['rope_threshold']*100:.2f}%): {res['prob_in_rope'] * 100:.2f}%")
    print("-" * 80)
    print(f"Bayesian Verdict: {res['verdict']}")
    print(f"Action:           {res['recommendation']}")
    print("=" * 80)


if __name__ == "__main__":
    results = compute_bayesian_metrics()
    print_summary(results)
