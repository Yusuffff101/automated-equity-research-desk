"""
ingestion/edgar_client.py — SEC EDGAR company-facts API client.

WHY this file exists:
  The SEC EDGAR /api/xbrl/companyfacts endpoint returns a rich JSON document
  containing every XBRL-tagged fact ever filed by a company, across all
  reporting periods and all taxonomies. This client handles:
    1. Fetching that JSON with a polite rate-limited, properly identified
       User-Agent (as required by SEC Fair Access policy).
    2. Caching the raw response to data/raw/ so repeated pipeline runs
       don't re-hit the API unnecessarily.
    3. Raising informative errors rather than silently returning empty data.

API reference: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json
"""

import json
import time
import logging
from pathlib import Path

import requests

from config import (
    EDGAR_BASE_URL,
    EDGAR_USER_AGENT,
    EDGAR_REQUEST_DELAY_SECONDS,
    RAW_DIR,
)

logger = logging.getLogger(__name__)

# Track the timestamp of the last request so we can enforce the inter-request delay.
_last_request_time: float = 0.0


def _rate_limit() -> None:
    """Pause execution if needed so we respect the configured request delay.

    WHY: SEC EDGAR's Fair Access policy asks crawlers to stay under 10 req/sec.
    Rather than using a fixed sleep on every call, we measure elapsed time since
    the last request and only sleep the remaining fraction, so we don't add
    unnecessary latency when the caller itself has taken longer than the delay.
    """
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    remaining = EDGAR_REQUEST_DELAY_SECONDS - elapsed
    if remaining > 0:
        time.sleep(remaining)
    _last_request_time = time.monotonic()


def _raw_cache_path(ticker: str) -> Path:
    """Return the path to the cached raw JSON file for a given ticker."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR / f"{ticker}.json"


def fetch_company_facts(ticker: str, cik: str, use_cache: bool = True) -> dict:
    """Fetch (or load from cache) the SEC EDGAR company-facts JSON for one company.

    Args:
        ticker:    The stock ticker symbol (used for cache filename + logging).
        cik:       The SEC CIK number as a string (e.g. "0001820953").
        use_cache: If True, return the cached file when it exists and skip the
                   API call. Set to False to force a fresh pull.

    Returns:
        The parsed JSON response as a dict with keys: 'cik', 'entityName', 'facts'.

    Raises:
        requests.HTTPError: If the API returns a non-200 status.
        ValueError:         If the response JSON is malformed or missing 'facts'.
    """
    cache_path = _raw_cache_path(ticker)

    # --- Cache hit ---
    if use_cache and cache_path.exists():
        logger.info(f"[{ticker}] Loading from cache: {cache_path}")
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # --- API call ---
    # CIK must be zero-padded to 10 digits in the URL (SEC requirement).
    cik_int = int(cik.lstrip("0") or "0")
    url = f"{EDGAR_BASE_URL}/CIK{cik_int:010d}.json"
    headers = {"User-Agent": EDGAR_USER_AGENT}

    _rate_limit()
    logger.info(f"[{ticker}] Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Basic sanity check before caching
    if "facts" not in data:
        raise ValueError(
            f"[{ticker}] Unexpected EDGAR response: 'facts' key missing. "
            f"Keys found: {list(data.keys())}"
        )

    # Persist raw response to disk
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    logger.info(f"[{ticker}] Cached to: {cache_path} ({cache_path.stat().st_size:,} bytes)")

    return data
