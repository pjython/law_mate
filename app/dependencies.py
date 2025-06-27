"""
의존성 주입 설정
FastAPI 애플리케이션의 의존성과 앱 팩토리를 정의합니다.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import get_settings
from core.logging.config import get_logger
from core.dependencies import set_rag_orchestrator
from services.rag.orchestrator import RAGOrchestrator

logger = get_logger(__name__)

# 전역 변수
rag_orchestrator: Optional[RAGOrchestrator] = None
scheduler: Optional[AsyncIOScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 앱 라이프사이클 관리"""
    global rag_orchestrator, scheduler
    settings = get_settings()

    try:
        # RAG 시스템 초기화
        logger.info("🚀 RAG 시스템 초기화 중...")
        rag_orchestrator = RAGOrchestrator()
        await rag_orchestrator.initialize()
        set_rag_orchestrator(rag_orchestrator)

        # 스케줄러 초기화 (운영 환경에서만)
        if not getattr(settings, "DEBUG", False):
            scheduler = AsyncIOScheduler()

            # 헬스체크 작업 (매 5분)
            scheduler.add_job(health_check_job, CronTrigger(minute="*/5"), id="health_check", name="정기 헬스체크")

            # 인덱스 재구축 작업 (매일 새벽 2시)
            scheduler.add_job(
                scheduled_rebuild_job, CronTrigger(hour=2, minute=0), id="rebuild_indexes", name="인덱스 재구축"
            )

            scheduler.start()
            logger.info("⏰ 스케줄러 시작 완료")

        logger.info("✅ 애플리케이션 시작 완료")
        yield

    except Exception as e:
        logger.error(f"❌ 애플리케이션 시작 실패: {str(e)}")
        raise
    finally:
        # 정리 작업
        if scheduler:
            scheduler.shutdown()
            logger.info("⏰ 스케줄러 종료 완료")

        if rag_orchestrator:
            await rag_orchestrator.cleanup()
            logger.info("🧹 RAG 시스템 정리 완료")


def create_app() -> FastAPI:
    """FastAPI 앱 생성 및 설정"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        debug=getattr(settings, "DEBUG", False),
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    from api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")

    # 디버그 미들웨어 (개발 환경에서만)
    if getattr(settings, "DEBUG", False):

        @app.middleware("http")
        async def debug_middleware(request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.debug(f"🔍 {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)")
            return response

    logger.info("⚙️ FastAPI 앱 생성 완료")
    return app


def health_check_job():
    """스케줄러용 헬스체크 작업"""
    try:
        if rag_orchestrator:
            status_info = rag_orchestrator.get_system_status()
            logger.info(f"📊 정기 상태 체크: {status_info}")
        else:
            logger.warning("⚠️ RAG 시스템이 초기화되지 않음")
    except Exception as e:
        logger.error(f"❌ 정기 헬스체크 실패: {str(e)}")


def scheduled_rebuild_job():
    """스케줄러용 인덱스 재구축 작업"""
    try:
        logger.info("🔄 스케줄된 인덱스 재구축 시작")
        if rag_orchestrator:
            import asyncio

            asyncio.create_task(rag_orchestrator.rebuild_indexes())
            logger.info("✅ 스케줄된 인덱스 재구축 작업 시작")
        else:
            logger.warning("⚠️ RAG 시스템이 초기화되지 않아 재구축 스킵")
    except Exception as e:
        logger.error(f"❌ 스케줄된 인덱스 재구축 실패: {str(e)}")
