"""
API 응답 스키마 정의
서버에서 클라이언트로 전송되는 응답 데이터 모델을 정의합니다.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .common import SourceDocument


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


class QueryResponse(BaseModel):
    """질문 응답 모델"""

    success: bool = Field(..., description="처리 성공 여부")
    answer: Optional[str] = Field(None, description="AI 답변")
    confidence: Optional[float] = Field(None, description="답변 신뢰도")
    processing_time: float = Field(..., description="처리 시간(초)")
    search_method: Optional[str] = Field(None, description="사용된 검색 방법")
    retrieved_docs_count: Optional[int] = Field(None, description="검색된 문서 수")
    classification: Optional[Dict[str, Any]] = Field(None, description="질문 분류 결과")
    sources: Optional[List[SourceDocument]] = Field(None, description="참조 문서 목록")
    error: Optional[str] = Field(None, description="오류 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "전세보증금 반환에 관한 법률적 조언입니다...",
                "confidence": 0.85,
                "processing_time": 2.5,
                "search_method": "하이브리드 검색 (BM25 + 벡터)",
                "retrieved_docs_count": 5,
                "classification": {"category": "부동산", "confidence": 0.95},
                "sources": [
                    {
                        "source": "주택임대차보호법",
                        "content_preview": "임차인은 임대차가 종료된 때에는...",
                        "hybrid_score": 0.85,
                        "bm25_score": 0.7,
                        "vector_score": 0.9,
                    }
                ],
                "error": None,
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
