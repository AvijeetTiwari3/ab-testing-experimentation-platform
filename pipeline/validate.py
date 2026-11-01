"""
Pipeline Module: Automated Data Quality & Experimentation Integrity Validation
Executes 10 rigorous checks on schema, distributions, SRM, and business constraints.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ab_testing.db"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"


def run_validation():
    print(f"Validating database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    df = pd.read_sql_query("""
        SELECT f.session_id, f.user_id, f.converted, f.hour_of_day,
               u.assigned_group, u.landing_page,
               d.date_id, d.day_of_week, d.is_weekend, d.days_since_start
        FROM fact_sessions f
        JOIN dim_users u ON f.user_id = u.user_id
        JOIN dim_dates d ON f.date_id = d.date_id
    """, conn)
    conn.close()

    checks = []

    # Check 1: Record volume
    row_count = len(df)
    c1 = row_count >= 290000
    checks.append(("Check 01: Clean session count >= 290,000", c1, f"{row_count:,} records"))

    # Check 2: Null values
    null_count = df.isnull().sum().sum()
    c2 = null_count == 0
    checks.append(("Check 02: Zero null values across all dimensions", c2, f"{null_count} nulls"))

    # Check 3: Valid groups
    allowed_groups = {"control", "treatment"}
    observed_groups = set(df["assigned_group"].unique())
    c3 = observed_groups.issubset(allowed_groups)
    checks.append(("Check 03: Assigned groups strictly within {control, treatment}", c3, f"{observed_groups}"))

    # Check 4: Valid landing pages
    allowed_pages = {"old_page", "new_page"}
    observed_pages = set(df["landing_page"].unique())
    c4 = observed_pages.issubset(allowed_pages)
    checks.append(("Check 04: Landing pages strictly within {old_page, new_page}", c4, f"{observed_pages}"))

    # Check 5: Conversion binary domain
    unique_conversions = set(df["converted"].unique())
    c5 = unique_conversions.issubset({0, 1})
    checks.append(("Check 05: Conversion indicator strictly binary {0, 1}", c5, f"{unique_conversions}"))

    # Check 6: User deduplication
    duplicate_users = df["user_id"].duplicated().sum()
    c6 = duplicate_users == 0
    checks.append(("Check 06: Zero duplicate users in clean cohort", c6, f"{duplicate_users} duplicates"))

    # Check 7: Sample Ratio Mismatch (SRM)
    n_control = (df["assigned_group"] == "control").sum()
    n_treatment = (df["assigned_group"] == "treatment").sum()
    observed_counts = [n_control, n_treatment]
    expected_counts = [len(df) / 2, len(df) / 2]
    chi2_stat, srm_p_value = stats.chisquare(f_obs=observed_counts, f_exp=expected_counts)
    c7 = srm_p_value > 0.01  # If p < 0.01, severe SRM exists
    checks.append(("Check 07: SRM Check (Sample Ratio Mismatch Chi2 test)", c7, 
                   f"Control={n_control:,}, Treat={n_treatment:,}, Chi2={chi2_stat:.4f}, p={srm_p_value:.4f}"))

    # Check 8: Control consistency
    control_mismatches = ((df["assigned_group"] == "control") & (df["landing_page"] != "old_page")).sum()
    c8 = control_mismatches == 0
    checks.append(("Check 08: 100% of Control group exposed to old_page", c8, f"{control_mismatches} mismatches"))

    # Check 9: Treatment consistency
    treatment_mismatches = ((df["assigned_group"] == "treatment") & (df["landing_page"] != "new_page")).sum()
    c9 = treatment_mismatches == 0
    checks.append(("Check 09: 100% of Treatment group exposed to new_page", c9, f"{treatment_mismatches} mismatches"))

    # Check 10: Experiment time duration
    unique_dates = df["date_id"].nunique()
    c10 = unique_dates >= 21
    checks.append(("Check 10: Experiment runs for at least 21 days", c10, f"{unique_dates} active days"))

    print("\n" + "=" * 80)
    print("DATA QUALITY & EXPERIMENTATION INTEGRITY VALIDATION SUITE")
    print("=" * 80)
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"[{status}] {name} -> {detail}")
    print("=" * 80)

    if all_passed:
        print("ALL 10 VALIDATION CHECKS PASSED SUCCESSFULLY!")
    else:
        print("SOME VALIDATION CHECKS FAILED.")

    return all_passed, checks


if __name__ == "__main__":
    passed, _ = run_validation()
    if not passed:
        exit(1)
