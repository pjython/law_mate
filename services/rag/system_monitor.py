"""
시스템 모니터링 서비스
RAG 시스템의 상태를 모니터링하고 관리하는 서비스입니다.
"""

from typing import Dict, Any, Optional
import time
from datetime import datetime

from core.config import get_settings
from core.logging.config import get_logger

# 로깅 설정
logger = get_logger(__name__)


class SystemMonitor:
    """
    시스템 모니터링 서비스
    RAG 시스템의 상태를 추적하고 모니터링합니다.
    """

    def __init__(self):
        """시스템 모니터 초기화"""
        logger.debug("🔧 시스템 모니터 초기화")

        self.settings = get_settings()

        # 시스템 상태 추적
        self._system_state = {
            "is_initialized": False,
            "documents_loaded": 0,
            "search_index_built": False,
            "last_initialized": None,
            "initialization_count": 0,
            "error_count": 0,
            "last_error": None,
        }

        # 성능 메트릭
        self._performance_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "response_times": [],  # 최근 100개 응답시간 저장
            "last_query_time": None,
        }

        logger.debug("✅ 시스템 모니터 초기화 완료")

    def update_initialization_status(
        self, is_initialized: bool, documents_loaded: int = 0, search_index_built: bool = False
    ) -> None:
        """
        초기화 상태 업데이트

        Args:
            is_initialized: 시스템 초기화 여부
            documents_loaded: 문서 로드 여부
            search_index_built: 검색 인덱스 구축 여부
        """
        logger.debug(f"📊 초기화 상태 업데이트 - 초기화: {is_initialized}, 문서: {documents_loaded}, 인덱스: {search_index_built}")

        self._system_state.update(
            {
                "is_initialized": is_initialized,
                "documents_loaded": documents_loaded,
                "search_index_built": search_index_built,
            }
        )

        if is_initialized:
            self._system_state["last_initialized"] = datetime.now()
            self._system_state["initialization_count"] += 1
            logger.info(f"🎉 시스템 초기화 완료 (총 {self._system_state['initialization_count']}회)")

    def record_error(self, error_message: str, error_type: str = "general") -> None:
        """
        오류 기록

        Args:
            error_message: 오류 메시지
            error_type: 오류 유형
        """
        logger.debug(f"❌ 오류 기록 - 유형: {error_type}, 메시지: {error_message}")

        self._system_state["error_count"] += 1
        self._system_state["last_error"] = {
            "message": error_message,
            "type": error_type,
            "timestamp": datetime.now(),
        }

    def record_query_performance(self, processing_time: float, success: bool = True) -> None:
        """
        쿼리 성능 기록

        Args:
            processing_time: 처리 시간 (초)
            success: 성공 여부
        """
        logger.debug(f"📈 쿼리 성능 기록 - 시간: {processing_time:.2f}초, 성공: {success}")

        self._performance_metrics["total_queries"] += 1
        self._performance_metrics["last_query_time"] = datetime.now()

        if success:
            self._performance_metrics["successful_queries"] += 1
        else:
            self._performance_metrics["failed_queries"] += 1

        # 응답 시간 기록 (최근 100개만 유지)
        self._performance_metrics["response_times"].append(processing_time)
        if len(self._performance_metrics["response_times"]) > 100:
            self._performance_metrics["response_times"].pop(0)

        # 평균 응답 시간 계산
        if self._performance_metrics["response_times"]:
            self._performance_metrics["average_response_time"] = sum(self._performance_metrics["response_times"]) / len(
                self._performance_metrics["response_times"]
            )

    def get_system_status(self, vector_store=None) -> Dict[str, Any]:
        """
        현재 시스템 상태 반환

        Args:
            vector_store: 벡터 스토어 인스턴스 (문서 수 조회용)

        Returns:
            시스템 상태 딕셔너리
        """
        try:
            logger.debug("📊 시스템 상태 조회")

            # 문서 수 조회 (vector_store가 있으면 항상 조회)
            document_count = 0
            if vector_store:
                try:
                    document_count = vector_store.get_document_count()
                    # 실제 문서가 있으면 documents_loaded 상태 업데이트
                    if document_count > 0 and not self._system_state["documents_loaded"]:
                        self._system_state["documents_loaded"] = document_count
                        logger.debug(f"📊 문서 상태 자동 업데이트: {document_count}개")
                except Exception as e:
                    logger.warning(f"⚠️ 문서 수 조회 실패: {str(e)}")

            status = {
                # 기본 상태
                "is_initialized": self._system_state["is_initialized"],
                "documents_loaded": self._system_state["documents_loaded"],
                "search_index_built": self._system_state["search_index_built"],
                "document_count": document_count,
                # 검색 설정
                "search_method": "하이브리드 검색 (BM25 + 벡터)",
                "top_k": self.settings.TOP_K_DOCUMENTS,
                "search_weights": {"bm25": self.settings.BM25_WEIGHT, "vector": self.settings.VECTOR_WEIGHT},
                # 모델 정보
                "embedding_model": self.settings.EMBEDDING_MODEL,
                "llm_model": self.settings.OPENAI_MODEL,
                # 데이터베이스 정보
                "vector_db_path": self.settings.VECTOR_DB_PATH,
                "collection_name": self.settings.COLLECTION_NAME,
                # 성능 메트릭
                "performance": {
                    "total_queries": self._performance_metrics["total_queries"],
                    "successful_queries": self._performance_metrics["successful_queries"],
                    "failed_queries": self._performance_metrics["failed_queries"],
                    "success_rate": self._calculate_success_rate(),
                    "average_response_time": round(self._performance_metrics["average_response_time"], 3),
                    "last_query_time": self._performance_metrics["last_query_time"],
                },
                # 시스템 메타데이터
                "metadata": {
                    "last_initialized": self._system_state["last_initialized"],
                    "initialization_count": self._system_state["initialization_count"],
                    "error_count": self._system_state["error_count"],
                    "last_error": self._system_state["last_error"],
                    "uptime_status": self._get_uptime_status(),
                },
            }

            return status

        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 오류: {str(e)}")
            self.record_error(str(e), "status_query")
            return {"is_initialized": False, "error": str(e)}

    def get_health_check(self) -> Dict[str, Any]:
        """
        시스템 건강성 체크

        Returns:
            건강성 체크 결과
        """
        logger.debug("🩺 시스템 건강성 체크")

        is_healthy = (
            self._system_state["is_initialized"]
            and self._system_state["documents_loaded"]
            and self._system_state["search_index_built"]
        )

        # 성능 기반 건강성 판단
        success_rate = self._calculate_success_rate()
        avg_response_time = self._performance_metrics["average_response_time"]

        performance_healthy = success_rate >= 0.9 and avg_response_time <= 10.0  # 90% 이상 성공률  # 10초 이하 평균 응답시간

        overall_healthy = is_healthy and performance_healthy

        health_status = {
            "healthy": overall_healthy,
            "system_ready": is_healthy,
            "performance_good": performance_healthy,
            "checks": {
                "initialization": self._system_state["is_initialized"],
                "documents": self._system_state["documents_loaded"],
                "search_index": self._system_state["search_index_built"],
                "success_rate_ok": success_rate >= 0.9,
                "response_time_ok": avg_response_time <= 10.0,
            },
            "metrics": {
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "error_count": self._system_state["error_count"],
            },
            "timestamp": datetime.now(),
        }

        logger.debug(f"🩺 건강성 체크 결과: {'건강' if overall_healthy else '문제 있음'}")
        return health_status

    def log_system_info(self) -> None:
        """시스템 정보 로깅"""
        try:
            status = self.get_system_status()
            logger.info("📊 시스템 정보:")
            logger.info(f"   - 문서 수: {status.get('document_count', 0)}")
            logger.info(f"   - 검색 방법: {status.get('search_method', 'unknown')}")
            logger.info(f"   - 임베딩 모델: {status.get('embedding_model', 'unknown')}")
            logger.info(f"   - LLM 모델: {status.get('llm_model', 'unknown')}")
            logger.info(f"   - 총 쿼리 수: {status['performance']['total_queries']}")
            logger.info(f"   - 성공률: {status['performance']['success_rate']:.1%}")
            logger.info(f"   - 평균 응답시간: {status['performance']['average_response_time']:.2f}초")
        except Exception as e:
            logger.error(f"❌ 시스템 정보 로깅 오류: {str(e)}")

    def reset_metrics(self) -> None:
        """성능 메트릭 초기화"""
        logger.info("🔄 성능 메트릭 초기화")

        self._performance_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "response_times": [],
            "last_query_time": None,
        }

    def _calculate_success_rate(self) -> float:
        """성공률 계산"""
        total = self._performance_metrics["total_queries"]
        if total == 0:
            return 1.0

        successful = self._performance_metrics["successful_queries"]
        return successful / total

    def _get_uptime_status(self) -> str:
        """가동 시간 상태 반환"""
        if not self._system_state["last_initialized"]:
            return "미초기화"

        uptime = datetime.now() - self._system_state["last_initialized"]
        hours = uptime.total_seconds() / 3600

        if hours < 1:
            return f"{int(uptime.total_seconds() / 60)}분"
        elif hours < 24:
            return f"{int(hours)}시간"
        else:
            return f"{int(hours / 24)}일"
