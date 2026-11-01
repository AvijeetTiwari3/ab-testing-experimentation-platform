"""
Pipeline Module: Data Transformation & Feature Engineering
Performs rigorous data hygiene, instrumentation mismatch detection,
time feature engineering, and cumulative metric calculations.
"""

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "ab_data.csv"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"
SUMMARY_DATA_PATH = BASE_DIR / "data" / "processed" / "experiment_summary.parquet"


def run_transformation():
    print(f"Reading raw experiment data from: {RAW_DATA_PATH}")
    df = pd.read_csv(RAW_DATA_PATH)
    total_raw_rows = len(df)
    print(f"Total raw records loaded: {total_raw_rows:,}")

    # 1. Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # 2. Instrumentation consistency check
    # In rigorous A/B testing, control users must see old_page, treatment users must see new_page
    df["consistency_flag"] = (
        ((df["group"] == "control") & (df["landing_page"] == "old_page")) |
        ((df["group"] == "treatment") & (df["landing_page"] == "new_page"))
    ).astype(int)

    mismatches = total_raw_rows - df["consistency_flag"].sum()
    print(f"Detected instrumentation mismatches: {mismatches:,} ({mismatches / total_raw_rows * 100:.2f}%)")

    # 3. Clean cohort extraction
    # Filter only consistent sessions
    df_clean = df[df["consistency_flag"] == 1].copy()

    # Deduplicate users: retain first recorded session per user
    user_dups_before = df_clean["user_id"].duplicated().sum()
    df_clean = df_clean.sort_values("timestamp").drop_duplicates(subset=["user_id"], keep="first").reset_index(drop=True)
    print(f"Deduplicated users removed: {user_dups_before:,}. Final clean user sessions: {len(df_clean):,}")

    # 4. Feature Engineering
    min_date = df_clean["timestamp"].dt.date.min()
    df_clean["session_date"] = df_clean["timestamp"].dt.strftime("%Y-%m-%d")
    df_clean["hour_of_day"] = df_clean["timestamp"].dt.hour.astype(int)
    df_clean["day_of_week"] = df_clean["timestamp"].dt.dayofweek.astype(int)
    df_clean["day_name"] = df_clean["timestamp"].dt.day_name()
    df_clean["is_weekend"] = (df_clean["day_of_week"] >= 5).astype(int)
    df_clean["days_since_start"] = (df_clean["timestamp"].dt.date - min_date).apply(lambda d: d.days).astype(int)
    
    df_clean["group_encoded"] = (df_clean["group"] == "treatment").astype(int)
    df_clean["landing_page_encoded"] = (df_clean["landing_page"] == "new_page").astype(int)
    df_clean["converted"] = df_clean["converted"].astype(int)

    # 5. Cumulative Daily Experiment Metrics
    daily_summary = df_clean.groupby(["session_date", "group"]).agg(
        sessions=("user_id", "count"),
        conversions=("converted", "sum")
    ).reset_index()

    daily_summary["conversion_rate"] = daily_summary["conversions"] / daily_summary["sessions"]
    
    # Calculate running cumulative totals
    daily_summary = daily_summary.sort_values(["group", "session_date"])
    daily_summary["cum_sessions"] = daily_summary.groupby("group")["sessions"].cumsum()
    daily_summary["cum_conversions"] = daily_summary.groupby("group")["conversions"].cumsum()
    daily_summary["cum_conversion_rate"] = daily_summary["cum_conversions"] / daily_summary["cum_sessions"]

    # Save outputs
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(PROCESSED_DATA_PATH, index=False)
    daily_summary.to_parquet(SUMMARY_DATA_PATH, index=False)

    print(f"Clean experiment dataset saved to: {PROCESSED_DATA_PATH} ({len(df_clean):,} rows)")
    print(f"Daily experiment summary saved to: {SUMMARY_DATA_PATH} ({len(daily_summary):,} rows)")

    return df_clean, daily_summary


if __name__ == "__main__":
    run_transformation()
