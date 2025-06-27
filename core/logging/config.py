"""
로깅 설정 모듈
전체 애플리케이션의 로깅 설정을 중앙화하여 관리합니다.
"""

import logging
import sys
from pathlib import Path
from core.config import get_settings


def setup_logging() -> None:
    """애플리케이션 로깅 설정"""
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 핸들러 설정
    handlers = [logging.StreamHandler(sys.stdout)]

    # 파일 핸들러 추가
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.LOG_FILE, encoding="utf-8"))

    # 기본 로깅 설정
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=handlers, force=True
    )

    # 외부 라이브러리 로깅 레벨 조정 (필수만)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # 설정 완료 로그
    logger = logging.getLogger(__name__)
    logger.info(f"✅ 로깅 설정 완료 - 레벨: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 반환"""
    return logging.getLogger(name)
