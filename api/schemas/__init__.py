"""
API 스키마 패키지
Pydantic 모델들을 요청/응답/공통으로 분류하여 관리합니다.
"""

from .common import BaseResponse, ErrorResponse
from .requests import QueryRequest
from .responses import QueryResponse, HealthResponse, SystemStatusResponse

__all__ = [
    # Common
    "BaseResponse",
    "ErrorResponse",
    # Requests
    "QueryRequest",
    # Responses
    "QueryResponse",
    "HealthResponse",
    "SystemStatusResponse",
]
