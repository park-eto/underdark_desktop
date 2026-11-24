import sys
import os
import cv2
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.detector import PopupDetector

def test_popup():
    detector = PopupDetector()

    def get_path(fn):
        p = os.path.join(project_root, "assets", "images", fn)
        if os.path.exists(p): return p
        return os.path.join(project_root, fn)

    # 1. 방지창 있는 이미지
    img_macro = cv2.imdecode(np.fromfile(get_path("화면캡처.png"), dtype=np.uint8), cv2.IMREAD_COLOR)
    pure_macro = img_macro[32:992, 0:540]
    detected_m, score_m, _ = detector.detect_popup(pure_macro)
    print(f"Macro Image Detected: {detected_m} (Score: {score_m:.4f})")
    assert detected_m is True, "Macro popup should be detected"

    # 2. 정상 화면 이미지
    img_normal = cv2.imdecode(np.fromfile(get_path("화면캡처 성공.png"), dtype=np.uint8), cv2.IMREAD_COLOR)
    pure_normal = img_normal[32:992, 0:540]
    detected_n, score_n, _ = detector.detect_popup(pure_normal)
    print(f"Normal Image Detected: {detected_n} (Score: {score_n:.4f})")
    assert detected_n is False, "Normal screen should not be detected as popup"

    print("Popup Detector Test PASSED!")

if __name__ == "__main__":
    test_popup()
