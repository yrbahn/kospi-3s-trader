"""유틸리티 헬퍼 함수"""
import os
import yaml
from typing import Dict, Any


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """설정 파일 로드"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompts(prompts_path: str = "config/prompts.yaml") -> Dict[str, Any]:
    """프롬프트 파일 로드"""
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_trading_weeks(start_date: str, end_date: str):
    """거래 주간 목록 생성 (월요일~금요일)"""
    import pandas as pd
    dates = pd.date_range(start=start_date, end=end_date, freq="W-MON")
    weeks = []
    for monday in dates:
        friday = monday + pd.Timedelta(days=4)
        weeks.append((monday.strftime("%Y%m%d"), friday.strftime("%Y%m%d")))
    return weeks


def format_number(value: float, decimals: int = 2) -> str:
    """숫자 포맷팅 (한국식)"""
    if abs(value) >= 1e12:
        return f"{value/1e12:.{decimals}f}조"
    elif abs(value) >= 1e8:
        return f"{value/1e8:.{decimals}f}억"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.{decimals}f}만"
    return f"{value:.{decimals}f}"
