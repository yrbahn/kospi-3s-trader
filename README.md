# 📈 kospi-3s-trader: LLM 기반 한국 주식 자동매매 시스템

> **논문 기반 구현**: [3S-Trader: A Multi-LLM Framework for Adaptive Stock Scoring, Strategy, and Selection in Portfolio Optimization](https://arxiv.org/abs/2510.17393) (arXiv:2510.17393)

**코스피/코스닥 시가총액 Top 200** 종목을 대상으로 6개의 LLM 에이전트가 협력하여 주간 포트폴리오를 자동으로 구성하고 실제 매매를 실행하는 시스템입니다.

[![GitHub](https://img.shields.io/badge/GitHub-kospi--3s--trader-blue)](https://github.com/yrbahn/kospi-3s-trader)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎯 주요 특징

- ✅ **완전 자동화**: 주간 분석부터 실제 매매까지 무인 운영
- ✅ **6개 LLM 에이전트**: 뉴스/기술적/재무 분석 → 점수 평가 → 종목 선택 → 전략 개선
- ✅ **한국어 프롬프트**: 모든 분석과 근거를 한국어로 출력
- ✅ **실시간 데이터**: MarketSense-AI 데이터베이스와 통합
- ✅ **실제 매매**: 한국투자증권 API 연동 (시장가 주문)
- ✅ **대시보드**: Streamlit 기반 실시간 모니터링

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    3S-Trader Framework                       │
│              (한국 주식 시장 특화 버전)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stage 1: 시장 데이터 분석 (Market Analysis)                  │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ 뉴스     │ │ 기술적 지표   │ │ 재무제표     │             │
│  │ 에이전트  │ │ 에이전트     │ │ 에이전트      │            │
│  │ (한국어) │ │ (한국어)     │ │ (한국어)      │            │
│  └────┬─────┘ └──────┬───────┘ └──────┬───────┘            │
│       │              │                │                     │
│       └──────────────┼────────────────┘                     │
│                      ▼                                      │
│  Stage 2: 종목 점수 평가 (Stock Scoring) - 한국어            │
│  ┌─────────────────────────────────┐                        │
│  │         점수 에이전트            │                        │
│  │  재무건전성 (1-10) | 성장잠재력   │                        │
│  │  뉴스감성 | 뉴스영향력           │                        │
│  │  가격모멘텀 | 변동성리스크        │                        │
│  │  → 한국어 근거 출력              │                        │
│  └────────────────┬────────────────┘                        │
│                   ▼                                         │
│  Stage 3: 종목 선택 (Stock Selection)                        │
│  ┌─────────────────────────────────┐                        │
│  │       선택 에이전트              │ ◄── 현재 전략           │
│  │  최대 5종목 + 비중 배분          │                        │
│  │  DB에서 종목명 자동 조회          │                        │
│  └────────────────┬────────────────┘                        │
│                   ▼                                         │
│  Stage 4: 실제 매매 (Order Execution)                        │
│  ┌─────────────────────────────────┐                        │
│  │    한국투자증권 API 연동          │                        │
│  │  시장가 매수/매도 (09:00)         │                        │
│  │  계좌: 67439904-01               │                        │
│  └─────────────────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 자동 실행 워크플로우

### 📅 주간 사이클

```
일요일 저녁 20:00
  ↓
┌─────────────────────────────────────┐
│ 1. 포트폴리오 분석 (analyze_only.py)  │
│   - 200개 종목 데이터 수집            │
│   - AI 점수 평가 (병렬 10개)          │
│   - 포트폴리오 선택 (최대 5종목)       │
│   - DB 저장                          │
│   ⏱️ 소요 시간: 약 14분              │
└─────────────────────────────────────┘
  ↓
텔레그램 알림 📱
  ↓
월요일 아침 09:00
  ↓
┌─────────────────────────────────────┐
│ 2. 매매 실행 (execute_portfolio.py)  │
│   - DB에서 포트폴리오 읽기            │
│   - 기존 종목 매도 (시장가)           │
│   - 신규 종목 매수 (시장가)           │
│   - 실행 기록 업데이트                │
│   ⏱️ 소요 시간: 약 1분               │
└─────────────────────────────────────┘
  ↓
텔레그램 알림 📱
  ↓
다음 주 일요일까지 보유 → 반복
```

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/yrbahn/kospi-3s-trader.git
cd kospi-3s-trader
```

### 2. 환경 설정

```bash
# .env 파일 생성 및 설정
cp .env.example .env

# 필수 환경변수
OPENAI_API_KEY=sk-your-api-key

# 한국투자증권 API (실제 매매용)
KIS_APP_KEY=your-app-key
KIS_APP_SECRET=your-app-secret
KIS_ACCOUNT_NO=your-account-no

# MarketSense-AI DB (데이터 소스)
DATABASE_URL=postgresql://user@localhost:5432/marketsense
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 대시보드 실행

```bash
# Streamlit 대시보드 (http://localhost:8502)
streamlit run dashboard.py
```

### 5. 수동 분석 실행

```bash
# 포트폴리오 분석만 (주문 없음)
python analyze_only.py

# 실제 매매 실행 (DB에 저장된 포트폴리오 기준)
python execute_portfolio.py
```

## ⚙️ 설정 파일

### `config/config.yaml` - 메인 설정

```yaml
llm:
  model: gpt-4o-mini        # 모델 (gpt-4o-mini: 저렴, gpt-4o: 고성능)
  temperature: 0.3          # 응답 다양성 (낮을수록 일관적)
  max_tokens: 4096          # 최대 토큰 수

trading:
  max_portfolio_stocks: 5            # 최대 보유 종목 수
  technical_lookback_weeks: 4        # 기술적 지표 룩백 기간
  fundamental_lookback_quarters: 4   # 재무제표 룩백 기간
  news_lookback_days: 7              # 뉴스 수집 기간

data:
  db_url: postgresql://user@localhost:5432/marketsense
  universe_file: config/market_top200.json  # 분석 대상 종목
```

### `config/prompts.yaml` - LLM 프롬프트 (한국어)

모든 LLM 에이전트의 시스템/유저 프롬프트를 한국어로 관리합니다.

**주요 프롬프트:**
- `news_agent`: 뉴스 분석 (한국어)
- `technical_agent`: 기술적 분석 (한국어)
- `fundamental_agent`: 재무 분석 (한국어)
- **`score_agent`**: 6차원 점수 평가 (**한국어 근거 출력**)
- `selector_agent`: 포트폴리오 선택
- `strategy_agent`: 전략 개선

**최근 업데이트 (2026-02-12):**
```yaml
score_agent:
  system: |
    ...
    **중요**: 모든 분석과 근거는 한국어로 작성하세요.
  user: |
    **점수 차원** (1-10점, 한국어로 답변):
    
    1. **재무건전성** (financial_health)
    2. **성장잠재력** (growth_potential)
    3. **뉴스감성** (news_sentiment)
    4. **뉴스영향력** (news_impact)
    5. **가격모멘텀** (price_momentum)
    6. **변동성리스크** (volatility_risk)
    
    rationale: "<각 점수에 대한 한국어 근거...>"
```

## 📊 6차원 점수 체계

| 차원 | 영문명 | 설명 | 높을수록 |
|------|-------|------|---------|
| 🏦 **재무건전성** | financial_health | 수익성, 부채, 현금흐름 | 펀더멘털 강하고 단기 리스크 낮음 |
| 🚀 **성장잠재력** | growth_potential | 투자 계획, 혁신, 확장 전망 | 장기 수익 잠재력 큼 |
| 📰 **뉴스감성** | news_sentiment | 최근 뉴스 감성 극성 | 긍정적 뉴스 많음 |
| 💥 **뉴스영향력** | news_impact | 뉴스 범위/지속성 | 지속적이고 광범위한 영향 |
| 📊 **가격모멘텀** | price_momentum | 최근 가격 추세 | 강하고 일관된 상승 |
| ⚡ **변동성리스크** | volatility_risk | 가격 변동 수준 | 변동성 높고 위험 (낮을수록 좋음) |

## 🔗 MarketSense-AI 통합

**중복 데이터 수집 제거, 실시간 데이터 공유**

| 데이터 | 소스 | 업데이트 주기 |
|--------|------|--------------|
| 📈 주가 데이터 | MarketSense-AI DB | 매일 자동 수집 |
| 📊 기술적 지표 | MarketSense-AI DB | 실시간 계산 |
| 📰 뉴스 | MarketSense-AI DB | 매일 수집 (2,884 종목) |
| 💰 재무제표 | MarketSense-AI DB | 분기별 (DART API) |
| 🤖 AI 분석 | MarketSense-AI RAG | LLM 증권사 리포트 분석 |

**장점:**
- ✅ 2,884개 전체 상장 종목 데이터 접근
- ✅ 자동화된 데이터 파이프라인 활용
- ✅ RAG, 증권사 리포트 등 추가 데이터 활용 가능
- ✅ 텔레그램 봇 통합

## 🤖 자동 실행 설정 (Cron)

**OpenClaw Gateway Cron을 통한 자동 실행:**

### 등록된 작업

```bash
# 1. 일요일 20:00 - 포트폴리오 분석
매주 일요일 20:00
├─ analyze_only.py 실행
├─ 200개 종목 분석 (14분)
└─ 텔레그램 알림

# 2. 월요일 09:00 - 매매 실행
매주 월요일 09:00
├─ execute_portfolio.py 실행
├─ 한국투자증권 API 주문 (1분)
└─ 텔레그램 알림
```

### 수동 관리

```bash
# Cron 작업 확인
openclaw cron list

# 작업 활성화/비활성화
openclaw cron update --id <job-id> --enabled true/false

# 즉시 실행
openclaw cron run --id <job-id>
```

## 💰 매매 전략

### 주문 방식

- **매수**: 시장가 (장 시작 즉시)
- **매도**: 시장가 (기존 종목 정리)
- **체결 보장**: 시장가로 거의 100% 체결
- **실행 계좌**: 한국투자증권 (67439904-01)

### 포트폴리오 구성

- **최대 종목**: 5개
- **현금 사용**: 80% (나머지 20% 현금 보유)
- **종목 선택**: 저가 종목 우선 (잔고 부족 방지)
- **비중 배분**: AI가 종목별 비중 결정 (0-100%)

### 리밸런싱

- **주기**: 매주 (월요일 09:00)
- **방식**: 전량 매도 → 신규 매수
- **근거**: AI 점수 + 전략에 따라 매주 재평가

## 📊 대시보드

**Streamlit 기반 실시간 모니터링** (http://localhost:8502)

```bash
# 대시보드 실행
streamlit run dashboard.py
```

**기능:**
- 📈 최신 포트폴리오 현황
- 📊 종목별 점수 시각화
- 💰 누적 수익률 차트
- 📋 주간별 실행 이력
- 🔍 AI 분석 근거 확인

## 📁 프로젝트 구조

```
kospi-3s-trader/
├── README.md                          # 프로젝트 문서 (이 파일)
├── requirements.txt                   # Python 의존성
├── .env.example                       # 환경변수 예시
├── .gitignore
├── config/
│   ├── config.yaml                    # 메인 설정
│   ├── prompts.yaml                   # LLM 프롬프트 (한국어)
│   └── market_top200.json             # 분석 대상 종목 (200개)
├── src/
│   ├── agents/                        # 6개 LLM 에이전트
│   │   ├── base_agent.py              # 기본 클래스
│   │   ├── news_agent.py              # 뉴스 분석 (한국어)
│   │   ├── technical_agent.py         # 기술적 분석 (한국어)
│   │   ├── fundamental_agent.py       # 재무 분석 (한국어)
│   │   ├── score_agent.py             # 점수 평가 (한국어 근거)
│   │   ├── selector_agent.py          # 포트폴리오 선택
│   │   └── strategy_agent.py          # 전략 개선
│   ├── data/
│   │   ├── data_loader.py             # MarketSense-AI DB 연동
│   │   └── data_manager.py            # 데이터 오케스트레이션
│   ├── kis/
│   │   └── kis_client.py              # 한국투자증권 API
│   └── utils/
│       └── helpers.py                 # 유틸리티
├── analyze_only.py                    # 포트폴리오 분석 (주문 없음)
├── execute_portfolio.py               # 실제 매매 실행
├── dashboard.py                       # Streamlit 대시보드
├── logs/                              # 실행 로그
├── debug/                             # AI 응답 디버그
└── results/                           # 백테스트 결과
```

## 🎯 분석 대상 종목

**코스피/코스닥 시가총액 Top 200**

`config/market_top200.json`에서 관리됩니다.

**주요 종목 예시:**
- 삼성전자, SK하이닉스, LG에너지솔루션
- 삼성바이오로직스, 현대차, 기아
- NAVER, 카카오, KB금융
- 에코프로, 에코프로비엠, 포스코퓨처엠
- ...

## 💸 비용 안내

### OpenAI API 비용 (gpt-4o-mini)

**주간 분석 (analyze_only.py):**
- 200개 종목 × 3개 에이전트 (뉴스/기술/재무) = 600회
- 200개 종목 × 1개 점수 에이전트 = 200회
- 1개 선택 에이전트 = 1회
- **총 약 800-1000회 API 호출**
- **예상 비용: $0.25-0.50 / 주**

**비용 절감:**
- gpt-4o 대신 gpt-4o-mini 사용 (20배 저렴)
- 병렬 처리로 시간 단축 (10개 동시)

### 한국투자증권 API

- **모의투자**: 무료
- **실전투자**: 거래 수수료 발생

## 📏 성능 지표 (백테스트)

*준비 중* - 충분한 데이터 수집 후 백테스트 결과 업데이트 예정

## ⚠️ 면책 사항

**주의사항:**
- ⚠️ 이 프로젝트는 **연구/교육 목적**으로 제작되었습니다.
- ⚠️ **실제 투자에 사용하여 발생하는 손실에 대해 책임지지 않습니다.**
- ⚠️ 과거 성과가 미래 수익을 보장하지 않습니다.
- ⚠️ LLM의 분석이 항상 정확하지 않을 수 있습니다.
- ⚠️ 시장가 주문으로 인한 슬리피지 발생 가능합니다.

**권장사항:**
- ✅ 소액으로 먼저 테스트
- ✅ 모의투자 계좌 사용 권장
- ✅ 정기적인 모니터링 필요
- ✅ 리스크 관리 철저히

## 🔗 관련 프로젝트

- **MarketSense-AI**: 한국 주식 데이터 수집 및 AI 분석 플랫폼
  - https://github.com/yrbahn/marketsense-ai
  - 2,884개 전체 상장 종목 지원
  - RAG 기반 증권사 리포트 분석
  - 텔레그램 봇 통합

## 📄 라이선스

MIT License

## 🙏 참고 논문

```bibtex
@article{ahmad2025threesTrader,
  title={3S-Trader: A Multi-LLM Framework for Adaptive Stock Scoring, Strategy, and Selection in Portfolio Optimization},
  author={Ahmad, Hussain and others},
  journal={arXiv preprint arXiv:2510.17393},
  year={2025}
}
```

## 📞 문의

- GitHub Issues: https://github.com/yrbahn/kospi-3s-trader/issues
- Email: yrbahn@gmail.com

---

**Made with ❤️ by Youngrok Bahn**
