"""
관리자 기능 엔드포인트
시스템 관리 및 유지보수 관련 API를 제공합니다.
"""

import os
from fastapi import APIRouter, Depends, BackgroundTasks

from core.config import get_settings
from core.logging.config import get_logger
from core.dependencies import get_rag_orchestrator
from api.schemas.requests import RebuildRequest
from api.schemas.responses import RebuildResponse, ConfigResponse
from services.rag.orchestrator import RAGOrchestrator
from app.utils import get_directory_size
from app.tasks import rebuild_task, create_backup


router = APIRouter()
logger = get_logger(__name__)


@router.post("/rebuild-indexes", response_model=RebuildResponse)
async def rebuild_indexes(
    request: RebuildRequest,
    background_tasks: BackgroundTasks,
    rag_orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
):
    """
    인덱스 재구축
    벡터 DB와 검색 인덱스를 재구축합니다.
    """
    logger.info(f"🔄 인덱스 재구축 요청 (backup: {request.backup})")

    try:
        # 백그라운드 작업으로 인덱스 재구축 실행
        background_tasks.add_task(rebuild_task, rag_orchestrator, request.backup)

        logger.info("📝 인덱스 재구축 백그라운드 작업 시작")

        return RebuildResponse(
            message="인덱스 재구축 작업이 백그라운드에서 시작되었습니다.", status="started", task_id=f"rebuild_{int(os.urandom(4).hex(), 16)}"
        )

    except Exception as e:
        logger.error(f"❌ 인덱스 재구축 요청 실패: {str(e)}")
        return RebuildResponse(message=f"인덱스 재구축 요청 실패: {str(e)}", status="failed")


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    설정 정보 조회 (디버그용)
    현재 시스템 설정을 반환합니다.
    """
    logger.debug("⚙️ 설정 정보 조회 요청")

    settings = get_settings()

    return ConfigResponse(
        debug_mode=getattr(settings, "DEBUG", False),
        environment=os.getenv("ENVIRONMENT", "development"),
        app_version=settings.APP_VERSION,
        chunk_size=settings.CHUNK_SIZE,
        top_k=settings.TOP_K_DOCUMENTS,
        vector_db_path=settings.VECTOR_DB_PATH,
        search_weights={"bm25": settings.BM25_WEIGHT, "vector": settings.VECTOR_WEIGHT},
    )


@router.get("/backups")
async def list_backups():
    """백업 목록 조회"""
    try:
        logger.debug("📋 백업 목록 조회")

        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            return {"success": True, "backups": [], "total_backups": 0, "message": "백업 디렉토리가 없습니다"}

        backups = []
        for backup_name in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, backup_name)
            if os.path.isdir(backup_path):
                # 백업 메타데이터 읽기
                metadata_path = os.path.join(backup_path, "backup_metadata.json")
                metadata = {}

                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            import json

                            metadata = json.load(f)
                    except Exception:
                        pass

                # 백업 정보 수집
                backup_info = {
                    "name": backup_name,
                    "path": backup_path,
                    "created_at": metadata.get("created_at", "알 수 없음"),
                    "size_bytes": metadata.get("backup_size", get_directory_size(backup_path)),
                    "files_count": len(metadata.get("files_backed_up", [])),
                    "files": metadata.get("files_backed_up", []),
                }

                backups.append(backup_info)

        # 생성 시간 순으로 정렬 (최신 순)
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return {"success": True, "backups": backups, "total_backups": len(backups), "backup_directory": backup_dir}

    except Exception as e:
        logger.error(f"❌ 백업 목록 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/backup")
async def create_manual_backup():
    """수동 백업 생성"""
    try:
        logger.info("📦 수동 백업 생성 요청")

        success = await create_backup()

        if success:
            return {"success": True, "message": "백업이 성공적으로 생성되었습니다"}
        else:
            return {"success": False, "message": "백업 생성에 실패했습니다"}

    except Exception as e:
        logger.error(f"❌ 수동 백업 생성 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@router.delete("/backups/{backup_name}")
async def delete_backup(backup_name: str):
    """백업 삭제"""
    try:
        logger.info(f"🗑️ 백업 삭제 요청: {backup_name}")

        backup_path = os.path.join("backups", backup_name)

        if not os.path.exists(backup_path):
            return {"success": False, "message": "백업을 찾을 수 없습니다"}

        if not os.path.isdir(backup_path):
            return {"success": False, "message": "유효하지 않은 백업 디렉토리입니다"}

        # 백업 디렉토리 삭제
        import shutil

        shutil.rmtree(backup_path)

        logger.info(f"✅ 백업 삭제 완료: {backup_name}")

        return {"success": True, "message": f"백업 '{backup_name}'이 삭제되었습니다"}

    except Exception as e:
        logger.error(f"❌ 백업 삭제 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/restore/{backup_name}")
async def restore_backup(backup_name: str):
    """백업 복원"""
    try:
        logger.info(f"🔄 백업 복원 요청: {backup_name}")

        backup_path = os.path.join("backups", backup_name)

        if not os.path.exists(backup_path):
            return {"success": False, "message": "백업을 찾을 수 없습니다"}

        settings = get_settings()

        # 현재 벡터 DB 백업 (복원 실패시 롤백용)
        current_backup_success = await create_backup()
        if not current_backup_success:
            logger.warning("⚠️ 현재 상태 백업 실패, 복원을 계속 진행합니다")

        # 벡터 DB 복원
        backup_vector_path = os.path.join(backup_path, "vector_db")
        if os.path.exists(backup_vector_path):
            import shutil

            # 기존 벡터 DB 삭제
            if os.path.exists(settings.VECTOR_DB_PATH):
                shutil.rmtree(settings.VECTOR_DB_PATH)

            # 백업에서 복원
            shutil.copytree(backup_vector_path, settings.VECTOR_DB_PATH)
            logger.info(f"✅ 벡터 DB 복원 완료: {settings.VECTOR_DB_PATH}")

        logger.info(f"✅ 백업 복원 완료: {backup_name}")

        return {"success": True, "message": f"백업 '{backup_name}'에서 성공적으로 복원되었습니다", "restored_from": backup_name}

    except Exception as e:
        logger.error(f"❌ 백업 복원 오류: {str(e)}")
        return {"success": False, "error": str(e)}
