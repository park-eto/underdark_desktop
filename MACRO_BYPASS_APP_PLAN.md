# Underdark 매크로 방지 자동 입력 시스템 개발 계획서
**Document Version:** 1.0.0  
**Target Project:** Underdark LDPlayer Macro-Bypass Desktop App  
**Target Audience:** 개발자 및 AI 개발 어시스턴트 모델  

---

## 1. 프로젝트 개요 (Overview)

### 1.1 배경 및 목적
- 모바일 게임 **Underdark**를 LDPlayer(안드로이드 앱플레이어)에서 구동하며 LDPlayer 자체 '작업 녹화(매크로)' 기능으로 반복 파밍을 진행함.
- 일정 횟수(판수) 진행 시 게임 내에서 **매크로 방지 4자리 숫자 핀코드 입력 팝업**이 발생함.
- 올바른 4자리 숫자를 입력하면 초록색으로 활성화되며 검증에 성공하고 기존 화면으로 복귀하지만, 방치 시 매크로가 엉뚱한 위치를 클릭하여 입력이 초기화되거나 멈춤.
- **목표:** 백그라운드에서 LDPlayer 화면을 실시간 모니터링하다가 매크로 방지창이 나타나면 이를 즉시 감지하여 4자리 숫자를 인식(OCR)하고 가상 키패드를 자동으로 순서대로 터치/클릭하여 해제해주는 **경량 데스크탑 GUI 애플리케이션**을 구축함.

---

## 2. 화면 및 입력 메커니즘 분석 (Image Analysis)

제공된 `화면캡처.png`와 `화면캡처 성공.png`를 기반으로 한 UI 분석 결과입니다.

```
+-----------------------------------------------------------+
|                      [LDPlayer 윈도우]                     |
|  [50번째 실행 중] (||) (■) ...                            |
|                                                           |
|     +-----------------------------------------------+     |
|     | "매크로 방지를 위해 아래 숫자를 키패드에 순서대로    |     |
|     |  입력해 주세요."                              |     |
|     |                                               |     |
|     |           +-----------------------+           |     |
|     |           |     8   5   4   3     |  <-- 타겟 번호 |
|     |           +-----------------------+     (4자리)     |
|     |                                               |     |
|     |       [ 1 ]   [ 2 ]   [ 3 ]   [ 4 ]   [ 5 ]   |     |
|     |       [ 6 ]   [ 7 ]   [ 8 ]   [ 9 ]   [ 0 ]   |     |
|     |                                 <-- 키패드 (2x5)   |
|     +-----------------------------------------------+     |
|                                                           |
+-----------------------------------------------------------+
```

### 2.1 UI 구성 요소
1. **안내 텍스트:** `"매크로 방지를 위해 아래 숫자를 키패드에 순서대로 입력해 주세요."`
   - 매크로 방지 팝업 등장 여부를 판단하는 1차 트리거로 활용 가능.
2. **숫자 표시 박스 (Target Display):**
   - 상단 검은색 직사각형 배경에 굵은 고딕 폰트로 4자리 정수 표시.
   - 입력 진행 상태에 따라 기입력된 숫자는 **형광 초록색 (`#00FF00` 계열)**, 미입력된 숫자는 **흰색 (`#FFFFFF`)** 으로 표시됨.
3. **가상 키패드 (Numpad Layout):**
   - 2행 5열 고정 그리드 레이아웃:
     - 1행: `[1]`, `[2]`, `[3]`, `[4]`, `[5]`
     - 2행: `[6]`, `[7]`, `[8]`, `[9]`, `[0]`
   - 버튼 클릭 시 해당 키패드 숫자도 초록색 하이라이트 효과가 적용됨.
4. **성공 및 초기화 조건:**
   - 4자리 올바른 입력 완료 시: 팝업이 즉시 닫히고 기존 게임 진행 화면(예: 보상 획득 팝업 등)으로 복귀.
   - 오입력 시: 입력된 숫자가 리셋되고 새로운 번호가 제시되거나 재입력 요구.

### 2.2 핵심 고려사항 (Key Challenges)
- **LDPlayer 녹화 매크로와의 충돌:**
  - LDPlayer 자체 매크로가 화면의 특정 위치를 계속 클릭하고 있을 가능성이 높음.
  - 방지창이 떴을 때 매크로가 엉뚱한 키패드를 건드려 초기화되지 않도록, **감지 즉시 빠르게(수백 ms 내) 4자리 연속 입력**을 수행하거나, 필요 시 LDPlayer 일시정지 단축키를 호출하는 전략 필요.
- **백그라운드 제어 지원 여부:**
  - 사용자가 다른 작업을 하거나 LDPlayer 창이 다른 창 뒤에 가려져 있어도 작동하도록 **ADB(Android Debug Bridge)** 연동을 기본 제어 방식으로 채택하는 것이 가장 안정적임.

