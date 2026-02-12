# 📋 QuickPay 이벤트 택소노미 (Event Taxonomy)

> **목적**: 핀테크 서비스 "QuickPay"의 모든 사용자 행동 이벤트를 체계적으로 분류  
> **규칙**: `{도메인}_{행동}` 네이밍 컨벤션 (snake_case)  
> **버전**: v1.0 | 최종 수정: 2026-02-12

---

## 🔤 네이밍 컨벤션

```
{domain}_{action}_{detail}

예시: payment_transfer_completed
      auth_signup_submitted
```

| 접두사 | 도메인 | 설명 |
|---|---|---|
| `auth_` | 인증 | 회원가입, 로그인, 본인인증 |
| `payment_` | 결제/송금 | 송금, 결제, 충전, 출금 |
| `product_` | 상품 | 상품 조회, 비교, 가입 |
| `screen_` | 화면 | 화면 진입, 이탈 |
| `system_` | 시스템 | 에러, 성능, 푸시 |

---

## 📊 이벤트 목록

### 1. 인증 도메인 (Auth)

| # | 이벤트명 | 트리거 시점 | 필수 속성 | 비즈니스 용도 |
|---|---|---|---|---|
| 1 | `auth_signup_started` | 회원가입 화면 진입 | device_type, referrer | 퍼널 시작점 |
| 2 | `auth_signup_submitted` | 회원가입 정보 제출 | signup_method | 가입 전환율 |
| 3 | `auth_signup_completed` | 가입 완료 | user_id, signup_method | 가입 완료율 |
| 4 | `auth_login_attempted` | 로그인 시도 | login_method | 로그인 성공률 |
| 5 | `auth_login_completed` | 로그인 성공 | user_id, login_method | DAU 산정 |
| 6 | `auth_identity_verified` | 본인인증 완료 | verification_type | 인증 전환율 |

### 2. 결제/송금 도메인 (Payment)

| # | 이벤트명 | 트리거 시점 | 필수 속성 | 비즈니스 용도 |
|---|---|---|---|---|
| 7 | `payment_transfer_started` | 송금 화면 진입 | - | 송금 퍼널 |
| 8 | `payment_transfer_amount_entered` | 금액 입력 | amount | 평균 송금액 |
| 9 | `payment_transfer_confirmed` | 송금 확인 | amount, recipient_type | 송금 완료율 |
| 10 | `payment_transfer_completed` | 송금 성공 | amount, fee, transfer_type | 매출, GMV |
| 11 | `payment_transfer_failed` | 송금 실패 | error_code, error_message | 에러 모니터링 |
| 12 | `payment_charge_completed` | 충전 완료 | amount, charge_method | 충전 패턴 |
| 13 | `payment_withdraw_completed` | 출금 완료 | amount | 출금 패턴 |
| 14 | `payment_qr_scanned` | QR 결제 스캔 | merchant_id | 오프라인 결제 |
| 15 | `payment_qr_completed` | QR 결제 완료 | amount, merchant_id | 오프라인 GMV |

### 3. 상품 도메인 (Product)

| # | 이벤트명 | 트리거 시점 | 필수 속성 | 비즈니스 용도 |
|---|---|---|---|---|
| 16 | `product_list_viewed` | 상품 목록 조회 | category | 관심 카테고리 |
| 17 | `product_detail_viewed` | 상품 상세 조회 | product_id, product_type | 상품 인기도 |
| 18 | `product_compared` | 상품 비교 | product_ids | 비교 패턴 |
| 19 | `product_applied` | 상품 가입 신청 | product_id | 전환율 |
| 20 | `product_application_completed` | 가입 완료 | product_id | 상품 매출 |

### 4. 화면 도메인 (Screen)

| # | 이벤트명 | 트리거 시점 | 필수 속성 | 비즈니스 용도 |
|---|---|---|---|---|
| 21 | `screen_viewed` | 화면 진입 | screen_name | 트래픽 분석 |
| 22 | `screen_exited` | 화면 이탈 | screen_name, duration_ms | 체류 시간 |
| 23 | `screen_tab_clicked` | 탭 클릭 | tab_name | UI 사용 패턴 |
| 24 | `screen_banner_clicked` | 배너 클릭 | banner_id, position | 배너 CTR |
| 25 | `screen_search_performed` | 검색 실행 | query, results_count | 검색 분석 |

### 5. 시스템 도메인 (System)

| # | 이벤트명 | 트리거 시점 | 필수 속성 | 비즈니스 용도 |
|---|---|---|---|---|
| 26 | `system_error_occurred` | 에러 발생 | error_code, error_type | 에러 모니터링 |
| 27 | `system_push_received` | 푸시 수신 | push_type, campaign_id | 푸시 도달률 |
| 28 | `system_push_clicked` | 푸시 클릭 | push_type, campaign_id | 푸시 CTR |

---

## 📐 이벤트 분류 매트릭스

```
                    자동 수집          수동 로깅
               ┌─────────────────┬──────────────────┐
 클라이언트    │ screen_viewed    │ payment_transfer  │
 (앱)         │ screen_exited    │ product_applied   │
               ├─────────────────┼──────────────────┤
 서버          │ system_error     │ auth_signup       │
               │ system_push      │ payment_completed │
               └─────────────────┴──────────────────┘
```

---

## ✅ QA 체크리스트

- [ ] 모든 이벤트에 `event_id`, `user_id`, `timestamp` 포함 확인
- [ ] 이벤트명이 네이밍 컨벤션을 따르는지 확인
- [ ] 필수 속성 누락 없는지 검증
- [ ] 이벤트 발화 시점이 명확한지 확인
- [ ] 중복 이벤트 없는지 확인
- [ ] 퍼널 단계별 이벤트가 빠짐없이 정의되었는지 확인
