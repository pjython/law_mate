"""
RAG 오케스트레이터
RAG 시스템의 모든 컴포넌트를 조율하고 관리하는 중앙 서비스입니다.
"""

import time
from typing import Dict, Any, List, Optional

from core.config import get_settings
from core.logging.config import get_logger
from services.document.processor import DocumentProcessor
from services.search.hybrid_search import HybridSearchService
from services.llm.openai_client import OpenAIService
from infrastructure.database.vector_store import VectorStore

# 로깅 설정
logger = get_logger(__name__)


class RAGOrchestrator:
    """
    RAG 오케스트레이터
    모든 RAG 컴포넌트를 조율하고 사용자 쿼리를 처리합니다.
    """

    def __init__(self):
        """RAG 오케스트레이터 초기화"""
        try:
            logger.info("🚀 RAG 오케스트레이터 초기화 중...")

            self.settings = get_settings()

            # 서비스 컴포넌트 초기화
            self.vector_store = VectorStore()
            self.document_processor = DocumentProcessor()
            self.llm_service = OpenAIService()
            self.search_service = HybridSearchService(self.vector_store)

            # 시스템 상태
            self.is_initialized = False
            self.documents_loaded = False
            self.search_index_built = False

            logger.info("✅ RAG 오케스트레이터 초기화 완료")

        except Exception as e:
            logger.error(f"❌ RAG 오케스트레이터 초기화 오류: {str(e)}")
            raise

    async def initialize(self) -> bool:
        """시스템 초기화 및 문서 로드"""
        try:
            if self.is_initialized:
                logger.info("ℹ️ 시스템이 이미 초기화되어 있습니다.")
                return True

            logger.info("📚 법률 문서 로드 및 처리 중...")

            # 1. 문서 처리
            success = await self.document_processor.process_documents()
            if not success:
                logger.error("❌ 문서 처리 실패")
                return False

            # 2. 벡터 스토어에 문서 추가
            processed_chunks = self.document_processor.get_processed_chunks()
            if processed_chunks:
                vector_success = await self.vector_store.add_documents(processed_chunks)
                if not vector_success:
                    logger.error("❌ 벡터 DB 구축 실패")
                    return False
                self.documents_loaded = True

                # 3. 검색 인덱스 구축
                logger.info("🔄 검색 인덱스 구축 중...")
                await self.search_service.build_indexes(processed_chunks)
                self.search_index_built = True
                logger.info("✅ 검색 인덱스 구축 완료")

            # 4. 설정 검증
            self._validate_configuration()

            self.is_initialized = True
            logger.info("🎉 RAG 시스템 초기화 완료!")

            # 시스템 정보 출력
            self._log_system_info()

            return True

        except Exception as e:
            logger.error(f"❌ 시스템 초기화 오류: {str(e)}")
            return False

    async def process_query(self, user_query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        사용자 질문 처리

        Args:
            user_query: 사용자 질문
            user_id: 사용자 ID (선택사항)

        Returns:
            처리 결과 딕셔너리
        """
        try:
            if not self.is_initialized:
                return self._create_error_response("시스템이 초기화되지 않았습니다. 잠시 후 다시 시도해주세요.")

            start_time = time.time()
            logger.info(f"🔍 질문 처리 시작: '{user_query}' (사용자: {user_id})")

            # 1. 질문 분류 및 검증
            logger.debug("📋 질문 분류 중...")
            classification = await self._classify_query(user_query)

            if not classification["is_legal"]:
                return self._create_response(
                    success=True,
                    answer="죄송합니다. 법률 관련 질문만 답변할 수 있습니다. 법률 상담이 필요한 질문을 해주세요.",
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    classification=classification,
                    search_method="분류 단계에서 차단",
                )

            # 2. 하이브리드 검색 수행
            logger.debug("🔍 하이브리드 검색 수행 중...")
            retrieved_docs = await self.search_service.search(
                query=user_query,
                top_k=self.settings.TOP_K_DOCUMENTS,
                similarity_threshold=self.settings.SIMILARITY_THRESHOLD,
            )

            if not retrieved_docs:
                return self._create_response(
                    success=True,
                    answer="관련된 법률 정보를 찾을 수 없습니다. 다른 방식으로 질문해 주시거나 더 구체적인 내용을 포함해 주세요.",
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    classification=classification,
                    search_method="하이브리드 검색 결과 없음",
                )

            # 3. LLM을 통한 답변 생성
            logger.debug("🤖 답변 생성 중...")
            response = await self.llm_service.generate_legal_response(user_query, retrieved_docs)

            processing_time = time.time() - start_time
            logger.info(f"✅ 처리 완료 ({processing_time:.2f}초)")

            return self._create_response(
                success=True,
                answer=response["answer"],
                confidence=response["confidence"],
                sources=self._format_sources(retrieved_docs),
                processing_time=processing_time,
                classification=classification,
                search_method="하이브리드 검색 (BM25 + 벡터)",
                retrieved_docs_count=len(retrieved_docs),
            )

        except Exception as e:
            logger.error(f"❌ 질문 처리 오류: {str(e)}")
            return self._create_error_response(f"처리 중 오류가 발생했습니다: {str(e)}")

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        try:
            document_count = 0
            if self.documents_loaded:
                document_count = self.vector_store.get_document_count()

            return {
                "is_initialized": self.is_initialized,
                "documents_loaded": self.documents_loaded,
                "search_index_built": self.search_index_built,
                "document_count": document_count,
                "search_method": "하이브리드 검색 (BM25 + 벡터)",
                "vector_db_path": self.settings.VECTOR_DB_PATH,
                "collection_name": self.settings.COLLECTION_NAME,
                "embedding_model": self.settings.EMBEDDING_MODEL,
                "llm_model": self.settings.OPENAI_MODEL,
                "top_k": self.settings.TOP_K_DOCUMENTS,
                "search_weights": {"bm25": self.settings.BM25_WEIGHT, "vector": self.settings.VECTOR_WEIGHT},
            }

        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 오류: {str(e)}")
            return {"is_initialized": False, "error": str(e)}

    async def rebuild_indexes(self, force_rebuild: bool = False) -> bool:
        """인덱스 재구축"""
        try:
            logger.info("🔄 인덱스 재구축 시작...")

            if not force_rebuild and self.is_initialized:
                logger.warning("⚠️ 시스템이 이미 초기화되어 있습니다. force_rebuild=True로 강제 재구축하세요.")
                return False

            # 기존 상태 초기화
            self.is_initialized = False
            self.documents_loaded = False
            self.search_index_built = False

            # 재초기화
            success = await self.initialize()

            if success:
                logger.info("✅ 인덱스 재구축 완료")
            else:
                logger.error("❌ 인덱스 재구축 실패")

            return success

        except Exception as e:
            logger.error(f"❌ 인덱스 재구축 오류: {str(e)}")
            return False

    # === 내부 헬퍼 메서드들 ===

    async def _classify_query(self, query: str) -> Dict[str, Any]:
        """질문 분류 (임시 구현)"""
        # TODO: 실제 분류기 구현
        return {"is_legal": True, "category": "general", "confidence": 0.8}

    def _validate_configuration(self) -> None:
        """설정 검증"""
        # 가중치 합계 검증은 이미 settings.py에서 수행됨
        logger.debug("✅ 설정 검증 완료")

    def _log_system_info(self) -> None:
        """시스템 정보 로깅"""
        status = self.get_system_status()
        logger.info("📊 시스템 정보:")
        logger.info(f"   - 문서 수: {status.get('document_count', 0)}")
        logger.info(f"   - 검색 방법: {status.get('search_method', 'unknown')}")
        logger.info(f"   - 임베딩 모델: {status.get('embedding_model', 'unknown')}")
        logger.info(f"   - LLM 모델: {status.get('llm_model', 'unknown')}")

    def _create_response(
        self,
        success: bool,
        answer: str,
        confidence: float = 0.0,
        sources: List[Dict] = None,
        processing_time: float = 0.0,
        classification: Dict = None,
        search_method: str = None,
        retrieved_docs_count: int = 0,
    ) -> Dict[str, Any]:
        """표준 응답 생성"""
        return {
            "success": success,
            "answer": answer,
            "confidence": confidence,
            "sources": sources or [],
            "processing_time": processing_time,
            "classification": classification,
            "search_method": search_method,
            "retrieved_docs_count": retrieved_docs_count,
        }

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """오류 응답 생성"""
        return {
            "success": False,
            "error": error_message,
            "answer": "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "confidence": 0.0,
            "sources": [],
            "processing_time": 0.0,
        }

    def _format_sources(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """검색된 문서를 소스 형태로 포맷팅"""
        sources = []
        for i, doc in enumerate(retrieved_docs):
            sources.append(
                {
                    "source": doc.get("source", f"문서 {i+1}"),
                    "content_preview": doc.get("content", "")[:200] + "...",
                    "hybrid_score": doc.get("hybrid_score", 0.0),
                    "bm25_score": doc.get("bm25_score", 0.0),
                    "vector_score": doc.get("vector_score", 0.0),
                }
            )
        return sources
