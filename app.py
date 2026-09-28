"""Streamlit dashboard over an FCA firm-specific complaints return.

Run: streamlit run app.py
"""
import pathlib
import pandas as pd
import streamlit as st
from src.etl import load, load_consumer_credit
from src.metrics import firm_summary, uphold_outliers, product_group_view

st.set_page_config(page_title="UK Complaints Dashboard", layout="wide")
ROOT = pathlib.Path(__file__).parent


@st.cache_data
def get_data(path):
    return load(path)


@st.cache_data
def get_cc(path):
    return load_consumer_credit(path)


st.title("UK Financial Services Complaints")
st.caption("Source: FCA firm-specific complaints data, published half-yearly. "
          "One row per firm per product group; a firm's own six-month "
          "reporting window may fall anywhere within the half-year shown.")

uploaded = st.sidebar.file_uploader("Complaints return (.xlsx)", type=["xlsx"])
default = ROOT / "data" / "firm-level-complaints-data-2025-h2.xlsx"
path = uploaded if uploaded is not None else (default if default.exists() else None)
if path is None:
    st.info("Upload an FCA firm-specific complaints return (.xlsx) to begin. "
           "Download the current release from fca.org.uk/data/complaints-data/firm-level.")
    st.stop()

df = get_data(path)
cc = get_cc(path)

groups = sorted(df.product_group.unique())
chosen_g = st.sidebar.multiselect("Product group", groups, default=groups)
df = df[df.product_group.isin(chosen_g)]

min_vol = st.sidebar.slider("Minimum complaints for outlier view", 100, 20000, 500, 100)

summary = firm_summary(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Complaints opened", f"{int(df.complaints_opened.sum()):,}")
c2.metric("Firms", f"{df.firm.nunique():,}")
c3.metric("Median uphold rate", f"{summary.pct_upheld.median():.1f}%")
c4.metric("Reporting periods in file", f"{df['period'].nunique()}")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Uphold outliers", "Firm detail", "Consumer credit"])

with tab1:
    left, right = st.columns(2)
    left.subheader("Volume by firm (top 15)")
    left.bar_chart(summary.sort_values("complaints_opened", ascending=False)
                          .head(15).complaints_opened)
    products = product_group_view(df)
    right.subheader("Volume by product group")
    right.bar_chart(products.complaints_opened)
    st.subheader("Uphold rate by product group")
    st.caption("Weighted by each firm's closed-complaint volume, not a simple "
              "average across firms.")
    st.bar_chart(products.pct_upheld)

with tab2:
    out = uphold_outliers(summary, min_complaints=min_vol)
    if out.empty:
        st.info("No firms above the volume threshold.")
    else:
        st.caption(f"Deviation from the sector median uphold rate "
                  f"({out.sector_median.iloc[0]:.1f}%), firms with "
                  f"{min_vol:,}+ complaints opened. Small denominators are "
                  f"excluded because a firm with a handful of closed cases "
                  f"would otherwise dominate the ranking on noise alone.")
        top = out.reindex(out.deviation_pp.abs().sort_values(ascending=False).index).head(20)
        st.bar_chart(top.sort_values("deviation_pp").deviation_pp)
        st.dataframe(out.head(30).round(2), use_container_width=True)

with tab3:
    firm = st.selectbox("Firm", summary.index)
    st.dataframe(df[df.firm == firm].round(2), use_container_width=True)

with tab4:
    st.caption("A separate FCA return with its own firm population — only "
              "partial overlap with the main return above. Shown separately "
              "rather than merged in, because merging would silently mix two "
              "different reporting regimes into one number.")
    if cc.empty:
        st.info("No Consumer Credit sheet found in this file.")
    else:
        st.dataframe(cc.sort_values("complaints_received", ascending=False)
                       .round(2), use_container_width=True)
