#!/usr/bin/env python3
"""ScoreAgent 상세 테스트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.data.data_manager import DataManager


def main():
    print("\n🔍 ScoreAgent 상세 테스트\n")
    
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # DataManager 생성
    data_manager = DataManager(config)
    
    # 데이터 수집
    print("📊 데이터 수집 중...")
    all_data = data_manager.collect_all_data("20241130")
    samsung = all_data.get('005930', {})
    
    if not samsung:
        print("❌ 삼성전자 데이터 없음")
        return
    
    # 1. NewsAgent 실행
    print("\n1️⃣ NewsAgent 실행 중...")
    news_agent = NewsAgent(config, prompts)
    news_report = news_agent.analyze(
        stock_code='005930',
        stock_name='삼성전자',
        news_text=samsung['news_text']
    )
    print(f"✅ NewsAgent 완료 ({len(news_report)}자)")
    
    # 2. TechnicalAgent 실행
    print("\n2️⃣ TechnicalAgent 실행 중...")
    tech_agent = TechnicalAgent(config, prompts)
    tech_summary = samsung['technical'].get('summary', '데이터 없음')
    tech_report = tech_agent.analyze(
        stock_code='005930',
        stock_name='삼성전자',
        technical_summary=tech_summary
    )
    print(f"✅ TechnicalAgent 완료 ({len(tech_report)}자)")
    
    # 3. FundamentalAgent 실행
    print("\n3️⃣ FundamentalAgent 실행 중...")
    fund_agent = FundamentalAgent(config, prompts)
    fund_report = fund_agent.analyze(
        stock_code='005930',
        stock_name='삼성전자',
        fundamental_text=samsung['fundamental_text']
    )
    print(f"✅ FundamentalAgent 완료 ({len(fund_report)}자)")
    
    # 4. ScoreAgent 실행
    print("\n4️⃣ ScoreAgent 실행 중...")
    print("=" * 80)
    
    try:
        score_agent = ScoreAgent(config, prompts)
        scores = score_agent.score(
            stock_code='005930',
            stock_name='삼성전자',
            news_analysis=news_report,
            technical_analysis=tech_report,
            fundamental_analysis=fund_report
        )
        
        print("✅ ScoreAgent 성공!")
        print("=" * 80)
        print("📊 점수 결과:")
        print("=" * 80)
        for key, value in scores.items():
            print(f"  {key}: {value}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ScoreAgent 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
