"""
RAG 오케스트레이터
RAG 시스템의 컴포넌트들을 조율하는 중앙 서비스입니다.
완전한 LangChain 파이프라인을 통해 사용자 쿼리를 처리합니다.
"""

import time
from typing import Dict, Any, List, Optional

from core.config import get_settings
from core.logging.config import get_logger
from services.document.processor import DocumentProcessor
from services.search.hybrid_search import HybridSearchService

# LangChain RAG 서비스만 사용
from services.llm.langchain_rag_service import LangChainRAGService
from infrastructure.database.vector_store import VectorStore

# 분리된 RAG 서비스들
from services.rag.response_formatter import ResponseFormatter
from services.rag.system_monitor import SystemMonitor

# 대화 관리는 LangChain Memory가 처리

logger = get_logger(__name__)


class RAGOrchestrator:
    """
    RAG 오케스트레이터
    완전한 LangChain 파이프라인을 통해 질문 분류부터 답변 생성까지 처리합니다.
    """

    def __init__(self):
        """RAG 오케스트레이터 초기화"""
        try:
            logger.info("🚀 RAG 오케스트레이터 초기화 중...")

            self.settings = get_settings()

            # 핵심 서비스 컴포넌트 초기화
            self.vector_store = VectorStore()
            self.document_processor = DocumentProcessor()
            self.langchain_rag_service = LangChainRAGService()
            self.search_service = HybridSearchService(self.vector_store)

            # 분리된 RAG 서비스들 초기화
            self.response_formatter = ResponseFormatter()
            self.system_monitor = SystemMonitor()

            # 대화 관리는 LangChain Memory가 자동 처리

            logger.info("✅ RAG 오케스트레이터 초기화 완료")

        except Exception as e:
            logger.error(f"❌ RAG 오케스트레이터 초기화 오류: {str(e)}")
            self.system_monitor.record_error(str(e), "initialization") if hasattr(self, "system_monitor") else None
            raise

    async def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            logger.info("📚 RAG 시스템 초기화 중...")

            # 검색 서비스 초기화 (벡터 스토어는 생성자에서 이미 초기화됨)
            if hasattr(self.search_service, "initialize"):
                await self.search_service.initialize()

            # 시스템 모니터 초기화 상태 설정
            document_count = self.vector_store.get_document_count()
            self.system_monitor.update_initialization_status(
                is_initialized=True, documents_loaded=document_count, search_index_built=True
            )

            logger.info("🎉 RAG 시스템 초기화 완료!")
            self.system_monitor.log_system_info()

            return True

        except Exception as e:
            error_msg = f"시스템 초기화 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.system_monitor.record_error(error_msg, "initialization")
            return False

    async def process_query(
        self, user_query: str, user_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자 질문 처리 (완전한 LangChain RAG 파이프라인)
        질문 분류 → 문서 검색 → 답변 생성이 하나의 체인으로 연결됨
        대화 맥락은 LangChain Memory가 자동 관리

        Args:
            user_query: 사용자 질문
            user_id: 사용자 ID (선택사항)
            session_id: 세션 ID (선택사항, 없으면 자동 생성)

        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()

        try:
            logger.info(f"🚀 LangChain 파이프라인 질문 처리: '{user_query}' (세션: {session_id})")

            # 세션 ID가 없으면 자동 생성 (UUID 기반)
            if not session_id:
                import uuid

                session_id = str(uuid.uuid4())
                logger.debug(f"🆕 새 세션 ID 생성: {session_id}")

            # 완전한 LangChain RAG 파이프라인 실행 (Memory 자동 관리)
            rag_result = await self.langchain_rag_service.process_query(query=user_query, session_id=session_id)

            processing_time = time.time() - start_time
            logger.info(f"✅ LangChain 파이프라인 처리 완료 ({processing_time:.2f}초)")

            # 성능 메트릭 기록
            self.system_monitor.record_query_performance(processing_time, success=True)

            # 최종 응답에 세션 및 성능 정보 추가
            rag_result["session_id"] = session_id
            rag_result["processing_time"] = processing_time
            rag_result["pipeline_type"] = "langchain_full_rag"

            return rag_result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"질문 처리 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")

            self.system_monitor.record_error(error_msg, "query_processing")
            self.system_monitor.record_query_performance(processing_time, success=False)

            return self.response_formatter.create_error_response(error_msg, "QUERY_PROCESSING_ERROR", processing_time)

    async def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """대화 기록 조회 (LangChain Memory에서)"""
        try:
            # LangChain Memory에서 대화 기록 조회
            memory_stats = self.langchain_rag_service.get_memory_stats(session_id)

            if memory_stats:
                return {
                    "success": True,
                    "session_id": session_id,
                    "messages": memory_stats.get("messages", []),
                    "total_messages": memory_stats.get("message_count", 0),
                    "context": {
                        "session_id": session_id,
                        "memory_type": memory_stats.get("memory_type", "ConversationBufferWindowMemory"),
                    },
                }
            else:
                return {"success": False, "error": "세션을 찾을 수 없습니다", "messages": [], "total_messages": 0, "context": {}}

        except Exception as e:
            logger.error(f"❌ 대화 기록 조회 실패: {str(e)}")
            return {"success": False, "error": str(e), "messages": [], "total_messages": 0, "context": {}}

    async def process_documents(self, data_path: str) -> Dict[str, Any]:
        """문서 처리 및 인덱싱"""
        try:
            logger.info(f"📄 문서 처리 시작: {data_path}")

            # 문서 처리
            processed_docs = await self.document_processor.process_documents(data_path)

            if not processed_docs:
                return {"success": False, "message": "처리할 문서가 없습니다.", "processed_count": 0}

            # 벡터 스토어에 추가
            success = await self.vector_store.add_documents(processed_docs)

            if success:
                # 검색 인덱스 재구축
                await self.search_service.rebuild_index()

                # 시스템 상태 업데이트
                document_count = self.vector_store.get_document_count()
                self.system_monitor.update_initialization_status(
                    is_initialized=True, documents_loaded=document_count, search_index_built=True
                )

                logger.info(f"✅ 문서 처리 완료: {len(processed_docs)}개")
                return {
                    "success": True,
                    "message": f"{len(processed_docs)}개 문서가 성공적으로 처리되었습니다.",
                    "processed_count": len(processed_docs),
                }
            else:
                return {"success": False, "message": "문서 저장에 실패했습니다.", "processed_count": 0}

        except Exception as e:
            error_msg = f"문서 처리 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.system_monitor.record_error(error_msg, "document_processing")
            return {"success": False, "message": error_msg, "processed_count": 0}

    async def rebuild_indexes(self) -> Dict[str, Any]:
        """인덱스 재구축"""
        try:
            logger.info("🔄 인덱스 재구축 시작...")

            # 검색 인덱스 재구축 (HybridSearchService의 rebuild_index 메서드 사용)
            await self.search_service.rebuild_index()

            # 시스템 상태 업데이트
            document_count = self.vector_store.get_document_count()
            self.system_monitor.update_initialization_status(
                is_initialized=True, documents_loaded=document_count, search_index_built=True
            )

            logger.info("✅ 인덱스 재구축 완료")
            return {"success": True, "message": "인덱스가 성공적으로 재구축되었습니다."}

        except Exception as e:
            error_msg = f"인덱스 재구축 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.system_monitor.record_error(error_msg, "index_rebuild")
            return {"success": False, "message": error_msg}

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            return self.system_monitor.get_system_status(self.vector_store)
        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 실패: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_service_statistics(self) -> Dict[str, Any]:
        """서비스 통계 조회"""
        try:
            return self.conversation_service.get_service_statistics()
        except Exception as e:
            logger.error(f"❌ 서비스 통계 조회 실패: {str(e)}")
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            logger.info("🧹 RAG 시스템 정리 중...")
            # 필요한 정리 작업 수행
            logger.info("✅ RAG 시스템 정리 완료")
        except Exception as e:
            logger.error(f"❌ 정리 작업 실패: {str(e)}")

    def _validate_configuration(self) -> bool:
        """설정 검증"""
        try:
            required_settings = ["OPENAI_API_KEY", "EMBEDDING_MODEL", "TOP_K_DOCUMENTS", "SIMILARITY_THRESHOLD"]

            for setting in required_settings:
                if not hasattr(self.settings, setting):
                    logger.error(f"❌ 필수 설정 누락: {setting}")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ 설정 검증 실패: {str(e)}")
            return False
