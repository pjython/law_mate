# Law Mate 🏛️

**Google Gemini & OpenAI 기반 지능형 법률 상담 AI 시스템**

Law Mate는 Google Gemini와 OpenAI GPT를 활용한 전문 법률 상담 AI입니다. 하이브리드 검색과 LangChain 기반 맥락 분석을 통해 정확하고 맥락적인 법률 조언을 제공합니다.

## 🚀 주요 기능

### 핵심 기능
- **Google Gemini 2.5 Flash 기반 답변 생성**: 전문적이고 정확한 법률 상담
- **하이브리드 검색**: BM25 + 벡터 검색으로 최적의 문서 검색
- **LangChain Memory 기반 대화 관리**: 대화 맥락을 기억하는 지능적 연속 대화
- **실시간 대화**: 세션 기반 연속 대화 지원
- **법제처 API 연동**: 실시간 법률 문서 수집 및 업데이트

### 법률 분야
- 부동산 (임대차, 전세, 매매)
- 근로/노동 (해고, 임금, 근로계약)
- 민사 (계약, 손해배상, 채무)
- 가족법 (이혼, 상속, 양육)
- 형사법 (고발, 신고, 범죄)

## 📋 시스템 요구사항

- Python 3.11+
- Google Gemini API 키 또는 OpenAI API 키
- 8GB+ RAM 권장

## ⚡ 빠른 시작

### 1. 설치
```bash
git clone https://github.com/your-repo/law_mate.git
cd law_mate
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 설정
```bash
cp env.example .env
# .env 파일에서 API 키 설정 (Gemini 또는 OpenAI)
```

### 3. 실행
```bash
# 개발 서버 (API + Streamlit)
make dev

# 또는 개별 실행
python -m app.main  # API 서버
streamlit run streamlit_client.py  # 웹 UI
```

### 4. 접속
- **웹 UI**: http://localhost:8501
- **API 문서**: http://localhost:8000/docs

## 🏗️ 아키텍처

```
사용자 질문 → LangChain Memory → 하이브리드 검색 → Gemini 답변 생성 → Memory 업데이트
     ↓              ↓                ↓              ↓                ↓
   의도 분석    맥락 이해 & 보강    문서 검색     전문 답변         대화 기록
```

### 주요 컴포넌트
- **RAG Orchestrator**: 전체 시스템 조율
- **LangChain RAG Service**: Gemini 기반 질문 분류 및 답변 생성
- **Hybrid Search**: BM25 + 벡터 검색 결합
- **Vector Store**: ChromaDB 기반 벡터 데이터베이스
- **Law API Collector**: 법제처 API를 통한 법률 문서 수집
- **Memory Management**: LangChain ConversationBufferWindowMemory

## 🔧 설정

### 환경 변수 (.env)
```bash
# AI 모델 설정 (둘 중 하나 또는 둘 다)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
TEMPERATURE=0.5

# 서버 설정
APP_NAME=Law Mate API
APP_VERSION=1.0.0
LOG_LEVEL=INFO
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501

# 벡터 DB 설정
VECTOR_DB_PATH=./vectordb
COLLECTION_NAME=law_documents
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask

# 검색 설정
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_DOCUMENTS=5
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7
SIMILARITY_THRESHOLD=0.7

# 법제처 API 설정
LAW_API_USER_ID=your_law_api_user_id

# 스케줄러 설정
ENABLE_SCHEDULER=true

# 로깅 설정
LOG_FILE=logs/law_mate_api.log
```

## 🛠️ 개발 명령어

```bash
# 개발 환경 설정
make setup

# 개발 서버 실행
make dev

# API 서버만 실행
make api

# 웹 클라이언트만 실행
make client

# 코드 포맷팅
make format

# 린팅
make lint

