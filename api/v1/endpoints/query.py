"""
질문 처리 엔드포인트
사용자 질문을 받아 RAG 시스템을 통해 답변을 생성합니다.
대화 맥락을 인식하고 연속적인 대화를 지원합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from core.logging.config import get_logger
from core.dependencies import get_rag_orchestrator
from api.schemas.requests import QueryRequest
from api.schemas.responses import QueryResponse
from services.rag.orchestrator import RAGOrchestrator


router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=QueryResponse)
async def process_query(request: QueryRequest, rag_orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator)):
    """
    질문 처리 (대화 맥락 지원)
    사용자의 법률 질문을 처리하여 AI 답변을 생성합니다.
    세션 ID가 없으면 새로운 대화를 시작하고, 있으면 기존 대화를 이어갑니다.
    """
    logger.info(f"📝 질문 처리 요청: '{request.query}' (사용자: {request.user_id}, 세션: {request.session_id})")

    try:
        # RAG 시스템을 통한 질문 처리 (대화 맥락 지원)
        result = await rag_orchestrator.process_query(
            user_query=request.query, user_id=request.user_id, session_id=request.session_id
        )

        # RAG 결과를 API 응답 형식으로 변환
        response = QueryResponse(
            success=result.get("success", True),
            answer=result.get("answer", "답변을 생성할 수 없습니다."),
            confidence=result.get("confidence", 0.0),
            processing_time=result.get("processing_time", 0.0),
            search_method=result.get("search_method", "하이브리드 검색"),
            retrieved_docs_count=result.get("retrieved_docs_count", 0),
            session_id=result.get("session_id", ""),
            context_analysis=result.get("context_analysis"),
            conversation_info=result.get("conversation_info"),
            classification=result.get("classification", {}),
            sources=result.get("sources", []),
            error=result.get("error", None) if not result.get("success", True) else None,
        )

        if response.success:
            logger.info(f"✅ 질문 처리 완료: {response.processing_time:.2f}초 (세션: {response.session_id})")
        else:
            logger.warning(f"⚠️ 질문 처리 실패: {response.error}")

        return response

    except Exception as e:
        logger.error(f"❌ 질문 처리 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"질문 처리 중 오류가 발생했습니다: {str(e)}")
