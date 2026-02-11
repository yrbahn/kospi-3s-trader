-- 3S-Trader 대시보드 쿼리
-- PostgreSQL로 포트폴리오 히스토리 분석

-- 1. 최근 5개 포트폴리오 히스토리
SELECT 
    id,
    execute_date,
    TO_CHAR(analyzed_at, 'YYYY-MM-DD HH24:MI') as analyzed_time,
    cash_weight * 100 as cash_percent,
    executed,
    CASE WHEN executed THEN TO_CHAR(executed_at, 'YYYY-MM-DD HH24:MI') ELSE '-' END as executed_time,
    LEFT(rationale, 100) as rationale_preview
FROM portfolio_history
ORDER BY analyzed_at DESC
LIMIT 5;

-- 2. 특정 포트폴리오의 종목 구성 (최신)
SELECT 
    ps.stock_code,
    ps.stock_name,
    ps.weight * 100 as weight_percent,
    ps.score_data->>'financial_health' as financial,
    ps.score_data->>'growth_potential' as growth,
    ps.score_data->>'news_sentiment' as sentiment
FROM portfolio_stocks ps
JOIN portfolio_history ph ON ps.portfolio_id = ph.id
WHERE ph.id = (SELECT id FROM portfolio_history ORDER BY analyzed_at DESC LIMIT 1)
ORDER BY ps.weight DESC;

-- 3. 종목별 선택 빈도 (TOP 10)
SELECT 
    stock_code,
    stock_name,
    COUNT(*) as selected_count,
    AVG(weight) * 100 as avg_weight_percent,
    MAX(ph.executed) as ever_executed
FROM portfolio_stocks ps
JOIN portfolio_history ph ON ps.portfolio_id = ph.id
GROUP BY stock_code, stock_name
ORDER BY selected_count DESC, avg_weight_percent DESC
LIMIT 10;

-- 4. 주간 포트폴리오 변화 (최근 4주)
SELECT 
    TO_CHAR(execute_date, 'YYYY-MM-DD (Dy)') as week,
    COUNT(DISTINCT ps.stock_code) as stock_count,
    ph.cash_weight * 100 as cash_percent,
    executed
FROM portfolio_history ph
LEFT JOIN portfolio_stocks ps ON ph.id = ps.portfolio_id
WHERE execute_date >= CURRENT_DATE - INTERVAL '4 weeks'
GROUP BY ph.id, execute_date, ph.cash_weight, executed
ORDER BY execute_date DESC;

-- 5. 현재 실행 대기 중인 포트폴리오
SELECT 
    ph.id,
    ph.execute_date,
    TO_CHAR(ph.analyzed_at, 'YYYY-MM-DD HH24:MI') as analyzed_time,
    ph.cash_weight * 100 as cash_percent,
    ph.rationale,
    COUNT(ps.id) as stock_count
FROM portfolio_history ph
LEFT JOIN portfolio_stocks ps ON ph.id = ps.portfolio_id
WHERE ph.executed = FALSE
GROUP BY ph.id, ph.execute_date, ph.analyzed_at, ph.cash_weight, ph.rationale
ORDER BY ph.analyzed_at DESC;

-- 6. 종목별 평균 점수 분석 (선택된 종목만)
SELECT 
    ps.stock_code,
    ps.stock_name,
    COUNT(*) as times_selected,
    ROUND(AVG((ps.score_data->>'financial_health')::numeric), 1) as avg_financial,
    ROUND(AVG((ps.score_data->>'growth_potential')::numeric), 1) as avg_growth,
    ROUND(AVG((ps.score_data->>'news_sentiment')::numeric), 1) as avg_sentiment,
    ROUND(AVG((ps.score_data->>'price_momentum')::numeric), 1) as avg_momentum,
    ROUND(AVG((ps.score_data->>'volatility_risk')::numeric), 1) as avg_volatility
FROM portfolio_stocks ps
GROUP BY ps.stock_code, ps.stock_name
HAVING COUNT(*) >= 2
ORDER BY times_selected DESC, avg_growth DESC
LIMIT 20;

-- 7. 실행률 통계
SELECT 
    COUNT(*) as total_portfolios,
    SUM(CASE WHEN executed THEN 1 ELSE 0 END) as executed_count,
    ROUND(SUM(CASE WHEN executed THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as execution_rate_percent,
    AVG(cash_weight) * 100 as avg_cash_weight_percent
FROM portfolio_history;

-- 8. 월별 포트폴리오 생성 추이
SELECT 
    TO_CHAR(analyzed_at, 'YYYY-MM') as month,
    COUNT(*) as portfolio_count,
    SUM(CASE WHEN executed THEN 1 ELSE 0 END) as executed_count
FROM portfolio_history
GROUP BY TO_CHAR(analyzed_at, 'YYYY-MM')
ORDER BY month DESC;
