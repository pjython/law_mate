"""
완전한 LangChain 기반 RAG 서비스 (Memory 통합)
질문 분류 → 문서 검색 → 답변 생성을 하나의 체인으로 연결하며,
LangChain Memory를 사용하여 대화 맥락을 자동 관리합니다.
"""

import os
from typing import List, Dict, Any, Optional
import json
import asyncio

# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_community.callbacks import get_openai_callback
from langchain.memory import ConversationBufferWindowMemory

from core.config import get_settings
from core.logging.config import get_logger
from infrastructure.database.vector_store import VectorStore
from services.search.hybrid_search import HybridSearchService
from services.llm.constants import *

logger = get_logger(__name__)


class QueryClassificationParser(BaseOutputParser[Dict[str, Any]]):
    """질문 분류 결과 파서"""

    def parse(self, text: str) -> Dict[str, Any]:
        """JSON 응답을 파싱하여 분류 결과 반환"""
        try:
            # JSON 블록 추출
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
            elif "{" in text and "}" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_text = text[json_start:json_end]
            else:
                json_text = text

            result = json.loads(json_text)

            # 필수 필드 검증
            return {
                "is_legal_related": result.get("is_legal_related", False),
                "legal_category": result.get("legal_category"),
                "confidence": float(result.get("confidence", 0.0)),
                "main_topic": result.get("main_topic", ""),
                "key_entities": result.get("key_entities", []),
                "search_keywords": result.get("search_keywords", []),
                "reasoning": result.get("reasoning", ""),
            }

        except Exception as e:
            logger.warning(f"⚠️ 분류 결과 파싱 실패: {str(e)}")
            # 기본값 반환
            return {
                "is_legal_related": False,
                "legal_category": None,
                "confidence": 0.0,
                "main_topic": "",
                "key_entities": [],
                "search_keywords": [],
                "reasoning": "파싱 실패로 기본값 사용",
            }


