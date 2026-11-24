import unittest
import sys
import re
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestLogTimestamp(unittest.TestCase):
    def test_log_includes_timestamp(self):
        window = MainWindow()
        test_msg = "[테스트 로그] 메시지 전송 확인"
        window._log(test_msg)
        
        log_text = window.log_view.toPlainText()
        self.assertIn(test_msg, log_text)
        
        # [HH:MM:SS] 패턴 확인 (정규표현식: \[\d{2}:\d{2}:\d{2}\])
        match = re.search(r"\[\d{2}:\d{2}:\d{2}\] " + re.escape(test_msg), log_text)
        self.assertIsNotNone(match, f"로그에 시간 형식이 포함되지 않았습니다: {log_text}")

if __name__ == '__main__':
    unittest.main()

