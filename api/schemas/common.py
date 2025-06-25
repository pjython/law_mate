"""
공통 스키마 정의
여러 API에서 공통으로 사용되는 데이터 모델을 정의합니다.
"""

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """참조 문서 모델"""

    source: str = Field(..., description="문서 출처")
    content_preview: str = Field(..., description="내용 미리보기")
    hybrid_score: float = Field(..., description="하이브리드 점수")
    bm25_score: float = Field(..., description="BM25 점수")
    vector_score: float = Field(..., description="벡터 점수")


class ErrorDetail(BaseModel):
    """오류 상세 정보"""

    code: str = Field(..., description="오류 코드")
    message: str = Field(..., description="오류 메시지")
    details: str = Field(None, description="오류 상세 정보")


class PaginationMeta(BaseModel):
    """페이지네이션 메타데이터"""

    page: int = Field(..., description="현재 페이지", ge=1)
    size: int = Field(..., description="페이지 크기", ge=1, le=100)
    total: int = Field(..., description="전체 항목 수", ge=0)
    pages: int = Field(..., description="전체 페이지 수", ge=0)
