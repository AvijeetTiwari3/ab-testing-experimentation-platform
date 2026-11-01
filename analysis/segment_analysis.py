"""
Analysis Module: Segmentation & Guardrail Experimentation Analysis
Performs temporal stability tests, novelty/primacy effect detection,
hourly/day-of-week segmentations, and daily SRM health auditing.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ab_testing.db"
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "ab_data.csv"


def load_session_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT f.session_id, f.user_id, f.converted, f.hour_of_day,
               u.assigned_group, u.landing_page,
               d.date_id, d.day_of_week, d.day_name, d.is_weekend, d.days_since_start
        FROM fact_sessions f
        JOIN dim_users u ON f.user_id = u.user_id
        JOIN dim_dates d ON f.date_id = d.date_id
    """, conn)
    conn.close()
    return df


def analyze_novelty_effect(df: pd.DataFrame = None):
    """
    Evaluates whether treatment experienced a novelty spike in early days
    followed by regression (a common failure mode in product A/B tests).
    """
    if df is None:
        df = load_session_data()

    # Bucket into 3 experiment phases
    def assign_phase(days):
        if days < 7:
            return "Week 1 (Days 0-6)"
        elif days < 14:
            return "Week 2 (Days 7-13)"
        else:
            return "Week 3+ (Days 14+)"

    df_copy = df.copy()
    df_copy["experiment_phase"] = df_copy["days_since_start"].apply(assign_phase)

    phase_agg = df_copy.groupby(["experiment_phase", "assigned_group"]).agg(
        sessions=("user_id", "count"),
        conversions=("converted", "sum")
    ).reset_index()

    phase_agg["conversion_rate"] = phase_agg["conversions"] / phase_agg["sessions"]

    # Pivot to compare relative lift across phases
    pivot = phase_agg.pivot(index="experiment_phase", columns="assigned_group", values="conversion_rate")
    pivot["abs_diff"] = pivot["treatment"] - pivot["control"]
    pivot["rel_lift_pct"] = (pivot["abs_diff"] / pivot["control"]) * 100

    return pivot.reset_index()


def analyze_hourly_patterns(df: pd.DataFrame = None):
    """
    Computes conversion rate and session distribution by hour of day (0-23).
    """
    if df is None:
        df = load_session_data()

    hourly = df.groupby(["hour_of_day", "assigned_group"]).agg(
        sessions=("user_id", "count"),
        conversions=("converted", "sum")
    ).reset_index()

    hourly["conversion_rate"] = hourly["conversions"] / hourly["sessions"]
    return hourly


def analyze_day_type(df: pd.DataFrame = None):
    """
    Computes weekend vs weekday segmentation.
    """
    if df is None:
        df = load_session_data()

    day_type = df.groupby(["is_weekend", "assigned_group"]).agg(
        sessions=("user_id", "count"),
        conversions=("converted", "sum")
    ).reset_index()

    day_type["day_category"] = day_type["is_weekend"].map({0: "Weekday (Mon-Fri)", 1: "Weekend (Sat-Sun)"})
    day_type["conversion_rate"] = day_type["conversions"] / day_type["sessions"]
    return day_type


def audit_daily_srm(df: pd.DataFrame = None):
    """
    Audits Sample Ratio Mismatch (SRM) on a daily level using Chi-Square Goodness of Fit.
    Flags any date where p < 0.01.
    """
    if df is None:
        df = load_session_data()

    daily_counts = df.groupby(["date_id", "assigned_group"]).size().unstack(fill_value=0)
    
    results = []
    for date_id, row in daily_counts.iterrows():
        c = row.get("control", 0)
        t = row.get("treatment", 0)
        total = c + t
        expected = [total / 2, total / 2]
        chi2, p_val = stats.chisquare([c, t], f_exp=expected)
        
        results.append({
            "date_id": date_id,
            "control_sessions": c,
            "treatment_sessions": t,
            "total_sessions": total,
            "chi2_stat": chi2,
            "p_value": p_val,
            "srm_flag": p_val < 0.01
        })

    return pd.DataFrame(results)


def print_summary():
    df = load_session_data()
    print("\n" + "=" * 80)
    print("SEGMENTATION & GUARDRAIL AUDIT REPORT")
    print("=" * 80)
    
    print("\n1. Novelty & Primacy Effect Across Timeline:")
    novelty = analyze_novelty_effect(df)
    print(novelty.to_string(index=False))

    print("\n2. Daily SRM Health Check:")
    daily_srm = audit_daily_srm(df)
    srm_flags = daily_srm["srm_flag"].sum()
    print(f"Total days audited: {len(daily_srm)} | Days with SRM anomaly (p < 0.01): {srm_flags}")

    print("\n3. Day Category (Weekday vs Weekend):")
    day_type = analyze_day_type(df)
    print(day_type[["day_category", "assigned_group", "sessions", "conversions", "conversion_rate"]].to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    print_summary()
