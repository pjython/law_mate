"""
응답 포맷팅 서비스
RAG 시스템의 응답을 표준화된 형태로 포맷팅하는 서비스입니다.
"""

from typing import Dict, Any, List

from core.logging.config import get_logger

# 로깅 설정
logger = get_logger(__name__)


class ResponseFormatter:
    """
    응답 포맷팅 서비스
    RAG 시스템의 다양한 응답을 표준화된 형태로 포맷팅합니다.
    """

    def __init__(self):
        """응답 포맷터 초기화"""
        logger.debug("🔧 응답 포맷터 초기화")

    def create_success_response(
        self,
        answer: str,
        confidence: float = 0.0,
        sources: List[Dict] = None,
        processing_time: float = 0.0,
        classification: Dict = None,
        search_method: str = None,
        retrieved_docs_count: int = 0,
    ) -> Dict[str, Any]:
        """
        성공 응답 생성

        Args:
            answer: 답변 내용
            confidence: 신뢰도 점수
            sources: 참조 소스 목록
            processing_time: 처리 시간
            classification: 질문 분류 결과
            search_method: 사용된 검색 방법
            retrieved_docs_count: 검색된 문서 수

        Returns:
            표준화된 성공 응답 딕셔너리
        """
        logger.debug(f"✅ 성공 응답 생성 - 신뢰도: {confidence}, 처리시간: {processing_time:.2f}초")

        return {
            "success": True,
            "answer": answer,
            "confidence": confidence,
            "sources": sources or [],
            "processing_time": processing_time,
            "classification": classification,
            "search_method": search_method,
            "retrieved_docs_count": retrieved_docs_count,
            "metadata": {
                "response_type": "success",
                "has_sources": bool(sources),
                "source_count": len(sources) if sources else 0,
            },
        }

    def create_error_response(
        self, error_message: str, error_code: str = None, processing_time: float = 0.0
    ) -> Dict[str, Any]:
        """
        오류 응답 생성

        Args:
            error_message: 오류 메시지
            error_code: 오류 코드 (선택사항)
            processing_time: 처리 시간

        Returns:
            표준화된 오류 응답 딕셔너리
        """
        logger.debug(f"❌ 오류 응답 생성 - 메시지: {error_message}")

        return {
            "success": False,
            "error": error_message,
            "error_code": error_code,
            "answer": "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "confidence": 0.0,
            "sources": [],
            "processing_time": processing_time,
            "metadata": {
                "response_type": "error",
                "has_error_code": bool(error_code),
            },
        }

    def create_non_legal_response(self, classification: Dict[str, Any], processing_time: float = 0.0) -> Dict[str, Any]:
        """
        비법률 질문 응답 생성

        Args:
            classification: 질문 분류 결과
            processing_time: 처리 시간

        Returns:
            비법률 질문에 대한 표준 응답
        """
        logger.debug(f"🚫 비법률 응답 생성 - 분류: {classification.get('reason', 'unknown')}")

        return self.create_success_response(
            answer="죄송합니다. 법률 관련 질문만 답변할 수 있습니다. 법률 상담이 필요한 질문을 해주세요.",
            confidence=0.0,
            processing_time=processing_time,
            classification=classification,
            search_method="분류 단계에서 차단",
        )

    def create_no_results_response(
        self, classification: Dict[str, Any], processing_time: float = 0.0
    ) -> Dict[str, Any]:
        """
        검색 결과 없음 응답 생성

        Args:
            classification: 질문 분류 결과
            processing_time: 처리 시간

        Returns:
            검색 결과가 없을 때의 표준 응답
        """
        logger.debug("🔍 검색 결과 없음 응답 생성")

        return self.create_success_response(
            answer="관련된 법률 정보를 찾을 수 없습니다. 다른 방식으로 질문해 주시거나 더 구체적인 내용을 포함해 주세요.",
            confidence=0.0,
            processing_time=processing_time,
            classification=classification,
            search_method="하이브리드 검색 결과 없음",
        )

    def format_sources(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색된 문서를 소스 형태로 포맷팅

        Args:
            retrieved_docs: 검색된 문서 목록

        Returns:
            포맷팅된 소스 목록
        """
        if not retrieved_docs:
            logger.debug("📄 포맷팅할 소스 문서 없음")
            return []

        logger.debug(f"📄 {len(retrieved_docs)}개 소스 문서 포맷팅")

        sources = []
        for i, doc in enumerate(retrieved_docs):
            # 콘텐츠 미리보기 생성 (200자 제한)
            content = doc.get("content", "")
            content_preview = content[:200] + "..." if len(content) > 200 else content

            source = {
                "id": i + 1,
                "source": doc.get("source", f"문서 {i+1}"),
                "content_preview": content_preview,
                "hybrid_score": round(doc.get("hybrid_score", 0.0), 3),
                "bm25_score": round(doc.get("bm25_score", 0.0), 3),
                "vector_score": round(doc.get("vector_score", 0.0), 3),
                "metadata": {
                    "content_length": len(content),
                    "has_full_content": len(content) <= 200,
                },
            }
            sources.append(source)

        return sources

    def format_system_status(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        시스템 상태를 표준 형태로 포맷팅

        Args:
            status_data: 원본 시스템 상태 데이터

        Returns:
            포맷팅된 시스템 상태
        """
        logger.debug("📊 시스템 상태 포맷팅")

        return {
            "system": {
                "is_initialized": status_data.get("is_initialized", False),
                "documents_loaded": status_data.get("documents_loaded", False),
                "search_index_built": status_data.get("search_index_built", False),
            },
            "data": {
                "document_count": status_data.get("document_count", 0),
                "collection_name": status_data.get("collection_name", "unknown"),
                "vector_db_path": status_data.get("vector_db_path", "unknown"),
            },
            "models": {
                "embedding_model": status_data.get("embedding_model", "unknown"),
                "llm_model": status_data.get("llm_model", "unknown"),
            },
            "search": {
                "method": status_data.get("search_method", "unknown"),
                "top_k": status_data.get("top_k", 0),
                "weights": status_data.get("search_weights", {}),
            },
            "metadata": {
                "status_healthy": (
                    status_data.get("is_initialized", False)
                    and status_data.get("documents_loaded", False)
                    and status_data.get("search_index_built", False)
                ),
                "error": status_data.get("error"),
            },
        }

    def add_debug_info(self, response: Dict[str, Any], debug_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        응답에 디버그 정보 추가

        Args:
            response: 기존 응답
            debug_data: 추가할 디버그 데이터

        Returns:
            디버그 정보가 추가된 응답
        """
        logger.debug("🐛 디버그 정보 추가")

        response["debug"] = {
            "timestamp": debug_data.get("timestamp"),
            "user_id": debug_data.get("user_id"),
            "query_length": debug_data.get("query_length", 0),
            "processing_steps": debug_data.get("processing_steps", []),
            "performance": debug_data.get("performance", {}),
        }

        return response
