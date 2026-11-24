import os
import unittest
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from src.core import controller
from src.core.detector import PopupDetector
from src.gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication([])


def load_image(path: str) -> np.ndarray:
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


class TestTowerPlacement(unittest.TestCase):
    def setUp(self):
        self.detector = PopupDetector()
        settings = QSettings("UnderDarkMacro", "UnderdarkMacroSolver")
        self._backup = {k: settings.value(k) for k in settings.allKeys()}
        settings.clear()

    def tearDown(self):
        settings = QSettings("UnderDarkMacro", "UnderdarkMacroSolver")
        settings.clear()
        for k, v in self._backup.items():
            settings.setValue(k, v)

    def test_controller_has_cv2_imported(self):
        """MacroWorker 오버레이 렌더링 시 NameError가 발생하지 않도록 cv2 모듈이 임포트되어 있는지 검증"""
        self.assertTrue(hasattr(controller, "cv2"))

    def test_detect_available_towers_ordered_left_to_right(self):
        """심연_게임화면 1, 2, 3에서 하단 타워 목록이 앞쪽(좌측 -> 우측) 순서로 정확히 인식되는지 검증"""
        # 1. 심연_게임화면.png: 저격수 -> 펭귄 -> 햄스터 -> 까마귀
        img1 = load_image(os.path.join("assets", "images", "심연_게임화면.png"))
        towers1 = self.detector.detect_available_towers(img1)
        keys1 = [t["key"] for t in towers1]
        self.assertEqual(keys1, ["sniper", "penguin", "hamster", "crow"])
        # x 좌표가 오름차순인지 확인
        xs1 = [t["slot_coords"][0] for t in towers1]
        self.assertEqual(xs1, sorted(xs1))

        # 2. 심연_게임화면2.png: 저격수 -> 햄스터
        img2 = load_image(os.path.join("assets", "images", "심연_게임화면2.png"))
        towers2 = self.detector.detect_available_towers(img2)
        keys2 = [t["key"] for t in towers2]
        self.assertEqual(keys2, ["sniper", "hamster"])

        # 3. 심연_게임화면3.png: 저격수 -> 로켓 -> 햄스터(2) -> 까마귀(2)
        img3 = load_image(os.path.join("assets", "images", "심연_게임화면3.png"))
        towers3 = self.detector.detect_available_towers(img3)
        keys3 = [t["key"] for t in towers3]
        self.assertEqual(keys3, ["sniper", "rocket", "hamster", "crow"])

    def test_plan_next_tower_placement_avoids_obstacles_and_ui(self):
        """장애물(2x2 돌덩이) 및 하단 타워 목록(y > 804)을 침범하지 않고 외곽 빈자리를 찾는지 검증"""
        for fname in ["심연_게임화면.png", "심연_게임화면2.png", "심연_게임화면3.png", "가장자리설치샘플.png"]:
            img = load_image(os.path.join("assets", "images", fname))
            plan = self.detector.plan_next_tower_placement(img)
            self.assertIsNotNone(plan, f"Failed to find placement on {fname}")

            # 1순위 선택 타워는 목록 맨 앞(저격수타워)이어야 함
            self.assertEqual(plan["tower"]["key"], "sniper")

            x1, y1, x2, y2 = plan["drop_rect"]
            # 하단 맨 아래열 제한(y <= 804) 준수 확인
            self.assertLessEqual(y2, 804, f"Placement {plan['drop_rect']} exceeds bottom limit on {fname}")
            self.assertGreaterEqual(y1, 58)
            self.assertGreaterEqual(x1, 62)
            self.assertLessEqual(x2, 934)

            # 감지된 모든 2x2 장애물과 겹치지 않는지 확인
            for ox1, oy1, ox2, oy2 in plan["obstacles"]:
                overlap = not (x2 <= ox1 + 4 or x1 >= ox2 - 4 or y2 <= oy1 + 4 or y1 >= oy2 - 4)
                self.assertFalse(overlap, f"Tower rect {(x1,y1,x2,y2)} overlaps obstacle {(ox1,oy1,ox2,oy2)} on {fname}")

    def test_auto_tower_checkbox_persistence(self):
        """심연 자동 타워 설치 체크박스가 QSettings를 통해 영구 보존되는지 검증"""
        win1 = MainWindow()
        self.assertTrue(win1.auto_tower_chk.isChecked())
        win1.auto_tower_chk.setChecked(False)
        win1.close()

        win2 = MainWindow()
        self.assertFalse(win2.auto_tower_chk.isChecked())
        win2.auto_tower_chk.setChecked(True)
        win2.close()

    def test_reset_tower_state(self):
        """라운드 전환 시 타워 설치 완료(탐지 중단) 플래그, 기록 및 최대 15개 설정이 정상 동작하는지 검증"""
        worker = controller.MacroWorker(None, self.detector, None)
        self.assertEqual(worker.max_tower_placements, 15)
        worker.placed_tower_spots.append((200, 200))
        worker.tower_placement_done = True
        worker.tower_no_plan_streak = 3

        worker._reset_tower_state()
        self.assertEqual(worker.placed_tower_spots, [])
        self.assertFalse(worker.tower_placement_done)
        self.assertEqual(worker.tower_no_plan_streak, 0)


if __name__ == "__main__":
    unittest.main()

