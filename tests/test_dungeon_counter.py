import unittest
from unittest.mock import MagicMock
from src.core.controller import MacroWorker

class TestDungeonCounter(unittest.TestCase):
    def setUp(self):
        self.mock_adb = MagicMock()
        self.mock_detector = MagicMock()
        self.mock_ocr = MagicMock()
        self.worker = MacroWorker(self.mock_adb, self.mock_detector, self.mock_ocr)

    def test_record_dungeon_completion_single(self):
        """1회 완료 기록 시 dungeon_count가 1 증가하고 True 반환"""
        self.assertFalse(self.worker.round_counted)
        self.assertEqual(self.worker.stats["dungeon_count"], 0)

        result = self.worker._record_dungeon_completion("테스트")
        self.assertTrue(result)
        self.assertTrue(self.worker.round_counted)
        self.assertEqual(self.worker.stats["dungeon_count"], 1)

    def test_record_dungeon_completion_no_duplicates(self):
        """동일 라운드에서 여러 번 호출되어도 중복 카운트되지 않음"""
        self.worker._record_dungeon_completion("GAMEOVER")
        self.assertEqual(self.worker.stats["dungeon_count"], 1)

        # REWARD 등 동일 라운드 후속 화면에서 다시 호출 시 무시됨
        result2 = self.worker._record_dungeon_completion("REWARD")
        self.assertFalse(result2)
        self.assertEqual(self.worker.stats["dungeon_count"], 1)

        # 3번째 호출도 무시됨
        result3 = self.worker._record_dungeon_completion("GAMEOVER")
        self.assertFalse(result3)
        self.assertEqual(self.worker.stats["dungeon_count"], 1)

    def test_next_round_resets_counter_flag(self):
        """다음 라운드 진입 시 플래그가 리셋되어 정상적으로 다음 판 카운트가 기록됨"""
        # 1라운드 종료
        self.worker._record_dungeon_completion("1라운드")
        self.assertEqual(self.worker.stats["dungeon_count"], 1)

        # 새 라운드 시작 (입장 또는 인게임)
        self.worker.round_counted = False

        # 2라운드 종료
        self.worker._record_dungeon_completion("2라운드")
        self.assertEqual(self.worker.stats["dungeon_count"], 2)

if __name__ == '__main__':
    unittest.main()

