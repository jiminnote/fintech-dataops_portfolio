"""
Airflow DAG: Tableau 데이터 갱신 파이프라인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
일간 지표 파이프라인 완료 후 Tableau용 CSV를 갱신하고
Tableau Server/Online의 Extract를 리프레시합니다.
(Tableau Public 사용 시에는 수동 업로드가 필요합니다)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

default_args = {
    "owner": "dataops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="quickpay_tableau_refresh",
    default_args=default_args,
    description="Tableau 데이터 갱신 (daily_metrics DAG 완료 후 실행)",
    schedule_interval="0 22 * * *",  # UTC 22:00 = KST 07:00 (daily_metrics 1시간 후)
    start_date=datetime(2025, 11, 15),
    catchup=False,
    tags=["quickpay", "tableau", "visualization"],
    max_active_runs=1,
)

# ━━━ Task 1: 일간 지표 DAG 완료 대기 ━━━
wait_for_daily_metrics = ExternalTaskSensor(
    task_id="wait_for_daily_metrics",
    external_dag_id="quickpay_daily_metrics",
    external_task_id="notify_success",
    execution_delta=timedelta(hours=1),  # 1시간 전 DAG
    timeout=3600,  # 최대 1시간 대기
    poke_interval=60,  # 1분마다 확인
    mode="reschedule",
    dag=dag,
)

# ━━━ Task 2: Tableau CSV 내보내기 ━━━
export_csv = BashOperator(
    task_id="export_tableau_csv",
    bash_command="""
        cd /opt/airflow/dags/fintech-dataops-portfolio
        python 06_tableau_dashboard/export_tableau_data.py 2>&1
        
        # 파일 크기 및 행 수 검증
        for f in 06_tableau_dashboard/exports/*.csv; do
            rows=$(wc -l < "$f")
            size=$(du -h "$f" | cut -f1)
            echo "📁 $(basename $f): ${rows} rows, ${size}"
            
            if [ "$rows" -lt 2 ]; then
                echo "❌ ERROR: $f has no data rows!"
                exit 1
            fi
        done
        
        echo "✅ All Tableau CSV files exported successfully"
    """,
    dag=dag,
)

# ━━━ Task 3: 데이터 검증 (Tableau 공급 데이터 정합성) ━━━
def _validate_tableau_data(**kwargs):
    """Tableau CSV의 기본 정합성 검증"""
    import pandas as pd
    from pathlib import Path
    
    export_dir = Path("/opt/airflow/dags/fintech-dataops-portfolio/06_tableau_dashboard/exports")
    
    # daily_kpi.csv 검증
    daily = pd.read_csv(export_dir / "daily_kpi.csv")
    assert len(daily) > 0, "daily_kpi.csv is empty"
    assert daily["dau"].min() > 0, "DAU has zero or negative values"
    assert daily["gmv"].min() >= 0, "GMV has negative values"
    print(f"✅ daily_kpi.csv: {len(daily)} rows, DAU range [{daily['dau'].min()}, {daily['dau'].max()}]")
    
    # retention_cohort.csv 검증
    retention = pd.read_csv(export_dir / "retention_cohort.csv")
    assert len(retention) > 0, "retention_cohort.csv is empty"
    assert retention["retention_rate"].max() <= 100, "Retention rate exceeds 100%"
    print(f"✅ retention_cohort.csv: {len(retention)} rows")
    
    # funnel_data.csv 검증
    funnel = pd.read_csv(export_dir / "funnel_data.csv")
    assert len(funnel) == 6, f"funnel should have 6 steps, got {len(funnel)}"
    assert funnel.iloc[0]["pct_from_start"] == 100.0, "First funnel step should be 100%"
    print(f"✅ funnel_data.csv: {len(funnel)} steps")
    
    # transaction_summary.csv 검증
    txn = pd.read_csv(export_dir / "transaction_summary.csv")
    assert len(txn) > 0, "transaction_summary.csv is empty"
    assert txn["total_amount"].min() >= 0, "Negative total_amount found"
    print(f"✅ transaction_summary.csv: {len(txn)} rows")
    
    print("\n✅ All Tableau data validation passed!")


validate_data = PythonOperator(
    task_id="validate_tableau_data",
    python_callable=_validate_tableau_data,
    dag=dag,
)

# ━━━ Task 4: 완료 알림 ━━━
def _notify_tableau_refresh(**kwargs):
    """Tableau 데이터 갱신 완료 알림"""
    execution_date = kwargs.get("ds", "unknown")
    print(f"📊 Tableau data refresh completed for {execution_date}")
    print("📌 Tableau Public 사용 시: 수동으로 데이터 소스를 업데이트하세요.")
    print("📌 Tableau Server 사용 시: Hyper 파일이 자동 갱신되었습니다.")


notify_refresh = PythonOperator(
    task_id="notify_tableau_refresh",
    python_callable=_notify_tableau_refresh,
    dag=dag,
)

# ━━━ DAG 의존성 ━━━
wait_for_daily_metrics >> export_csv >> validate_data >> notify_refresh
