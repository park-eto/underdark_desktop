import time
import datetime
import gc
import cv2
import numpy as np
from typing import Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from .adb_client import AdbClient
from .detector import PopupDetector
from .ocr_engine import OcrEngine

class MacroWorker(QThread):
    """
    백그라운드에서 실시간 모니터링, 매크로 방지 핀코드 해제,
    및 던전 자동 반복 파밍 루프를 수행하는 QThread 워커
    (멀티 해상도, 스마트 스크롤 탐색 및 초기 커맨드 1회 실행 기능 탑재)
    """
    log_signal = pyqtSignal(str)
    frame_signal = pyqtSignal(np.ndarray)
    stat_signal = pyqtSignal(dict)
    status_signal = pyqtSignal(str)

    MODE_FULL_AUTO = "full_auto"          # 던전 자동 반복 + 핀코드 자동 해제 (심연의 모래 구멍)
    MODE_PIN_ONLY = "pin_only"            # 단독 핀코드 자동 해제만
    MODE_STAGE_FARMING = "stage_farming"  # 신규: 일반 810 스테이지 노가다 (Final Wave 포기하기 반복)

    def __init__(self, adb_client: AdbClient, detector: PopupDetector, ocr: OcrEngine):
        super().__init__()
        self.adb = adb_client
        self.detector = detector
        self.ocr = ocr

        self.running = False
        self.mode = self.MODE_FULL_AUTO
        self.check_interval = 0.6      # 기본 검사 주기 (초)
        self.tap_delay = 0.08           # 키패드 터치 딜레이 (초)
        self.auto_solve_pin = True      # 핀코드 자동 해제 활성화 여부 (체크박스 연동)
        self.auto_click_confirm = True  # 핀코드 해제 후 확인 버튼 자동 터치
        self.auto_restart_app = True    # 앱 튕김/비정상 종료 시 자동 재시작 여부
        self.max_runs = 0               # 목표 반복 횟수 (0 = 무제한)
        self.target_stage = 810         # 일반 스테이지 노가다 목표 스테이지 번호 (기본 810)
        
        # 🐾 펫 자동 일괄 합성 설정 (특정 던전 완료 판수마다 실행)
        self.pet_synth_enabled: bool = False
        self.pet_synth_interval: int = 5
        self.last_pet_synth_round: int = -1
        self.force_pet_synth: bool = False

        # 🏰 심연 던전 자동 타워 설치 설정 (체크박스 On/Off 연동)
        self.auto_place_tower: bool = True
        self.max_tower_placements: int = 15
        self.placed_tower_spots: list = []
        self.tower_placement_done: bool = False
        self.tower_no_plan_streak: int = 0

        # 전투 시작 시 1회 초기 커맨드 실행 설정
        self.initial_cmd_enabled: bool = False
        self.initial_cmd_type: str = "drag_right"  # drag_right, drag_left, drag_up, drag_down, drag_up_right, drag_down_right, drag_up_left, drag_down_left
        self.initial_cmd_duration: int = 200       # ms (기본 200ms)
        self.initial_cmd_executed: bool = False

        self.dungeon_scroll_count: int = 0
        self.round_counted: bool = False  # 라운드 완료 카운트 중복 방지 플래그

        # 내부 상태 추적
        self.current_state = "IDLE"
        self.game_start_time: Optional[float] = None
        self.last_state = "UNKNOWN"
        self.state_repeat_count = 0

        # 통계 데이터
        self.stats = {
            "dungeon_count": 0,
            "success_count": 0,
            "last_code": "-",
            "last_time": "-",
            "retry_count": 0,
            "elapsed_battle": "00:00",
            "current_state": "대기 중"
        }

    def stop(self):
        self.running = False
        self.wait(2000)

    def _reset_tower_state(self):
        """새 라운드 시작 또는 종료 시 타워 설치 상태 및 탐지 중단 플래그 초기화"""
        self.placed_tower_spots.clear()
        self.tower_placement_done = False
        self.tower_no_plan_streak = 0

    def _execute_initial_command(self, fw: int, fh: int):
        """전투 시작 직후 사용자가 지정한 초기 커맨드를 1회 실행 (8방향 드래그)"""
        try:
            self.initial_cmd_executed = True
            cmd = self.initial_cmd_type
            duration = max(50, self.initial_cmd_duration)
            cx, cy = fw // 2, int(fh * 0.65)  # 하단 중앙 (가상 조이스틱 기준 영역)

            self.log_signal.emit(f"[초기 커맨드] 게임 시작 조작 1회 실행: {cmd} ({duration}ms)")
            self.status_signal.emit(f"초기 조작 실행: {cmd}")

            dx = int(fw * 0.28)
            dy = int(fh * 0.22)
            diag_dx = int(fw * 0.20)
            diag_dy = int(fh * 0.16)

            # 4대 직선 방향
            if cmd == "drag_right":
                tx = min(fw - 20, cx + dx)
                self.adb.swipe(cx, cy, tx, cy, duration)
            elif cmd == "drag_left":
                tx = max(20, cx - dx)
                self.adb.swipe(cx, cy, tx, cy, duration)
            elif cmd == "drag_up":
                ty = max(20, cy - dy)
                self.adb.swipe(cx, cy, cx, ty, duration)
            elif cmd == "drag_down":
                ty = min(fh - 20, cy + dy)
                self.adb.swipe(cx, cy, cx, ty, duration)
            # 4대 대각선 방향
            elif cmd == "drag_up_right":
                tx = min(fw - 20, cx + diag_dx)
                ty = max(20, cy - diag_dy)
                self.adb.swipe(cx, cy, tx, ty, duration)
            elif cmd == "drag_down_right":
                tx = min(fw - 20, cx + diag_dx)
                ty = min(fh - 20, cy + diag_dy)
                self.adb.swipe(cx, cy, tx, ty, duration)
            elif cmd == "drag_up_left":
                tx = max(20, cx - diag_dx)
                ty = max(20, cy - diag_dy)
                self.adb.swipe(cx, cy, tx, ty, duration)
            elif cmd == "drag_down_left":
                tx = max(20, cx - diag_dx)
                ty = min(fh - 20, cy + diag_dy)
                self.adb.swipe(cx, cy, tx, ty, duration)

            self.log_signal.emit("[초기 커맨드] 실행 완료! 정상 전투 모니터링 계속")
            time.sleep(0.3)
        except Exception as e:
            self.log_signal.emit(f"[초기 커맨드] 실행 중 오류: {e}")

    def _record_dungeon_completion(self, mode_tag: str = "810 노가다") -> bool:
        """
        던전 1회 완료 통계 기록 및 신호 송출 (중복 카운트 방지).
        신규 카운트가 기록되었으면 True, 이미 카운트된 라운드이면 False 반환.
        """
        if self.round_counted:
            return False

        self.round_counted = True
        self.stats["dungeon_count"] += 1
        self.stats["last_time"] = datetime.datetime.now().strftime("%H:%M:%S")
        self.stats["elapsed_battle"] = "완료"
        self.stat_signal.emit(self.stats)
        self.log_signal.emit(f"[{mode_tag}] 던전 완료! 누적 {self.stats['dungeon_count']}회 완료")
        return True

    def _run_pet_synthesis(self, frame: np.ndarray, fw: int, fh: int):
        """
        캠프 화면에서 특정 판수 주기 도달 시 실행되는 펫 자동 일괄 합성 서브루틴.
        1. 캠프 화면 하단 [인벤토리] 터치
        2. 인벤토리 내 [펫] 서브탭 터치
        3. 펫 인벤토리 중앙 [합성] 버튼 터치
        4. 합성 알고리즘 루프:
           - [일괄 합성] 버튼 존재 시 터치
           - [일괄 합성] 버튼 부재 시 [취소] 터치 -> [캠프] 터치하여 종료
           - 일괄 합성 등급 팝업: '<-' 화살표를 눌러 '일반'에서 '전설'로 변경 -> [확인] 터치
           - 합성 결과 팝업: [확인] 터치 -> 4번으로 돌아가 반복
        """
        self.log_signal.emit(f"[펫합성] 🐾 던전 {self.stats['dungeon_count']}회 완료 달성! 펫 자동 일괄 합성 루틴 시작")
        self.status_signal.emit("펫 자동 합성 시작...")

        # 1단계: 캠프 -> 하단 [인벤토리] 터치
        _, _, (inv_x, inv_y) = self.detector.detect_tab_inventory(frame)
        self.log_signal.emit(f"[펫합성] 1단계: 하단 [인벤토리] 탭 터치 ({inv_x}, {inv_y})")
        self.status_signal.emit("펫 합성: 인벤토리 이동 중...")
        self.adb.tap(inv_x, inv_y)
        time.sleep(1.2)

        if not self.running:
            return

        # 2단계: 인벤토리 -> [펫] 서브탭 터치
        frame_inv = self.adb.capture_screen()
        if frame_inv is not None:
            _, _, (pet_x, pet_y) = self.detector.detect_tab_pet(frame_inv)
        else:
            pet_x, pet_y = int(0.592 * fw), int(0.825 * fh)

        self.log_signal.emit(f"[펫합성] 2단계: [펫] 서브탭 터치 ({pet_x}, {pet_y})")
        self.status_signal.emit("펫 합성: 펫 인벤토리 진입...")
        self.adb.tap(pet_x, pet_y)
        time.sleep(1.0)

        if not self.running:
            return

        # 3단계: 펫 인벤토리 -> [합성] 버튼 터치
        frame_pet = self.adb.capture_screen()
        if frame_pet is not None:
            _, _, (synth_x, synth_y) = self.detector.detect_pet_synth_btn(frame_pet)
        else:
            synth_x, synth_y = int(0.283 * fw), int(0.413 * fh)

        self.log_signal.emit(f"[펫합성] 3단계: [합성] 버튼 터치 ({synth_x}, {synth_y})")
        self.status_signal.emit("펫 합성: 합성 메뉴 오픈...")
        self.adb.tap(synth_x, synth_y)
        time.sleep(1.2)

        # 4단계 ~ 6단계 반복 루프
        synth_loop_count = 0
        max_synth_loops = 20  # 안전 루프 제한

        while self.running and synth_loop_count < max_synth_loops:
            synth_loop_count += 1
            cur_frame = self.adb.capture_screen()
            if cur_frame is None:
                time.sleep(0.5)
                continue

            # 일괄 합성 버튼 존재 여부 확인
            has_batch, b_score, (bx, by) = self.detector.detect_batch_synth_btn(cur_frame)
            if has_batch:
                self.log_signal.emit(f"[펫합성] 4단계: [일괄 합성] 버튼 감지(신뢰도 {b_score*100:.1f}%) -> 터치 ({bx}, {by})")
                self.status_signal.emit("펫 합성: 일괄 합성 진행...")
                self.adb.tap(bx, by)
                time.sleep(0.8)

                if not self.running:
                    break

                # 5단계: 일괄 합성 등급 팝업 ('일반' -> '전설' 변경)
                dlg_frame = self.adb.capture_screen()
                is_legend = False
                if dlg_frame is not None:
                    is_legend, _, _ = self.detector.detect_tier_legend(dlg_frame)

                arrow_taps = 0
                while self.running and not is_legend and arrow_taps < 6:
                    arrow_taps += 1
                    if dlg_frame is not None:
                        _, _, (arr_x, arr_y) = self.detector.detect_batch_arrow_left(dlg_frame)
                    else:
                        arr_x, arr_y = int(0.368 * fw), int(0.537 * fh)

                    self.log_signal.emit(f"[펫합성] 5단계: [<-] 화살표 터치 ({arr_x}, {arr_y}) - 등급을 '전설'로 변경 시도 ({arrow_taps}회)")
                    self.adb.tap(arr_x, arr_y)
                    time.sleep(0.4)

                    dlg_frame = self.adb.capture_screen()
                    if dlg_frame is not None:
                        is_legend, _, _ = self.detector.detect_tier_legend(dlg_frame)

                if is_legend:
                    self.log_signal.emit("[펫합성] 5단계: '전설' 등급 선택 확인 완료!")
                else:
                    self.log_signal.emit("[펫합성] 5단계: 등급 텍스트 미검출 -> 좌측 화살표 조작 후 계속 진행")

                # 일괄 합성 [확인] 버튼 터치
                if dlg_frame is not None:
                    _, _, (conf_x, conf_y) = self.detector.detect_batch_confirm_btn(dlg_frame)
                else:
                    conf_x, conf_y = int(0.391 * fw), int(0.645 * fh)

                self.log_signal.emit(f"[펫합성] 5단계: 일괄 합성 [확인] 버튼 터치 ({conf_x}, {conf_y})")
                self.adb.tap(conf_x, conf_y)
                time.sleep(1.5)  # 합성 애니메이션 및 결과 화면 대기

                if not self.running:
                    break

                # 6단계: 합성 결과 화면 대기 및 [확인] 터치
                result_confirmed = False
                for _ in range(5):
                    if not self.running:
                        break
                    res_frame = self.adb.capture_screen()
                    if res_frame is not None:
                        has_res_conf, r_score, (rc_x, rc_y) = self.detector.detect_synth_result(res_frame)
                        if has_res_conf:
                            self.log_signal.emit(f"[펫합성] 6단계: 합성 결과 화면 감지(신뢰도 {r_score*100:.1f}%) -> [확인] 버튼 터치 ({rc_x}, {rc_y})")
                            self.status_signal.emit("펫 합성 결과 확인 터치")
                            self.adb.tap(rc_x, rc_y)
                            result_confirmed = True
                            time.sleep(1.0)
                            break
                    time.sleep(0.5)

                if not result_confirmed:
                    # 폴백: 결과창 기본 확인 위치 1회 터치
                    self.adb.tap(int(0.481 * fw), int(0.813 * fh))
                    time.sleep(1.0)

                # 4단계로 돌아가서 추가 합성 대상이 있는지 재확인
                continue

            else:
                # [일괄 합성] 버튼이 없음 -> 합성 종료 절차
                self.log_signal.emit("[펫합성] 4단계: 일괄 합성 버튼 없음 (합성 가능한 펫 없음) -> 루틴 종료 진행")
                self.status_signal.emit("펫 합성 종료 중...")

                # [취소] 버튼 터치
                _, _, (cancel_x, cancel_y) = self.detector.detect_cancel_synth_btn(cur_frame)
                self.log_signal.emit(f"[펫합성] [취소] 버튼 터치 ({cancel_x}, {cancel_y})")
                self.adb.tap(cancel_x, cancel_y)
                time.sleep(0.8)

                # 하단 중앙 [캠프] 탭 터치하여 캠프 화면 복귀
                cur_frame2 = self.adb.capture_screen()
                if cur_frame2 is not None:
                    _, _, (camp_x, camp_y) = self.detector.detect_tab_camp(cur_frame2)
                else:
                    camp_x, camp_y = int(0.482 * fw), int(0.950 * fh)

                self.log_signal.emit(f"[펫합성] 하단 중앙 [캠프] 탭 터치 ({camp_x}, {camp_y}) -> 캠프 복귀")
                self.adb.tap(camp_x, camp_y)
                time.sleep(1.2)
                break

        self.log_signal.emit("[펫합성] 🐾 펫 자동 일괄 합성 루틴 완료! 정상 파밍으로 복귀합니다.")
        self.status_signal.emit("펫 합성 완료 -> 파밍 재개")

    def _check_adb_app_crashed(self) -> tuple[bool, str]:
        """
        아이콘 이미지 매칭에 의존하지 않고 ADB로 UnderDark 앱이 종료(튕김)되었거나
        홈 런처(LDPlayer / BlueStacks Air 등)로 빠져나갔는지 직접 판별.
        """
        if not hasattr(self.adb, "get_foreground_package"):
            return False, ""

        game_pkg = self.adb.find_game_package()
        fg_pkg = self.adb.get_foreground_package()
        if not fg_pkg:
            return False, ""

        if fg_pkg.lower() == game_pkg.lower():
            return False, ""

        fg_lower = fg_pkg.lower()
        launcher_keywords = (
            "launcher", "bluestacks", "appmart", "home", "trebuchet", "ldlauncher"
        )
        if any(kw in fg_lower for kw in launcher_keywords):
            return True, f"홈/런처 화면 감지 ({fg_pkg})"

        running = self.adb.is_app_running(game_pkg)
        if running is False:
            return True, f"게임 프로세스 종료 확인 (현재 포그라운드: {fg_pkg})"

        return False, ""

    def run(self):
        self.running = True
        if self.mode == self.MODE_STAGE_FARMING:
            mode_text = "일반 810 스테이지 노가다 파밍 (Final Wave 포기)"
        elif self.mode == self.MODE_FULL_AUTO:
            mode_text = "통합 던전 자동 반복"
        else:
            mode_text = "단독 핀코드 자동 해제"

        self.log_signal.emit(f"[시작] {mode_text} 매크로 워커 구동 시작")
        self.status_signal.emit("모니터링 중...")

        loop_counter = 0

        while self.running:
            loop_counter += 1
            if loop_counter % 50 == 0:
                gc.collect()

            try:
                frame = self.adb.capture_screen()
                if frame is None:
                    self.status_signal.emit("캡처 대기 중 (디바이스 확인 필요)")
                    time.sleep(1.0)
                    continue

                fh, fw = frame.shape[:2]

                # 1. 최우선 순위: 매크로 방지 4자리 핀코드 팝업 감지
                detected_popup, p_score, loc = self.detector.detect_popup(frame)
                if detected_popup:
                    # 핀코드 자동 해제 옵션이 꺼져있고 단독 핀코드 모드가 아닌 경우 (사용자 수동 해결 대기)
                    if not self.auto_solve_pin and self.mode != self.MODE_PIN_ONLY:
                        self.current_state = "POPUP_MANUAL"
                        self.status_signal.emit("매크로 방지창 감지됨 (수동 입력 대기 중)")
                        debug_frame = self.detector.draw_debug_overlay(frame, True, p_score, state="POPUP", popup_loc=loc)
                        self.frame_signal.emit(debug_frame)
                        time.sleep(1.0)
                        continue

                    self.current_state = "POPUP"
                    self.status_signal.emit("매크로 방지창 감지됨!")
                    self.log_signal.emit(f"[감지] 매크로 방지 팝업 발견 (신뢰도: {p_score*100:.1f}%)")

                    # 1) 숫자 영역 크롭 및 인식 (팝업 위치 기반)
                    crop, _ = self.detector.get_display_crop(frame, loc)
                    code, conf = self.ocr.recognize(crop)
                    self.log_signal.emit(f"[OCR] 인식된 4자리 번호: [{code}] (신뢰도: {conf*100:.1f}%)")

                    # 프리뷰 오버레이 전송
                    debug_frame = self.detector.draw_debug_overlay(frame, True, p_score, code, state="POPUP", popup_loc=loc)
                    self.frame_signal.emit(debug_frame)

                    if len(code) == 4 and code.isdigit():
                        self.status_signal.emit(f"키패드 입력 중: {code}")
                        self.log_signal.emit(f"[입력] 키패드 자동 터치 시작: {code}")

                        # 2) 키패드 연속 터치 (팝업 위치 기반 정밀 터치)
                        for ch in code:
                            if not self.running:
                                break
                            digit = int(ch)
                            tx, ty = self.detector.get_keypad_coords(digit, fw, fh, loc)
                            self.adb.tap(tx, ty)
                            time.sleep(self.tap_delay)

                        # 3) 입력 결과 검증
                        time.sleep(0.35)
                        verify_frame = self.adb.capture_screen()
                        if verify_frame is not None:
                            still_detected, _, _ = self.detector.detect_popup(verify_frame)
                            if not still_detected:
                                self.stats["success_count"] += 1
                                self.stats["last_code"] = code
                                self.stats["last_time"] = datetime.datetime.now().strftime("%H:%M:%S")
                                self.stat_signal.emit(self.stats)

                                self.log_signal.emit(f"[성공] 매크로 방지 번호 [{code}] 해제 완료! (누적 {self.stats['success_count']}회)")
                                self.status_signal.emit(f"해제 성공! ({code})")

                                # 해제 후 [확인] 버튼 자동 클릭 옵션 처리
                                if self.auto_click_confirm:
                                    time.sleep(0.4)
                                    confirm_frame = self.adb.capture_screen()
                                    if confirm_frame is not None:
                                        found, c_score, (cx, cy) = self.detector.detect_confirm_button(confirm_frame)
                                        self.adb.tap(cx, cy)
                                        if found:
                                            self.log_signal.emit(f"[확인] 감지된 [확인] 버튼 터치 완료! ({cx}, {cy})")
                                        else:
                                            self.log_signal.emit(f"[확인] [확인] 버튼 기본 위치 터치 완료! ({cx}, {cy})")

                                time.sleep(0.6)
                                continue
                            else:
                                self.log_signal.emit("[경고] 입력 후에도 팝업이 유지됨. 재시도 예정")
                                self.stats["retry_count"] += 1
                                self.stat_signal.emit(self.stats)
                    else:
                        self.log_signal.emit(f"[오류] 4자리 숫자 분할 실패 (인식값: {code})")
                        time.sleep(0.5)
                        continue

                # 단독 핀코드 모드인 경우 여기서 종료 후 대기
                if self.mode == self.MODE_PIN_ONLY:
                    self.current_state = "MONITORING"
                    debug_frame = self.detector.draw_debug_overlay(frame, False, p_score, state="MONITORING")
                    self.frame_signal.emit(debug_frame)
                    self.status_signal.emit("모니터링 중...")
                    time.sleep(self.check_interval)
                    continue

                # 2. 화면 상태 판별 (현재 모드 및 목표 스테이지 전달)
                state, score, target_coords = self.detector.analyze_screen_state(
                    frame, mode=self.mode, target_stage=self.target_stage
                )
                self.current_state = state
                self.stats["current_state"] = state

                # 동일 상태 연속 지속 횟수 추적
                if state == self.last_state:
                    self.state_repeat_count += 1
                else:
                    self.last_state = state
                    self.state_repeat_count = 0

                # UNKNOWN 상태가 2회 이상 지속되면 ADB로 앱 튕김/홈 이탈 여부를 직접 교차 검증
                # (BlueStacks Air 등 런처 아이콘 크기/모양이 달라도 100% 튕김 감지)
                adb_crash_reason = ""
                if state == "UNKNOWN" and self.state_repeat_count >= 2 and (self.state_repeat_count % 3 == 2):
                    is_adb_crashed, adb_crash_reason = self._check_adb_app_crashed()
                    if is_adb_crashed:
                        state = "APP_CRASHED"
                        target_coords = None
                        self.current_state = state
                        self.stats["current_state"] = state

                # 프리뷰 오버레이 송출
                debug_frame = self.detector.draw_debug_overlay(
                    frame, False, score, state=state, target_coords=target_coords
                )
                self.frame_signal.emit(debug_frame)

                # ==========================================================
                # [공통 처리] 게임 비정상 종료 (앱 튕김) -> ADB 직접 실행 우선, 실패 시 아이콘 터치 폴백
                # ==========================================================
                if state == "APP_CRASHED":
                    if not self.auto_restart_app:
                        self.status_signal.emit("앱 튕김 감지됨 (재시작 옵션 비활성)")
                        self.log_signal.emit("[앱 튕김] 게임 비정상 종료가 감지되었으나 '앱 튕김 시 자동 재시작' 옵션이 꺼져 있어 대기합니다.")
                        time.sleep(1.0)
                        continue

                    self.status_signal.emit("게임 튕김 감지! 재실행 중...")
                    launched_via_adb = False
                    if hasattr(self.adb, "launch_app"):
                        launched_via_adb = self.adb.launch_app()

                    if launched_via_adb:
                        reason_tag = f" ({adb_crash_reason})" if adb_crash_reason else ""
                        self.log_signal.emit(f"[앱 재실행] 게임 비정상 종료 감지{reason_tag} -> ADB로 UnderDark 앱 직접 재실행 완료")
                    else:
                        cx, cy = target_coords if target_coords else (int(0.60 * fw), int(0.22 * fh))
                        self.log_signal.emit(f"[앱 재실행] 게임 비정상 종료(튕김) 감지 -> UnderDark 아이콘 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)

                    self.game_start_time = None
                    self.initial_cmd_executed = False
                    self.dungeon_scroll_count = 0

                    # 게임 재실행 및 로딩 대기 (약 7초 카운트다운)
                    self.log_signal.emit("[앱 재실행] 게임 구동 및 로딩 대기 시작...")
                    for remaining in range(7, 0, -1):
                        if not self.running:
                            break
                        self.status_signal.emit(f"게임 로딩 대기 중... ({remaining}초)")
                        time.sleep(1.0)

                    self.log_signal.emit("[앱 재실행] 로딩 대기 완료! 정상 모니터링 재개")
                    continue

                # ==========================================================
                # [공통 처리] 랭킹/정기 보상 상자 팝업 -> [받기] 버튼 터치
                # ==========================================================
                if state == "RANK_REWARD":
                    cx, cy = target_coords if target_coords else (fw // 2, int(0.690 * fh))
                    self.status_signal.emit("랭킹/시즌 보상: [받기] 클릭")
                    self.log_signal.emit(f"[보상상자] 정기/랭킹 보상 상자 감지! [받기] 버튼 터치 ({cx}, {cy})")
                    self.adb.tap(cx, cy)
                    time.sleep(1.2)
                    continue

                # ==========================================================
                # [모드 분기 1] 일반 810 스테이지 노가다 파밍 루프
                # ==========================================================
                if self.mode == self.MODE_STAGE_FARMING:
                    # [상태 1] 포기 확인 팝업 ("게임을 종료하시겠습니까?" -> [예] 클릭)
                    if state == "GIVEUP_CONFIRM":
                        cx, cy = target_coords if target_coords else (int(0.385 * fw), int(0.598 * fh))
                        self.status_signal.emit("포기 확인: [예] 클릭")
                        self.log_signal.emit(f"[포기하기] 게임 종료 확인 팝업 감지 -> [예] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        time.sleep(1.0)
                        continue

                    # [상태 2] 인게임 설정창 ([포기하기] 버튼 클릭)
                    elif state == "GIVEUP_SETTING":
                        cx, cy = target_coords if target_coords else (int(0.407 * fw), int(0.598 * fh))
                        self.status_signal.emit("설정창: [포기하기] 클릭")
                        self.log_signal.emit(f"[설정] 인게임 설정창 감지 -> [포기하기] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        time.sleep(0.8)
                        continue

                    # [상태 3] Final Wave 보스 등장 -> 우측 상단 햄버거 메뉴 터치
                    elif state == "FINAL_WAVE":
                        scale = fh / 960.0
                        cx, cy = target_coords if target_coords else (fw - int(68 * scale), int(0.077 * fh))
                        self.status_signal.emit("Final Wave 보스 등장! 설정 메뉴 클릭")
                        self.log_signal.emit(f"[보스등장] Final Wave 도달! 우측 상단 햄버거 메뉴 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        time.sleep(0.8)
                        continue

                    # [상태 4] 게임 오버 화면 ([광고 x2] 클릭) -> 게임 종료 시점 1회 완료 카운트
                    elif state == "GAMEOVER":
                        cx, cy = target_coords if target_coords else (fw // 2, int(0.6448 * fh))
                        self.status_signal.emit("게임 오버: [광고 x2] 클릭")
                        self.log_signal.emit(f"[게임오버] 패배(게임 종료) 감지 -> [광고 x2] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        self.initial_cmd_executed = False

                        # 게임 종료(패배) 시점 즉시 던전 완료 카운트 기록
                        self._record_dungeon_completion(mode_tag=f"{self.target_stage} 노가다")
                        self.game_start_time = None

                        # 목표 횟수 달성 여부 체크
                        if self.max_runs > 0 and self.stats["dungeon_count"] >= self.max_runs:
                            self.log_signal.emit(f"[목표 달성] 설정된 반복 횟수({self.max_runs}회)를 모두 완료하여 매크로를 종료합니다.")
                            self.status_signal.emit("목표 완료됨")
                            self.running = False
                            break

                        time.sleep(1.8)
                        continue

                    # [상태 5] 획득 보상 화면 ([확인] 클릭) -> 보상 확인 (GAMEOVER 누락 시 대비 카운트 보장)
                    elif state == "REWARD":
                        cx, cy = target_coords if target_coords else (fw // 2, int(0.8115 * fh))
                        self.status_signal.emit("보상 화면: [확인] 클릭")
                        self.log_signal.emit(f"[보상] 획득 보상 화면 감지! [확인] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)

                        # GAMEOVER를 거치지 않고 바로 REWARD가 떴을 경우를 대비한 카운트 기록 (이미 카운트되었으면 중복 방지)
                        self._record_dungeon_completion(mode_tag=f"{self.target_stage} 노가다")
                        self.game_start_time = None
                        self.initial_cmd_executed = False

                        # 목표 횟수 달성 여부 체크
                        if self.max_runs > 0 and self.stats["dungeon_count"] >= self.max_runs:
                            self.log_signal.emit(f"[목표 달성] 설정된 반복 횟수({self.max_runs}회)를 모두 완료하여 매크로를 종료합니다.")
                            self.status_signal.emit("목표 완료됨")
                            self.running = False
                            break

                        time.sleep(1.4)
                        continue

                    # [상태 6] 목표 스테이지 확인 완료 -> [입장] 터치 (소탕 아님!)
                    elif state in ("STAGE_810_READY", "STAGE_TARGET_READY"):
                        scale = fh / 960.0
                        default_enter = (fw // 2 + int(66 * scale), int(0.444 * fh))
                        cx, cy = target_coords if target_coords else default_enter
                        nav_msg = getattr(self.detector, "nav_status_msg", "")
                        if nav_msg:
                            self.log_signal.emit(nav_msg)
                        self.status_signal.emit(f"Stage {self.target_stage}: [입장] 클릭 (소탕 아님)")
                        self.log_signal.emit(f"[스테이지 {self.target_stage}] Stage {self.target_stage} 확인 완료! [입장] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        if hasattr(self.detector, "reset_stage_navigation"):
                            self.detector.reset_stage_navigation()
                        self.game_start_time = time.time()
                        self.initial_cmd_executed = False
                        self.round_counted = False  # 신규 라운드 시작 -> 카운트 플래그 리셋
                        time.sleep(2.5)  # 로딩 진입 대기
                        continue

                    # [상태 7] 던전 선택 창이지만 목표 스테이지가 아님 -> [<- 이전] 화살표 클릭
                    elif state == "STAGE_NEED_PREV":
                        scale = fh / 960.0
                        default_prev = (fw // 2 - int(135 * scale), int(0.370 * fh))
                        cx, cy = target_coords if target_coords else default_prev
                        nav_msg = getattr(self.detector, "nav_status_msg", "")
                        rem_steps = abs(getattr(self.detector, "nav_remaining_steps", 0))
                        est_stage = getattr(self.detector, "nav_estimated_stage", None)
                        if nav_msg:
                            self.log_signal.emit(nav_msg)
                        if est_stage is not None and rem_steps > 0:
                            self.status_signal.emit(f"Stage {est_stage} → {self.target_stage}: [<-] ({rem_steps}회 남음)")
                            self.log_signal.emit(f"[던전 이동] 현재(추정) Stage {est_stage} -> 목표 {self.target_stage}까지 [<- 이전] 터치 ({cx}, {cy}) [남은 이동: {rem_steps}회]")
                        else:
                            self.status_signal.emit(f"Stage {self.target_stage} 탐색: [<-] 화살표 클릭")
                            self.log_signal.emit(f"[던전] 기준 스테이지 탐색을 위해 [<- 이전] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        if hasattr(self.detector, "record_stage_step"):
                            self.detector.record_stage_step(-1)
                        time.sleep(0.75)
                        continue

                    # [상태 7-2] 던전 선택 창이지만 목표 스테이지가 아님 -> [-> 다음] 화살표 클릭
                    elif state == "STAGE_NEED_NEXT":
                        scale = fh / 960.0
                        default_next = (fw // 2 + int(135 * scale), int(0.370 * fh))
                        cx, cy = target_coords if target_coords else default_next
                        nav_msg = getattr(self.detector, "nav_status_msg", "")
                        rem_steps = abs(getattr(self.detector, "nav_remaining_steps", 0))
                        est_stage = getattr(self.detector, "nav_estimated_stage", None)
                        if nav_msg:
                            self.log_signal.emit(nav_msg)
                        if est_stage is not None and rem_steps > 0:
                            self.status_signal.emit(f"Stage {est_stage} → {self.target_stage}: [->] ({rem_steps}회 남음)")
                            self.log_signal.emit(f"[던전 이동] 현재(추정) Stage {est_stage} -> 목표 {self.target_stage}까지 [-> 다음] 터치 ({cx}, {cy}) [남은 이동: {rem_steps}회]")
                        else:
                            self.status_signal.emit(f"Stage {self.target_stage} 탐색: [->] 화살표 클릭")
                            self.log_signal.emit(f"[던전] 기준 스테이지 탐색을 위해 [-> 다음] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        if hasattr(self.detector, "record_stage_step"):
                            self.detector.record_stage_step(1)
                        time.sleep(0.75)
                        continue

                    # [상태 8] 던전 선택 창 상단 [일반] 탭 터치 필요
                    elif state == "STAGE_TAB_GENERAL":
                        if hasattr(self.detector, "reset_stage_navigation"):
                            self.detector.reset_stage_navigation()
                        cx, cy = target_coords if target_coords else (int(0.28 * fw), int(0.15 * fh))
                        self.status_signal.emit("던전 창: [일반] 탭 선택")
                        self.log_signal.emit(f"[던전] 상단 [일반] 탭 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        time.sleep(0.8)
                        continue

                    # [상태 9] 캠프 화면 -> [던전] 터치
                    elif state == "CAMP":
                        self.game_start_time = None
                        self.initial_cmd_executed = False

                        # 🐾 펫 자동 일괄 합성 주기 도달 또는 수동 요청 시 실행
                        should_synth = self.force_pet_synth or (
                            self.pet_synth_enabled and 
                            self.stats["dungeon_count"] > 0 and 
                            (self.stats["dungeon_count"] % self.pet_synth_interval == 0) and 
                            (self.last_pet_synth_round != self.stats["dungeon_count"])
                        )
                        if should_synth:
                            self.force_pet_synth = False
                            self.last_pet_synth_round = self.stats["dungeon_count"]
                            self._run_pet_synthesis(frame, fw, fh)
                            continue

                        cx, cy = target_coords if target_coords else (fw // 2, int(0.7396 * fh))
                        self.status_signal.emit("캠프 화면: [던전] 클릭")
                        self.log_signal.emit(f"[캠프] 중앙 하단 [던전] 버튼 터치 ({cx}, {cy})")
                        self.adb.tap(cx, cy)
                        time.sleep(1.2)
                        continue

                    # [상태 10] 인게임 일반 웨이브 진행 중 (1/16 ~ 15/16)
                    elif state == "IN_GAME":
                        if self.game_start_time:
                            elapsed = int(time.time() - self.game_start_time)
                            m, s = divmod(elapsed, 60)
                            self.stats["elapsed_battle"] = f"{m:02d}:{s:02d}"
                        else:
                            self.game_start_time = time.time()
                            self.stats["elapsed_battle"] = "00:00"

                        self.stat_signal.emit(self.stats)

                        # 전투 시작 시 1회 초기 커맨드 실행
                        if self.initial_cmd_enabled and not self.initial_cmd_executed:
                            self._execute_initial_command(fw, fh)

                        self.round_counted = False  # 전투 중 카운트 플래그 리셋
                        self.status_signal.emit(f"810 전투 진행 중... ({self.stats['elapsed_battle']})")
                        time.sleep(1.0)
                        continue

                    # [상태 11] 알 수 없음 / 로딩 중
                    else:
                        if self.game_start_time:
                            elapsed = int(time.time() - self.game_start_time)
                            m, s = divmod(elapsed, 60)
                            self.stats["elapsed_battle"] = f"{m:02d}:{s:02d}"
                            self.stat_signal.emit(self.stats)

                        self.status_signal.emit("화면 전환 / 로딩 대기 중...")
                        time.sleep(self.check_interval)
                        continue

                # ==========================================================
                # [모드 분기 2] 심연의 모래 구멍 자동 반복 루프 (기존 모드)
                # ==========================================================

                # ==========================================================
                # [상태 1] 획득 보상 화면 (REWARD) -> [확인] 클릭
                # ==========================================================
                if state == "REWARD":
                    cx, cy = target_coords if target_coords else (fw // 2, int(0.8115 * fh))
                    self.status_signal.emit("보상 화면: [확인] 클릭")
                    self.log_signal.emit(f"[보상] 획득 보상 화면 감지! [확인] 버튼 터치 ({cx}, {cy})")
                    self.adb.tap(cx, cy)

                    self._record_dungeon_completion(mode_tag="심연")
                    self.game_start_time = None
                    self.initial_cmd_executed = False
                    self.dungeon_scroll_count = 0
                    self._reset_tower_state()

                    # 목표 횟수 달성 여부 체크
                    if self.max_runs > 0 and self.stats["dungeon_count"] >= self.max_runs:
                        self.log_signal.emit(f"[목표 달성] 설정된 반복 횟수({self.max_runs}회)를 모두 완료하여 매크로를 종료합니다.")
                        self.status_signal.emit("목표 완료됨")
                        self.running = False
                        break

                    time.sleep(1.4)
                    continue

                # ==========================================================
                # [상태 2] 게임 오버 화면 (GAMEOVER) -> [광고 x2] 클릭
                # ==========================================================
                elif state == "GAMEOVER":
                    cx, cy = target_coords if target_coords else (fw // 2, int(0.6448 * fh))
                    self.status_signal.emit("게임 오버: [광고 x2] 클릭")
                    self.log_signal.emit(f"[게임오버] 패배 감지 -> [광고 x2] 버튼 터치 ({cx}, {cy})")
                    self.adb.tap(cx, cy)
                    self.initial_cmd_executed = False
                    self.dungeon_scroll_count = 0
                    self._reset_tower_state()

                    # 패배 종료 시점 즉시 1회 완료 카운트 기록
                    self._record_dungeon_completion(mode_tag="심연")
                    self.game_start_time = None

                    # 목표 횟수 달성 여부 체크
                    if self.max_runs > 0 and self.stats["dungeon_count"] >= self.max_runs:
                        self.log_signal.emit(f"[목표 달성] 설정된 반복 횟수({self.max_runs}회)를 모두 완료하여 매크로를 종료합니다.")
                        self.status_signal.emit("목표 완료됨")
                        self.running = False
                        break

                    time.sleep(1.8)
                    continue

                # ==========================================================
                # [상태 3] 던전 선택 팝업 (DUNGEON_POPUP) -> 랭킹 탭 & 심연 입장
                # ==========================================================
                elif state == "DUNGEON_POPUP":
                    # 먼저 화면에 '심연의 모래 구멍' 카드/타이틀이 실제로 보이는지 검사
                    is_abyss, a_score, abyss_coords = self.detector.detect_abyss_dungeon(frame)
                    
                    if is_abyss and a_score >= 0.75:
                        # 심연의 모래 구멍이 확실하게 감지됨 -> [입장] 터치!
                        ax, ay = abyss_coords
                        self.status_signal.emit("심연의 모래 구멍 [입장] 클릭")
                        self.log_signal.emit(f"[던전] '심연의 모래 구멍' 발견(신뢰도 {a_score*100:.1f}%) -> [입장] 터치 ({ax}, {ay})")
                        self.adb.tap(ax, ay)
                        self.game_start_time = time.time()
                        self.initial_cmd_executed = False
                        self.round_counted = False  # 신규 라운드 시작 -> 카운트 플래그 리셋
                        self.dungeon_scroll_count = 0
                        self._reset_tower_state()
                        time.sleep(2.5)  # 로딩 진입 대기
                    else:
                        # 아직 심연의 모래 구멍이 보이지 않음 -> 랭킹 탭 확인 후 아래로 스크롤
                        self.dungeon_scroll_count += 1

                        # 첫 스크롤 시작 시 또는 6회 이상 못 찾았을 때 [랭킹] 탭을 눌러 목록 상단으로 리셋
                        if self.dungeon_scroll_count == 1 or self.dungeon_scroll_count > 6:
                            self.status_signal.emit("랭킹 탭 선택")
                            rx, ry = target_coords if target_coords else (fw // 2 - int(73 * (fh / 960.0)), int(0.1385 * fh))
                            self.log_signal.emit(f"[던전] [랭킹] 탭 터치 ({rx}, {ry})")
                            self.adb.tap(rx, ry)
                            time.sleep(0.5)
                            if self.dungeon_scroll_count > 6:
                                self.dungeon_scroll_count = 1

                        # 스크롤: 화면 중앙에서 아래에서 위로 스와이프하여 목록 내리기
                        self.status_signal.emit(f"심연의 모래 구멍 탐색 스크롤 ({self.dungeon_scroll_count}회)")
                        self.log_signal.emit(f"[던전] 심연의 모래 구멍 탐색 중... 목록 스크롤 ({self.dungeon_scroll_count}회)")
                        center_x = fw // 2
                        self.adb.swipe(center_x, int(fh * 0.72), center_x, int(fh * 0.32), 350)
                        time.sleep(0.8)

                    continue

                # ==========================================================
                # [상태 4] 캠프 화면 (CAMP) -> [던전] 버튼 클릭
                # ==========================================================
                elif state == "CAMP":
                    self.game_start_time = None
                    self.initial_cmd_executed = False
                    self.dungeon_scroll_count = 0
                    self._reset_tower_state()

                    # 🐾 펫 자동 일괄 합성 주기 도달 또는 수동 요청 시 실행
                    should_synth = self.force_pet_synth or (
                        self.pet_synth_enabled and 
                        self.stats["dungeon_count"] > 0 and 
                        (self.stats["dungeon_count"] % self.pet_synth_interval == 0) and 
                        (self.last_pet_synth_round != self.stats["dungeon_count"])
                    )
                    if should_synth:
                        self.force_pet_synth = False
                        self.last_pet_synth_round = self.stats["dungeon_count"]
                        self._run_pet_synthesis(frame, fw, fh)
                        continue

                    cx, cy = target_coords if target_coords else (fw // 2, int(0.7396 * fh))
                    self.status_signal.emit("캠프 화면: [던전] 클릭")
                    self.log_signal.emit(f"[캠프] 중앙 하단 [던전] 버튼 터치 ({cx}, {cy})")
                    self.adb.tap(cx, cy)
                    time.sleep(1.2)  # 던전 팝업 오픈 대기
                    continue

                # ==========================================================
                # [상태 5] 인게임 화면 (IN_GAME) -> 전투 진행 대기 및 자동 타워 설치
                # ==========================================================
                elif state == "IN_GAME":
                    if self.game_start_time:
                        elapsed = int(time.time() - self.game_start_time)
                        m, s = divmod(elapsed, 60)
                        self.stats["elapsed_battle"] = f"{m:02d}:{s:02d}"
                    else:
                        self.game_start_time = time.time()
                        self.stats["elapsed_battle"] = "00:00"

                    self.stat_signal.emit(self.stats)

                    # 전투 시작 시 1회 초기 커맨드 실행
                    if self.initial_cmd_enabled and not self.initial_cmd_executed:
                        self._execute_initial_command(fw, fh)

                    self.round_counted = False  # 전투 중 카운트 플래그 리셋

                    # 🏰 심연 던전 자동 타워 설치 실행 (체크박스 활성화 및 이번 판 맵 만석 미도달 시)
                    if self.auto_place_tower and not self.tower_placement_done:
                        # 하단 타워 덱에 설치 대상 타워가 있을 때만 맵 빈 공간 탐색 수행
                        available_towers = self.detector.detect_available_towers(frame)
                        if available_towers:
                            plan = self.detector.plan_next_tower_placement(
                                frame, excluded_spots=self.placed_tower_spots
                            )
                            if plan is not None:
                                self.tower_no_plan_streak = 0
                                tw = plan["tower"]
                                sx, sy = plan["start_coords"]
                                dx, dy = plan["drop_coords"]
                                fx, fy = plan.get("drag_end_coords", (dx, dy))
                                rx1, ry1, rx2, ry2 = plan["drop_rect"]

                                # 프리뷰 오버레이에 타워 드래그 경로 및 설치 예정 격자 표시
                                vis = debug_frame.copy()
                                for ox1, oy1, ox2, oy2 in plan["obstacles"]:
                                    cv2.rectangle(vis, (ox1, oy1), (ox2, oy2), (0, 0, 200), 1)
                                cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 255, 120), 2)
                                cv2.circle(vis, (sx, sy), 18, (0, 200, 255), 2)
                                cv2.arrowedLine(vis, (sx, sy), (dx, dy), (0, 255, 120), 2, tipLength=0.06)
                                self.frame_signal.emit(vis)
                                del vis

                                self.status_signal.emit(
                                    f"타워 설치 ({len(self.placed_tower_spots)+1}/{self.max_tower_placements}): {tw['name']} -> ({dx}, {dy})"
                                )
                                self.log_signal.emit(
                                    f"[타워설치] 🏰 ({len(self.placed_tower_spots)+1}/{self.max_tower_placements}) "
                                    f"[{tw['name']} ({tw['grid_w']}*{tw['grid_h']})] 감지 "
                                    f"-> 외곽 빈자리 ({dx}, {dy})로 고속 드래그 설치 (터치점: {fx}, {fy})"
                                )
                                self.adb.swipe(sx, sy, fx, fy, 350)
                                # 한 번 시도한 위치(성공 또는 실패)는 이번 판이 끝날 때까지 영구 스킵하여 동일 위치 무한 재시도 방지
                                self.placed_tower_spots.append((dx, dy))
                                if len(self.placed_tower_spots) >= self.max_tower_placements:
                                    self.tower_placement_done = True
                                    self.log_signal.emit(
                                        f"[타워설치] 🏰 이번 판 최대 타워 설치 개수({self.max_tower_placements}개)에 도달하여 타워 탐지 및 설치를 종료합니다. (다음 판 자동 재개)"
                                    )
                                time.sleep(0.35)
                                continue
                            else:
                                # 하단 덱에 타워는 있는데 맵 전체에 빈 공간이 전혀 없는 상태가 3회 연속될 때 탐지 종료
                                self.tower_no_plan_streak += 1
                                if self.tower_no_plan_streak >= 3:
                                    self.tower_placement_done = True
                                    self.log_signal.emit(
                                        "[타워설치] 🏰 맵에 더 이상 타워를 배치할 빈 공간이 없어 이번 판 타워 탐지를 종료합니다. (다음 판 자동 재개)"
                                    )
                        else:
                            # 하단 덱이 비어 있는 경우(레벨업 보상 대기 중)에는 스트릭을 쌓지 않고 가볍게 패스
                            self.tower_no_plan_streak = 0

                    self.status_signal.emit(f"전투 진행 중... ({self.stats['elapsed_battle']})")
                    time.sleep(1.2)
                    continue

                # ==========================================================
                # [상태 6] 알 수 없음 / 로딩 중 (UNKNOWN)
                # ==========================================================
                else:
                    if self.game_start_time:
                        elapsed = int(time.time() - self.game_start_time)
                        m, s = divmod(elapsed, 60)
                        self.stats["elapsed_battle"] = f"{m:02d}:{s:02d}"
                        self.stat_signal.emit(self.stats)

                    self.status_signal.emit("화면 전환 / 로딩 대기 중...")
                    time.sleep(self.check_interval)

            except Exception as e:
                self.log_signal.emit(f"[에러] 모니터링 루프 오류: {e}")
                gc.collect()
                time.sleep(1.0)

        self.log_signal.emit("[중지] 매크로가 중지되었습니다.")
        self.status_signal.emit("중지됨")
