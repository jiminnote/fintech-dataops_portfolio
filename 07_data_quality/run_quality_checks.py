"""
QuickPay 데이터 품질 검증 실행기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DuckDB 데이터에 대해 품질 검증 규칙을 실행하고 결과를 리포트합니다.
Great Expectations 없이도 독립 실행 가능한 경량 버전입니다.
"""

import json
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "quickpay.duckdb"
REPORT_DIR = Path(__file__).parent / "reports"


class QualityCheck:
    """데이터 품질 검증 규칙"""
    
    def __init__(self, name: str, query: str, expectation: str, severity: str = "warning"):
        self.name = name
        self.query = query
        self.expectation = expectation
        self.severity = severity  # "critical" or "warning"
        self.passed = None
        self.details = None
    
    def run(self, con: duckdb.DuckDBPyConnection) -> bool:
        try:
            result = con.execute(self.query).fetchdf()
            if len(result) == 0:
                self.passed = True
                self.details = "No violations found"
            else:
                self.passed = False
                self.details = f"{len(result)} violations found"
                self.violations = result
            return self.passed
        except Exception as e:
            self.passed = False
            self.details = f"Error: {str(e)}"
            return False


def define_quality_checks() -> list[QualityCheck]:
    """품질 검증 규칙 정의"""
    return [
        # ━━━ Events 테이블 ━━━
        QualityCheck(
            name="events_not_null_event_id",
            query="SELECT * FROM events WHERE event_id IS NULL LIMIT 10",
            expectation="event_id should never be NULL",
            severity="critical"
        ),
        QualityCheck(
            name="events_unique_event_id",
            query="""
                SELECT event_id, COUNT(*) AS cnt 
                FROM events 
                GROUP BY 1 HAVING COUNT(*) > 1 
                LIMIT 10
            """,
            expectation="event_id should be unique (no duplicates)",
            severity="critical"
        ),
        QualityCheck(
            name="events_valid_event_name",
            query="""
                SELECT DISTINCT event_name 
                FROM events 
                WHERE event_name NOT IN (
                    'auth_signup_started', 'auth_signup_submitted', 'auth_signup_completed',
                    'auth_login_attempted', 'auth_login_completed', 'auth_identity_verified',
                    'payment_transfer_started', 'payment_transfer_amount_entered',
                    'payment_transfer_confirmed', 'payment_transfer_completed', 'payment_transfer_failed',
                    'payment_charge_completed', 'payment_withdraw_completed',
                    'payment_qr_scanned', 'payment_qr_completed',
                    'product_list_viewed', 'product_detail_viewed', 'product_compared',
                    'product_applied', 'product_application_completed',
                    'screen_viewed', 'screen_exited', 'screen_tab_clicked',
                    'screen_banner_clicked', 'screen_search_performed',
                    'system_error_occurred', 'system_push_received', 'system_push_clicked'
                )
            """,
            expectation="event_name should be in the defined taxonomy",
            severity="critical"
        ),
        QualityCheck(
            name="events_valid_platform",
            query="SELECT DISTINCT platform FROM events WHERE platform NOT IN ('ios', 'android', 'web')",
            expectation="platform should be ios, android, or web",
            severity="warning"
        ),
        QualityCheck(
            name="events_not_null_timestamp",
            query="SELECT * FROM events WHERE event_timestamp IS NULL LIMIT 10",
            expectation="event_timestamp should never be NULL",
            severity="critical"
        ),
        QualityCheck(
            name="events_null_rate_user_id",
            query="""
                SELECT 
                    ROUND(SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS null_pct
                FROM events
                HAVING null_pct > 5
            """,
            expectation="user_id null rate should be less than 5%",
            severity="warning"
        ),
        
        # ━━━ Transactions 테이블 ━━━
        QualityCheck(
            name="txn_not_null_transaction_id",
            query="SELECT * FROM transactions WHERE transaction_id IS NULL LIMIT 10",
            expectation="transaction_id should never be NULL",
            severity="critical"
        ),
        QualityCheck(
            name="txn_unique_transaction_id",
            query="""
                SELECT transaction_id, COUNT(*) AS cnt 
                FROM transactions 
                GROUP BY 1 HAVING COUNT(*) > 1 
                LIMIT 10
            """,
            expectation="transaction_id should be unique",
            severity="critical"
        ),
        QualityCheck(
            name="txn_positive_amount",
            query="SELECT * FROM transactions WHERE amount <= 0 LIMIT 10",
            expectation="amount should be positive",
            severity="critical"
        ),
        QualityCheck(
            name="txn_non_negative_fee",
            query="SELECT * FROM transactions WHERE fee < 0 LIMIT 10",
            expectation="fee should be non-negative",
            severity="critical"
        ),
        QualityCheck(
            name="txn_valid_status",
            query="""
                SELECT DISTINCT status 
                FROM transactions 
                WHERE status NOT IN ('completed', 'failed', 'pending', 'cancelled')
            """,
            expectation="status should be in the valid set",
            severity="critical"
        ),
        QualityCheck(
            name="txn_valid_type",
            query="""
                SELECT DISTINCT transaction_type 
                FROM transactions 
                WHERE transaction_type NOT IN ('transfer', 'qr_payment', 'charge', 'withdraw')
            """,
            expectation="transaction_type should be in the valid set",
            severity="warning"
        ),
        QualityCheck(
            name="txn_amount_gte_fee",
            query="SELECT * FROM transactions WHERE amount < fee LIMIT 10",
            expectation="amount should always be >= fee",
            severity="warning"
        ),
        
        # ━━━ Cross-table 정합성 ━━━
        QualityCheck(
            name="txn_users_exist",
            query="""
                SELECT DISTINCT t.user_id 
                FROM transactions t 
                LEFT JOIN users u ON t.user_id = u.user_id 
                WHERE u.user_id IS NULL
                LIMIT 10
            """,
            expectation="All transaction user_ids should exist in users table",
            severity="warning"
        ),
        
        # ━━━ 볼륨 이상 탐지 ━━━
        QualityCheck(
            name="events_daily_volume_anomaly",
            query="""
                WITH daily AS (
                    SELECT CAST(event_timestamp AS DATE) AS dt, COUNT(*) AS cnt
                    FROM events GROUP BY 1
                ),
                stats AS (
                    SELECT AVG(cnt) AS mean_cnt, STDDEV(cnt) AS std_cnt FROM daily
                )
                SELECT d.dt, d.cnt, s.mean_cnt, 
                       ROUND((d.cnt - s.mean_cnt) / NULLIF(s.std_cnt, 0), 2) AS zscore
                FROM daily d CROSS JOIN stats s
                WHERE ABS((d.cnt - s.mean_cnt) / NULLIF(s.std_cnt, 0)) > 3
            """,
            expectation="Daily event volume should not deviate more than 3 std from mean",
            severity="warning"
        ),
    ]


