"""로깅 설정 모듈"""
import logging
import os
from datetime import datetime


def setup_logger(name: str = "3s_trader", level: str = "INFO", log_file: str = None) -> logging.Logger:
    """로거 설정 및 반환"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 핸들러
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 파일 핸들러
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
