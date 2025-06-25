"""
로깅 설정 모듈
전체 애플리케이션의 로깅 설정을 중앙화하여 관리합니다.
"""

import logging
import sys
from pathlib import Path
from core.config.settings import get_settings


def setup_logging() -> None:
    """
    애플리케이션 전체의 로깅을 설정합니다.
    설정 팩토리에서 가져온 설정을 사용합니다.
    """
    settings = get_settings()

    # 로깅 레벨 설정
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
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,  # 기존 설정 덮어쓰기
    )

    # 외부 라이브러리 로깅 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if getattr(settings, "DEBUG", False) else logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    # 설정 완료 로그
    logger = logging.getLogger(__name__)
    logger.info(f"✅ 로깅 설정 완료")
    logger.info(f"   - 레벨: {settings.LOG_LEVEL}")
    logger.info(f"   - 파일: {settings.LOG_FILE}")
    logger.info(f"   - 디버그: {getattr(settings, 'DEBUG', False)}")


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거를 반환합니다.

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name)
