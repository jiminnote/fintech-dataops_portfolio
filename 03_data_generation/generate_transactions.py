"""
QuickPay 거래 데이터 생성기
━━━━━━━━━━━━━━━━━━━━━━━━━━
서버사이드 거래(transactions) 테이블 데이터를 생성합니다.
- 이벤트 로그와 연동되는 거래 레코드
- 송금, QR결제, 충전, 출금 거래 포함
- 수수료, 상태, 정산 정보 포함
"""

import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "data"
NUM_DAYS = 90
START_DATE = datetime(2025, 11, 15)

TRANSACTION_TYPES = {
    "transfer": 0.50,      # 송금
    "qr_payment": 0.25,    # QR 결제
    "charge": 0.15,        # 충전
    "withdraw": 0.10,      # 출금
}

STATUS_PROBS = {
    "completed": 0.93,
    "failed": 0.04,
    "pending": 0.02,
    "cancelled": 0.01,
}

BANK_CODES = {
    "088": "신한은행",
    "004": "KB국민은행",
    "003": "기업은행",
    "011": "농협은행",
    "020": "우리은행",
    "090": "카카오뱅크",
    "092": "토스뱅크",
}


def generate_transactions() -> pd.DataFrame:
    """거래 데이터 생성"""
    # 사용자 로드
    users_df = pd.read_csv(OUTPUT_DIR / "users.csv")
    user_ids = users_df["user_id"].tolist()
    
    records = []
    
    for day_offset in range(NUM_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        
        # 일간 거래 수 (성장 트렌드 + 요일 효과)
        base_txns = 3000 + int(day_offset * 30)  # 일간 3000 → 5700
        weekday_factor = 1.15 if date.weekday() >= 5 else 1.0
        daily_txns = int(base_txns * weekday_factor * random.uniform(0.85, 1.15))
        
        for _ in range(daily_txns):
            tx_type = random.choices(
                list(TRANSACTION_TYPES.keys()),
                weights=list(TRANSACTION_TYPES.values())
            )[0]
            
            status = random.choices(
                list(STATUS_PROBS.keys()),
                weights=list(STATUS_PROBS.values())
            )[0]
            
            # 금액 분포 (거래 유형별)
            if tx_type == "transfer":
                amount = int(np.random.lognormal(mean=10.5, sigma=1.2))
                amount = min(max(amount, 1000), 5_000_000)  # 1천 ~ 500만
                amount = round(amount, -3)  # 천원 단위 반올림
                fee = random.choice([0, 0, 0, 0, 500]) if amount >= 100000 else 0
            elif tx_type == "qr_payment":
                amount = int(np.random.lognormal(mean=8.8, sigma=0.8))
                amount = min(max(amount, 1000), 500_000)
                amount = round(amount, -2)
                fee = 0
            elif tx_type == "charge":
                amount = random.choice([10000, 30000, 50000, 100000, 200000, 500000])
                fee = 0
            else:  # withdraw
                amount = random.choice([10000, 50000, 100000, 200000, 500000])
                fee = random.choice([0, 0, 500])
            
            hour = random.choices(range(24), weights=[
                2,1,1,1,1,2, 3,5,7,8,7,6, 8,7,6,5,5,6, 7,6,5,4,3,2
            ])[0]
            ts = date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )
            
            bank_code = random.choice(list(BANK_CODES.keys()))
            
            record = {
                "transaction_id": str(uuid.uuid4()),
                "user_id": random.choice(user_ids),
                "transaction_type": tx_type,
                "amount": amount,
                "fee": fee,
                "currency": "KRW",
                "status": status,
                "bank_code": bank_code,
                "bank_name": BANK_CODES[bank_code],
                "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": (ts + timedelta(seconds=random.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S") if status == "completed" else None,
                "error_code": f"ERR_{random.randint(100,999)}" if status == "failed" else None,
                "merchant_id": f"mrc_{random.choice(['cafe','restaurant','convenience_store','grocery'])}_{random.randint(1,100):03d}" if tx_type == "qr_payment" else None,
                "merchant_category": random.choice(["cafe", "restaurant", "convenience_store", "grocery", "clothing"]) if tx_type == "qr_payment" else None,
            }
            records.append(record)
    
    df = pd.DataFrame(records)
    df = df.sort_values("created_at").reset_index(drop=True)
    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("💳 거래 데이터 생성 중...")
    txn_df = generate_transactions()
    
    # CSV 저장
    txn_df.to_csv(OUTPUT_DIR / "transactions.csv", index=False)
    
    print(f"   ✅ {len(txn_df):,}건 거래 생성")
    print(f"   📁 data/transactions.csv ({(OUTPUT_DIR / 'transactions.csv').stat().st_size / 1024 / 1024:.1f} MB)")
    
    # 통계
    print("\n📈 거래 유형별 건수:")
    for tx_type, count in txn_df["transaction_type"].value_counts().items():
        avg_amt = txn_df[txn_df["transaction_type"] == tx_type]["amount"].mean()
        print(f"   {tx_type}: {count:,}건 (평균 {avg_amt:,.0f}원)")
    
    print(f"\n💰 총 거래액 (GMV): ₩{txn_df[txn_df['status']=='completed']['amount'].sum():,.0f}")
    print(f"💰 총 수수료 매출: ₩{txn_df[txn_df['status']=='completed']['fee'].sum():,.0f}")
    
    print(f"\n📊 상태별 건수:")
    for status, count in txn_df["status"].value_counts().items():
        print(f"   {status}: {count:,}건 ({count/len(txn_df)*100:.1f}%)")


if __name__ == "__main__":
    main()
