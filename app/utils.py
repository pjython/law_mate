import os


def get_directory_size(directory: str) -> int:
    """디렉토리 크기 계산"""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size
    except Exception:
        return 0
