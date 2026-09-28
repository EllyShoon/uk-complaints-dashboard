"""Load and clean the FCA firm-specific complaints return.

REAL FILE SHAPE (confirmed against firm-level-complaints-data-2025-h2.xlsx —
this is not a guess, it is read directly from the workbook):

The workbook is NOT one flat table. It is 11 sheets, and the five that matter
for the main return are all WIDE: one row per firm, one column per product
group, plus a 'Grand Total' column —

    Firm Name | Group | Joint Reporting | Reporting period | Banking and
    credit cards | Decumulation & pensions | Home finance | Insurance & pure
    protection | Investments | Grand Total

— repeated identically across the 'Opened', 'Closed', 'Percentage upheld',
'Percentage within 3 days' and 'Percentage after 3 days, within' [8 weeks]
sheets. A firm's row is blank (NaN) in a product-group column it did not
report against, which is a real "did not sell this" rather than a zero.

Two more things a first pass gets wrong if you assume a flat table:

- There is NO redress column anywhere in the FIRM-LEVEL file. Total redress
  paid is only published in the separate AGGREGATE release. Code here never
  invents one.
- 'Reporting period' is set PER FIRM, not per sheet. Firms report on their own
  financial-year-aligned six-month window, so a "2025 H2" file actually
  contains several distinct date ranges (five, in the H2 2025 release), all
  of which fall within H2 but do not all start and end on the same day.

'Consumer Credit' is a genuinely separate return (different columns, and only
partial overlap in which firms appear) and is loaded separately rather than
forced into the same shape.
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

PRODUCT_GROUP_SHEETS = {
    "Opened": "complaints_opened",
    "Closed": "complaints_closed",
    "Percentage upheld": "pct_upheld",
    "Percentage within 3 days": "pct_closed_3_days",
    "Percentage after 3 days, within": "pct_closed_after_3_days_within_8_weeks",
}
ID_COLS = ["firm", "group", "joint_reporting", "period"]
PCT_COLS = ["pct_upheld", "pct_closed_3_days", "pct_closed_after_3_days_within_8_weeks"]


def _melt_sheet(xl: pd.ExcelFile, sheet: str, value_name: str) -> pd.DataFrame:
    """Wide (one column per product group) -> long (one row per firm x product)."""
    raw = pd.read_excel(xl, sheet_name=sheet)
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.rename(columns={"Firm Name": "firm", "Group": "group",
                              "Joint Reporting": "joint_reporting",
                              "Reporting period": "period"})
    product_cols = [c for c in raw.columns if c not in ID_COLS + ["Grand Total"]]
    long = raw.melt(id_vars=ID_COLS, value_vars=product_cols,
                    var_name="product_group", value_name=value_name)
    # A blank cell means the firm did not report against that product group in
    # that period, not a zero complaint count. Dropping it (rather than
    # filling 0) keeps a firm's per-product averages honest.
    return long.dropna(subset=[value_name])


def load(path: str | pathlib.Path) -> pd.DataFrame:
    """Load the main return (five product groups) as one long dataframe:
    firm, group, joint_reporting, period, product_group, complaints_opened,
    complaints_closed, pct_upheld, pct_closed_3_days,
    pct_closed_after_3_days_within_8_weeks.

    Percentages are converted from the raw proportion (0-1, as the FCA stores
    them) to a 0-100 scale, since every consumer of this table formats them
    as "{:.1f}%".
    """
    xl = pd.ExcelFile(path)
    missing = [s for s in PRODUCT_GROUP_SHEETS if s not in xl.sheet_names]
    if missing:
        raise ValueError(
            f"Expected sheet(s) not found: {missing}. Found: {xl.sheet_names}. "
            "The FCA may have renamed a tab in a later release — update "
            "PRODUCT_GROUP_SHEETS in this file to match."
        )

    merged = None
    for sheet, value_name in PRODUCT_GROUP_SHEETS.items():
        piece = _melt_sheet(xl, sheet, value_name)
        merged = piece if merged is None else merged.merge(
            piece, on=ID_COLS + ["product_group"], how="outer")

    for c in PCT_COLS:
        merged[c] = pd.to_numeric(merged[c], errors="coerce") * 100

    merged["firm"] = merged["firm"].astype(str).str.strip()
    merged["group"] = merged["group"].astype(str).str.strip()
    return merged.reset_index(drop=True)


def load_consumer_credit(path: str | pathlib.Path) -> pd.DataFrame:
    """The Consumer Credit return. Different schema, different firm population
    (only partial overlap with the main return) — kept separate rather than
    forced into the main table's shape."""
    xl = pd.ExcelFile(path)
    if "Consumer Credit" not in xl.sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(xl, sheet_name="Consumer Credit")
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.rename(columns={
        "Firm Name": "firm", "Group": "group",
        "Reporting frequency": "reporting_frequency", "Reporting period": "period",
        "Semester": "semester", "Complaints Received": "complaints_received",
        "Complaints Closed": "complaints_closed",
        "Complaints upheld by firm": "pct_upheld",
    })
    keep = [c for c in ["firm", "group", "reporting_frequency", "period", "semester",
                        "complaints_received", "complaints_closed", "pct_upheld"]
            if c in raw.columns]
    raw = raw[keep].dropna(subset=["firm"])
    if "pct_upheld" in raw:
        raw["pct_upheld"] = pd.to_numeric(raw["pct_upheld"], errors="coerce") * 100
    return raw.reset_index(drop=True)
