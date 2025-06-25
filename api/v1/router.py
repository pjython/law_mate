"""
API v1 메인 라우터
모든 v1 엔드포인트를 통합하는 메인 라우터입니다.
"""

from fastapi import APIRouter
from api.v1.endpoints import health, query, admin

# 메인 API 라우터 생성
api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(health.router, prefix="/health", tags=["Health Check"])

api_router.include_router(query.router, prefix="/query", tags=["Query Processing"])

api_router.include_router(admin.router, prefix="/admin", tags=["Admin Functions"])
