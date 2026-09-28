"""Regenerates docs/index.html, the static snapshot served by GitHub Pages,
from an FCA firm-specific complaints return.

    python scripts/build_static_dashboard.py [path/to/return.xlsx]

The Streamlit app (app.py) is the full interactive version but needs Python to
run. This page needs only a browser, so it is the one a visitor can actually
open. Data is embedded at build time: it is a snapshot and does not update.
"""
import json, pathlib, sys
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.etl import load
from src.metrics import firm_summary, product_group_view

FLOOR = 100   # matches the minimum of the slider in the page


def build(xlsx):
    df = load(xlsx)
    s, p = firm_summary(df), product_group_view(df)
    w = df.dropna(subset=["pct_upheld", "complaints_closed"])
    r2 = lambda x: None if pd.isna(x) else round(float(x), 2)
    data = {
        "m": {"o": int(df.complaints_opened.sum()), "f": int(df.firm.nunique()),
              "w": float(np.average(w.pct_upheld, weights=w.complaints_closed)),
              "md": float(s.pct_upheld.median())},
        "p": [[i, int(r.complaints_opened), r2(r.pct_upheld)] for i, r in p.iterrows()],
        "f": [[i, int(r.complaints_opened), r2(r.pct_upheld)]
              for i, r in s[s.complaints_opened >= FLOOR].iterrows()],
    }
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "scripts" / "dashboard_template.html").read_text(encoding="utf-8")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace("__DATA__", payload), encoding="utf-8")
    print(f"Wrote {out} ({len(data['f'])} firms embedded)")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1
          else ROOT / "data" / "firm-level-complaints-data-2025-h2.xlsx")
