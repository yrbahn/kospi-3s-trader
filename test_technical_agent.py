#!/usr/bin/env python3
"""TechnicalAgent 상세 테스트"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.technical_agent import TechnicalAgent
from src.data.data_manager import DataManager


def main():
    print("\n🔍 TechnicalAgent 상세 테스트\n")
    
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # DataManager 생성
    data_manager = DataManager(config)
    
    # 데이터 수집
    print("📊 데이터 수집 중...")
    try:
        all_data = data_manager.collect_all_data("20241130")
        samsung = all_data.get('005930', {})
        
        if not samsung:
            print("❌ 삼성전자 데이터 없음")
            return
        
        print(f"✅ 기술적 데이터:")
        print(f"  - technical: {samsung.get('technical')}")
        print()
        
        if not samsung.get('technical'):
            print("❌ technical 데이터가 None입니다!")
            return
        
        # TechnicalAgent 실행
        print("🤖 TechnicalAgent 실행 중...")
        agent = TechnicalAgent(config, prompts)
        result = agent.analyze(
            stock_code='005930',
            stock_name='삼성전자',
            technical_data=samsung['technical']
        )
        
        # 결과 출력
        print("=" * 80)
        print("📄 TechnicalAgent 전체 출력:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print(f"\n총 길이: {len(result)}자")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
