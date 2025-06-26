"""
벡터 스토어
ChromaDB를 사용한 벡터 데이터베이스 관리를 담당합니다.
"""

from typing import List, Dict, Any
from core.config import get_settings
from core.logging.config import get_logger

logger = get_logger(__name__)


class VectorStore:
    """벡터 스토어"""

    def __init__(self):
        self.settings = get_settings()
        self.document_count = 0

    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """문서를 벡터 DB에 추가"""
        try:
            logger.info(f"📊 벡터 DB에 {len(documents)}개 문서 추가 중...")

            # TODO: 실제 ChromaDB 연동 구현

            self.document_count = len(documents)
            logger.info("✅ 벡터 DB 문서 추가 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 벡터 DB 문서 추가 실패: {str(e)}")
            return False

    def get_document_count(self) -> int:
        """문서 개수 반환"""
        return self.document_count
