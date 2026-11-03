"""
네이버 뉴스 크롤러 (PyQt6 GUI)
- 검색어로 네이버 검색 결과에서 뉴스 기사 링크를 찾아 본문까지 크롤링
- requests + BeautifulSoup4 로 크롤링, PyQt6 로 화면 구성
- 결과는 표로 보여주고, 선택한 기사의 본문을 아래에 표시, CSV 로 저장 가능
"""
import csv
import html
import re
import sys
import time
import webbrowser
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://www.naver.com/",
}

# 검색 범위: 화면 표시 이름 -> 네이버 where 파라미터
SEARCH_TYPES = {
    "통합검색": "nexearch",
    "뉴스 탭": "news",
}

# 네이버 뉴스 기사 URL 패턴 (n.news.naver.com/mnews/article/언론사코드/기사번호)
ARTICLE_RE = re.compile(r"https?://n\.news\.naver\.com/(?:mnews/)?article/(\d+)/(\d+)")

COLUMNS = ["title", "press", "date", "reporter", "url", "body"]
COLUMN_LABELS = ["제목", "언론사", "날짜", "기자", "URL"]

# 엑셀 저장 시 열 이름과 열 너비
EXCEL_HEADERS = ["제목", "언론사", "날짜", "기자", "URL", "본문"]
EXCEL_WIDTHS = [50, 12, 20, 30, 50, 100]

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

