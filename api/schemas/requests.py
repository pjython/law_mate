"""
API 요청 스키마 정의
클라이언트에서 서버로 전송되는 요청 데이터 모델을 정의합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """질문 요청 모델"""

    query: str = Field(..., description="법률 질문", min_length=1, max_length=1000)
    user_id: Optional[str] = Field(None, description="사용자 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")

    class Config:
        json_schema_extra = {
            "example": {"query": "전세보증금을 돌려받지 못하고 있어요", "user_id": "user123", "session_id": "session456"}
        }


class RebuildRequest(BaseModel):
    """인덱스 재구축 요청 모델"""

    force: bool = Field(default=False, description="강제 재구축 여부")
    backup: bool = Field(default=True, description="기존 인덱스 백업 여부")

    class Config:
        json_schema_extra = {"example": {"force": True, "backup": True}}
