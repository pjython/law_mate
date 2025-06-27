"""
Law Mate 설정 관리
환경별 설정을 하나의 파일에서 관리합니다.
"""

import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """환경에 따른 .env 파일 경로 결정"""
    # ENV_FILE 환경변수가 있으면 우선 사용
    if env_file := os.getenv("ENV_FILE"):
        return env_file

    # ENVIRONMENT에 따라 자동 선택
    env = os.getenv("ENVIRONMENT", "development").lower()
    env_files = {"development": ".env.dev", "production": ".env.prod", "test": ".env.test"}
    selected_file = env_files.get(env, ".env")
    print(f"🔧 [CONFIG] 환경 파일 선택: {selected_file} (환경: {env})")
    return selected_file


class Settings(BaseSettings):
    """통합 설정 클래스"""

    # === 애플리케이션 정보 ===
    APP_NAME: str = "Law Mate API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI 기반 법률 상담 하이브리드 검색 API"

    # === 환경 설정 ===
    ENVIRONMENT: str = "development"

    # === OpenAI 설정 ===
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    CLASSIFICATION_TEMPERATURE: float = 0.3
    ANSWER_TEMPERATURE: float = 0.6
    # === Google Gemini 설정===
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""

    # === 서버 설정 ===
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    STREAMLIT_PORT: int = 8501

    # === 데이터베이스 설정 ===
    VECTOR_DB_PATH: str = "./vectordb"
    COLLECTION_NAME: str = "law_documents"

    # === 임베딩 모델 설정 ===
    EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"

    # === 문서 처리 설정 ===
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # === RAG 설정 ===
    TOP_K_DOCUMENTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7

    # === 하이브리드 검색 가중치 ===
    BM25_WEIGHT: float = 0.3
    VECTOR_WEIGHT: float = 0.7

    # === 경로 설정 ===
    DATA_PATH: str = "./data/sample_laws"
    SECRET_PATH: str = "./secrets"

    # === 로깅 설정 ===
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/law_mate_api.log"

    # === 스케줄러 설정 ===
    ENABLE_SCHEDULER: bool = True

    # === Collector 설정 ===
    LAW_API_USER_ID: str = ""

    # === 환경별 .env 파일 로딩 (동적 로딩) ===
    model_config = SettingsConfigDict(env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    def __init__(self, **kwargs):
        """초기화 시 동적으로 환경변수 파일 로드"""
        # 현재 환경에 맞는 .env 파일 결정
        env_file = get_env_file()

        # 환경변수 파일이 존재하면 로드
        if os.path.exists(env_file):
            print(f"📄 [CONFIG] 환경변수 파일 로드: {env_file}")
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)  # override=True로 기존 환경변수 덮어쓰기
        else:
            print(f"⚠️ [CONFIG] 환경변수 파일 없음: {env_file}")

        # 부모 클래스 초기화
        super().__init__(**kwargs)

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """CORS 허용 오리진 목록 (환경별)"""
        if self.ENVIRONMENT.lower() == "development":
            return [
                "http://localhost:3000",  # React 개발 서버
                "http://localhost:8501",  # Streamlit
                "http://127.0.0.1:8501",
                "http://localhost:8000",  # API 서버
                "http://127.0.0.1:8000",
            ]
        elif self.ENVIRONMENT.lower() == "production":
            return [
                "https://your-domain.com",
                "https://www.your-domain.com",
                f"https://streamlit.your-domain.com",
            ]
        else:
            # 기본값
            return [f"http://localhost:{self.STREAMLIT_PORT}", f"http://127.0.0.1:{self.STREAMLIT_PORT}"]

    def model_post_init(self, __context) -> None:
        """초기화 후 필수 디렉토리 생성 및 검증 (한 번만 실행)"""
        print(f"🔧 [CONFIG] Settings 초기화 완료 - 환경: {self.ENVIRONMENT}")

        # 필수 디렉토리 생성
        dirs = [
            os.path.dirname(self.LOG_FILE) if self.LOG_FILE else None,
            self.VECTOR_DB_PATH,
            self.DATA_PATH,
            self.SECRET_PATH,
        ]

        for directory in dirs:
            if directory:
                os.makedirs(directory, exist_ok=True)
                print(f"📁 [CONFIG] 디렉토리 확인: {directory}")

        # 환경별 추가 설정
        self._apply_environment_overrides()

        # 설정 검증
        self._validate_settings()

    def _apply_environment_overrides(self) -> None:
        """환경별 설정 오버라이드"""
        env = self.ENVIRONMENT.lower()

        if env == "development":
            # 개발 환경 오버라이드
            object.__setattr__(self, "DEBUG", True)
            object.__setattr__(self, "LOG_LEVEL", "DEBUG")
            object.__setattr__(self, "ENABLE_SCHEDULER", False)
            print("⚙️ [CONFIG] 개발 환경 설정 적용")

        elif env == "production":
            # 프로덕션 환경 오버라이드
            object.__setattr__(self, "DEBUG", False)
            object.__setattr__(self, "LOG_LEVEL", "WARNING")
            object.__setattr__(self, "ENABLE_SCHEDULER", True)
            print("🏭 [CONFIG] 프로덕션 환경 설정 적용")

        elif env == "test":
            # 테스트 환경 오버라이드
            object.__setattr__(self, "DEBUG", True)
            object.__setattr__(self, "LOG_LEVEL", "DEBUG")
            object.__setattr__(self, "ENABLE_SCHEDULER", False)
            object.__setattr__(self, "VECTOR_DB_PATH", "./vectordb_test")
            print("🧪 [CONFIG] 테스트 환경 설정 적용")

    def _validate_settings(self) -> None:
        """설정 검증"""
        # OpenAI API 키 검증 (개발 환경에서는 스킵)
        if not self.OPENAI_API_KEY and self.ENVIRONMENT.lower() != "development":
            raise ValueError(f"❌ OPENAI_API_KEY가 설정되지 않았습니다. 환경 파일을 확인하세요.")

        # 가중치 검증
        weight_sum = self.BM25_WEIGHT + self.VECTOR_WEIGHT
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(f"❌ 검색 가중치 합계가 1.0이 아닙니다: {weight_sum}")

        print(f"✅ [CONFIG] 설정 검증 완료")


def get_settings() -> Settings:
    """설정 인스턴스 반환 (환경 변경 시 새로운 인스턴스 생성)"""
    print("🚀 [CONFIG] Settings 인스턴스 생성")
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
