"""
공통 스키마 정의
여러 API에서 공통으로 사용되는 데이터 모델을 정의합니다.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """기본 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    message: Optional[str] = Field(None, description="응답 메시지")
    data: Optional[Any] = Field(None, description="응답 데이터")


class ErrorResponse(BaseModel):
    """오류 응답 모델"""

    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(..., description="오류 메시지")
    error_code: Optional[str] = Field(None, description="오류 코드")
    details: Optional[Any] = Field(None, description="오류 상세 정보")
