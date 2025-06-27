"""
하이브리드 검색 서비스
BM25와 벡터 검색을 결합한 하이브리드 검색을 제공합니다.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
import asyncio

from core.config import get_settings
from core.logging.config import get_logger

logger = get_logger(__name__)


class BM25:
    """BM25 알고리즘 구현"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.term_frequencies = []
        self.document_frequencies = defaultdict(int)
        self.idf_cache = {}

    def fit(self, documents: List[str]) -> None:
        """BM25 인덱스 구축"""
        self.documents = documents
        self.doc_lengths = []
        self.term_frequencies = []
        self.document_frequencies = defaultdict(int)
        self.idf_cache = {}

        # 각 문서를 토큰화하고 통계 계산
        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))

            # 단어 빈도 계산
            term_freq = Counter(tokens)
            self.term_frequencies.append(term_freq)

            # 문서 빈도 계산
            for term in set(tokens):
                self.document_frequencies[term] += 1

        # 평균 문서 길이 계산
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0

        # IDF 사전 계산
        for term in self.document_frequencies:
            self.idf_cache[term] = self._calculate_idf(term)

    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        # 한글, 영문, 숫자만 추출
        text = re.sub(r"[^\w\s가-힣]", " ", text.lower())
        tokens = text.split()

        # 한글 단어 분리 (간단한 방식)
        result_tokens = []
        for token in tokens:
            if len(token) >= 2:  # 2글자 이상만 사용
                result_tokens.append(token)

                # 한글 단어의 경우 2-gram도 추가
                if re.match(r"[가-힣]+", token) and len(token) >= 3:
                    for i in range(len(token) - 1):
                        result_tokens.append(token[i : i + 2])

        return result_tokens

    def _calculate_idf(self, term: str) -> float:
        """IDF 계산"""
        df = self.document_frequencies.get(term, 0)
        if df == 0:
            return 0
        return math.log((len(self.documents) - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """BM25 검색"""
        query_tokens = self._tokenize(query)
        scores = []

        for doc_idx in range(len(self.documents)):
            score = 0
            doc_length = self.doc_lengths[doc_idx]
            term_freq = self.term_frequencies[doc_idx]

            for term in query_tokens:
                if term in term_freq:
                    tf = term_freq[term]
                    idf = self.idf_cache.get(term, 0)

                    # BM25 점수 계산
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                    score += idf * (numerator / denominator)

            scores.append((doc_idx, score))

        # 점수 순으로 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridSearchService:
    """하이브리드 검색 서비스"""

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.settings = get_settings()
        self.bm25 = BM25()
        self.documents = []
        self.document_metadata = []
        self.bm25_index_built = False

        # 가중치 설정
        self.bm25_weight = self.settings.BM25_WEIGHT
        self.vector_weight = self.settings.VECTOR_WEIGHT

    async def build_indexes(self, documents: List[Dict[str, Any]]) -> None:
        """검색 인덱스 구축"""
        try:
            logger.info("🔍 검색 인덱스 구축 중...")

            if not documents:
                logger.warning("⚠️ 인덱스 구축할 문서가 없습니다")
                return

            # 문서 데이터 저장
            self.documents = []
            self.document_metadata = []

            for doc in documents:
                content = doc.get("content", "")
                if content:
                    self.documents.append(content)
                    self.document_metadata.append(
                        {
                            "source": doc.get("source", "unknown"),
                            "metadata": doc.get("metadata", {}),
                            "original_doc": doc,
                        }
                    )

            # BM25 인덱스 구축
            await self._build_bm25_index()

            # 벡터 인덱스는 vector_store에서 처리
            logger.info("✅ 검색 인덱스 구축 완료")

        except Exception as e:
            logger.error(f"❌ 검색 인덱스 구축 실패: {str(e)}")
            raise

    async def _build_bm25_index(self) -> None:
        """BM25 인덱스 구축"""
        try:
            logger.debug("🔤 BM25 인덱스 구축 중...")

            # 별도 스레드에서 BM25 인덱스 구축 (CPU 집약적 작업)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, self.bm25.fit, self.documents)

            self.bm25_index_built = True
            logger.debug("✅ BM25 인덱스 구축 완료")

        except Exception as e:
            logger.error(f"❌ BM25 인덱스 구축 실패: {str(e)}")
            raise

    async def search(self, query: str, top_k: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """하이브리드 검색 수행"""
        try:
            logger.debug(f"🔍 하이브리드 검색: '{query[:50]}...'")

            if not query.strip():
                logger.warning("⚠️ 빈 검색 쿼리")
                return []

            # 병렬로 BM25와 벡터 검색 수행
            bm25_task = self._bm25_search(query, top_k * 2)  # 더 많은 결과 가져오기
            vector_task = self._vector_search(query, top_k * 2, similarity_threshold)

            bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)

            # 하이브리드 점수 계산 및 결합
            hybrid_results = self._combine_results(bm25_results, vector_results, top_k)

            logger.debug(f"✅ 하이브리드 검색 완료: {len(hybrid_results)}개 결과")
            return hybrid_results

        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 실패: {str(e)}")
            return []

    async def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """BM25 검색"""
        try:
            if not self.bm25_index_built or not self.documents:
                logger.warning("⚠️ BM25 인덱스가 구축되지 않았습니다")
                return []

            logger.debug(f"🔤 BM25 검색 수행: '{query[:30]}...'")

            # 별도 스레드에서 BM25 검색 수행
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                bm25_scores = await loop.run_in_executor(executor, self.bm25.search, query, top_k)

            # 결과 변환
            results = []
            for doc_idx, score in bm25_scores:
                if score > 0:  # 점수가 0보다 큰 경우만
                    results.append(
                        {
                            "content": self.documents[doc_idx],
                            "source": self.document_metadata[doc_idx]["source"],
                            "metadata": self.document_metadata[doc_idx]["metadata"],
                            "bm25_score": score,
                            "doc_index": doc_idx,
                        }
                    )

            logger.debug(f"✅ BM25 검색 완료: {len(results)}개 결과")
            return results

        except Exception as e:
            logger.error(f"❌ BM25 검색 실패: {str(e)}")
            return []

    async def _vector_search(self, query: str, top_k: int, similarity_threshold: float) -> List[Dict[str, Any]]:
        """벡터 검색"""
        try:
            logger.debug(f"🔍 벡터 검색 수행: '{query[:30]}...'")

            # 벡터 스토어를 통한 검색
            vector_results = await self.vector_store.search_similar(query, top_k, similarity_threshold)

            # 결과에 벡터 점수 추가
            for result in vector_results:
                result["vector_score"] = result.get("similarity_score", 0.0)

            logger.debug(f"✅ 벡터 검색 완료: {len(vector_results)}개 결과")
            return vector_results

        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {str(e)}")
            return []

    def _combine_results(
        self, bm25_results: List[Dict[str, Any]], vector_results: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """BM25와 벡터 검색 결과 결합"""
        try:
            logger.debug("🔗 검색 결과 결합 중...")

            # 문서별 점수 집계
            doc_scores = defaultdict(
                lambda: {
                    "bm25_score": 0.0,
                    "vector_score": 0.0,
                    "hybrid_score": 0.0,
                    "content": "",
                    "source": "",
                    "metadata": {},
                    "found_in": [],
                }
            )

            # BM25 결과 처리
            max_bm25_score = max([r.get("bm25_score", 0) for r in bm25_results]) if bm25_results else 1.0
            for result in bm25_results:
                content = result["content"]
                normalized_bm25 = result.get("bm25_score", 0) / max_bm25_score if max_bm25_score > 0 else 0

                doc_scores[content]["bm25_score"] = normalized_bm25
                doc_scores[content]["content"] = content
                doc_scores[content]["source"] = result.get("source", "")
                doc_scores[content]["metadata"] = result.get("metadata", {})
                doc_scores[content]["found_in"].append("bm25")

            # 벡터 결과 처리
            for result in vector_results:
                content = result["content"]
                vector_score = result.get("vector_score", 0)

                doc_scores[content]["vector_score"] = vector_score
                if not doc_scores[content]["content"]:  # BM25에서 찾지 못한 경우
                    doc_scores[content]["content"] = content
                    doc_scores[content]["source"] = result.get("source", "")
                    doc_scores[content]["metadata"] = result.get("metadata", {})
                doc_scores[content]["found_in"].append("vector")

            # 하이브리드 점수 계산
            hybrid_results = []
            for content, scores in doc_scores.items():
                if content:  # 빈 문서 제외
                    hybrid_score = scores["bm25_score"] * self.bm25_weight + scores["vector_score"] * self.vector_weight

                    # 두 검색에서 모두 발견된 경우 보너스
                    if len(scores["found_in"]) > 1:
                        hybrid_score *= 1.1

                    hybrid_results.append(
                        {
                            "content": content,
                            "source": scores["source"],
                            "metadata": scores["metadata"],
                            "hybrid_score": hybrid_score,
                            "bm25_score": scores["bm25_score"],
                            "vector_score": scores["vector_score"],
                            "found_in": scores["found_in"],
                            "search_method": "hybrid",
                        }
                    )

            # 하이브리드 점수로 정렬
            hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

            # 상위 결과만 반환
            final_results = hybrid_results[:top_k]

            logger.debug(f"✅ 검색 결과 결합 완료: {len(final_results)}개 최종 결과")
            return final_results

        except Exception as e:
            logger.error(f"❌ 검색 결과 결합 실패: {str(e)}")
            return []

    async def get_search_statistics(self) -> Dict[str, Any]:
        """검색 통계 정보"""
        try:
            stats = {
                "bm25_index_built": self.bm25_index_built,
                "total_documents": len(self.documents),
                "bm25_weight": self.bm25_weight,
                "vector_weight": self.vector_weight,
                "avg_doc_length": self.bm25.avg_doc_length if self.bm25_index_built else 0,
            }

            # 벡터 스토어 통계 추가
            if hasattr(self.vector_store, "get_collection_stats"):
                vector_stats = await self.vector_store.get_collection_stats()
                stats["vector_store"] = vector_stats

            return stats

        except Exception as e:
            logger.error(f"❌ 검색 통계 조회 실패: {str(e)}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """하이브리드 검색 상태 확인"""
        try:
            health_info = {
                "status": "healthy",
                "bm25_ready": self.bm25_index_built,
                "vector_store_ready": self.vector_store is not None,
                "document_count": len(self.documents),
            }

            # 간단한 검색 테스트
            try:
                test_results = await self.search("테스트", top_k=1)
                health_info["search_functional"] = True
                health_info["test_results_count"] = len(test_results)
            except Exception as e:
                health_info["search_functional"] = False
                health_info["search_error"] = str(e)

            return health_info

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def rebuild_index(self) -> None:
        """
        검색 인덱스 재구축
        VectorStore에서 모든 문서를 다시 로드하여 BM25 인덱스를 재구축합니다.
        """
        try:
            logger.info("🔄 검색 인덱스 재구축 시작...")

            # 기존 인덱스 초기화
            self.documents = []
            self.document_metadata = []
            self.bm25_index_built = False
            logger.debug("🧹 기존 인덱스 초기화 완료")

            # VectorStore에서 모든 문서 조회
            logger.debug("📄 VectorStore에서 모든 문서 조회 중...")
            all_documents = await self.vector_store.get_all_documents()

            if not all_documents:
                logger.warning("⚠️ 재구축할 문서가 없습니다")
                return

            logger.info(f"📋 {len(all_documents)}개 문서로 인덱스 재구축 중...")

            # 새로운 인덱스 구축
            await self.build_indexes(all_documents)

            logger.info("✅ 검색 인덱스 재구축 완료")

        except Exception as e:
            logger.error(f"❌ 검색 인덱스 재구축 실패: {str(e)}")
            raise

    async def rebuild_index_by_source(self, source: str) -> None:
        """
        특정 소스의 문서만 인덱스 재구축
        특정 파일의 문서만 업데이트할 때 사용
        """
        try:
            logger.info(f"🔄 소스별 인덱스 재구축 시작: {source}")

            # 해당 소스의 문서 조회
            source_documents = await self.vector_store.get_documents_by_source(source)

            if not source_documents:
                logger.warning(f"⚠️ 소스 '{source}'의 문서가 없습니다")
                return

            # 기존 인덱스에서 해당 소스 문서 제거
            self._remove_documents_by_source(source)

            # 새로운 소스 문서들을 인덱스에 추가
            await self._add_documents_to_index(source_documents)

            logger.info(f"✅ 소스별 인덱스 재구축 완료: {source} ({len(source_documents)}개 문서)")

        except Exception as e:
            logger.error(f"❌ 소스별 인덱스 재구축 실패: {str(e)}")
            raise

    def _remove_documents_by_source(self, source: str) -> None:
        """기존 인덱스에서 특정 소스의 문서 제거"""
        try:
            logger.debug(f"🗑️ 인덱스에서 소스 '{source}' 문서 제거 중...")

            # 제거할 인덱스 찾기
            indices_to_remove = []
            for i, metadata in enumerate(self.document_metadata):
                if metadata.get("source") == source:
                    indices_to_remove.append(i)

            # 역순으로 제거 (인덱스 변경 방지)
            for i in reversed(indices_to_remove):
                if i < len(self.documents):
                    del self.documents[i]
                if i < len(self.document_metadata):
                    del self.document_metadata[i]

            logger.debug(f"✅ {len(indices_to_remove)}개 문서 제거 완료")

        except Exception as e:
            logger.error(f"❌ 소스별 문서 제거 실패: {str(e)}")

    async def _add_documents_to_index(self, documents: List[Dict[str, Any]]) -> None:
        """새로운 문서들을 기존 인덱스에 추가"""
        try:
            logger.debug(f"➕ 인덱스에 {len(documents)}개 문서 추가 중...")

            # 문서 데이터 저장
            new_documents = []
            new_metadata = []

            for doc in documents:
                content = doc.get("content", "")
                if content:
                    new_documents.append(content)
                    new_metadata.append(
                        {
                            "source": doc.get("source", "unknown"),
                            "metadata": doc.get("metadata", {}),
                            "original_doc": doc,
                        }
                    )

            # 기존 데이터에 추가
            self.documents.extend(new_documents)
            self.document_metadata.extend(new_metadata)

            # BM25 인덱스 재구축 (전체 문서로)
            if self.documents:
                await self._build_bm25_index()

            logger.debug(f"✅ {len(new_documents)}개 문서 추가 완료")

        except Exception as e:
            logger.error(f"❌ 문서 추가 실패: {str(e)}")
            raise

    async def get_index_statistics(self) -> Dict[str, Any]:
        """인덱스 통계 정보 조회"""
        try:
            # 기본 통계
            stats = await self.get_search_statistics()

            # 소스별 문서 개수 추가
            source_counts = await self.vector_store.get_documents_count_by_source()
            stats["documents_by_source"] = source_counts

            # 인덱스 상태 정보
            stats["index_status"] = {
                "bm25_built": self.bm25_index_built,
                "documents_in_memory": len(self.documents),
                "metadata_count": len(self.document_metadata),
                "vector_store_count": self.vector_store.get_document_count(),
            }

            return stats

        except Exception as e:
            logger.error(f"❌ 인덱스 통계 조회 실패: {str(e)}")
            return {"error": str(e)}
