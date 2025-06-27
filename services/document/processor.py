"""
문서 처리 서비스 (간소화)
텍스트 문서 로드, 청킹, 전처리를 담당합니다.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.config import get_settings
from core.logging.config import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    """간소화된 문서 처리 서비스"""

    def __init__(self):
        self.settings = get_settings()
        self.processed_chunks = []

        # 청킹 설정
        self.chunk_size = self.settings.CHUNK_SIZE
        self.chunk_overlap = self.settings.CHUNK_OVERLAP

        # 지원 파일 형식 (텍스트만)
        self.supported_extensions = {".txt", ".md"}

    async def process_documents(self, data_path: Optional[str] = None) -> bool:
        """문서 처리"""
        try:
            source_path = data_path or self.settings.DATA_PATH
            logger.info(f"📄 문서 처리 시작: {source_path}")

            if not os.path.exists(source_path):
                logger.warning(f"⚠️ 데이터 경로가 존재하지 않습니다: {source_path}")
                return await self._create_sample_documents()

            # 문서 파일 수집
            document_files = self._collect_document_files(source_path)

            if not document_files:
                logger.warning("⚠️ 처리할 문서 파일이 없습니다. 샘플 문서를 생성합니다.")
                return await self._create_sample_documents()

            # 문서 처리
            self.processed_chunks = []
            total_processed = 0

            for file_path in document_files:
                try:
                    chunks = await self._process_single_file(file_path)
                    self.processed_chunks.extend(chunks)
                    total_processed += len(chunks)
                    logger.debug(f"✅ 파일 처리 완료: {file_path} ({len(chunks)}개 청크)")

                except Exception as e:
                    logger.error(f"❌ 파일 처리 실패: {file_path} - {str(e)}")
                    continue

            logger.info(f"✅ 문서 처리 완료: {len(document_files)}개 파일, {total_processed}개 청크")
            return True

        except Exception as e:
            logger.error(f"❌ 문서 처리 실패: {str(e)}")
            return False

    def _collect_document_files(self, data_path: str) -> List[str]:
        """문서 파일 수집 (텍스트 파일만)"""
        try:
            document_files = []
            data_dir = Path(data_path)

            if data_dir.is_file():
                # 단일 파일인 경우
                if data_dir.suffix.lower() in self.supported_extensions:
                    document_files.append(str(data_dir))
            else:
                # 디렉토리인 경우 재귀적으로 탐색
                for file_path in data_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                        document_files.append(str(file_path))

            logger.debug(f"📁 수집된 문서 파일: {len(document_files)}개")
            return document_files

        except Exception as e:
            logger.error(f"❌ 문서 파일 수집 실패: {str(e)}")
            return []

    async def _process_single_file(self, file_path: str) -> List[Dict[str, Any]]:
        """단일 파일 처리 (간소화)"""
        try:
            file_path_obj = Path(file_path)

            logger.debug(f"📄 파일 처리 중: {file_path}")

            # 파일 내용 읽기
            content = await self._read_text_file(file_path)

            if not content:
                logger.warning(f"⚠️ 빈 파일: {file_path}")
                return []

            # 문서 메타데이터 생성
            metadata = {
                "file_path": file_path,
                "file_name": file_path_obj.name,
                "processed_at": datetime.now().isoformat(),
            }

            # 텍스트 청킹
            chunks = self._create_chunks(content, metadata)

            return chunks

        except Exception as e:
            logger.error(f"❌ 파일 처리 실패: {file_path} - {str(e)}")
            return []

    async def _read_text_file(self, file_path: str) -> str:
        """텍스트 파일 읽기"""
        try:
            # UTF-8 인코딩으로 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"✅ 파일 읽기 성공: {file_path}")
            return content

        except UnicodeDecodeError:
            # CP949 인코딩으로 재시도
            try:
                with open(file_path, "r", encoding="cp949") as f:
                    content = f.read()
                logger.debug(f"✅ 파일 읽기 성공 (CP949): {file_path}")
                return content
            except Exception as e:
                logger.error(f"❌ 파일 읽기 실패: {file_path} - {str(e)}")
                return ""

        except Exception as e:
            logger.error(f"❌ 텍스트 파일 읽기 실패: {file_path} - {str(e)}")
            return ""

    def _create_chunks(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """텍스트 청킹 (간소화)"""
        try:
            # 텍스트 전처리
            cleaned_content = self._preprocess_text(content)

            if not cleaned_content or len(cleaned_content) < 50:
                logger.warning("⚠️ 텍스트가 너무 짧아 청킹하지 않습니다")
                return []

            # 청킹 수행
            chunks = []
            text_length = len(cleaned_content)

            # 문서가 청크 크기보다 작으면 전체를 하나의 청크로
            if text_length <= self.chunk_size:
                chunks.append(
                    {
                        "content": cleaned_content,
                        "source": metadata.get("file_name", "unknown"),
                        "metadata": {**metadata, "chunk_id": 0, "total_chunks": 1},
                    }
                )
            else:
                # 슬라이딩 윈도우 방식으로 청킹
                chunk_id = 0
                start = 0

                while start < text_length:
                    end = min(start + self.chunk_size, text_length)

                    # 문장 경계에서 자르기 시도
                    if end < text_length:
                        for i in range(end, max(start + self.chunk_size // 2, start + 100), -1):
                            if cleaned_content[i - 1] in ".!?\n":
                                end = i
                                break

                    chunk_content = cleaned_content[start:end].strip()

                    if chunk_content and len(chunk_content) > 20:  # 너무 짧은 청크 제외
                        chunks.append(
                            {
                                "content": chunk_content,
                                "source": metadata.get("file_name", "unknown"),
                                "metadata": {**metadata, "chunk_id": chunk_id, "chunk_length": len(chunk_content)},
                            }
                        )
                        chunk_id += 1

                    # 다음 청크 시작점 (오버랩 고려)
                    start = end - self.chunk_overlap

                    if start >= text_length - self.chunk_overlap:
                        break

                # 총 청크 수 메타데이터 업데이트
                for chunk in chunks:
                    chunk["metadata"]["total_chunks"] = len(chunks)

            logger.debug(f"✅ 청킹 완료: {len(chunks)}개 청크")
            return chunks

        except Exception as e:
            logger.error(f"❌ 청킹 실패: {str(e)}")
            return []

    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리 (간소화)"""
        try:
            # 기본 정리
            text = text.strip()

            # 여러 공백을 하나로
            text = re.sub(r"\s+", " ", text)

            # 여러 줄바꿈을 최대 2개로
            text = re.sub(r"\n{3,}", "\n\n", text)

            return text.strip()

        except Exception as e:
            logger.error(f"❌ 텍스트 전처리 실패: {str(e)}")
            return text

    async def _create_sample_documents(self) -> bool:
        """샘플 문서 생성 (간소화)"""
        try:
            logger.info("📝 샘플 문서 생성 중...")

            sample_documents = [
                {
                    "content": """주택임대차보호법에 따른 보증금 반환 절차

1. 내용증명 발송: 임대인에게 보증금 반환을 요구하는 내용증명을 발송합니다.
2. 임차권등기명령 신청: 주택임대차보호법에 따라 임차권등기명령을 신청할 수 있습니다.
3. 소액사건심판 또는 민사소송: 보증금 반환 소송을 제기할 수 있습니다.
4. 강제집행: 승소 판결을 받은 후 강제집행을 통해 보증금을 회수할 수 있습니다.

주택도시보증공사의 전세보증금반환보증 등을 통해 보증금을 보호받을 수 있습니다.""",
                    "source": "주택임대차보호법",
                    "metadata": {"category": "부동산", "type": "법률조항"},
                },
                {
                    "content": """근로기준법에 따른 부당해고 구제 절차

1. 노동위원회 신청: 해고일로부터 3개월 이내에 노동위원회에 부당해고 구제신청을 해야 합니다.
2. 조사 및 심문: 노동위원회에서 사실관계를 조사하고 당사자를 심문합니다.
3. 구제명령: 부당해고가 인정되면 원직복직 및 임금상당액 지급 명령이 내려집니다.
4. 이행강제금: 구제명령을 이행하지 않으면 이행강제금이 부과됩니다.

해고는 정당한 이유가 있어야 하며, 해고절차를 준수해야 합니다.""",
                    "source": "근로기준법",
                    "metadata": {"category": "근로", "type": "법률조항"},
                },
            ]

            self.processed_chunks = sample_documents
            logger.info(f"✅ 샘플 문서 생성 완료: {len(sample_documents)}개")
            return True

        except Exception as e:
            logger.error(f"❌ 샘플 문서 생성 실패: {str(e)}")
            return False

    def get_processed_chunks(self) -> List[Dict[str, Any]]:
        """처리된 문서 청크 반환"""
        return self.processed_chunks

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """문서 처리 통계"""
        try:
            stats = {
                "total_chunks": len(self.processed_chunks),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "supported_extensions": list(self.supported_extensions),
            }

            if self.processed_chunks:
                # 소스별 통계
                sources = {}
                categories = {}
                total_content_length = 0

                for chunk in self.processed_chunks:
                    source = chunk.get("source", "unknown")
                    category = chunk.get("metadata", {}).get("category", "unknown")
                    content_length = len(chunk.get("content", ""))

                    sources[source] = sources.get(source, 0) + 1
                    categories[category] = categories.get(category, 0) + 1
                    total_content_length += content_length

                stats.update(
                    {
                        "sources": sources,
                        "categories": categories,
                        "avg_chunk_length": total_content_length / len(self.processed_chunks),
                        "total_content_length": total_content_length,
                    }
                )

            return stats

        except Exception as e:
            logger.error(f"❌ 처리 통계 조회 실패: {str(e)}")
            return {"error": str(e)}
