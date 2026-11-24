import os
import unittest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from src.core.detector import PopupDetector
from src.core.controller import MacroWorker
from src.gui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication([])

class TestSettingsAndStage(unittest.TestCase):
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

    def test_mode_combo_order(self):
        """심연 매크로(full_auto)가 첫 번째 인덱스(0번)에 정렬되어 있는지 확인"""
        win = MainWindow()
        self.assertEqual(win.mode_combo.itemData(0), MacroWorker.MODE_FULL_AUTO)
        self.assertEqual(win.mode_combo.itemData(1), MacroWorker.MODE_STAGE_FARMING)
        self.assertEqual(win.mode_combo.itemData(2), MacroWorker.MODE_PIN_ONLY)
        win.close()

    def test_target_stage_spin_default_and_range(self):
        """목표 스테이지 기본값이 810이고 정상 범위를 가지는지 확인"""
        win = MainWindow()
        self.assertEqual(win.target_stage_spin.value(), 810)
        self.assertEqual(win.target_stage_spin.minimum(), 1)
        self.assertEqual(win.target_stage_spin.maximum(), 9999)
        win.close()

    def test_settings_save_and_restore(self):
        """사용자가 변경한 설정값이 시스템 재시작 시에도 유지(QSettings)되는지 확인"""
        test_settings = QSettings("UnderDarkMacro", "UnderdarkMacroSolver")
        
        # 임의의 사용자 설정값 기록
        test_settings.setValue("macro_mode", MacroWorker.MODE_STAGE_FARMING)
        test_settings.setValue("target_stage", 850)
        test_settings.setValue("max_runs", 25)
        test_settings.setValue("check_interval", 1.2)
        test_settings.setValue("tap_delay", 120)
        test_settings.setValue("pin_bypass", False)
        test_settings.setValue("auto_confirm", False)
        test_settings.setValue("app_restart", False)
        test_settings.setValue("pet_synth_enabled", True)
        test_settings.setValue("pet_synth_interval", 15)

        # 새로운 창을 띄워 복원 검증
        win = MainWindow()
        self.assertEqual(win.mode_combo.currentData(), MacroWorker.MODE_STAGE_FARMING)
        self.assertEqual(win.target_stage_spin.value(), 850)
        self.assertEqual(win.runs_spin.value(), 25)
        self.assertAlmostEqual(win.interval_spin.value(), 1.2, places=1)
        self.assertEqual(win.delay_spin.value(), 120)
        self.assertFalse(win.pin_bypass_chk.isChecked())
        self.assertFalse(win.confirm_chk.isChecked())
        self.assertFalse(win.app_restart_chk.isChecked())
        self.assertTrue(win.pet_synth_chk.isChecked())
        self.assertEqual(win.pet_interval_spin.value(), 15)

        # 디폴트 복원
        test_settings.setValue("macro_mode", MacroWorker.MODE_FULL_AUTO)
        test_settings.setValue("target_stage", 810)
        win.close()

    def test_detect_stage_target_detection(self):
        """810 스테이지 및 타겟 스테이지 감지 로직 검증"""
        # 810 스테이지 이미지 테스트
        img_path = os.path.join("assets", "images", "일반_810스테이지_던전선택2.png")
        if os.path.exists(img_path):
            import cv2
            img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            # target=810 일 때 매칭
            is_target, score, coords = self.detector.detect_stage_target(img, target_stage=810)
            self.assertTrue(is_target)
            self.assertGreaterEqual(score, 0.85)

            state, _, _ = self.detector.analyze_screen_state(img, mode="stage_farming", target_stage=810)
            self.assertEqual(state, "STAGE_810_READY")

            # target=820 일 때 다른 스테이지 탐색 필요
            state_other, _, _ = self.detector.analyze_screen_state(img, mode="stage_farming", target_stage=820)
            self.assertIn(state_other, ("STAGE_NEED_NEXT", "STAGE_NEED_PREV", "STAGE_TAB_GENERAL"))

    def test_detect_stage_830_and_navigation(self):
        """스테이지 830 직독 및 828, 829 등에서의 방향 탐색 검증 (진동 버그 방지)"""
        import cv2
        p_830 = "stage_830_screen.png"
        p_829 = "stage_829_screen.png"
        p_828 = "stage_828_screen.png"

        if os.path.exists(p_830):
            img_830 = cv2.imread(p_830)
            # 1. 830 화면에서 숫자 직독 검증
            cur_stage = self.detector.detect_current_stage(img_830)
            self.assertEqual(cur_stage, 830)

            # 2. 목표가 830일 때 STAGE_TARGET_READY 반환 검증
            state, score, coords = self.detector.analyze_screen_state(img_830, mode="stage_farming", target_stage=830)
            self.assertEqual(state, "STAGE_TARGET_READY")
            self.assertIsNotNone(coords)

            # 3. 목표가 825일 때 STAGE_NEED_PREV 반환 검증
            state_prev, _, _ = self.detector.analyze_screen_state(img_830, mode="stage_farming", target_stage=825)
            self.assertEqual(state_prev, "STAGE_NEED_PREV")

        if os.path.exists(p_829):
            img_829 = cv2.imread(p_829)
            # 4. 829 화면에서 목표가 830일 때 STAGE_NEED_NEXT 반환 검증 (이전 진동 버그 방지)
            state_next, _, _ = self.detector.analyze_screen_state(img_829, mode="stage_farming", target_stage=830)
            self.assertEqual(state_next, "STAGE_NEED_NEXT")

        if os.path.exists(p_828):
            img_828 = cv2.imread(p_828)
            # 5. 828 화면에서 목표가 830일 때 STAGE_NEED_NEXT 반환 검증
            state_next2, _, _ = self.detector.analyze_screen_state(img_828, mode="stage_farming", target_stage=830)
            self.assertEqual(state_next2, "STAGE_NEED_NEXT")

    def test_stage_navigation_planner_and_crosscheck(self):
        """
        스테이지 이동 계획(Planner) 수립, OCR 미인식 시 추정 이동, 중간 크로스체크 및
        붙은 숫자(840 등) 분할 인식 검증
        """
        import cv2
        p_830 = "stage_830_screen.png"
        p_829 = "stage_829_screen.png"
        p_828 = "stage_828_screen.png"
        if not (os.path.exists(p_830) and os.path.exists(p_829) and os.path.exists(p_828)):
            return

        img_830 = cv2.imread(p_830)
        img_829 = cv2.imread(p_829)
        img_828 = cv2.imread(p_828)

        # 스테이지 알약 숫자 영역만 마스킹하여 OCR 미인식 상황을 시뮬레이션하는 헬퍼
        def make_unreadable_pill(frame):
            f = frame.copy()
            fh, fw = f.shape[:2]
            f[int(fh * 0.33):int(fh * 0.38), int(fw * 0.40):int(fw * 0.60)] = 0
            return f

        # 1. [계획 수립 + OCR 미인식 구간 통과 + 목표 도달 판정]
        # 현재 830에서 목표 828로 이동할 때 (좌측 2회 이동 계획)
        self.detector.reset_stage_navigation()
        state1, _, _ = self.detector.analyze_screen_state(img_830, mode="stage_farming", target_stage=828)
        self.assertEqual(state1, "STAGE_NEED_PREV")
        self.assertEqual(self.detector.nav_anchor_stage, 830)
        self.assertEqual(self.detector.nav_estimated_stage, 830)
        self.assertEqual(self.detector.nav_remaining_steps, -2)

        # 1번째 [<-] 클릭 기록 -> 추정 스테이지 829, 남은 이동 -1
        self.detector.record_stage_step(-1)
        self.assertEqual(self.detector.nav_estimated_stage, 829)
        self.assertEqual(self.detector.nav_remaining_steps, -1)

        # 중간 스테이지(829)에서 OCR이 실패하더라도 추정 스테이지(829) 기준으로 계속 [<-] 이동해야 함
        unreadable_829 = make_unreadable_pill(img_829)
        state2, _, _ = self.detector.analyze_screen_state(unreadable_829, mode="stage_farming", target_stage=828)
        self.assertEqual(state2, "STAGE_NEED_PREV")
        self.assertEqual(self.detector.nav_estimated_stage, 829)

        # 2번째 [<-] 클릭 기록 -> 추정 스테이지 828 (목표 도달!), 남은 이동 0
        self.detector.record_stage_step(-1)
        self.assertEqual(self.detector.nav_estimated_stage, 828)
        self.assertEqual(self.detector.nav_remaining_steps, 0)

        # 목표 스테이지(828)에서조차 OCR이 실패하더라도, 계획된 2회 이동을 마쳤으므로 진동 없이 즉시 입장(STAGE_TARGET_READY)해야 함!
        unreadable_828 = make_unreadable_pill(img_828)
        state3, _, _ = self.detector.analyze_screen_state(unreadable_828, mode="stage_farming", target_stage=828)
        self.assertEqual(state3, "STAGE_TARGET_READY")

        # 2. [중간 크로스체크 보정 검증]
        # 828에서 목표 830으로 이동 계획 수립 (+2회) -> [->] 클릭했으나 렉으로 화면이 안 넘어가 여전히 828이 인식된 경우
        self.detector.reset_stage_navigation()
        state_a, _, _ = self.detector.analyze_screen_state(img_828, mode="stage_farming", target_stage=830)
        self.assertEqual(state_a, "STAGE_NEED_NEXT")
        self.assertEqual(self.detector.nav_remaining_steps, 2)

        self.detector.record_stage_step(1)  # 추정값은 829가 됨
        # 그러나 실제 화면은 여전히 828로 인식됨 -> 크로스체크가 828로 보정하고 남은 횟수를 다시 2회로 복구해야 함
        state_b, _, _ = self.detector.analyze_screen_state(img_828, mode="stage_farming", target_stage=830)
        self.assertEqual(state_b, "STAGE_NEED_NEXT")
        self.assertEqual(self.detector.nav_estimated_stage, 828)
        self.assertEqual(self.detector.nav_remaining_steps, 2)

if __name__ == "__main__":
    unittest.main()