# 정리
make clean
```

## 📊 API 엔드포인트

### 질의응답
- `POST /api/v1/query` - 법률 질문 처리

### 헬스체크
- `GET /api/v1/health` - 헬스체크

### 관리 기능
- `GET /api/v1/admin/status` - 시스템 상태 조회
- `POST /api/v1/admin/rebuild-indexes` - 검색 인덱스 재구축
- `GET /api/v1/admin/config` - 설정 정보 조회 (디버그용)

## 🎯 사용 예시

### Python API 클라이언트
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/query",
        json={
            "query": "전세 계약 시 주의사항이 뭔가요?",
            "session_id": "user123"
        }
    )
    result = response.json()
    print(result["answer"])
```

### Curl
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "부당해고 시 대응 방법은?", "session_id": "user123"}'
```

## 🔍 특징

### LangChain 기반 메모리 시스템
- ConversationBufferWindowMemory로 최근 10개 메시지 기억
- 세션별 독립적 대화 맥락 관리
- 후속 질문 자동 감지 및 처리
- 주제 변경 인식 및 대응

### 하이브리드 검색
- BM25 키워드 검색 (30% 가중치)
- 벡터 의미 검색 (70% 가중치)
- 한국어 최적화 임베딩 모델 (jhgan/ko-sroberta-multitask)
- 검색 결과 융합 및 관련도 기반 랭킹

### 법제처 API 연동
- 실시간 법률 문서 수집
- 키워드 기반 법령 검색
- 자동 문서 파싱 및 인덱싱
- API 상태 모니터링

### 견고한 시스템
- AI API 실패 시 폴백 메커니즘
- 환경별 설정 관리 (.env.dev, .env.prod, .env.test)
- 세션 기반 대화 관리
- 실시간 시스템 모니터링
- 자동 인덱스 재구축 스케줄링

## 🤖 AI 모델 지원

### Google Gemini (기본)
- **모델**: gemini-2.5-flash
- **장점**: 빠른 응답, 한국어 지원 우수, 비용 효율적
- **용도**: 일반적인 법률 상담

### OpenAI GPT (선택)
- **모델**: gpt-4o
- **장점**: 높은 정확도, 복잡한 추론
- **용도**: 고도의 법률 분석 필요 시

## 📁 프로젝트 구조

```
law_mate/
├── api/                    # FastAPI 라우터 및 스키마
│   ├── schemas/           # 요청/응답 모델
│   └── v1/endpoints/      # API 엔드포인트
├── app/                   # 애플리케이션 진입점
├── core/                  # 핵심 설정 및 로깅
├── services/              # 비즈니스 로직
│   ├── llm/              # AI 모델 서비스
│   ├── rag/              # RAG 오케스트레이터
│   ├── search/           # 하이브리드 검색
│   ├── document/         # 문서 처리
│   └── collector/        # 법제처 API 수집
├── infrastructure/        # 인프라 계층
│   └── database/         # 벡터 데이터베이스
├── data/                 # 샘플 법률 문서
└── streamlit_client.py   # 웹 UI
```

## 🚦 상태 모니터링

시스템 상태는 다음 명령으로 확인할 수 있습니다:

```bash
curl http://localhost:8000/api/v1/admin/status
```

응답 예시:
```json
{
  "status": "healthy",
  "rag_initialized": true,
  "document_count": 150,
  "search_method": "하이브리드 검색",
  "conversation_stats": {
    "total_sessions": 10,
    "active_sessions": 5
  }
}
```

## 🔄 환경별 설정

### 개발 환경 (.env.dev)
- DEBUG=true
- LOG_LEVEL=DEBUG
- ENABLE_SCHEDULER=false

### 프로덕션 환경 (.env.prod)
- DEBUG=false
- LOG_LEVEL=WARNING
- ENABLE_SCHEDULER=true

### 테스트 환경 (.env.test)
- VECTOR_DB_PATH=./vectordb_test
- LOG_LEVEL=DEBUG

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!

---

**Law Mate** - 당신의 믿을 수 있는 AI 법률 상담사 🏛️⚖️ 