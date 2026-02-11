# 한국투자증권 모의투자 연동 가이드

## 📋 개요

**kospi-3s-trader**를 한국투자증권 모의투자 계좌와 연동하는 방법입니다.

---

## 🔑 1. KIS OpenAPI 신청

### 1-1. 회원가입 및 계좌 개설

1. **한국투자증권 가입**
   - https://securities.koreainvestment.com/

2. **모의투자 계좌 개설**
   - 실전투자 > 모의투자
   - 가상 계좌 생성 (즉시 발급)

### 1-2. OpenAPI 신청

1. **KIS Developers 접속**
   - https://apiportal.koreainvestment.com/

2. **앱 등록**
   - 로그인 > 나의 앱
   - 새 앱 등록
   - 앱 이름: "kospi-3s-trader"
   - 서비스: 국내주식, 해외주식, 기타

3. **APP KEY 발급**
   ```
   APP KEY: PSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   APP SECRET: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. **모의투자 신청**
   - "모의투자 신청" 클릭
   - 승인 즉시 완료

---

## ⚙️ 2. 환경 설정

### 2-1. .env 파일 생성

```bash
cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader
cp .env.example .env
```

### 2-2. .env 파일 편집

```bash
# 한국투자증권 OpenAPI (모의투자)
KIS_APP_KEY=PSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KIS_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KIS_ACCOUNT_NO=12345678-01

# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# MarketSense-AI 데이터베이스
DATABASE_URL=postgresql://yrbahn@localhost:5432/marketsense
```

**주의:**
- `KIS_ACCOUNT_NO`: "계좌번호 앞자리-뒷자리" 형식
  - 예: `50123456-01`
  - 모의투자 계좌 정보에서 확인

---

## 🧪 3. 테스트

### 3-1. KIS API 연결 테스트

```bash
cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader
python3 -m src.kis.kis_client
```

**예상 출력:**
```
✅ Access Token 발급 완료

1️⃣ 잔고 조회
현금: 10,000,000원

2️⃣ 현재가 조회
삼성전자 현재가: 165,800원

✅ 테스트 완료
```

### 3-2. 모의 투자 시스템 테스트

```bash
python3 live_trader_kis.py
```

**예상 시간:** 5-10분

**예상 출력:**
```
🚀 주간 3S-Trader 분석 시작
📊 Stage 1: 시장 데이터 분석...
🎯 Stage 2: 종목 점수 평가...
  [삼성전자] 재무:8 성장:7 뉴스감성:5
  [SK하이닉스] 재무:7 성장:8 뉴스감성:7
  ...
📋 Stage 3: 포트폴리오 구성...
🔄 포트폴리오 리밸런싱...
현재 현금: 10,000,000원
현재 보유 종목: 0개
현재 총 자산: 10,000,000원
📈 매수: 삼성전자(005930) 15주 @ 165,800원
✅ 매수 주문 성공: 005930 15주
...

📊 3S-Trader 주간 리포트 (KIS 모의투자)
🕒 2026-02-11 18:00

💰 포트폴리오 가치
현재: 10,000,000원
누적 수익: +0원 (+0.00%)
현금: 5,000,000원

📈 매수
- 삼성전자(005930): 15주 @ 165,800원
- SK하이닉스(000660): 10주 @ 180,000원

📋 현재 보유
- 삼성전자(005930): 15주
- SK하이닉스(000660): 10주
```

---

## ⏰ 4. 자동화 (OpenClaw Cron)

### 4-1. Cron Job 등록

```bash
openclaw cron add \
  --name "3S-Trader KIS 주간 실행" \
  --schedule "0 9 * * 1" \
  --command "cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader && python3 live_trader_kis.py"
```

**설명:**
- 매주 월요일 오전 9시 실행
- KIS 모의투자 계좌에 자동 주문

### 4-2. Cron Job 확인

```bash
openclaw cron list
```

---

## 📊 5. 결과 확인

### 5-1. KIS 홈페이지에서 확인

1. https://securities.koreainvestment.com/ 로그인
2. 모의투자 > 계좌 조회
3. 주문 내역 / 잔고 확인

### 5-2. 거래 이력 파일

```bash
cat trading_history.json
```

```json
[
  {
    "date": "2026-02-11T18:00:00",
    "total_value": 10000000,
    "cash": 5000000,
    "sells": [],
    "buys": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "shares": 15,
        "price": 165800
      }
    ]
  }
]
```

---

## ⚠️ 주의사항

### 1. 모의투자 vs 실전투자

**현재 설정:** 모의투자 (mock=True)

**실전투자로 변경 시:**
```python
# live_trader_kis.py
return KISClient(app_key, app_secret, account_no, mock=False)  # ← False로 변경
```

⚠️ **실전투자는 실제 돈이 들어갑니다!** 충분히 테스트 후 사용하세요.

### 2. API 제한

- **1초당 20건**
- **1분당 1000건**
- 초과 시 429 에러

→ 50종목 분석 시 약 5-10분 소요

### 3. 거래 시간

**한국 주식시장:**
- 정규장: 09:00 ~ 15:30
- 시간외: 16:00 ~ 18:00

**모의투자:**
- 정규장만 가능
- 시간외 주문 불가

→ Cron 실행 시간을 오전 9시로 설정

### 4. 데이터 의존성

**MarketSense-AI DB 필수!**

```bash
# 데이터 업데이트
cd /Users/yrbahn/.openclaw/workspace/marketsense-ai
bash scripts/daily_update.sh
```

---

## 🐛 문제 해결

### 에러: "401 Unauthorized"

```
원인: APP KEY / APP SECRET 오류
해결: .env 파일 확인
```

### 에러: "종목 조회 실패"

```
원인: 종목 코드 오류 (6자리 필요)
해결: config.yaml의 종목 코드 확인
예: "5930" ❌ → "005930" ✅
```

### 에러: "주문 실패"

```
원인: 잔고 부족, 거래 시간 외, API 제한
해결: 
1. KIS 홈페이지에서 잔고 확인
2. 거래 시간 확인 (09:00-15:30)
3. 1분 대기 후 재시도
```

### 로그 확인

```bash
tail -f logs/3s_trader.log
```

---

## 📞 문의

- KIS API 문의: https://apiportal.koreainvestment.com/
- 기술 지원: @royy_1975
