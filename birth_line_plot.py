"""대한민국 출생아수 라인 그래프 (1970~2025)"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from birth_analysis import DEFAULT_SRC, OUT, draw_births_line, load_clean

args = [a for a in sys.argv[1:] if not a.startswith("--")]
src = Path(args[0]) if args else DEFAULT_SRC
df, _ = load_clean(src)
df = df.loc[1970:2025]

fig, ax = plt.subplots(figsize=(13, 6))
draw_births_line(ax, df, show_tfr="--tfr" in sys.argv)
fig.text(0.99, 0.01, "출처: 통계청 「인구동향조사」 (KOSIS)", ha="right", fontsize=8, color="gray")
fig.tight_layout()

OUT.mkdir(exist_ok=True)
out_path = OUT / "01_births_line_1970_2025.png"
fig.savefig(out_path, dpi=150)
print(f"[저장] {out_path}")
if "--show" in sys.argv:
    plt.show()
