DARK_THEME_QSS = """
/* 기본 위젯 스타일 */
QWidget {
    background-color: #16181D;
    color: #E2E8F0;
    font-family: "Segoe UI", "Apple SD Gothic Neo", "맑은 고딕", sans-serif;
    font-size: 13px;
}

/* 메인 윈도우 */
QMainWindow {
    background-color: #111216;
}

/* 그룹 박스 */
QGroupBox {
    border: 1px solid #2D3748;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #A0AEC0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #16181D;
    color: #00E676;
}

/* 레이블 */
QLabel {
    color: #E2E8F0;
}

/* 입력 필드 & 콤보박스 */
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: #1E222B;
    border: 1px solid #323A48;
    border-radius: 6px;
    padding: 5px 10px;
    color: #FFFFFF;
    selection-background-color: #00E676;
    selection-color: #111216;
}

QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #00E676;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: 1px solid #323A48;
}

/* 체크박스 */
QCheckBox {
    color: #E2E8F0;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #3E4C63;
    border-radius: 4px;
    background-color: #1E222B;
}

QCheckBox::indicator:hover {
    border: 1px solid #00E676;
}

QCheckBox::indicator:checked {
    background-color: #00E676;
    border: 1px solid #00E676;
    image: none;
}


/* 푸시 버튼 */
QPushButton {
    background-color: #2D3748;
    border: 1px solid #3E4C63;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: bold;
    color: #FFFFFF;
}

QPushButton:hover {
    background-color: #3B475C;
    border: 1px solid #4D5E7B;
}

QPushButton:pressed {
    background-color: #232B38;
}

/* 주요 실행 버튼 (스타트) */
QPushButton#startBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00C853, stop:1 #00E676);
    color: #0B1911;
    border: none;
    font-size: 14px;
    padding: 9px 20px;
}

QPushButton#startBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E676, stop:1 #69F0AE);
}

QPushButton#startBtn:disabled {
    background: #233529;
    color: #4A6353;
}

/* 정지 버튼 */
QPushButton#stopBtn {
    background-color: #E53E3E;
    color: #FFFFFF;
    border: none;
    font-size: 14px;
    padding: 9px 20px;
}

QPushButton#stopBtn:hover {
    background-color: #F56565;
}

QPushButton#stopBtn:disabled {
    background-color: #3C2222;
    color: #6E4545;
}

/* 텍스트 에디트 (로그 뷰어) */
QTextEdit {
    background-color: #0E1015;
    border: 1px solid #232936;
    border-radius: 6px;
    color: #A0AEC0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}

/* 스크롤바 */
QScrollBar:vertical {
    border: none;
    background: #111216;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2D3748;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #4A5568;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 통계 카드 */
QFrame.statCard {
    background-color: #1E222B;
    border: 1px solid #2B3342;
    border-radius: 8px;
    padding: 10px;
}
"""
