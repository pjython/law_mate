# Law Mate Makefile

.PHONY: help setup dev api client clean format lint

# 기본 타겟
help:
	@echo "Law Mate 개발 명령어:"
	@echo ""
	@echo "  setup     - 초기 환경 설정"
	@echo "  dev       - 개발 서버 실행 (API + Streamlit)"
	@echo "  api       - API 서버만 실행"
	@echo "  client    - Streamlit 클라이언트만 실행"
	@echo "  format    - 코드 포맷팅"
	@echo "  lint      - 코드 린팅"
	@echo "  clean     - 캐시 및 임시 파일 정리"

# 초기 환경 설정
setup:
	@echo "🚀 Law Mate 초기 설정 중..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "✅ .env 파일 생성 완료"; \
		echo "⚠️ .env 파일에서 OpenAI API 키를 설정하세요"; \
	else \
		echo "✅ .env 파일이 이미 존재합니다"; \
	fi
	@mkdir -p logs vectordb data
	@echo "✅ 디렉토리 생성 완료"

# 개발 서버 실행 (병렬)
dev:
	@echo "🚀 개발 서버 시작 중..."
	@echo "   - API 서버: http://localhost:8000"
	@echo "   - Streamlit: http://localhost:8501"
	@echo "   - API 문서: http://localhost:8000/docs"
	@make -j2 api client

# API 서버 실행
api:
	@echo "🔧 API 서버 시작 중..."
	python -m app.main

# Streamlit 클라이언트 실행
client:
	@echo "🖥️ Streamlit 클라이언트 시작 중..."
	streamlit run streamlit_client.py --server.port 8501

# 코드 포맷팅
format:
	@echo "🎨 코드 포맷팅 중..."
	@if command -v black >/dev/null 2>&1; then \
		black app/ core/ api/ services/ --line-length=120; \
	else \
		echo "⚠️ black이 설치되지 않았습니다. pip install black"; \
	fi

# 코드 린팅
lint:
	@echo "🔍 코드 린팅 중..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 app/ core/ api/ services/ --max-line-length=120 --exclude=__pycache__; \
	else \
		echo "⚠️ flake8이 설치되지 않았습니다. pip install flake8"; \
	fi

# 정리
clean:
	@echo "🧹 정리 중..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.log" -delete 2>/dev/null || true
	@echo "✅ 정리 완료" 