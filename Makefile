# Law Mate 프로젝트 Makefile (리팩토링된 구조)
# 개발 편의성을 위한 명령어 모음

.PHONY: help install dev api client test clean setup

# 기본 명령어 (help)
help:
	@echo "🚀 Law Mate 프로젝트 명령어 (리팩토링된 구조)"
	@echo ""
	@echo "📦 설치 및 설정:"
	@echo "  make setup     - 프로젝트 초기 설정"
	@echo "  make install   - 의존성 설치"
	@echo "  make env       - 환경변수 파일 생성"
	@echo ""
	@echo "🏃 실행:"
	@echo "  make dev       - 개발 서버 실행 (API + Client)"
	@echo "  make api       - API 서버만 실행"
	@echo "  make client    - Streamlit 클라이언트만 실행"
	@echo ""
	@echo "🧪 테스트 및 품질:"
	@echo "  make test      - 테스트 실행"
	@echo "  make lint      - 코드 린팅"
	@echo "  make format    - 코드 포맷팅"
	@echo ""
	@echo "🧹 정리:"
	@echo "  make clean     - 임시 파일 정리"
	@echo "  make reset     - 데이터베이스 초기화"
	@echo ""
	@echo "🌍 환경 설정:"
	@echo "  make dev-env   - 개발 환경으로 설정"
	@echo "  make prod-env  - 운영 환경으로 설정"

# 프로젝트 초기 설정
setup: env install
	@echo "✅ 프로젝트 초기 설정 완료"

# 환경변수 파일 생성
env:
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "📝 .env 파일이 생성되었습니다. OPENAI_API_KEY를 설정해주세요."; \
	else \
		echo "✅ .env 파일이 이미 존재합니다."; \
	fi

# 의존성 설치
install:
	@echo "📦 의존성 설치 중..."
	pip install -r requirements.txt
	@echo "✅ 의존성 설치 완료"

# 개발 환경 설정
dev-env:
	@echo "🔧 개발 환경으로 설정 중..."
	@echo "ENVIRONMENT=development" > .env.local
	@echo "✅ 개발 환경 설정 완료"

# 운영 환경 설정
prod-env:
	@echo "🚀 운영 환경으로 설정 중..."
	@echo "ENVIRONMENT=production" > .env.local
	@echo "✅ 운영 환경 설정 완료"

# 개발 서버 실행 (병렬)
dev: dev-env
	@echo "🚀 개발 서버 시작 중..."
	@echo "   - API 서버: http://localhost:8000"
	@echo "   - Streamlit: http://localhost:8501"
	@echo "   - API 문서: http://localhost:8000/docs"
	@make -j2 api client

# API 서버 실행 (새 구조)
api:
	@echo "🔧 API 서버 시작 중..."
	@if [ -f .env.local ]; then export $(cat .env.local | xargs); fi && \
	python -m app.main

# Streamlit 클라이언트 실행
client:
	@echo "🖥️ Streamlit 클라이언트 시작 중..."
	streamlit run streamlit_client.py --server.port 8501

# 테스트 실행
test:
	@echo "🧪 테스트 실행 중..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v --cov=app --cov=core --cov=api --cov=services; \
	else \
		echo "⚠️ tests 디렉토리가 없습니다."; \
	fi

# 코드 린팅
lint:
	@echo "🔍 코드 린팅 중..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 app/ core/ api/ services/ --max-line-length=120 --exclude=__pycache__; \
	else \
		echo "⚠️ flake8이 설치되지 않았습니다. pip install flake8"; \
	fi

# 코드 포맷팅
format:
	@echo "🎨 코드 포맷팅 중..."
	@if command -v black >/dev/null 2>&1; then \
		black app/ core/ api/ services/ --line-length=120; \
	else \
		echo "⚠️ black이 설치되지 않았습니다. pip install black"; \
	fi

# 임시 파일 정리
clean:
	@echo "🧹 임시 파일 정리 중..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 정리 완료"

# 데이터베이스 초기화
reset:
	@echo "🗑️ 데이터베이스 초기화 중..."
	@if [ -d "vectordb" ]; then \
		rm -rf vectordb; \
		echo "✅ 벡터 데이터베이스 삭제 완료"; \
	fi
	@if [ -d "logs" ]; then \
		rm -rf logs; \
		echo "✅ 로그 파일 삭제 완료"; \
	fi

# 상태 확인
status:
	@echo "📊 프로젝트 상태:"
	@echo "   - Python: $(shell python --version 2>&1)"
	@echo "   - 가상환경: $(shell echo $$VIRTUAL_ENV | sed 's/.*\///' || echo '없음')"
	@echo "   - .env 파일: $(shell [ -f .env ] && echo '✅ 존재' || echo '❌ 없음')"
	@echo "   - 환경 설정: $(shell [ -f .env.local ] && cat .env.local || echo '기본값')"
	@echo "   - vectordb: $(shell [ -d vectordb ] && echo '✅ 존재' || echo '❌ 없음')"
	@echo "   - 구조: 리팩토링된 계층형 아키텍처"

# 프로젝트 구조 확인
tree:
	@echo "🌳 프로젝트 구조:"
	@if command -v tree >/dev/null 2>&1; then \
		tree -I '__pycache__|*.pyc|venv|.git|vectordb|logs|.idea|.vscode' -L 3; \
	else \
		find . -type d -name "__pycache__" -prune -o -type d -name "venv" -prune -o -type d -name ".git" -prune -o -type f -print | head -20; \
	fi

# API 문서 열기
docs:
	@echo "📖 API 문서 열기 중..."
	@echo "브라우저에서 http://localhost:8000/docs 를 열어주세요"
	@if command -v open >/dev/null 2>&1; then \
		open http://localhost:8000/docs; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open http://localhost:8000/docs; \
	fi 