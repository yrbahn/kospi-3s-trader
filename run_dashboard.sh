#!/bin/bash
# 3S-Trader 대시보드 실행 스크립트

cd "$(dirname "$0")"

echo "🚀 3S-Trader Dashboard 시작..."
echo ""
echo "대시보드 URL: http://localhost:8501"
echo ""
echo "중지하려면 Ctrl+C를 누르세요."
echo ""

streamlit run dashboard.py --server.port 8501 --server.headless true