---

## 3. 권장 기술 스택 (Recommended Tech Stack)

| 구분 | 추천 기술 | 선정 이유 |
| :--- | :--- | :--- |
| **언어 (Language)** | **Python 3.10+** | 컴퓨터 비전(OpenCV), ADB 제어, GUI 라이브러리 생태계가 가장 성숙함 |
| **GUI 프레임워크** | **PyQt6** 또는 **PySide6** | 네이티브 윈도우 스타일, 반응형 UI, 스레딩(QThread) 처리가 용이 |
| **이미지 처리 & 검출** | **OpenCV (`opencv-python`)**, **NumPy** | 고속 ROI 크롭, 템플릿 매칭, 이진화, 색상 마스킹 |
| **문자 인식 (OCR)** | **Custom Template Matching** 또는 **EasyOCR / Tesseract** | 숫자가 고정 폰트의 0~9 단 10종이므로 템플릿 매칭(Template Matching) 적용 시 100%에 가까운 정확도와 5ms 미만의 압도적 속도 보장 |
| **에뮬레이터 제어** | **`pure-python-adb` (`ppadb`)** / **`adbutils`** | LDPlayer 내부 안드로이드에 ADB로 직접 연결하여 백그라운드 스크린샷 및 고속 터치(`input tap`) 전송 |
| **보조/대체 제어** | **`pywin32`**, **`mss`**, **`pydirectinput`** | ADB 비활성화 유저를 위한 Windows Window Handle 기반 비활성 창 클릭/캡처 폴백(Fallback) |

---

## 4. 시스템 아키텍처 (System Architecture)

```mermaid
flowchart TD
    subgraph UI_Layer [Desktop GUI Layer (PyQt6)]
        MainWindow[메인 윈도우 UI]
        LogViewer[실시간 로그 & 스크린샷 뷰어]
        ConfigPanel[설정 패널: 감지 주기, ADB 포트, 딜레이]
        StatusIndicator[상태 표시: 모니터링 중 / 입력 중 / 완료]
    end

    subgraph Core_Engine [Core Engine (QThread Worker)]
        Loop[모니터링 루프 (0.5s ~ 1.0s 주기)]
        Capture[화면 캡처 모듈 (ADB Screencap)]
        Detector{매크로 방지창 감지 여부}
        OCR[숫자 인식 모듈 (Color Filter + Template Matching)]
        KeypadMapper[키패드 좌표 매핑 (Grid / Coordinate Calc)]
        Action[ADB Input 터치 입력 전송 (4자리 연타)]
        Verify[입력 결과 검증 (창 닫힘 여부 확인)]
    end

    subgraph LDPlayer [Target: LDPlayer Instance]
        AndroidOS[Android Subsystem]
        Game[Underdark App]
    end

    MainWindow -->|시작 / 정지| Core_Engine
    Loop --> Capture
    Capture -->|이미지 프레임| Detector
    Detector -->|No| Loop
    Detector -->|Yes| OCR
    OCR -->|인식된 숫자 '8543'| KeypadMapper
    KeypadMapper -->|좌표 큐| Action
    Action -->|adb shell input tap x y| AndroidOS
    Action --> Verify
    Verify -->|성공 알림| UI_Layer
```

---

## 5. 상세 모듈 구현 설계 (Detailed Module Design)

### 5.1 모듈 1: LDPlayer 연결 및 캡처 (`DeviceManager`)
- **역할:** 실행 중인 LDPlayer 인스턴스를 찾고 ADB 포트로 연결.
- **포트 감지:**
  - LDPlayer 9 기본 포트: `127.0.0.1:5555`, 2번째 인스턴스: `5555 + 32 = 5587` 등 자동 스캔.
- **화면 캡처 파이프라인:**
  ```python
  # adb screencap을 메모리 버퍼로 바로 로드 (파일 IO 없음)
  raw_bytes = device.screencap()
  image = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
  ```

### 5.2 모듈 2: 팝업 감지기 (`PopupDetector`)
- **판단 기준:**
  1. **고정 텍스트 템플릿 매칭:** "매크로 방지를 위해..." 텍스트 영역 또는 상단 안내 문구 영역 템플릿 비교.
  2. **특정 UI 바운더리 박스 검출:** 키패드 외곽선 및 검은색 숫자 디스플레이 박스 위치의 형태적 특징 검출.
- **최적화:** 전체 화면을 스캔하지 않고, 게임 화면 중앙부(가로/세로 30%~70% 구역)만 지정하여 크롭 후 검사 -> CPU 점유율 1% 미만 유지.

