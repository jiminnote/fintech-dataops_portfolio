# 🔗 QuickPay 데이터 리니지 (Data Lineage)

> **목적**: 원천 데이터 → 지표까지의 변환 경로를 추적 가능하게 문서화

---

## 전체 리니지 다이어그램

```
[Raw Sources]           [Staging]            [Intermediate]         [Marts]              [Visualization]
                                                                    
 events (JSON)    ──▶  stg_events      ──▶  int_daily_active   ──▶ mart_daily_kpi  ──▶  Tableau: KPI 대시보드
                       │                    _users                  │
                       │               ──▶  int_funnel         ──▶ mart_funnel     ──▶  Tableau: 퍼널 분석
                       │                    _conversion             │
                       │               ──▶  int_user_cohort    ──▶ mart_retention  ──▶  Tableau: 리텐션 차트
                       │                                            │
 transactions    ──▶  stg_transactions ─────────────────────── ──▶ mart_revenue    ──▶  Tableau: 매출 대시보드
 (DB)                  │
                       │
 users (DB)      ──▶  stg_users ──────────────────────────────────┘
```

---

## 테이블별 리니지 상세

### Raw → Staging

| 원천 | 스테이징 모델 | 변환 내용 |
|---|---|---|
| events (JSON/Kafka) | `stg_events` | 타임존 변환 (UTC→KST), 필드명 표준화, 타입 캐스팅 |
| transactions (PostgreSQL) | `stg_transactions` | 금액 단위 표준화, 상태코드 매핑, null 처리 |
| users (PostgreSQL) | `stg_users` | PII 마스킹, 코호트 주차 계산, 테스트 계정 필터 |

### Staging → Intermediate

| 스테이징 | 중간 모델 | 변환 내용 |
|---|---|---|
| `stg_events` | `int_daily_active_users` | 일자별 DISTINCT user_id 집계, 봇 제외 |
| `stg_events` | `int_funnel_conversion` | 이벤트 시퀀스 → 퍼널 단계 매핑, 전환율 계산 |
| `stg_events` + `stg_users` | `int_user_cohort` | 가입주차 기준 코호트 생성, N-day 재방문 플래그 |

### Intermediate → Marts

| 중간 모델 | 마트 | 지표 | 소비자 |
|---|---|---|---|
| `int_daily_active_users` | `mart_daily_kpi` | DAU, MAU, WAU, Stickiness | 경영진, Growth팀 |
| `int_funnel_conversion` | `mart_funnel` | 퍼널 전환율, 이탈률 | Product팀 |
| `int_user_cohort` | `mart_retention` | D1~D30 리텐션 | Growth팀 |
| `stg_transactions` | `mart_revenue` | GMV, ARPPU, 수수료 매출 | Finance팀, Revenue팀 |

---

## 지표별 역추적 (Reverse Lineage)

### DAU 역추적
```
mart_daily_kpi.dau
  └── int_daily_active_users.unique_users
        └── stg_events (WHERE event_name = 'auth_login_completed')
              └── Raw events (Kafka topic: quickpay.events)
```

### ARPPU 역추적
```
mart_revenue.arppu
  ├── SUM(stg_transactions.fee)
  │     └── Raw transactions (PostgreSQL: public.transactions)
  └── COUNT(DISTINCT stg_transactions.user_id WHERE fee > 0)
        └── Raw transactions (PostgreSQL: public.transactions)
```

### D7 리텐션 역추적
```
mart_retention.d7_retention_rate
  └── int_user_cohort.retained_d7 / int_user_cohort.cohort_size
        ├── stg_events (로그인 이벤트)
        │     └── Raw events
        └── stg_users (가입일 기준)
              └── Raw users (PostgreSQL: public.users)
```

---

## 데이터 신선도 (Freshness) SLA

| 레이어 | 갱신 주기 | SLA | 지연 시 대응 |
|---|---|---|---|
| Raw → Staging | 매시간 | 1시간 이내 | 🟡 Slack 알림 |
| Staging → Intermediate | 일간 06:00 KST | 08:00 KST까지 | 🟡 Slack 알림 |
| Intermediate → Marts | 일간 06:30 KST | 09:00 KST까지 | 🔴 PagerDuty |
| Marts → Tableau | 일간 07:00 KST | 10:00 KST까지 | 🟡 Slack 알림 |