def run_quality_checks():
    """모든 품질 검증 실행"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    con = duckdb.connect(str(DB_PATH), read_only=True)
    checks = define_quality_checks()
    
    print("🔍 QuickPay 데이터 품질 검증 시작")
    print(f"   DB: {DB_PATH}")
    print(f"   검증 규칙: {len(checks)}개\n")
    
    results = []
    passed_count = 0
    failed_count = 0
    
    for check in checks:
        success = check.run(con)
        status_icon = "✅" if success else ("🔴" if check.severity == "critical" else "🟡")
        print(f"   {status_icon} {check.name}: {check.details}")
        
        if success:
            passed_count += 1
        else:
            failed_count += 1
        
        results.append({
            "check_name": check.name,
            "expectation": check.expectation,
            "severity": check.severity,
            "passed": success,
            "details": check.details,
            "run_at": datetime.now().isoformat(),
        })
    
    con.close()
    
    # 결과 요약
    total = len(checks)
    print(f"\n{'='*50}")
    print(f"📋 품질 검증 결과 요약")
    print(f"   전체: {total}개 | ✅ 통과: {passed_count}개 | ❌ 실패: {failed_count}개")
    print(f"   품질 점수: {passed_count / total * 100:.1f}%")
    
    # JSON 리포트 저장
    report = {
        "run_timestamp": datetime.now().isoformat(),
        "total_checks": total,
        "passed": passed_count,
        "failed": failed_count,
        "quality_score": round(passed_count / total * 100, 1),
        "results": results,
    }
    
    report_path = REPORT_DIR / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 리포트 저장: {report_path}")
    
    return report


if __name__ == "__main__":
    report = run_quality_checks()
    
    # 실패한 검증이 있으면 Slack 알림 발송 (옵션)
    if report["failed"] > 0:
        print("\n⚠️  실패한 검증이 있습니다. Slack 알림을 발송하려면:")
        print("   python 07_data_quality/slack_alert.py")
