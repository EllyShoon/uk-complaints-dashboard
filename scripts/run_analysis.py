"""Builds static figures and CSV outputs from a real FCA complaints return."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.etl import load, load_consumer_credit
from src.metrics import firm_summary, uphold_outliers, product_group_view

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
OUT = ROOT / "output"; OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})

def main(path):
    df = load(path)
    print(f"Loaded {len(df):,} firm x product-group rows, {df.firm.nunique()} firms, "
         f"{df['period'].nunique()} distinct reporting periods")
    summary = firm_summary(df)
    outliers = uphold_outliers(summary, min_complaints=500)
    products = product_group_view(df)
    cc = load_consumer_credit(path)

    top = summary.sort_values("complaints_opened", ascending=False).head(12)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh([f[:32] for f in top.index[::-1]], top.complaints_opened[::-1], color="#1f3864")
    ax.set_xlabel("Complaints opened, H2 2025"); ax.set_title("Complaint volume by firm")
    plt.tight_layout(); plt.savefig(FIG / "01_volume_by_firm.png"); plt.close()

    o = outliers.reindex(outliers.deviation_pp.abs().sort_values(ascending=False).index).head(12)
    o = o.sort_values("deviation_pp")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh([f[:32] for f in o.index], o.deviation_pp,
            color=["#c0504d" if v > 0 else "#4f81bd" for v in o.deviation_pp])
    ax.axvline(0, color="#333", lw=1)
    ax.set_xlabel(f"Deviation from sector median ({o.sector_median.iloc[0]:.1f}%), pp")
    ax.set_title("Uphold-rate outliers (firms with 500+ complaints opened)")
    plt.tight_layout(); plt.savefig(FIG / "02_uphold_outliers.png"); plt.close()

    fig, ax1 = plt.subplots(figsize=(7, 4))
    x = range(len(products))
    ax1.bar(x, products.complaints_opened, color="#1f3864", label="Complaints opened")
    ax1.set_ylabel("Complaints opened"); ax1.set_xticks(list(x))
    ax1.set_xticklabels([p.replace(" & ", " &\n") for p in products.index], fontsize=8)
    ax2 = ax1.twinx()
    ax2.plot(x, products.pct_upheld, "o-", color="#c0504d", label="Uphold rate")
    ax2.set_ylabel("Uphold rate (%)", color="#c0504d")
    ax1.set_title("Volume and uphold rate by product group")
    plt.tight_layout(); plt.savefig(FIG / "03_product_groups.png"); plt.close()

    summary.to_csv(OUT / "firm_summary.csv")
    outliers.to_csv(OUT / "uphold_outliers.csv")
    products.to_csv(OUT / "product_groups.csv")
    if not cc.empty:
        cc.to_csv(OUT / "consumer_credit.csv", index=False)

    print("\n=== Top firms by volume ===")
    print(summary.head(8).round(1).to_string())
    print("\n=== Uphold outliers (top 8 by |deviation|) ===")
    print(o[["group","complaints_opened","pct_upheld","deviation_pp"]].round(2).to_string())
    print("\n=== Product groups ===")
    print(products.round(1).to_string())
    if not cc.empty:
        print(f"\nConsumer Credit: {len(cc)} firms, "
              f"{cc.complaints_received.sum():,.0f} complaints received")

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "firm-level-complaints-data-2025-h2.xlsx"
    main(p)
