"""
dashboard/app.py — Main Entry Point for Automated Equity Research Desk Dashboard.

Run via:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from config import COMPANIES
from dashboard.data_loader import (
    load_financials,
    load_ratios,
    load_market_data,
    load_anomalies,
    get_company_name,
)
from dashboard.components.peer_comparison import render_peer_comparison
from dashboard.components.anomaly_panel import render_anomaly_panel
from dashboard.components.company_deep_dive import render_company_deep_dive
from dashboard.components.methodology_guide import render_methodology_guide


# ---------------------------------------------------------------------------
# Page Configuration & Institutional Theme Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Automated Equity Research Desk | Fintech & Specialty Lenders",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* Dark Institutional Theme */
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    
    /* Top Header Pill */
    .header-pill {
        display: inline-block;
        background-color: #1e293b;
        color: #38bdf8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        padding: 4px 10px;
        border-radius: 9999px;
        text-transform: uppercase;
        margin-bottom: 8px;
        border: 1px solid #0284c7;
    }
    
    /* Metric Card */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    # -----------------------------------------------------------------------
    # Sidebar Controls
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.markdown('<div class="header-pill">EQUITY RESEARCH DESK</div>', unsafe_allow_html=True)
        st.markdown("## **Fintech & Lenders**")
        st.caption("Sub-sector: BNPL & Tech-Driven Consumer Credit")

        st.markdown("---")
        st.markdown("### ⚙️ Peer & View Controls")

        # Peer multi-selection
        all_tickers = list(COMPANIES.keys())
        default_peers = ["AFRM", "SEZL", "UPST", "SOFI", "PGY"]
        selected_tickers = st.multiselect(
            "Select Peer Companies (2+):",
            options=all_tickers,
            default=default_peers,
            format_func=lambda t: f"{t} ({get_company_name(t)})",
            help="Select public lenders to compare. Pick 2 or more constituents.",
        )

        # Outlier clipping toggle
        clip_outliers = st.checkbox(
            "Clip Extreme Outliers on Axes",
            value=True,
            help="Default to a readable visual axis range for extreme values (e.g. SEZL -430% ROE, AFRM -12x coverage). True unclipped values always appear in hover tooltips and tables.",
        )

        # Year Range Slider
        year_range = st.slider(
            "Calendar Year Range:",
            min_value=2021,
            max_value=2026,
            value=(2021, 2026),
            step=1,
            help="Coverage universe spans 2021–2026 (AFRM June 2026 annual filing included).",
        )

        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        nav_mode = st.radio(
            "Select View:",
            options=[
                "📊 Peer Comparison View",
                "🚨 Forensic Anomaly & Distress Panel",
                "📑 Company Forensic Deep-Dive",
                "ℹ️ Methodology & Adaptation Guide",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 11px; color: #64748b; line-height: 1.4;">
                <b>Data Integrity & Provenance:</b><br>
                • Financials: Direct SEC EDGAR XBRL (10-K/A)<br>
                • Market Caps: yfinance Year-End Share Prices<br>
                • Pipeline: SQLite + Pandas + Plotly
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Data Ingestion from Cache
    # -----------------------------------------------------------------------
    with st.spinner("Loading normalized financial database..."):
        financials_df = load_financials()
        ratios_df = load_ratios()
        market_df = load_market_data()
        anomalies_df = load_anomalies()

    # -----------------------------------------------------------------------
    # View Router
    # -----------------------------------------------------------------------
    if nav_mode == "📊 Peer Comparison View":
        render_peer_comparison(
            selected_tickers=selected_tickers,
            year_range=year_range,
            clip_outliers=clip_outliers,
            ratios_df=ratios_df,
            anomalies_df=anomalies_df,
            market_df=market_df,
        )
    elif nav_mode == "🚨 Forensic Anomaly & Distress Panel":
        render_anomaly_panel(
            selected_tickers=selected_tickers,
            anomalies_df=anomalies_df,
            ratios_df=ratios_df,
        )
    elif nav_mode == "📑 Company Forensic Deep-Dive":
        render_company_deep_dive(
            selected_tickers=selected_tickers,
            financials_df=financials_df,
            ratios_df=ratios_df,
            anomalies_df=anomalies_df,
            market_df=market_df,
        )
    elif nav_mode == "ℹ️ Methodology & Adaptation Guide":
        render_methodology_guide()


if __name__ == "__main__":
    main()
