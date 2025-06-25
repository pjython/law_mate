# ⚖️ Law Mate - AI 법률 상담 시스템

LLM과 하이브리드 검색 기반의 개인 법률 상담 AI 시스템입니다. 사용자의 자연어 질문에 대해 관련 법률 문서를 검색하고, RAG(Retrieval-Augmented Generation) 구조를 통해 신뢰할 수 있는 법률 자문 응답을 제공합니다.

## 🎯 주요 기능

- 📝 **자연어 질문 처리**: 일반적인 언어로 법률 질문 가능
- 🔍 **하이브리드 검색**: BM25 키워드 + 벡터 의미 검색 결합
- 🤖 **AI 법률 상담**: GPT-4o 기반 구조화된 법률 자문 제공
- 🛡️ **질문 필터링**: 법률 외 질문은 정중하게 안내
- 📊 **신뢰도 지표**: 응답의 신뢰도 및 참조 문서 표시
- 💬 **분리형 아키텍처**: FastAPI 백엔드 + Streamlit 프론트엔드

## 🏗️ 시스템 아키텍처

### **계층형 구조**
```
📁 law_mate/
├── 📱 app/                           # 애플리케이션 코어
│   ├── main.py                       # FastAPI 진입점
│   └── dependencies.py               # 의존성 주입
│
├── 🌐 api/                           # API 레이어
│   ├── v1/endpoints/                 # 엔드포인트
│   │   ├── health.py                 # 헬스체크
│   │   ├── query.py                  # 질문 처리
│   │   └── admin.py                  # 관리 기능
│   └── schemas/                      # 요청/응답 스키마
│
├── ⚙️ core/                          # 핵심 설정
│   ├── config/                       # 환경별 설정
│   └── logging/                      # 로깅 시스템
│
├── 🔧 services/                      # 비즈니스 로직
│   ├── rag/orchestrator.py          # RAG 오케스트레이터
│   ├── search/hybrid_search.py      # 하이브리드 검색
│   ├── llm/openai_client.py         # OpenAI 서비스
│   └── document/processor.py        # 문서 처리
│
├── 🗄️ infrastructure/               # 인프라 레이어
│   └── database/vector_store.py     # 벡터 스토어
│
├── 📄 data/sample_laws/             # 법률 문서
└── 📱 streamlit_client.py           # 프론트엔드
```

### **분리된 서비스 구조**
```
📱 프론트엔드 (Streamlit)  ←→  ⚙️ 백엔드 (FastAPI)
    - 사용자 인터페이스           - AI 처리 엔진
    - API 클라이언트             - 하이브리드 검색
    - 세션 관리                  - 데이터 파이프라인
```

## 🛠️ 기술 스택

- **언어**: Python 3.10+
- **백엔드**: FastAPI, Uvicorn
- **프론트엔드**: Streamlit
- **LLM**: OpenAI GPT-4o
- **검색**: BM25 + Sentence Transformers
- **벡터DB**: ChromaDB
- **형태소 분석**: Kiwi (한국어 특화)
- **설정 관리**: Pydantic Settings
- **로깅**: 중앙화된 로깅 시스템

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository>
cd law_mate

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성 (env.example 참고)
cp env.example .env

# OpenAI API 키 설정
echo "OPENAI_API_KEY=your_api_key_here" >> .env
```

### 3. 서버 실행

#### 개발 환경 (권장)
```bash
# Makefile 사용 - 백엔드와 프론트엔드 동시 실행
make dev

# 또는 개별 실행
make api      # 백엔드만 실행 (포트 8000)
make client   # 프론트엔드만 실행 (포트 8501)
```

#### 수동 실행
```bash
# 백엔드 서버 (필수)
python -m app.main

# 프론트엔드 클라이언트 (별도 터미널)
streamlit run streamlit_client.py
```

### 4. 접속
- **프론트엔드**: http://localhost:8501
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

## 📋 사용 가이드

### 1. 시스템 초기화
1. 웹 브라우저에서 프론트엔드 접속
2. 사이드바에서 "🚀 시스템 초기화" 클릭
3. "📄 샘플 문서 추가"로 법률 문서 로드

### 2. 법률 상담 사용
- **예시 질문**: 미리 준비된 버튼 클릭
- **직접 질문**: 텍스트 영역에 질문 입력 후 전송

### 3. 지원 법률 분야
- 🏠 **주택임대차**: 전세, 월세, 보증금 등
- 💼 **근로관계**: 부당해고, 임금, 퇴직 등
- ⚖️ **민사분쟁**: 손해배상, 계약 위반 등

## 🔗 API 엔드포인트

### 기본 엔드포인트
```bash
GET  /health        # 서버 상태 확인
GET  /status        # 시스템 상태 조회
POST /query         # 법률 질문 처리
POST /rebuild       # 인덱스 재구축
```

### API 사용 예시
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "전세보증금을 돌려받지 못하고 있어요",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

## 💡 응답 구조

```
📋 요약
- 질문의 핵심 내용 요약

📖 상세 답변
- 법률적 근거와 상세 설명

⚖️ 관련 법령
- 해당 법률 조항

💡 권장사항
- 구체적 행동 지침

⚠️ 주의사항
- 고려사항

📊 메타 정보
- 신뢰도, 참조 문서, 처리 시간
```

## 🔧 개발 도구

### Makefile 명령어
```bash
make setup      # 초기 환경 설정
make dev        # 개발 서버 실행 (병렬)
make api        # 백엔드만 실행
make client     # 프론트엔드만 실행
make tree       # 프로젝트 구조 확인
make clean      # 캐시 정리
```

### 로그 확인
```bash
# API 서버 로그
tail -f logs/law_mate_api.log

# 실시간 로그 모니터링
make logs
```

## ⚠️ 주의사항

1. **법률 자문 한계**: 일반적인 법률 정보 제공 목적이며, 개별 사안 법률 자문을 대체하지 않습니다.
2. **전문가 상담 권고**: 복잡한 법률 문제는 반드시 전문 변호사와 상담하세요.
3. **정보 정확성**: AI 생성 정보이므로 최신 법령 변경사항이 반영되지 않을 수 있습니다.

## 🔍 문제 해결

### 서버 연결 실패
```bash
# 서버 상태 확인
make status

# 서버 재시작
make restart
```

### 벡터DB 오류
```bash
# 데이터베이스 초기화
rm -rf vectordb/
# 프론트엔드에서 "시스템 초기화" 재실행
```

## 📈 확장 가능성

- **문서 확장**: 더 많은 법률 문서 추가
- **다국어 지원**: 영어, 중국어 등 지원
- **전문 분야**: 특허법, 세법 등 특화
- **API 확장**: 외부 서비스 연동
- **음성 인터페이스**: STT/TTS 기능

## 📄 라이선스

MIT 라이선스 하에 배포됩니다.

---

**⚖️ Law Mate**: 모든 사람이 쉽게 접근할 수 있는 AI 법률 상담 서비스 