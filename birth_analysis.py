"""대한민국 출생아수·합계출산율·자연증가 (KOSIS, 1970~2025): 클렌징 → 다각도 분석

CLI 실행 시 리포트를 출력하고 birth_output/ 에 정제 CSV와 그래프를 저장한다.
birth_line_plot.py, birth_gui.py 가 이 모듈의 함수를 재사용한다.
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

matplotlib.rcParams["font.family"] = "Malgun Gothic"   # 한글 폰트 (Windows)
matplotlib.rcParams["axes.unicode_minus"] = False

XLSX_NAME = "출생아수__합계출산율__자연증가_등.xlsx"
# exe로 배포된 경우 실행 파일 옆, 아니면 스크립트 옆 → 수업 데이터셋 폴더 순으로 기본 파일을 찾음
APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
DEFAULT_SRC = next((p for p in (Path(r"C:\Users\user\Desktop\생산성본부_바이브코딩수업\DataSet") / XLSX_NAME,
                                APP_DIR / XLSX_NAME)
                    if p.exists()), APP_DIR / XLSX_NAME)
OUT = APP_DIR / "birth_output"

# 원본 행 이름 → 분석용 컬럼명
RENAME = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}
INDICATORS = list(RENAME.values())
COLORS = {"births": "#2e86de", "tfr": "#c0392b", "up": "#2e86de", "down": "#e74c3c", "ratio": "#8e44ad"}


# ----------------------------------------------------------------------
# 데이터 클렌징
# ----------------------------------------------------------------------
def load_clean(src=DEFAULT_SRC):
    """KOSIS 가로형(지표 × 연도) 시트를 연도 인덱스의 세로형 DataFrame으로 정리. (df, 클렌징 로그) 반환"""
    log = []
    raw = pd.read_excel(src, sheet_name="데이터", header=None)
    log.append(f"원본 shape: {raw.shape}  (행=지표, 열=연도인 가로형)")
    log.append("원본 미리보기:\n" + raw.iloc[:, :8].to_string())

    # 첫 행 = 연도 헤더, 첫 열 = 지표명 → 전치해서 연도를 행으로
    df = raw.set_index(0).T
    df = df.rename(columns={"기본항목별": "연도", **RENAME})
    df.columns.name = None

    # 연도: 1970.0(float) / "2025 p)"(잠정치 표기) 혼재 → 정수 연도 + 잠정치 플래그
    year_str = df["연도"].astype(str).str.strip()
    df["잠정치"] = year_str.str.contains("p", case=False)
    df["연도"] = pd.to_numeric(year_str.str.extract(r"(\d{4})")[0], errors="coerce").astype("Int64")

    # 수치 컬럼: 문자열·object 혼재 → 콤마 제거 후 float
    for col in INDICATORS:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce")

    before = len(df)
    df = df.dropna(subset=["연도", "출생아수"]).drop_duplicates(subset="연도")
    df = df.sort_values("연도").set_index("연도")
    df.index = df.index.astype(int)
    for col in ["출생아수", "자연증가건수"]:
        df[col] = df[col].astype("int64")
    # 파생 변수: 사망자수 = 출생아수 - 자연증가건수
    df["사망자수(추정)"] = df["출생아수"] - df["자연증가건수"]

    log.append("[클렌징] 가로형 → 세로형 전치, 연도 정수화, 수치형 변환")
    log.append(f"[클렌징] 연도/출생아수 결측·중복 제거: {before - len(df)}행")
    log.append(f"[클렌징] 잠정치 연도: {df.index[df['잠정치']].tolist()}")
    log.append(f"[클렌징] 남은 결측치: {int(df[INDICATORS].isna().sum().sum())}개")
    log.append("[파생] 사망자수(추정) = 출생아수 - 자연증가건수")
    # 논리 검증: 연도 연속성, 값 범위
    missing_years = sorted(set(range(df.index.min(), df.index.max() + 1)) - set(df.index))
    log.append(f"[검증] 누락 연도: {missing_years or '없음'}")
    log.append(f"[검증] 출생아수 > 0: {(df['출생아수'] > 0).all()}, "
               f"합계출산율 0~10: {df['합계출산율'].between(0, 10).all()}, "
               f"출생성비 90~130: {df['출생성비'].between(90, 130).all()}")
    log.append(f"기간: {df.index.min()}~{df.index.max()}, {len(df)}개 연도")
    return df, log


def yoy_table(df):
    b = df["출생아수"]
    return pd.DataFrame({"출생아수": b, "증감": b.diff(), "증감률(%)": b.pct_change() * 100})


# ----------------------------------------------------------------------
# 다각도 분석 리포트
# ----------------------------------------------------------------------
def build_report(df, clean_log):
    """다각도 분석 결과를 텍스트 리포트로 반환"""
    out = []

    def section(title):
        out.append(f"\n{'=' * 70}\n{title}\n{'=' * 70}")

    with pd.option_context("display.width", 140, "display.max_columns", 20):
        section("1. 데이터 클렌징")
        out.extend(clean_log)

        section("2. 기술통계")
        out.append(df[INDICATORS].describe().T.round(2).to_string())

        section("3. 출생아수 최고·최저 / 장기 변화")
        b = df["출생아수"]
        first, last = df.index.min(), df.index.max()
        out.append(f"최고: {b.idxmax()}년 {b.max():,}명")
        out.append(f"최저: {b.idxmin()}년 {b.min():,}명")
        if last > first:
            cagr = (b[last] / b[first]) ** (1 / (last - first)) - 1
            out.append(f"{first}→{last}: {b[first]:,} → {b[last]:,}명 ({b[last] / b[first] - 1:+.1%}), "
                       f"연평균 {cagr:+.2%}")
        for y in range(1980, last, 10):
            if y in b.index and y > first:
                out.append(f"  {y}년 대비 {last}년: {b[last] / b[y] - 1:+.1%}")

        section("4. 연대별 평균")
        decade = df[INDICATORS].groupby(df.index // 10 * 10).mean()
        decade.index = [f"{d}년대" for d in decade.index]
        out.append(decade.round({"출생아수": 0, "자연증가건수": 0}).round(2).to_string())

        section("5. 전년 대비 증감 (출생아수)")
        yoy = yoy_table(df)
        out.append("감소폭 큰 해 Top 5:\n" + yoy.nsmallest(5, "증감률(%)").round(2).to_string())
        out.append("\n증가폭 큰 해 Top 5:\n" + yoy.nlargest(5, "증감률(%)").round(2).to_string())
        down = (yoy["증감"] < 0).astype(int)
        runs = down.groupby((down != down.shift()).cumsum()).agg(["sum", "size"])
        longest = runs.loc[runs["sum"] > 0, "size"].max()
        out.append(f"\n최장 연속 감소: {0 if pd.isna(longest) else longest}년")
        out.append(f"감소한 해 {int((yoy['증감'] < 0).sum())}개 / 증가한 해 {int((yoy['증감'] > 0).sum())}개")

        section("6. 합계출산율 임계점")
        tfr = df["합계출산율"]
        for label, th in [("대체출산율 2.1 미만", 2.1), ("초저출산 1.3 미만", 1.3), ("1.0 미만", 1.0)]:
            below = tfr[tfr < th]
            out.append(f"{label}: " + (f"최초 {below.index.min()}년 (해당 연도 {len(below)}개)"
                                        if len(below) else "해당 없음"))
        out.append(f"합계출산율 최저: {tfr.idxmin()}년 {tfr.min():.3f}명")

        section("7. 자연증가 (출생 - 사망)")
        nat = df["자연증가건수"]
        neg = nat[nat < 0]
        out.append(f"자연감소 최초 연도: {neg.index.min()}년, 자연감소 {len(neg)}개 연도" if len(neg)
                   else "자연감소 연도 없음")
        out.append(df.loc[df.index >= 2015, ["출생아수", "사망자수(추정)", "자연증가건수", "자연증가율"]].to_string())

        section("8. 출생성비 (여아 100명당 남아)")
        sr = df["출생성비"]
        out.append(f"최고: {sr.idxmax()}년 {sr.max()} / 정상범위(103~107) 이탈 연도:")
        off = sr[(sr < 103) | (sr > 107)]
        out.append(off.to_string() if len(off) else "없음")

        section("9. 지표 간 상관관계")
        out.append(df[INDICATORS].corr().round(3).to_string())

        section("10. 최근 동향 (2015~)")
        recent = df.loc[2015:, ["출생아수", "합계출산율", "자연증가건수", "잠정치"]].copy()
        recent["증감률(%)"] = (recent["출생아수"].pct_change() * 100).round(2)
        out.append(recent.to_string())
    return "\n".join(out).strip()


# ----------------------------------------------------------------------
# 그래프
# ----------------------------------------------------------------------
def draw_births_line(ax, df, show_tfr=False):
    """출생아수 라인 그래프 (최고·최저·최근 주석, 잠정치 구간 점선, 선택 시 합계출산율 보조축)"""
    births = df["출생아수"]
    ax.plot(births.index, births, color=COLORS["births"], lw=2.2, marker="o", ms=3.5, label="출생아수")

    for year, label, offset in [(births.idxmax(), "최고", (10, 10)),
                                (births.idxmin(), "최저", (-60, -30)),
                                (births.index.max(), "최근", (-20, 25))]:
        ax.annotate(f"{label} {year}년\n{births[year]:,}명", xy=(year, births[year]),
                    xytext=offset, textcoords="offset points", fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="gray"))

    # 잠정치 구간은 점선으로 구분
    prov = df.index[df["잠정치"]]
    if len(prov):
        seg = births.loc[prov.min() - 1:]
        ax.plot(seg.index, seg, color=COLORS["births"], lw=2.2, ls="--")
        ax.text(prov.min(), births[prov.min()] * 0.85, "p) 잠정치", ha="center", fontsize=8, color="gray")

    first, last = df.index.min(), df.index.max()
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e4:,.0f}만"))
    step = 5 if last - first > 15 else 1
    ax.set_xticks(range(first - first % step if step > 1 else first, last + 1, step))
    ax.set_xlim(first - 1, last + 1)
    ax.set_ylim(0, births.max() * 1.12)
    ax.set_title(f"대한민국 연도별 출생아수 ({first}~{last})", fontsize=15, pad=12)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수 (명)")
    ax.grid(alpha=0.3)

    handles, labels = ax.get_legend_handles_labels()
    if show_tfr:
        ax2 = ax.twinx()
        ax2.plot(df.index, df["합계출산율"], color=COLORS["tfr"], lw=1.5, ls="-.", label="합계출산율(우)")
        ax2.set_ylabel("합계출산율 (명)")
        ax2.set_ylim(0, df["합계출산율"].max() * 1.12)
        h2, l2 = ax2.get_legend_handles_labels()
        handles, labels = handles + h2, labels + l2
    ax.legend(handles, labels, loc="upper right")


def draw_dashboard(fig, df):
    """합계출산율 / 자연증가 / 전년 대비 증감률 / 출생성비 2×2 대시보드"""
    axes = fig.subplots(2, 2)
    first, last = df.index.min(), df.index.max()

    ax = axes[0, 0]
    ax.plot(df.index, df["합계출산율"], color=COLORS["tfr"], marker="o", ms=3)
    for th, ls in [(2.1, "--"), (1.3, ":")]:
        ax.axhline(th, color="gray", ls=ls, lw=1)
        ax.text(last, th, f" {th}", va="bottom", ha="right", color="gray")
    ax.set_title("합계출산율 (명)")

    ax = axes[0, 1]
    nat = df["자연증가건수"]
    ax.bar(df.index, nat / 1e4, color=np.where(nat >= 0, COLORS["up"], COLORS["down"]))
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("자연증가건수 (만 명)")

    ax = axes[1, 0]
    rate = yoy_table(df)["증감률(%)"]
    ax.bar(df.index, rate, color=np.where(rate >= 0, COLORS["up"], COLORS["down"]))
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("출생아수 전년 대비 증감률 (%)")

    ax = axes[1, 1]
    ax.plot(df.index, df["출생성비"], color=COLORS["ratio"], marker="o", ms=3)
    ax.axhspan(103, 107, color="green", alpha=0.1, label="정상범위 103~107")
    ax.set_title("출생성비 (여아 100명당 남아)")
    ax.legend()

    for ax in axes.flat:
        ax.grid(alpha=0.3)
    prov = df.index[df["잠정치"]].tolist()
    note = f", {','.join(map(str, prov))}년은 잠정치" if prov else ""
    fig.suptitle(f"대한민국 출산 지표 대시보드 ({first}~{last}{note})", fontsize=14)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = Path(args[0]) if args else DEFAULT_SRC
    OUT.mkdir(exist_ok=True)
    df, log = load_clean(src)
    print(build_report(df, log))
    df.to_csv(OUT / "birth_clean.csv", encoding="utf-8-sig")

    fig = Figure(figsize=(14, 9), tight_layout=True)
    draw_dashboard(fig, df)
    fig.savefig(OUT / "02_analysis_dashboard.png", dpi=150)
    print(f"\n[저장] {OUT / 'birth_clean.csv'}\n[저장] {OUT / '02_analysis_dashboard.png'}")


if __name__ == "__main__":
    main()
