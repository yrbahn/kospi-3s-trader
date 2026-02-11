#!/usr/bin/env python3
"""StrategyAgent 상세 테스트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.strategy_agent import StrategyAgent


def main():
    print("\n🔍 StrategyAgent 상세 테스트\n")
    
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # 현재 전략
    current_strategy = "균형 잡힌 접근법: 재무건전성이 높고 변동성이 낮은 종목을 우선 선택하되, 성장잠재력과 긍정적 뉴스감성을 가진 종목에 가중치를 부여합니다."
    
    # 성과 데이터
    portfolio_return = 2.5
    market_avg_return = 1.8
    
    # 점수 및 수익률 데이터
    scores_returns = [
        {
            "code": "005930",
            "name": "삼성전자",
            "scores": {
                "financial_health": 8,
                "growth_potential": 7,
                "news_sentiment": 5,
                "news_impact": 6,
                "price_momentum": 6,
                "volatility_risk": 5,
            },
            "return": 3.2,
        },
        {
            "code": "000660",
            "name": "SK하이닉스",
            "scores": {
                "financial_health": 7,
                "growth_potential": 8,
                "news_sentiment": 7,
                "news_impact": 7,
                "price_momentum": 8,
                "volatility_risk": 6,
            },
            "return": 5.1,
        },
        {
            "code": "373220",
            "name": "LG에너지솔루션",
            "scores": {
                "financial_health": 6,
                "growth_potential": 9,
                "news_sentiment": 6,
                "news_impact": 8,
                "price_momentum": 5,
                "volatility_risk": 7,
            },
            "return": -1.2,
        },
    ]
    
    # 포맷팅
    scores_returns_text = StrategyAgent.format_scores_returns(
        [s["scores"] | {"code": s["code"], "name": s["name"]} for s in scores_returns],
        {s["code"]: s["return"] for s in scores_returns}
    )
    
    # 전략 이력
    strategy_history = [
        {
            "week": "W1(2024-12-02)",
            "strategy": "균형 잡힌 접근법",
            "portfolio_return": 0.015,
            "market_avg_return": 0.012,
        },
        {
            "week": "W2(2024-12-09)",
            "strategy": "성장주 중심 전략",
            "portfolio_return": 0.032,
            "market_avg_return": 0.018,
        },
    ]
    
    history_text = StrategyAgent.format_strategy_history(strategy_history)
    
    print("📊 입력 데이터:")
    print("=" * 80)
    print(f"현재 전략:\n{current_strategy}\n")
    print(f"포트폴리오 수익률: {portfolio_return}%")
    print(f"시장 평균 수익률: {market_avg_return}%\n")
    print(f"점수 및 수익률:\n{scores_returns_text}\n")
    print(f"전략 이력:\n{history_text}")
    print("=" * 80)
    print()
    
    # StrategyAgent 실행
    print("🤖 StrategyAgent 실행 중...")
    print("=" * 80)
    
    try:
        strategy_agent = StrategyAgent(config, prompts)
        new_strategy = strategy_agent.refine_strategy(
            current_strategy=current_strategy,
            portfolio_return=portfolio_return,
            market_avg_return=market_avg_return,
            scores_and_returns=scores_returns_text,
            strategy_history=history_text,
        )
        
        print("✅ StrategyAgent 성공!")
        print("=" * 80)
        print("🔄 새로운 전략:")
        print("=" * 80)
        print(f"전략:\n{new_strategy.get('strategy', 'N/A')}\n")
        print(f"선호 차원: {new_strategy.get('preferred_dimensions', [])}")
        print(f"회피 차원: {new_strategy.get('avoid_dimensions', [])}\n")
        print(f"분석:\n{new_strategy.get('analysis', 'N/A')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ StrategyAgent 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
