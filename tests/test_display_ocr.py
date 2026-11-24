import unittest
import os
import cv2
import numpy as np

from src.core.detector import PopupDetector
from src.core.ocr_engine import OcrEngine
from src.core.resources import get_resource_path

class TestDisplayOcr(unittest.TestCase):
    def setUp(self):
        self.detector = PopupDetector()
        self.ocr = OcrEngine()

    def test_ocr_8543(self):
        path = get_resource_path(os.path.join("assets", "images", "화면캡처.png"))
        if not os.path.exists(path):
            path = "화면캡처.png"
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        detected, score, loc = self.detector.detect_popup(img)
        self.assertTrue(detected)

        crop, _ = self.detector.get_display_crop(img, loc)
        code, conf = self.ocr.recognize(crop)
        self.assertEqual(code, "8543")
        self.assertGreaterEqual(conf, 0.60)

    def test_ocr_2154(self):
        """비밀번호해제못함.png에서 2154 정상 인식 검증 (과거 0250 오인식 버그 해결 확인)"""
        path = get_resource_path(os.path.join("assets", "images", "비밀번호해제못함.png"))
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        detected, score, loc = self.detector.detect_popup(img)
        self.assertTrue(detected, f"Popup not detected: score={score}")

        crop, _ = self.detector.get_display_crop(img, loc)
        code, conf = self.ocr.recognize(crop)
        self.assertEqual(code, "2154", f"Expected 2154, got {code}")
        self.assertGreaterEqual(conf, 0.70)

if __name__ == '__main__':
    unittest.main()
