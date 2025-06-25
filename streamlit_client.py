"""
Streamlit 클라이언트 - 프론트엔드 MVP
FastAPI 서버와 통신하여 AI 처리 요청
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
    """FastAPI 서버와 통신하는 클라이언트"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())  # 세션 ID 생성

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

    async def process_query(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """질문 처리 요청"""
        try:
            payload = {"query": query, "user_id": user_id, "session_id": self.session_id}

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


def display_chat_message(message_type: str, content: str, timestamp: str, extra_info: Dict = None):
    """채팅 메시지 표시"""
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


async def process_query_async(user_query: str):
    """비동기 질문 처리"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 사용자 메시지 추가
    st.session_state.chat_history.append({"type": "user", "content": user_query, "timestamp": timestamp})

    # API 요청
    with st.spinner("🔍 하이브리드 검색으로 질문을 처리하고 있습니다..."):
        result = await st.session_state.api_client.process_query(user_query)

    # 응답 처리
    if result["status"] == "success":
        response_data = result["data"]

        if response_data["success"]:
            # 성공적인 AI 응답
            st.session_state.chat_history.append(
                {
                    "type": "assistant",
                    "content": response_data["answer"],
                    "timestamp": timestamp,
                    "extra_info": {
                        "confidence": response_data["confidence"],
                        "processing_time": response_data["processing_time"],
                        "search_method": response_data["search_method"],
                        "retrieved_docs_count": response_data["retrieved_docs_count"],
                        "sources": response_data["sources"],
                    },
                }
            )
        else:
            # AI 처리 오류
            st.session_state.chat_history.append(
                {
                    "type": "error",
                    "content": f"AI 처리 오류: {response_data.get('error', '알 수 없는 오류')}",
                    "timestamp": timestamp,
                }
            )
    else:
        # API 통신 오류
        st.session_state.chat_history.append(
            {"type": "error", "content": f"API 통신 오류: {result['error']}", "timestamp": timestamp}
        )


def main():
    """메인 함수"""
    initialize_session_state()

    # 헤더
    st.markdown(
        """
    <div class="main-header">
        <h1>⚖️ Law Mate</h1>
        <p>AI 기반 개인 법률 상담 서비스 (API 클라이언트)</p>
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
        st.info(f"**세션 ID**: {st.session_state.api_client.session_id[:8]}...")

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
                    st.info(f"📚 BM25 인덱스: {'✅' if status_data.get('bm25_index_built', False) else '❌'}")
                    st.info(f"⏱️ 서버 가동시간: {status_data.get('uptime', 'N/A')}")
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
python api_server.py

# 또는
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
        """
        )

        st.markdown("### 🎯 시스템 구조")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                """
            **🖥️ 프론트엔드 (현재 페이지)**
            - Streamlit 기반 웹 UI
            - API 클라이언트 역할
            - 사용자 인터페이스 제공
            """
            )

        with col2:
            st.markdown(
                """
            **⚙️ 백엔드 (API 서버)**
            - FastAPI 기반 REST API
            - 하이브리드 검색 RAG 시스템
            - AI 처리 및 데이터 관리
            """
            )

        return

    # 채팅 인터페이스
    st.markdown("## 💬 법률 상담 채팅")

    # 채팅 히스토리 표시
    if st.session_state.chat_history:
        st.markdown("### 📋 대화 기록")
        for chat in st.session_state.chat_history:
            display_chat_message(chat["type"], chat["content"], chat["timestamp"], chat.get("extra_info"))

    # 질문 입력
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
        user_query = st.text_area("법률 관련 질문을 입력하세요:", height=100, placeholder="예: 전세보증금 반환이 안 되는데 어떻게 해야 하나요?")

        submitted = st.form_submit_button("📨 질문하기", type="primary")

        if submitted and user_query.strip():
            asyncio.run(process_query_async(user_query.strip()))
            st.rerun()


if __name__ == "__main__":
    main()
