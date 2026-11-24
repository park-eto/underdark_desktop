import os
import unittest
import numpy as np
import cv2

from src.core.detector import PopupDetector
from src.core.controller import MacroWorker


class TestRankReward(unittest.TestCase):
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

    def test_claim_templates_loaded(self):
        """정기/랭킹 보상 상자 [받기] 템플릿 로드 검증"""
        self.assertIsNotNone(self.detector.template_btn_claim)

    def test_detect_rank_reward_on_sample(self):
        """랭킹보상.png 샘플에서 [받기] 버튼 정밀 검출 검증"""
        img = self._load_image("랭킹보상.png")
        matched, score, (cx, cy) = self.detector.detect_rank_reward(img)
        self.assertTrue(matched)
        self.assertGreaterEqual(score, 0.85)
        self.assertAlmostEqual(cx, 480, delta=15)
        self.assertAlmostEqual(cy, 687, delta=15)

    def test_analyze_screen_state_rank_reward(self):
        """모든 파밍 모드에서 랭킹 보상 팝업이 최우선 상태(RANK_REWARD)로 판별되는지 검증"""
        img = self._load_image("랭킹보상.png")
        for mode in ["stage_farming", "full_auto"]:
            st, score, coords = self.detector.analyze_screen_state(img, mode=mode)
            self.assertEqual(st, "RANK_REWARD")
            self.assertGreaterEqual(score, 0.85)
            self.assertIsNotNone(coords)
            self.assertAlmostEqual(coords[0], 480, delta=15)
            self.assertAlmostEqual(coords[1], 687, delta=15)

    def test_no_false_positive_on_other_screens(self):
        """일반 게임 화면들에서 RANK_REWARD 오탐이 발생하지 않는지 검증"""
        other_samples = [
            "캠프화면.png",
            "던전선택화면.png",
            "게임진행화면.png",
            "게임오버화면.png",
            "획득보상화면.png",
            "언더다크튕김.png"
        ]
        for name in other_samples:
            p = os.path.join(self.images_dir, name)
            if not os.path.exists(p):
                p = os.path.join(".", name)
            if os.path.exists(p):
                img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    matched, score, _ = self.detector.detect_rank_reward(img)
                    self.assertFalse(matched, f"False positive RANK_REWARD on {name} (score={score:.3f})")


if __name__ == "__main__":
    unittest.main()

