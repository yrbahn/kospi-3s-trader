#!/usr/bin/env python3
"""각 에이전트를 개별적으로 테스트하는 스크립트"""
import sys
from pathlib import Path
import yaml

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.agents.selector_agent import SelectorAgent
from src.agents.strategy_agent import StrategyAgent
from src.data.data_manager import DataManager


def load_config():
    """설정 파일 로드"""
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    return config, prompts


def test_news_agent(config, prompts, data_manager):
    """NewsAgent 테스트"""
    print("=" * 60)
    print("1️⃣ NewsAgent 테스트")
    print("=" * 60)
    
    try:
        # 데이터 수집
        all_data = data_manager.collect_all_data("20241130")
        samsung = all_data.get('005930', {})
        
        if not samsung:
            print("❌ 삼성전자 데이터 없음")
            return None
        
        # NewsAgent 실행
        agent = NewsAgent(config, prompts)
        result = agent.analyze(
            stock_code='005930',
            stock_name='삼성전자',
            news_text=samsung['news_text']
        )
        
        print(f"입력: 뉴스 {len(samsung['news_text'])}자")
        print(f"출력: {len(result)}자")
        print(f"내용 샘플:\n{result[:500]}")
        print("✅ NewsAgent 성공!\n")
        return result
        
    except Exception as e:
        print(f"❌ NewsAgent 실패: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_technical_agent(config, prompts, data_manager):
    """TechnicalAgent 테스트"""
    print("=" * 60)
    print("2️⃣ TechnicalAgent 테스트")
    print("=" * 60)
    
    try:
        # 데이터 수집
        all_data = data_manager.collect_all_data("20241130")
        samsung = all_data.get('005930', {})
        
        if not samsung:
            print("❌ 삼성전자 데이터 없음")
            return None
        
        # TechnicalAgent 실행
        agent = TechnicalAgent(config, prompts)
        result = agent.analyze(
            stock_code='005930',
            stock_name='삼성전자',
            technical_data=samsung['technical']
        )
        
        print(f"입력: 기술적 데이터")
        print(f"  - latest_close: {samsung['technical']['prices']['latest_close']}")
        print(f"  - sma_20: {samsung['technical']['indicators']['sma_20']}")
        print(f"  - rsi: {samsung['technical']['indicators']['rsi']}")
        print(f"출력: {len(result)}자")
        print(f"내용 샘플:\n{result[:500]}")
        print("✅ TechnicalAgent 성공!\n")
        return result
        
    except Exception as e:
        print(f"❌ TechnicalAgent 실패: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_fundamental_agent(config, prompts, data_manager):
    """FundamentalAgent 테스트"""
    print("=" * 60)
    print("3️⃣ FundamentalAgent 테스트")
    print("=" * 60)
    
    try:
        # 데이터 수집
        all_data = data_manager.collect_all_data("20241130")
        samsung = all_data.get('005930', {})
        
        if not samsung:
            print("❌ 삼성전자 데이터 없음")
            return None
        
        # FundamentalAgent 실행
        agent = FundamentalAgent(config, prompts)
        result = agent.analyze(
            stock_code='005930',
            stock_name='삼성전자',
            fundamental_text=samsung['fundamental_text']
        )
        
        print(f"입력: 재무 데이터 {len(samsung['fundamental_text'])}자")
        print(f"출력: {len(result)}자")
        print(f"내용 샘플:\n{result[:500]}")
        print("✅ FundamentalAgent 성공!\n")
        return result
        
    except Exception as e:
        print(f"❌ FundamentalAgent 실패: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_score_agent(config, prompts, news_report, tech_report, fund_report):
    """ScoreAgent 테스트"""
    print("=" * 60)
    print("4️⃣ ScoreAgent 테스트")
    print("=" * 60)
    
    try:
        if not all([news_report, tech_report, fund_report]):
            print("❌ 이전 에이전트 결과 없음")
            return None
        
        # ScoreAgent 실행
        agent = ScoreAgent(config, prompts)
        result = agent.score(
            stock_code='005930',
            stock_name='삼성전자',
            news_report=news_report,
            technical_report=tech_report,
            fundamental_report=fund_report
        )
        
        print(f"입력: 3개 리포트")
        print(f"출력: {result}")
        print("✅ ScoreAgent 성공!\n")
        return result
        
    except Exception as e:
        print(f"❌ ScoreAgent 실패: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 실행"""
    print("\n🧪 3S-Trader 에이전트 개별 테스트\n")
    
    # 설정 로드
    config, prompts = load_config()
    
    # DataManager 생성
    data_manager = DataManager(config)
    
    # 1. NewsAgent 테스트
    news_report = test_news_agent(config, prompts, data_manager)
    
    # 2. TechnicalAgent 테스트
    tech_report = test_technical_agent(config, prompts, data_manager)
    
    # 3. FundamentalAgent 테스트
    fund_report = test_fundamental_agent(config, prompts, data_manager)
    
    # 4. ScoreAgent 테스트
    scores = test_score_agent(config, prompts, news_report, tech_report, fund_report)
    
    # 결과 요약
    print("=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"1️⃣ NewsAgent: {'✅' if news_report else '❌'}")
    print(f"2️⃣ TechnicalAgent: {'✅' if tech_report else '❌'}")
    print(f"3️⃣ FundamentalAgent: {'✅' if fund_report else '❌'}")
    print(f"4️⃣ ScoreAgent: {'✅' if scores else '❌'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
