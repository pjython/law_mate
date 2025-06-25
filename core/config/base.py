"""
기본 설정 클래스
모든 환경에서 공통으로 사용되는 설정을 정의합니다.
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    """기본 설정 클래스"""
    
    # 애플리케이션 정보
    APP_NAME: str = "Law Mate API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI 기반 법률 상담 하이브리드 검색 API"
    
    # OpenAI 설정
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    TEMPERATURE: float = Field(default=0.5, env="TEMPERATURE")
    
    # 서버 설정
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    STREAMLIT_PORT: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # 데이터베이스 설정
    VECTOR_DB_PATH: str = Field(default="./vectordb", env="VECTOR_DB_PATH")
    COLLECTION_NAME: str = Field(default="law_documents", env="COLLECTION_NAME")
    
    # 임베딩 모델 설정
    EMBEDDING_MODEL: str = Field(default="jhgan/ko-sroberta-multitask", env="EMBEDDING_MODEL")
    
    # 문서 처리 설정
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # RAG 설정
    TOP_K_DOCUMENTS: int = Field(default=5, env="TOP_K_DOCUMENTS")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # 하이브리드 검색 가중치
    BM25_WEIGHT: float = Field(default=0.3, env="BM25_WEIGHT")
    VECTOR_WEIGHT: float = Field(default=0.7, env="VECTOR_WEIGHT")
    
    # 데이터 경로
    DATA_PATH: str = Field(default="./data/sample_laws", env="DATA_PATH")
    SECRET_PATH: str = Field(default="./secrets", env="SECRET_PATH")
    
    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/law_mate_api.log", env="LOG_FILE")
    
    # 스케줄러 설정
    ENABLE_SCHEDULER: bool = Field(default=True, env="ENABLE_SCHEDULER")
    
    # CORS 설정
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        return [
            f"http://localhost:{self.STREAMLIT_PORT}",
            f"http://127.0.0.1:{self.STREAMLIT_PORT}"
        ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def create_directories(self) -> None:
        """필수 디렉토리 생성"""
        directories = [
            os.path.dirname(self.LOG_FILE),
            self.VECTOR_DB_PATH,
            self.DATA_PATH,
            self.SECRET_PATH
        ]
        
        for directory in directories:
            if directory:  # 빈 문자열 체크
                os.makedirs(directory, exist_ok=True) 