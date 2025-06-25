"""
헬스체크 엔드포인트
API 서버와 RAG 시스템의 상태를 확인합니다.
"""

from datetime import datetime
from fastapi import APIRouter, Depends

from core.logging.config import get_logger
from core.dependencies import get_app_uptime, get_rag_orchestrator
from api.schemas.responses import HealthResponse, SystemStatusResponse
from services.rag.orchestrator import RAGOrchestrator

# 라우터 생성
router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    기본 헬스체크
    API 서버의 기본 상태를 반환합니다.
    """
    logger.debug("🔍 헬스체크 요청 수신")

    return HealthResponse(
        status="healthy", message="Law Mate API 서버가 정상 작동 중입니다.", timestamp=datetime.now().isoformat()
    )


@router.get("/status", response_model=SystemStatusResponse)
async def system_status(
    uptime: float = Depends(get_app_uptime), rag_orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)
):
    """
    시스템 상태 확인
    RAG 시스템 및 전체 시스템의 상세 상태를 반환합니다.
    """
    logger.debug("🔍 시스템 상태 확인 요청 수신")

    try:
        # 실제 RAG 시스템 상태 조회
        rag_status = rag_orchestrator.get_system_status()

        return SystemStatusResponse(
            status="healthy" if rag_status.get("is_initialized", False) else "degraded",
            timestamp=datetime.now().isoformat(),
            rag_initialized=rag_status.get("is_initialized", False),
            document_count=rag_status.get("document_count", 0),
            search_method=rag_status.get("search_method", "unknown"),
            uptime=uptime,
        )

    except Exception as e:
        logger.error(f"❌ 시스템 상태 확인 실패: {str(e)}")

        return SystemStatusResponse(
            status="degraded",
            timestamp=datetime.now().isoformat(),
            rag_initialized=False,
            document_count=0,
            search_method="unknown",
            uptime=uptime,
        )
