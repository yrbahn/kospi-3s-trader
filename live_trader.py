#!/usr/bin/env python3
"""
실시간 모의 투자 시스템
매주 월요일 3S-Trader 분석을 실행하고 포트폴리오를 리밸런싱합니다.
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_manager import DataManager
from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.agents.selector_agent import SelectorAgent
from src.agents.strategy_agent import StrategyAgent

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("live_trader")

PORTFOLIO_FILE = Path(__file__).parent / "portfolio_state.json"
INITIAL_CASH = 10_000_000  # 1천만원


class LiveTrader:
    """실시간 모의 투자 시스템"""

    def __init__(self, config: dict, prompts: dict):
        self.config = config
        self.prompts = prompts
        
        # 데이터 매니저
        self.data_manager = DataManager(config)
        
        # 에이전트
        self.news_agent = NewsAgent(config, prompts)
        self.technical_agent = TechnicalAgent(config, prompts)
        self.fundamental_agent = FundamentalAgent(config, prompts)
        self.score_agent = ScoreAgent(config, prompts)
        self.selector_agent = SelectorAgent(config, prompts)
        self.strategy_agent = StrategyAgent(config, prompts)
        
        # 포트폴리오 상태 로드
        self.portfolio = self._load_portfolio()

    def _load_portfolio(self) -> dict:
        """포트폴리오 상태 로드"""
        if PORTFOLIO_FILE.exists():
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 초기 포트폴리오
            return {
                "cash": INITIAL_CASH,
                "holdings": {},  # {ticker: {name, shares, avg_price}}
                "total_value": INITIAL_CASH,
                "strategy": self.prompts.get("initial_strategy", "균형 잡힌 접근법"),
                "history": [],  # [{date, action, ...}]
            }

    def _save_portfolio(self):
        """포트폴리오 상태 저장"""
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.portfolio, f, ensure_ascii=False, indent=2)

    def _get_current_prices(self, tickers: list) -> dict:
        """현재 가격 조회"""
        prices = {}
        today = datetime.now().strftime("%Y%m%d")
        
        for ticker in tickers:
            data = self.data_manager.get_all_universe_data([ticker], lookback_weeks=1)
            if ticker in data and data[ticker].get('prices'):
                latest = data[ticker]['prices'][-1]
                prices[ticker] = latest.get('close', 0)
        
        return prices

    def _calculate_portfolio_value(self, current_prices: dict) -> float:
        """현재 포트폴리오 가치 계산"""
        total = self.portfolio["cash"]
        
        for ticker, holding in self.portfolio["holdings"].items():
            price = current_prices.get(ticker, 0)
            total += holding["shares"] * price
        
        return total

    def run_weekly_analysis(self) -> dict:
        """주간 3S-Trader 분석 실행"""
        logger.info("🚀 주간 3S-Trader 분석 시작")
        
        today = datetime.now().strftime("%Y%m%d")
        
        # Stage 1: 데이터 수집
        logger.info("📊 Stage 1: 시장 데이터 분석...")
        all_data = self.data_manager.collect_all_data(today)
        
        # Stage 2: 종목 점수 평가
        logger.info("🎯 Stage 2: 종목 점수 평가...")
        all_scores = []
        
        for ticker, data in all_data.items():
            name = data["name"]
            
            # 3개 에이전트 분석
            news_analysis = self.news_agent.analyze(ticker, name, data["news_text"])
            tech_summary = data["technical"].get("summary", "데이터 없음")
            tech_analysis = self.technical_agent.analyze(ticker, name, tech_summary)
            fund_analysis = self.fundamental_agent.analyze(ticker, name, data["fundamental_text"])
            
            # 점수 평가
            scores = self.score_agent.score(
                ticker, name,
                news_analysis, tech_analysis, fund_analysis
            )
            all_scores.append(scores)
        
        # Stage 3: 포트폴리오 구성
        logger.info("📋 Stage 3: 포트폴리오 구성...")
        scores_text = ScoreAgent.format_scores_text(all_scores)
        new_portfolio = self.selector_agent.select(
            scores_text, self.portfolio["strategy"]
        )
        
        return new_portfolio

    def rebalance(self, new_portfolio: dict) -> dict:
        """포트폴리오 리밸런싱"""
        logger.info("🔄 포트폴리오 리밸런싱...")
        
        # 현재 가격 조회
        all_tickers = set()
        for item in new_portfolio.get("portfolio", []):
            all_tickers.add(item["code"])
        for ticker in self.portfolio["holdings"].keys():
            all_tickers.add(ticker)
        
        current_prices = self._get_current_prices(list(all_tickers))
        
        # 현재 포트폴리오 가치 계산
        current_value = self._calculate_portfolio_value(current_prices)
        
        # 매도 (새 포트폴리오에 없는 종목)
        new_codes = {item["code"] for item in new_portfolio.get("portfolio", [])}
        sells = []
        
        for ticker in list(self.portfolio["holdings"].keys()):
            if ticker not in new_codes:
                holding = self.portfolio["holdings"][ticker]
                price = current_prices.get(ticker, 0)
                proceeds = holding["shares"] * price
                
                sells.append({
                    "ticker": ticker,
                    "name": holding["name"],
                    "shares": holding["shares"],
                    "price": price,
                    "proceeds": proceeds,
                })
                
                self.portfolio["cash"] += proceeds
                del self.portfolio["holdings"][ticker]
        
        # 매수 (새 포트폴리오 종목)
        buys = []
        
        for item in new_portfolio.get("portfolio", []):
            ticker = item["code"]
            name = item["name"]
            target_weight = item["weight"]
            price = current_prices.get(ticker, 0)
            
            if price == 0:
                continue
            
            target_value = current_value * target_weight
            shares = int(target_value / price)
            cost = shares * price
            
            if shares > 0 and self.portfolio["cash"] >= cost:
                buys.append({
                    "ticker": ticker,
                    "name": name,
                    "shares": shares,
                    "price": price,
                    "cost": cost,
                })
                
                self.portfolio["cash"] -= cost
                self.portfolio["holdings"][ticker] = {
                    "name": name,
                    "shares": shares,
                    "avg_price": price,
                }
        
        # 포트폴리오 가치 업데이트
        self.portfolio["total_value"] = self._calculate_portfolio_value(current_prices)
        
        # 이력 기록
        self.portfolio["history"].append({
            "date": datetime.now().isoformat(),
            "total_value": self.portfolio["total_value"],
            "cash": self.portfolio["cash"],
            "sells": sells,
            "buys": buys,
        })
        
        return {
            "sells": sells,
            "buys": buys,
            "current_value": current_value,
            "new_value": self.portfolio["total_value"],
        }

    def generate_report(self, rebalance_result: dict) -> str:
        """Telegram 리포트 생성"""
        lines = []
        lines.append("📊 **3S-Trader 주간 리포트**")
        lines.append(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # 포트폴리오 가치
        current = rebalance_result["current_value"]
        new = rebalance_result["new_value"]
        change = new - INITIAL_CASH
        change_pct = (change / INITIAL_CASH) * 100
        
        lines.append("💰 **포트폴리오 가치**")
        lines.append(f"현재: {new:,.0f}원")
        lines.append(f"누적 수익: {change:+,.0f}원 ({change_pct:+.2f}%)")
        lines.append(f"현금: {self.portfolio['cash']:,.0f}원")
        lines.append("")
        
        # 매도
        if rebalance_result["sells"]:
            lines.append("📉 **매도**")
            for sell in rebalance_result["sells"]:
                lines.append(
                    f"- {sell['name']}({sell['ticker']}): "
                    f"{sell['shares']:,}주 @ {sell['price']:,.0f}원 "
                    f"= {sell['proceeds']:,.0f}원"
                )
            lines.append("")
        
        # 매수
        if rebalance_result["buys"]:
            lines.append("📈 **매수**")
            for buy in rebalance_result["buys"]:
                lines.append(
                    f"- {buy['name']}({buy['ticker']}): "
                    f"{buy['shares']:,}주 @ {buy['price']:,.0f}원 "
                    f"= {buy['cost']:,.0f}원"
                )
            lines.append("")
        
        # 현재 보유
        lines.append("📋 **현재 보유**")
        if self.portfolio["holdings"]:
            for ticker, holding in self.portfolio["holdings"].items():
                lines.append(f"- {holding['name']}({ticker}): {holding['shares']:,}주")
        else:
            lines.append("- 현금 100%")
        
        return "\n".join(lines)

    def run(self):
        """메인 실행"""
        try:
            # 주간 분석
            new_portfolio = self.run_weekly_analysis()
            
            # 리밸런싱
            result = self.rebalance(new_portfolio)
            
            # 포트폴리오 저장
            self._save_portfolio()
            
            # 리포트 생성
            report = self.generate_report(result)
            
            logger.info("✅ 주간 실행 완료")
            print("\n" + report)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """메인 함수"""
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # LiveTrader 실행
    trader = LiveTrader(config, prompts)
    report = trader.run()
    
    # TODO: Telegram 메시지 전송 (openclaw message 사용)
    # 지금은 출력만


if __name__ == "__main__":
    main()
