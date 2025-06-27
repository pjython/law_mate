"""
Streamlit 클라이언트 - 프론트엔드 MVP
FastAPI 서버와 통신하여 AI 처리 요청
대화 맥락을 지원하는 연속적인 대화 기능 제공
"""

import streamlit as st
import httpx
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# 페이지 설정
st.set_page_config(page_title="Law Mate - 법률 상담 AI", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

# API 서버 설정
API_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30.0

# 커스텀 CSS (기존과 동일)
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #333333 !important;
    }
    
    .chat-message strong {
        color: #1a1a1a !important;
    }
    
    .chat-message small {
        color: #666666 !important;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        color: #1565c0 !important;
    }
    
    .assistant-message {
        background-color: #f1f8e9;
        border-left: 4px solid #4caf50;
        color: #2e7d32 !important;
    }
    
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        color: #c62828 !important;
    }
    
    .context-info {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        color: #e65100 !important;
        font-size: 0.9em;
        margin-bottom: 0.5rem;
    }
    
    .api-status {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    .status-healthy {
        background-color: #e8f5e8;
        color: #2e7d32;
    }
    
    .status-error {
        background-color: #ffebee;
        color: #c62828;
    }
    
    .status-loading {
        background-color: #fff3e0;
        color: #ef6c00;
    }
</style>
""",
    unsafe_allow_html=True,
)


class APIClient:
    """FastAPI 서버와 통신하는 클라이언트 (대화 맥락 지원)"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url

    async def health_check(self) -> Dict[str, Any]:
        """서버 헬스체크"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/health")
                response.raise_for_status()
                return {"status": "healthy", "data": response.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/health/status")
                response.raise_for_status()
                return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def start_new_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """새로운 대화 세션 시작 (단순히 성공 응답 반환)"""
        # LangChain Memory가 자동으로 세션을 관리하므로 별도 API 호출 불필요
        return {
            "status": "success", 
            "data": {
                "message": "새로운 대화 세션을 시작할 준비가 되었습니다.",
                "user_id": user_id
            }
        }

    async def process_query(
        self, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """질문 처리 요청 (대화 맥락 지원)"""
        try:
            payload = {"query": query, "user_id": user_id, "session_id": session_id}

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(f"{self.base_url}/api/v1/query", json=payload)
                response.raise_for_status()
                return {"status": "success", "data": response.json()}

        except httpx.TimeoutException:
            return {"status": "error", "error": "요청 시간 초과 (30초)"}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "error": f"HTTP 오류: {e.response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def clear_session_memory(self, session_id: str) -> Dict[str, Any]:
        """세션 메모리 클리어 (대화 종료와 동일한 효과)"""
        # 실제로는 클라이언트 측에서 세션 ID를 초기화하는 것으로 충분
        return {
            "status": "success", 
            "data": {
                "message": f"세션 {session_id[:8]}...의 대화가 종료되었습니다.",
                "session_id": session_id
            }
        }

    async def rebuild_indexes(self, backup: bool = False, force: bool = False) -> Dict[str, Any]:
        """인덱스 재구축 요청"""
        try:
            payload = {"backup": backup, "force": force}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.base_url}/api/v1/admin/rebuild-indexes", json=payload)
                response.raise_for_status()
                return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}


def initialize_session_state():
    """세션 상태 초기화"""
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "server_status" not in st.session_state:
        st.session_state.server_status = "unknown"

    # 대화 관리 상태 추가
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None

    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user_{str(uuid.uuid4())[:8]}"

    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = {}


async def check_server_status():
    """서버 상태 확인"""
    try:
        health_result = await st.session_state.api_client.health_check()

        if health_result["status"] == "healthy":
            st.session_state.server_status = "healthy"
            return True
        else:
            st.session_state.server_status = "error"
            return False

    except Exception as e:
        st.session_state.server_status = "error"
        return False


def display_server_status():
    """서버 상태 표시"""
    if st.session_state.server_status == "healthy":
        st.markdown(
            """
        <div class="api-status status-healthy">
            ✅ API 서버 연결됨
        </div>
        """,
            unsafe_allow_html=True,
        )
    elif st.session_state.server_status == "error":
        st.markdown(
            """
        <div class="api-status status-error">
            ❌ API 서버 연결 실패 - 서버가 실행 중인지 확인해주세요
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div class="api-status status-loading">
            🔄 서버 상태 확인 중...
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_chat_message(
    message_type: str, content: str, timestamp: str, extra_info: Dict = None, context_info: Dict = None
):
    """채팅 메시지 표시 (맥락 정보 포함)"""

    # 맥락 정보 표시
    if context_info and context_info.get("is_follow_up"):
        context_text = f"🔗 후속 질문 (맥락 점수: {context_info.get('context_score', 0):.2f})"
        if context_info.get("suggested_category"):
            context_text += f" | 카테고리: {context_info['suggested_category']}"

        st.markdown(
            f"""
        <div class="chat-message context-info">
            <small>{context_text}</small>
        </div>
        """,
            unsafe_allow_html=True,
        )

    if message_type == "user":
        st.markdown(
            f"""
        <div class="chat-message user-message">
            <strong>👤 사용자</strong> <small>({timestamp})</small><br>
            {content}
        </div>
        """,
            unsafe_allow_html=True,
        )
    elif message_type == "assistant":
        # 검색 방법 정보 표시
        search_info = ""
        if extra_info and extra_info.get("search_method"):
            search_info = f"<small>[{extra_info['search_method']}]</small><br>"

        st.markdown(
            f"""
        <div class="chat-message assistant-message">
            <strong>⚖️ Law Mate</strong> <small>({timestamp})</small><br>
            {search_info}
            {content}
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 추가 정보 표시
        if extra_info:
            with st.expander("📊 상세 정보"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("신뢰도", f"{extra_info.get('confidence', 0):.2f}")

                with col2:
                    st.metric("처리 시간", f"{extra_info.get('processing_time', 0):.2f}초")

                with col3:
                    st.metric("검색된 문서", f"{extra_info.get('retrieved_docs_count', 0)}개")

                with col4:
                    st.metric("검색 방법", extra_info.get("search_method", "N/A"))

                # 참조 문서
                if extra_info.get("sources"):
                    st.markdown("**📄 참조 문서:**")
                    for i, source in enumerate(extra_info["sources"][:3], 1):
                        with st.expander(f"{i}. {source.get('source', 'Unknown')}"):
                            st.write(f"**하이브리드 점수**: {source.get('hybrid_score', 0):.3f}")
                            st.write(f"**BM25 점수**: {source.get('bm25_score', 0):.3f}")
                            st.write(f"**벡터 점수**: {source.get('vector_score', 0):.3f}")
                            st.write("**내용 미리보기**:")
                            st.write(source.get("content_preview", "내용 없음"))

                # 대화 맥락 정보
                if context_info:
                    st.markdown("**🧠 대화 맥락:**")
                    if context_info.get("conversation_info"):
                        conv_info = context_info["conversation_info"]
                        st.write(f"**현재 주제**: {conv_info.get('current_topic', 'N/A')}")
                        st.write(f"**법률 카테고리**: {conv_info.get('legal_category', 'N/A')}")
                        st.write(f"**메시지 수**: {conv_info.get('message_count', 0)}개")
    else:  # error
        st.markdown(
            f"""
        <div class="chat-message error-message">
            <strong>❌ 오류</strong> <small>({timestamp})</small><br>
            {content}
        </div>
        """,
            unsafe_allow_html=True,
        )


async def start_new_conversation():
    """새로운 대화 시작"""
    with st.spinner("🆕 새로운 대화를 시작하고 있습니다..."):
        result = await st.session_state.api_client.start_new_session(user_id=st.session_state.user_id)

    if result["status"] == "success":
        # 세션 상태 초기화 (실제 세션 ID는 첫 질문 시 생성됨)
        st.session_state.current_session_id = "ready"  # 준비 상태 표시
        st.session_state.conversation_context = {}
        st.session_state.chat_history = []  # 채팅 기록 초기화

        st.success("✅ 새로운 대화가 시작되었습니다! 첫 번째 질문을 입력해주세요.")
        return True
    else:
        st.error(f"❌ 대화 시작 실패: {result['error']}")
        return False


async def process_query_async(user_query: str):
    """비동기 질문 처리 (대화 맥락 지원)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 사용자 메시지 추가
    st.session_state.chat_history.append({"type": "user", "content": user_query, "timestamp": timestamp})

    # API 요청 (ready 상태면 None으로 전달하여 새 세션 생성)
    session_id_to_send = None if st.session_state.current_session_id == "ready" else st.session_state.current_session_id
    
    with st.spinner("🔍 하이브리드 검색으로 질문을 처리하고 있습니다..."):
        result = await st.session_state.api_client.process_query(
            query=user_query, user_id=st.session_state.user_id, session_id=session_id_to_send
        )

    # 응답 처리
    if result["status"] == "success":
        response_data = result["data"]

        # response_data가 None인지 확인
        if response_data is None:
            st.session_state.chat_history.append(
                {
                    "type": "error",
                    "content": "서버에서 빈 응답을 받았습니다.",
                    "timestamp": timestamp,
                }
            )
            return

        # success 필드 확인 (기본값 True)
        success = response_data.get("success", True)
        
        if success:
            # 세션 ID 업데이트 (새로 생성된 경우)
            session_id = response_data.get("session_id")
            if session_id:
                st.session_state.current_session_id = session_id

            # 대화 맥락 정보 업데이트
            conversation_info = response_data.get("conversation_info")
            if conversation_info:
                st.session_state.conversation_context = conversation_info

            # 성공적인 AI 응답
            st.session_state.chat_history.append(
                {
                    "type": "assistant",
                    "content": response_data.get("answer", "답변을 생성할 수 없습니다."),
                    "timestamp": timestamp,
                    "extra_info": {
                        "confidence": response_data.get("confidence", 0.0),
                        "processing_time": response_data.get("processing_time", 0.0),
                        "search_method": response_data.get("search_method", "하이브리드 검색"),
                        "retrieved_docs_count": response_data.get("retrieved_docs_count", 0),
                        "sources": response_data.get("sources", []),
                        "classification": response_data.get("classification", {}),
                    },
                    "context_info": {
                        "is_follow_up": response_data.get("context_analysis", {}).get("is_follow_up", False) if response_data.get("context_analysis") else False,
                        "context_score": response_data.get("context_analysis", {}).get("context_score", 0.0) if response_data.get("context_analysis") else 0.0,
                        "suggested_category": response_data.get("context_analysis", {}).get("suggested_category") if response_data.get("context_analysis") else None,
                        "conversation_info": conversation_info or {},
                    },
                }
            )
        else:
            # AI 처리 오류
            error_msg = response_data.get('error', '알 수 없는 오류')
            st.session_state.chat_history.append(
                {
                    "type": "error",
                    "content": f"AI 처리 오류: {error_msg}",
                    "timestamp": timestamp,
                }
            )
    else:
        # API 통신 오류
        error_msg = result.get('error', '알 수 없는 오류')
        st.session_state.chat_history.append(
            {"type": "error", "content": f"API 통신 오류: {error_msg}", "timestamp": timestamp}
        )


async def end_current_conversation():
    """현재 대화 종료"""
    if not st.session_state.current_session_id or st.session_state.current_session_id == "ready":
        st.warning("⚠️ 활성 대화가 없습니다.")
        return

    with st.spinner("🔚 대화를 종료하고 있습니다..."):
        result = await st.session_state.api_client.clear_session_memory(st.session_state.current_session_id)

    if result["status"] == "success":
        # 채팅 기록에서 메시지 수 계산
        total_messages = len([msg for msg in st.session_state.chat_history if msg["type"] in ["user", "assistant"]])
        
        st.success(f"✅ 대화가 종료되었습니다! (총 {total_messages}개 메시지)")

        # 세션 상태 초기화
        st.session_state.current_session_id = None
        st.session_state.conversation_context = {}
    else:
        st.error(f"❌ 대화 종료 실패: {result['error']}")


def main():
    """메인 함수"""
    initialize_session_state()

    # 헤더
    st.markdown(
        """
    <div class="main-header">
        <h1>⚖️ Law Mate</h1>
        <p>AI 기반 개인 법률 상담 서비스 (대화 맥락 지원)</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 서버 상태 확인
    if st.button("🔄 서버 상태 확인"):
        with st.spinner("서버 상태 확인 중..."):
            asyncio.run(check_server_status())

    display_server_status()

    # 사이드바
    with st.sidebar:
        st.header("🛠️ 시스템 관리")

        # API 서버 정보
        st.markdown("### 🔗 API 서버")
        st.info(f"**서버 주소**: {API_BASE_URL}")
        st.info(f"**사용자 ID**: {st.session_state.user_id}")

        # 현재 세션 정보
        if st.session_state.current_session_id:
            if st.session_state.current_session_id == "ready":
                st.info("**현재 세션**: 대화 준비 중...")
            else:
                st.info(f"**현재 세션**: {st.session_state.current_session_id[:8]}...")

            # 대화 맥락 정보
            if st.session_state.conversation_context:
                context = st.session_state.conversation_context
                st.markdown("### 🧠 대화 맥락")
                if context.get("current_topic"):
                    st.write(f"**주제**: {context['current_topic']}")
                if context.get("legal_category"):
                    st.write(f"**분야**: {context['legal_category']}")
                st.write(f"**메시지**: {context.get('message_count', 0)}개")
        else:
            st.warning("활성 대화 없음")

        # 대화 관리
        st.markdown("### 💬 대화 관리")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 새 대화"):
                asyncio.run(start_new_conversation())
                st.rerun()

        with col2:
            if st.button("🔚 대화 종료"):
                if st.session_state.current_session_id:
                    asyncio.run(end_current_conversation())
                    st.rerun()
                else:
                    st.warning("종료할 대화가 없습니다.")

        # 서버 상태 상세 정보
        if st.button("📊 시스템 상태 조회"):
            with st.spinner("시스템 상태 조회 중..."):

                async def get_status():
                    return await st.session_state.api_client.get_system_status()

                status_result = asyncio.run(get_status())

                if status_result["status"] == "success":
                    status_data = status_result["data"]
                    st.success("✅ 시스템 정상 동작")

                    st.subheader("📊 상세 상태")
                    st.info(f"🔍 검색 방식: {status_data.get('search_method', 'N/A')}")
                    st.info(f"📄 문서 수: {status_data.get('document_count', 0)}개")
                    st.info(f"⏱️ 서버 가동시간: {status_data.get('uptime', 0):.1f}초")

                    # 대화 통계
                    if status_data.get("conversation_stats"):
                        conv_stats = status_data["conversation_stats"]
                        st.subheader("💬 대화 통계")
                        st.info(f"📊 총 세션: {conv_stats.get('sessions', {}).get('total_sessions', 0)}개")
                        st.info(f"🔄 활성 세션: {conv_stats.get('sessions', {}).get('active_sessions', 0)}개")
                        st.info(f"💬 총 메시지: {conv_stats.get('sessions', {}).get('total_messages', 0)}개")
                else:
                    st.error(f"❌ 상태 조회 실패: {status_result['error']}")

        # 인덱스 재구축
        if st.button("🔄 인덱스 재구축"):
            with st.spinner("인덱스 재구축 요청 중..."):

                async def rebuild():
                    return await st.session_state.api_client.rebuild_indexes()

                rebuild_result = asyncio.run(rebuild())

                if rebuild_result["status"] == "success":
                    st.success("✅ 인덱스 재구축 요청 완료!")
                    st.info("백그라운드에서 재구축이 진행됩니다.")
                else:
                    st.error(f"❌ 재구축 요청 실패: {rebuild_result['error']}")

        st.markdown("---")

        # 채팅 관리
        if st.button("🗑️ 채팅 기록 삭제"):
            st.session_state.chat_history = []
            st.success("채팅 기록이 삭제되었습니다.")

    # 메인 콘텐츠
    if st.session_state.server_status != "healthy":
        st.warning("⚠️ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")

        st.markdown("### 🚀 서버 실행 방법")
        st.code(
            """
# 터미널에서 다음 명령어 실행:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        """
        )

        return

    # 채팅 인터페이스
    st.markdown("## 💬 법률 상담 채팅")

    # 현재 세션이 없으면 새 대화 시작 안내
    if not st.session_state.current_session_id:
        st.info("💡 새로운 대화를 시작하려면 사이드바의 '🆕 새 대화' 버튼을 클릭하세요.")

    # 채팅 히스토리 표시
    if st.session_state.chat_history:
        st.markdown("### 📋 대화 기록")
        for chat in st.session_state.chat_history:
            display_chat_message(
                chat["type"], chat["content"], chat["timestamp"], chat.get("extra_info"), chat.get("context_info")
            )

    # 질문 입력 (세션이 있을 때만)
    if st.session_state.current_session_id:
        st.markdown("### ❓ 질문하기")

        # 예시 질문
        example_questions = ["전세보증금을 돌려받지 못하고 있어요", "임대차 계약을 중도 해지하고 싶습니다", "회사에서 부당 해고를 당했어요", "부동산 매매 계약서를 검토해주세요"]

        st.markdown("**💡 예시 질문:**")
        for i, example in enumerate(example_questions):
            if st.button(f"🔸 {example}", key=f"example_{i}"):
                asyncio.run(process_query_async(example))
                st.rerun()

        # 직접 입력
        with st.form("query_form"):
            user_query = st.text_area("법률 관련 질문을 입력하세요:", height=100, placeholder="예: 그럼 전세보증금 반환 절차는 어떻게 되나요? (후속 질문)")

            submitted = st.form_submit_button("📨 질문하기", type="primary")

            if submitted and user_query.strip():
                asyncio.run(process_query_async(user_query.strip()))
                st.rerun()


if __name__ == "__main__":
    main()
