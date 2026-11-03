"""
코스피200 크롤러 (PyQt6 GUI)
- 대상: https://stock.naver.com/market/stock/kr (코스피200)
- 이 페이지는 Next.js 로 만들어져 시세를 브라우저에서 JavaScript 로 불러온다.
  그래서 requests + BeautifulSoup4 로 HTML 을 받으면 숫자가 비어 있다.
  대신 페이지가 내부적으로 호출하는 JSON API 를 직접 호출한다.
- 지수 현재가 / 구성종목 전체 / 최근 일별 시세를 화면에 보여주고 CSV, 엑셀로 저장
"""
import csv
import sys
import time
import webbrowser
from datetime import datetime

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

API = "https://m.stock.naver.com/api/index/KPI200"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/market/stock/kr",
}
PAGE_SIZE = 50  # 100 이상은 400 에러
DAILY_COUNT = 20  # 일별 시세 표시 일수
AUTO_REFRESH_SEC = 30

STOCK_COLUMNS = ["순위", "종목코드", "종목명", "현재가", "전일대비", "등락률(%)",
                 "거래량", "거래대금(백만)", "시가총액(억)"]
STOCK_WIDTHS = [56, 70, 0, 90, 82, 78, 96, 108, 104]  # 0: 남는 폭 채우기
DAILY_COLUMNS =["날짜", "종가", "전일대비", "등락률(%)", "시가", "고가", "저가"]

# ---------------------------------------------------------------------------
# 디자인 (색상 + Qt 스타일시트)
# ---------------------------------------------------------------------------
BG = "#F4F5F7"
CARD = "#FFFFFF"
BORDER = "#E6E8EC"
TEXT = "#1F2328"
MUTED = "#6B7280"
ACCENT = "#3B5BDB"
ACCENT_HOVER = "#3249B8"
SELECT = "#EEF2FF"
UP = "#E03131"    # 상승: 빨강 (국내 증시 관례)
DOWN = "#1C7ED6"  # 하락: 파랑

