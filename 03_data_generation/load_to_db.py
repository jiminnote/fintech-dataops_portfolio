"""
QuickPay DB 적재 스크립트
━━━━━━━━━━━━━━━━━━━━━━━━
CSV 데이터를 DuckDB(로컬 분석용)에 적재합니다.
DuckDB는 설치 없이 SQL 분석이 가능하여 포트폴리오 시연에 최적화되어 있습니다.
"""

from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "quickpay.duckdb"


def load_to_duckdb():
    """CSV 데이터를 DuckDB에 적재"""
    con = duckdb.connect(str(DB_PATH))
    
    # ━━━ 사용자 테이블 ━━━
    print("👤 users 테이블 적재...")
    con.execute("""
        CREATE OR REPLACE TABLE users AS
        SELECT
            user_id,
            device_id,
            platform,
            device_model,
            CAST(signup_date AS DATE) as signup_date,
            signup_method,
            DATE_PART('week', CAST(signup_date AS DATE)) as signup_week,
            DATE_TRUNC('month', CAST(signup_date AS DATE)) as signup_month
        FROM read_csv_auto(?)
    """, [str(DATA_DIR / "users.csv")])
    count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f"   ✅ {count:,}건")
    
    # ━━━ 이벤트 테이블 ━━━
    print("📊 events 테이블 적재...")
    con.execute("""
        CREATE OR REPLACE TABLE events AS
        SELECT * FROM read_csv_auto(?)
    """, [str(DATA_DIR / "events.csv")])
    count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"   ✅ {count:,}건")
    
    # ━━━ 거래 테이블 ━━━
    print("💳 transactions 테이블 적재...")
    con.execute("""
        CREATE OR REPLACE TABLE transactions AS
        SELECT
            transaction_id,
            user_id,
            transaction_type,
            CAST(amount AS BIGINT) as amount,
            CAST(fee AS BIGINT) as fee,
            currency,
            status,
            bank_code,
            bank_name,
            CAST(created_at AS TIMESTAMP) as created_at,
            CAST(completed_at AS TIMESTAMP) as completed_at,
            error_code,
            merchant_id,
            merchant_category
        FROM read_csv_auto(?)
    """, [str(DATA_DIR / "transactions.csv")])
    count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"   ✅ {count:,}건")
    
    # ━━━ 인덱스 및 통계 ━━━
    print("\n📋 테이블 요약:")
    for table in ["users", "events", "transactions"]:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cols = con.execute(f"SELECT * FROM {table} LIMIT 0").description
        print(f"   {table}: {count:,}건, {len(cols)}개 컬럼")
    
    con.close()
    print(f"\n💾 DB 저장: {DB_PATH}")
    print(f"   크기: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    load_to_duckdb()
