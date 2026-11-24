import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def test_headless():
    app = QApplication(sys.argv)
    window = MainWindow()
    print("MainWindow successfully instantiated!")
    
    # 샘플 진단 로직 직접 호출 테스트
    print("Running sample diagnosis...")
    window._run_sample_diagnosis()
    print("Sample diagnosis finished without error!")
    
    app.quit()

if __name__ == "__main__":
    test_headless()
