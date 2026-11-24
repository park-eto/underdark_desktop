import sys
import os
import cv2
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.detector import PopupDetector

def cv_imread(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def get_img(name):
    p = os.path.join(project_root, "assets", "images", name)
    return cv_imread(p)

def test_stage_farming_flow():
    detector = PopupDetector()

    # 1. 캠프 화면 -> [던전] 터치
    img_camp = get_img("캠프화면.png")
    state, score, coords = detector.analyze_screen_state(img_camp, mode="stage_farming")
    print(f"[1. 캠프] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "CAMP", f"Expected CAMP, got {state}"
    assert coords is not None

    # 2. 던전 선택 화면 (Stage 811) -> [<- 이전] 화살표 터치
    img_dungeon = get_img("일반_810스테이지_던전선택.png")
    state, score, coords = detector.analyze_screen_state(img_dungeon, mode="stage_farming")
    print(f"[2. 던전선택-811] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "STAGE_NEED_PREV", f"Expected STAGE_NEED_PREV, got {state}"
    assert coords is not None and abs(coords[0] - 363) < 15 and abs(coords[1] - 377) < 15

    # 3. 810 스테이지 확인 완료 -> 우측 [입장] 버튼 터치 (소탕 아님!)
    img_810 = get_img("일반_810스테이지_810스테이지.png")
    state, score, coords = detector.analyze_screen_state(img_810, mode="stage_farming")
    print(f"[3. 810 준비 (영문 Stage 810)] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "STAGE_810_READY", f"Expected STAGE_810_READY, got {state}"
    assert coords is not None and abs(coords[0] - 565) < 15 and abs(coords[1] - 442) < 15

    # 3-1. 신규 한글 810 스테이지 확인 완료 ('스테이지 810')
    img_810_kr = get_img("일반_810스테이지_던전선택2.png")
    state_kr, score_kr, coords_kr = detector.analyze_screen_state(img_810_kr, mode="stage_farming")
    print(f"[3-1. 810 준비 (한글 '스테이지 810')] State: {state_kr}, Score: {score_kr:.2f}, Coords: {coords_kr}")
    assert state_kr == "STAGE_810_READY", f"Expected STAGE_810_READY, got {state_kr}"
    assert coords_kr is not None

    # 4. 인게임 일반 웨이브 진행 (1/16 ~ 15/16)
    img_game = get_img("일반_810스테이지_게임화면.png")
    state, score, coords = detector.analyze_screen_state(img_game, mode="stage_farming")
    print(f"[4. 인게임 일반] State: {state}, Score: {score:.2f}")
    assert state == "IN_GAME", f"Expected IN_GAME, got {state}"

    # 5. Final Wave 보스 등장 -> 우측 상단 햄버거 메뉴 터치
    img_boss = get_img("일반_810스테이지_보스등장.png")
    state, score, coords = detector.analyze_screen_state(img_boss, mode="stage_farming")
    print(f"[5. 보스 등장 (영문 Final wave)] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "FINAL_WAVE", f"Expected FINAL_WAVE, got {state}"
    assert coords is not None and abs(coords[0] - 930) < 20 and abs(coords[1] - 77) < 20

    # 5-1. 신규 한글 보스 등장 ('마지막 웨이브')
    img_boss_kr = get_img("일반_810스테이지_보스등장2.png")
    state_b_kr, score_b_kr, coords_b_kr = detector.analyze_screen_state(img_boss_kr, mode="stage_farming")
    print(f"[5-1. 보스 등장 (한글 '마지막 웨이브')] State: {state_b_kr}, Score: {score_b_kr:.2f}, Coords: {coords_b_kr}")
    assert state_b_kr == "FINAL_WAVE", f"Expected FINAL_WAVE, got {state_b_kr}"
    assert coords_b_kr is not None and abs(coords_b_kr[0] - 930) < 20 and abs(coords_b_kr[1] - 77) < 20

    # 6. 인게임 설정창 -> [포기하기] 버튼 터치
    img_setting = get_img("일반_810스테이지_설정창.png")
    state, score, coords = detector.analyze_screen_state(img_setting, mode="stage_farming")
    print(f"[6. 설정창] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "GIVEUP_SETTING", f"Expected GIVEUP_SETTING, got {state}"
    assert coords is not None and abs(coords[0] - 407) < 15 and abs(coords[1] - 595) < 15

    # 7. 포기하기 확인 팝업 -> [예] 버튼 터치
    img_giveup = get_img("일반_810스테이지_포기하기.png")
    state, score, coords = detector.analyze_screen_state(img_giveup, mode="stage_farming")
    print(f"[7. 포기확인] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "GIVEUP_CONFIRM", f"Expected GIVEUP_CONFIRM, got {state}"
    assert coords is not None and abs(coords[0] - 385) < 15 and abs(coords[1] - 595) < 15

    # 8. 게임 종료 / 패배 화면 -> [광고 x2] 터치
    img_over = get_img("일반_810스테이지_게임종료.png")
    state, score, coords = detector.analyze_screen_state(img_over, mode="stage_farming")
    print(f"[8. 게임오버] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "GAMEOVER", f"Expected GAMEOVER, got {state}"
    assert coords is not None and abs(coords[0] - 478) < 15 and abs(coords[1] - 653) < 15

    # 9. 보상 획득 화면 -> [확인] 터치
    img_reward = get_img("일반_810스테이지_보상획득.png")
    state, score, coords = detector.analyze_screen_state(img_reward, mode="stage_farming")
    print(f"[9. 보상획득] State: {state}, Score: {score:.2f}, Coords: {coords}")
    assert state == "REWARD", f"Expected REWARD, got {state}"
    assert coords is not None and abs(coords[0] - 481) < 15 and abs(coords[1] - 813) < 15

    print("\n>>> ALL STAGE 810 FARMING TESTS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    test_stage_farming_flow()
