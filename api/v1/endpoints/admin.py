"""
관리자 기능 엔드포인트
시스템 관리 및 유지보수 관련 API를 제공합니다.
"""

import os
from fastapi import APIRouter, Depends, BackgroundTasks

from core.config.settings import get_settings
from core.logging.config import get_logger
from core.dependencies import get_rag_orchestrator
from api.schemas.requests import RebuildRequest
from api.schemas.responses import RebuildResponse, ConfigResponse
from services.rag.orchestrator import RAGOrchestrator


router = APIRouter()
logger = get_logger(__name__)


@router.post("/rebuild-indexes", response_model=RebuildResponse)
async def rebuild_indexes(
    request: RebuildRequest,
    background_tasks: BackgroundTasks,
    rag_orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
):
    """
    인덱스 재구축
    벡터 DB와 검색 인덱스를 재구축합니다.
    """
    logger.info(f"🔄 인덱스 재구축 요청 (force: {request.force}, backup: {request.backup})")

    try:
        # 백그라운드 작업으로 인덱스 재구축 실행
        background_tasks.add_task(rebuild_task, rag_orchestrator, request.force, request.backup)

        logger.info("📝 인덱스 재구축 백그라운드 작업 시작")

        return RebuildResponse(
            message="인덱스 재구축 작업이 백그라운드에서 시작되었습니다.", status="started", task_id=f"rebuild_{int(os.urandom(4).hex(), 16)}"
        )

    except Exception as e:
        logger.error(f"❌ 인덱스 재구축 요청 실패: {str(e)}")
        return RebuildResponse(message=f"인덱스 재구축 요청 실패: {str(e)}", status="failed")


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    설정 정보 조회 (디버그용)
    현재 시스템 설정을 반환합니다.
    """
    logger.debug("⚙️ 설정 정보 조회 요청")

    settings = get_settings()

    return ConfigResponse(
        debug_mode=getattr(settings, "DEBUG", False),
        environment=os.getenv("ENVIRONMENT", "development"),
        app_version=settings.APP_VERSION,
        chunk_size=settings.CHUNK_SIZE,
        top_k=settings.TOP_K_DOCUMENTS,
        vector_db_path=settings.VECTOR_DB_PATH,
        search_weights={"bm25": settings.BM25_WEIGHT, "vector": settings.VECTOR_WEIGHT},
    )


# === 백그라운드 작업 함수들 ===


async def rebuild_task(rag_orchestrator: RAGOrchestrator, force: bool, backup: bool) -> None:
    """백그라운드 인덱스 재구축 작업"""
    try:
        logger.info("🔄 백그라운드 인덱스 재구축 시작...")

        # 백업 수행 (필요시)
        if backup:
            logger.info("💾 기존 인덱스 백업 중...")
            # TODO: 실제 백업 로직 구현

        # 인덱스 재구축
        success = await rag_orchestrator.rebuild_indexes(force_rebuild=force)

        if success:
            logger.info("✅ 백그라운드 인덱스 재구축 완료")
        else:
            logger.error("❌ 백그라운드 인덱스 재구축 실패")

    except Exception as e:
        logger.error(f"❌ 백그라운드 인덱스 재구축 오류: {str(e)}")
