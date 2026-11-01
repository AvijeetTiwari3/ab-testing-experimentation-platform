"""
Pipeline Module: SQLite Star Schema Warehouse Ingestion
Loads processed experiment data into a relational star schema
for analytical querying and validation.
"""

from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "ab_clean.parquet"
DB_PATH = BASE_DIR / "data" / "ab_testing.db"


def run_ingestion():
    print(f"Reading processed data from: {PROCESSED_DATA_PATH}")
    df = pd.read_parquet(PROCESSED_DATA_PATH)

    print(f"Connecting to SQLite database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables
    cursor.executescript("""
    DROP TABLE IF EXISTS fact_sessions;
    DROP TABLE IF EXISTS dim_users;
    DROP TABLE IF EXISTS dim_dates;
    DROP TABLE IF EXISTS agg_daily_metrics;

    CREATE TABLE dim_users (
        user_id INTEGER PRIMARY KEY,
        assigned_group TEXT NOT NULL,
        landing_page TEXT NOT NULL,
        first_seen_timestamp TEXT NOT NULL
    );

    CREATE TABLE dim_dates (
        date_id TEXT PRIMARY KEY,
        day_of_week INTEGER NOT NULL,
        day_name TEXT NOT NULL,
        is_weekend INTEGER NOT NULL,
        days_since_start INTEGER NOT NULL
    );

    CREATE TABLE fact_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date_id TEXT NOT NULL,
        converted INTEGER NOT NULL,
        hour_of_day INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES dim_users (user_id),
        FOREIGN KEY (date_id) REFERENCES dim_dates (date_id)
    );

    CREATE TABLE agg_daily_metrics (
        date_id TEXT NOT NULL,
        assigned_group TEXT NOT NULL,
        sessions INTEGER NOT NULL,
        conversions INTEGER NOT NULL,
        conversion_rate REAL NOT NULL,
        cum_sessions INTEGER NOT NULL,
        cum_conversions INTEGER NOT NULL,
        cum_conversion_rate REAL NOT NULL,
        PRIMARY KEY (date_id, assigned_group)
    );
    """)

    # 1. Populate dim_users
    dim_users = df[["user_id", "group", "landing_page", "timestamp"]].copy()
    dim_users.columns = ["user_id", "assigned_group", "landing_page", "first_seen_timestamp"]
    dim_users["first_seen_timestamp"] = dim_users["first_seen_timestamp"].astype(str)
    dim_users.to_sql("dim_users", conn, if_exists="append", index=False)
    print(f"dim_users populated: {len(dim_users):,} records")

    # 2. Populate dim_dates
    dim_dates = df[["session_date", "day_of_week", "day_name", "is_weekend", "days_since_start"]].drop_duplicates().copy()
    dim_dates.columns = ["date_id", "day_of_week", "day_name", "is_weekend", "days_since_start"]
    dim_dates = dim_dates.sort_values("date_id")
    dim_dates.to_sql("dim_dates", conn, if_exists="append", index=False)
    print(f"dim_dates populated: {len(dim_dates):,} records")

    # 3. Populate fact_sessions
    fact_sessions = df[["user_id", "session_date", "converted", "hour_of_day"]].copy()
    fact_sessions.columns = ["user_id", "date_id", "converted", "hour_of_day"]
    fact_sessions.to_sql("fact_sessions", conn, if_exists="append", index=False)
    print(f"fact_sessions populated: {len(fact_sessions):,} records")

    # 4. Populate agg_daily_metrics
    summary_path = BASE_DIR / "data" / "processed" / "experiment_summary.parquet"
    if summary_path.exists():
        daily_summary = pd.read_parquet(summary_path)
        daily_summary = daily_summary.rename(columns={"session_date": "date_id", "group": "assigned_group"})
        daily_summary.to_sql("agg_daily_metrics", conn, if_exists="append", index=False)
        print(f"agg_daily_metrics populated: {len(daily_summary):,} records")

    # Create indexes for analytical speed
    cursor.execute("CREATE INDEX idx_fact_user ON fact_sessions(user_id);")
    cursor.execute("CREATE INDEX idx_fact_date ON fact_sessions(date_id);")
    cursor.execute("CREATE INDEX idx_user_group ON dim_users(assigned_group);")
    conn.commit()
    conn.close()

    print(f"SQLite warehouse successfully created at: {DB_PATH}")


if __name__ == "__main__":
    run_ingestion()
