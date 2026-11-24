import sys
import os

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.core.resources import get_resource_path
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Underdark Macro Solver")
    
    icon_path = get_resource_path("assets/icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
