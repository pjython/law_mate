"""
백그라운드 작업 함수들
"""
import os
from services.rag.orchestrator import RAGOrchestrator
from core.logging.config import get_logger
from core.config import get_settings
from app.utils import get_directory_size


logger = get_logger(__name__)


async def rebuild_task(rag_orchestrator: RAGOrchestrator, backup: bool) -> None:
    """백그라운드 인덱스 재구축 작업"""
    try:
        logger.info("🔄 백그라운드 인덱스 재구축 시작...")

        # 백업 수행 (필요시)
        if backup:
            logger.info("💾 기존 인덱스 백업 중...")
            backup_success = await create_backup()
            if not backup_success:
                logger.warning("⚠️ 백업 실패했지만 재구축을 계속 진행합니다")

        # 인덱스 재구축
        success = await rag_orchestrator.rebuild_indexes()

        if success:
            logger.info("✅ 백그라운드 인덱스 재구축 완료")
        else:
            logger.error("❌ 백그라운드 인덱스 재구축 실패")

    except Exception as e:
        logger.error(f"❌ 백그라운드 인덱스 재구축 오류: {str(e)}")


async def create_backup() -> bool:
    """벡터 DB 및 인덱스 백업"""
    try:
        import shutil
        from datetime import datetime

        settings = get_settings()

        # 백업 디렉토리 생성
        backup_dir = os.path.join("backups", datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(backup_dir, exist_ok=True)

        logger.info(f"📦 백업 생성 중: {backup_dir}")

        # 벡터 DB 백업
        vector_db_path = settings.VECTOR_DB_PATH
        if os.path.exists(vector_db_path):
            backup_vector_path = os.path.join(backup_dir, "vector_db")
            shutil.copytree(vector_db_path, backup_vector_path)
            logger.debug(f"✅ 벡터 DB 백업 완료: {backup_vector_path}")

        # 로그 파일 백업 (선택사항)
        log_file = settings.LOG_FILE
        if log_file and os.path.exists(log_file):
            backup_log_path = os.path.join(backup_dir, os.path.basename(log_file))
            shutil.copy2(log_file, backup_log_path)
            logger.debug(f"✅ 로그 파일 백업 완료: {backup_log_path}")

        # 설정 파일 백업
        config_files = [".env", ".env.dev", ".env.prod"]
        for config_file in config_files:
            if os.path.exists(config_file):
                backup_config_path = os.path.join(backup_dir, config_file)
                shutil.copy2(config_file, backup_config_path)
                logger.debug(f"✅ 설정 파일 백업 완료: {backup_config_path}")

        # 백업 메타데이터 생성
        backup_metadata = {
            "created_at": datetime.now().isoformat(),
            "vector_db_path": vector_db_path,
            "backup_size": get_directory_size(backup_dir),
            "files_backed_up": os.listdir(backup_dir),
        }

        metadata_path = os.path.join(backup_dir, "backup_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            import json

            json.dump(backup_metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 백업 생성 완료: {backup_dir}")
        return True

    except Exception as e:
        logger.error(f"❌ 백업 생성 실패: {str(e)}")
        return False
