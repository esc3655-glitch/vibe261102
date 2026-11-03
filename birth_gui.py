"""대한민국 출생아수 데이터 분석기 (PyQt6 GUI)

엑셀 불러오기 → 데이터 클렌징 → 다각도 분석 리포트 → 출생아수 라인그래프/분석 대시보드
"""
import sys
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QAbstractTableModel, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                             QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableView, QTabWidget,
                             QVBoxLayout, QWidget)

from birth_analysis import DEFAULT_SRC, build_report, draw_births_line, draw_dashboard, load_clean

INT_COLS = {"출생아수", "자연증가건수", "사망자수(추정)"}


# ----------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------
class DataFrameModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def set_df(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        col = self._df.columns[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            v = self._df.iat[index.row(), index.column()]
            if col == "잠정치":
                return "p)" if v else ""
            if pd.isna(v):
                return ""
            return f"{v:,.0f}" if col in INT_COLS else f"{v:,.3f}".rstrip("0").rstrip(".")
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])


class ChartTab(QWidget):
    """matplotlib Figure + 툴바(확대/이동/저장)"""

    def __init__(self, figsize):
        super().__init__()
        self.figure = Figure(figsize=figsize, tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대한민국 출생아수 데이터 분석기")
        self.resize(1300, 820)
        self.df = None

        # 상단: 파일 열기 / 연도 범위 / 옵션
        self.btn_open = QPushButton("엑셀 열기")
        self.lbl_file = QLabel("파일을 열어 주세요")
        self.year_from = QSpinBox()
        self.year_to = QSpinBox()
        for w, v in ((self.year_from, 1970), (self.year_to, 2025)):
            w.setRange(1900, 2100)
            w.setValue(v)
            w.setSuffix("년")
        self.chk_tfr = QCheckBox("합계출산율 함께 보기")
        self.btn_draw = QPushButton("그래프 그리기")
        self.btn_save_csv = QPushButton("정제 CSV 저장")

        top = QHBoxLayout()
        top.addWidget(self.btn_open)
        top.addWidget(self.lbl_file, 1)
        top.addWidget(QLabel("기간:"))
        top.addWidget(self.year_from)
        top.addWidget(QLabel("~"))
        top.addWidget(self.year_to)
        top.addWidget(self.chk_tfr)
        top.addWidget(self.btn_draw)
        top.addWidget(self.btn_save_csv)

        # 탭: 출생아수 그래프 / 분석 대시보드 / 분석 리포트 / 정제 데이터
        self.tab_line = ChartTab((14, 6))
        self.tab_dash = ChartTab((16, 10))
        self.report = QPlainTextEdit(readOnly=True)
        self.report.setFont(QFont("Consolas", 10))
        self.model = DataFrameModel()
        self.table = QTableView()
        self.table.setModel(self.model)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.tab_line, "출생아수 그래프")
        self.tabs.addTab(self.tab_dash, "분석 대시보드")
        self.tabs.addTab(self.report, "분석 리포트")
        self.tabs.addTab(self.table, "정제 데이터")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        self.btn_open.clicked.connect(self.open_file)
        self.btn_draw.clicked.connect(self.draw_charts)
        self.btn_save_csv.clicked.connect(self.save_csv)
        self.chk_tfr.toggled.connect(self.draw_charts)
        self.set_enabled(False)

        if DEFAULT_SRC.exists():
            self.load(DEFAULT_SRC)

    def set_enabled(self, on):
        for w in (self.btn_draw, self.btn_save_csv, self.year_from, self.year_to, self.chk_tfr):
            w.setEnabled(on)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "출생아수 엑셀 열기", str(DEFAULT_SRC.parent),
                                              "엑셀 파일 (*.xlsx)")
        if path:
            self.load(Path(path))

    def load(self, path):
        try:
            df, log = load_clean(path)
            report = build_report(df, log)
        except Exception as e:
            QMessageBox.critical(self, "불러오기 실패", f"{path.name}\n\n{e}")
            return
        self.df = df
        first, last = df.index.min(), df.index.max()
        self.lbl_file.setText(f"{path.name}  ({first}~{last}, {len(df)}개 연도)")
        for w in (self.year_from, self.year_to):
            w.setRange(first, last)
        self.year_from.setValue(first)
        self.year_to.setValue(last)
        self.report.setPlainText(report)
        self.model.set_df(df)
        self.table.resizeColumnsToContents()
        self.set_enabled(True)
        self.draw_charts()
        self.statusBar().showMessage("클렌징 및 분석 완료", 5000)

    def draw_charts(self):
        if self.df is None:
            return
        start, end = self.year_from.value(), self.year_to.value()
        period = self.df.loc[start:end]
        if len(period) < 2:
            QMessageBox.warning(self, "기간 오류", "시작 연도가 종료 연도보다 앞서야 합니다.")
            return

        fig = self.tab_line.figure
        fig.clear()
        draw_births_line(fig.add_subplot(), period, show_tfr=self.chk_tfr.isChecked())
        fig.text(0.99, 0.01, "출처: 통계청 「인구동향조사」 (KOSIS)", ha="right", fontsize=8, color="gray")
        self.tab_line.canvas.draw()

        fig = self.tab_dash.figure
        fig.clear()
        draw_dashboard(fig, period)
        self.tab_dash.canvas.draw()

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "정제 데이터 저장", "birth_clean.csv", "CSV 파일 (*.csv)")
        if path:
            self.df.to_csv(path, encoding="utf-8-sig")
            self.statusBar().showMessage(f"저장 완료: {path}", 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
