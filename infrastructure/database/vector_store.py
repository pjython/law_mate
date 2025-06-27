"""
벡터 스토어
ChromaDB를 사용한 벡터 데이터베이스 관리를 담당합니다.
"""

import os
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

from core.config import get_settings
from core.logging.config import get_logger

logger = get_logger(__name__)


class VectorStore:
    """벡터 스토어"""

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.document_count = 0

        # 초기화
        self._initialize_chromadb()
        self._initialize_embedding_model()

    def _initialize_chromadb(self):
        """ChromaDB 클라이언트 초기화"""
        try:
            logger.info("🔧 ChromaDB 초기화 중...")

            # ChromaDB 데이터 디렉토리 생성
            db_path = os.path.abspath(self.settings.VECTOR_DB_PATH)
            os.makedirs(db_path, exist_ok=True)

            # ChromaDB 클라이언트 생성
            self.client = chromadb.PersistentClient(
                path=db_path, settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
            )

            # 컬렉션 생성 또는 가져오기
            try:
                self.collection = self.client.get_collection(name=self.settings.COLLECTION_NAME)
                self.document_count = self.collection.count()
                logger.info(f"✅ 기존 컬렉션 로드: {self.settings.COLLECTION_NAME} ({self.document_count}개 문서)")
            except Exception:
                # 컬렉션이 없으면 새로 생성
                self.collection = self.client.create_collection(
                    name=self.settings.COLLECTION_NAME, metadata={"description": "Law Mate 법률 문서 컬렉션"}
                )
                logger.info(f"✅ 새 컬렉션 생성: {self.settings.COLLECTION_NAME}")

        except Exception as e:
            logger.error(f"❌ ChromaDB 초기화 실패: {str(e)}")
            raise

    def _initialize_embedding_model(self):
        """임베딩 모델 초기화"""
        try:
            logger.info(f"🤖 임베딩 모델 로드 중: {self.settings.EMBEDDING_MODEL}")

            self.embedding_model = SentenceTransformer(self.settings.EMBEDDING_MODEL)

            logger.info("✅ 임베딩 모델 로드 완료")

        except Exception as e:
            logger.error(f"❌ 임베딩 모델 로드 실패: {str(e)}")
            # 기본 모델로 폴백
            try:
                logger.warning("🔄 기본 임베딩 모델로 폴백 시도...")
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("✅ 기본 임베딩 모델 로드 완료")
            except Exception as fallback_error:
                logger.error(f"❌ 기본 임베딩 모델 로드도 실패: {str(fallback_error)}")
                raise

    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """문서를 벡터 DB에 추가"""
        try:
            if not documents:
                logger.warning("⚠️ 추가할 문서가 없습니다")
                return True

            logger.info(f"📊 벡터 DB에 {len(documents)}개 문서 추가 중...")

            # 문서 데이터 준비
            ids = []
            contents = []
            metadatas = []
            embeddings = []

            for doc in documents:
                # 고유 ID 생성
                doc_id = doc.get("id", str(uuid.uuid4()))
                ids.append(doc_id)

                # 문서 내용
                content = doc.get("content", "")
                contents.append(content)

                # 메타데이터
                metadata = doc.get("metadata", {})
                # ChromaDB는 문자열과 숫자만 지원하므로 변환
                clean_metadata = self._clean_metadata(metadata)
                clean_metadata["source"] = doc.get("source", "unknown")
                metadatas.append(clean_metadata)

                # 임베딩 생성
                if content:
                    embedding = self.embedding_model.encode(content).tolist()
                    embeddings.append(embedding)
                else:
                    logger.warning(f"⚠️ 빈 문서 내용: {doc_id}")
                    embeddings.append([0.0] * self.embedding_model.get_sentence_embedding_dimension())

            # ChromaDB에 추가
            self.collection.add(ids=ids, documents=contents, metadatas=metadatas, embeddings=embeddings)

            self.document_count = self.collection.count()
            logger.info(f"✅ 벡터 DB 문서 추가 완료: 총 {self.document_count}개 문서")
            return True

        except Exception as e:
            logger.error(f"❌ 벡터 DB 문서 추가 실패: {str(e)}")
            return False

    async def search_similar(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """유사도 검색"""
        try:
            logger.debug(f"🔍 벡터 검색: '{query[:50]}...' (top_k={top_k})")

            if not query.strip():
                logger.warning("⚠️ 빈 검색 쿼리")
                return []

            # 쿼리 임베딩 생성
            query_embedding = self.embedding_model.encode(query).tolist()

            # ChromaDB 검색
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.document_count) if self.document_count > 0 else top_k,
                include=["documents", "metadatas", "distances"],
            )

            # 결과 변환
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
                ):
                    # 거리를 유사도로 변환 (거리가 작을수록 유사도가 높음)
                    similarity = 1.0 / (1.0 + distance)

                    if similarity >= similarity_threshold:
                        search_results.append(
                            {
                                "content": doc,
                                "source": metadata.get("source", "unknown"),
                                "metadata": metadata,
                                "similarity_score": similarity,
                                "distance": distance,
                                "rank": i + 1,
                            }
                        )

            logger.debug(f"✅ 벡터 검색 완료: {len(search_results)}개 결과")
            return search_results

        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {str(e)}")
            return []

    async def delete_documents(self, document_ids: List[str]) -> bool:
        """문서 삭제"""
        try:
            logger.info(f"🗑️ {len(document_ids)}개 문서 삭제 중...")

            # 존재하는 문서 ID만 필터링
            existing_ids = []
            for doc_id in document_ids:
                try:
                    result = self.collection.get(ids=[doc_id])
                    if result["ids"]:
                        existing_ids.append(doc_id)
                except Exception:
                    logger.warning(f"⚠️ 문서 ID 없음: {doc_id}")

            if existing_ids:
                self.collection.delete(ids=existing_ids)
                self.document_count = self.collection.count()
                logger.info(f"✅ {len(existing_ids)}개 문서 삭제 완료")
            else:
                logger.warning("⚠️ 삭제할 문서가 없습니다")

            return True

        except Exception as e:
            logger.error(f"❌ 문서 삭제 실패: {str(e)}")
            return False

    async def clear_collection(self) -> bool:
        """컬렉션 전체 삭제"""
        try:
            logger.warning("🗑️ 컬렉션 전체 삭제 중...")

            # 컬렉션 삭제 후 재생성
            self.client.delete_collection(name=self.settings.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=self.settings.COLLECTION_NAME, metadata={"description": "Law Mate 법률 문서 컬렉션"}
            )

            self.document_count = 0
            logger.info("✅ 컬렉션 전체 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 컬렉션 삭제 실패: {str(e)}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보"""
        try:
            stats = {
                "total_documents": self.document_count,
                "collection_name": self.settings.COLLECTION_NAME,
                "embedding_model": self.settings.EMBEDDING_MODEL,
                "db_path": self.settings.VECTOR_DB_PATH,
            }

            # 추가 통계 (가능한 경우)
            try:
                # 샘플 문서 조회로 메타데이터 분석
                sample_results = self.collection.get(limit=10)
                if sample_results["metadatas"]:
                    sources = set()
                    for metadata in sample_results["metadatas"]:
                        if "source" in metadata:
                            sources.add(metadata["source"])
                    stats["unique_sources"] = len(sources)
                    stats["sample_sources"] = list(sources)[:5]
            except Exception:
                pass

            return stats

        except Exception as e:
            logger.error(f"❌ 통계 정보 조회 실패: {str(e)}")
            return {"total_documents": self.document_count, "error": str(e)}

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        인덱스 재구축을 위한 모든 문서 조회
        ChromaDB에서 모든 문서의 내용과 메타데이터를 가져옵니다.
        """
        try:
            logger.info(f"📄 모든 문서 조회 중... (총 {self.document_count}개)")

            if self.document_count == 0:
                logger.warning("⚠️ 조회할 문서가 없습니다")
                return []

            # ChromaDB에서 모든 문서 조회
            # 대용량 문서를 위해 배치 단위로 조회
            batch_size = 1000  # 한 번에 조회할 문서 수
            all_documents = []

            # 전체 문서를 배치로 나누어 조회
            for offset in range(0, self.document_count, batch_size):
                try:
                    # 현재 배치 크기 계산
                    current_batch_size = min(batch_size, self.document_count - offset)

                    logger.debug(f"📋 배치 조회 중: {offset + 1} ~ {offset + current_batch_size}")

                    # ChromaDB에서 배치 조회
                    batch_results = self.collection.get(
                        limit=current_batch_size, offset=offset, include=["documents", "metadatas"]
                    )

                    # 결과 처리
                    if batch_results["documents"]:
                        for i, (content, metadata) in enumerate(
                            zip(batch_results["documents"], batch_results["metadatas"])
                        ):
                            # 문서 데이터 구성 (ID는 자동 생성)
                            document = {
                                "id": f"doc_{offset + i}",  # 임시 ID 생성
                                "content": content,
                                "source": metadata.get("source", "unknown"),
                                "metadata": metadata,
                            }
                            all_documents.append(document)

                    logger.debug(f"✅ 배치 조회 완료: {len(batch_results['documents'])}개 문서")

                except Exception as batch_error:
                    logger.error(f"❌ 배치 조회 실패 (offset: {offset}): {str(batch_error)}")
                    # 배치 실패 시에도 계속 진행
                    continue

            logger.info(f"✅ 모든 문서 조회 완료: {len(all_documents)}개 문서")
            return all_documents

        except Exception as e:
            logger.error(f"❌ 모든 문서 조회 실패: {str(e)}")
            return []

    async def get_documents_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        특정 소스의 문서들만 조회
        특정 파일이나 소스에서 온 문서들만 가져올 때 사용
        """
        try:
            logger.info(f"📄 소스별 문서 조회: {source}")

            # 메타데이터 필터링으로 특정 소스 문서 조회
            results = self.collection.get(where={"source": source}, include=["documents", "metadatas"])

            documents = []
            if results["documents"]:
                for i, (content, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
                    documents.append(
                        {
                            "id": f"source_{source}_{i}",  # 임시 ID 생성
                            "content": content,
                            "source": metadata.get("source", "unknown"),
                            "metadata": metadata,
                        }
                    )

            logger.info(f"✅ 소스별 문서 조회 완료: {len(documents)}개 문서")
            return documents

        except Exception as e:
            logger.error(f"❌ 소스별 문서 조회 실패: {str(e)}")
            return []

    async def get_documents_count_by_source(self) -> Dict[str, int]:
        """
        소스별 문서 개수 통계
        각 소스(파일)별로 몇 개의 문서가 있는지 조회
        """
        try:
            logger.debug("📊 소스별 문서 개수 조회 중...")

            # 모든 메타데이터 조회
            results = self.collection.get(include=["metadatas"])

            # 소스별 개수 계산
            source_counts = {}
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    source = metadata.get("source", "unknown")
                    source_counts[source] = source_counts.get(source, 0) + 1

            logger.debug(f"✅ 소스별 문서 개수 조회 완료: {len(source_counts)}개 소스")
            return source_counts

        except Exception as e:
            logger.error(f"❌ 소스별 문서 개수 조회 실패: {str(e)}")
            return {}

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB 호환 메타데이터로 변환"""
        clean_metadata = {}

        for key, value in metadata.items():
            # ChromaDB는 문자열과 숫자만 지원
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif isinstance(value, list):
                # 리스트는 문자열로 변환
                clean_metadata[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                # 딕셔너리는 JSON 문자열로 변환
                import json

                clean_metadata[key] = json.dumps(value, ensure_ascii=False)
            else:
                # 기타는 문자열로 변환
                clean_metadata[key] = str(value)

        return clean_metadata

    def get_document_count(self) -> int:
        """문서 개수 반환"""
        return self.document_count

    async def health_check(self) -> Dict[str, Any]:
        """벡터 스토어 상태 확인"""
        try:
            # 기본 정보
            health_info = {
                "status": "healthy",
                "client_connected": self.client is not None,
                "collection_exists": self.collection is not None,
                "embedding_model_loaded": self.embedding_model is not None,
                "document_count": self.document_count,
            }

            # 간단한 검색 테스트
            try:
                test_results = await self.search_similar("테스트", top_k=1)
                health_info["search_functional"] = True
                health_info["search_test_results"] = len(test_results)
            except Exception as e:
                health_info["search_functional"] = False
                health_info["search_error"] = str(e)

            return health_info

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
