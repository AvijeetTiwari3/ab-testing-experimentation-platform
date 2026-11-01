"""
Test Suite: Data Pipeline & Warehouse Validation
"""

from pathlib import Path
import sys
import sqlite3
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
DB_PATH = BASE_DIR / "data" / "ab_testing.db"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"


def test_processed_dataset_exists_and_valid():
    assert PROCESSED_DATA_PATH.exists(), f"Processed parquet file missing at {PROCESSED_DATA_PATH}"
    df = pd.read_parquet(PROCESSED_DATA_PATH)
    assert len(df) >= 290000, f"Expected at least 290,000 clean records, got {len(df)}"
    assert set(df["group"].unique()) == {"control", "treatment"}
    assert set(df["converted"].unique()).issubset({0, 1})
    assert df["user_id"].duplicated().sum() == 0, "Duplicate users found in clean cohort"


def test_sqlite_warehouse_integrity():
    assert DB_PATH.exists(), f"Database file missing at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cursor.fetchall()}
    expected_tables = {"dim_users", "dim_dates", "fact_sessions", "agg_daily_metrics"}
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    # Check row counts
    cursor.execute("SELECT COUNT(*) FROM fact_sessions;")
    fact_count = cursor.fetchone()[0]
    assert fact_count >= 290000, f"Fact sessions row count too low: {fact_count}"

    cursor.execute("SELECT COUNT(*) FROM dim_dates;")
    date_count = cursor.fetchone()[0]
    assert date_count >= 21, f"Expected at least 21 days, got {date_count}"

    conn.close()


def test_validation_suite_passes():
    from pipeline.validate import run_validation
    passed, checks = run_validation()
    assert passed is True, "Validation suite failed one or more checks"
    assert len(checks) == 10, f"Expected 10 validation checks, got {len(checks)}"
