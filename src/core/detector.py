import os
import glob
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
from .resources import get_resource_path

class PopupDetector:
    """
    Underdark 게임의 매크로 방지 팝업 감지 및 자동 던전 반복 파밍을 위한 화면 분석기
    (멀티 해상도 및 1:1, 9:16, 16:9 가로/세로 커스텀 해상도 완벽 적응형)
    """
    def __init__(self, template_path: Optional[str] = None):
        if template_path is None:
            template_path = get_resource_path(os.path.join("assets", "templates", "template_title.png"))
            
        self.template_path = template_path
        self._template_gray_cache: Dict[int, np.ndarray] = {}
        self.template = self._load_template(template_path)
        
        # 템플릿 로드
        self.template_confirm = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_confirm.png")))
        self.template_camp_dungeon = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_camp_dungeon.png")))
        self.template_tab_ranking = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tab_ranking.png")))
        self.template_abyss_card = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_abyss_card.png")))
        self.template_abyss_title = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_abyss_title.png")))
        self.template_abyss_enter = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_abyss_enter.png")))
        self.template_gameover_defeat = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_gameover_defeat.png")))
        self.template_gameover_ad = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_gameover_ad.png")))
        self.template_reward_title = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_reward_title.png")))
        self.template_ingame_menu = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_ingame_menu.png")))
        
        # 810 스테이지 노가다 파밍용 신규 템플릿 로드
        self.template_tab_general = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tab_general.png")))
        self.template_stage_810_text = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_810_text.png")))
        self.template_stage_810_kr = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_810_kr.png")))
        self.template_stage_811_text = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_811_text.png")))
        self.template_stage_arrow_left = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_arrow_left.png")))
        self.template_stage_arrow_right = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_arrow_right.png")))
        self.template_stage_enter_btn = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_enter_btn.png")))
        self.template_stage_sweep_btn = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_stage_sweep_btn.png")))
        self.template_final_wave = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_final_wave.png")))
        self.template_final_wave_kr = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_final_wave_kr.png")))
        self.template_btn_giveup = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_giveup.png")))
        self.template_btn_yes = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_yes.png")))
        
        # 앱 비정상 종료(튕김) 감지용 런처 UnderDark 아이콘 템플릿
        self.template_app_icon = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_app_icon.png")))

        # 펫 자동 일괄 합성용 템플릿 로드
        self.template_tab_inventory = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tab_inventory.png")))
        self.template_tab_pet = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tab_pet.png")))
        self.template_btn_pet_synth = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_pet_synth.png")))
        self.template_btn_batch_synth = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_batch_synth.png")))
        self.template_btn_cancel_synth = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_cancel_synth.png")))
        self.template_batch_arrow_left = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_batch_arrow_left.png")))
        self.template_tier_legend = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tier_legend.png")))
        self.template_btn_batch_confirm = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_batch_confirm.png")))
        self.template_tab_camp = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tab_camp.png")))
        
        # 정기/랭킹/주간 보상 상자 [받기] 팝업 템플릿 로드
        self.template_btn_claim = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_btn_claim.png")))
        self.template_rank_reward_title = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_rank_reward_title.png")))

        # 🔢 일반 스테이지 노가다용 0~9 개별 숫자 템플릿 로드 (해상도별 변형 포함)
        self.stage_digits: Dict[int, list] = {i: [] for i in range(10)}
        tpl_dir = get_resource_path(os.path.join("assets", "templates"))
        for num in range(10):
            matches = glob.glob(os.path.join(tpl_dir, f"stage_digit_{num}*.png"))
            for p in matches:
                img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.stage_digits[num].append(img)

        # 🧭 스테이지 탐색 계획(Planner) 및 크로스체크 상태 변수
        self.nav_anchor_stage: Optional[int] = None
        self.nav_estimated_stage: Optional[int] = None
        self.nav_remaining_steps: int = 0
        self.nav_last_target: Optional[int] = None
        self.nav_step_pending: int = 0
        self.nav_outlier_stage: Optional[int] = None
        self.nav_status_msg: str = ""

        # 🏰 심연 던전 자동 타워 설치용 5종 타워 및 장애물(돌덩이/나무상자) 템플릿 로드
        self.template_tower_rocket = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tower_rocket.png")))
        self.template_tower_hamster = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tower_hamster.png")))
        self.template_tower_penguin = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tower_penguin.png")))
        self.template_tower_crow = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tower_crow.png")))
        self.template_tower_sniper = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_tower_sniper.png")))
        self.template_obstacle_stone = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_obstacle_stone.png")))
        self.template_obstacle_wood = self._load_template(get_resource_path(os.path.join("assets", "templates", "template_obstacle_wood.png")))

        self.tower_specs = [
            {"key": "rocket", "name": "로켓타워", "grid_w": 3, "grid_h": 3, "template": self.template_tower_rocket},
            {"key": "hamster", "name": "햄스터타워", "grid_w": 2, "grid_h": 2, "template": self.template_tower_hamster},
            {"key": "penguin", "name": "펭귄타워", "grid_w": 2, "grid_h": 2, "template": self.template_tower_penguin},
            {"key": "crow", "name": "까마귀타워", "grid_w": 3, "grid_h": 3, "template": self.template_tower_crow},
            {"key": "sniper", "name": "저격수타워", "grid_w": 3, "grid_h": 2, "template": self.template_tower_sniper},
        ]

        # 최근 감지된 팝업 타이틀 좌상단 좌표 (x, y) 및 감지 스케일 캐시
        self.last_popup_loc: Optional[Tuple[int, int]] = None
        self.last_popup_scale: float = 1.0

        # 키패드 상대 비율 좌표 (폴백용)
        self.keypad_ratios: Dict[int, Tuple[float, float]] = {
            1: (0.1889, 0.5146),
            2: (0.3426, 0.5146),
            3: (0.4963, 0.5146),
            4: (0.6481, 0.5146),
            5: (0.8019, 0.5146),
            6: (0.1889, 0.5990),
            7: (0.3426, 0.5990),
            8: (0.4963, 0.5990),
            9: (0.6481, 0.5990),
            0: (0.8019, 0.5990),
        }
        
        self.display_box_ratio = (0.2685, 0.4010, 0.7130, 0.4583)
        self.confirm_button_ratio = (0.5000, 0.8115)
        self.camp_dungeon_ratio = (0.5000, 0.7396)
        self.tab_ranking_ratio = (0.4200, 0.1385)
        self.abyss_enter_ratio = (0.5000, 0.7063)
        self.gameover_ad_ratio = (0.5000, 0.6448)

    def _load_template(self, path: str) -> Optional[np.ndarray]:
        if not os.path.exists(path):
            return None
        tpl = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if tpl is not None:
            self._template_gray_cache[id(tpl)] = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        return tpl

    def match_template(self, frame: np.ndarray, template: Optional[np.ndarray], 
                       roi: Optional[Tuple[float, float, float, float]] = None, 
                       threshold: float = 0.80) -> Tuple[bool, float, Tuple[int, int]]:
        """
        해상도 적응형 템플릿 매칭 공통 유틸 함수
        (1.0x 원본 크기 및 세로 비율 scale = fh / 960.0 멀티 스케일 탐색 지원, 메모리 누수 방지 및 예외 복구)
        반환: (일치여부, 유사도점수, 중심좌표(cx, cy))
        """
        if template is None or frame is None:
            return False, 0.0, (0, 0)

        fh, fw = frame.shape[:2]
        th, tw = template.shape[:2]

        if roi:
            rx1, ry1, rx2, ry2 = roi
            x1, y1 = max(0, int(rx1 * fw)), max(0, int(ry1 * fh))
            x2, y2 = min(fw, int(rx2 * fw)), min(fh, int(ry2 * fh))
            search_img = frame[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            search_img = frame
            offset_x, offset_y = 0, 0

        fgray = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)
        tgray = self._template_gray_cache.get(id(template))
        if tgray is None:
            tgray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            self._template_gray_cache[id(template)] = tgray

        scale_candidates = sorted(list(set([1.0, round(fh / 960.0, 3)])))
        best_val = -1.0
        best_loc = (0, 0)
        best_w, best_h = tw, th

        for s in scale_candidates:
            stw = max(1, int(tw * s))
            sth = max(1, int(th * s))
            if search_img.shape[0] < sth or search_img.shape[1] < stw:
                continue
            scaled_tpl = cv2.resize(tgray, (stw, sth)) if abs(s - 1.0) > 0.03 else tgray
            try:
                res = cv2.matchTemplate(fgray, scaled_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                del res
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
                    best_w, best_h = stw, sth
            except cv2.error:
                import gc
                gc.collect()

        cx = offset_x + best_loc[0] + best_w // 2
        cy = offset_y + best_loc[1] + best_h // 2
        is_matched = (best_val >= threshold)

        return is_matched, float(best_val), (cx, cy)

    def detect_popup(self, frame: np.ndarray, threshold: float = 0.78) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """
        화면에서 매크로 방지 팝업 등장 여부 판별 (멀티 스케일 적응형, 메모리 절약 ROI 탐색)
        반환: (감지여부, 유사도점수, 템플릿좌표(x, y))
        """
        if self.template is None or frame is None:
            return False, 0.0, None

        fh, fw = frame.shape[:2]
        th, tw = self.template.shape[:2]

        # 팝업 타이틀은 화면 상단~중단(15%~65%) 영역에만 출현하므로 불필요한 전체 화면 연산 방지
        y_offset = int(0.15 * fh)
        search_img = frame[y_offset:int(0.65 * fh), :]
        frame_gray = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)
        tgray = self._template_gray_cache.get(id(self.template))
        if tgray is None:
            tgray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)

        # 후보 스케일: 1.0 (원본), 세로/가로 비율 기반 스케일
        scale_candidates = [1.0, fh / 960.0, fw / 540.0, fw / 960.0]
        scales = sorted(list(set([round(s, 3) for s in scale_candidates if 0.4 <= s <= 1.8])))

        best_val = -1.0
        best_loc = None
        best_scale = 1.0

        for s in scales:
            stw = max(1, int(tw * s))
            sth = max(1, int(th * s))
            if stw > fw or sth > search_img.shape[0]:
                continue
            scaled_tpl = cv2.resize(tgray, (stw, sth)) if abs(s - 1.0) > 0.03 else tgray
            try:
                res = cv2.matchTemplate(frame_gray, scaled_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                del res
                if max_val > best_val:
                    best_val = max_val
                    best_loc = (max_loc[0], max_loc[1] + y_offset)
                    best_scale = s
            except cv2.error:
                import gc
                gc.collect()

        is_detected = (best_val >= threshold)
        if is_detected:
            self.last_popup_loc = best_loc
            self.last_popup_scale = best_scale
        return is_detected, float(best_val), best_loc

    def get_display_crop(self, frame: np.ndarray, popup_loc: Optional[Tuple[int, int]] = None) -> Tuple[Optional[np.ndarray], Tuple[int, int, int, int]]:
        """
        화면에서 숫자 디스플레이 박스 영역을 동적으로 크롭하여 반환
        popup_loc가 주어지면 해당 타이틀 위치를 기준으로 절대적 위치 계산
        """
        if frame is None:
            return None, (0, 0, 0, 0)
        fh, fw = frame.shape[:2]
        loc = popup_loc or self.last_popup_loc
        scale = getattr(self, "last_popup_scale", 1.0) if loc is not None else (fh / 960.0)

        if loc is not None:
            tx, ty = loc
            # 템플릿 타이틀 가로 430 기준 중심점
            cx = tx + int(215 * scale)
            y1 = max(0, ty + int(46 * scale))
            y2 = min(fh, ty + int(112 * scale))
            box_half_w = int(128 * scale)
            x1 = max(0, cx - box_half_w)
            x2 = min(fw, cx + box_half_w)
        else:
            cx = fw // 2
            y1 = max(0, int(0.395 * fh))
            y2 = min(fh, int(0.485 * fh))
            box_half_w = int(128 * scale)
            x1 = max(0, cx - box_half_w)
            x2 = min(fw, cx + box_half_w)

        crop = frame[y1:y2, x1:x2].copy()
        return crop, (x1, y1, x2, y2)

    def get_keypad_coords(self, digit: int, width: int, height: int, popup_loc: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:
        """
        특정 숫자에 해당하는 키패드 터치 좌표 (x, y) 반환.
        팝업 위치(popup_loc)를 기반으로 화면 비율/해상도에 관계없이 정밀 계산.
        """
        loc = popup_loc or self.last_popup_loc
        scale = getattr(self, "last_popup_scale", 1.0) if loc is not None else (height / 960.0)

        if loc is not None:
            tx, ty = loc
            cx = tx + int(215 * scale)
            r1 = ty + int(159 * scale)
            r2 = ty + int(240 * scale)
        else:
            cx = width // 2
            r1 = int(0.5146 * height)
            r2 = int(0.5990 * height)

        spacing = int(83 * scale)

        if digit in [1, 2, 3, 4, 5]:
            col_offset = digit - 3  # 1->-2, 2->-1, 3->0, 4->1, 5->2
            return int(cx + col_offset * spacing), int(r1)
        else:
            col_idx = (digit if digit != 0 else 10) - 8  # 6->-2, 7->-1, 8->0, 9->1, 0->2
            return int(cx + col_idx * spacing), int(r2)

    def get_confirm_coords(self, width: int, height: int) -> Tuple[int, int]:
        """성공 화면 확인 버튼의 기본 중심 좌표 (x, y) 반환"""
        return int(width * 0.5), int(0.8115 * height)

    def detect_confirm_button(self, frame: np.ndarray, threshold: float = 0.80) -> Tuple[bool, float, Tuple[int, int]]:
        """화면에서 [확인] 버튼 존재 여부 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = fw // 2
        default_cy = int(0.8115 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_confirm, roi=(0.10, 0.60, 0.90, 0.95), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_camp(self, frame: np.ndarray, threshold: float = 0.80) -> Tuple[bool, float, Tuple[int, int]]:
        """캠프 화면 감지 및 중앙 하단 [던전] 버튼 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = fw // 2
        default_cy = int(0.7396 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_camp_dungeon, roi=(0.10, 0.55, 0.90, 0.90), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_dungeon_popup(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """던전 선택 팝업 감지 및 상단 [랭킹] 탭 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        default_cx = fw // 2 - int(73 * scale)
        default_cy = int(0.1385 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tab_ranking, roi=(0.05, 0.05, 0.85, 0.25), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_abyss_dungeon(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """
        던전 팝업 내 '심연의 모래 구멍' 및 [입장] 버튼 감지.
        다른 던전 버튼을 잘못 누르지 않도록 반드시 '심연의 모래 구멍' 카드/타이틀이 일치할 때만 True 반환.
        반환: (감지여부, 유사도점수, [입장] 버튼 중심좌표(cx, cy))
        """
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        default_cx = fw // 2
        default_cy = int(0.7063 * fh)

        # 1. '심연의 모래 구멍' 전체 카드 템플릿 검사 (가장 확실함)
        if self.template_abyss_card is not None:
            matched_card, c_score, (ccx, ccy) = self.match_template(
                frame, self.template_abyss_card, threshold=threshold
            )
            if matched_card:
                c_sth = int(self.template_abyss_card.shape[0] * scale)
                c_stw = int(self.template_abyss_card.shape[1] * scale)
                card_x = ccx - c_stw // 2
                card_y = ccy - c_sth // 2
                # 카드 내부 [입장] 버튼 상대 위치: (189, 204)
                enter_x = card_x + int(189 * scale)
                enter_y = card_y + int(204 * scale)
                return True, c_score, (enter_x, enter_y)

        # 2. '심연의 모래 구멍' 타이틀 검사
        matched_title, t_score, (tcx, tcy) = self.match_template(
            frame, self.template_abyss_title, threshold=threshold
        )
        if matched_title:
            # 타이틀이 감지되었을 때만 그 아래 입장 버튼 검사
            matched_enter, e_score, (ecx, ecy) = self.match_template(
                frame, self.template_abyss_enter, roi=(0.10, 0.45, 0.90, 0.85), threshold=threshold
            )
            if matched_enter:
                return True, max(t_score, e_score), (ecx, ecy)
            else:
                return True, t_score, (tcx, tcy + int(160 * scale))

        # 심연의 모래 구멍이 화면에 없음 (다른 던전 오클릭 방지)
        return False, max(t_score, c_score if self.template_abyss_card is not None else 0.0), (default_cx, default_cy)

    def detect_gameover(self, frame: np.ndarray, threshold: float = 0.80) -> Tuple[bool, float, Tuple[int, int]]:
        """게임 오버(패배) 화면 감지 및 [광고 x2] 버튼 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = fw // 2
        default_cy = int(0.6448 * fh)

        # '패배' 타이틀 확인
        matched_defeat, d_score, _ = self.match_template(
            frame, self.template_gameover_defeat, roi=(0.10, 0.25, 0.90, 0.55), threshold=threshold
        )
        # '광고 x2' 버튼 확인
        matched_ad, a_score, (acx, acy) = self.match_template(
            frame, self.template_gameover_ad, roi=(0.10, 0.45, 0.90, 0.85), threshold=threshold
        )

        if matched_defeat or matched_ad:
            score = max(d_score, a_score)
            target_cx = acx if matched_ad else default_cx
            target_cy = acy if matched_ad else default_cy
            return True, score, (target_cx, target_cy)

        return False, max(d_score, a_score), (default_cx, default_cy)

    def detect_reward_screen(self, frame: np.ndarray, threshold: float = 0.80) -> Tuple[bool, float, Tuple[int, int]]:
        """획득 보상 화면 감지 및 하단 [확인] 버튼 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = fw // 2
        default_cy = int(0.8115 * fh)

        matched_title, t_score, _ = self.match_template(
            frame, self.template_reward_title, roi=(0.10, 0.10, 0.90, 0.35), threshold=threshold
        )
        matched_btn, b_score, (cx, cy) = self.detect_confirm_button(frame, threshold=threshold)

        if matched_title or (matched_btn and b_score >= 0.85):
            score = max(t_score, b_score)
            return True, score, (cx, cy)

        return False, max(t_score, b_score), (default_cx, default_cy)

    def detect_in_game(self, frame: np.ndarray, threshold: float = 0.70) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """게임 진행 중(전투) 화면 감지 (우측 상단 햄버거 메뉴 버튼 기반)"""
        matched_menu, m_score, menu_coords = self.match_template(
            frame, self.template_ingame_menu, roi=(0.60, 0.0, 1.0, 0.22), threshold=threshold
        )
        return matched_menu, m_score, menu_coords

    def detect_tab_general(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """던전 선택 팝업 상단 [일반] 탭 감지 및 클릭 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.28 * fw)
        default_cy = int(0.15 * fh)
        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tab_general, roi=(0.15, 0.10, 0.45, 0.22), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_stage_810(self, frame: np.ndarray) -> Tuple[bool, float, Tuple[int, int]]:
        """
        던전 선택 화면에서 중앙 스테이지가 Stage 810 (한글 '스테이지 810' 포함)인지 정밀 판별.
        (하위 호환성 유지용: detect_stage_target(frame, 810) 호출)
        """
        return self.detect_stage_target(frame, target_stage=810)

    def reset_stage_navigation(self) -> None:
        """스테이지 이동 계획 및 크로스체크 상태 초기화 (던전 입장/전투 진입/캠프 복귀 시)"""
        self.nav_anchor_stage = None
        self.nav_estimated_stage = None
        self.nav_remaining_steps = 0
        self.nav_step_pending = 0
        self.nav_outlier_stage = None
        self.nav_status_msg = ""

    def record_stage_step(self, direction: int) -> None:
        """
        화살표 클릭으로 스테이지를 1칸 이동했음을 기록.
        direction: -1 ([<- 이전] 클릭) 또는 +1 ([-> 다음] 클릭)
        """
        self.nav_step_pending = direction
        if self.nav_estimated_stage is not None:
            self.nav_estimated_stage += direction
            if self.nav_last_target is not None:
                self.nav_remaining_steps = self.nav_last_target - self.nav_estimated_stage

    def _match_single_stage_digit(self, crop: np.ndarray) -> Tuple[Optional[int], float]:
        """단일 숫자 크롭 이미지를 상하좌우 ±1px 시프트 허용 방식으로 0~9 템플릿과 대조"""
        ch, cw = crop.shape[:2]
        if ch <= 0 or cw <= 0:
            return None, -1.0

        padded = cv2.copyMakeBorder(crop, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        best_d: Optional[int] = None
        best_score: float = -1.0

        for d, tpls in self.stage_digits.items():
            for tpl in tpls:
                th_t, tw_t = tpl.shape[:2]
                if th_t <= padded.shape[0] and tw_t <= padded.shape[1]:
                    res = cv2.matchTemplate(padded, tpl, cv2.TM_CCOEFF_NORMED)
                    s1 = float(res.max())
                    if s1 > best_score:
                        best_score = s1
                        best_d = d
                resized_tpl = cv2.resize(tpl, (cw, ch), interpolation=cv2.INTER_NEAREST)
                res2 = cv2.matchTemplate(padded, resized_tpl, cv2.TM_CCOEFF_NORMED)
                s2 = float(res2.max())
                if s2 > best_score:
                    best_score = s2
                    best_d = d

        return best_d, best_score

    @staticmethod
    def _split_touching_digit_boxes(th: np.ndarray, raw_boxes: list) -> list:
        """인접한 두 숫자(예: '40', '44')가 1픽셀로 붙어 하나의 컨투어가 된 경우 수직 투영 최소점 기준으로 분할"""
        final_boxes = []
        for (x, y, w, h) in raw_boxes:
            if 3 <= w <= 13:
                final_boxes.append((x, y, w, h))
            elif 14 <= w <= 24:
                sub = th[y:y+h, x:x+w]
                mid = w // 2
                s_start = max(3, mid - 2)
                s_end = min(w - 3, mid + 3)
                if s_start < s_end:
                    col_sums = [int(np.sum(sub[:, c] > 0)) for c in range(s_start, s_end)]
                    split_off = s_start + int(np.argmin(col_sums))
                else:
                    split_off = mid
                final_boxes.append((x, y, split_off, h))
                final_boxes.append((x + split_off, y, w - split_off, h))
            elif 25 <= w <= 36:
                w1 = w // 3
                w2 = (w * 2) // 3
                final_boxes.append((x, y, w1, h))
                final_boxes.append((x + w1, y, w2 - w1, h))
                final_boxes.append((x + w2, y, w - w2, h))
        return final_boxes

    def detect_current_stage(self, frame: np.ndarray, min_digits: int = 3) -> Optional[int]:
        """
        던전 선택 화면의 스테이지 알약 UI에서 현재 표시된 스테이지 숫자를 정밀 인식.
        (다중 임계값 + 붙은 숫자 자동 분할 + ±1px 시프트 불변 매칭 + 부분 누락 방지 검증)
        """
        if frame is None or not self.stage_digits:
            return None

        fh, fw = frame.shape[:2]
        pill = frame[int(fh * 0.33):int(fh * 0.38), int(fw * 0.40):int(fw * 0.60)]
        if pill.size == 0:
            return None

        gray = cv2.cvtColor(pill, cv2.COLOR_BGR2GRAY)
        pw = pill.shape[1]

        best_stage: Optional[int] = None
        best_avg_score: float = -1.0

        for thresh_val in (140, 155, 170, 125):
            _, th = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            raw_boxes = [
                cv2.boundingRect(c) for c in contours
                if 8 <= cv2.boundingRect(c)[3] <= 16
                and 3 <= cv2.boundingRect(c)[2] <= 36
                and int(pw * 0.50) <= cv2.boundingRect(c)[0] <= int(pw * 0.85)
            ]
            raw_boxes.sort(key=lambda b: b[0])
            boxes = self._split_touching_digit_boxes(th, raw_boxes)

            if len(boxes) < min_digits:
                continue

            digits = []
            scores = []
            all_valid = True
            for (x, y, w, h) in boxes:
                crop = th[y:y+h, x:x+w]
                best_d, best_s = self._match_single_stage_digit(crop)
                # 하나라도 신뢰도 미달이면 일부 자릿수만 합쳐서 잘못된 숫자(예: 844 -> 84, 840 -> 80)를 만들지 않도록 즉시 기각
                if best_d is None or best_s < 0.55:
                    all_valid = False
                    break
                digits.append(str(best_d))
                scores.append(best_s)

            if all_valid and len(digits) == len(boxes) and len(digits) >= min_digits:
                avg_score = sum(scores) / len(scores)
                if avg_score > best_avg_score:
                    try:
                        best_stage = int("".join(digits))
                        best_avg_score = avg_score
                    except ValueError:
                        pass

        return best_stage

    def detect_stage_target(self, frame: np.ndarray, target_stage: int = 810) -> Tuple[bool, float, Tuple[int, int]]:
        """
        던전 선택 화면에서 중앙 스테이지가 목표 스테이지(target_stage, 기본 810)인지 판별.
        (Stage/스테이지 텍스트, 화살표 또는 소탕/입장 버튼 존재 검증)
        반환: (is_target, score, enter_btn_coords)
        """
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        # 기본 입장 버튼 좌표 (소탕 버튼 오른쪽: x ≈ 565, y ≈ 442)
        default_enter_x = fw // 2 + int(66 * scale)
        default_enter_y = int(0.444 * fh)

        # 1. 우측/좌측 화살표 존재 여부
        m_arr_r, s_arr_r, _ = self.match_template(
            frame, self.template_stage_arrow_right, roi=(0.50, 0.30, 0.85, 0.45), threshold=0.70
        )
        m_arr_l, s_arr_l, _ = self.match_template(
            frame, self.template_stage_arrow_left, roi=(0.25, 0.32, 0.50, 0.45), threshold=0.75
        )
        # 2. 소탕 버튼 존재 여부
        m_sw, s_sw, _ = self.match_template(
            frame, self.template_stage_sweep_btn, roi=(0.20, 0.35, 0.60, 0.55), threshold=0.70
        )
        # 3. [입장] 버튼 템플릿 매칭 (소탕 버튼 우측 또는 중앙 입장 버튼)
        m_ent, s_ent, ent_coords = self.match_template(
            frame, self.template_stage_enter_btn, roi=(0.25, 0.35, 0.80, 0.60), threshold=0.70
        )
        target_coords = ent_coords if m_ent else (default_enter_x, default_enter_y)

        # 던전 선택 화면 요소가 전혀 없으면 False
        if not (m_arr_r or m_arr_l or m_sw or m_ent):
            return False, 0.0, target_coords

        # 4. 숫자 템플릿 OCR로 현재 스테이지 직접 검증
        min_d = len(str(target_stage)) if target_stage >= 100 else 1
        cur_stage = self.detect_current_stage(frame, min_digits=min_d)
        if cur_stage is not None:
            if cur_stage == target_stage:
                return True, 0.99, target_coords
            elif target_stage != 810:
                return False, 0.99, target_coords

        # 5. 디폴트 810 스테이지: 고정밀 템플릿(영문/한글) 기반 100% 매칭 폴백
        if target_stage == 810:
            m_810_en, s_810_en, _ = self.match_template(
                frame, self.template_stage_810_text, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            m_810_kr, s_810_kr, _ = self.match_template(
                frame, self.template_stage_810_kr, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            s_810 = max(s_810_en, s_810_kr)

            m_811, s_811, _ = self.match_template(
                frame, self.template_stage_811_text, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.75
            )

            is_810 = (s_810 >= 0.85 and (s_810 > s_811 or s_810 >= 0.90)) and (m_arr_r or m_sw or m_ent)
            score = max(s_810, s_ent)
            return is_810, score, target_coords

        elif target_stage == 811:
            m_811, s_811, _ = self.match_template(
                frame, self.template_stage_811_text, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            is_811 = (s_811 >= 0.85) and (m_sw or m_ent or m_arr_r)
            score = max(s_811, s_ent)
            return is_811, score, target_coords

        else:
            return False, s_ent, target_coords

    def plan_stage_navigation(
        self, frame: np.ndarray, target_stage: int = 810
    ) -> Optional[Tuple[str, float, Tuple[int, int]]]:
        """
        던전 선택 창에서 현재 스테이지 인식, 목표 스테이지까지의 이동 횟수 계획 수립,
        OCR 미인식 시 기준 스테이지 기반 이동 추적 및 중간 스테이지 크로스체크 수행.
        던전 선택 창이 아니면 None 반환.
        """
        fh, fw = frame.shape[:2]
        scale = fh / 960.0

        is_arrow_l, arr_l_score, arr_l_coords = self.detect_stage_arrow_left(frame)
        is_arrow_r, arr_r_score, arr_r_coords = self.detect_stage_arrow_right(frame)
        m_sw, s_sw, _ = self.match_template(
            frame, self.template_stage_sweep_btn, roi=(0.20, 0.35, 0.60, 0.55), threshold=0.70
        )
        m_ent, s_ent, ent_coords = self.match_template(
            frame, self.template_stage_enter_btn, roi=(0.25, 0.35, 0.80, 0.60), threshold=0.70
        )

        # 던전 스테이지 카드 화면이 아닌 경우
        if not (is_arrow_l or is_arrow_r or m_sw or m_ent):
            return None

        default_enter = (fw // 2 + int(66 * scale), int(0.444 * fh)) if m_sw else (fw // 2, int(0.444 * fh))
        enter_coords = ent_coords if m_ent else default_enter

        if self.nav_last_target != target_stage:
            self.reset_stage_navigation()
            self.nav_last_target = target_stage

        # 1. 현재 화면의 스테이지 OCR 판독
        min_d = len(str(target_stage)) if target_stage >= 100 else 1
        cur_stage = self.detect_current_stage(frame, min_digits=min_d)

        # 810 / 811 전용 고정밀 템플릿 보조 확인
        if cur_stage is None:
            m_810_en, s_810_en, _ = self.match_template(
                frame, self.template_stage_810_text, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            m_810_kr, s_810_kr, _ = self.match_template(
                frame, self.template_stage_810_kr, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            m_811, s_811, _ = self.match_template(
                frame, self.template_stage_811_text, roi=(0.20, 0.30, 0.80, 0.45), threshold=0.85
            )
            if max(s_810_en, s_810_kr) >= 0.85 and max(s_810_en, s_810_kr) > s_811:
                cur_stage = 810
            elif s_811 >= 0.85:
                cur_stage = 811

        # 물리적 화살표 경계 검증:
        # 우측 화살표가 아예 없고 좌측 화살표만 있는 경우(최고 도달 스테이지, 예: 844)에는
        # 목표 스테이지보다 작은 번호(cur_stage < target_stage)로 잘못 읽혔다면 물리적으로 우측 이동이 불가능하므로 기각
        if cur_stage is not None and (not is_arrow_r and is_arrow_l) and cur_stage < target_stage:
            cur_stage = None

        step_was_pending = (self.nav_step_pending != 0)
        self.nav_step_pending = 0

        # 2. 계획 수립 및 중간 크로스체크
        if cur_stage is not None:
            if step_was_pending and self.nav_estimated_stage is not None:
                diff_from_est = abs(cur_stage - self.nav_estimated_stage)
                if diff_from_est <= 2:
                    # 정상 크로스체크 범위 이내
                    prev_est = self.nav_estimated_stage
                    self.nav_anchor_stage = cur_stage
                    self.nav_estimated_stage = cur_stage
                    self.nav_remaining_steps = target_stage - cur_stage
                    self.nav_outlier_stage = None

                    rem = self.nav_remaining_steps
                    if rem == 0:
                        self.nav_status_msg = f"[크로스체크 완료] 현재 Stage {cur_stage} 확인 -> 목표 Stage {target_stage} 도달!"
                    else:
                        d_str = "-> 다음" if rem > 0 else "<- 이전"
                        if cur_stage == prev_est:
                            self.nav_status_msg = f"[크로스체크 일치] Stage {cur_stage} 확인 (계획대로 이동 중, [{d_str}] {abs(rem)}회 남음)"
                        else:
                            self.nav_status_msg = f"[크로스체크 보정] Stage {cur_stage} 인식(예상 {prev_est}) -> 목표 {target_stage}까지 [{d_str}] {abs(rem)}회로 재조정"
                else:
                    # 1회 클릭 직후 예상치보다 3스테이지 이상 갑자기 튄 경우 -> 단일 프레임 OCR 오인식 필터링
                    if self.nav_outlier_stage == cur_stage:
                        # 2회 연속 동일 번호로 인식되면 실제 해당 스테이지로 기준 재설정
                        self.nav_anchor_stage = cur_stage
                        self.nav_estimated_stage = cur_stage
                        self.nav_remaining_steps = target_stage - cur_stage
                        self.nav_outlier_stage = None
                        rem = self.nav_remaining_steps
                        d_str = "-> 다음" if rem > 0 else "<- 이전"
                        self.nav_status_msg = f"[기준 재설정] Stage {cur_stage} 연속 확인 -> 목표 {target_stage}까지 [{d_str}] {abs(rem)}회 계획 수립"
                    else:
                        self.nav_outlier_stage = cur_stage
                        rem = target_stage - self.nav_estimated_stage
                        d_str = "-> 다음" if rem > 0 else "<- 이전"
                        self.nav_status_msg = f"[크로스체크 필터] 튀는 인식값({cur_stage}) 무시 -> 추정 Stage {self.nav_estimated_stage} 유지 ([{d_str}] {abs(rem)}회 남음)"
            else:
                # 최초 스테이지 인식 (또는 직접 호출): 즉시 이동 계획 수립
                self.nav_anchor_stage = cur_stage
                self.nav_estimated_stage = cur_stage
                self.nav_remaining_steps = target_stage - cur_stage
                self.nav_outlier_stage = None
                rem = self.nav_remaining_steps
                if rem == 0:
                    self.nav_status_msg = f"[스테이지 확인] 현재 Stage {cur_stage} 인식 -> 목표 Stage {target_stage} 일치!"
                else:
                    d_str = "-> 다음" if rem > 0 else "<- 이전"
                    self.nav_status_msg = f"[계획 수립] 현재 Stage {cur_stage} 인식 -> 목표 Stage {target_stage}까지 [{d_str}] {abs(rem)}회 이동 계획 수립"
        else:
            # 3. OCR 미인식 시: 기존 기준 스테이지 계획이 있으면 추정 스테이지로 진행, 없으면 인접 스테이지 탐색
            if self.nav_estimated_stage is not None:
                self.nav_remaining_steps = target_stage - self.nav_estimated_stage
                rem = self.nav_remaining_steps
                if rem == 0:
                    self.nav_status_msg = f"[계획 이동 완료] 기준 Stage {self.nav_anchor_stage}로부터 계획 이동 완료 -> 목표 Stage {target_stage} 도달 판정!"
                else:
                    d_str = "-> 다음" if rem > 0 else "<- 이전"
                    self.nav_status_msg = f"[계획 이동 중] 현재 스테이지 OCR 미인식 -> 기준 Stage {self.nav_anchor_stage} 기반 추정 Stage {self.nav_estimated_stage} ([{d_str}] {abs(rem)}회 남음)"
            else:
                # 아직 기준 스테이지를 모르는 상태에서 OCR도 안 된 경우 -> 가능한 화살표 방향으로 1칸 움직여서 기준 스테이지 획득
                if is_arrow_l and not is_arrow_r:
                    self.nav_status_msg = "[기준 스테이지 탐색] 현재 스테이지 미인식(우측 끝) -> [<- 이전] 1회 이동하여 기준 스테이지 확인"
                    return "STAGE_NEED_PREV", arr_l_score, arr_l_coords
                elif is_arrow_r and not is_arrow_l:
                    self.nav_status_msg = "[기준 스테이지 탐색] 현재 스테이지 미인식(좌측 끝) -> [-> 다음] 1회 이동하여 기준 스테이지 확인"
                    return "STAGE_NEED_NEXT", arr_r_score, arr_r_coords
                elif is_arrow_l:
                    self.nav_status_msg = "[기준 스테이지 탐색] 현재 스테이지 미인식 -> [<- 이전] 1회 이동하여 기준 스테이지 확인"
                    return "STAGE_NEED_PREV", arr_l_score, arr_l_coords
                elif is_arrow_r:
                    self.nav_status_msg = "[기준 스테이지 탐색] 현재 스테이지 미인식 -> [-> 다음] 1회 이동하여 기준 스테이지 확인"
                    return "STAGE_NEED_NEXT", arr_r_score, arr_r_coords
                return None

        # 4. 최종 추정 스테이지(nav_estimated_stage) 기준 액션 결정
        est = self.nav_estimated_stage
        if est == target_stage:
            state_name = "STAGE_810_READY" if target_stage == 810 else "STAGE_TARGET_READY"
            return state_name, 0.99, enter_coords
        elif est < target_stage:
            # 우측(->)으로 가야 하는데 우측 화살표가 아예 없고 좌측 화살표만 있다면 최고 스테이지 화면이므로 좌측으로 이동해 재측정
            if not is_arrow_r and is_arrow_l:
                self.reset_stage_navigation()
                self.nav_last_target = target_stage
                self.nav_status_msg = "[경계 보정] 우측 화살표 없음(최고 스테이지) 감지 -> [<- 이전] 이동하여 기준 스테이지 재측정"
                return "STAGE_NEED_PREV", arr_l_score, arr_l_coords
            return "STAGE_NEED_NEXT", arr_r_score, arr_r_coords
        else:
            # 좌측(<-)으로 가야 하는데 좌측 화살표가 아예 없고 우측 화살표만 있다면 최저 스테이지 화면이므로 우측으로 이동해 재측정
            if not is_arrow_l and is_arrow_r:
                self.reset_stage_navigation()
                self.nav_last_target = target_stage
                self.nav_status_msg = "[경계 보정] 좌측 화살표 없음(최저 스테이지) 감지 -> [-> 다음] 이동하여 기준 스테이지 재측정"
                return "STAGE_NEED_NEXT", arr_r_score, arr_r_coords
            return "STAGE_NEED_PREV", arr_l_score, arr_l_coords

    def detect_stage_arrow_left(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """던전 선택 화면에서 좌측 화살표 '<-' 감지 및 좌표 반환"""
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        default_cx = fw // 2 - int(135 * scale)
        default_cy = int(0.370 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_stage_arrow_left, roi=(0.25, 0.32, 0.50, 0.45), threshold=threshold
        )
        if matched:
            return True, score, (cx, max(cy, int(0.365 * fh)))
        return False, score, (default_cx, default_cy)

    def detect_stage_arrow_right(self, frame: np.ndarray, threshold: float = 0.70) -> Tuple[bool, float, Tuple[int, int]]:
        """던전 선택 화면에서 우측 화살표 '->' 감지 및 좌표 반환"""
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        default_cx = fw // 2 + int(135 * scale)
        default_cy = int(0.370 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_stage_arrow_right, roi=(0.50, 0.30, 0.85, 0.45), threshold=threshold
        )
        if matched:
            return True, score, (cx, max(cy, int(0.365 * fh)))
        return False, score, (default_cx, default_cy)

    def detect_final_wave(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """
        인게임 좌측 패널의 'Final wave' 또는 한글 '마지막 웨이브' 감지.
        감지 시 우측 상단 햄버거 메뉴 버튼 [≡] 클릭 좌표 반환.
        """
        fh, fw = frame.shape[:2]
        scale = fh / 960.0
        # 우측 상단 햄버거 버튼 기본 좌표
        default_menu_x = fw - int(68 * scale)
        default_menu_y = int(0.077 * fh)

        # 영문 'Final wave' 및 한글 '마지막 웨이브' 동시 검사
        m_en, score_en, _ = self.match_template(
            frame, self.template_final_wave, roi=(0.0, 0.15, 0.30, 0.40), threshold=threshold
        )
        m_kr, score_kr, _ = self.match_template(
            frame, self.template_final_wave_kr, roi=(0.0, 0.15, 0.30, 0.40), threshold=threshold
        )

        matched = m_en or m_kr
        score = max(score_en, score_kr)

        if matched:
            # 우측 상단 메뉴 버튼 위치도 정밀 감지
            _, _, menu_pos = self.match_template(
                frame, self.template_ingame_menu, roi=(0.70, 0.0, 1.0, 0.22), threshold=0.70
            )
            target = menu_pos if menu_pos != (0, 0) else (default_menu_x, default_menu_y)
            return True, score, target

        return False, score, (default_menu_x, default_menu_y)

    def detect_giveup_btn(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """인게임 설정창의 [포기하기] 버튼 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.407 * fw)
        default_cy = int(0.598 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_giveup, roi=(0.20, 0.48, 0.60, 0.70), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_giveup_confirm(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """'게임을 종료하시겠습니까?' 팝업의 [예] 버튼 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.385 * fw)
        default_cy = int(0.598 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_yes, roi=(0.20, 0.50, 0.55, 0.70), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_app_icon(self, frame: np.ndarray, threshold: float = 0.70) -> Tuple[bool, float, Tuple[int, int]]:
        """
        게임 비정상 종료(튕김) 시 바탕화면의 UnderDark 아이콘 감지 및 중심 좌표 반환.
        반환: (일치여부, 유사도점수, 아이콘 중심좌표(cx, cy))
        """
        if frame is None or self.template_app_icon is None:
            return False, 0.0, (0, 0)

        # 런처 바탕화면 상단~중단 그리드 영역(0%~70%)에서 메모리 절약 매칭
        matched, score, coords = self.match_template(
            frame, self.template_app_icon, roi=(0.0, 0.05, 1.0, 0.70), threshold=threshold
        )
        return matched, score, coords

    # ==========================================================
    # 펫 자동 일괄 합성 전용 감지 메서드군
    # ==========================================================
    def detect_tab_inventory(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """캠프 화면 하단 [인벤토리] 탭 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.318 * fw)
        default_cy = int(0.950 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tab_inventory, roi=(0.20, 0.88, 0.40, 0.99), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_tab_pet(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """인벤토리 화면 하단 상단 서브탭 [펫] 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.592 * fw)
        default_cy = int(0.825 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tab_pet, roi=(0.45, 0.78, 0.72, 0.88), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_pet_synth_btn(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """펫 인벤토리 화면 좌측 하단 [합성] 버튼 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.283 * fw)
        default_cy = int(0.413 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_pet_synth, roi=(0.20, 0.35, 0.40, 0.48), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_batch_synth_btn(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """펫 합성 팝업 우측 [일괄 합성] 버튼 감지 및 중심 좌표 반환 (합성 가능 여부 판별)"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.675 * fw)
        default_cy = int(0.448 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_batch_synth, roi=(0.55, 0.38, 0.80, 0.52), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_cancel_synth_btn(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """펫 합성 팝업 좌측 [취소] 버튼 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.485 * fw)
        default_cy = int(0.448 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_cancel_synth, roi=(0.35, 0.38, 0.60, 0.52), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_batch_arrow_left(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """일괄 합성 등급 선택 팝업의 [<-] 좌측 화살표 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.368 * fw)
        default_cy = int(0.537 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_batch_arrow_left, roi=(0.30, 0.48, 0.45, 0.60), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_tier_legend(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """일괄 합성 등급이 '전설'로 설정되었는지 감지"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.482 * fw)
        default_cy = int(0.537 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tier_legend, roi=(0.42, 0.48, 0.55, 0.60), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_batch_confirm_btn(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """일괄 합성 등급 선택 팝업 하단 [확인] 버튼 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.391 * fw)
        default_cy = int(0.645 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_btn_batch_confirm, roi=(0.30, 0.58, 0.50, 0.70), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_tab_camp(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """하단 네비게이션 바의 [캠프] 탭 감지 및 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.482 * fw)
        default_cy = int(0.950 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_tab_camp, roi=(0.40, 0.88, 0.60, 0.99), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_synth_result(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """펫 합성 결과 팝업 감지 및 하단 [확인] 버튼 중심 좌표 반환"""
        fh, fw = frame.shape[:2]
        default_cx = int(0.481 * fw)
        default_cy = int(0.813 * fh)

        matched, score, (cx, cy) = self.match_template(
            frame, self.template_confirm, roi=(0.35, 0.75, 0.65, 0.88), threshold=threshold
        )
        if matched:
            return True, score, (cx, cy)
        return False, score, (default_cx, default_cy)

    def detect_rank_reward(self, frame: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        """
        정기/랭킹/주간 보상 상자 팝업 감지 및 하단 [받기] 버튼 중심 좌표 반환.
        반환: (일치여부, 유사도점수, [받기] 버튼 중심좌표(cx, cy))
        """
        if frame is None or self.template_btn_claim is None:
            return False, 0.0, (0, 0)

        fh, fw = frame.shape[:2]
        default_cx = fw // 2
        default_cy = int(0.690 * fh)

        matched, score, coords = self.match_template(
            frame, self.template_btn_claim, roi=(0.30, 0.60, 0.70, 0.78), threshold=threshold
        )
        if matched:
            return True, score, coords

        # 보조 검사: 팝업 타이틀이 감지되는 경우 기본 [받기] 버튼 위치 반환
        if self.template_rank_reward_title is not None:
            t_matched, t_score, _ = self.match_template(
                frame, self.template_rank_reward_title, roi=(0.35, 0.25, 0.65, 0.35), threshold=threshold
            )
            if t_matched:
                return True, t_score, (default_cx, default_cy)

        return False, score, (default_cx, default_cy)

    # ==========================================================
    # 🏰 심연 던전 자동 타워 설치 (5종 타워 슬롯 인식 & 장애물 회피 외곽 배치)
    # ==========================================================
    def detect_available_towers(self, frame: np.ndarray, threshold: float = 0.78) -> list:
        """
        화면 중앙 하단 타워 목록 영역에서 보유 중인 타워(5종)를 인식하고,
        타워 목록 앞쪽(좌측 -> 우측) 순서로 정렬하여 반환.
        반환: [{"key": str, "name": str, "grid_w": int, "grid_h": int, "slot_coords": (cx, cy), "score": float}, ...]
        """
        if frame is None:
            return []

        found = []
        # 하단 타워 목록 슬롯 영역 (오른쪽 끝에 반쯤 잘린 슬롯 오인식 방지를 위해 x: 0.18 ~ 0.74 범위 탐색)
        slot_roi = (0.18, 0.84, 0.74, 0.99)

        for spec in self.tower_specs:
            tpl = spec["template"]
            if tpl is None:
                continue
            matched, score, coords = self.match_template(frame, tpl, roi=slot_roi, threshold=threshold)
            if matched:
                found.append({
                    "key": spec["key"],
                    "name": spec["name"],
                    "grid_w": spec["grid_w"],
                    "grid_h": spec["grid_h"],
                    "slot_coords": coords,
                    "score": score,
                })

        # 타워 목록 앞쪽(좌측 x좌표 오름차순)부터 설치하도록 정렬
        found.sort(key=lambda item: item["slot_coords"][0])
        return found

    def detect_map_obstacles(self, frame: np.ndarray, threshold: float = 0.56) -> list:
        """
        맵 내의 2x2 장애물(돌덩이, 나무상자 블록) 좌상단 좌표 리스트 반환.
        반환: [(ox, oy), ...]
        """
        if frame is None:
            return []

        fh, fw = frame.shape[:2]
        scale = fw / 967.0
        obs_pts = []

        for tpl in (self.template_obstacle_stone, self.template_obstacle_wood):
            if tpl is None:
                continue
            th, tw = tpl.shape[:2]
            if abs(scale - 1.0) > 0.05:
                sw, sh = max(10, int(tw * scale)), max(10, int(th * scale))
                cur_tpl = cv2.resize(tpl, (sw, sh), interpolation=cv2.INTER_AREA)
            else:
                cur_tpl = tpl

            res = cv2.matchTemplate(frame, cur_tpl, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= threshold)
            min_dist = max(22, int(32 * scale))
            for x, y in zip(xs, ys):
                ix, iy = int(x), int(y)
                # 상단/하단 UI 바깥의 실제 맵 영역만 필터링
                if iy < int(0.05 * fh) or iy > int(0.84 * fh):
                    continue
                if not any(abs(ix - px) < min_dist and abs(iy - py) < min_dist for px, py in obs_pts):
                    obs_pts.append((ix, iy))

        obs_pts.sort(key=lambda p: (p[1], p[0]))
        return obs_pts

    def find_tower_placement(
        self,
        frame: np.ndarray,
        grid_w: int,
        grid_h: int,
        excluded_spots: Optional[list] = None
    ) -> Optional[Tuple[Tuple[int, int], Tuple[int, int, int, int], list]]:
        """
        타워의 격자 크기(grid_w x grid_h)에 맞춰 장애물(2x2 돌덩이), 기존 설치된 타워,
        상/하/좌/우 UI 영역을 모두 피하면서 맵의 가장자리(외곽)부터 빈 맨땅 위치를 탐색.
        반환: ((drop_x, drop_y), (x1, y1, x2, y2), obs_rects) 또는 None
        """
        if frame is None:
            return None

        fh, fw = frame.shape[:2]
        scale = fw / 967.0
        cell = max(16, int(round(32.0 * scale)))
        cap_offset = int(round(12.0 * scale))
        block_size = 2 * cell

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        obs_pts = self.detect_map_obstacles(frame)

        # 공중을 날아다니는 화염구/폭발 이펙트(밝은 주황·노란색 계열: R>160, G>75, R-B>80)만 마스킹하고
        # 로켓타워의 순수 빨간색 콘(G<65)은 마스킹하지 않도록 분리
        b_ch, g_ch, r_ch = cv2.split(frame)
        missile_mask = ((r_ch > 160) & (g_ch > 75) & (r_ch.astype(np.int16) - b_ch.astype(np.int16) > 80)).astype(np.uint8)
        k_size = max(7, int(round(9 * scale)) | 1)
        missile_mask = cv2.dilate(missile_mask, np.ones((k_size, k_size), np.uint8), iterations=1)
        # 화염구 이펙트가 아닌 실제 구조물(돌덩이, 나무상자, 이미 설치된 타워)의 굵은 검은색 외곽선 픽셀 맵
        dark_struct = ((gray < 42) & (missile_mask == 0)).astype(np.uint8)

        # 장애물 좌표를 기준으로 현재 프레임의 32px 격자 원점 (x0, y0) 동적 보정
        if obs_pts:
            x0 = int(np.median([x % cell for x, _ in obs_pts]))
            y0 = int(np.median([(y + cap_offset) % cell for _, y in obs_pts]))
        else:
            x0 = int(round(2 * scale))
            y0 = int(round(29 * scale))

        obs_rects = [(ox, oy + cap_offset, ox + block_size, oy + cap_offset + block_size) for ox, oy in obs_pts]

        # LDPlayer 창 캡처(994x967, 상단 타이틀바 포함)와 순수 ADB 캡처(960x960) 간 Y축 오프셋 자동 보정
        top_offset = (fh - fw) if (fh > fw + 15) else 0

        # 좌/우 외곽 통로(3x2, 3x3 타워 폭)까지 충분히 활용하면서 상단 벽면과 하단 타워바 취소 영역만 피하는 안전 경계
        min_x = int(round(78 * scale))
        max_x = int(round(890 * scale))
        min_y = top_offset + int(round(118 * scale))
        max_y = top_offset + int(round(730 * scale))

        # UI 충돌 제외 영역
        ui_tl_x, ui_tl_y = int(round(118 * scale)), top_offset + int(round(318 * scale))   # 좌상단 레벨/웨이브 패널
        ui_tr_x, ui_tr_y = int(round(820 * scale)), top_offset + int(round(100 * scale))   # 우상단 배속/메뉴 버튼
        timer_x1, timer_x2 = int(round(420 * scale)), int(round(545 * scale))              # 상단 중앙 타이머
        timer_y = top_offset + int(round(135 * scale))
        center_x1, center_x2 = int(round(400 * scale)), int(round(565 * scale))            # 중앙 캐릭터/화톳불 영역
        center_y1, center_y2 = top_offset + int(round(356 * scale)), top_offset + int(round(531 * scale))

        candidates = []
        max_rows = (fh // cell) + 2
        max_cols = (fw // cell) + 2

        for r in range(0, max_rows):
            y1 = y0 + r * cell
            y2 = y1 + grid_h * cell
            if y1 < min_y or y2 > max_y:
                continue

            for c in range(0, max_cols):
                x1 = x0 + c * cell
                x2 = x1 + grid_w * cell
                if x1 < min_x or x2 > max_x:
                    continue

                # 1. UI 영역 침범 검사
                if x1 < ui_tl_x and y1 < ui_tl_y:
                    continue
                if x2 > ui_tr_x and y1 < ui_tr_y:
                    continue
                if not (x2 <= timer_x1 or x1 >= timer_x2 or y1 >= timer_y):
                    continue
                if not (x2 <= center_x1 or x1 >= center_x2 or y2 <= center_y1 or y1 >= center_y2):
                    continue

                # 2. 2x2 돌덩이/나무상자 장애물 충돌 검사
                tol = max(2, int(4 * scale))
                if any(not (x2 <= ox1 + tol or x1 >= ox2 - tol or y2 <= oy1 + tol or y1 >= oy2 - tol)
                       for ox1, oy1, ox2, oy2 in obs_rects):
                    continue

                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # 3. 이미 시도/설치한 위치(excluded_spots) 및 그 주변 격자 영역 영구 스킵
                # (1칸=32px씩 옆으로만 옮기며 실패 위치를 반복 시도하지 않도록 타워 크기에 비례한 반경 스킵)
                if excluded_spots:
                    skip_radius = int(round((max(grid_w, grid_h) - 0.4) * cell))
                    if any(abs(cx - ex) < skip_radius and abs(cy - ey) < skip_radius for ex, ey in excluded_spots):
                        continue

                # 4. 맨땅(Bare Ground) 픽셀 검증 (미사일/투사체 및 작은 바닥 자갈/경험치 구슬 무시):
                # 인접 블록의 테두리가 걸리지 않도록 안쪽(margin=2px)만 검사하며,
                # 실제 타워/장애물 외곽선(> 35px)은 걸러내고 미사일/작은 바닥 무늬(<= 35px)는 통과시킴
                margin = max(2, int(round(2 * scale)))
                py1 = max(0, y1 + margin)
                py2 = min(fh, y2 - margin)
                px1 = max(0, x1 + margin)
                px2 = min(fw, x2 - margin)
                patch = dark_struct[py1:py2, px1:px2]
                if patch.size == 0:
                    continue

                if int(np.sum(patch)) > int(28 * scale * scale):
                    continue

                # 5. 가장자리(외곽 테두리) 우선순위 계산 (격자 링 단위 -> 상/좌/우/하 외곽부터 배치)
                dist_top = max(0, y1 - min_y) // cell
                dist_bottom = max(0, max_y - y2) // cell
                dist_left = max(0, x1 - min_x) // cell
                dist_right = max(0, max_x - x2) // cell
                edge_ring = min(dist_top, dist_bottom, dist_left, dist_right)

                candidates.append((edge_ring, y1, x1, (cx, cy), (x1, y1, x2, y2)))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        _, _, _, best_center, best_rect = candidates[0]
        return best_center, best_rect, obs_rects

    def plan_next_tower_placement(
        self,
        frame: np.ndarray,
        excluded_spots: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """
        하단 타워 목록의 앞쪽(좌측) 타워부터 순서대로 확인하여,
        배치 가능한 외곽 맨땅 좌표가 있으면 드래그 시작점과 드롭 목표점을 반환.
        """
        available = self.detect_available_towers(frame)
        if not available:
            return None

        for tower in available:
            res = self.find_tower_placement(
                frame,
                grid_w=tower["grid_w"],
                grid_h=tower["grid_h"],
                excluded_spots=excluded_spots,
            )
            if res is not None:
                drop_coords, drop_rect, obs_rects = res
                fh, fw = frame.shape[:2]
                scale = fw / 967.0
                # 인게임 드래그 시 타워 프리뷰가 손가락 위치보다 약 64px(2칸) 위쪽에 떠서 이동하므로,
                # 실제 타워를 drop_coords에 안착시키려면 손가락은 (drop_x, drop_y + 64) 지점까지 드래그해야 함!
                finger_offset_y = int(round(64.0 * scale))
                drag_end_coords = (drop_coords[0], drop_coords[1] + finger_offset_y)
                return {
                    "tower": tower,
                    "start_coords": tower["slot_coords"],
                    "drop_coords": drop_coords,
                    "drag_end_coords": drag_end_coords,
                    "drop_rect": drop_rect,
                    "obstacles": obs_rects,
                    "all_available": available,
                }
        return None

    def analyze_screen_state(self, frame: np.ndarray, mode: str = "full_auto", target_stage: int = 810) -> Tuple[str, float, Optional[Tuple[int, int]]]:
        """
        현재 프레임의 게임 상태를 종합 판별하여 반환.
        mode에 따라 full_auto(심연의 모래 구멍) 또는 stage_farming(일반 스테이지 노가다) 지원
        target_stage: stage_farming 모드 시 목표 스테이지 번호 (기본 810)
        """
        if frame is None:
            return "UNKNOWN", 0.0, None

        # 1. 방지 팝업 (모든 모드 최우선)
        is_popup, p_score, loc = self.detect_popup(frame)
        if is_popup:
            return "POPUP", p_score, loc

        # 2. 게임 비정상 종료(튕김/홈화면) 감지 (모든 모드 공통 최우선 처리)
        is_crashed, icon_score, icon_coords = self.detect_app_icon(frame)
        if is_crashed:
            return "APP_CRASHED", icon_score, icon_coords

        # 3. 정기/랭킹/주간 보상 상자 팝업 감지 (자정/일요일 보상 등 - [받기] 버튼 터치)
        is_rank_reward, rr_score, claim_coords = self.detect_rank_reward(frame)
        if is_rank_reward:
            return "RANK_REWARD", rr_score, claim_coords

        # ==========================================================
        # [신규 모드] 일반 스테이지 노가다 파밍 상태 판별
        # ==========================================================
        if mode == "stage_farming":
            # 2. 포기하기 확인 팝업 [예] 버튼
            is_yes, y_score, y_coords = self.detect_giveup_confirm(frame)
            if is_yes:
                self.reset_stage_navigation()
                return "GIVEUP_CONFIRM", y_score, y_coords

            # 3. 설정창 [포기하기] 버튼
            is_giveup, g_score, g_coords = self.detect_giveup_btn(frame)
            if is_giveup:
                self.reset_stage_navigation()
                return "GIVEUP_SETTING", g_score, g_coords

            # 4. 보상 화면 ([확인] 버튼)
            is_reward, r_score, r_coords = self.detect_reward_screen(frame)
            if is_reward:
                self.reset_stage_navigation()
                return "REWARD", r_score, r_coords

            # 5. 게임 오버 화면 ([광고 x2] 버튼)
            is_gameover, go_score, go_coords = self.detect_gameover(frame)
            if is_gameover:
                self.reset_stage_navigation()
                return "GAMEOVER", go_score, go_coords

            # 6. Final Wave 감지 (보스 등장 -> 우측 상단 설정창 버튼 클릭)
            is_final, f_score, menu_coords = self.detect_final_wave(frame)
            if is_final:
                self.reset_stage_navigation()
                return "FINAL_WAVE", f_score, menu_coords

            # 7. 던전 선택 창에서 현재 스테이지 인식, 이동 횟수 계획 수립 및 중간 크로스체크
            nav_result = self.plan_stage_navigation(frame, target_stage=target_stage)
            if nav_result is not None:
                return nav_result

            # 9. 던전 선택 창 상단 [일반] 탭 선택 필요 시
            is_tab_gen, tab_score, tab_coords = self.detect_tab_general(frame)
            is_tab_rank, _, _ = self.detect_dungeon_popup(frame)
            if is_tab_gen or is_tab_rank:
                return "STAGE_TAB_GENERAL", tab_score, tab_coords

            # 10. 캠프 화면
            is_camp, c_score, c_coords = self.detect_camp(frame)
            if is_camp:
                self.reset_stage_navigation()
                return "CAMP", c_score, c_coords

            # 11. 인게임 일반 전투 진행 화면 (1/16 ~ 15/16 웨이브)
            is_ingame, in_score, in_coords = self.detect_in_game(frame)
            if is_ingame:
                self.reset_stage_navigation()
                return "IN_GAME", in_score, in_coords

            return "UNKNOWN", 0.0, None

        # ==========================================================
        # [기존 기본 모드] 심연의 모래 구멍 자동 파밍 상태 판별
        # ==========================================================
        # 2. 보상 화면
        is_reward, r_score, r_coords = self.detect_reward_screen(frame)
        if is_reward:
            return "REWARD", r_score, r_coords

        # 3. 게임 오버 화면
        is_gameover, go_score, go_coords = self.detect_gameover(frame)
        if is_gameover:
            return "GAMEOVER", go_score, go_coords

        # 4. 던전 선택 팝업
        is_dungeon, d_score, d_coords = self.detect_dungeon_popup(frame)
        if is_dungeon:
            return "DUNGEON_POPUP", d_score, d_coords

        # 5. 캠프 화면
        is_camp, c_score, c_coords = self.detect_camp(frame)
        if is_camp:
            return "CAMP", c_score, c_coords

        # 6. 인게임 화면
        is_ingame, in_score, in_coords = self.detect_in_game(frame)
        if is_ingame:
            return "IN_GAME", in_score, in_coords

        return "UNKNOWN", 0.0, None

    def draw_debug_overlay(self, frame: np.ndarray, detected: bool, score: float, 
                           digits: Optional[str] = None, state: str = "MONITORING",
                           target_coords: Optional[Tuple[int, int]] = None,
                           popup_loc: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        GUI 프리뷰 화면에 실시간 감지 상태 및 타겟 좌표 오버레이 표시
        """
        overlay = frame.copy()
        fh, fw = overlay.shape[:2]

        if state == "POPUP" or detected:
            # 1. 디스플레이 박스 표시
            _, (x1, y1, x2, y2) = self.get_display_crop(frame, popup_loc)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            if digits:
                cv2.putText(overlay, f"CODE: {digits}", (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 2. 키패드 버튼 위치 점/원 표시
            for d in range(10):
                cx, cy = self.get_keypad_coords(d, fw, fh, popup_loc)
                cv2.circle(overlay, (cx, cy), 18, (0, 200, 255), 2)
                cv2.putText(overlay, str(d), (cx - 6, cy + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)

            # 상단 알림 배너
            cv2.rectangle(overlay, (0, 0), (fw, 40), (0, 140, 0), -1)
            status_text = f"POPUP DETECTED! (Conf: {score*100:.1f}%)"
            cv2.putText(overlay, status_text, (10, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        elif state == "APP_CRASHED":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (0, 0, 180), -1)
            cv2.putText(overlay, f"APP CRASHED! (Score: {score*100:.1f}%) -> CLICK UNDERDARK ICON", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 28, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 24, 2)

        elif state == "CAMP":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (0, 120, 150), -1)
            cv2.putText(overlay, f"CAMP SCREEN (Score: {score*100:.1f}%) -> CLICK [DUNGEON]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "STAGE_810_READY":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (0, 160, 80), -1)
            cv2.putText(overlay, f"STAGE 810 READY! -> CLICK [ENTER] (NOT SWEEP)", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 26, (0, 255, 120), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 120), cv2.MARKER_CROSS, 22, 2)

        elif state == "STAGE_NEED_PREV":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (180, 100, 20), -1)
            cv2.putText(overlay, f"NOT STAGE 810 -> CLICK [<- PREV] TO FIND 810", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 200, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 200, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "STAGE_TAB_GENERAL":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (140, 70, 180), -1)
            cv2.putText(overlay, f"DUNGEON POPUP -> SELECT [GENERAL] TAB", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (255, 150, 255), 2)
                cv2.drawMarker(overlay, target_coords, (255, 150, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "FINAL_WAVE":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (0, 0, 220), -1)
            cv2.putText(overlay, f"FINAL WAVE BOSS DETECTED! -> CLICK [MENU (HAMBURGER)]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 100, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 100, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "GIVEUP_SETTING":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (180, 50, 50), -1)
            cv2.putText(overlay, f"IN-GAME SETTINGS -> CLICK [GIVE UP]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "GIVEUP_CONFIRM":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (200, 20, 80), -1)
            cv2.putText(overlay, f"CONFIRM POPUP -> CLICK [YES (CONFIRM QUIT)]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 100), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 100), cv2.MARKER_CROSS, 20, 2)

        elif state == "DUNGEON_POPUP":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (120, 60, 180), -1)
            cv2.putText(overlay, f"DUNGEON SELECT (Score: {score*100:.1f}%)", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (255, 120, 255), 2)
                cv2.drawMarker(overlay, target_coords, (255, 120, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "GAMEOVER":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (40, 40, 200), -1)
            cv2.putText(overlay, f"GAME OVER (Score: {score*100:.1f}%) -> CLICK [AD x2]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 0), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

        elif state == "REWARD":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (30, 130, 80), -1)
            cv2.putText(overlay, f"REWARD SCREEN (Score: {score*100:.1f}%) -> CLICK [CONFIRM]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "RANK_REWARD":
            cv2.rectangle(overlay, (0, 0), (fw, 36), (200, 100, 20), -1)
            cv2.putText(overlay, f"RANK REWARD (Score: {score*100:.1f}%) -> CLICK [CLAIM]", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

        elif state == "IN_GAME":
            cv2.rectangle(overlay, (0, 0), (fw, 32), (60, 60, 60), -1)
            cv2.putText(overlay, f"IN GAME BATTLE (Score: {score*100:.1f}%)", (10, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 150), 1)

        else:
            cv2.rectangle(overlay, (0, 0), (fw, 30), (30, 30, 30), -1)
            cv2.putText(overlay, f"MONITORING... ({state})", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        return overlay

