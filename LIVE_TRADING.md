# 실시간 모의 투자 가이드

## 📋 개요

**kospi-3s-trader**를 실시간 모의 투자 시스템으로 사용하는 방법입니다.

---

## 🚀 시스템 구조

### 1. `live_trader.py`
- 매주 3S-Trader 분석 실행
- 포트폴리오 리밸런싱
- Telegram 알림

### 2. `portfolio_state.json`
- 현재 포트폴리오 상태 저장
- 초기 자본: 10,000,000원 (1천만원)
- 보유 종목 + 현금

### 3. OpenClaw Cron
- 매주 월요일 오전 9시 자동 실행

---

## 📦 설치

### 1. 초기 포트폴리오 설정

`portfolio_state.json` 파일이 이미 생성되어 있습니다:

```json
{
  "cash": 10000000,
  "holdings": {},
  "total_value": 10000000,
  "strategy": "균형 잡힌 접근법...",
  "history": []
}
```

### 2. 수동 테스트

```bash
cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader
python3 live_trader.py
```

**예상 시간:** 5-10분 (50종목 분석)

---

## ⏰ OpenClaw Cron 설정

### 방법 1: OpenClaw CLI (추천)

```bash
openclaw cron add \
  --name "kospi-3s-trader 주간 실행" \
  --schedule "0 9 * * 1" \
  --command "cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader && python3 live_trader.py"
```

**설명:**
- `0 9 * * 1`: 매주 월요일 오전 9시
- 한국 시간 (Asia/Seoul)

### 방법 2: OpenClaw Gateway Config

`~/.openclaw/config/gateway.yaml`에 추가:

```yaml
cron:
  jobs:
    - name: "kospi-3s-trader 주간 실행"
      schedule:
        kind: "cron"
        expr: "0 9 * * 1"
        tz: "Asia/Seoul"
      payload:
        kind: "systemEvent"
        text: "cd /Users/yrbahn/.openclaw/workspace/kospi-3s-trader && python3 live_trader.py"
      sessionTarget: "main"
      enabled: true
```

---

## 📊 리포트 예시

```
📊 **3S-Trader 주간 리포트**
🕒 2026-02-11 09:00

💰 **포트폴리오 가치**
현재: 10,250,000원
누적 수익: +250,000원 (+2.50%)
현금: 1,500,000원

📈 **매수**
- 삼성전자(005930): 15주 @ 165,800원 = 2,487,000원
- SK하이닉스(000660): 10주 @ 180,000원 = 1,800,000원

📋 **현재 보유**
- 삼성전자(005930): 15주
- SK하이닉스(000660): 10주
- 삼성바이오로직스(207940): 5주
```

---

## 🔔 Telegram 알림 설정

### 옵션 1: OpenClaw Message Tool (구현 예정)

`live_trader.py`의 `main()` 함수에서:

```python
# Telegram 메시지 전송
import subprocess
subprocess.run([
    "openclaw", "message", "send",
    "--channel", "telegram",
    "--to", "7824301023",
    "--message", report
])
```

### 옵션 2: 직접 구현

Python `telegram-send` 패키지 사용

---

## 📈 포트폴리오 조회

```bash
cat /Users/yrbahn/.openclaw/workspace/kospi-3s-trader/portfolio_state.json
```

또는:

```python
python3 << EOF
import json
with open('portfolio_state.json', 'r') as f:
    p = json.load(f)
print(f"현금: {p['cash']:,}원")
print(f"총 가치: {p['total_value']:,}원")
for ticker, holding in p['holdings'].items():
    print(f"- {holding['name']}: {holding['shares']}주")
EOF
```

---

## 🛠️ 설정 변경

### 초기 자본 변경

`live_trader.py`:

```python
INITIAL_CASH = 50_000_000  # 5천만원으로 변경
```

### 종목 수 변경

`config/config.yaml`:

```yaml
universe:
  tickers:
    - "005930"  # 삼성전자
    - "000660"  # SK하이닉스
    # ... 원하는 종목만
```

### 투자 전략 변경

`config/prompts.yaml`:

```yaml
initial_strategy: |
  성장주 중심 전략: 성장잠재력과 가격모멘텀이 높은 종목을 우선 선택하고...
```

---

## ⚠️ 주의사항

1. **모의 투자입니다!** 실제 매매는 발생하지 않습니다.
2. **데이터 의존성:** MarketSense-AI DB가 최신이어야 합니다.
3. **API 비용:** OpenAI API 비용 발생 (주당 약 50종목 × 4 = $1~2)
4. **실행 시간:** 5-10분 소요

---

## 🐛 문제 해결

### 에러: "MarketSense-AI DB 연결 실패"

```bash
# MarketSense-AI 데이터 업데이트
cd /Users/yrbahn/.openclaw/workspace/marketsense-ai
bash scripts/daily_update.sh
```

### 에러: "OpenAI API key not found"

```bash
# .env 파일 확인
cat .env | grep OPENAI_API_KEY
```

### 로그 확인

```bash
tail -f logs/3s_trader.log
```

---

## 📞 문의

문제가 있으면 @royy_1975에게 문의하세요!
