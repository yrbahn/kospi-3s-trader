#!/usr/bin/env python3
"""NewsAgent 상세 테스트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.news_agent import NewsAgent
from src.data.data_manager import DataManager


def main():
    print("\n🔍 NewsAgent 상세 테스트\n")
    
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
    
    print(f"✅ 뉴스 데이터: {len(samsung['news_text'])}자\n")
    
    # NewsAgent 실행
    print("🤖 NewsAgent 실행 중...")
    agent = NewsAgent(config, prompts)
    result = agent.analyze(
        stock_code='005930',
        stock_name='삼성전자',
        news_text=samsung['news_text']
    )
    
    # 결과 출력
    print("=" * 80)
    print("📄 NewsAgent 전체 출력:")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print(f"\n총 길이: {len(result)}자")


if __name__ == "__main__":
    main()
