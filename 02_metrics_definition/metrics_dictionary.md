# 📊 QuickPay KPI 지표 정의서 (Metrics Dictionary)

> **목적**: 서비스 핵심 지표를 명확히 정의하여 조직 전체가 동일한 기준으로 데이터를 해석  
> **적용 범위**: QuickPay 송금·결제·충전 서비스  
> **버전**: v1.0 | 최종 수정: 2026-02-12  
> **승인**: DataOps팀 → PO → 경영진

---

## 📌 지표 분류 체계

```
Level 0: North Star Metric (NSM)
  └── Level 1: 핵심 KPI (5개)
        └── Level 2: 운영 지표 (10개)
              └── Level 3: 진단 지표 (다수)
```

---

## ⭐ North Star Metric

| 항목 | 내용 |
|---|---|
| **지표명** | 주간 활성 송금 사용자 수 (Weekly Active Senders) |
| **정의** | 최근 7일간 1회 이상 송금을 완료한 고유 사용자 수 |
| **산출식** | `COUNT(DISTINCT user_id) WHERE event_name = 'payment_transfer_completed' AND event_timestamp >= NOW() - INTERVAL '7 days'` |
| **측정 주기** | 일간 (Rolling 7일) |
| **목표** | MoM +15% 성장 |
| **선정 이유** | 송금은 QuickPay의 핵심 가치이며, 활성 송금자 수는 서비스 건강도를 가장 잘 대표 |

---

## 🔑 Level 1: 핵심 KPI (5개)

### KPI-01. DAU (Daily Active Users)

| 항목 | 내용 |
|---|---|
| **지표명** | 일간 활성 사용자 수 |
| **영문명** | Daily Active Users (DAU) |
| **정의** | 해당 일자에 앱에 로그인 완료한 고유 사용자 수 |
| **산출식** | `COUNT(DISTINCT user_id) WHERE event_name = 'auth_login_completed' AND DATE(event_timestamp) = {target_date}` |
| **데이터 소스** | `events` 테이블 → `stg_events` → `int_daily_active_users` |
| **측정 주기** | 일간 |
| **세그먼트** | platform, app_version, signup_cohort |
| **목표** | 100,000 DAU |
| **담당** | Growth팀 |
| **주의사항** | 봇/테스트 계정 제외 (user_id LIKE 'usr_test%' 제외) |

### KPI-02. 전환율 (Conversion Rate)

| 항목 | 내용 |
|---|---|
| **지표명** | 가입→첫 송금 전환율 |
| **영문명** | Signup to First Transfer Conversion Rate |
| **정의** | 가입 완료 후 7일 이내 첫 송금을 완료한 사용자 비율 |
| **산출식** | `COUNT(DISTINCT first_transfer_users) / COUNT(DISTINCT signup_users) × 100` |
| **퍼널 단계** | signup_completed → identity_verified → transfer_started → transfer_completed |
| **데이터 소스** | `events` → `int_funnel_conversion` → `mart_funnel` |
| **측정 주기** | 일간 (7일 window) |
| **세그먼트** | signup_method, platform, referrer |
| **목표** | 40% |
| **담당** | Product팀 |

### KPI-03. 리텐션 (Retention Rate)

| 항목 | 내용 |
|---|---|
| **지표명** | N-Day 리텐션 |
| **영문명** | N-Day Retention Rate |
| **정의** | 가입일로부터 N일 후 다시 접속한 사용자 비율 |
| **산출식** | `COUNT(DISTINCT retained_users_day_n) / COUNT(DISTINCT cohort_users) × 100` |
| **기준일** | D1, D3, D7, D14, D30 |
| **데이터 소스** | `events` → `int_user_cohort` → `mart_retention` |
| **측정 주기** | 일간 |
| **세그먼트** | signup_week, platform, signup_method |
| **목표** | D1: 60%, D7: 40%, D30: 25% |
| **담당** | Growth팀 |

### KPI-04. ARPPU (Average Revenue Per Paying User)

