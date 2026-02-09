#!/usr/bin/env python3
"""
3S-Trader: LLM 기반 코스피 포트폴리오 최적화 프레임워크

논문: "3S-Trader: A Multi-LLM Framework for Adaptive Stock Scoring,
       Strategy, and Selection in Portfolio Optimization"
       (arXiv:2510.17393)

사용법:
  python -m src.main                          # 기본 백테스트
  python -m src.main --start 2024-01-01       # 시작일 지정
  python -m src.main --end 2024-12-31         # 종료일 지정
  python -m src.main --config config.yaml     # 설정 파일 지정
"""
import argparse
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.helpers import load_config, load_prompts
from src.utils.logger import setup_logger
from backtest.backtester import Backtester
from src.portfolio.evaluator import Evaluator


def main():
    parser = argparse.ArgumentParser(
        description="3S-Trader: LLM 기반 코스피 포트폴리오 최적화"
    )
    parser.add_argument("--config", default="config/config.yaml", help="설정 파일 경로")
    parser.add_argument("--prompts", default="config/prompts.yaml", help="프롬프트 파일 경로")
    parser.add_argument("--start", default=None, help="백테스트 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="백테스트 종료일 (YYYY-MM-DD)")
    parser.add_argument("--output", default="./results", help="결과 출력 디렉토리")
    args = parser.parse_args()

    # 설정 로드
    config = load_config(args.config)
    prompts = load_prompts(args.prompts)

    # 로거 설정
    log_config = config.get("logging", {})
    logger = setup_logger(
        level=log_config.get("level", "INFO"),
        log_file=log_config.get("file", "./logs/3s_trader.log"),
    )

    logger.info("🚀 3S-Trader 시작")
    logger.info(f"  모델: {config.get('llm', {}).get('model', 'gpt-4o')}")
    logger.info(f"  종목 수: {len(config.get('stocks', {}).get('universe', {}))}")

    # 백테스트 실행
    backtester = Backtester(config, prompts)

    start = args.start.replace("-", "") if args.start else None
    end = args.end.replace("-", "") if args.end else None

    metrics = backtester.run(start_date=start, end_date=end)

    logger.info("✅ 3S-Trader 완료")
    return metrics


if __name__ == "__main__":
    main()
