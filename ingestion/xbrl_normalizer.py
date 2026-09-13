"""
ingestion/xbrl_normalizer.py — XBRL company-facts → tidy DataFrame.

WHY this module is the most complex part of Phase 2:
  The EDGAR company-facts JSON is rich but noisy. For any given line item,
  the same balance-sheet date may appear in dozens of records — once per
  filing (10-K, 10-Q, 10-K/A, 8-K, etc.) that referenced it. Tags vary
  across companies (AFRM reports revenue under one tag; OMF under another).
  And two companies have June 30 fiscal year-ends, not December 31.

  This module handles all of that complexity in one place, with every
  design decision commented inline.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from config import TAG_MAP_PATH, MIN_HISTORY_YEARS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tag map loading
# ---------------------------------------------------------------------------

def load_tag_map(path: Path = TAG_MAP_PATH) -> dict:
    """Load the XBRL tag mapping from JSON.

    Returns a dict keyed by canonical line-item name, each value being
    a list of us-gaap XBRL tags to try (in priority order).
    """
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    # Strip metadata keys (starting with "_") and empty tag lists
    return {
        k: v["tags"]
        for k, v in raw.items()
        if not k.startswith("_") and isinstance(v, dict) and v.get("tags")
    }


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

def _extract_tag_records(facts_json: dict, tag: str) -> list[dict]:
    """Pull raw records for a single us-gaap XBRL tag from a company-facts dict.

    Returns the list of period records under facts → us-gaap → {tag} → units → USD,
    or an empty list if the tag is absent.
    """
    return (
        facts_json
        .get("facts", {})
        .get("us-gaap", {})
        .get(tag, {})
        .get("units", {})
        .get("USD", [])
    )


def _get_annual_df_for_tag(facts_json: dict, tag: str) -> pd.DataFrame:
    """Retrieve and filter annual records for a single tag or compound tag ('TagA+TagB').

    When tag contains '+', annual records for each subtag are fetched, aligned on
    end_date via outer merge, and their numeric values summed. This handles companies
    like OPRT where total debt is split between SecuredDebt and WarehouseAgreementBorrowings.
    """
    if "+" in tag:
        subtags = [t.strip() for t in tag.split("+")]
        sub_dfs = []
        for st in subtags:
            recs = _extract_tag_records(facts_json, st)
            f_df = _filter_annual_filings(recs)
            if not f_df.empty:
                sub_dfs.append((st, f_df))
        if not sub_dfs:
            return pd.DataFrame()

        res_df = None
        for st, f_df in sub_dfs:
            f_df_renamed = f_df.rename(columns={
                "val": f"val_{st}",
                "form": f"form_{st}",
                "filed_date": f"filed_date_{st}",
                "is_restated": f"is_restated_{st}",
                "is_comparative": f"is_comparative_{st}",
            })
            if res_df is None:
                res_df = f_df_renamed
            else:
                res_df = pd.merge(res_df, f_df_renamed, on="end_date", how="outer")

        val_cols = [c for c in res_df.columns if c.startswith("val_")]
        res_df["val"] = res_df[val_cols].fillna(0).sum(axis=1)

        restated_cols = [c for c in res_df.columns if c.startswith("is_restated_")]
        res_df["is_restated"] = res_df[restated_cols].fillna(False).any(axis=1)

        comp_cols = [c for c in res_df.columns if c.startswith("is_comparative_")]
        res_df["is_comparative"] = res_df[comp_cols].fillna(False).all(axis=1) & (~res_df["is_restated"])

        filed_cols = [c for c in res_df.columns if c.startswith("filed_date_")]
        res_df["filed_date"] = res_df[filed_cols].max(axis=1)

        form_cols = [c for c in res_df.columns if c.startswith("form_")]
        res_df["form"] = res_df[form_cols].bfill(axis=1).iloc[:, 0]

        return res_df[["end_date", "val", "form", "filed_date", "is_restated", "is_comparative"]]

    raw_records = _extract_tag_records(facts_json, tag)
    return _filter_annual_filings(raw_records)


def _filter_annual_filings(records: list[dict]) -> pd.DataFrame:
    """Keep only annual (10-K / 10-K/A) records from the raw XBRL list.

    WHY we filter to 10-K / 10-K/A only:
      The same balance-sheet date appears in multiple records — the original
      10-K filing plus every subsequent quarterly filing (10-Q) that carries forward
      the prior-year comparative. Keeping only annual records ensures we use
      audited annual figures.

    HOW we distinguish COMPARATIVE vs RESTATED:
      Companies routinely include 2-3 prior years in each 10-K for comparative purposes.
      - COMPARATIVE: A prior-period value that reappears in a later filing with
        the SAME numeric value (routine comparative reporting — not an anomaly).
      - RESTATED: A prior-period value that reappears in a later filing with
        a DIFFERENT numeric value than originally reported, or that comes
        specifically from a 10-K/A amendment.
    """
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Keep only annual filings (10-K or 10-K/A)
    annual_mask = df["form"].isin(["10-K", "10-K/A"])
    df = df[annual_mask].copy()

    if df.empty:
        return df

    # Parse dates
    df["end_date"] = pd.to_datetime(df["end"])
    df["filed_date"] = pd.to_datetime(df["filed"])

    # For duration concepts (income statement / cash flow), exclude sub-annual footnote
    # disclosures (e.g., quarterly summaries reported inside a 10-K footnote with duration < 300 days)
    if "start" in df.columns:
        df["start_date"] = pd.to_datetime(df["start"])
        dur_days = (df["end_date"] - df["start_date"]).dt.days
        df = df[dur_days.isna() | (dur_days >= 300)].copy()

    if df.empty:
        return df

    # Sort descending by filed_date so the latest filing appears first
    df = df.sort_values("filed_date", ascending=False)

    # Per unique period-end date, evaluate restatement vs comparative
    stats = []
    for end_date, grp in df.groupby("end_date"):
        grp_filings = grp.drop_duplicates(subset=["filed_date"])
        n_filings = len(grp_filings)
        has_amendment = (grp["form"] == "10-K/A").any()
        val_differs = grp_filings["val"].nunique() > 1
        is_restated = has_amendment or (n_filings > 1 and val_differs)
        is_comparative = (n_filings > 1) and (not val_differs) and (not has_amendment)
        stats.append({
            "end_date": end_date,
            "n_filings": n_filings,
            "is_restated": is_restated,
            "is_comparative": is_comparative,
        })

    stats_df = pd.DataFrame(stats)

    # Deduplicate: keep the latest filed record for each end_date
    dedup = df.drop_duplicates(subset="end_date", keep="first")
    merged = dedup.merge(stats_df, on="end_date")

    return merged.reset_index(drop=True)


def _calendar_year_label(period_end: pd.Timestamp, fye_month: int) -> int:
    """Map a fiscal year-end date to a calendar year label.

    WHY we use the calendar year of the FYE date for all companies:
      AFRM and SEZL have June 30 FYEs, while the other 7 have December 31.
      If we used the company's own `fy` field from EDGAR, AFRM's fiscal
      year 2024 (ending June 30, 2024) would align with OMF's fiscal year
      2024 (ending December 31, 2024) — even though AFRM's figures actually
      reflect a period ending 6 months earlier.

      Using the calendar year of the period-end date (e.g., June 30, 2024
      → cal_year 2024; December 31, 2024 → cal_year 2024) means both
      companies are labelled 2024, but the dashboard and memo explicitly
      note the 6-month FYE difference. This is standard sell-side practice.

    See METHODOLOGY.md for the full rationale.
    """
    return period_end.year


def _is_within_history_window(period_end: pd.Timestamp) -> bool:
    """Return True if the period is within MIN_HISTORY_YEARS of today."""
    cutoff = pd.Timestamp(date.today()).replace(month=1, day=1) - pd.DateOffset(years=MIN_HISTORY_YEARS)
    return period_end >= cutoff


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_company(
    ticker: str,
    cik: str,
    facts_json: dict,
    fye_month: int,
) -> pd.DataFrame:
    """Normalize a company's EDGAR company-facts JSON into a tidy DataFrame.

    For each canonical line item in the tag map:
      - Try XBRL tags in priority order until one yields annual records.
      - Filter to annual (10-K) filings only; deduplicate by period end date.
      - Restrict to MIN_HISTORY_YEARS of history.
      - Assign a calendar year label.
      - Record the data quality status.

    Returns a tidy DataFrame with columns:
        ticker, cik, cal_year, fiscal_period_end, line_item,
        value, source_tag, data_quality
    """
    tag_map = load_tag_map()
    rows: list[dict] = []

    expected_years = set(_expected_cal_years(fye_month))

    for line_item, tags in tag_map.items():
        claimed_years: set[int] = set()

        for i, tag in enumerate(tags):
            annual_df = _get_annual_df_for_tag(facts_json, tag)

            if annual_df.empty:
                continue

            # Apply history window filter
            annual_df = annual_df[annual_df["end_date"].apply(_is_within_history_window)].copy()
            if annual_df.empty:
                continue

            annual_df["cal_year"] = annual_df["end_date"].apply(lambda d: _calendar_year_label(d, fye_month))

            # Only accept years that have not already been claimed by a higher-priority tag
            new_rows_df = annual_df[~annual_df["cal_year"].isin(claimed_years)]
            if new_rows_df.empty:
                continue

            for _, row in new_rows_df.iterrows():
                cal_year = int(row["cal_year"])
                claimed_years.add(cal_year)

                # Determine data quality flag:
                # 1. RESTATED: true restatement (different value or from 10-K/A amendment)
                # 2. FALLBACK: non-primary tag used
                # 3. COMPARATIVE: prior period reported again with unchanged value
                # 4. OK: primary tag, first/only filing
                if row.get("is_restated", False):
                    dq = "RESTATED"
                elif i > 0:
                    dq = f"FALLBACK_{tag}"
                elif row.get("is_comparative", False):
                    dq = "COMPARATIVE"
                else:
                    dq = "OK"

                # Flag zero values — may be legitimate (e.g. no debt) or a gap
                if row["val"] == 0:
                    dq = dq + "|ZERO_VALUE" if dq != "OK" else "ZERO_VALUE"

                rows.append({
                    "ticker":            ticker,
                    "cik":               cik,
                    "cal_year":          cal_year,
                    "fiscal_period_end": row["end_date"].date().isoformat(),
                    "line_item":         line_item,
                    "value":             float(row["val"]),
                    "source_tag":        tag,
                    "data_quality":      dq,
                    "form":              row.get("form", ""),
                    "filed":             row["filed_date"].date().isoformat(),
                })

            if claimed_years >= expected_years:
                break  # All expected years for this line item have been found

        # For any expected years not claimed by any tag, emit MISSING_TAG sentinel rows
        missing_years = sorted(expected_years - claimed_years)
        if missing_years:
            if not claimed_years:
                logger.warning(f"[{ticker}] MISSING_TAG for line_item='{line_item}' — none of {tags} had annual data.")
            for cal_year in missing_years:
                rows.append({
                    "ticker":            ticker,
                    "cik":               cik,
                    "cal_year":          cal_year,
                    "fiscal_period_end": None,
                    "line_item":         line_item,
                    "value":             float("nan"),
                    "source_tag":        None,
                    "data_quality":      "MISSING_TAG",
                    "form":              None,
                    "filed":             None,
                })

    df = pd.DataFrame(rows)

    # Ensure there are no duplicate (ticker, cal_year, line_item) rows.
    # If deduplication above didn't fully resolve, keep the row with the
    # latest filed date (most recent data wins).
    if not df.empty:
        df = (
            df.sort_values("filed", ascending=False, na_position="last")
              .drop_duplicates(subset=["ticker", "cal_year", "line_item"], keep="first")
              .sort_values(["cal_year", "line_item"])
              .reset_index(drop=True)
        )

    logger.info(f"[{ticker}] Normalized {len(df)} rows across {df['cal_year'].nunique() if not df.empty else 0} calendar years.")
    return df


def _expected_cal_years(fye_month: int) -> list[int]:
    """Return the list of calendar years we expect to have data for.

    Based on MIN_HISTORY_YEARS and today's date.
    """
    this_year = date.today().year
    return list(range(this_year - MIN_HISTORY_YEARS, this_year + 1))
