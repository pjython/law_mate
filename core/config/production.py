"""
운영 환경 설정
운영 환경에서 사용되는 설정을 정의합니다.
"""

from core.config.base import BaseConfig


class ProductionConfig(BaseConfig):
    """운영 환경 설정"""
    
    # 디버그 모드 비활성화
    DEBUG: bool = False
    
    # 운영용 로그 레벨
    LOG_LEVEL: str = "INFO"
    
    # 리로드 비활성화
    RELOAD: bool = False
    
    # 운영용 CORS 설정 (엄격함)
    @property
    def ALLOWED_ORIGINS(self):
        # 운영 환경에서는 특정 도메인만 허용
        return [
            "https://your-domain.com",
            "https://www.your-domain.com",
            # Streamlit 클라이언트 도메인
            f"https://streamlit.your-domain.com",
        ]
    
    # 운영용 스케줄러 활성화
    ENABLE_SCHEDULER: bool = True
    
    # 운영용 보안 설정
    SECURE_HEADERS: bool = True
    
    # 운영용 로그 파일 경로 (절대 경로 권장)
    LOG_FILE: str = "/var/log/law_mate/api.log" 