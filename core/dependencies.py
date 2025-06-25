"""
의존성 주입 함수들
FastAPI 의존성 주입에 사용되는 함수들을 정의합니다.
"""

import time
from typing import Optional
from fastapi import HTTPException, status

from core.logging.config import get_logger

logger = get_logger(__name__)

# 전역 변수
app_start_time = time.time()
rag_orchestrator_instance: Optional[object] = None


def get_app_uptime() -> float:
    """앱 가동 시간 반환"""
    return time.time() - app_start_time


def set_rag_orchestrator(orchestrator) -> None:
    """RAG 오케스트레이터 인스턴스 설정"""
    global rag_orchestrator_instance
    rag_orchestrator_instance = orchestrator


def get_rag_orchestrator():
    """RAG 오케스트레이터 의존성 주입"""
    if rag_orchestrator_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG 시스템이 초기화되지 않았습니다. 잠시 후 다시 시도해주세요."
        )
    return rag_orchestrator_instance
