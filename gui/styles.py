"""
Modern Dark Theme QSS Stylesheet for the FitGirl Repack Downloader.
Inspired by Windows 11 Fluent Design.
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #181818;
    color: #ffffff;
}

QWidget {
    background-color: #181818;
    color: #f0f0f0;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #202020;
    border-right: 1px solid #2d2d2d;
    min-width: 210px;
    max-width: 210px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #bbbbbb;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

#sidebar QPushButton:hover {
    background-color: #2b2b2b;
    color: #ffffff;
}

#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {
    background-color: #0078d4;
    color: #ffffff;
    font-weight: 600;
}

/* Cards & Content Containers */
.QFrame, #card {
    background-color: #242424;
    border: 1px solid #323232;
    border-radius: 8px;
    padding: 12px;
}

/* Metric Cards */
#metricCard {
    background-color: #252525;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 14px;
}

#metricTitle {
    color: #888888;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}

#metricValue {
    color: #00a4ef;
    font-size: 20px;
    font-weight: 700;
}

/* Headers */
QLabel#viewHeader {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 6px;
}

QLabel#viewSubtitle {
    font-size: 12px;
    color: #888888;
    margin-bottom: 12px;
}

/* Primary Action Buttons */
QPushButton#primaryButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #1084d9;
}

QPushButton#primaryButton:pressed {
    background-color: #006cbe;
}

QPushButton#primaryButton:disabled {
    background-color: #333333;
    color: #666666;
}

/* Secondary Buttons */
QPushButton {
    background-color: #2e2e2e;
    color: #ffffff;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383838;
    border-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #242424;
}

/* Line Edits */
QLineEdit {
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #0078d4;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
    background-color: #232323;
}

/* Progress Bars */
QProgressBar {
    background-color: #202020;
    border: 1px solid #333333;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078d4, stop:1 #00bcf2);
    border-radius: 5px;
}

/* Tables */
QTableWidget {
    background-color: #202020;
    border: 1px solid #303030;
    border-radius: 6px;
    gridline-color: #2b2b2b;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #282828;
}

QHeaderView::section {
    background-color: #262626;
    color: #aaaaaa;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #333333;
    font-weight: 600;
}

/* Text Edit (Logs) */
QTextEdit {
    background-color: #161616;
    color: #cccccc;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #303030;
    border-radius: 6px;
    padding: 8px;
}

/* ScrollBars */
QScrollBar:vertical {
    background-color: #181818;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #3a3a3a;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4a4a4a;
}
"""
