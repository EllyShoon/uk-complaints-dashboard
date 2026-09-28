"""Derived measures over the long-format complaints table from src.etl.load()."""
from __future__ import annotations
import numpy as np
import pandas as pd


def firm_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Firm-level totals, with uphold rate weighted by closed volume.

    An unweighted mean would let a firm that closed 3 complaints move the
    figure as much as one that closed 30,000. Weighting by the volume each
    firm actually closed avoids that.
    """
    out = df.groupby("firm").agg(
        group=("group", "first"),
        complaints_opened=("complaints_opened", "sum"),
        complaints_closed=("complaints_closed", "sum"),
    )
    w = df.dropna(subset=["pct_upheld", "complaints_closed"])
    if not w.empty:
        weighted = (w.groupby("firm")
                     .apply(lambda g: np.average(g.pct_upheld, weights=g.complaints_closed)
                            if g.complaints_closed.sum() else np.nan,
                            include_groups=False))
        out["pct_upheld"] = weighted
    return out.sort_values("complaints_opened", ascending=False)


def uphold_outliers(summary: pd.DataFrame, min_complaints: int = 500) -> pd.DataFrame:
    """Firms whose uphold rate sits far from the sector norm.

    Restricted to firms above a volume floor: an uphold rate is a ratio, and
    ratios with small denominators are noise-dominated. Without a floor, the
    ranking fills with firms that closed a handful of complaints and lost most
    of them — which is a sample-size artefact, not a signal.

    Deviation is scaled by IQR rather than standard deviation, because the
    uphold-rate distribution has a long right tail that would drag a
    mean/SD-based z-score toward the outliers it is meant to flag.
    """
    if "pct_upheld" not in summary:
        return pd.DataFrame()
    s = summary[summary.complaints_opened >= min_complaints].dropna(subset=["pct_upheld"])
    if s.empty:
        return s
    med = s.pct_upheld.median()
    iqr = s.pct_upheld.quantile(.75) - s.pct_upheld.quantile(.25)
    out = s.assign(sector_median=med, deviation_pp=s.pct_upheld - med,
                  robust_z=(s.pct_upheld - med) / iqr if iqr else np.nan)
    return out.reindex(out.robust_z.abs().sort_values(ascending=False).index)


def product_group_view(df: pd.DataFrame) -> pd.DataFrame:
    """Volume and average uphold rate by product group across all firms."""
    out = df.groupby("product_group").agg(
        complaints_opened=("complaints_opened", "sum"),
        complaints_closed=("complaints_closed", "sum"),
    )
    w = df.dropna(subset=["pct_upheld", "complaints_closed"])
    out["pct_upheld"] = (w.groupby("product_group")
                          .apply(lambda g: np.average(g.pct_upheld, weights=g.complaints_closed)
                                 if g.complaints_closed.sum() else np.nan,
                                 include_groups=False))
    out["pct_of_complaints"] = 100 * out.complaints_opened / out.complaints_opened.sum()
    return out.sort_values("complaints_opened", ascending=False)
