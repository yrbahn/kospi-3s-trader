#!/usr/bin/env python3
"""
각 에이전트에 입력되는 데이터 확인
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_manager import DataManager
from src.utils.helpers import load_config

def check_agent_inputs():
    """현대차우(005385) 데이터 확인"""
    config = load_config()
    dm = DataManager(config)
    
    today = datetime.now().strftime("%Y%m%d")
    
    print("🔍 에이전트 입력 데이터 확인\n")
    print("=" * 80)
    
    # 한 종목만 확인 (현대차우)
    all_data = dm.collect_all_data(today)
    
    # 현대차우 데이터
    ticker = "005385"
    if ticker not in all_data:
        print(f"❌ {ticker} 데이터 없음")
        return
    
    data = all_data[ticker]
    name = data["name"]
    
    print(f"\n📊 종목: {name}({ticker})")
    print("=" * 80)
    
    # 1. NewsAgent 입력
    print("\n1️⃣ NewsAgent 입력 (news_text):")
    print("-" * 80)
    news_text = data["news_text"]
    print(f"길이: {len(news_text)}자")
    print(f"샘플:\n{news_text[:500]}...")
    
    # 2. TechnicalAgent 입력
    print("\n2️⃣ TechnicalAgent 입력 (technical.summary):")
    print("-" * 80)
    tech_summary = data["technical"].get("summary", "")
    print(f"길이: {len(tech_summary)}자")
    print(f"샘플:\n{tech_summary[:500]}...")
    
    # 3. FundamentalAgent 입력
    print("\n3️⃣ FundamentalAgent 입력 (fundamental_text):")
    print("-" * 80)
    fund_text = data["fundamental_text"]
    print(f"길이: {len(fund_text)}자")
    print(f"샘플:\n{fund_text[:500]}...")
    
    # 4. 데이터 구조
    print("\n4️⃣ 전체 데이터 구조:")
    print("-" * 80)
    print(f"키: {list(data.keys())}")
    print(f"technical 키: {list(data['technical'].keys())}")
    
    print("\n" + "=" * 80)
    print("✅ 확인 완료")

if __name__ == "__main__":
    check_agent_inputs()
