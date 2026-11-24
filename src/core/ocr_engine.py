import os
import cv2
import numpy as np
from typing import Optional, List, Tuple
from .resources import get_resource_path

class OcrEngine:
    """
    4자리 매크로 방지 핀코드 숫자 인식 엔진
    """
    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            template_dir = get_resource_path(os.path.join("assets", "templates"))
            
        self.template_dir = template_dir
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        templates = {}
        for num in range(10):
            path = os.path.join(self.template_dir, f"digit_{num}.png")
            if os.path.exists(path):
                img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                templates[num] = img
            else:
                print(f"[OCR] 템플릿 파일 없음: {path}")
        return templates

    def recognize(self, display_img: np.ndarray) -> Tuple[str, float]:
        """
        숫자 디스플레이 박스 이미지를 받아 4자리 핀코드 문자열과 평균 신뢰도를 반환.
        반환 예: ("8543", 0.77)
        - 다중 임계값(Multi-threshold) 시도로 글자 뭉침 방지 및 4자리 자동 분리
        - 실패 시 실제 텍스트 바운딩 박스 기준 4등분 스마트 슬라이싱 폴백
        """
        if display_img is None or not self.templates:
            return "", 0.0

        gray = cv2.cvtColor(display_img, cv2.COLOR_BGR2GRAY)
        crop_h = gray.shape[0]
        min_h = max(10, int(crop_h * 0.20))
        max_h = max(min_h + 5, int(crop_h * 0.95))
        min_w = max(4, int(crop_h * 0.08))
        max_w = max(min_w + 5, int(crop_h * 0.85))

        # 1차 시도: 다중 임계값(140, 160, 180, 200, 130, 120, 210)으로 정확히 4개의 문자 박스 탐색
        threshold_candidates = [140, 160, 180, 200, 130, 120, 210, 100]
        best_thresh = None

        for th in threshold_candidates:
            _, thresh = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            if best_thresh is None:
                best_thresh = thresh

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            char_boxes = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                if min_h <= h <= max_h and min_w <= w <= max_w:
                    char_boxes.append((x, y, w, h))

            if len(char_boxes) == 4:
                char_boxes.sort(key=lambda b: b[0])
                digits, confs = self._match_boxes(thresh, char_boxes)
                avg_conf = sum(confs) / len(confs) if confs else 0.0
                if avg_conf >= 0.50:
                    return "".join(map(str, digits)), avg_conf

        # 2차 시도 (폴백): 텍스트 실제 영역 바운딩 후 4등분 슬롯 슬라이싱
        if best_thresh is None:
            _, best_thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)

        return self._recognize_by_grid_slice(best_thresh, min_h, min_w)

    def _match_boxes(self, thresh: np.ndarray, boxes: List[Tuple[int, int, int, int]]) -> Tuple[List[int], List[float]]:
        digits = []
        confs = []
        for x, y, w, h in boxes:
            char_crop = thresh[y:y+h, x:x+w]
            char_resized = cv2.resize(char_crop, (20, 30), interpolation=cv2.INTER_AREA)

            best_num = 0
            best_score = -1.0
            for num, tpl in self.templates.items():
                res = cv2.matchTemplate(char_resized, tpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0])
                if score > best_score:
                    best_score = score
                    best_num = num

            digits.append(best_num)
            confs.append(max(0.0, best_score))
        return digits, confs

    def _recognize_by_grid_slice(self, thresh: np.ndarray, min_h: int = 14, min_w: int = 6) -> Tuple[str, float]:
        """
        글자가 겹치거나 컨투어 분할이 실패했을 때,
        실제 텍스트가 존재하는 영역만을 찾아 4등분 슬롯으로 매칭하는 스마트 폴백 로직
        """
        pts = cv2.findNonZero(thresh)
        if pts is None:
            return "0000", 0.0

        tx, ty, tw, th = cv2.boundingRect(pts)
        if tw < 20 or th < min_h:
            return "0000", 0.0

        slot_w = tw / 4.0
        digits = []
        confs = []

        for i in range(4):
            sx1 = max(0, tx + int(i * slot_w))
            sx2 = min(thresh.shape[1], tx + int((i + 1) * slot_w))
            slot_crop = thresh[ty:ty+th, sx1:sx2]

            # 슬롯 내 유효 흰색 픽셀 영역 바운딩
            sub_pts = cv2.findNonZero(slot_crop)
            if sub_pts is not None:
                cx, cy, cw, ch = cv2.boundingRect(sub_pts)
                char_crop = slot_crop[cy:cy+ch, cx:cx+cw]
            else:
                char_crop = slot_crop

            char_resized = cv2.resize(char_crop, (20, 30), interpolation=cv2.INTER_AREA)

            best_num = 0
            best_score = -1.0
            for num, tpl in self.templates.items():
                res = cv2.matchTemplate(char_resized, tpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0])
                if score > best_score:
                    best_score = score
                    best_num = num

            digits.append(best_num)
            confs.append(max(0.0, best_score))

        avg_conf = sum(confs) / len(confs) if confs else 0.0
        return "".join(map(str, digits)), avg_conf