### 5.3 모듈 3: 4자리 숫자 인식 (`CodeRecognizer`)
- **인식 대상:** 상단 검은색 배경 박스 안의 숫자.
- **전처리 (Preprocessing):**
  1. 숫자 영역 박스를 정규화된 해상도 비율로 크롭.
  2. 텍스트가 초록색(`(0, 255, 0)`) 또는 흰색(`(255, 255, 255)`)이므로, HSV 또는 Grayscale 변환 후 Threshold 이진화 적용:
     ```python
     # 텍스트만 흰색(255), 배경은 검은색(0)으로 분리
     gray = cv2.cvtColor(crop_display, cv2.COLOR_BGR2GRAY)
     _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
     ```
  3. 컨투어(`cv2.findContours`)를 추출하여 좌->우 방향으로 4개의 숫자 바운딩 박스 정렬.
- **숫자 판별 알고리즘:**
  - **방법 A (권장 - 템플릿 매칭):** Underdark 게임 폰트의 `0`부터 `9`까지 10개 템플릿 이미지를 미리 저장해두고, 각 숫자 슬롯과 템플릿 간 `cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)` 수행. 가장 일치율이 높은 숫자를 선택. (인식 시간 < 2ms, 정확도 100%)
  - **방법 B (범용 - OCR):** Tesseract OCR (`--psm 7 -c tessedit_char_whitelist=0123456789`) 적용.

### 5.4 모듈 4: 키패드 좌표 매핑 및 터치 (`KeypadController`)
- **키패드 구조 분석:**
  - 10개의 버튼이 정확히 2행 5열로 정렬되어 있음.
  - LDPlayer 해상도 기준(예: 1080x1920 세로모드 또는 900x1600 등) 상대 비율(Normalized Coordinate: 0.0 ~ 1.0)로 계산.
- **좌표 계산 공식:**
  ```python
  # 화면 해상도 W, H 기준 키패드 중심 상대 비율
  KEYPAD_RATIO = {
      1: (0.178, 0.528), 2: (0.323, 0.528), 3: (0.468, 0.528), 4: (0.613, 0.528), 5: (0.758, 0.528),
      6: (0.178, 0.612), 7: (0.323, 0.612), 8: (0.468, 0.612), 9: (0.613, 0.612), 0: (0.758, 0.612),
  }
  ```
  *(※ 실제 해상도에 맞춰 캘리브레이션 또는 버튼 중심점 자동 감지 기능 탑재)*
- **입력 전송:**
  - 인식된 4자리 숫자를 순서대로 터치:
    ```python
    for digit in recognized_digits:
        x, y = get_keypad_coords(digit, screen_width, screen_height)
        device.shell(f"input tap {x} {y}")
        time.sleep(0.08)  # 게임 내 입력 애니메이션 반영을 위한 80ms 딜레이
    ```

### 5.5 모듈 5: 사후 검증 및 실패 복구 (`Verifier & Recovery`)
- 4자리 입력 후 약 300ms 대기.
- 다시 화면을 캡처하여 매크로 방지 팝업이 사라졌는지 확인:
  - **성공 시:** "매크로 방지 번호 [8, 5, 4, 3] 해제 완료" 로그 기록 및 카운터 증가.
  - **실패(팝업 잔존) 시:** 
    - 입력 중간에 LDPlayer 기존 녹화 매크로의 간섭 등으로 꼬였을 가능성 존재.
    - 최대 3회 재시도(Retry).
    - 연속 3회 실패 시 비프음(Beep sound) 출력 및 사용자 알림 발송.

---

## 6. 데스크탑 GUI 디자인 및 기능 명세

### 6.1 UI 레이아웃 구성 (PyQt6 기반)
```
+-------------------------------------------------------------+
|  Underdark Macro-Guard Auto Solver  v1.0.0          [-] [X]  |
+-------------------------------------------------------------+
|  [연결 상태: LDPlayer-1 (127.0.0.1:5555) - 연결됨 ● ]       |
+-------------------------------------------------------------+
|  [설정]                                                     |
|  - 검사 주기(초): [ 0.5 ]초    - 입력 딜레이: [ 80 ]ms       |
|  - 텔레그램/디스코드 웹훅 알림: [v] 활성화                  |
+-------------------------------------------------------------+
|  [실시간 상태 모니터링]                                     |
|  +---------------------------+  +-------------------------+  |
|  | [화면 프리뷰]             |  | • 상태: 모니터링 중...  |  |
|  |                           |  | • 누적 해제 횟수: 14회  |  |
|  | (방지창 감지 시 하이라이트|  | • 최근 입력: [8 5 4 3]  |  |
|  |  및 실시간 캡처 표시)     |  | • 최종 성공: 23:14:02   |  |
|  +---------------------------+  +-------------------------+  |
+-------------------------------------------------------------+
|  [로그 콘솔]                                                |
|  [23:10:01] 모니터링 루프 시작...                           |
|  [23:12:45] 매크로 방지 팝업 감지됨!                        |
|  [23:12:45] 숫자 인식 완료: [8, 5, 4, 3]                    |
|  [23:12:46] 키패드 터치 입력 완료 -> 팝업 해제 성공!        |
+-------------------------------------------------------------+
|  [ ▶ 모니터링 시작 ]       [ ■ 중지 ]       [ ⚙ 테스트 캡처 ]|
+-------------------------------------------------------------+
```

