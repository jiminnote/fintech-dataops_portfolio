# 📐 QuickPay 로그 스키마 정의서

> **목적**: 모든 이벤트 로그의 공통/개별 스키마를 정의하여 데이터 정합성 확보  
> **적용 범위**: 클라이언트(앱) + 서버 사이드 로그  
> **버전**: v1.0 | 최종 수정: 2026-02-12

---

## 1. 공통 스키마 (Common Schema)

모든 이벤트에 반드시 포함되는 필드입니다.

| 필드명 | 타입 | 필수 | 설명 | 예시 |
|---|---|---|---|---|
| `event_id` | STRING(UUID) | ✅ | 이벤트 고유 ID | `550e8400-e29b-41d4-a716-446655440000` |
| `event_name` | STRING | ✅ | 이벤트명 (taxonomy 참조) | `payment_transfer_completed` |
| `event_timestamp` | TIMESTAMP | ✅ | 이벤트 발생 시각 (UTC, ISO 8601) | `2026-02-12T13:45:30.123Z` |
| `received_at` | TIMESTAMP | ✅ | 서버 수신 시각 | `2026-02-12T13:45:30.456Z` |
| `user_id` | STRING | ⚠️ | 사용자 ID (비로그인 시 null) | `usr_abc123` |
| `session_id` | STRING | ✅ | 세션 ID | `sess_xyz789` |
| `device_id` | STRING | ✅ | 디바이스 고유 ID | `dev_123abc` |
| `platform` | ENUM | ✅ | `ios` / `android` / `web` | `ios` |
| `app_version` | STRING | ✅ | 앱 버전 | `3.2.1` |
| `os_version` | STRING | ✅ | OS 버전 | `iOS 17.2` |
| `device_model` | STRING | ✅ | 디바이스 모델 | `iPhone 15 Pro` |
| `event_properties` | JSON | ✅ | 이벤트별 개별 속성 | `{"amount": 50000, ...}` |

---

## 2. 이벤트별 개별 스키마 (Event Properties)

### 2.1 송금 이벤트 (`payment_transfer_*`)

```json
{
  "amount": 50000,                    // INTEGER, 필수, 송금 금액 (원)
  "currency": "KRW",                  // STRING, 필수, 통화
  "transfer_type": "instant",         // ENUM: instant|scheduled|recurring
  "recipient_type": "contact",        // ENUM: contact|account|qr
  "fee": 0,                           // INTEGER, 수수료
  "bank_code": "088",                 // STRING, 은행코드
  "is_first_transfer": false,         // BOOLEAN, 첫 송금 여부
  "error_code": null,                 // STRING, nullable, 실패시 에러코드
  "error_message": null,              // STRING, nullable, 실패시 메시지
  "latency_ms": 342                   // INTEGER, 처리 소요시간(ms)
}
```

### 2.2 충전 이벤트 (`payment_charge_completed`)

```json
{
  "amount": 100000,                   // INTEGER, 필수, 충전 금액
  "charge_method": "bank_transfer",   // ENUM: bank_transfer|card|convenience_store
  "bank_code": "088",                 // STRING, 은행코드
  "is_auto_charge": false,            // BOOLEAN, 자동충전 여부
  "balance_after": 150000             // INTEGER, 충전 후 잔액
}
```

### 2.3 회원가입 이벤트 (`auth_signup_*`)

```json
{
  "signup_method": "phone",           // ENUM: phone|email|social_kakao|social_apple
  "referrer": "friend_invite",        // STRING, nullable, 유입 경로
  "referral_code": "REF123",          // STRING, nullable, 추천 코드
  "marketing_channel": "instagram",   // STRING, nullable, 마케팅 채널
  "step": 3,                          // INTEGER, 가입 단계 (1~5)
  "total_steps": 5                    // INTEGER, 전체 단계 수
}
```

### 2.4 화면 조회 이벤트 (`screen_viewed`)

```json
{
  "screen_name": "home",              // STRING, 필수, 화면명
  "screen_class": "HomeViewController", // STRING, 화면 클래스
  "previous_screen": "login",         // STRING, nullable, 이전 화면
  "referrer": "push_notification",    // STRING, nullable, 진입 경로
  "load_time_ms": 230                 // INTEGER, 화면 로드 시간
}
```

### 2.5 QR 결제 이벤트 (`payment_qr_*`)

```json
{
  "amount": 15000,                    // INTEGER, 필수, 결제 금액
  "merchant_id": "mrc_456",           // STRING, 필수, 가맹점 ID
  "merchant_name": "스타벅스 강남점",   // STRING, 가맹점명
  "merchant_category": "cafe",        // STRING, 업종
  "payment_method": "balance",        // ENUM: balance|card|point
  "discount_amount": 1000,            // INTEGER, 할인 금액
  "point_earned": 150                 // INTEGER, 적립 포인트
}
```

---

## 3. 데이터 타입 규칙

| 타입 | 규칙 | 예시 |
|---|---|---|
| TIMESTAMP | UTC, ISO 8601, ms 단위 | `2026-02-12T13:45:30.123Z` |
| AMOUNT | 정수 (원 단위), 음수 불허 | `50000` |
| ENUM | 미리 정의된 값만 허용 | `ios`, `android`, `web` |
| UUID | v4 UUID | `550e8400-e29b-...` |
| STRING | UTF-8, 최대 1024자 | - |

---

## 4. 데이터 수집 아키텍처

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  Mobile   │────▶│  Event SDK   │────▶│  API Gateway │────▶│  Kafka   │
│  App      │     │  (Client)    │     │  (Server)    │     │  Topic   │
└──────────┘     └──────────────┘     └─────────────┘     └────┬─────┘
                                                                │
                  ┌─────────────────────────────────────────────┘
                  │
            ┌─────▼─────┐     ┌──────────────┐     ┌──────────────┐
            │  Spark     │────▶│  Data Lake    │────▶│  Data Mart   │
            │  Streaming │     │  (S3/Parquet) │     │  (PostgreSQL)│
            └───────────┘     └──────────────┘     └──────────────┘
```

---

## 5. 로그 QA 규칙

### 5.1 실시간 검증 (SDK 레벨)
- `event_id` UUID 형식 검증
- `event_name`이 taxonomy에 등록된 값인지 확인
- 필수 필드 null 체크
- `event_timestamp` 미래 시간 불허 (서버 시간 + 5분 이내)

### 5.2 배치 검증 (일간)
- 이벤트 볼륨 이상 탐지 (전일 대비 ±30% 이상 변동 시 알림)
- 필드별 null rate 모니터링 (임계값: 5%)
- 중복 `event_id` 검출
- 스키마 변경 감지 (새 필드 추가, 필드 타입 변경)

### 5.3 품질 지표 (Data Quality Score)

```
DQ Score = (1 - null_rate) × 0.3
         + (1 - duplicate_rate) × 0.2
         + schema_compliance_rate × 0.3
         + timeliness_rate × 0.2
```
