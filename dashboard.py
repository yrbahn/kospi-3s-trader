#!/usr/bin/env python3
"""
3S-Trader 대시보드
Streamlit 기반 포트폴리오 모니터링
"""
import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="3S-Trader Dashboard",
    page_icon="📊",
    layout="wide"
)

# DB 연결
@st.cache_resource
def get_connection():
    return psycopg2.connect("postgresql://yrbahn@localhost:5432/marketsense")

def get_data(query):
    """SQL 쿼리 실행"""
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    return df

# 타이틀
st.title("📊 3S-Trader Dashboard")
st.markdown("**AI 기반 포트폴리오 자동화 시스템**")

# 요약 통계
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_query = "SELECT COUNT(*) as count FROM portfolio_history"
    total = get_data(total_query)['count'][0]
    st.metric("총 포트폴리오", f"{total}개")

with col2:
    executed_query = "SELECT COUNT(*) as count FROM portfolio_history WHERE executed = TRUE"
    executed = get_data(executed_query)['count'][0]
    st.metric("실행 완료", f"{executed}개")

with col3:
    pending_query = "SELECT COUNT(*) as count FROM portfolio_history WHERE executed = FALSE"
    pending = get_data(pending_query)['count'][0]
    st.metric("실행 대기", f"{pending}개")

with col4:
    if total > 0:
        exec_rate = (executed / total) * 100
        st.metric("실행률", f"{exec_rate:.1f}%")
    else:
        st.metric("실행률", "0%")

st.divider()

# 최근 포트폴리오 히스토리
st.header("📋 최근 포트폴리오 히스토리")

history_query = """
SELECT 
    id,
    execute_date as "실행일",
    TO_CHAR(analyzed_at, 'YYYY-MM-DD HH24:MI') as "분석시간",
    ROUND(cash_weight * 100, 1) as "현금비중(%)",
    CASE WHEN executed THEN '✅' ELSE '⏳' END as "상태",
    LEFT(rationale, 80) as "선정근거"
FROM portfolio_history
ORDER BY analyzed_at DESC
LIMIT 5
"""

history_df = get_data(history_query)
st.dataframe(history_df, use_container_width=True, hide_index=True)

st.divider()

# 현재 포트폴리오 구성
st.header("💼 현재 포트폴리오 구성")

latest_query = """
SELECT 
    ps.stock_code,
    ps.stock_name,
    ps.weight,
    ROUND(ps.weight * 100, 1) as weight_percent
FROM portfolio_stocks ps
JOIN portfolio_history ph ON ps.portfolio_id = ph.id
WHERE ph.id = (SELECT id FROM portfolio_history ORDER BY analyzed_at DESC LIMIT 1)
ORDER BY ps.weight DESC
"""

portfolio_df = get_data(latest_query)

if not portfolio_df.empty:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # 파이 차트
        fig = px.pie(
            portfolio_df, 
            values='weight', 
            names='stock_name',
            title='종목별 비중',
            hole=0.3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 테이블
        display_df = portfolio_df[['stock_name', 'stock_code', 'weight_percent']].copy()
        display_df.columns = ['종목명', '종목코드', '비중(%)']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 현금 비중
        cash_query = """
        SELECT ROUND(cash_weight * 100, 1) as cash_percent
        FROM portfolio_history
        ORDER BY analyzed_at DESC
        LIMIT 1
        """
        cash_df = get_data(cash_query)
        if not cash_df.empty:
            cash_pct = cash_df['cash_percent'][0]
            st.info(f"💰 현금 비중: {cash_pct}%")
else:
    st.info("포트폴리오 데이터가 없습니다.")

st.divider()

# 종목별 선택 빈도
st.header("📈 종목별 선택 빈도 (TOP 10)")

frequency_query = """
SELECT 
    stock_code,
    stock_name,
    COUNT(*) as selected_count,
    ROUND(AVG(weight) * 100, 1) as avg_weight_percent
FROM portfolio_stocks ps
JOIN portfolio_history ph ON ps.portfolio_id = ph.id
GROUP BY stock_code, stock_name
ORDER BY selected_count DESC, avg_weight_percent DESC
LIMIT 10
"""

frequency_df = get_data(frequency_query)

if not frequency_df.empty:
    fig = px.bar(
        frequency_df,
        x='stock_name',
        y='selected_count',
        title='선택 횟수',
        labels={'stock_name': '종목', 'selected_count': '선택 횟수'},
        color='avg_weight_percent',
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 테이블
    display_df = frequency_df.copy()
    display_df.columns = ['종목코드', '종목명', '선택횟수', '평균비중(%)']
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("선택 빈도 데이터가 없습니다.")

st.divider()

# 종목별 평균 점수 분석
st.header("🎯 종목별 평균 점수 분석")

score_query = """
SELECT 
    ps.stock_name as "종목명",
    COUNT(*) as "선택횟수",
    ROUND(AVG((ps.score_data->>'financial_health')::numeric), 1) as "재무",
    ROUND(AVG((ps.score_data->>'growth_potential')::numeric), 1) as "성장",
    ROUND(AVG((ps.score_data->>'news_sentiment')::numeric), 1) as "뉴스",
    ROUND(AVG((ps.score_data->>'price_momentum')::numeric), 1) as "모멘텀",
    ROUND(AVG((ps.score_data->>'volatility_risk')::numeric), 1) as "변동성"
FROM portfolio_stocks ps
GROUP BY ps.stock_code, ps.stock_name
HAVING COUNT(*) >= 1
ORDER BY "선택횟수" DESC, "성장" DESC
LIMIT 10
"""

score_df = get_data(score_query)

if not score_df.empty:
    st.dataframe(
        score_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "재무": st.column_config.ProgressColumn(
                "재무",
                format="%0.1f",
                min_value=0,
                max_value=10,
            ),
            "성장": st.column_config.ProgressColumn(
                "성장",
                format="%0.1f",
                min_value=0,
                max_value=10,
            ),
            "뉴스": st.column_config.ProgressColumn(
                "뉴스",
                format="%0.1f",
                min_value=0,
                max_value=10,
            ),
            "모멘텀": st.column_config.ProgressColumn(
                "모멘텀",
                format="%0.1f",
                min_value=0,
                max_value=10,
            ),
            "변동성": st.column_config.ProgressColumn(
                "변동성",
                format="%0.1f",
                min_value=0,
                max_value=10,
            ),
        }
    )
else:
    st.info("점수 데이터가 없습니다.")

# 푸터
st.divider()
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 포트폴리오는 매주 일요일 밤 자동 분석되며, 월요일 아침 실행됩니다.")
