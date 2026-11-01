"""
Analysis Module: Statistical Power & Sample Size Calculator
Computes pre-experiment sample size requirements, minimum detectable effect (MDE),
post-hoc statistical power, and power-tradeoff curves.
"""

import numpy as np
import pandas as pd
from statsmodels.stats.power import zt_ind_solve_power
from statsmodels.stats.proportion import proportion_effectsize


def calculate_sample_size(
    baseline_cr: float = 0.12,
    mde_relative_pct: float = 2.0,  # e.g., 2% relative change
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True
):
    """
    Computes required sample size per variant for a two-proportion test.
    """
    treatment_cr = baseline_cr * (1.0 + mde_relative_pct / 100.0)
    effect_size = proportion_effectsize(treatment_cr, baseline_cr)

    alternative = "two-sided" if two_tailed else "larger"
    n_per_variant = zt_ind_solve_power(
        effect_size=abs(effect_size),
        alpha=alpha,
        power=power,
        ratio=1.0,
        alternative=alternative
    )

    n_per_variant = int(np.ceil(n_per_variant))
    total_required = n_per_variant * 2

    return {
        "baseline_cr": baseline_cr,
        "mde_relative_pct": mde_relative_pct,
        "treatment_cr": treatment_cr,
        "effect_size_h": abs(effect_size),
        "alpha": alpha,
        "power": power,
        "n_per_variant": n_per_variant,
        "total_required": total_required
    }


def calculate_achievable_mde(
    baseline_cr: float = 0.12,
    n_per_variant: int = 145000,
    alpha: float = 0.05,
    power: float = 0.80
):
    """
    Computes the Minimum Detectable Effect (MDE) achievable given a fixed sample size.
    """
    # Solve for effect size given n
    target_effect_size = zt_ind_solve_power(
        nobs1=n_per_variant,
        alpha=alpha,
        power=power,
        ratio=1.0,
        alternative="two-sided"
    )

    # Convert Cohen's h effect size back to relative MDE
    # h = 2 * arcsin(sqrt(p2)) - 2 * arcsin(sqrt(p1))
    phi1 = 2 * np.arcsin(np.sqrt(baseline_cr))
    phi2 = phi1 + target_effect_size
    p2 = np.sin(phi2 / 2) ** 2
    abs_mde = p2 - baseline_cr
    rel_mde_pct = (abs_mde / baseline_cr) * 100

    return {
        "baseline_cr": baseline_cr,
        "n_per_variant": n_per_variant,
        "achievable_abs_mde": abs_mde,
        "achievable_rel_mde_pct": rel_mde_pct,
        "achievable_treatment_cr": p2,
        "effect_size_h": target_effect_size
    }


def calculate_post_hoc_power(
    baseline_cr: float = 0.12039,
    observed_cr: float = 0.11881,
    n_control: int = 145274,
    n_treatment: int = 145310,
    alpha: float = 0.05
):
    """
    Computes post-hoc observed statistical power for the actual experiment.
    """
    effect_size = proportion_effectsize(observed_cr, baseline_cr)
    avg_n = (n_control + n_treatment) / 2

    observed_power = zt_ind_solve_power(
        effect_size=abs(effect_size),
        nobs1=avg_n,
        alpha=alpha,
        ratio=n_treatment / n_control,
        alternative="two-sided"
    )

    # Also compute how much N was actually needed to detect THIS small effect at 80% power
    required_n = zt_ind_solve_power(
        effect_size=abs(effect_size),
        alpha=alpha,
        power=0.80,
        ratio=1.0,
        alternative="two-sided"
    )

    return {
        "baseline_cr": baseline_cr,
        "observed_cr": observed_cr,
        "effect_size": abs(effect_size),
        "observed_power": float(observed_power),
        "needed_n_per_variant": int(np.ceil(required_n)),
        "needed_total_n": int(np.ceil(required_n)) * 2,
        "is_underpowered": observed_power < 0.80
    }


def generate_power_curve_data(baseline_cr: float = 0.12, alpha: float = 0.05, power: float = 0.80):
    """
    Generates data points for MDE vs Required Sample Size curve.
    """
    mde_range = np.linspace(0.5, 10.0, 50)  # 0.5% to 10% relative lift
    records = []

    for mde in mde_range:
        res = calculate_sample_size(baseline_cr=baseline_cr, mde_relative_pct=mde, alpha=alpha, power=power)
        records.append({
            "relative_mde_pct": mde,
            "n_per_variant": res["n_per_variant"],
            "total_sample_size": res["total_required"]
        })

    return pd.DataFrame(records)


def print_summary():
    print("\n" + "=" * 80)
    print("POWER ANALYSIS & EXPERIMENT SIZING REPORT")
    print("=" * 80)
    res_2pct = calculate_sample_size(baseline_cr=0.1204, mde_relative_pct=2.0, alpha=0.05, power=0.80)
    print(f"To detect +/- 2.0% relative lift at 80% power:")
    print(f"  Required sample size per variant: {res_2pct['n_per_variant']:,}")
    print(f"  Total experiment sample size:     {res_2pct['total_required']:,}")
    print("-" * 80)
    mde_res = calculate_achievable_mde(baseline_cr=0.1204, n_per_variant=145000, alpha=0.05, power=0.80)
    print(f"With actual sample size (~145K per variant):")
    print(f"  Achievable Minimum Detectable Effect (MDE): +/- {mde_res['achievable_rel_mde_pct']:.2f}% relative")
    print(f"  Absolute conversion rate sensitivity:       +/- {mde_res['achievable_abs_mde'] * 100:.3f} pp")
    print("-" * 80)
    post_hoc = calculate_post_hoc_power()
    print(f"Post-Hoc Power Analysis on Observed Difference (-1.31% relative):")
    print(f"  Observed statistical power:   {post_hoc['observed_power'] * 100:.2f}%")
    print(f"  Sample size needed for 80%:   {post_hoc['needed_n_per_variant']:,} per group ({post_hoc['needed_total_n']:,} total)")
    print(f"  Underpowered for tiny lift?   {'YES - Required over 360K per group' if post_hoc['is_underpowered'] else 'NO'}")
    print("=" * 80)


if __name__ == "__main__":
    print_summary()
