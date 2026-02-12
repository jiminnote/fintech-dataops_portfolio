"""
QuickPay 이벤트 로그 생성기
━━━━━━━━━━━━━━━━━━━━━━━━━━
가상 핀테크 서비스의 사용자 행동 이벤트 로그를 현실적으로 생성합니다.
- 90일치 데이터 (약 200만 이벤트)
- 사용자 행동 패턴 반영 (시간대별 활동량, 요일 효과)
- 퍼널 전환율 반영 (가입→인증→첫 송금)
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
from faker import Faker

fake = Faker("ko_KR")
random.seed(42)
np.random.seed(42)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NUM_USERS = 10_000           # 총 사용자 수
DAYS = 90                    # 생성 기간 (일)
START_DATE = datetime(2025, 11, 15)
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# 플랫폼 분포
PLATFORMS = {"ios": 0.55, "android": 0.40, "web": 0.05}

# 시간대별 활동 가중치 (0~23시)
HOUR_WEIGHTS = [
    0.02, 0.01, 0.01, 0.01, 0.01, 0.02,  # 0~5시
    0.03, 0.05, 0.07, 0.08, 0.07, 0.06,  # 6~11시
    0.08, 0.07, 0.06, 0.05, 0.05, 0.06,  # 12~17시
    0.07, 0.06, 0.05, 0.04, 0.03, 0.02,  # 18~23시
]

# 앱 버전 분포
APP_VERSIONS = ["3.2.1", "3.2.0", "3.1.9", "3.1.8"]
VERSION_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

# 디바이스 모델
IOS_MODELS = ["iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro", "iPhone 14", "iPhone 13"]
ANDROID_MODELS = ["Galaxy S24 Ultra", "Galaxy S24", "Galaxy S23", "Pixel 8 Pro", "Pixel 8"]

SCREENS = [
    "home", "transfer_home", "transfer_confirm", "transfer_complete",
    "charge_home", "qr_scan", "product_list", "product_detail",
    "my_page", "settings", "notification", "benefit_home"
]

MERCHANT_CATEGORIES = ["cafe", "restaurant", "convenience_store", "grocery", "clothing", "transport"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 사용자 프로필 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_users(n: int) -> list[dict]:
    """사용자 프로필 생성 (가입일, 플랫폼, 디바이스 등)"""
    users = []
    for i in range(n):
        platform = random.choices(
            list(PLATFORMS.keys()), weights=list(PLATFORMS.values())
        )[0]
        
        signup_day = random.randint(0, DAYS - 1)
        signup_date = START_DATE + timedelta(days=signup_day)
        
        if platform == "ios":
            device_model = random.choice(IOS_MODELS)
            os_version = f"iOS {random.choice(['17.2', '17.1', '17.0', '16.6'])}"
        elif platform == "android":
            device_model = random.choice(ANDROID_MODELS)
            os_version = f"Android {random.choice(['14', '13', '12'])}"
        else:
            device_model = "Web Browser"
            os_version = "Chrome 120"

        # 사용자 활성도 (power law 분포)
        activity_level = min(1.0, np.random.pareto(1.5) * 0.1)
        
        users.append({
            "user_id": f"usr_{uuid.uuid4().hex[:8]}",
            "device_id": f"dev_{uuid.uuid4().hex[:8]}",
            "platform": platform,
            "device_model": device_model,
            "os_version": os_version,
            "app_version": random.choices(APP_VERSIONS, weights=VERSION_WEIGHTS)[0],
            "signup_date": signup_date,
            "signup_method": random.choice(["phone", "phone", "phone", "email", "social_kakao", "social_apple"]),
            "activity_level": activity_level,
        })
    return users


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이벤트 생성 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def make_event(user: dict, event_name: str, ts: datetime, properties: dict) -> dict:
    """공통 스키마 + 이벤트별 속성을 조합하여 이벤트 생성"""
    received_delay = random.uniform(0.1, 2.0)  # 서버 수신 지연(초)
    return {
        "event_id": str(uuid.uuid4()),
        "event_name": event_name,
        "event_timestamp": ts.isoformat() + "Z",
        "received_at": (ts + timedelta(seconds=received_delay)).isoformat() + "Z",
        "user_id": user["user_id"],
        "session_id": f"sess_{uuid.uuid4().hex[:8]}",
        "device_id": user["device_id"],
        "platform": user["platform"],
        "app_version": user["app_version"],
        "os_version": user["os_version"],
        "device_model": user["device_model"],
        "event_properties": properties,
    }


def random_time_in_day(date: datetime) -> datetime:
    """시간대별 가중치를 적용한 랜덤 시각 생성"""
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    ms = random.randint(0, 999)
    return date.replace(hour=hour, minute=minute, second=second, microsecond=ms * 1000)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 퍼널별 이벤트 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_signup_events(user: dict) -> list[dict]:
    """회원가입 퍼널 이벤트 (가입일에 1회)"""
    events = []
    ts = random_time_in_day(user["signup_date"])
    
    # 가입 시작 (100%)
    events.append(make_event(user, "auth_signup_started", ts, {
        "device_type": user["platform"],
        "referrer": random.choice(["organic", "friend_invite", "instagram", "youtube", "search", None]),
    }))
    
    # 가입 제출 (85%)
    if random.random() < 0.85:
        ts += timedelta(minutes=random.randint(1, 5))
        events.append(make_event(user, "auth_signup_submitted", ts, {
            "signup_method": user["signup_method"],
            "step": 3,
            "total_steps": 5,
        }))
        
        # 가입 완료 (90% of submitted)
        if random.random() < 0.90:
            ts += timedelta(minutes=random.randint(1, 3))
            events.append(make_event(user, "auth_signup_completed", ts, {
                "signup_method": user["signup_method"],
                "referrer": random.choice(["organic", "friend_invite", "instagram", None]),
                "referral_code": f"REF{random.randint(1000,9999)}" if random.random() < 0.3 else None,
                "marketing_channel": random.choice(["instagram", "youtube", "search", "organic"]),
                "step": 5,
                "total_steps": 5,
            }))
            
            # 본인인증 (80% of completed)
            if random.random() < 0.80:
                ts += timedelta(minutes=random.randint(2, 10))
                events.append(make_event(user, "auth_identity_verified", ts, {
                    "verification_type": random.choice(["phone_sms", "phone_sms", "bank_account", "pass_cert"]),
                }))
    
    return events


def generate_daily_events(user: dict, date: datetime) -> list[dict]:
    """일간 활동 이벤트 생성 (로그인, 화면조회, 송금, QR결제 등)"""
    events = []
    
    # 활동 여부 결정 (activity_level 기반)
    # 요일 효과: 주말에 약간 더 활성
    weekday_boost = 1.2 if date.weekday() >= 5 else 1.0
    if random.random() > user["activity_level"] * weekday_boost:
        return events
    
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    ts = random_time_in_day(date)
    
    # 로그인
    events.append(make_event(user, "auth_login_completed", ts, {
        "login_method": random.choice(["biometric", "biometric", "pin", "password"]),
    }))
    
    # 화면 조회 (2~8개)
    num_screens = random.randint(2, 8)
    prev_screen = None
    for _ in range(num_screens):
        ts += timedelta(seconds=random.randint(10, 120))
        screen = random.choice(SCREENS)
        events.append(make_event(user, "screen_viewed", ts, {
            "screen_name": screen,
            "screen_class": f"{screen.title().replace('_','')}ViewController",
            "previous_screen": prev_screen,
            "referrer": None,
            "load_time_ms": random.randint(80, 500),
        }))
        
        # 화면 이탈
        duration = random.randint(3000, 60000)
        events.append(make_event(user, "screen_exited", ts + timedelta(milliseconds=duration), {
            "screen_name": screen,
            "duration_ms": duration,
        }))
        prev_screen = screen
    
    # 송금 (40% 확률)
    if random.random() < 0.40:
        ts += timedelta(minutes=random.randint(1, 5))
        amount = random.choice([10000, 30000, 50000, 100000, 200000, 500000])
        
        events.append(make_event(user, "payment_transfer_started", ts, {}))
        
        ts += timedelta(seconds=random.randint(5, 30))
        events.append(make_event(user, "payment_transfer_amount_entered", ts, {
            "amount": amount,
        }))
        
        ts += timedelta(seconds=random.randint(3, 15))
        events.append(make_event(user, "payment_transfer_confirmed", ts, {
            "amount": amount,
            "recipient_type": random.choice(["contact", "contact", "account", "qr"]),
        }))
        
        # 성공 (95%) vs 실패 (5%)
        ts += timedelta(milliseconds=random.randint(200, 2000))
        if random.random() < 0.95:
            fee = random.choice([0, 0, 0, 0, 500])  # 대부분 무료
            events.append(make_event(user, "payment_transfer_completed", ts, {
                "amount": amount,
                "currency": "KRW",
                "transfer_type": random.choice(["instant", "instant", "scheduled"]),
                "recipient_type": random.choice(["contact", "account"]),
                "fee": fee,
                "bank_code": random.choice(["088", "004", "003", "011", "020"]),
                "is_first_transfer": False,
                "error_code": None,
                "error_message": None,
                "latency_ms": random.randint(150, 800),
            }))
        else:
            error = random.choice([
                ("TRF_TIMEOUT_001", "network", "송금 처리 시간 초과"),
                ("TRF_LIMIT_002", "business", "일일 한도 초과"),
                ("TRF_BANK_003", "external", "수취 은행 점검 중"),
            ])
            events.append(make_event(user, "payment_transfer_failed", ts, {
                "error_code": error[0],
                "error_type": error[1],
                "error_message": error[2],
            }))
    
    # QR 결제 (20% 확률)
    if random.random() < 0.20:
        ts += timedelta(minutes=random.randint(10, 120))
        qr_amount = random.choice([3500, 4500, 5000, 6500, 12000, 15000, 25000])
        category = random.choice(MERCHANT_CATEGORIES)
        merchant_id = f"mrc_{category}_{random.randint(1,100):03d}"
        
        events.append(make_event(user, "payment_qr_scanned", ts, {
            "merchant_id": merchant_id,
        }))
        
        ts += timedelta(seconds=random.randint(2, 10))
        events.append(make_event(user, "payment_qr_completed", ts, {
            "amount": qr_amount,
            "merchant_id": merchant_id,
            "merchant_name": f"{fake.company()} {random.choice(['강남점','역삼점','판교점','성수점'])}",
            "merchant_category": category,
            "payment_method": random.choice(["balance", "balance", "card", "point"]),
            "discount_amount": random.choice([0, 0, 500, 1000]) if random.random() < 0.3 else 0,
            "point_earned": int(qr_amount * 0.01),
        }))
    
    # 충전 (15% 확률)
    if random.random() < 0.15:
        ts += timedelta(minutes=random.randint(1, 30))
        charge_amount = random.choice([10000, 30000, 50000, 100000, 200000])
        events.append(make_event(user, "payment_charge_completed", ts, {
            "amount": charge_amount,
            "charge_method": random.choice(["bank_transfer", "bank_transfer", "card"]),
            "bank_code": random.choice(["088", "004", "003"]),
            "is_auto_charge": random.random() < 0.2,
            "balance_after": charge_amount + random.randint(0, 500000),
        }))
    
    # 배너 클릭 (10% 확률)
    if random.random() < 0.10:
        ts += timedelta(minutes=random.randint(1, 10))
        events.append(make_event(user, "screen_banner_clicked", ts, {
            "banner_id": f"bnr_{random.randint(1,20):03d}",
            "position": random.randint(1, 5),
        }))
    
    # 푸시 (30% 확률)
    if random.random() < 0.30:
        push_ts = random_time_in_day(date)
        events.append(make_event(user, "system_push_received", push_ts, {
            "push_type": random.choice(["marketing", "transactional", "reminder"]),
            "campaign_id": f"camp_{random.randint(1,50):03d}",
        }))
        # 클릭 (40% CTR)
        if random.random() < 0.40:
            events.append(make_event(user, "system_push_clicked", push_ts + timedelta(minutes=random.randint(1, 60)), {
                "push_type": random.choice(["marketing", "transactional", "reminder"]),
                "campaign_id": f"camp_{random.randint(1,50):03d}",
            }))
    
    return events


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔧 사용자 프로필 생성 중...")
    users = generate_users(NUM_USERS)
    
    # 사용자 정보 저장
    users_df = pd.DataFrame([{
        "user_id": u["user_id"],
        "device_id": u["device_id"],
        "platform": u["platform"],
        "device_model": u["device_model"],
        "signup_date": u["signup_date"].strftime("%Y-%m-%d"),
        "signup_method": u["signup_method"],
    } for u in users])
    users_df.to_csv(OUTPUT_DIR / "users.csv", index=False)
    print(f"   ✅ {len(users):,}명 사용자 생성 → data/users.csv")
    
    # 이벤트 생성
    print("📊 이벤트 로그 생성 중...")
    all_events = []
    
    for user in users:
        # 가입 이벤트
        all_events.extend(generate_signup_events(user))
        
        # 일간 이벤트 (가입일 이후)
        for day_offset in range(DAYS):
            date = START_DATE + timedelta(days=day_offset)
            if date >= user["signup_date"]:
                all_events.extend(generate_daily_events(user, date))
    
    # 시간순 정렬
    all_events.sort(key=lambda x: x["event_timestamp"])
    
    # JSON 저장
    with open(OUTPUT_DIR / "events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    
    # CSV 저장 (Tableau / 분석용 - event_properties를 flatten)
    flat_events = []
    for e in all_events:
        flat = {k: v for k, v in e.items() if k != "event_properties"}
        flat.update({f"prop_{k}": v for k, v in e["event_properties"].items()})
        flat_events.append(flat)
    
    events_df = pd.DataFrame(flat_events)
    events_df.to_csv(OUTPUT_DIR / "events.csv", index=False)
    
    print(f"   ✅ {len(all_events):,}개 이벤트 생성")
    print(f"   📁 data/events.json ({Path(OUTPUT_DIR / 'events.json').stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"   📁 data/events.csv ({Path(OUTPUT_DIR / 'events.csv').stat().st_size / 1024 / 1024:.1f} MB)")
    
    # 이벤트별 통계
    event_counts = events_df["event_name"].value_counts()
    print("\n📈 이벤트별 건수:")
    for name, count in event_counts.head(15).items():
        print(f"   {name}: {count:,}")


if __name__ == "__main__":
    main()
