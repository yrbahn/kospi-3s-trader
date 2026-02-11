#!/usr/bin/env python3
"""KIS API 연결 테스트"""
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.kis.kis_client import KISClient

def main():
    print("🔐 KIS API 연결 테스트\n")
    
    # 환경변수 확인
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    account_no = os.getenv("KIS_ACCOUNT_NO")
    
    print("환경변수 확인:")
    print(f"✅ APP_KEY: {app_key[:10]}..." if app_key else "❌ APP_KEY 없음")
    print(f"✅ APP_SECRET: {app_secret[:10]}..." if app_secret else "❌ APP_SECRET 없음")
    print(f"✅ ACCOUNT_NO: {account_no}" if account_no else "❌ ACCOUNT_NO 없음")
    print()
    
    if not all([app_key, app_secret, account_no]):
        print("❌ 환경변수 설정 필요!")
        return
    
    try:
        # KIS 클라이언트 생성 (실전투자 모드)
        print("📡 KIS API 연결 중... (실전투자 모드)")
        client = KISClient(app_key, app_secret, account_no, mock=False)
        
        # 잔고 조회
        print("\n1️⃣ 잔고 조회")
        balance = client.get_balance()
        print(f"현금: {balance['cash']:,.0f}원")
        
        if balance['holdings']:
            print("보유 종목:")
            for ticker, holding in balance['holdings'].items():
                print(f"  - {holding['name']}({ticker}): {holding['shares']:,}주 @ {holding['avg_price']:,.0f}원")
        else:
            print("보유 종목: 없음")
        
        # 현재가 조회
        print("\n2️⃣ 현재가 조회")
        price = client.get_current_price("005930")
        if price:
            print(f"삼성전자 현재가: {price:,.0f}원")
        else:
            print("현재가 조회 실패")
        
        print("\n✅ 연결 테스트 성공!")
        print("\n⚠️ 모의투자 모드로 테스트했습니다.")
        print("실전투자로 전환하려면 live_trader_kis.py에서 mock=False로 변경하세요.")
        
    except Exception as e:
        print(f"\n❌ 연결 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