STYLESHEET = f"""
QWidget#root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-size: 10pt; }}

QLabel#appTitle {{ font-size: 20pt; font-weight: 700; }}
QLabel#appSubtitle {{ color: {MUTED}; }}
QLabel#sectionTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#status {{ color: {MUTED}; font-size: 9pt; }}
QLabel#indexName {{ color: {MUTED}; font-weight: 600; }}
QLabel#indexPrice {{ font-size: 26pt; font-weight: 700; }}
QLabel#indexChange {{ font-size: 13pt; font-weight: 600; }}
QLabel#indexMeta {{ color: {MUTED}; font-size: 9pt; }}

QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 18px;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}

QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {BG}; }}
QPushButton:disabled {{ color: #B0B5BD; background: {CARD}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; border: none; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #A5B4EC; color: white; }}
QPushButton#ghost {{ padding: 5px 14px; font-size: 9pt; }}

QCheckBox {{ color: {MUTED}; spacing: 6px; }}

QTableWidget {{
    background: {CARD};
    border: none;
    selection-background-color: {SELECT};
    selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 0 8px; border-bottom: 1px solid #F0F1F3; }}
QTableWidget::item:selected {{ background: {SELECT}; }}
QHeaderView::section {{
    background: {CARD};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-size: 9pt;
    font-weight: 600;
}}
QTableCornerButton::section {{ background: {CARD}; border: none; }}

QSplitter::handle {{ background: transparent; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #D5D8DE; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #BCC1C9; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #D5D8DE; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""


# ---------------------------------------------------------------------------
# 크롤링 함수
# ---------------------------------------------------------------------------
def get_json(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_index_summary():
    """코스피200 지수 현재가"""
    d = get_json(f"{API}/basic")
    return {
        "지수명": d.get("stockName", "코스피 200"),
        "현재가": d.get("closePrice", ""),
        "전일대비": d.get("compareToPreviousClosePrice", ""),
        "등락률(%)": d.get("fluctuationsRatio", ""),
        "장상태": d.get("marketStatus", ""),
        "기준시각": d.get("localTradedAt", ""),
    }


def fetch_daily_prices(count=DAILY_COUNT):
    """코스피200 최근 일별 시세"""
    rows = get_json(f"{API}/price", {"page": 1, "pageSize": count})
    return [
        {
            "날짜": r["localTradedAt"],
            "종가": float(r["closePrice"].replace(",", "")),
            "전일대비": float(r["compareToPreviousClosePrice"].replace(",", "")),
            "등락률(%)": float(r["fluctuationsRatio"]),
            "시가": float(r["openPrice"].replace(",", "")),
            "고가": float(r["highPrice"].replace(",", "")),
            "저가": float(r["lowPrice"].replace(",", "")),
        }
        for r in rows
    ]


def fetch_constituents():
    """코스피200 구성종목 전체 (시가총액 순)"""
    result, seen, page = [], set(), 1
    while True:
        rows = get_json(f"{API}/enrollStocks", {"page": page, "pageSize": PAGE_SIZE})
        if not rows:
            break
        for r in rows:
            if r["itemCode"] in seen:
                continue
            seen.add(r["itemCode"])
            result.append(
                {
                    "순위": len(result) + 1,
                    "종목코드": r["itemCode"],
                    "종목명": r["stockName"],
                    "현재가": int(r["closePriceRaw"]),
                    "전일대비": int(r["compareToPreviousClosePriceRaw"]),
                    "등락률(%)": float(r["fluctuationsRatio"]),
                    "거래량": int(r["accumulatedTradingVolumeRaw"]),
                    "거래대금(백만)": int(r["accumulatedTradingValueRaw"]) // 1_000_000,
                    "시가총액(억)": int(r["marketValueRaw"]) // 100_000_000,
                    "기준시각": r["localTradedAt"],
                    "URL": r.get("newPcUrl") or f"https://stock.naver.com/domestic/stock/{r['itemCode']}",
                }
            )
        page += 1
        time.sleep(0.2)  # 서버 부담 줄이기
    return result


# ---------------------------------------------------------------------------
# 백그라운드 작업 스레드 (크롤링 중에도 화면이 멈추지 않도록)
# ---------------------------------------------------------------------------
class FetchWorker(QThread):
    done = pyqtSignal(dict, list, list)  # (지수, 구성종목, 일별 시세)
    failed = pyqtSignal(str)

    def run(self):
        try:
            summary = fetch_index_summary()
            daily = fetch_daily_prices()
            stocks = fetch_constituents()
        except (requests.RequestException, KeyError, ValueError) as e:
            self.failed.emit(str(e))
            return
        self.done.emit(summary, stocks, daily)


class NumberItem(QTableWidgetItem):
    """숫자 기준으로 정렬되는 표 셀 (문자열 정렬 방지)"""

    def __init__(self, value, text):
        super().__init__(text)
        self.value = value
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, NumberItem):
            return self.value < other.value
        return super().__lt__(other)


def change_color(value):
    if value > 0:
        return QColor(UP)
    if value < 0:
        return QColor(DOWN)
    return QColor(TEXT)


def make_table(columns):
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setShowGrid(False)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(34)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setMinimumSectionSize(60)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)  # 처음엔 첫 열 오름차순
    return table


# ---------------------------------------------------------------------------
# 메인 화면
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 크롤러")
        self.resize(1480, 860)
        self.summary = {}
        self.stocks = []
        self.daily = []
        self.worker = None

        # 상단 머리말: 제목 + 설명
        title = QLabel("코스피200")
        title.setObjectName("appTitle")
        subtitle = QLabel("네이버페이 증권에서 코스피200 지수와 구성종목 시세를 가져옵니다")
        subtitle.setObjectName("appSubtitle")

        # 지수 카드: 현재가 + 등락 + 조작 버튼
        self.index_name = QLabel("코스피 200")
        self.index_name.setObjectName("indexName")
        self.index_price = QLabel("-")
        self.index_price.setObjectName("indexPrice")
        self.index_change = QLabel("")
        self.index_change.setObjectName("indexChange")
        self.index_meta = QLabel("")
        self.index_meta.setObjectName("indexMeta")

        price_row = QHBoxLayout()
        price_row.setSpacing(14)
        price_row.addWidget(self.index_price)
        price_row.addWidget(self.index_change, 0, Qt.AlignmentFlag.AlignBottom)
        price_row.addStretch(1)

        index_info = QVBoxLayout()
        index_info.setSpacing(2)
        index_info.addWidget(self.index_name)
        index_info.addLayout(price_row)
        index_info.addWidget(self.index_meta)

        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.setObjectName("primary")
        self.refresh_btn.clicked.connect(self.start_fetch)
        self.auto_check = QCheckBox(f"{AUTO_REFRESH_SEC}초마다 자동 갱신")
        self.auto_check.toggled.connect(self.toggle_auto)
        self.csv_btn = QPushButton("CSV")
        self.csv_btn.setObjectName("ghost")
        self.csv_btn.setEnabled(False)
        self.csv_btn.clicked.connect(self.save_csv)
        self.excel_btn = QPushButton("Excel")
        self.excel_btn.setObjectName("ghost")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_row.addWidget(self.csv_btn)
        save_row.addWidget(self.excel_btn)
        controls = QVBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.auto_check)
        controls.addLayout(save_row)

        index_row = QHBoxLayout()
        index_row.addLayout(index_info, 1)
        index_row.addLayout(controls)
        index_card = self.make_card(index_row)

        # 구성종목 카드: 건수 + 검색 + 표
        self.stock_count = QLabel("구성종목")
        self.stock_count.setObjectName("sectionTitle")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("종목명 또는 코드 검색")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setFixedWidth(220)
        self.filter_edit.textChanged.connect(self.apply_filter)

        stock_head = QHBoxLayout()
        stock_head.addWidget(self.stock_count)
        stock_head.addStretch(1)
        stock_head.addWidget(self.filter_edit)

        self.stock_table = make_table(STOCK_COLUMNS)
        # 숫자 열은 고정 폭(마우스로 조절 가능), 종목명이 남는 폭을 차지
        stock_header = self.stock_table.horizontalHeader()
        for col, width in enumerate(STOCK_WIDTHS):
            if width:
                stock_header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
                self.stock_table.setColumnWidth(col, width)
        self.stock_table.setToolTip("더블클릭: 네이버페이 증권에서 종목 열기")
        self.stock_table.cellDoubleClicked.connect(self.open_stock)

        stock_layout = QVBoxLayout()
        stock_layout.setSpacing(10)
        stock_layout.addLayout(stock_head)
        stock_layout.addWidget(self.stock_table, 1)
        stock_card = self.make_card(stock_layout)

        # 일별 시세 카드
        daily_title = QLabel(f"일별 시세 (최근 {DAILY_COUNT}일)")
        daily_title.setObjectName("sectionTitle")
        self.daily_table = make_table(DAILY_COLUMNS)
        self.daily_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        daily_layout = QVBoxLayout()
        daily_layout.setSpacing(10)
        daily_layout.addWidget(daily_title)
        daily_layout.addWidget(self.daily_table, 1)
        daily_card = self.make_card(daily_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(16)
        splitter.addWidget(stock_card)
        splitter.addWidget(daily_card)
        splitter.setSizes([860, 560])

        self.status_label = QLabel("새로고침을 눌러 시세를 불러오세요")
        self.status_label.setObjectName("status")

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addSpacing(2)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(index_card)
        layout.addSpacing(16)
        layout.addWidget(splitter, 1)
        layout.addSpacing(10)
        layout.addWidget(self.status_label)

        central = QWidget()
        central.setObjectName("root")
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.setInterval(AUTO_REFRESH_SEC * 1000)
        self.timer.timeout.connect(self.start_fetch)

        # 시작하자마자 한 번 불러오기
        QTimer.singleShot(0, self.start_fetch)

    @staticmethod
    def make_card(inner_layout):
        """흰 배경의 둥근 카드 위젯으로 감싸기"""
        card = QFrame()
        card.setObjectName("card")
        inner_layout.setContentsMargins(16, 14, 16, 14)
        card.setLayout(inner_layout)
        return card

    # --- 데이터 불러오기 ---
    def start_fetch(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = FetchWorker()
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("시세를 불러오는 중...")

    def toggle_auto(self, checked):
        if checked:
            self.timer.start()
        else:
            self.timer.stop()

    def on_failed(self, error):
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"불러오기 실패: {error}")

    def on_done(self, summary, stocks, daily):
        self.summary, self.stocks, self.daily = summary, stocks, daily
        self.refresh_btn.setEnabled(True)
        self.csv_btn.setEnabled(True)
        self.excel_btn.setEnabled(True)
        self.show_summary()
        self.fill_stock_table()
        self.fill_daily_table()
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(
            f"{now} 갱신  ·  구성종목 {len(stocks)}개  ·  일별 시세 {len(daily)}일"
        )

    # --- 화면 채우기 ---
    def show_summary(self):
        s = self.summary
        self.index_name.setText(s["지수명"])
        self.index_price.setText(s["현재가"])
        try:
            diff = float(s["전일대비"].replace(",", ""))
        except ValueError:
            diff = 0
        arrow = "▲" if diff > 0 else "▼" if diff < 0 else ""
        self.index_change.setText(f"{arrow} {abs(diff):,.2f}  ({s['등락률(%)']}%)")
        self.index_change.setStyleSheet(f"color: {change_color(diff).name()};")
        status = {"OPEN": "장중", "CLOSE": "장마감", "PREOPEN": "장전"}.get(s["장상태"], s["장상태"])
        traded = s["기준시각"].replace("T", " ")[:16]
        self.index_meta.setText(f"{status}  ·  {traded} 기준")

    def fill_stock_table(self):
        table = self.stock_table
        table.setSortingEnabled(False)  # 채우는 동안 정렬이 끼어들지 않도록
        table.setRowCount(len(self.stocks))
        for row, s in enumerate(self.stocks):
            color = change_color(s["전일대비"])
            cells = [
                NumberItem(s["순위"], str(s["순위"])),
                QTableWidgetItem(s["종목코드"]),
                QTableWidgetItem(s["종목명"]),
                NumberItem(s["현재가"], f"{s['현재가']:,}"),
                NumberItem(s["전일대비"], f"{s['전일대비']:+,}"),
                NumberItem(s["등락률(%)"], f"{s['등락률(%)']:+.2f}"),
                NumberItem(s["거래량"], f"{s['거래량']:,}"),
                NumberItem(s["거래대금(백만)"], f"{s['거래대금(백만)']:,}"),
                NumberItem(s["시가총액(억)"], f"{s['시가총액(억)']:,}"),
            ]
            # 더블클릭 시 열 URL 을 첫 칸에 보관 (정렬해도 행과 함께 이동)
            cells[0].setData(Qt.ItemDataRole.UserRole, s["URL"])
            for col, item in enumerate(cells):
                if STOCK_COLUMNS[col] in ("현재가", "전일대비", "등락률(%)"):
                    item.setForeground(color)
                table.setItem(row, col, item)
        table.setSortingEnabled(True)
        self.apply_filter()

    def fill_daily_table(self):
        table = self.daily_table
        table.setRowCount(len(self.daily))
        for row, d in enumerate(self.daily):
            color = change_color(d["전일대비"])
            cells = [
                QTableWidgetItem(d["날짜"]),
                NumberItem(d["종가"], f"{d['종가']:,.2f}"),
                NumberItem(d["전일대비"], f"{d['전일대비']:+,.2f}"),
                NumberItem(d["등락률(%)"], f"{d['등락률(%)']:+.2f}"),
                NumberItem(d["시가"], f"{d['시가']:,.2f}"),
                NumberItem(d["고가"], f"{d['고가']:,.2f}"),
                NumberItem(d["저가"], f"{d['저가']:,.2f}"),
            ]
            for col, item in enumerate(cells):
                if DAILY_COLUMNS[col] in ("종가", "전일대비", "등락률(%)"):
                    item.setForeground(color)
                table.setItem(row, col, item)

    # --- 화면 동작 ---
    def apply_filter(self):
        keyword = self.filter_edit.text().strip().lower()
        code_col, name_col = STOCK_COLUMNS.index("종목코드"), STOCK_COLUMNS.index("종목명")
        shown = 0
        for row in range(self.stock_table.rowCount()):
            code = self.stock_table.item(row, code_col).text()
            name = self.stock_table.item(row, name_col).text().lower()
            hide = bool(keyword) and keyword not in name and keyword not in code
            self.stock_table.setRowHidden(row, hide)
            shown += not hide
        total = self.stock_table.rowCount()
        text = f"구성종목  ·  {total}개" if shown == total else f"구성종목  ·  {shown}/{total}개"
        self.stock_count.setText(text)

    def open_stock(self, row, _col):
        url = self.stock_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if url:
            webbrowser.open(url)

    def save_csv(self):
        if not self.stocks:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV 저장 (구성종목)", "kospi200_stocks.csv", "CSV 파일 (*.csv)"
        )
        if not path:
            return
        # 일별 시세는 같은 폴더에 _daily 를 붙여 함께 저장
        daily_path = path[:-4] + "_daily.csv" if path.lower().endswith(".csv") else path + "_daily.csv"
        try:
            for rows, p in ((self.stocks, path), (self.daily, daily_path)):
                with open(p, "w", newline="", encoding="utf-8-sig") as f:  # 엑셀 한글 깨짐 방지
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
        except PermissionError:
            QMessageBox.warning(self, "저장 실패", "파일이 다른 프로그램(엑셀 등)에서 열려 있는지 확인하세요.")
            return
        self.status_label.setText(f"저장했습니다: {path}, {daily_path}")

    def save_excel(self):
        if not self.stocks:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀 저장", "kospi200.xlsx", "엑셀 파일 (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        wb = Workbook()
        ws_stock = wb.active
        ws_stock.title = "구성종목"
        self.write_sheet(ws_stock, self.stocks, number_formats={
            "현재가": "#,##0", "전일대비": "+#,##0;-#,##0;0", "등락률(%)": "+0.00;-0.00;0.00",
            "거래량": "#,##0", "거래대금(백만)": "#,##0", "시가총액(억)": "#,##0",
        })
        # URL 은 클릭하면 열리도록 하이퍼링크로 설정
        url_col = list(self.stocks[0].keys()).index("URL") + 1
        for row in range(2, ws_stock.max_row + 1):
            cell = ws_stock.cell(row=row, column=url_col)
            cell.hyperlink = cell.value
            cell.font = Font(color="0563C1", underline="single")

        ws_daily = wb.create_sheet("일별 시세")
        self.write_sheet(ws_daily, self.daily, number_formats={
            key: "#,##0.00" for key in ("종가", "시가", "고가", "저가")
        } | {"전일대비": "+#,##0.00;-#,##0.00;0.00", "등락률(%)": "+0.00;-0.00;0.00"})

        try:
            wb.save(path)
        except PermissionError:
            QMessageBox.warning(self, "저장 실패", "파일이 다른 프로그램(엑셀 등)에서 열려 있는지 확인하세요.")
            return
        self.status_label.setText(f"엑셀로 저장했습니다: {path}")

    @staticmethod
    def write_sheet(ws, rows, number_formats):
        """머리글(굵게 + 배경색, 첫 행 고정) + 데이터 + 열 너비"""
        keys = list(rows[0].keys())
        ws.append(keys)
        header_fill = PatternFill("solid", fgColor="DDEBF7")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.freeze_panes = "A2"

        for r in rows:
            ws.append([r[k] for k in keys])
        for col, key in enumerate(keys, 1):
            letter = ws.cell(row=1, column=col).column_letter
            if key in number_formats:
                for cell in ws[letter][1:]:
                    cell.number_format = number_formats[key]
            width = max(len(str(r[key])) for r in rows)
            ws.column_dimensions[letter].width = min(max(width, len(key) * 2) + 2, 60)
        ws.auto_filter.ref = ws.dimensions

    def closeEvent(self, event):
        # 창을 닫을 때 작업 중인 스레드 정리
        self.timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.wait(5000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Malgun Gothic", 10))
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
