"""
설정 팩토리
환경에 따라 적절한 설정을 반환하는 팩토리 함수를 제공합니다.
"""

import os
from functools import lru_cache
from typing import Union

from core.config.base import BaseConfig
from core.config.development import DevelopmentConfig
from core.config.production import ProductionConfig


@lru_cache()
def get_settings() -> Union[DevelopmentConfig, ProductionConfig, BaseConfig]:
    """
    환경에 따라 적절한 설정을 반환합니다.
    
    환경 변수 ENVIRONMENT 값에 따라:
    - development: DevelopmentConfig
    - production: ProductionConfig
    - 기타: BaseConfig (기본값)
    
    Returns:
        설정 객체
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "development":
        config = DevelopmentConfig()
    elif environment == "production":
        config = ProductionConfig()
    else:
        # 기본 설정 (테스트 환경 등)
        config = BaseConfig()
    
    # 필수 디렉토리 생성
    config.create_directories()
    
    # 설정 검증
    _validate_settings(config)
    
    return config


def _validate_settings(config: BaseConfig) -> None:
    """
    설정 검증
    
    Args:
        config: 검증할 설정 객체
        
    Raises:
        ValueError: 필수 설정이 누락된 경우
    """
    if not config.OPENAI_API_KEY:
        raise ValueError(
            "❌ OPENAI_API_KEY가 설정되지 않았습니다. "
            ".env 파일을 생성하고 API 키를 설정해주세요.\n"
            "예시: cp env.example .env"
        )
    
    # 가중치 합계 검증
    weight_sum = config.BM25_WEIGHT + config.VECTOR_WEIGHT
    if abs(weight_sum - 1.0) > 0.01:  # 부동소수점 오차 고려
        raise ValueError(
            f"❌ BM25_WEIGHT({config.BM25_WEIGHT}) + VECTOR_WEIGHT({config.VECTOR_WEIGHT}) = {weight_sum}. "
            "합계가 1.0이 되어야 합니다."
        )
    
    print(f"✅ 설정 검증 완료")
    print(f"   - 환경: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"   - 모델: {config.OPENAI_MODEL}")
    print(f"   - 임베딩: {config.EMBEDDING_MODEL}")
    print(f"   - 디버그: {getattr(config, 'DEBUG', False)}")
    print(f"   - 로그 레벨: {config.LOG_LEVEL}")


# 전역 설정 인스턴스 (앱 전체에서 사용)
settings = get_settings() 