"""
API 응답 스키마 정의
서버에서 클라이언트로 전송되는 응답 데이터 모델을 정의합니다.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""

    status: str = Field(..., description="서버 상태")
    message: Optional[str] = Field(None, description="상태 메시지")
    timestamp: str = Field(..., description="응답 시간")
    version: Optional[str] = Field(None, description="API 버전")


class SystemStatusResponse(BaseModel):
    """시스템 상태 응답 모델"""

    status: str = Field(..., description="시스템 상태")
    timestamp: str = Field(..., description="응답 시간")
    rag_initialized: bool = Field(..., description="RAG 시스템 초기화 상태")
    document_count: int = Field(..., description="문서 개수")
    search_method: str = Field(..., description="검색 방법")
    uptime: float = Field(..., description="가동 시간(초)")

    # 대화 관리 통계 추가
    conversation_stats: Optional[Dict[str, Any]] = Field(None, description="대화 관리 통계")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00",
                "rag_initialized": True,
                "document_count": 150,
                "search_method": "하이브리드 검색",
                "uptime": 3600.0,
                "conversation_stats": {"total_sessions": 10, "active_sessions": 5, "total_messages": 50},
            }
        }


class QueryResponse(BaseModel):
    """질문 응답 모델"""

    success: bool = Field(..., description="처리 성공 여부")
    answer: str = Field(..., description="AI 답변")
    confidence: float = Field(..., description="답변 신뢰도")
    processing_time: float = Field(..., description="처리 시간 (초)")
    search_method: str = Field(..., description="검색 방법")
    retrieved_docs_count: int = Field(..., description="검색된 문서 수")

    # 대화 관리 정보 추가
    session_id: str = Field(..., description="세션 ID")

    # 맥락 분석 정보 추가
    context_analysis: Optional[Dict[str, Any]] = Field(None, description="맥락 분석 결과")
    conversation_info: Optional[Dict[str, Any]] = Field(None, description="대화 정보")

    classification: Dict[str, Any] = Field(..., description="질문 분류 결과")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="참조 문서")
    error: Optional[str] = Field(None, description="오류 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "전세보증금 반환에 관한 법률적 조언입니다...",
                "confidence": 0.85,
                "processing_time": 2.3,
                "search_method": "하이브리드 검색 (BM25 + 벡터) + 대화 맥락",
                "retrieved_docs_count": 5,
                "session_id": "session456",
                "context_analysis": {
                    "is_follow_up": False,
                    "is_topic_change": False,
                    "context_score": 0.0,
                    "suggested_category": "부동산",
                },
                "conversation_info": {"current_topic": "전세보증금", "legal_category": "부동산", "message_count": 1},
                "classification": {"is_legal": True, "category": "부동산", "confidence": 0.9},
                "sources": [],
            }
        }


class RebuildResponse(BaseModel):
    """인덱스 재구축 응답 모델"""

    message: str = Field(..., description="응답 메시지")
    status: str = Field(..., description="작업 상태")
    task_id: Optional[str] = Field(None, description="백그라운드 작업 ID")


class ConfigResponse(BaseModel):
    """설정 정보 응답 모델 (디버그용)"""

    debug_mode: bool = Field(..., description="디버그 모드")
    environment: str = Field(..., description="실행 환경")
    app_version: str = Field(..., description="앱 버전")
    chunk_size: int = Field(..., description="청크 크기")
    top_k: int = Field(..., description="상위 K개 문서")
    vector_db_path: str = Field(..., description="벡터 DB 경로")
    search_weights: Dict[str, float] = Field(..., description="검색 가중치")
