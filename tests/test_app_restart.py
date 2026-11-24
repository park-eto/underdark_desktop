import unittest
import os
import cv2
import numpy as np
from src.core.detector import PopupDetector
from src.core.controller import MacroWorker
from src.core.resources import get_resource_path

class TestAppRestart(unittest.TestCase):
    def setUp(self):
        self.detector = PopupDetector()

    def test_detect_app_icon_success(self):
        """언더다크튕김.png에서 UnderDark 앱 아이콘이 정확히 감지되는지 검증"""
        path = get_resource_path(os.path.join("assets", "images", "언더다크튕김.png"))
        if not os.path.exists(path):
            path = os.path.join("assets", "images", "언더다크튕김.png")
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        frame = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        matched, score, coords = self.detector.detect_app_icon(frame)

        self.assertTrue(matched, f"Failed to detect UnderDark icon (score: {score})")
        self.assertGreaterEqual(score, 0.70)
        # 아이콘 중심 좌표 확인 (대략 x=590~600, y=210~220 근처)
        cx, cy = coords
        self.assertTrue(550 <= cx <= 650, f"Unexpected cx: {cx}")
        self.assertTrue(180 <= cy <= 250, f"Unexpected cy: {cy}")

    def test_analyze_screen_state_app_crashed(self):
        """analyze_screen_state 호출 시 APP_CRASHED 상태가 정상 반환되는지 검증"""
        path = os.path.join("assets", "images", "언더다크튕김.png")
        frame = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

        # 1) 일반 던전 모드 (full_auto)
        state_auto, score_auto, coords_auto = self.detector.analyze_screen_state(frame, mode="full_auto")
        self.assertEqual(state_auto, "APP_CRASHED")
        self.assertGreaterEqual(score_auto, 0.70)
        self.assertIsNotNone(coords_auto)

        # 2) 810 스테이지 모드 (stage_farming)
        state_stage, score_stage, coords_stage = self.detector.analyze_screen_state(frame, mode="stage_farming")
        self.assertEqual(state_stage, "APP_CRASHED")
        self.assertGreaterEqual(score_stage, 0.70)
        self.assertIsNotNone(coords_stage)

    def test_no_false_positives_on_normal_screens(self):
        """다른 게임 화면에서 UnderDark 아이콘이 오탐되지 않는지 검증"""
        test_images = [
            "캠프화면.png",
            "게임진행화면.png",
            "던전선택화면.png",
            "게임오버화면.png",
            "획득보상화면.png"
        ]
        for img_name in test_images:
            path = os.path.join("assets", "images", img_name)
            if not os.path.exists(path):
                continue
            frame = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            matched, score, _ = self.detector.detect_app_icon(frame)
            self.assertFalse(matched, f"False positive on {img_name}: score={score}")

    def test_draw_overlay_crashed(self):
        """APP_CRASHED 상태에 대한 디버그 오버레이가 정상 생성되는지 검증"""
        path = os.path.join("assets", "images", "언더다크튕김.png")
        frame = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        overlay = self.detector.draw_debug_overlay(frame, False, 0.95, state="APP_CRASHED", target_coords=(596, 215))
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay.shape, frame.shape)

    def test_adb_crash_detection_and_launch_for_bluestacks(self):
        """BlueStacks Air 등 런처 종류와 무관하게 ADB 기반 앱 튕김 감지 및 직접 재실행 검증"""
        from unittest.mock import MagicMock
        from src.core.adb_client import AdbClient

        adb = AdbClient()
        adb.is_connected = True
        adb.device = MagicMock()
        adb.device.shell.side_effect = lambda cmd: (
            "package:com.FreeDust.UnderDark\n" if "pm list packages" in cmd
            else "Events injected: 1" if "monkey" in cmd
            else ""
        )

        # 1) 패키지 자동 탐색
        self.assertEqual(adb.find_game_package(), "com.FreeDust.UnderDark")

        # 2) BlueStacks 홈 런처가 포그라운드인 경우 -> 튕김 감지 True
        adb.device.app_current.return_value = MagicMock(package="com.bluestacks.appmart")
        worker = MacroWorker(adb, self.detector, MagicMock())
        crashed, reason = worker._check_adb_app_crashed()
        self.assertTrue(crashed)
        self.assertIn("com.bluestacks.appmart", reason)

        # 3) UnderDark가 포그라운드인 경우 -> 튕김 감지 False
        adb.device.app_current.return_value = MagicMock(package="com.FreeDust.UnderDark")
        crashed_game, _ = worker._check_adb_app_crashed()
        self.assertFalse(crashed_game)

        # 4) ADB 직접 재실행 호출 검증
        self.assertTrue(adb.launch_app())

if __name__ == '__main__':
    unittest.main()

