"""
개발 환경 설정
개발 시에만 사용되는 설정을 정의합니다.
"""

from core.config.base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """개발 환경 설정"""
    
    # 디버그 모드 활성화
    DEBUG: bool = True
    
    # 개발용 로그 레벨
    LOG_LEVEL: str = "DEBUG"
    
    # 개발용 리로드 활성화
    RELOAD: bool = True
    
    # 개발용 CORS 설정 (더 관대함)
    @property
    def ALLOWED_ORIGINS(self):
        return [
            "http://localhost:3000",  # React 개발 서버
            "http://localhost:8501",  # Streamlit
            "http://127.0.0.1:8501",
            "http://localhost:8000",  # API 서버 자체
            "http://127.0.0.1:8000",
        ]
    
    # 개발용 스케줄러 비활성화 (선택적)
    ENABLE_SCHEDULER: bool = False 