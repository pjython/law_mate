"""
Law Mate FastAPI 애플리케이션 진입점
"""

import uvicorn
from core.config import get_settings
from core.logging.config import setup_logging, get_logger
from app.dependencies import create_app

# 설정 로드
settings = get_settings()

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# FastAPI 앱 생성
app = create_app()

# === 메인 실행 ===
if __name__ == "__main__":
    logger.info("🚀 Law Mate API 서버를 시작합니다...")
    logger.info(f"   - 호스트: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"   - 디버그: {settings.DEBUG}")
    logger.info(f"   - 모델: {settings.OPENAI_MODEL}")

    # 개발 서버 실행
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
