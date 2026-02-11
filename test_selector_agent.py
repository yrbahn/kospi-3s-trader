#!/usr/bin/env python3
"""SelectorAgent 상세 테스트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.selector_agent import SelectorAgent
from src.agents.score_agent import ScoreAgent


def main():
    print("\n🔍 SelectorAgent 상세 테스트\n")
    
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # 테스트용 점수 데이터 (5개 종목)
    all_scores = [
        {
            "code": "005930",
            "name": "삼성전자",
            "financial_health": 8,
            "growth_potential": 7,
            "news_sentiment": 5,
            "news_impact": 6,
            "price_momentum": 6,
            "volatility_risk": 5,
        },
        {
            "code": "000660",
            "name": "SK하이닉스",
            "financial_health": 7,
            "growth_potential": 8,
            "news_sentiment": 7,
            "news_impact": 7,
            "price_momentum": 8,
            "volatility_risk": 6,
        },
        {
            "code": "373220",
            "name": "LG에너지솔루션",
            "financial_health": 6,
            "growth_potential": 9,
            "news_sentiment": 6,
            "news_impact": 8,
            "price_momentum": 5,
            "volatility_risk": 7,
        },
        {
            "code": "207940",
            "name": "삼성바이오로직스",
            "financial_health": 9,
            "growth_potential": 7,
            "news_sentiment": 6,
            "news_impact": 5,
            "price_momentum": 7,
            "volatility_risk": 4,
        },
        {
            "code": "005380",
            "name": "현대차",
            "financial_health": 7,
            "growth_potential": 6,
            "news_sentiment": 5,
            "news_impact": 6,
            "price_momentum": 6,
            "volatility_risk": 5,
        },
    ]
    
    # 점수를 텍스트로 포맷
    scores_text = ScoreAgent.format_scores_text(all_scores)
    
    print("📊 입력 데이터:")
    print("=" * 80)
    print(scores_text)
    print("=" * 80)
    print()
    
    # 투자 전략
    strategy = prompts.get("initial_strategy", "균형 잡힌 접근법")
    print(f"💡 투자 전략:\n{strategy}\n")
    
    # SelectorAgent 실행
    print("🤖 SelectorAgent 실행 중...")
    print("=" * 80)
    
    try:
        selector_agent = SelectorAgent(config, prompts)
        portfolio = selector_agent.select(scores_text, strategy)
        
        print("✅ SelectorAgent 성공!")
        print("=" * 80)
        print("📋 포트폴리오:")
        print("=" * 80)
        
        for item in portfolio.get("portfolio", []):
            print(f"  {item['name']}({item['code']}): {item['weight']*100:.1f}%")
        
        cash = portfolio.get("cash_weight", 0)
        print(f"  현금: {cash*100:.1f}%")
        print()
        print(f"근거:\n{portfolio.get('rationale', 'N/A')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ SelectorAgent 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
