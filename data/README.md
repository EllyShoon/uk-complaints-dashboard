# Data

Not committed. Download the current firm-specific return and place it here.

## Source

**FCA firm-specific complaints data**, published half-yearly, free, no
registration: https://www.fca.org.uk/data/complaints-data/firm-level

Direct download for the current release (H2 2025, published 15 May 2026):
https://www.fca.org.uk/publication/data/firm-level-complaints-data-2025-h2.xlsx

A new release replaces this roughly every April and October — check the page
above for the current link when it updates.

## The real shape of the file (read this before changing the code)

This is **not** one flat table. It is an 11-sheet workbook, and the sheets
that matter are **wide**, not long — one row per firm, one column per product
group:

```
Firm Name | Group | Joint Reporting | Reporting period | Banking and credit
cards | Decumulation & pensions | Home finance | Insurance & pure protection
| Investments | Grand Total
```

...repeated identically across five sheets: `Opened`, `Closed`,
`Percentage upheld`, `Percentage within 3 days`, and
`Percentage after 3 days, within` (the FCA's own column header, truncated —
it means "within 8 weeks"). `src/etl.py` melts each of these five sheets from
wide to long and merges them into one table keyed on firm, group, reporting
period and product group.

Three things a first pass at this file gets wrong:

- **There is no redress column anywhere in this file.** Total redress paid
  is published separately, in the *aggregate* release
  (`aggregate-complaints-data-2025-h2.xlsx`), not the firm-specific one. Code
  in this repo never invents a redress figure for firm-level data.
- **A blank cell means "did not report in that product group," not zero.**
  Filling blanks with 0 would understate every firm's average by counting
  products it doesn't sell.
- **`Reporting period` is set per firm, not per file.** Firms report on their
  own financial-year-aligned six-month window, so an "H2 2025" release
  actually contains five distinct date ranges, not one.

## Other sheets in the workbook

- **`Consumer Credit`** — a genuinely separate return: different columns
  (`Complaints Received`, `Complaints Closed`, `Complaints upheld by firm`),
  and only partial overlap in which firms appear (77 of 151 consumer-credit
  reporters also appear in the main return). Loaded separately by
  `load_consumer_credit()` rather than merged in.
- **`Context - Intermediation` / `Context - Provision`** — complaints per
  unit of business (e.g. per thousand policies), not complaint counts. Not
  currently used by this project.
- **`Trading Names`** — a partial firm-name lookup (85 of 219 main-return
  firms). Not a complete join key.
- **`Main return Joint reporters` / `Consumer credit Joint reporters`** —
  which firms report jointly with which. Not currently used.

## If the FCA changes the sheet names in a future release

`src/etl.py` raises a clear error naming exactly which expected sheet is
missing, rather than silently mis-parsing. Update the `PRODUCT_GROUP_SHEETS`
dictionary at the top of that file to match.
