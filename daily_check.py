#!/usr/bin/env python3
"""
일일 포트폴리오 체크
매일 장 마감 후 실행하여 보유 종목의 손익을 확인하고 위험 종목을 알립니다.
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


def daily_check():
    """일일 포트폴리오 체크"""
    print(f"\n📊 일일 포트폴리오 체크")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
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
    cash = balance["cash"]
    holdings = balance["holdings"]
    
    if not holdings:
        print("📋 보유 종목: 없음")
        print(f"💰 현금: {cash:,.0f}원\n")
        return
    
    # 종목별 현황 분석
    total_value = cash
    total_profit = 0
    danger_stocks = []  # 손실 10% 이상
    
    lines = []
    lines.append("📋 **보유 종목 현황**\n")
    
    for ticker, holding in holdings.items():
        name = holding["name"]
        shares = holding["shares"]
        avg_price = holding["avg_price"]
        
        # 현재가 조회
        current_price = kis.get_current_price(ticker)
        if not current_price:
            print(f"⚠️ {name}({ticker}) 현재가 조회 실패")
            continue
        
        # 손익 계산
        buy_value = shares * avg_price
        current_value = shares * current_price
        profit = current_value - buy_value
        profit_rate = (profit / buy_value) * 100
        
        total_value += current_value
        total_profit += profit
        
        # 상태 이모지
        if profit_rate >= 0:
            emoji = "📈" if profit_rate >= 5 else "➡️"
        else:
            emoji = "📉"
            if profit_rate <= -10:
                emoji = "🚨"
                danger_stocks.append({
                    "name": name,
                    "ticker": ticker,
                    "profit_rate": profit_rate,
                })
        
        # 출력
        line = (
            f"{emoji} **{name}({ticker})**\n"
            f"   수량: {shares:,}주\n"
            f"   매입가: {avg_price:,.0f}원\n"
            f"   현재가: {current_price:,.0f}원\n"
            f"   손익: {profit:+,.0f}원 ({profit_rate:+.2f}%)\n"
        )
        lines.append(line)
        print(line)
    
    # 총 손익
    initial_value = total_value - total_profit
    total_rate = (total_profit / initial_value) * 100 if initial_value > 0 else 0
    
    summary = (
        f"\n💰 **포트폴리오 요약**\n"
        f"현금: {cash:,.0f}원\n"
        f"총 자산: {total_value:,.0f}원\n"
        f"총 손익: {total_profit:+,.0f}원 ({total_rate:+.2f}%)\n"
    )
    lines.append(summary)
    print(summary)
    
    # 위험 종목 알림
    if danger_stocks:
        warning = "\n🚨 **주의: 손실 10% 이상 종목**\n"
        for stock in danger_stocks:
            warning += f"- {stock['name']}({stock['ticker']}): {stock['profit_rate']:.2f}%\n"
        warning += "\n💡 대응 방안을 고려하세요!\n"
        lines.append(warning)
        print(warning)
    
    # Telegram 리포트 생성
    report = "".join(lines)
    
    # TODO: Telegram 메시지 전송
    # 지금은 콘솔 출력만
    
    print("\n✅ 일일 체크 완료\n")
    
    return report


if __name__ == "__main__":
    daily_check()
