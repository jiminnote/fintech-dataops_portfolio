# 📘 Tableau Public 게시 단계별 가이드

> Tableau 경험이 없는 상태에서 포트폴리오용 대시보드를 만드는 실전 가이드

---

## Step 0: 사전 준비

### Tableau Public Desktop 설치
1. https://public.tableau.com/en-us/s/download 접속
2. macOS / Windows 버전 다운로드
3. 설치 후 Tableau Public 계정 생성 (무료)

### 데이터 준비
```bash
# 프로젝트 루트에서 실행
python 03_data_generation/generate_events.py
python 03_data_generation/generate_transactions.py
python 03_data_generation/load_to_db.py
python 06_tableau_dashboard/export_tableau_data.py
```

생성되는 CSV 파일:
- `exports/daily_kpi.csv` — 일간 KPI (DAU, GMV 등)
- `exports/retention_cohort.csv` — 리텐션 히트맵용
- `exports/funnel_data.csv` — 퍼널 전환율
- `exports/transaction_summary.csv` — 거래 분석

---

## Step 1: 데이터 연결 (5분)

1. Tableau Public Desktop 실행
2. 좌측 "연결" → **텍스트 파일** 클릭
3. `exports/daily_kpi.csv` 선택
4. 데이터가 올바르게 로드되었는지 확인
5. 좌측 하단 "시트 1" 탭 클릭하여 작업 시작

> 💡 나머지 CSV는 "데이터 소스" → "새 데이터 소스" 로 추가

---

## Step 2: Sheet 1 — KPI Overview 만들기 (20분)

### 2-1. DAU 라인 차트
1. `date`를 **열(Columns)**로 드래그 → 자동으로 연속 날짜
2. `dau`를 **행(Rows)**로 드래그
3. 마크(Marks)에서 **라인** 선택
4. `dau` 우클릭 → "테이블 계산 추가" → "이동 평균" → 7일
5. 색상: `#3182F6` (토스 블루)

### 2-2. GMV 듀얼 축
1. `gmv`를 행(Rows)의 두번째에 드래그
2. 우측 축 우클릭 → "듀얼 축" 선택
3. 축 동기화 체크
4. GMV 마크를 **영역(Area)**로 변경
5. 투명도 30%로 설정

### 2-3. KPI 카드 추가
1. 새 시트에서 AGG(dau)를 텍스트 마크에 추가
2. 서식 → 숫자 → "K" 단위 (예: 5.2K)
3. 같은 방법으로 GMV, Fee Revenue 카드 생성

---

## Step 3: Sheet 2 — Funnel Chart 만들기 (15분)

1. 새 데이터 소스: `exports/funnel_data.csv`
2. `step_name`을 **행(Rows)**로 (정렬: step_order 기준)
3. `users`를 **열(Columns)**로
4. 마크: **바(Bar)**
5. `pct_from_start`를 레이블(Label)에 추가
6. 색상: 단계별 그라데이션 (진한 파랑 → 연한 파랑)
7. 바 폭을 점점 좁게 → 퍼널 형태 완성

---

## Step 4: Sheet 3 — Retention Heatmap 만들기 (20분)

1. 새 데이터 소스: `exports/retention_cohort.csv`
2. `cohort_week`을 **행(Rows)**로
3. `day_n`을 **열(Columns)**로 (불연속)
4. `retention_rate`를 **색상(Color)**에 드래그
5. 마크 유형: **사각형(Square)**
6. 색상 편집:
   - 팔레트: 순차적 → "녹색-금색" 또는 커스텀
   - 범위: 0% ~ 80%
7. `retention_rate`를 **레이블(Label)**에도 추가 (소수점 1자리)

> 💡 이 히트맵이 면접에서 가장 임팩트 있는 시각화입니다!

---

## Step 5: Sheet 4 — Revenue Dashboard 만들기 (15분)

1. 새 데이터 소스: `exports/transaction_summary.csv`
2. **월별 GMV Bar Chart**: `month` → 열, `total_amount` → 행, `transaction_type` → 색상
3. **시간대별 히트맵**: `day_of_week` → 행, `hour` → 열, `txn_count` → 색상
4. **은행별 Bar**: `bank_name` → 행, `txn_count` → 열 (정렬: 내림차순)

---

## Step 6: 대시보드 조립 (10분)

1. 하단 탭에서 "새 대시보드" 클릭
2. 크기: **자동** 또는 **1200 × 900 px**
3. 좌측에서 4개 시트를 드래그하여 배치
4. "필터" 동작 추가:
   - 날짜 범위 필터 → 모든 시트에 적용
5. 제목 추가: "QuickPay DataOps Dashboard"

---

## Step 7: Tableau Public에 게시 (3분)

1. **서버** → **Tableau Public에 저장**
2. Tableau Public 계정으로 로그인
3. 워크북 이름 입력: "QuickPay-DataOps-Dashboard"
4. **저장** 클릭
5. 브라우저에서 자동으로 열림
6. URL 복사하여 포트폴리오에 추가!

---

## 🎯 완성 후 체크리스트

- [ ] 4개 시트가 모두 정상 동작
- [ ] 날짜 필터가 전체 대시보드에 연동
- [ ] 숫자 포맷 (천 단위 쉼표, 퍼센트 등) 적용
- [ ] 색상이 일관성 있게 적용 (토스 블루 계열)
- [ ] 대시보드 제목과 각 시트 제목 명확
- [ ] Tableau Public URL 정상 접근 가능
- [ ] 포트폴리오 README에 URL 링크 추가

---

## 💡 Pro Tips

1. **반응형**: 대시보드 크기를 "자동"으로 설정하면 모바일에서도 잘 보임
2. **툴팁**: 마크에 마우스 올리면 상세 정보 표시 — 정보량을 높이는 핵심
3. **참조선**: 평균, 목표값에 참조선을 추가하면 컨텍스트 전달력 ↑
4. **스토리**: Tableau 스토리 기능으로 발표 자료 형태로도 구성 가능
