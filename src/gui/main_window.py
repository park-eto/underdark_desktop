import os
import datetime
import cv2
import numpy as np
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QGroupBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QImage, QPixmap, QFont, QIcon, QPixmapCache

from ..core.adb_client import AdbClient
from ..core.detector import PopupDetector
from ..core.ocr_engine import OcrEngine
from ..core.controller import MacroWorker
from ..core.resources import get_resource_path
from .styles import DARK_THEME_QSS

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Underdark 통합 자동 매크로 & 핀코드 해제기 v2.3.0")
        icon_path = get_resource_path("assets/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.resize(1120, 800)
        self.setStyleSheet(DARK_THEME_QSS)

        # QPixmap 캐시 메모리 제한 (2MB 상한 설정으로 장시간 구동 시 메모리 누수 방지)
        QPixmapCache.setCacheLimit(2048)

        # 코어 컴포넌트 초기화
        self.adb = AdbClient()
        self.detector = PopupDetector()
        self.ocr = OcrEngine()
        self.worker: Optional[MacroWorker] = None
        self.saved_device_serial = ""

        self._init_ui()
        self._load_settings()
        self._refresh_device_list()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. 상단 디바이스 연결 바
        top_bar = self._create_top_bar()
        main_layout.addLayout(top_bar)

        # 2. 본문 (좌측: 프리뷰, 우측: 컨트롤/통계/로그)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # 좌측 프리뷰 패널
        left_panel = self._create_preview_panel()
        body_layout.addWidget(left_panel, 4)

        # 우측 제어 패널
        right_panel = self._create_control_panel()
        body_layout.addWidget(right_panel, 6)

        main_layout.addLayout(body_layout)

    def _create_top_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        title_label = QLabel("LDPlayer ADB 디바이스:")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(title_label)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(220)
        layout.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("디바이스 검색 🔄")
        self.refresh_btn.clicked.connect(self._refresh_device_list)
        layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("연결하기")
        self.connect_btn.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_btn)

        layout.addStretch()

        self.status_badge = QLabel("연결 대기 중")
        self.status_badge.setStyleSheet("color: #FFA500; font-weight: bold; padding: 4px 10px; background: #262118; border-radius: 4px;")
        layout.addWidget(self.status_badge)

        return layout

    def _create_preview_panel(self) -> QGroupBox:
        group = QGroupBox("실시간 화면 프리뷰")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.preview_label = QLabel("화면 대기 중")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #0E1015; border-radius: 6px; border: 1px dashed #2B3342;")
        self.preview_label.setMinimumSize(320, 480)
        layout.addWidget(self.preview_label, 1)

        # 샘플 진단 선택 및 버튼
        sample_group = QGroupBox("오프라인 샘플 진단")
        sample_layout = QVBoxLayout(sample_group)
        sample_layout.setSpacing(6)

        self.sample_combo = QComboBox()
        # 신규 기능: 심연 던전 자동 타워 설치 샘플
        self.sample_combo.addItem("🏰 심연_게임화면.png (심연 전투 - 타워 슬롯 인식 & 외곽 자동 배치)", "심연_게임화면.png")
        self.sample_combo.addItem("🏰 심연_게임화면2.png (심연 전투 2 - 타워 2종 인식 & 외곽 배치)", "심연_게임화면2.png")
        self.sample_combo.addItem("🏰 심연_게임화면3.png (심연 전투 3 - 로켓/까마귀/햄스터/저격수 배치)", "심연_게임화면3.png")
        self.sample_combo.addItem("🏰 가장자리설치샘플.png (외곽 기설치 타워 회피 & 잔여 외곽 빈자리 탐색)", "가장자리설치샘플.png")
        # 신규 기능: 앱 튕김 / 자동 재실행 샘플
        self.sample_combo.addItem("🔄 언더다크튕김.png (앱 비정상 종료/바탕화면 - 자동 재실행)", "언더다크튕김.png")
        # 신규 기능: 정기/랭킹 보상 상자 샘플
        self.sample_combo.addItem("🎁 랭킹보상.png (정기/랭킹 보상 상자 - [받기] 터치)", "랭킹보상.png")
        # 신규 기능: 펫 자동 일괄 합성 샘플
        self.sample_combo.addItem("🐾 펫합성_캠프화면2.png (캠프 - 하단 인벤토리 터치)", "펫합성_캠프화면2.png")
        self.sample_combo.addItem("🐾 펫합성_인벤토리.png (인벤토리 - 서브탭 '펫' 터치)", "펫합성_인벤토리.png")
        self.sample_combo.addItem("🐾 펫합성_펫인벤토리.png (펫 인벤토리 - 중앙 '합성' 버튼 터치)", "펫합성_펫인벤토리.png")
        self.sample_combo.addItem("🐾 펫합성_합성버튼클릭.png (펫 합성 팝업 - '일괄 합성' 버튼 감지)", "펫합성_합성버튼클릭.png")
        self.sample_combo.addItem("🐾 펫합성_일괄합성없음.png (합성 대상 없음 - '취소' 및 '캠프' 복귀)", "펫합성_일괄합성없음.png")
        self.sample_combo.addItem("🐾 펫합성_일괄합성클릭.png (일괄 합성 등급 - '<-' 화살표 터치)", "펫합성_일괄합성클릭.png")
        self.sample_combo.addItem("🐾 펫합성_일괄합성전설.png (등급 '전설' 확인 - [확인] 버튼 터치)", "펫합성_일괄합성전설.png")
        self.sample_combo.addItem("🐾 펫합성_합성결과.png (펫 합성 결과 팝업 - [확인] 터치)", "펫합성_합성결과.png")
        # 신규 810 스테이지 노가다 파밍 샘플
        self.sample_combo.addItem("⭐ 일반_810스테이지_던전선택2.png (던전선택 - 한글 '스테이지 810')", "일반_810스테이지_던전선택2.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_보스등장2.png (보스등장 - 한글 '마지막 웨이브')", "일반_810스테이지_보스등장2.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_던전선택.png (던전선택 - 811 스테이지)", "일반_810스테이지_던전선택.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_810스테이지.png (810 스테이지 입장 대기)", "일반_810스테이지_810스테이지.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_게임화면.png (게임화면 - 일반 웨이브)", "일반_810스테이지_게임화면.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_보스등장.png (보스등장 - Final Wave)", "일반_810스테이지_보스등장.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_설정창.png (설정창 - 포기하기)", "일반_810스테이지_설정창.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_포기하기.png (포기하기 확인 - 예/아니오)", "일반_810스테이지_포기하기.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_게임종료.png (게임종료 - 패배 광고x2)", "일반_810스테이지_게임종료.png")
        self.sample_combo.addItem("⭐ 일반_810스테이지_보상획득.png (보상획득 - 확인 버튼)", "일반_810스테이지_보상획득.png")
        # 기존 심연 및 핀코드 샘플
        self.sample_combo.addItem("🛡️ 비밀번호해제못함.png (매크로 방지 핀코드 - 2154)", "비밀번호해제못함.png")
        self.sample_combo.addItem("화면캡처.png (매크로 방지 핀코드)", "화면캡처.png")
        self.sample_combo.addItem("캠프화면.png (캠프 - 던전 버튼)", "캠프화면.png")
        self.sample_combo.addItem("던전선택화면.png (던전 팝업 - 랭킹 & 심연)", "던전선택화면.png")
        self.sample_combo.addItem("게임진행화면.png (게임 진행 - 전투 화면)", "게임진행화면.png")
        self.sample_combo.addItem("게임오버화면.png (게임 오버 - 광고 x2 버튼)", "게임오버화면.png")
        self.sample_combo.addItem("획득보상화면.png (획득 보상 - 확인 버튼)", "획득보상화면.png")
        self.sample_combo.addItem("캠프화면_960_960.png (960x960 캠프 메인)", "캠프화면_960_960.png")
        self.sample_combo.addItem("던전선택화면_960_960.png (960x960 심연의 모래 구멍)", "던전선택화면_960_960.png")
        self.sample_combo.addItem("게임진행화면_960_960.png (960x960 전투 화면)", "게임진행화면_960_960.png")
        self.sample_combo.addItem("게임오버화면_960_960.png (960x960 게임 오버)", "게임오버화면_960_960.png")
        self.sample_combo.addItem("심연의모래구멍.png (심연의 모래 구멍 타겟 카드)", "심연의모래구멍.png")
        sample_layout.addWidget(self.sample_combo)

        btn_layout = QHBoxLayout()
        self.test_sample_btn = QPushButton("선택 샘플 진단 실행 🔍")
        self.test_sample_btn.clicked.connect(self._run_sample_diagnosis)
        btn_layout.addWidget(self.test_sample_btn)

        self.snap_btn = QPushButton("현재 화면 1회 캡처 📸")
        self.snap_btn.clicked.connect(self._capture_single_frame)
        btn_layout.addWidget(self.snap_btn)
        sample_layout.addLayout(btn_layout)

        layout.addWidget(sample_group)
        return group

    def _create_control_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. 통계 카드 영역 (4종 카드)
        stats_group = QGroupBox("매크로 동작 현황 통계")
        stats_layout = QHBoxLayout(stats_group)
        stats_layout.setSpacing(8)

        card1, self.stat_dungeon_label = self._create_stat_card("던전 완료", "0 회", "#00E676")
        card2, self.stat_pin_label = self._create_stat_card("핀코드 해결", "0 회", "#38BDF8")
        card3, self.stat_state_label = self._create_stat_card("현재 상태", "대기 중", "#FBBF24")
        card4, self.stat_battle_label = self._create_stat_card("전투 경과 / 완료시각", "-", "#A78BFA")

        stats_layout.addWidget(card1)
        stats_layout.addWidget(card2)
        stats_layout.addWidget(card3)
        stats_layout.addWidget(card4)
        layout.addWidget(stats_group)

        # 2. 모드 및 동작 설정 영역
        config_group = QGroupBox("매크로 모드 및 기본 설정")
        config_vbox = QVBoxLayout(config_group)
        config_vbox.setSpacing(8)

        # 모드 선택 행
        mode_layout = QHBoxLayout()
        mode_label = QLabel("동작 모드:")
        mode_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔥 [심연의 모래 구멍] 던전 자동 반복 파밍", MacroWorker.MODE_FULL_AUTO)
        self.mode_combo.addItem("⭐ [일반 스테이지] 노가다 파밍 (Final Wave 포기하기 반복)", MacroWorker.MODE_STAGE_FARMING)
        self.mode_combo.addItem("🛡️ 단독 매크로 방지 핀코드 해제만 (기존 모드)", MacroWorker.MODE_PIN_ONLY)
        mode_layout.addWidget(self.mode_combo, 1)

        self.target_stage_label = QLabel("목표 스테이지:")
        self.target_stage_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        mode_layout.addWidget(self.target_stage_label)

        self.target_stage_spin = QSpinBox()
        self.target_stage_spin.setRange(1, 9999)
        self.target_stage_spin.setValue(810)
        self.target_stage_spin.setSuffix(" 스테이지")
        self.target_stage_spin.setToolTip("일반 스테이지 노가다 파밍 시 진입할 목표 스테이지 번호입니다. (기본값: 810)")
        mode_layout.addWidget(self.target_stage_spin)

        config_vbox.addLayout(mode_layout)

        # 세부 설정 행
        config_layout = QHBoxLayout()
        config_layout.setSpacing(10)

        config_layout.addWidget(QLabel("반복 횟수:"))
        self.runs_spin = QSpinBox()
        self.runs_spin.setRange(0, 9999)
        self.runs_spin.setValue(0)
        self.runs_spin.setSpecialValueText("무제한 (0)")
        self.runs_spin.setSuffix(" 회")
        config_layout.addWidget(self.runs_spin)

        config_layout.addWidget(QLabel("검사 주기:"))
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.2, 5.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(0.6)
        self.interval_spin.setSuffix(" 초")
        config_layout.addWidget(self.interval_spin)

        config_layout.addWidget(QLabel("터치 딜레이:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(30, 500)
        self.delay_spin.setSingleStep(10)
        self.delay_spin.setValue(80)
        self.delay_spin.setSuffix(" ms")
        config_layout.addWidget(self.delay_spin)

        config_vbox.addLayout(config_layout)

        # 체크박스 행 (핀코드 해제 옵션, 확인 버튼 클릭 옵션, 앱 재시작 옵션)
        chk_layout = QHBoxLayout()
        chk_layout.setSpacing(14)

        self.pin_bypass_chk = QCheckBox("🛡️ 매크로 방지 핀코드 자동 해제")
        self.pin_bypass_chk.setToolTip("체크 시 던전 또는 스테이지 파밍 중 4자리 핀코드가 발생하면 자동으로 인식 및 터치하여 해제합니다.\n해제 시 핀코드가 감지되어도 건드리지 않고 수동 입력을 대기합니다.")
        self.pin_bypass_chk.setChecked(True)
        chk_layout.addWidget(self.pin_bypass_chk)

        self.confirm_chk = QCheckBox("해제 후 [확인] 버튼 자동 클릭")
        self.confirm_chk.setChecked(True)
        chk_layout.addWidget(self.confirm_chk)

        self.pin_bypass_chk.toggled.connect(self.confirm_chk.setEnabled)

        self.app_restart_chk = QCheckBox("🔄 앱 튕김 시 자동 재시작")
        self.app_restart_chk.setToolTip("게임 중 비정상 종료(튕김)로 홈 화면으로 나갔을 때\n바탕화면의 UnderDark 아이콘을 찾아 클릭하여 재시작하고 로딩을 기다립니다.")
        self.app_restart_chk.setChecked(True)
        chk_layout.addWidget(self.app_restart_chk)

        self.auto_tower_chk = QCheckBox("🏰 심연 자동 타워 설치")
        self.auto_tower_chk.setToolTip(
            "심연의 모래 구멍 전투 중 하단 타워 목록 앞쪽부터 5종 타워(로켓 3x3, 까마귀 3x3, 저격수 3x2, 햄스터 2x2, 펭귄 2x2)를 인식하여\n"
            "2x2 돌덩이 장애물과 UI를 피해 맵의 가장자리(외곽) 맨땅부터 자동으로 드래그 앤 드롭 설치합니다.\n"
            "(설치할 타워나 빈 공간이 모두 소진되면 해당 판에서는 자동으로 탐지를 중지하여 메모리/CPU를 절약합니다.)"
        )
        self.auto_tower_chk.setChecked(True)
        self.auto_tower_chk.toggled.connect(self._on_auto_tower_toggled)
        chk_layout.addWidget(self.auto_tower_chk)

        chk_layout.addStretch()
        config_vbox.addLayout(chk_layout)

        layout.addWidget(config_group)

        # 3. 신규 기능: 전투 시작 초기 커맨드 1회 실행 설정
        cmd_group = QGroupBox("🎮 전투 시작 초기 조작 설정 (게임 시작 시 1회 실행)")
        cmd_vbox = QVBoxLayout(cmd_group)
        cmd_vbox.setSpacing(8)

        cmd_top_layout = QHBoxLayout()
        self.init_cmd_chk = QCheckBox("전투 진입 시 초기 커맨드(이동/키) 1회 자동 실행")
        self.init_cmd_chk.setChecked(False)
        cmd_top_layout.addWidget(self.init_cmd_chk)
        cmd_top_layout.addStretch()
        cmd_vbox.addLayout(cmd_top_layout)

        cmd_settings_layout = QHBoxLayout()
        cmd_settings_layout.setSpacing(8)

        cmd_settings_layout.addWidget(QLabel("조작 유형:"))
        self.cmd_type_combo = QComboBox()
        self.cmd_type_combo.addItem("👉 오른쪽으로 드래그 (우측 이동)", "drag_right")
        self.cmd_type_combo.addItem("👈 왼쪽으로 드래그 (좌측 이동)", "drag_left")
        self.cmd_type_combo.addItem("👆 위쪽으로 드래그 (상단 이동)", "drag_up")
        self.cmd_type_combo.addItem("👇 아래쪽으로 드래그 (하단 이동)", "drag_down")
        self.cmd_type_combo.addItem("↗️ 오른쪽 위로 드래그 (우상단 이동)", "drag_up_right")
        self.cmd_type_combo.addItem("↘️ 오른쪽 아래로 드래그 (우하단 이동)", "drag_down_right")
        self.cmd_type_combo.addItem("↖️ 왼쪽 위로 드래그 (좌상단 이동)", "drag_up_left")
        self.cmd_type_combo.addItem("↙️ 왼쪽 아래로 드래그 (좌하단 이동)", "drag_down_left")
        cmd_settings_layout.addWidget(self.cmd_type_combo, 1)

        cmd_settings_layout.addWidget(QLabel("지속 시간:"))
        self.cmd_dur_spin = QSpinBox()
        self.cmd_dur_spin.setRange(50, 5000)
        self.cmd_dur_spin.setSingleStep(50)
        self.cmd_dur_spin.setValue(200)
        self.cmd_dur_spin.setSuffix(" ms")
        cmd_settings_layout.addWidget(self.cmd_dur_spin)

        self.cmd_test_btn = QPushButton("⚡ 1회 즉시 테스트")
        self.cmd_test_btn.clicked.connect(self._test_initial_command)
        cmd_settings_layout.addWidget(self.cmd_test_btn)

        cmd_vbox.addLayout(cmd_settings_layout)
        layout.addWidget(cmd_group)

        # 4. 신규 기능: 펫 자동 일괄 합성 설정 (특정 판수 주기마다 실행)
        pet_group = QGroupBox("🐾 펫 자동 일괄 합성 설정 (캠프 진입 시 N판 주기 실행)")
        pet_vbox = QVBoxLayout(pet_group)
        pet_vbox.setSpacing(8)

        pet_settings_layout = QHBoxLayout()
        pet_settings_layout.setSpacing(12)

        self.pet_synth_chk = QCheckBox("🐾 펫 자동 일괄 합성 활성화")
        self.pet_synth_chk.setToolTip("활성화 시 지정한 던전 완료 판수(N판)마다 캠프 화면에서 인벤토리 -> 펫으로 이동하여 전설 등급까지 일괄 합성을 자동으로 수행합니다.")
        self.pet_synth_chk.setChecked(True)
        pet_settings_layout.addWidget(self.pet_synth_chk)

        pet_settings_layout.addWidget(QLabel("합성 주기:"))
        self.pet_interval_spin = QSpinBox()
        self.pet_interval_spin.setRange(1, 1000)
        self.pet_interval_spin.setValue(5)
        self.pet_interval_spin.setSuffix(" 판마다")
        pet_settings_layout.addWidget(self.pet_interval_spin)

        self.pet_synth_chk.toggled.connect(self.pet_interval_spin.setEnabled)

        self.pet_test_btn = QPushButton("⚡ 다음 캠프 즉시 1회 합성")
        self.pet_test_btn.setToolTip("매크로 실행 중 다음 번 캠프 화면에 도달했을 때 판수 주기와 무관하게 펫 일괄 합성을 즉시 1회 실행하도록 예약합니다.")
        self.pet_test_btn.clicked.connect(self._trigger_instant_pet_synth)
        pet_settings_layout.addWidget(self.pet_test_btn)

        pet_settings_layout.addStretch()
        pet_vbox.addLayout(pet_settings_layout)
        layout.addWidget(pet_group)

        # 5. 제어 버튼 (시작 / 정지)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.start_btn = QPushButton("▶ 매크로 시작")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.clicked.connect(self._start_worker)
        btn_box.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ 매크로 중지")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(44)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_worker)
        btn_box.addWidget(self.stop_btn)

        layout.addLayout(btn_box)

        # 5. 실시간 로그 영역
        log_group = QGroupBox("실시간 동작 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(1000)  # 최대 1000줄 유지 (장시간 구동 시 메모리 비대화 방지)
        log_layout.addWidget(self.log_view)

        clear_btn = QPushButton("로그 지우기")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.log_view.clear)
        log_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(log_group, 1)

        return widget

    def _create_stat_card(self, title: str, default_val: str, color: str):
        card = QFrame()
        card.setProperty("class", "statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #718096; font-size: 11px;")
        layout.addWidget(t_lbl)

        v_lbl = QLabel(default_val)
        v_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(v_lbl)

        return card, v_lbl

    def _log(self, msg: str):
        time_str = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_view.append(f"{time_str} {msg}")

    def _refresh_device_list(self):
        self.device_combo.clear()
        devices = self.adb.list_devices()
        if devices:
            self.device_combo.addItems(devices)
            self._log(f"[ADB] {len(devices)}개의 디바이스 발견: {', '.join(devices)}")
            if hasattr(self, 'saved_device_serial') and self.saved_device_serial:
                idx = self.device_combo.findText(self.saved_device_serial)
                if idx >= 0:
                    self.device_combo.setCurrentIndex(idx)
        else:
            self.device_combo.addItem("감지된 디바이스 없음")
            self._log("[ADB] 연결된 디바이스가 없습니다. LDPlayer가 실행 중인지 확인하세요.")

    def _toggle_connection(self):
        if self.adb.is_connected:
            self.adb.disconnect()
            self.connect_btn.setText("연결하기")
            self.status_badge.setText("연결 해제됨")
            self.status_badge.setStyleSheet("color: #FFA500; font-weight: bold; padding: 4px 10px; background: #262118; border-radius: 4px;")
            self._log("[ADB] 연결이 해제되었습니다.")
        else:
            serial = self.device_combo.currentText()
            if serial == "감지된 디바이스 없음":
                serial = None
            if self.adb.connect(serial):
                self.saved_device_serial = self.adb.serial
                self._save_settings()
                self.connect_btn.setText("연결 해제")
                self.status_badge.setText(f"연결됨: {self.adb.serial}")
                self.status_badge.setStyleSheet("color: #00E676; font-weight: bold; padding: 4px 10px; background: #122B1E; border-radius: 4px;")
                self._log(f"[ADB] 디바이스 ({self.adb.serial}) 에 성공적으로 연결되었습니다.")
            else:
                QMessageBox.warning(self, "연결 실패", "LDPlayer 디바이스에 연결할 수 없습니다.\nLDPlayer 설정에서 ADB 디버깅이 활성화되어 있는지 확인하세요.")

    def _test_initial_command(self):
        """설정된 초기 커맨드를 1회 즉시 실행하여 캐릭터/키 입력을 테스트"""
        if not self.adb.is_connected:
            QMessageBox.warning(self, "연결 필요", "디바이스가 연결되어 있지 않습니다. 먼저 상단 [연결하기]를 눌러주세요.")
            return

        cmd = self.cmd_type_combo.currentData()
        duration = self.cmd_dur_spin.value()
        res = self.adb.get_resolution()
        if res:
            fw, fh = res
        else:
            fw, fh = 960, 960

        cx, cy = fw // 2, int(fh * 0.65)
        self._log(f"[테스트] 초기 조작 1회 즉시 실행: {cmd} ({duration}ms)")

        dx = int(fw * 0.28)
        dy = int(fh * 0.22)
        diag_dx = int(fw * 0.20)
        diag_dy = int(fh * 0.16)

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

        self._log("[테스트] 초기 조작 테스트 실행 완료!")

    def _trigger_instant_pet_synth(self):
        """캠프 진입 시 펫 일괄 합성을 즉시 1회 실행하도록 예약"""
        if self.worker and self.worker.isRunning():
            self.worker.force_pet_synth = True
            self._log("[펫합성] ⚡ 다음 번 캠프 화면 도달 시 펫 자동 일괄 합성을 즉시 1회 실행하도록 예약되었습니다.")
            QMessageBox.information(self, "예약 완료", "다음 번 캠프 화면에 도달하면 판수 주기와 무관하게\n펫 자동 일괄 합성을 즉시 1회 실행합니다.")
        else:
            QMessageBox.information(self, "알림", "매크로가 실행 중일 때만 동작합니다.\n매크로 시작 후 버튼을 누르시면 다음 캠프 진입 시 즉시 실행됩니다.")

    def _on_auto_tower_toggled(self, checked: bool):
        """심연 자동 타워 설치 체크박스 토글 시 실행 중인 워커에 즉시 반영"""
        if self.worker:
            self.worker.auto_place_tower = checked
            if checked:
                self.worker._reset_tower_state()

    def _on_mode_changed(self):
        """선택된 모드에 따라 전용 설정 위젯 활성화/비활성화"""
        is_stage = (self.mode_combo.currentData() == MacroWorker.MODE_STAGE_FARMING)
        self.target_stage_label.setEnabled(is_stage)
        self.target_stage_spin.setEnabled(is_stage)

    def _start_worker(self):
        if not self.adb.is_connected:
            if not self.adb.connect():
                QMessageBox.warning(self, "연결 필요", "먼저 LDPlayer에 연결해주세요.")
                return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.worker = MacroWorker(self.adb, self.detector, self.ocr)
        self.worker.mode = self.mode_combo.currentData()
        self.worker.target_stage = self.target_stage_spin.value()
        self.worker.max_runs = self.runs_spin.value()
        self.worker.check_interval = self.interval_spin.value()
        self.worker.tap_delay = self.delay_spin.value() / 1000.0
        self.worker.auto_solve_pin = self.pin_bypass_chk.isChecked()
        self.worker.auto_click_confirm = self.confirm_chk.isChecked()
        self.worker.auto_restart_app = self.app_restart_chk.isChecked()
        self.worker.auto_place_tower = self.auto_tower_chk.isChecked()

        # 🐾 펫 자동 일괄 합성 옵션 주입
        self.worker.pet_synth_enabled = self.pet_synth_chk.isChecked()
        self.worker.pet_synth_interval = self.pet_interval_spin.value()

        # 초기 커맨드 옵션 주입
        self.worker.initial_cmd_enabled = self.init_cmd_chk.isChecked()
        self.worker.initial_cmd_type = self.cmd_type_combo.currentData()
        self.worker.initial_cmd_duration = self.cmd_dur_spin.value()

        self.worker.log_signal.connect(self._log)
        self.worker.frame_signal.connect(self._update_preview)
        self.worker.stat_signal.connect(self._update_stats)
        self.worker.status_signal.connect(lambda s: self.status_badge.setText(s))

        self.worker.start()

    def _stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _update_stats(self, stats: dict):
        self.stat_dungeon_label.setText(f"{stats.get('dungeon_count', 0)} 회")
        self.stat_pin_label.setText(f"{stats.get('success_count', 0)} 회")
        
        cur_st = stats.get('current_state', '대기 중')
        tgt_num = self.target_stage_spin.value()
        st_map = {
            "CAMP": "캠프",
            "DUNGEON_POPUP": "던전 선택",
            "STAGE_TAB_GENERAL": "일반 탭 선택",
            "STAGE_810_READY": f"{tgt_num} 준비 완료",
            "STAGE_TARGET_READY": f"{tgt_num} 준비 완료",
            "STAGE_NEED_PREV": "목표 탐색 중(<-)",
            "STAGE_NEED_NEXT": "목표 탐색 중(->)",
            "IN_GAME": "전투 중",
            "FINAL_WAVE": "Final Wave (보스)",
            "GIVEUP_SETTING": "포기하기",
            "GIVEUP_CONFIRM": "종료 확인",
            "GAMEOVER": "게임오버",
            "REWARD": "보상 수령",
            "POPUP": "핀코드 감지",
            "POPUP_MANUAL": "핀코드 수동대기",
            "APP_CRASHED": "앱 튕김 (재실행 중)",
            "MONITORING": "모니터링"
        }
        self.stat_state_label.setText(st_map.get(cur_st, cur_st))
        
        battle_time = stats.get('elapsed_battle', '-')
        last_t = stats.get('last_time', '-')
        if battle_time and battle_time != "00:00" and battle_time != "완료":
            self.stat_battle_label.setText(f"전투 {battle_time}")
        elif last_t != "-":
            self.stat_battle_label.setText(f"완료 {last_t}")
        else:
            self.stat_battle_label.setText("-")

    def _update_preview(self, frame: np.ndarray):
        if frame is None:
            return
        
        # UI 프리뷰 라벨 크기에 맞춰 OpenCV에서 먼저 최적 크기로 축소 (QImage/QPixmap 메모리 할당 95% 이상 절감)
        target_size = self.preview_label.size()
        lbl_w = max(100, target_size.width())
        lbl_h = max(100, target_size.height())

        fh, fw = frame.shape[:2]
        scale = min(lbl_w / fw, lbl_h / fh)
        nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))

        small_frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        del small_frame

        bytes_per_line = 3 * nw
        q_img = QImage(rgb_frame.data, nw, nh, bytes_per_line, QImage.Format.Format_RGB888).copy()
        del rgb_frame

        pixmap = QPixmap.fromImage(q_img)
        self.preview_label.setPixmap(pixmap)
        del q_img
        del pixmap

    def _capture_single_frame(self):
        if not self.adb.is_connected:
            QMessageBox.information(self, "알림", "디바이스에 연결되어 있지 않습니다.")
            return
        frame = self.adb.capture_screen()
        if frame is not None:
            cur_mode = self.mode_combo.currentData()
            state, score, target_coords = self.detector.analyze_screen_state(frame, mode=cur_mode)
            code = None
            if state == "POPUP":
                is_p, p_score, loc = self.detector.detect_popup(frame)
                crop, _ = self.detector.get_display_crop(frame, loc)
                code, conf = self.ocr.recognize(crop)
                self._log(f"[진단] 매크로 방지 팝업 감지! (일치율: {score*100:.1f}%) -> 핀코드: [{code}]")
                overlay = self.detector.draw_debug_overlay(frame, True, score, code, state=state, popup_loc=loc)
            else:
                self._log(f"[진단] 화면 상태 판별: [{state}] (일치율: {score*100:.1f}%, 타겟 좌표: {target_coords})")
                overlay = self.detector.draw_debug_overlay(frame, False, score, code, state=state, target_coords=target_coords)

            self._update_preview(overlay)

    def _run_sample_diagnosis(self):
        """선택된 샘플 이미지로 검출 및 상태 판별 오프라인 테스트"""
        filename = self.sample_combo.currentData()
        # assets/images/ 경로 및 루트 디렉토리 후보군 모두 검색
        candidate_paths = [
            get_resource_path(os.path.join("assets", "images", filename)),
            get_resource_path(filename),
            os.path.join("assets", "images", filename),
            filename
        ]
        sample_path = None
        for cp in candidate_paths:
            if os.path.exists(cp):
                sample_path = cp
                break

        if sample_path is None:
            QMessageBox.warning(self, "파일 없음", f"{filename} 샘플 파일이 존재하지 않습니다.")
            return

        frame = cv2.imdecode(np.fromfile(sample_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            QMessageBox.warning(self, "로드 실패", f"{filename} 이미지를 읽을 수 없습니다.")
            return

        # 🐾 펫 자동 합성 샘플 이미지 전용 진단 로직
        if "펫합성" in filename:
            overlay = frame.copy()
            fh, fw = frame.shape[:2]

            m_res, s_res, c_res = self.detector.detect_synth_result(frame)
            m_leg, s_leg, c_leg = self.detector.detect_tier_legend(frame)
            m_bconf, s_bconf, c_bconf = self.detector.detect_batch_confirm_btn(frame)
            m_arr, s_arr, c_arr = self.detector.detect_batch_arrow_left(frame)
            m_batch, s_batch, c_batch = self.detector.detect_batch_synth_btn(frame)
            m_can, s_can, c_can = self.detector.detect_cancel_synth_btn(frame)
            m_synth, s_synth, c_synth = self.detector.detect_pet_synth_btn(frame)
            m_pet, s_pet, c_pet = self.detector.detect_tab_pet(frame)
            m_camp, s_camp, _ = self.detector.detect_camp(frame)
            m_inv, s_inv, c_inv = self.detector.detect_tab_inventory(frame)

            if m_res and s_res >= 0.85:
                desc = f"펫 합성 결과 화면 -> [확인] 버튼 터치 (신뢰도 {s_res*100:.1f}%)"
                target_coords = c_res
            elif m_leg and s_leg >= 0.80 and m_bconf and s_bconf >= 0.80:
                desc = f"일괄 합성 '전설' 등급 확인 완료 -> [확인] 버튼 터치 (신뢰도 {s_bconf*100:.1f}%)"
                target_coords = c_bconf
            elif m_arr and s_arr >= 0.80:
                desc = f"일괄 합성 등급 선택 ('일반') -> [<-] 화살표 터치하여 '전설' 변경 (신뢰도 {s_arr*100:.1f}%)"
                target_coords = c_arr
            elif m_batch and s_batch >= 0.80:
                desc = f"펫 합성 팝업 -> 우측 [일괄 합성] 버튼 터치 (신뢰도 {s_batch*100:.1f}%)"
                target_coords = c_batch
            elif m_can and s_can >= 0.80:
                desc = f"일괄 합성 불가 (대상 없음) -> [취소] 터치 후 [캠프] 복귀 (신뢰도 {s_can*100:.1f}%)"
                target_coords = c_can
            elif m_synth and s_synth >= 0.80:
                desc = f"펫 인벤토리 화면 -> 중앙 [합성] 버튼 터치 (신뢰도 {s_synth*100:.1f}%)"
                target_coords = c_synth
            elif m_pet and s_pet >= 0.80:
                desc = f"인벤토리 화면 -> 서브탭 [펫] 터치 (신뢰도 {s_pet*100:.1f}%)"
                target_coords = c_pet
            elif m_camp and s_camp >= 0.80:
                desc = f"캠프 메인 화면 -> 하단 [인벤토리] 탭 터치 (신뢰도 {s_inv*100:.1f}%)"
                target_coords = c_inv
            else:
                desc = "펫 합성 화면 (터치 타겟 대기)"
                target_coords = (fw // 2, fh // 2)

            self._log(f"[샘플 진단: {filename}] 🐾 {desc} (클릭 좌표: {target_coords})")

            cv2.rectangle(overlay, (0, 0), (fw, 36), (180, 100, 40), -1)
            cv2.putText(overlay, f"PET SYNTHESIS: {desc}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            if target_coords:
                cv2.circle(overlay, target_coords, 25, (0, 255, 255), 2)
                cv2.drawMarker(overlay, target_coords, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

            self._update_preview(overlay)
            return

        # 모드 판별: 파일명이 '일반_810'으로 시작하거나 현재 모드가 STAGE_FARMING이면 stage_farming 적용
        cur_mode = self.mode_combo.currentData()
        if "810" in filename or cur_mode == MacroWorker.MODE_STAGE_FARMING:
            eval_mode = MacroWorker.MODE_STAGE_FARMING
        else:
            eval_mode = MacroWorker.MODE_FULL_AUTO

        cur_stage = self.target_stage_spin.value()
        state, score, target_coords = self.detector.analyze_screen_state(
            frame, mode=eval_mode, target_stage=cur_stage
        )
        code = None

        if state == "POPUP":
            is_p, p_sc, loc = self.detector.detect_popup(frame)
            crop, _ = self.detector.get_display_crop(frame, loc)
            code, conf = self.ocr.recognize(crop)
            self._log(f"[샘플 진단: {filename}] 매크로 방지 팝업 감지! (일치율: {score*100:.1f}%) -> 4자리 번호: [{code}]")
            overlay = self.detector.draw_debug_overlay(frame, True, score, code, state=state, popup_loc=loc)
        else:
            st_kr = {
                "CAMP": "캠프 메인 (중앙 하단 던전 버튼 감지)",
                "DUNGEON_POPUP": "던전 선택 (랭킹 탭 & 심연의 모래 구멍 감지)",
                "STAGE_TAB_GENERAL": "던전 선택 (상단 일반 탭 선택 필요)",
                "STAGE_810_READY": f"Stage {cur_stage} 준비 완료 -> 우측 [입장] 버튼 터치 (소탕 아님!)",
                "STAGE_TARGET_READY": f"Stage {cur_stage} 준비 완료 -> 우측 [입장] 버튼 터치 (소탕 아님!)",
                "STAGE_NEED_PREV": f"Stage {cur_stage} 아님 -> 좌측 [<- 이전] 버튼 터치",
                "STAGE_NEED_NEXT": f"Stage {cur_stage} 아님 -> 우측 [-> 다음] 버튼 터치",
                "IN_GAME": "인게임 일반 웨이브 진행 중 (전투 화면)",
                "FINAL_WAVE": "Final Wave 보스 등장! -> 우측 상단 햄버거 메뉴 터치",
                "GIVEUP_SETTING": "인게임 설정창 -> [포기하기] 버튼 터치",
                "GIVEUP_CONFIRM": "게임 종료 확인 팝업 -> [예] 버튼 터치",
                "GAMEOVER": "게임 오버 (패배 - 광고 x2 버튼 감지)",
                "REWARD": "획득 보상 (확인 버튼 감지)",
                "RANK_REWARD": "정기/랭킹 보상 상자 (하단 [받기] 버튼 감지)",
                "APP_CRASHED": "앱 튕김 감지 -> UnderDark 아이콘 자동 터치하여 재실행"
            }.get(state, state)
            self._log(f"[샘플 진단: {filename}] 판별 상태: [{st_kr}] (신뢰도: {score*100:.1f}%, 클릭 좌표: {target_coords})")
            overlay = self.detector.draw_debug_overlay(frame, False, score, code, state=state, target_coords=target_coords)

            # 인게임 전투 화면인 경우 타워 슬롯 인식 및 외곽 자동 배치 시뮬레이션 표시
            if state == "IN_GAME" and self.auto_tower_chk.isChecked():
                plan = self.detector.plan_next_tower_placement(frame)
                if plan is not None:
                    tw = plan["tower"]
                    sx, sy = plan["start_coords"]
                    dx, dy = plan["drop_coords"]
                    rx1, ry1, rx2, ry2 = plan["drop_rect"]
                    avail_names = ", ".join(f"{t['name']}({t['grid_w']}*{t['grid_h']})" for t in plan["all_available"])
                    self._log(
                        f"[타워 진단: {filename}] 🏰 감지된 타워 목록(앞쪽 순): [{avail_names}] "
                        f"| 1순위 배치: [{tw['name']}] ({sx}, {sy}) -> 외곽 목표 ({dx}, {dy}) [장애물 {len(plan['obstacles'])}개 회피]"
                    )
                    for ox1, oy1, ox2, oy2 in plan["obstacles"]:
                        cv2.rectangle(overlay, (ox1, oy1), (ox2, oy2), (0, 0, 220), 1)
                    for t_info in plan["all_available"]:
                        tx, ty = t_info["slot_coords"]
                        cv2.circle(overlay, (tx, ty), 14, (255, 200, 0), 2)
                    cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (0, 255, 120), 2)
                    cv2.circle(overlay, (sx, sy), 18, (0, 255, 255), 2)
                    cv2.arrowedLine(overlay, (sx, sy), (dx, dy), (0, 255, 120), 3, tipLength=0.05)

        self._update_preview(overlay)

    def _load_settings(self):
        """앱 시작 시 이전에 저장된 사용자 설정값을 복원"""
        settings = QSettings("UnderDarkMacro", "UnderdarkMacroSolver")

        # 1. 동작 모드 (기본: 심연의 모래 구멍 full_auto)
        saved_mode = settings.value("macro_mode", MacroWorker.MODE_FULL_AUTO, type=str)
        idx = self.mode_combo.findData(saved_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        else:
            self.mode_combo.setCurrentIndex(0)

        # 2. 목표 스테이지 번호 (기본 810)
        self.target_stage_spin.setValue(settings.value("target_stage", 810, type=int))

        # 3. 반복 횟수, 검사 주기, 터치 딜레이
        self.runs_spin.setValue(settings.value("max_runs", 0, type=int))
        self.interval_spin.setValue(settings.value("check_interval", 0.6, type=float))
        self.delay_spin.setValue(settings.value("tap_delay", 80, type=int))

        # 4. 체크박스 옵션
        self.pin_bypass_chk.setChecked(settings.value("pin_bypass", True, type=bool))
        self.confirm_chk.setChecked(settings.value("auto_confirm", True, type=bool))
        self.app_restart_chk.setChecked(settings.value("app_restart", True, type=bool))
        self.auto_tower_chk.setChecked(settings.value("auto_place_tower", True, type=bool))

        # 5. 초기 조작 옵션
        self.init_cmd_chk.setChecked(settings.value("init_cmd_enabled", False, type=bool))
        saved_cmd_type = settings.value("init_cmd_type", "drag_right", type=str)
        c_idx = self.cmd_type_combo.findData(saved_cmd_type)
        if c_idx >= 0:
            self.cmd_type_combo.setCurrentIndex(c_idx)
        self.cmd_dur_spin.setValue(settings.value("init_cmd_duration", 200, type=int))

        # 6. 펫 자동 일괄 합성 옵션
        self.pet_synth_chk.setChecked(settings.value("pet_synth_enabled", True, type=bool))
        self.pet_interval_spin.setValue(settings.value("pet_synth_interval", 5, type=int))

        # 7. 마지막 연결 디바이스 시리얼
        self.saved_device_serial = settings.value("last_device_serial", "", type=str)

        # 컨트롤 변경 시 설정 자동 저장 연결
        self.mode_combo.currentIndexChanged.connect(self._save_settings)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.target_stage_spin.valueChanged.connect(self._save_settings)
        self.runs_spin.valueChanged.connect(self._save_settings)
        self.interval_spin.valueChanged.connect(self._save_settings)
        self.delay_spin.valueChanged.connect(self._save_settings)
        self.pin_bypass_chk.toggled.connect(self._save_settings)
        self.confirm_chk.toggled.connect(self._save_settings)
        self.app_restart_chk.toggled.connect(self._save_settings)
        self.auto_tower_chk.toggled.connect(self._save_settings)
        self.init_cmd_chk.toggled.connect(self._save_settings)
        self.cmd_type_combo.currentIndexChanged.connect(self._save_settings)
        self.cmd_dur_spin.valueChanged.connect(self._save_settings)
        self.pet_synth_chk.toggled.connect(self._save_settings)
        self.pet_interval_spin.valueChanged.connect(self._save_settings)

        self._on_mode_changed()

    def _save_settings(self):
        """사용자가 변경한 설정값을 QSettings(Windows 레지스트리)에 영구 저장"""
        settings = QSettings("UnderDarkMacro", "UnderdarkMacroSolver")
        settings.setValue("macro_mode", self.mode_combo.currentData())
        settings.setValue("target_stage", self.target_stage_spin.value())
        settings.setValue("max_runs", self.runs_spin.value())
        settings.setValue("check_interval", self.interval_spin.value())
        settings.setValue("tap_delay", self.delay_spin.value())
        settings.setValue("pin_bypass", self.pin_bypass_chk.isChecked())
        settings.setValue("auto_confirm", self.confirm_chk.isChecked())
        settings.setValue("app_restart", self.app_restart_chk.isChecked())
        settings.setValue("auto_place_tower", self.auto_tower_chk.isChecked())
        settings.setValue("init_cmd_enabled", self.init_cmd_chk.isChecked())
        settings.setValue("init_cmd_type", self.cmd_type_combo.currentData())
        settings.setValue("init_cmd_duration", self.cmd_dur_spin.value())
        settings.setValue("pet_synth_enabled", self.pet_synth_chk.isChecked())
        settings.setValue("pet_synth_interval", self.pet_interval_spin.value())
        if hasattr(self, 'saved_device_serial') and self.saved_device_serial:
            settings.setValue("last_device_serial", self.saved_device_serial)

    def closeEvent(self, event):
        self._save_settings()
        self._stop_worker()
        if self.adb.is_connected:
            self.adb.disconnect()
        event.accept()
