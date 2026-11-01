"""
Test Suite: Statistical Analysis Modules (Frequentist, Bayesian, Power, Segmentation)
"""

from pathlib import Path
import sys
import pytest
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from analysis.freq_testing import compute_frequentist_metrics
from analysis.bayesian_analysis import compute_bayesian_metrics
from analysis.power_analysis import (
    calculate_sample_size,
    calculate_achievable_mde,
    calculate_post_hoc_power
)
from analysis.segment_analysis import analyze_novelty_effect, audit_daily_srm


def test_frequentist_metrics():
    res = compute_frequentist_metrics()
    assert "chi2_stat" in res
    assert "z_p_val" in res
    assert "cohen_h" in res
    assert 0.0 <= res["chi2_p_val"] <= 1.0
    assert 0.0 <= res["z_p_val"] <= 1.0
    assert res["ci_ctrl"][0] < res["ci_ctrl"][1]
    assert res["ci_treat"][0] < res["ci_treat"][1]
    assert isinstance(res["is_significant"], bool)


def test_bayesian_metrics():
    res = compute_bayesian_metrics(n_simulations=5000)
    assert "prob_t_better" in res
    assert "prob_c_better" in res
    assert abs((res["prob_t_better"] + res["prob_c_better"]) - 1.0) < 0.001
    assert res["loss_choosing_t"] >= 0.0
    assert res["loss_choosing_c"] >= 0.0
    assert 0.0 <= res["prob_in_rope"] <= 1.0


def test_power_analysis():
    # Sizing
    res = calculate_sample_size(baseline_cr=0.10, mde_relative_pct=5.0, alpha=0.05, power=0.80)
    assert res["n_per_variant"] > 0
    assert res["total_required"] == res["n_per_variant"] * 2

    # Achievable MDE
    mde_res = calculate_achievable_mde(baseline_cr=0.10, n_per_variant=50000)
    assert mde_res["achievable_rel_mde_pct"] > 0

    # Post-hoc
    post_hoc = calculate_post_hoc_power()
    assert 0.0 <= post_hoc["observed_power"] <= 1.0
    assert post_hoc["needed_n_per_variant"] > 0


def test_segmentation_guardrails():
    novelty = analyze_novelty_effect()
    assert len(novelty) == 3  # Week 1, Week 2, Week 3+
    
    daily_srm = audit_daily_srm()
    assert len(daily_srm) >= 21
    assert daily_srm["srm_flag"].sum() == 0, "Expected zero SRM anomalies in authentic dataset"
