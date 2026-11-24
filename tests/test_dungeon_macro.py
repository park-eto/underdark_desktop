import sys
import os
import cv2
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.detector import PopupDetector

def cv_imread(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def test_all_screens():
    detector = PopupDetector()

    def get_img_path(name):
        p1 = os.path.join(project_root, "assets", "images", name)
        if os.path.exists(p1): return p1
        return os.path.join(project_root, name)

    # 1. 캠프 화면 테스트
    camp_path = get_img_path("캠프화면.png")
    img_camp = cv_imread(camp_path)[34:994, 0:540]
    state, score, coords = detector.analyze_screen_state(img_camp)
    print(f"[캠프화면] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "CAMP", f"Expected CAMP, got {state}"
    assert coords is not None and abs(coords[0] - 269) < 15 and abs(coords[1] - 710) < 15

    # 2. 던전 선택 화면 테스트
    dungeon_path = get_img_path("던전선택화면.png")
    img_dungeon = cv_imread(dungeon_path)[34:994, 0:540]
    state, score, coords = detector.analyze_screen_state(img_dungeon)
    print(f"[던전선택화면] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "DUNGEON_POPUP", f"Expected DUNGEON_POPUP, got {state}"
    
    # 심연의 모래 구멍 감지 테스트
    found_abyss, a_score, a_coords = detector.detect_abyss_dungeon(img_dungeon)
    print(f"[심연의모래구멍] Found: {found_abyss}, Score: {a_score:.2f}, Coords: {a_coords}")
    assert found_abyss is True, "Expected abyss dungeon to be found"
    assert abs(a_coords[0] - 264) < 15 and abs(a_coords[1] - 678) < 15

    # 3. 게임 진행 화면 테스트
    game_path = get_img_path("게임진행화면.png")
    img_game = cv_imread(game_path)[34:994, 0:540]
    state, score, coords = detector.analyze_screen_state(img_game)
    print(f"[게임진행화면] State: {state}, Score: {score:.2f}")
    assert state == "IN_GAME", f"Expected IN_GAME, got {state}"

    # 4. 게임 오버 화면 테스트
    go_path = get_img_path("게임오버화면.png")
    img_go = cv_imread(go_path)[34:994, 0:540]
    state, score, coords = detector.analyze_screen_state(img_go)
    print(f"[게임오버화면] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "GAMEOVER", f"Expected GAMEOVER, got {state}"
    assert coords is not None and abs(coords[0] - 268) < 15 and abs(coords[1] - 619) < 15

    # 5. 획득 보상 화면 테스트
    reward_path = get_img_path("획득보상화면.png")
    img_reward = cv_imread(reward_path)[34:994, 0:540]
    state, score, coords = detector.analyze_screen_state(img_reward)
    print(f"[획득보상화면] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "REWARD", f"Expected REWARD, got {state}"
    assert coords is not None and abs(coords[0] - 271) < 15 and abs(coords[1] - 779) < 15

    # 6. 매크로 방지 팝업 화면 테스트 (우선순위 1위 확인)
    popup_path = get_img_path("화면캡처.png")
    img_popup = cv_imread(popup_path)[32:992, 0:540]
    state, score, coords = detector.analyze_screen_state(img_popup)
    print(f"[방지팝업화면] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "POPUP", f"Expected POPUP, got {state}"

    print("\n>>> ALL DUNGEON MACRO DETECTION TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_all_screens()