STYLESHEET = f"""
QWidget#root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-size: 10pt; }}

QLabel#appTitle {{ font-size: 20pt; font-weight: 700; }}
QLabel#appSubtitle {{ color: {MUTED}; }}
QLabel#sectionTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#status {{ color: {MUTED}; font-size: 9pt; }}

QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit, QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {MUTED}; background: {BG}; }}
QComboBox {{ min-width: 90px; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER};
    selection-background-color: {SELECT};
    selection-color: {TEXT};
    outline: none;
}}

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

QTableWidget {{
    background: {CARD};
    border: none;
    selection-background-color: {SELECT};
    selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 0 8px; border-bottom: 1px solid #F0F1F3; }}
QTableWidget::item:selected {{ background: {SELECT}; color: {TEXT}; }}
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

QTextEdit#bodyView {{
    background: {CARD};
    border: none;
    font-size: 10.5pt;
}}

QSplitter::handle {{ background: transparent; }}

QProgressBar {{ background: {BORDER}; border: none; border-radius: 2px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}

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
def build_search_url(query, where):
    return (
        f"https://search.naver.com/search.naver?where={where}"
        f"&sm=top_hty&fbm=0&ie=utf8&query={quote(query)}"
    )


def get_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def collect_article_links(search_url):
    """검색 결과 페이지에서 네이버뉴스 기사 링크를 중복 없이 수집"""
    soup = get_soup(search_url)
    links = []
    seen = set()

    def add(m):
        url = f"https://n.news.naver.com/mnews/article/{m.group(1)}/{m.group(2)}"
        if url not in seen:
            seen.add(url)
            links.append(url)

    # 1) <a> 태그의 href 에서 찾기
    for a in soup.find_all("a", href=True):
        m = ARTICLE_RE.search(a["href"])
        if m:
            add(m)

    # 2) 통합검색은 일부 기사 링크가 <script> 데이터 안에만 있으므로 함께 수집
    for script in soup.find_all("script"):
        text = (script.string or "").replace("\\/", "/")
        for m in ARTICLE_RE.finditer(text):
            add(m)
    return links


def select_text(soup, *selectors):
    """여러 선택자 중 처음 찾은 요소의 텍스트 반환"""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(" ", strip=True)
    return ""


def parse_article(url):
    """기사 페이지에서 제목/언론사/날짜/기자/본문 추출"""
    soup = get_soup(url)

    title = select_text(soup, "#title_area", "h2.media_end_head_headline", "h4.title")

    press_img = soup.select_one(".media_end_head_top_logo img")
    press = press_img.get("alt", "") if press_img else ""

    date_el = soup.select_one("span.media_end_head_info_datestamp_time")
    date = date_el.get("data-date-time", date_el.get_text(strip=True)) if date_el else ""

    reporter = select_text(soup, ".byline_s", ".media_end_head_journalist_name")

    body_el = soup.select_one("#dic_area") or soup.select_one("#articeBody")
    body = ""
    if body_el:
        # 사진 설명, 스크립트 등 본문과 무관한 요소 제거
        for tag in body_el.select("script, style, .img_desc, em.img_desc, .end_photo_org"):
            tag.decompose()
        body = re.sub(r"\s+", " ", body_el.get_text(" ", strip=True))

    return {
        "title": title,
        "press": press,
        "date": date,
        "reporter": reporter,
        "url": url,
        "body": body,
    }


# ---------------------------------------------------------------------------
# 백그라운드 작업 스레드 (크롤링 중에도 화면이 멈추지 않도록)
# ---------------------------------------------------------------------------
class CrawlWorker(QThread):
    links_found = pyqtSignal(int)          # 수집된 링크 수
    article_done = pyqtSignal(int, dict)   # (진행 번호, 기사 데이터)
    message = pyqtSignal(str)              # 상태 메시지
    finished_all = pyqtSignal(int)         # 완료된 기사 수

    def __init__(self, search_url):
        super().__init__()
        self.search_url = search_url
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            links = collect_article_links(self.search_url)
        except requests.RequestException as e:
            self.message.emit(f"검색 페이지 요청 실패: {e}")
            self.finished_all.emit(0)
            return

        self.links_found.emit(len(links))
        count = 0
        for i, url in enumerate(links, 1):
            if self._stop:
                self.message.emit("사용자가 중지했습니다.")
                break
            try:
                article = parse_article(url)
            except requests.RequestException as e:
                self.message.emit(f"[{i}] 실패: {url} ({e})")
                continue
            count += 1
            self.article_done.emit(i, article)
            time.sleep(0.5)  # 서버 부담을 줄이기 위한 딜레이
        self.finished_all.emit(count)


# ---------------------------------------------------------------------------
# 메인 화면
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("뉴스 크롤러")
        self.resize(1180, 800)
        self.articles = []
        self.worker = None

        # 상단 머리말: 제목 + 설명
        title = QLabel("뉴스 크롤러")
        title.setObjectName("appTitle")
        subtitle = QLabel("네이버 검색 결과에서 뉴스 기사를 모아 본문까지 가져옵니다")
        subtitle.setObjectName("appSubtitle")

        # 검색 카드: 검색어 / 검색 범위 / 실행 버튼
        self.query_edit = QLineEdit("반도체")
        self.query_edit.setPlaceholderText("검색어를 입력하세요")
        self.query_edit.setClearButtonEnabled(True)
        self.query_edit.returnPressed.connect(self.start_crawl)

        self.type_combo = QComboBox()
        self.type_combo.addItems(SEARCH_TYPES.keys())

        self.search_btn = QPushButton("검색")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self.start_crawl)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_crawl)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(self.type_combo)
        search_row.addWidget(self.search_btn)
        search_row.addWidget(self.stop_btn)
        search_card = self.make_card(search_row)

        # 목록 카드 머리: 건수 + 저장 버튼
        self.count_label = QLabel("기사 목록")
        self.count_label.setObjectName("sectionTitle")
        self.save_btn = QPushButton("CSV")
        self.save_btn.setObjectName("ghost")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_csv)
        self.excel_btn = QPushButton("Excel")
        self.excel_btn.setObjectName("ghost")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel)

        list_head = QHBoxLayout()
        list_head.addWidget(self.count_label)
        list_head.addStretch(1)
        list_head.addWidget(self.save_btn)
        list_head.addWidget(self.excel_btn)

        # 기사 목록 표
        self.table = QTableWidget(0, len(COLUMN_LABELS))
        self.table.setHorizontalHeaderLabels(COLUMN_LABELS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(COLUMN_LABELS) - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # URL 은 길어서 고정 폭으로 두고, 마우스로 조절 가능
        header.setSectionResizeMode(len(COLUMN_LABELS) - 1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(len(COLUMN_LABELS) - 1, 150)
        self.table.itemSelectionChanged.connect(self.show_body)
        self.table.cellDoubleClicked.connect(self.open_in_browser)

        list_layout = QVBoxLayout()
        list_layout.setSpacing(10)
        list_layout.addLayout(list_head)
        list_layout.addWidget(self.table, 1)
        list_card = self.make_card(list_layout)

        # 본문 카드
        self.body_view = QTextEdit()
        self.body_view.setObjectName("bodyView")
        self.body_view.setReadOnly(True)
        self.body_view.setPlaceholderText("목록에서 기사를 선택하면 본문이 표시됩니다. (더블클릭: 브라우저로 열기)")
        body_layout = QVBoxLayout()
        body_layout.addWidget(self.body_view)
        body_card = self.make_card(body_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(16)
        splitter.addWidget(list_card)
        splitter.addWidget(body_card)
        splitter.setSizes([430, 320])

        # 하단: 진행 상태
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.status_label = QLabel("검색어를 입력하고 검색을 눌러 주세요")
        self.status_label.setObjectName("status")

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addSpacing(2)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(search_card)
        layout.addSpacing(16)
        layout.addWidget(splitter, 1)
        layout.addSpacing(12)
        layout.addWidget(self.progress)
        layout.addSpacing(8)
        layout.addWidget(self.status_label)

        central = QWidget()
        central.setObjectName("root")
        central.setLayout(layout)
        self.setCentralWidget(central)

    @staticmethod
    def make_card(inner_layout):
        """흰 배경의 둥근 카드 위젯으로 감싸기"""
        card = QFrame()
        card.setObjectName("card")
        inner_layout.setContentsMargins(16, 14, 16, 14)
        card.setLayout(inner_layout)
        return card

    # --- 크롤링 제어 ---
    def start_crawl(self):
        query = self.query_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
            return
        if self.worker and self.worker.isRunning():
            return

        self.articles = []
        self.table.setRowCount(0)
        self.body_view.clear()
        self.progress.setValue(0)
        self.count_label.setText("기사 목록")

        where = SEARCH_TYPES[self.type_combo.currentText()]
        self.worker = CrawlWorker(build_search_url(query, where))
        self.worker.links_found.connect(self.on_links_found)
        self.worker.article_done.connect(self.on_article_done)
        self.worker.message.connect(self.status_label.setText)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()

        self.set_running(True)
        self.status_label.setText(f"'{query}' 검색 결과 수집 중...")

    def stop_crawl(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def set_running(self, running):
        self.search_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.query_edit.setEnabled(not running)
        self.type_combo.setEnabled(not running)
        self.save_btn.setEnabled(not running and bool(self.articles))
        self.excel_btn.setEnabled(not running and bool(self.articles))

    # --- 작업 스레드 신호 처리 ---
    def on_links_found(self, total):
        self.progress.setMaximum(max(total, 1))
        self.status_label.setText(f"기사 링크 {total}개 발견, 본문 수집 중...")

    def on_article_done(self, index, article):
        self.articles.append(article)
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, key in enumerate(COLUMNS[:len(COLUMN_LABELS)]):
            self.table.setItem(row, col, QTableWidgetItem(article[key]))
        self.count_label.setText(f"기사 목록  ·  {len(self.articles)}건")
        self.progress.setValue(index)
        self.status_label.setText(f"[{index}/{self.progress.maximum()}] {article['title']}")

    def on_finished(self, count):
        self.set_running(False)
        self.progress.setValue(self.progress.maximum())
        self.status_label.setText(f"완료: 총 {count}개 기사 수집")

    # --- 화면 동작 ---
    def show_body(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.articles):
            a = {k: html.escape(v) for k, v in self.articles[row].items()}
            meta = "  ·  ".join(v for v in (a["press"], a["date"], a["reporter"]) if v)
            self.body_view.setHtml(
                f"<div style='font-size:17pt; font-weight:600; color:{TEXT};'>{a['title']}</div>"
                f"<div style='margin-top:6px; color:{MUTED};'>{meta}</div>"
                f"<div style='margin-top:2px;'><a style='color:{ACCENT}; text-decoration:none;' "
                f"href='{a['url']}'>{a['url']}</a></div>"
                f"<p style='margin-top:16px; line-height:170%; color:{TEXT};'>{a['body']}</p>"
            )

    def open_in_browser(self, row, _col):
        if 0 <= row < len(self.articles):
            webbrowser.open(self.articles[row]["url"])

    def save_csv(self):
        if not self.articles:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV 저장", "naver_news.csv", "CSV 파일 (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(self.articles)
        self.status_label.setText(f"{len(self.articles)}개 기사를 저장했습니다: {path}")

    def save_excel(self):
        if not self.articles:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀 저장", "naver_news.xlsx", "엑셀 파일 (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "뉴스"

        # 머리글: 굵은 글씨 + 배경색, 첫 행 고정
        ws.append(EXCEL_HEADERS)
        header_fill = PatternFill("solid", fgColor="DDEBF7")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.freeze_panes = "A2"

        for a in self.articles:
            ws.append([a[key] for key in COLUMNS])
            row = ws.max_row
            # URL 은 클릭하면 열리도록 하이퍼링크로 설정
            url_cell = ws.cell(row=row, column=COLUMNS.index("url") + 1)
            url_cell.hyperlink = a["url"]
            url_cell.font = Font(color="0563C1", underline="single")
            for cell in ws[row]:
                cell.alignment = Alignment(vertical="top", wrap_text=cell.column == len(COLUMNS))

        for i, width in enumerate(EXCEL_WIDTHS, 1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
        ws.auto_filter.ref = ws.dimensions

        try:
            wb.save(path)
        except PermissionError:
            QMessageBox.warning(self, "저장 실패", "파일이 다른 프로그램(엑셀 등)에서 열려 있는지 확인하세요.")
            return
        self.status_label.setText(f"{len(self.articles)}개 기사를 엑셀로 저장했습니다: {path}")

    def closeEvent(self, event):
        # 창을 닫을 때 작업 중인 스레드 정리
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
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
