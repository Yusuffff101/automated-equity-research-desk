"""
config.py — Central configuration for the Automated Equity Research Desk pipeline.

This file is the single source of truth for:
  - The company universe (tickers, CIKs, names, fiscal year-end months)
  - File paths
  - API behaviour (rate limiting, User-Agent)
  - Data ingestion parameters (years of history)

WHY fiscal year-end month matters:
  AFRM and SEZL report on a June 30 FYE (month=6). All other companies
  use December 31 (month=12). The normalizer uses `fye_month` to assign
  a consistent `cal_year` label across the peer set. See METHODOLOGY.md.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR   = Path(__file__).parent
DATA_DIR   = ROOT_DIR / "data"
RAW_DIR    = DATA_DIR / "raw"
NORM_DIR   = DATA_DIR / "normalized"
MAP_DIR    = DATA_DIR / "mappings"

SQLITE_PATH          = NORM_DIR / "financials.db"
CSV_PATH             = NORM_DIR / "financials.csv"
RATIOS_CSV_PATH      = NORM_DIR / "ratios.csv"
MARKET_DATA_RAW_DIR  = RAW_DIR  / "market_data"
MARKET_DATA_CSV_PATH = NORM_DIR / "market_data.csv"
ANOMALIES_CSV_PATH   = NORM_DIR / "anomalies.csv"
TAG_MAP_PATH         = MAP_DIR  / "xbrl_tag_map.json"

# ---------------------------------------------------------------------------
# SEC EDGAR API
# ---------------------------------------------------------------------------
# SEC guidance: identify yourself in the User-Agent header.
# Format: "CompanyName AppName contact@email.com"
EDGAR_USER_AGENT = "EquityResearchDesk ingestion-pipeline yusuf@example.com"
EDGAR_BASE_URL   = "https://data.sec.gov/api/xbrl/companyfacts"

# Polite delay between API requests — SEC recommends staying below 10 req/sec.
# 0.15 seconds = ~6.7 req/sec, giving comfortable headroom.
EDGAR_REQUEST_DELAY_SECONDS = 0.15

# ---------------------------------------------------------------------------
# Data parameters
# ---------------------------------------------------------------------------
# Pull this many full fiscal years of history per company.
# 5 years gives us FY2021–FY2025 for Dec-FYE companies (OMF, ENVA, etc.)
# and FY2022–FY2026 for AFRM/SEZL (June FYE, so their latest is FY ending Jun 2026).
MIN_HISTORY_YEARS = 5

# ---------------------------------------------------------------------------
# Company universe
# ---------------------------------------------------------------------------
# fye_month: the calendar month of fiscal year-end (6 = June 30, 12 = December 31).
# CIKs verified against SEC EDGAR EFTS on 2026-09-13.
COMPANIES = {
    "AFRM": {
        "cik":       "0001820953",
        "name":      "Affirm Holdings, Inc.",
        "fye_month": 6,    # June 30 fiscal year-end
        "sic":       "6141",
    },
    "SEZL": {
        "cik":       "0001662991",
        "name":      "Sezzle Inc.",
        "fye_month": 12,   # December 31 fiscal year-end (NOTE: Sezzle uses Dec 31)
        "sic":       "7389",
    },
    "UPST": {
        "cik":       "0001647639",
        "name":      "Upstart Holdings, Inc.",
        "fye_month": 12,
        "sic":       "6199",
    },
    "SOFI": {
        "cik":       "0001818874",
        "name":      "SoFi Technologies, Inc.",
        "fye_month": 12,
        "sic":       "6199",
    },
    "LC": {
        "cik":       "0001409970",
        "name":      "LendingClub Corp",
        "fye_month": 12,
        "sic":       "6141",
    },
    "PGY": {
        "cik":       "0001883085",
        "name":      "Pagaya Technologies Ltd.",
        "fye_month": 12,
        "sic":       "6199",
    },
    "OPRT": {
        "cik":       "0001538716",
        "name":      "Oportun Financial Corp",
        "fye_month": 12,
        "sic":       "6199",
    },
    "OMF": {
        "cik":       "0001584207",
        "name":      "OneMain Holdings, Inc.",
        "fye_month": 12,
        "sic":       "6141",
    },
    "ENVA": {
        "cik":       "0001529864",
        "name":      "Enova International, Inc.",
        "fye_month": 12,
        "sic":       "6141",
    },
}
