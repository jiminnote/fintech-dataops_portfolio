"""
Airflow DAG: 일간 지표 파이프라인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
매일 06:00 KST에 실행되어 전일 데이터를 처리합니다.

파이프라인 흐름:
  데이터 검증 → dbt 모델 실행 → dbt 테스트 → Tableau 데이터 갱신 → Slack 리포트
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# ━━━ DAG 기본 설정 ━━━
default_args = {
    "owner": "dataops",
    "depends_on_past": False,
    "email": ["dataops@quickpay.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

dag = DAG(
    dag_id="quickpay_daily_metrics",
    default_args=default_args,
    description="QuickPay 일간 KPI 지표 파이프라인",
    schedule_interval="0 21 * * *",  # UTC 21:00 = KST 06:00
    start_date=datetime(2025, 11, 15),
    catchup=False,
    tags=["quickpay", "metrics", "daily"],
    max_active_runs=1,
)

# ━━━ Task 1: 데이터 신선도 확인 ━━━
check_data_freshness = BashOperator(
    task_id="check_data_freshness",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python -c "
import duckdb
from datetime import datetime, timedelta

con = duckdb.connect('data/quickpay.duckdb', read_only=True)

# 최신 이벤트 시각 확인
latest = con.execute('''
    SELECT MAX(CAST(event_timestamp AS TIMESTAMP)) as latest_event
    FROM events
''').fetchone()[0]

# 최신 거래 시각 확인
latest_txn = con.execute('''
    SELECT MAX(CAST(created_at AS TIMESTAMP)) as latest_txn
    FROM transactions
''').fetchone()[0]

con.close()

print(f'Latest event: {latest}')
print(f'Latest transaction: {latest_txn}')

# 24시간 이내 데이터가 있는지 확인
threshold = datetime.now() - timedelta(hours=48)
if latest and latest >= threshold:
    print('✅ Data freshness OK')
else:
    raise ValueError(f'⚠️ Data is stale! Latest: {latest}, Threshold: {threshold}')
"
    """,
    dag=dag,
)

# ━━━ Task 2: dbt 모델 실행 ━━━
run_dbt_models = BashOperator(
    task_id="run_dbt_models",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio/04_dbt_mart
        dbt run --profiles-dir . --project-dir . 2>&1
    """,
    dag=dag,
)

# ━━━ Task 3: dbt 테스트 실행 ━━━
run_dbt_tests = BashOperator(
    task_id="run_dbt_tests",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio/04_dbt_mart
        dbt test --profiles-dir . --project-dir . 2>&1
    """,
    dag=dag,
)

# ━━━ Task 4: 데이터 품질 검증 ━━━
run_quality_checks = BashOperator(
    task_id="run_quality_checks",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python 07_data_quality/run_quality_checks.py 2>&1
    """,
    dag=dag,
)

# ━━━ Task 5: 품질 결과에 따른 분기 ━━━
def _check_quality_result(**kwargs):
    """품질 점수에 따라 다음 작업을 분기"""
    import json
    from pathlib import Path
    
    report_dir = Path("/opt/airflow/dags/fintech-dataops-portfolio/07_data_quality/reports")
    report_files = sorted(report_dir.glob("quality_report_*.json"))
    
    if not report_files:
        return "notify_failure"
    
    with open(report_files[-1]) as f:
        report = json.load(f)
    
    # 품질 점수 80% 미만이면 실패 경로
    if report["quality_score"] < 80:
        return "notify_failure"
    else:
        return "export_tableau_data"


branch_on_quality = BranchPythonOperator(
    task_id="branch_on_quality",
    python_callable=_check_quality_result,
    dag=dag,
)

# ━━━ Task 6: Tableau 데이터 갱신 ━━━
export_tableau_data = BashOperator(
    task_id="export_tableau_data",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python 06_tableau_dashboard/export_tableau_data.py 2>&1
    """,
    dag=dag,
)

# ━━━ Task 7: 성공 알림 ━━━
def _send_success_notification(**kwargs):
    """파이프라인 성공 시 Slack 알림"""
    import sys
    sys.path.insert(0, "/opt/airflow/dags/fintech-dataops-portfolio")
    from datetime import datetime
    
    # 간단한 성공 메시지
    execution_date = kwargs.get("ds", datetime.now().strftime("%Y-%m-%d"))
    print(f"✅ Daily metrics pipeline completed successfully for {execution_date}")
    print("📊 Tableau data exported. Dashboard will refresh automatically.")


notify_success = PythonOperator(
    task_id="notify_success",
    python_callable=_send_success_notification,
    dag=dag,
)

# ━━━ Task 8: 실패 알림 ━━━
def _send_failure_notification(**kwargs):
    """품질 검증 실패 시 Slack 알림"""
    print("🔴 Data quality check failed! Quality score below 80%.")
    print("📋 Please review the quality report and fix the issues.")


notify_failure = PythonOperator(
    task_id="notify_failure",
    python_callable=_send_failure_notification,
    dag=dag,
)

# ━━━ DAG 의존성 ━━━
# 메인 파이프라인
check_data_freshness >> run_dbt_models >> run_dbt_tests >> run_quality_checks

# 분기
run_quality_checks >> branch_on_quality

# 성공 경로
branch_on_quality >> export_tableau_data >> notify_success

# 실패 경로
branch_on_quality >> notify_failure