class LangChainRAGService:
    """완전한 LangChain 기반 RAG 서비스 (Memory 통합)"""

    def __init__(self):
        """LangChain RAG 서비스 초기화"""
        self.settings = get_settings()

        # ChatOpenAI 초기화
        # if self.settings.OPENAI_API_KEY:
        #     self.llm = ChatOpenAI(
        #         api_key=self.settings.OPENAI_API_KEY,
        #         model=self.settings.OPENAI_MODEL,
        #         temperature=self.settings.TEMPERATURE,
        #         max_tokens=1500,
        #         streaming=False
        #     )
        #     logger.info("✅ LangChain ChatOpenAI 초기화 완료")
        if self.settings.GEMINI_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model=self.settings.GEMINI_MODEL,
                google_api_key=self.settings.GEMINI_API_KEY,
                temperature=self.settings.TEMPERATURE,
            )
            logger.info("✅ LangChain Gemini 초기화 완료")
        else:
            self.llm = None
            logger.warning("⚠️ OpenAI API 키가 설정되지 않았습니다.")

        # 검색 서비스 초기화
        self.vector_store = VectorStore()
        self.search_service = HybridSearchService(self.vector_store)

        # Memory 시스템 초기화 (세션별 관리)
        self._memories: Dict[str, ConversationBufferWindowMemory] = {}

        # 시스템 프롬프트 설정
        self.classification_system_template = self._read_prompt_file("system_prompt.txt")
        self.classification_human_template = self._read_prompt_file("human_template.txt")
        self.answer_system_template = self._read_prompt_file("answer_system_template.txt")
        self.answer_human_template = self._read_prompt_file("answer_human_template.txt")

        # 프롬프트 템플릿 설정
        self._setup_prompt_templates()

        # 완전한 RAG 체인 구성
        self._setup_rag_chain()

        logger.info("✅ LangChain RAG 서비스 (Memory 통합) 초기화 완료")

    def _read_prompt_file(self, prompt_file_name: str):
        file_path = os.path.join(self.settings.SECRET_PATH, prompt_file_name)
        prompt_text = ""
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                prompt_text = f.read()
        return prompt_text

    def _get_or_create_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """세션별 Memory 생성 또는 조회"""
        if session_id not in self._memories:
            # 대화 윈도우 메모리 생성 (최근 10개 메시지만 유지)
            self._memories[session_id] = ConversationBufferWindowMemory(
                k=10,  # 최근 10개 메시지만 기억
                memory_key="chat_history",
                return_messages=True,
                human_prefix="사용자",
                ai_prefix="Law Mate",
            )
            logger.debug(f"🧠 새 Memory 생성: {session_id}")

        return self._memories[session_id]

    def _setup_prompt_templates(self):
        """프롬프트 템플릿 설정 (Memory 포함)"""

        # 1. 질문 분류 프롬프트 (대화 맥락 포함)
        self.classification_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(self.classification_system_template),
                HumanMessagePromptTemplate.from_template(self.classification_human_template),
            ]
        )

        # 2. 최종 답변 생성 프롬프트 (대화 맥락 포함)
        self.answer_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(self.answer_system_template),
                HumanMessagePromptTemplate.from_template(self.answer_human_template),
            ]
        )

    def _setup_rag_chain(self):
        """완전한 RAG 체인 구성"""
        if not self.llm:
            self.rag_chain = None
            return

        # 파서 초기화
        classification_parser = QueryClassificationParser()
        answer_parser = StrOutputParser()

        # 1. 질문 분류 체인
        classification_chain = self.classification_prompt | self.llm | classification_parser

        # 2. 문서 검색 함수
        async def retrieve_documents_async(classification_result: Dict[str, Any]) -> Dict[str, Any]:
            """분류 결과를 바탕으로 문서 검색 (비동기)"""
            try:
                # 검색 키워드 추출
                search_keywords = classification_result.get("search_keywords", [])
                main_topic = classification_result.get("main_topic", "")

                # 검색 쿼리 구성
                search_query = " ".join(search_keywords) if search_keywords else main_topic

                if not search_query.strip():
                    logger.warning("⚠️ 검색 쿼리가 비어있음")
                    return {
                        "classification_result": classification_result,
                        "retrieved_docs": [],
                        "search_performed": False,
                    }

                logger.info(f"🔍 문서 검색: '{search_query}'")

                # 하이브리드 검색 수행
                retrieved_docs = await self.search_service.search(
                    query=search_query,
                    top_k=self.settings.TOP_K_DOCUMENTS,
                    similarity_threshold=self.settings.SIMILARITY_THRESHOLD,
                )

                logger.info(f"📚 검색 결과: {len(retrieved_docs)}개 문서")

                return {
                    "classification_result": classification_result,
                    "retrieved_docs": retrieved_docs,
                    "search_performed": True,
                    "search_query": search_query,
                }

            except Exception as e:
                logger.error(f"❌ 문서 검색 실패: {str(e)}")
                return {
                    "classification_result": classification_result,
                    "retrieved_docs": [],
                    "search_performed": False,
                    "error": str(e),
                }

        # 동기 래퍼 함수
        def retrieve_documents(classification_result: Dict[str, Any]) -> Dict[str, Any]:
            """문서 검색 동기 래퍼"""
            return asyncio.create_task(retrieve_documents_async(classification_result))

        # 3. 답변 생성용 데이터 포맷팅
        def format_for_answer(search_result: Dict[str, Any]) -> Dict[str, Any]:
            """답변 생성을 위한 데이터 포맷팅"""
            classification = search_result["classification_result"]
            retrieved_docs = search_result.get("retrieved_docs", [])

            # 분류 결과 포맷팅
            classification_text = f"""법률 관련성: {classification.get('is_legal_related', False)}
법률 분야: {classification.get('legal_category', '없음')}
주요 주제: {classification.get('main_topic', '')}
핵심 개체: {', '.join(classification.get('key_entities', []))}
분류 근거: {classification.get('reasoning', '')}
신뢰도: {classification.get('confidence', 0.0):.2f}"""

            # 검색 문서 포맷팅
            if retrieved_docs:
                docs_text = ""
                for i, doc in enumerate(retrieved_docs[:3], 1):
                    docs_text += f"{i}. 출처: {doc.get('source', '알 수 없음')}\n"
                    docs_text += f"   내용: {doc.get('content', '')}\n"
                    docs_text += f"   유사도: {doc.get('similarity_score', 0.0):.2f}\n\n"
            else:
                docs_text = "관련 법률 문서를 찾을 수 없습니다."

            return {
                "classification_result": classification_text.strip(),
                "retrieved_docs": docs_text.strip(),
                "original_query": search_result.get("original_query", ""),
                # 메타데이터 보존
                "_classification": classification,
                "_retrieved_docs": retrieved_docs,
                "_search_performed": search_result.get("search_performed", False),
            }

        # 4. 최종 답변 생성 체인
        answer_chain = self.answer_prompt | self.llm | answer_parser

        # 5. 완전한 RAG 체인 구성 (단순화된 버전)
        self.classification_chain = classification_chain
        self.answer_chain = answer_chain
        self.retrieve_documents_func = retrieve_documents_async
        self.format_for_answer_func = format_for_answer

        logger.info("✅ 완전한 LangChain RAG 체인 설정 완료")

    async def process_query(
        self, query: str, session_id: str = "default", context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """RAG 파이프라인으로 질문 처리 (Memory 통합)"""
        try:
            if not self.llm:
                return self._generate_fallback_response(query, context_info)

            logger.info(f"🚀 LangChain RAG 파이프라인 시작: '{query[:50]}...' (세션: {session_id})")

            # 세션별 Memory 조회/생성
            memory = self._get_or_create_memory(session_id)

            # 대화 기록을 문자열로 변환
            chat_history = ""
            if hasattr(memory, "chat_memory") and memory.chat_memory.messages:
                # 최근 대화 기록을 문자열로 변환
                recent_messages = memory.chat_memory.messages[-6:]  # 최근 3턴
                for msg in recent_messages:
                    if hasattr(msg, "content"):
                        role = "사용자" if msg.__class__.__name__ == "HumanMessage" else "Law Mate"
                        chat_history += f"{role}: {msg.content}\n"

            # 완전한 RAG 체인 실행 (토큰 사용량 추적)
            with get_openai_callback() as cb:
                # 1단계: 질문 분류 (대화 맥락 포함)
                logger.debug("1️⃣ 질문 분류 중... (대화 맥락 포함)")
                classification_input = {"query": query, "chat_history": chat_history.strip()}
                classification_result = await self.classification_chain.ainvoke(classification_input)

                # 2단계: 문서 검색
                logger.debug("2️⃣ 문서 검색 중...")
                search_result = await self.retrieve_documents_func(classification_result)
                search_result["original_query"] = query

                # 3단계: 답변 생성용 데이터 포맷팅
                logger.debug("3️⃣ 데이터 포맷팅 중...")
                formatted_data = self.format_for_answer_func(search_result)
                formatted_data["chat_history"] = chat_history.strip()

                # 4단계: 최종 답변 생성 (대화 맥락 포함)
                logger.debug("4️⃣ 답변 생성 중... (대화 맥락 포함)")
                answer = await self.answer_chain.ainvoke(formatted_data)

                # 5단계: Memory에 대화 저장
                logger.debug("5️⃣ 대화 기록 저장 중...")
                memory.save_context({"input": query}, {"output": answer})

            # 결과 추출
            classification = formatted_data["_classification"]
            retrieved_docs = formatted_data["_retrieved_docs"]
            search_performed = formatted_data["_search_performed"]

            # 신뢰도 계산
            confidence = self._calculate_confidence(answer, retrieved_docs, classification.get("confidence", 0.0))

            logger.info(f"✅ LangChain RAG 파이프라인 완료 (토큰: {cb.total_tokens}, 세션: {session_id})")

            return {
                "answer": answer,
                "confidence": confidence,
                "classification": {
                    "is_legal_related": classification.get("is_legal_related", False),
                    "category": classification.get("legal_category"),
                    "confidence": classification.get("confidence", 0.0),
                    "reason": f"LangChain 분류: {classification.get('reasoning', '')}",
                    "main_topic": classification.get("main_topic", ""),
                    "key_entities": classification.get("key_entities", []),
                    "is_follow_up": classification.get("is_follow_up", False),
                },
                "retrieved_docs": retrieved_docs,
                "search_performed": search_performed,
                "tokens_used": cb.total_tokens,
                "model": self.settings.OPENAI_MODEL,
                "cost": cb.total_cost if hasattr(cb, "total_cost") else 0.0,
                "pipeline_type": "langchain_full_rag_with_memory",
                "session_id": session_id,
                "has_context": len(chat_history) > 0,
            }

        except Exception as e:
            logger.error(f"❌ LangChain RAG 파이프라인 실패: {str(e)}")

            # API 키 오류인 경우 더 나은 폴백 제공
            if "401" in str(e) or "api_key" in str(e).lower():
                return self._generate_enhanced_fallback_response(query, session_id, context_info)

            return {
                "answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
                "confidence": 0.0,
                "classification": {
                    "is_legal_related": False,
                    "category": None,
                    "confidence": 0.0,
                    "reason": f"파이프라인 오류: {str(e)}",
                },
                "error": str(e),
                "pipeline_type": "langchain_full_rag_with_memory",
                "session_id": session_id,
            }

    def _calculate_confidence(
        self, answer: str, retrieved_docs: List[Dict[str, Any]], classification_confidence: float
    ) -> float:
        """종합 신뢰도 계산"""
        confidence = classification_confidence * 0.4  # 분류 신뢰도 40%

        # 답변 길이 기반 조정 (20%)
        if len(answer) > 100:
            confidence += 0.1
        if len(answer) > 300:
            confidence += 0.1

        # 참조 문서 수 기반 조정 (30%)
        if retrieved_docs:
            confidence += min(len(retrieved_docs) * 0.1, 0.3)

        # 법률 키워드 포함 여부 (10%)
        keyword_count = sum(1 for keyword in LEGAL_KEYWORDS if keyword in answer)
        confidence += min(keyword_count * 0.02, 0.1)

        return min(max(confidence, 0.0), 1.0)

    def _generate_fallback_response(self, query: str, context_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """폴백 응답 생성 (API 키가 없을 때)"""
        return {
            "answer": f"안녕하세요! Law Mate입니다. '{query}'에 대한 답변을 위해 OpenAI API 키가 필요합니다.",
            "confidence": 0.0,
            "classification": {
                "is_legal_related": False,
                "category": None,
                "confidence": 0.0,
                "reason": "API 키 없음으로 분류 불가",
            },
            "retrieved_docs": [],
            "search_performed": False,
            "model": "fallback",
            "tokens_used": 0,
            "pipeline_type": "langchain_full_rag",
        }

    def _generate_enhanced_fallback_response(
        self, query: str, session_id: str, context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """향상된 폴백 응답 생성 (API 키 오류 시 더 나은 답변)"""

        # 기본적인 규칙 기반 분류
        query_lower = query.lower()

        legal_category = None
        is_legal_related = False

        # 간단한 키워드 기반 분류
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                legal_category = category
                is_legal_related = True
                break

        # Memory에 기록 (세션이 있는 경우)
        if session_id != "default":
            memory = self._get_or_create_memory(session_id)
            fallback_answer = (
                f"안녕하세요! Law Mate입니다. '{query}'에 대한 질문을 받았습니다. "
                f"현재 OpenAI API 연결에 문제가 있어 완전한 답변을 드리기 어렵습니다. "
                f"API 키를 확인해주세요."
            )

            if is_legal_related:
                fallback_answer += f" 질문이 {legal_category} 분야와 관련된 것 같습니다."

            # Memory에 저장
            memory.save_context({"input": query}, {"output": fallback_answer})
        else:
            fallback_answer = f"API 키 설정이 필요합니다. '{query}' 질문에 대한 답변을 위해 OpenAI API 키를 확인해주세요."

        return {
            "answer": fallback_answer,
            "confidence": 0.3 if is_legal_related else 0.1,
            "classification": {
                "is_legal_related": is_legal_related,
                "category": legal_category,
                "confidence": 0.7 if is_legal_related else 0.0,
                "reason": f"규칙 기반 분류 (API 키 오류로 인한 폴백): {legal_category or '일반'}",
            },
            "retrieved_docs": [],
            "search_performed": False,
            "model": "fallback_enhanced",
            "tokens_used": 0,
            "pipeline_type": "langchain_full_rag_with_memory",
            "session_id": session_id,
            "fallback_reason": "OpenAI API 키 오류",
        }

    def clear_memory(self, session_id: str) -> bool:
        """특정 세션의 Memory 초기화"""
        if session_id in self._memories:
            self._memories[session_id].clear()
            logger.info(f"🧹 Memory 초기화: {session_id}")
            return True
        return False

    def delete_memory(self, session_id: str) -> bool:
        """특정 세션의 Memory 삭제"""
        if session_id in self._memories:
            del self._memories[session_id]
            logger.info(f"🗑️ Memory 삭제: {session_id}")
            return True
        return False

    def get_memory_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Memory 통계 정보"""
        try:
            if session_id:
                # 특정 세션의 통계
                memory = self._memories.get(session_id)
                if memory and hasattr(memory, "chat_memory"):
                    messages = memory.chat_memory.messages
                    return {
                        "session_id": session_id,
                        "message_count": len(messages),
                        "messages": [
                            {
                                "role": "user" if msg.__class__.__name__ == "HumanMessage" else "assistant",
                                "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                            }
                            for msg in messages
                        ],
                        "memory_type": "ConversationBufferWindowMemory",
                    }
                else:
                    return {
                        "session_id": session_id,
                        "message_count": 0,
                        "messages": [],
                        "memory_type": "ConversationBufferWindowMemory",
                    }
            else:
                # 전체 통계
                return {
                    "total_sessions": len(self._memories),
                    "memory_info": {
                        session_id: {
                            "message_count": len(memory.chat_memory.messages) if hasattr(memory, "chat_memory") else 0,
                            "memory_type": memory.__class__.__name__,
                        }
                        for session_id, memory in self._memories.items()
                    },
                }
        except Exception as e:
            logger.error(f"❌ Memory 통계 조회 실패: {str(e)}")
            return {}

    async def get_pipeline_info(self) -> Dict[str, Any]:
        """파이프라인 정보 조회"""
        return {
            "pipeline_type": "langchain_full_rag_with_memory",
            "llm_available": self.llm is not None,
            "model": self.settings.OPENAI_MODEL if self.llm else None,
            "temperature": self.settings.TEMPERATURE,
            "chain_configured": self.llm is not None,
            "memory_enabled": True,
            "memory_sessions": len(self._memories),
            "components": {
                "classification": "LangChain + LLM + Memory",
                "retrieval": "HybridSearch (BM25 + Vector)",
                "generation": "LangChain + LLM + Memory",
                "memory": "ConversationBufferWindowMemory",
            },
            "flow": "Query + Memory → Classification → Retrieval → Generation → Memory Update",
        }
