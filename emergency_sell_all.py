#!/usr/bin/env python3
"""
긴급 전체 매도
모든 보유 종목을 즉시 시장가로 매도합니다.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.kis.kis_client import KISClient

# .env 로드
load_dotenv()


def emergency_sell_all():
    """긴급 전체 매도"""
    print("\n🚨 긴급 전체 매도\n")
    
    # 확인
    confirm = input("⚠️ 모든 종목을 매도하시겠습니까? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ 취소되었습니다.")
        return
    
    # KIS 클라이언트
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    account_no = os.getenv("KIS_ACCOUNT_NO")
    
    if not all([app_key, app_secret, account_no]):
        print("❌ KIS API 인증 정보 없음!")
        return
    
    kis = KISClient(app_key, app_secret, account_no, mock=False)
    
    # 잔고 조회
    balance = kis.get_balance()
    holdings = balance["holdings"]
    
    if not holdings:
        print("📋 보유 종목이 없습니다.")
        return
    
    print(f"\n📋 매도할 종목: {len(holdings)}개\n")
    
    # 종목별 매도
    success_count = 0
    fail_count = 0
    
    for ticker, holding in holdings.items():
        name = holding["name"]
        shares = holding["shares"]
        
        print(f"📉 매도 중: {name}({ticker}) {shares}주...")
        
        # 시장가 매도
        success = kis.order_sell(ticker, shares, price=None)
        
        if success:
            print(f"✅ 매도 성공!")
            success_count += 1
        else:
            print(f"❌ 매도 실패!")
            fail_count += 1
        
        print()
    
    # 결과
    print("=" * 60)
    print("📊 긴급 매도 결과")
    print("=" * 60)
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print("=" * 60)
    
    # 최종 잔고
    final_balance = kis.get_balance()
    print(f"\n💰 최종 현금: {final_balance['cash']:,.0f}원\n")


if __name__ == "__main__":
    emergency_sell_all()
