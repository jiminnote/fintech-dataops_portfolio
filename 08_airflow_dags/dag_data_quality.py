"""
Airflow DAG: 데이터 품질 검증 파이프라인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
매 6시간마다 데이터 품질을 점검하고 이상 시 알림을 발송합니다.
BranchPythonOperator를 활용한 조건부 알림 로직 포함.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "dataops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

dag = DAG(
    dag_id="quickpay_data_quality",
    default_args=default_args,
    description="QuickPay 데이터 품질 모니터링 (6시간 주기)",
    schedule_interval="0 */6 * * *",  # 매 6시간
    start_date=datetime(2025, 11, 15),
    catchup=False,
    tags=["quickpay", "quality", "monitoring"],
    max_active_runs=1,
)

# ━━━ Task 1: 이벤트 볼륨 체크 ━━━
check_event_volume = BashOperator(
    task_id="check_event_volume",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python -c "
import duckdb
from datetime import datetime, timedelta

con = duckdb.connect('data/quickpay.duckdb', read_only=True)

# 최근 24시간 이벤트 수
result = con.execute('''
    WITH daily_counts AS (
        SELECT 
            CAST(event_timestamp AS DATE) AS dt,
            COUNT(*) AS cnt
        FROM events
        GROUP BY 1
    ),
    stats AS (
        SELECT AVG(cnt) AS mean_cnt, STDDEV(cnt) AS std_cnt 
        FROM daily_counts
    )
    SELECT 
        d.dt, d.cnt, s.mean_cnt, s.std_cnt,
        ROUND((d.cnt - s.mean_cnt) / NULLIF(s.std_cnt, 0), 2) AS zscore
    FROM daily_counts d
    CROSS JOIN stats s
    ORDER BY d.dt DESC
    LIMIT 1
''').fetchone()

con.close()

dt, cnt, mean_cnt, std_cnt, zscore = result
print(f'Date: {dt}, Count: {cnt}, Mean: {mean_cnt:.0f}, Z-score: {zscore}')

if abs(zscore) > 3:
    raise ValueError(f'🚨 Event volume anomaly! Z-score: {zscore}')
else:
    print(f'✅ Event volume normal (Z-score: {zscore})')
"
    """,
    dag=dag,
)

# ━━━ Task 2: 거래 성공률 체크 ━━━
check_success_rate = BashOperator(
    task_id="check_success_rate",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python -c "
import duckdb

con = duckdb.connect('data/quickpay.duckdb', read_only=True)

# 최근 거래 성공률
result = con.execute('''
    SELECT
        ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) AS success_rate,
        COUNT(*) AS total
    FROM transactions
    WHERE CAST(created_at AS DATE) = (SELECT MAX(CAST(created_at AS DATE)) FROM transactions)
''').fetchone()

con.close()

success_rate, total = result
print(f'Success Rate: {success_rate}%, Total Txns: {total}')

if success_rate < 85:
    raise ValueError(f'🚨 Transaction success rate too low: {success_rate}%')
else:
    print(f'✅ Success rate OK ({success_rate}%)')
"
    """,
    dag=dag,
)

# ━━━ Task 3: 스키마 변경 감지 ━━━
check_schema_drift = BashOperator(
    task_id="check_schema_drift",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python -c "
import duckdb
import json
from pathlib import Path

con = duckdb.connect('data/quickpay.duckdb', read_only=True)

# 현재 스키마 추출
tables = ['events', 'transactions', 'users']
current_schema = {}

for table in tables:
    cols = con.execute(f'DESCRIBE {table}').fetchdf()
    current_schema[table] = {row['column_name']: row['column_type'] for _, row in cols.iterrows()}

con.close()

# 이전 스키마와 비교
schema_path = Path('data/schema_snapshot.json')
if schema_path.exists():
    with open(schema_path) as f:
        prev_schema = json.load(f)
    
    for table in tables:
        prev_cols = set(prev_schema.get(table, {}).keys())
        curr_cols = set(current_schema[table].keys())
        
        new_cols = curr_cols - prev_cols
        removed_cols = prev_cols - curr_cols
        
        if new_cols:
            print(f'⚠️ {table}: New columns detected: {new_cols}')
        if removed_cols:
            print(f'⚠️ {table}: Removed columns: {removed_cols}')
        if not new_cols and not removed_cols:
            print(f'✅ {table}: Schema unchanged')

# 현재 스키마 저장
with open(schema_path, 'w') as f:
    json.dump(current_schema, f, indent=2)
    
print('📸 Schema snapshot saved')
"
    """,
    dag=dag,
)

# ━━━ Task 4: 전체 품질 검증 실행 ━━━
run_full_quality_checks = BashOperator(
    task_id="run_full_quality_checks",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python 07_data_quality/run_quality_checks.py 2>&1
    """,
    dag=dag,
)

# ━━━ Task 5: 결과 분기 ━━━
def _decide_alert(**kwargs):
    """품질 점수에 따라 알림 수준 결정"""
    import json
    from pathlib import Path
    
    report_dir = Path("/opt/airflow/dags/fintech-dataops-portfolio/07_data_quality/reports")
    report_files = sorted(report_dir.glob("quality_report_*.json"))
    
    if not report_files:
        return "alert_critical"
    
    with open(report_files[-1]) as f:
        report = json.load(f)
    
    score = report["quality_score"]
    
    if score < 80:
        return "alert_critical"
    elif score < 90:
        return "alert_warning"
    else:
        return "no_alert"


decide_alert = BranchPythonOperator(
    task_id="decide_alert",
    python_callable=_decide_alert,
    dag=dag,
)

# ━━━ 알림 태스크들 ━━━
alert_critical = PythonOperator(
    task_id="alert_critical",
    python_callable=lambda: print("🔴 CRITICAL: Data quality score below 80%! Immediate action required."),
    dag=dag,
)

alert_warning = PythonOperator(
    task_id="alert_warning",
    python_callable=lambda: print("🟡 WARNING: Data quality score below 90%. Review within business hours."),
    dag=dag,
)

no_alert = EmptyOperator(
    task_id="no_alert",
    dag=dag,
)

# 합류 지점
quality_check_done = EmptyOperator(
    task_id="quality_check_done",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

# ━━━ DAG 의존성 ━━━
# 병렬 실행: 볼륨 + 성공률 + 스키마
[check_event_volume, check_success_rate, check_schema_drift] >> run_full_quality_checks

# 분기
run_full_quality_checks >> decide_alert
decide_alert >> [alert_critical, alert_warning, no_alert]
[alert_critical, alert_warning, no_alert] >> quality_check_done
