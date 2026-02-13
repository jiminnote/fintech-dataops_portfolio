# 🏦 핀테크 DataOps 포트폴리오 — "토스페이 클론" 데이터 운영 체계

[https://jiminnote.github.io/fintech-dataops_portfolio/](https://jiminnote.github.io/fintech-dataops_portfolio/)

> **가상의 핀테크 서비스 "QuickPay"**(송금·결제·충전)를 대상으로  
> 서비스 로그 설계 → 지표 체계 정의 → 데이터 마트 구축 → 대시보드 시각화 → 품질 모니터링  
> 까지 **DataOps 전 주기**를 구현한 포트폴리오 프로젝트입니다.

---

## 📌 프로젝트 목적

| 역량 영역 | 보완 포인트 | 이 프로젝트에서 구현하는 것 |
|---|---|---|
| ① 로그 설계·수집·QA | 앱/서비스 로그 설계 경험 부재 | 핀테크 이벤트 로그 스키마 설계 + 수집 시뮬레이션 |
| ② 핵심 지표 정의·정합성 | 비즈니스 KPI 관리 경험 부재 | DAU, 전환율, 리텐션, ARPPU 등 지표 정의서 + dbt 모델 |
| ④ Tableau 시각화 | Tableau/Looker 경험 부재 | Tableau Public 대시보드 + 시각화 설계서 |
| 품질 모니터링 | 체계적 품질 관리 필요 | Great Expectations + Slack 알림 파이프라인 |

---

## 🏗 프로젝트 구조

```
fintech-dataops-portfolio/
│
├── README.md                          # 프로젝트 개요 (이 파일)
├── requirements.txt                   # Python 의존성
├── docker-compose.yml                 # PostgreSQL + Airflow 로컬 환경
│
├── 01_log_design/                     # ① 서비스 로그 설계
│   ├── event_taxonomy.md              # 이벤트 택소노미 (전체 이벤트 목록)
│   ├── log_schema.md                  # 로그 스키마 정의서
│   ├── event_schema.json              # JSON Schema 정의
│   └── sample_events.json             # 샘플 이벤트 데이터
│
├── 02_metrics_definition/             # ② 핵심 지표 정의
│   ├── metrics_dictionary.md          # 지표 정의서 (KPI Dictionary)
│   ├── metrics_tree.md                # 지표 트리 (Metrics Tree)
│   └── data_lineage.md               # 데이터 리니지 문서
│
├── 03_data_generation/                # 샘플 데이터 생성
│   ├── generate_events.py             # 이벤트 로그 생성기
│   ├── generate_transactions.py       # 거래 데이터 생성기
│   └── load_to_db.py                  # DB 적재 스크립트
│
├── 04_dbt_mart/                       # ⑤ dbt 데이터 마트
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/                   # 스테이징 모델
│   │   │   ├── stg_events.sql
│   │   │   ├── stg_transactions.sql
│   │   │   └── stg_users.sql
│   │   ├── intermediate/              # 중간 변환 모델
│   │   │   ├── int_daily_active_users.sql
│   │   │   ├── int_funnel_conversion.sql
│   │   │   └── int_user_cohort.sql
│   │   └── marts/                     # 최종 마트
│   │       ├── mart_daily_kpi.sql
│   │       ├── mart_retention.sql
│   │       ├── mart_revenue.sql
│   │       └── mart_funnel.sql
│   └── tests/                         # dbt 테스트
│       ├── assert_dau_positive.sql
│       └── assert_revenue_not_negative.sql
│
├── 05_sql_queries/                    # ③ SQL 지표 추출
│   ├── daily_active_users.sql
│   ├── conversion_funnel.sql
│   ├── retention_analysis.sql
│   ├── arppu_calculation.sql
│   └── anomaly_detection.sql
│
├── 06_tableau_dashboard/              # ④ Tableau 시각화
│   ├── dashboard_design.md            # 대시보드 설계서
│   ├── exports/                       # Tableau용 CSV 데이터
│   │   ├── daily_kpi.csv
│   │   ├── retention_cohort.csv
│   │   ├── funnel_data.csv
│   │   └── transaction_summary.csv
│   └── tableau_guide.md              # Tableau Public 게시 가이드
│
├── 07_data_quality/                   # 품질 모니터링
│   ├── great_expectations/
│   │   ├── great_expectations.yml
│   │   └── expectations/
│   │       ├── events_suite.json
│   │       └── transactions_suite.json
│   ├── slack_alert.py                 # Slack 알림 모듈
│   └── quality_dashboard.md           # 품질 대시보드 설계
│
└── 08_airflow_dags/                   # ⑥ 운영 자동화
    ├── dag_daily_metrics.py           # 일간 지표 파이프라인
    ├── dag_data_quality.py            # 품질 검증 DAG
    └── dag_tableau_refresh.py         # Tableau 데이터 갱신 DAG
```

---

## 🚀 Quick Start

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 샘플 데이터 생성
python 03_data_generation/generate_events.py
python 03_data_generation/generate_transactions.py

# 3. DB 적재 (SQLite 기본)
python 03_data_generation/load_to_db.py

# 4. dbt 모델 실행
cd 04_dbt_mart && dbt run && dbt test

# 5. Tableau용 CSV 내보내기
python 06_tableau_dashboard/export_tableau_data.py

# 6. 데이터 품질 검증
python 07_data_quality/run_quality_checks.py
```

---

## 🎯 핵심 성과 요약

| 항목 | 수치 |
|---|---|
| 설계한 이벤트 로그 | 28개 이벤트 × 12개 속성 |
| 정의한 KPI 지표 | 15개 (DAU, MAU, 전환율, 리텐션, ARPPU 등) |
| dbt 모델 수 | 10개 (staging 3 + intermediate 3 + mart 4) |
| SQL 분석 쿼리 | 5개 핵심 비즈니스 쿼리 |
| Tableau 대시보드 | 4개 시트 + 1개 인터랙티브 대시보드 |
| 데이터 품질 규칙 | 20+ Great Expectations 규칙 |
| 자동화 DAG | 3개 Airflow DAG |

---

## 📝 기술 스택

- **데이터 모델링**: dbt Core, SQL (PostgreSQL / DuckDB)
- **시각화**: Tableau Public
- **품질 관리**: Great Expectations, dbt test
- **자동화**: Apache Airflow
- **알림**: Slack Webhook
- **언어**: Python 3.10+, SQL
- **인프라**: Docker Compose (로컬 개발)

---

## 👤 Author

**지민** — DataOps Engineer  
IoT 데이터 파이프라인 & 대규모 SQL 운영 경험 기반,  
핀테크 서비스 데이터 운영 체계를 End-to-End로 구축한 프로젝트입니다.