| 항목 | 내용 |
|---|---|
| **지표명** | 결제 사용자당 평균 매출 |
| **영문명** | Average Revenue Per Paying User |
| **정의** | 해당 월에 1회 이상 수수료를 발생시킨 사용자의 평균 수수료 매출 |
| **산출식** | `SUM(fee) / COUNT(DISTINCT user_id WHERE fee > 0)` |
| **데이터 소스** | `transactions` → `stg_transactions` → `mart_revenue` |
| **측정 주기** | 월간 |
| **세그먼트** | user_tier, signup_cohort |
| **목표** | ₩2,500/월 |
| **담당** | Revenue팀 |

### KPI-05. GMV (Gross Merchandise Value)

| 항목 | 내용 |
|---|---|
| **지표명** | 총 거래액 |
| **영문명** | Gross Merchandise Value |
| **정의** | 해당 기간 내 모든 송금+결제 거래의 총 금액 |
| **산출식** | `SUM(amount) WHERE event_name IN ('payment_transfer_completed', 'payment_qr_completed')` |
| **데이터 소스** | `events` → `stg_events` → `mart_daily_kpi` |
| **측정 주기** | 일간, 주간, 월간 |
| **세그먼트** | transaction_type, platform |
| **목표** | 월간 ₩500억 |
| **담당** | Finance팀 |

---

## 📈 Level 2: 운영 지표 (10개)

| # | 지표명 | 정의 | 산출식 | 상위 KPI |
|---|---|---|---|---|
| OP-01 | MAU | 월간 활성 사용자 수 | `COUNT(DISTINCT user_id) per month` | DAU |
| OP-02 | DAU/MAU Ratio | 서비스 점착도 | `DAU / MAU × 100` | DAU |
| OP-03 | 가입 완료율 | 가입 시작 → 완료 비율 | `signup_completed / signup_started × 100` | 전환율 |
| OP-04 | 본인인증 완료율 | 가입 → 본인인증 비율 | `identity_verified / signup_completed × 100` | 전환율 |
| OP-05 | 송금 성공률 | 송금 시도 → 성공 비율 | `transfer_completed / transfer_confirmed × 100` | GMV |
| OP-06 | 평균 송금액 | 건당 평균 송금 금액 | `AVG(amount) WHERE transfer_completed` | ARPPU |
| OP-07 | 충전 빈도 | 사용자당 월 평균 충전 횟수 | `COUNT(charge) / COUNT(DISTINCT user_id)` | ARPPU |
| OP-08 | QR 결제 비율 | 전체 결제 중 QR 결제 비율 | `qr_completed / total_payments × 100` | GMV |
| OP-09 | 에러율 | 전체 요청 대비 에러 비율 | `error_count / total_requests × 100` | 전환율 |
| OP-10 | 푸시 CTR | 푸시 클릭률 | `push_clicked / push_received × 100` | DAU |

---

## ⚠️ 지표 정합성 규칙 (Data Contract)

### 규칙 1: DAU 상한선
```
DAU ≤ MAU (동일 월 기준)
위반 시: 🔴 Critical Alert → 데이터 파이프라인 점검
```

### 규칙 2: GMV = 송금 GMV + QR 결제 GMV
```
SUM(transfer_amount) + SUM(qr_amount) = Total GMV
허용 오차: ±₩100 (반올림 차이)
위반 시: 🟡 Warning → 이중 집계 확인
```

### 규칙 3: 리텐션 단조감소
```
D1 ≥ D3 ≥ D7 ≥ D14 ≥ D30 (동일 코호트)
위반 시: 🟡 Warning → 코호트 정의 확인
```

### 규칙 4: 전환율 범위
```
0% ≤ Conversion Rate ≤ 100%
위반 시: 🔴 Critical → 퍼널 이벤트 누락 확인
```

---

## 📋 지표 변경 관리 (Change Log)

| 날짜 | 지표 | 변경 내용 | 사유 | 승인자 |
|---|---|---|---|---|
| 2026-02-12 | 전체 | v1.0 초기 정의 | 프로젝트 시작 | DataOps |