### 6.2 주요 컨트롤 버튼 기능
1. **모니터링 시작/중지 (`Start/Stop`):** 백그라운드 QThread 워커 구동.
2. **테스트 캡처 (`Test Capture & OCR`):** 현재 화면을 캡처하여 방지창 감지 여부, 숫자 인식 결과, 키패드 위치를 즉시 시각적으로 박스 표시해주는 진단 기능.
3. **디바이스 재검색 (`Refresh Device`):** LDPlayer 재실행 시 포트 재연결.

---

## 7. 단계별 구현 로드맵 (Implementation Plan)

### Phase 1: 프로토타입 핵심 비전 알고리즘 검증 (CLI 기반)
- [x] 제공된 `화면캡처.png` 샘플 이미지를 통한 오프라인 검증 스크립트 작성.
- [ ] 숫자 영역 ROI 크롭 및 템플릿 매칭 알고리즘 작성 (`0`~`9` 템플릿 생성).
- [ ] 키패드 중심 좌표 계산 로직 검증.

### Phase 2: LDPlayer ADB 연동 및 자동화 테스트
- [ ] ADB 연결 매니저 구현 (`adbutils` 사용).
- [ ] 실시간 스크린 캡처 및 백그라운드 `input tap` 속도 벤치마크 (딜레이 최적화).
- [ ] 실제 게임 구동 중 매크로 방지창 발생 시 자동 입력 엔드투엔드(E2E) 테스트.

### Phase 3: GUI 데스크탑 앱 구현 (PyQt6)
- [ ] 메인 윈도우 UI 및 컨트롤러 연동.
- [ ] 스레드 분리 (`QThread`를 통한 UI 프리징 방지).
- [ ] 실시간 로그 출력 및 통계 카운터 반영.

### Phase 4: 안정화 및 예외 처리
- [ ] 연속 실패 감지 시 디스코드 웹훅(Discord Webhook) 알림 연동.
- [ ] PyInstaller를 통한 단일 실행 파일(`.exe`) 패키징.

---

## 8. 샘플 핵심 코드 스니펫 (Reference Implementation)

다른 AI 모델이나 개발자가 바로 착수할 수 있도록 제공하는 핵심 파이프라인 의사코드입니다.

```python
import cv2
import numpy as np
import time

class UnderdarkSolver:
    def __init__(self, adb_device):
        self.device = adb_device
        # 1080x1920 기준 상대 좌표 (해상도에 맞게 스케일링)
        self.keypad_map = {
            1: (0.178, 0.528), 2: (0.323, 0.528), 3: (0.468, 0.528), 4: (0.613, 0.528), 5: (0.758, 0.528),
            6: (0.178, 0.612), 7: (0.323, 0.612), 8: (0.468, 0.612), 9: (0.613, 0.612), 0: (0.758, 0.612),
        }

    def is_popup_present(self, frame):
        # 안내 문구 영역 또는 특정 마커 템플릿 매칭 (유사도 0.85 이상)
        # 예: '매크로 방지를 위해' 텍스트 템플릿 매칭
        return True # 조건 만족 시

    def extract_and_solve_digits(self, frame):
        # 1. 상단 디스플레이 박스 크롭
        # 2. 이진화 및 4개 숫자 분할
        # 3. 0~9 템플릿 매칭으로 4자리 추출
        digits = [8, 5, 4, 3] # 예시 결과
        return digits

    def solve(self):
        raw = self.device.screencap()
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        h, w, _ = frame.shape

        if self.is_popup_present(frame):
            digits = self.extract_and_solve_digits(frame)
            for d in digits:
                rx, ry = self.keypad_map[d]
                x, y = int(rx * w), int(ry * h)
                self.device.shell(f"input tap {x} {y}")
                time.sleep(0.08)
            return True
        return False
```

---

## 9. 결론 및 다음 단계 제안
1. 본 문서([MACRO_BYPASS_APP_PLAN.md](file:///c:/dev/workplace/underdark_desktop/MACRO_BYPASS_APP_PLAN.md))를 바탕으로 개발을 즉시 시작할 수 있습니다.
2. 우선 제공해주신 `화면캡처.png`에서 **숫자 0~9의 템플릿 이미지를 추출하고 번호 인식을 검증하는 파이썬 스크립트**를 첫 번째 단계로 작성하는 것을 추천합니다.
