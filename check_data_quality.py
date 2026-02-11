#!/usr/bin/env python3
"""
에이전트 입력 데이터 품질 체크
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_manager import DataManager
from src.utils.helpers import load_config
from datetime import datetime

def check_data_quality():
    """데이터 품질 검사"""
    config = load_config()
    dm = DataManager(config)
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 샘플 종목: 삼성전자 (005930)
    sample_ticker = "005930"
    
    print(f"🔍 데이터 품질 체크: {sample_ticker}")
    print("=" * 60)
    
    # 전체 데이터 수집
    all_data = dm.collect_all_data(today)
    
    if sample_ticker not in all_data:
        print(f"❌ {sample_ticker} 데이터 없음!")
        return
    
    data = all_data[sample_ticker]
    
    # 1. 뉴스 데이터 체크
    print("\n📰 뉴스 데이터:")
    news_text = data.get("news_text", "")
    if not news_text or news_text == "관련 뉴스가 없습니다.":
        print("❌ 뉴스 데이터 없음!")
    else:
        print(f"✅ 뉴스 있음 (길이: {len(news_text)}자)")
        print(f"   샘플: {news_text[:100]}...")
    
    # 2. 기술적 데이터 체크
    print("\n📈 기술적 데이터:")
    technical = data.get("technical", {})
    summary = technical.get("summary", "")
    if not summary or summary == "데이터 없음":
        print("❌ 기술적 데이터 없음!")
    else:
        print(f"✅ 기술적 데이터 있음 (길이: {len(summary)}자)")
        print(f"   샘플: {summary[:100]}...")
    
    # 3. 재무 데이터 체크
    print("\n💰 재무 데이터:")
    fund_text = data.get("fundamental_text", "")
    if not fund_text or fund_text == "재무 데이터가 없습니다.":
        print("❌ 재무 데이터 없음!")
    else:
        print(f"✅ 재무 데이터 있음 (길이: {len(fund_text)}자)")
        print(f"   샘플: {fund_text[:100]}...")
    
    # 4. 전체 통계
    print("\n" + "=" * 60)
    print("📊 전체 종목 통계:")
    
    total = len(all_data)
    no_news = 0
    no_tech = 0
    no_fund = 0
    
    for ticker, d in all_data.items():
        news = d.get("news_text", "")
        tech = d.get("technical", {}).get("summary", "")
        fund = d.get("fundamental_text", "")
        
        if not news or news == "관련 뉴스가 없습니다.":
            no_news += 1
        if not tech or tech == "데이터 없음":
            no_tech += 1
        if not fund or fund == "재무 데이터가 없습니다.":
            no_fund += 1
    
    print(f"전체 종목: {total}개")
    print(f"뉴스 없음: {no_news}개 ({no_news/total*100:.1f}%)")
    print(f"기술 없음: {no_tech}개 ({no_tech/total*100:.1f}%)")
    print(f"재무 없음: {no_fund}개 ({no_fund/total*100:.1f}%)")
    
    # 5. 완전한 데이터를 가진 종목
    complete = total - max(no_news, no_tech, no_fund)
    print(f"\n✅ 완전한 데이터: 약 {complete}개 종목")

if __name__ == "__main__":
    check_data_quality()
