import os
import sys

def get_resource_path(relative_path: str = "") -> str:
    """
    일반 실행(개발 모드) 및 PyInstaller 패키징 환경(sys._MEIPASS)을 모두 지원하는 경로 반환 함수.
    
    :param relative_path: 프로젝트 루트 기준 상대 경로 (예: "assets/templates/digit_0.png")
    :return: 환경에 따른 절대 경로
    """
    if hasattr(sys, '_MEIPASS'):
        base_path = getattr(sys, '_MEIPASS')
    else:
        # 프로젝트 루트 디렉토리 (src의 상위 디렉토리)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if relative_path:
        return os.path.normpath(os.path.join(base_path, relative_path))
    return base_path
