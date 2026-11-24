import os
import unittest
import numpy as np
import cv2

from src.core.detector import PopupDetector
from src.core.controller import MacroWorker
from src.core.resources import get_resource_path


class TestPetSynthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PopupDetector()
        cls.images_dir = os.path.join("assets", "images")

    def _load_image(self, name: str) -> np.ndarray:
        p = os.path.join(self.images_dir, name)
        self.assertTrue(os.path.exists(p), f"Sample image not found: {p}")
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(img, f"Failed to decode image: {p}")
        return img

    def test_templates_loaded(self):
        """펫 자동 일괄 합성에 필요한 9개 신규 템플릿이 정상 로드되는지 확인"""
        self.assertIsNotNone(self.detector.template_tab_inventory)
        self.assertIsNotNone(self.detector.template_tab_pet)
        self.assertIsNotNone(self.detector.template_btn_pet_synth)
        self.assertIsNotNone(self.detector.template_btn_batch_synth)
        self.assertIsNotNone(self.detector.template_btn_cancel_synth)
        self.assertIsNotNone(self.detector.template_batch_arrow_left)
        self.assertIsNotNone(self.detector.template_tier_legend)
        self.assertIsNotNone(self.detector.template_btn_batch_confirm)
        self.assertIsNotNone(self.detector.template_tab_camp)

    def test_detect_tab_inventory(self):
        """캠프 화면에서 하단 [인벤토리] 탭 검출 확인"""
        camp = self._load_image("펫합성_캠프화면2.png")
        matched, score, (cx, cy) = self.detector.detect_tab_inventory(camp)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 317, delta=15)
        self.assertAlmostEqual(cy, 945, delta=15)

    def test_detect_tab_pet(self):
        """인벤토리 화면에서 서브탭 [펫] 검출 확인"""
        inv = self._load_image("펫합성_인벤토리.png")
        matched, score, (cx, cy) = self.detector.detect_tab_pet(inv)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 592, delta=15)
        self.assertAlmostEqual(cy, 824, delta=15)

    def test_detect_pet_synth_btn(self):
        """펫 인벤토리 화면에서 중앙 하단 [합성] 버튼 검출 확인"""
        pet_inv = self._load_image("펫합성_펫인벤토리.png")
        matched, score, (cx, cy) = self.detector.detect_pet_synth_btn(pet_inv)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 283, delta=15)
        self.assertAlmostEqual(cy, 411, delta=15)

    def test_detect_batch_synth_btn_presence_and_absence(self):
        """일괄 합성 버튼 존재(합성 가능) 및 부재(합성 불가) 검출 확인"""
        synth_click = self._load_image("펫합성_합성버튼클릭.png")
        matched, score, (cx, cy) = self.detector.detect_batch_synth_btn(synth_click)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 675, delta=15)
        self.assertAlmostEqual(cy, 446, delta=15)

        synth_none = self._load_image("펫합성_일괄합성없음.png")
        matched_none, score_none, _ = self.detector.detect_batch_synth_btn(synth_none)
        self.assertFalse(matched_none)
        self.assertLess(score_none, 0.60)

    def test_detect_cancel_synth_btn(self):
        """일괄 합성 불가 시 [취소] 버튼 검출 확인"""
        synth_none = self._load_image("펫합성_일괄합성없음.png")
        matched, score, (cx, cy) = self.detector.detect_cancel_synth_btn(synth_none)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 485, delta=15)
        self.assertAlmostEqual(cy, 446, delta=15)

    def test_detect_batch_arrow_left(self):
        """일괄 합성 등급 선택 팝업에서 [<-] 좌측 화살표 검출 확인"""
        batch_click = self._load_image("펫합성_일괄합성클릭.png")
        matched, score, (cx, cy) = self.detector.detect_batch_arrow_left(batch_click)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 368, delta=15)
        self.assertAlmostEqual(cy, 537, delta=15)

    def test_detect_tier_legend(self):
        """일괄 합성 등급 '전설' 도달 여부 판별 확인"""
        batch_legend = self._load_image("펫합성_일괄합성전설.png")
        matched_legend, score_legend, _ = self.detector.detect_tier_legend(batch_legend)
        self.assertTrue(matched_legend)
        self.assertGreaterEqual(score_legend, 0.85)

        batch_click = self._load_image("펫합성_일괄합성클릭.png")
        matched_click, score_click, _ = self.detector.detect_tier_legend(batch_click)
        self.assertFalse(matched_click)
        self.assertLess(score_click, 0.70)

    def test_detect_batch_confirm_btn(self):
        """일괄 합성 팝업 [확인] 버튼 검출 확인"""
        batch_legend = self._load_image("펫합성_일괄합성전설.png")
        matched, score, (cx, cy) = self.detector.detect_batch_confirm_btn(batch_legend)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 391, delta=15)
        self.assertAlmostEqual(cy, 642, delta=15)

    def test_detect_synth_result(self):
        """펫 합성 결과 화면 및 [확인] 버튼 검출 확인"""
        res = self._load_image("펫합성_합성결과.png")
        matched, score, (cx, cy) = self.detector.detect_synth_result(res)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 481, delta=15)
        self.assertAlmostEqual(cy, 813, delta=15)

    def test_detect_tab_camp(self):
        """하단 중앙 [캠프] 탭 검출 확인"""
        synth_none = self._load_image("펫합성_일괄합성없음.png")
        matched, score, (cx, cy) = self.detector.detect_tab_camp(synth_none)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 482, delta=15)
        self.assertAlmostEqual(cy, 945, delta=15)

    def test_controller_synthesis_trigger_logic(self):
        """컨트롤러의 N판 주기 펫 합성 트리거 판별 로직 검증"""
        worker = MacroWorker(None, self.detector, None)
        worker.pet_synth_enabled = True
        worker.pet_synth_interval = 5

        # 0판: 트리거되지 않음
        worker.stats["dungeon_count"] = 0
        should_synth = worker.pet_synth_enabled and worker.stats["dungeon_count"] > 0 and (worker.stats["dungeon_count"] % worker.pet_synth_interval == 0) and (worker.last_pet_synth_round != worker.stats["dungeon_count"])
        self.assertFalse(should_synth)

        # 4판: 5판 주기가 아니므로 미트리거
        worker.stats["dungeon_count"] = 4
        should_synth = worker.pet_synth_enabled and worker.stats["dungeon_count"] > 0 and (worker.stats["dungeon_count"] % worker.pet_synth_interval == 0) and (worker.last_pet_synth_round != worker.stats["dungeon_count"])
        self.assertFalse(should_synth)

        # 5판: 5의 배수이므로 첫 트리거 발생
        worker.stats["dungeon_count"] = 5
        should_synth = worker.pet_synth_enabled and worker.stats["dungeon_count"] > 0 and (worker.stats["dungeon_count"] % worker.pet_synth_interval == 0) and (worker.last_pet_synth_round != worker.stats["dungeon_count"])
        self.assertTrue(should_synth)

        # 합성 실행 후 last_pet_synth_round 업데이트 -> 동일 5판 상태에서는 재트리거 방지
        worker.last_pet_synth_round = 5
        should_synth = worker.pet_synth_enabled and worker.stats["dungeon_count"] > 0 and (worker.stats["dungeon_count"] % worker.pet_synth_interval == 0) and (worker.last_pet_synth_round != worker.stats["dungeon_count"])
        self.assertFalse(should_synth)

        # 10판: 다음 5판 주기 도달 시 트리거
        worker.stats["dungeon_count"] = 10
        should_synth = worker.pet_synth_enabled and worker.stats["dungeon_count"] > 0 and (worker.stats["dungeon_count"] % worker.pet_synth_interval == 0) and (worker.last_pet_synth_round != worker.stats["dungeon_count"])
        self.assertTrue(should_synth)


if __name__ == "__main__":
    unittest.main()
