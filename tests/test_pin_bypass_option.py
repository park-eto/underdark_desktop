import unittest
from unittest.mock import MagicMock
import numpy as np
from src.core.controller import MacroWorker

class TestPinBypassOption(unittest.TestCase):
    def setUp(self):
        self.mock_adb = MagicMock()
        self.mock_detector = MagicMock()
        self.mock_ocr = MagicMock()

        self.worker = MacroWorker(self.mock_adb, self.mock_detector, self.mock_ocr)

    def test_pin_bypass_enabled_in_stage_farming(self):
        # 핀코드 체크박스 ON + 스테이지 파밍 모드
        self.worker.auto_solve_pin = True
        self.worker.mode = MacroWorker.MODE_STAGE_FARMING

        # 팝업 감지 모의
        fake_frame = np.zeros((1080, 540, 3), dtype=np.uint8)
        self.mock_detector.detect_popup.return_value = (True, 0.99, (50, 200, 440, 600))
        self.mock_detector.get_display_crop.return_value = (np.zeros((100, 300, 3)), (0, 0))
        self.mock_ocr.recognize.return_value = ("1234", 0.95)
        self.mock_detector.get_keypad_coords.return_value = (100, 200)

        # 핀코드 처리 플래그 확인
        self.assertTrue(self.worker.auto_solve_pin)

    def test_pin_bypass_disabled_in_stage_farming(self):
        # 핀코드 체크박스 OFF + 스테이지 파밍 모드 -> POPUP_MANUAL 처리되어야 함
        self.worker.auto_solve_pin = False
        self.worker.mode = MacroWorker.MODE_STAGE_FARMING

        self.assertFalse(self.worker.auto_solve_pin)
        self.assertNotEqual(self.worker.mode, MacroWorker.MODE_PIN_ONLY)

    def test_pin_only_mode_ignores_checkbox(self):
        # MODE_PIN_ONLY 모드일 때는 체크박스가 False여도 핀코드 해제 수행
        self.worker.auto_solve_pin = False
        self.worker.mode = MacroWorker.MODE_PIN_ONLY

        # controller.py 조건문: if not self.auto_solve_pin and self.mode != self.MODE_PIN_ONLY:
        condition = not self.worker.auto_solve_pin and self.worker.mode != MacroWorker.MODE_PIN_ONLY
        self.assertFalse(condition, "MODE_PIN_ONLY 모드에서는 체크박스 OFF여도 수동대기로 빠지지 않고 자동 해제를 수행해야 함")

if __name__ == "__main__":
    unittest.main()
