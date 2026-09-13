"""
dashboard/components/company_deep_dive.py — Single-Company Forensic Profile.

Displays a complete 5-year longitudinal breakdown of:
  - Top-line and balance-sheet financials
  - 10 financial ratios
  - 4 forensic anomaly and solvency scores with audit explanations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import COMPANIES
from dashboard.data_loader import get_company_name
from dashboard.utils import PEER_COLORS, METRIC_METADATA, STATUS_COLORS


def render_company_deep_dive(
    selected_tickers: list[str],
    financials_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
    anomalies_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> None:
    """Render single-company forensic deep-dive."""
    st.markdown("### 📑 Company Forensic Deep-Dive")
    st.markdown("Inspect a comprehensive multi-year fundamental and forensic audit profile for any coverage constituent.")

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        active_ticker = st.selectbox(
            "Select Focus Company:",
            options=list(COMPANIES.keys()),
            index=list(COMPANIES.keys()).index("PGY") if "PGY" in COMPANIES else 0,
            format_func=lambda t: f"{t} — {get_company_name(t)}",
        )

    cik = COMPANIES.get(active_ticker, {}).get("cik", "")
    fye_month = COMPANIES.get(active_ticker, {}).get("fye_month", 12)
    fye_str = "June 30" if fye_month == 6 else "December 31"

    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 14px 20px; border-radius: 8px; margin: 10px 0 20px 0; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 20px; font-weight: 800; color: #f8fafc;">{get_company_name(active_ticker)} ({active_ticker})</span>
                    <span style="color: #94a3b8; font-size: 13px; margin-left: 12px;">CIK: {cik} | FYE: {fye_str}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_fin, tab_rat, tab_anom = st.tabs([
        "💵 Fundamental Financials",
        "📊 Financial Ratios (10 Metrics)",
        "🚨 Forensic Anomaly & Distress Audit",
    ])

    # 1. Fundamental Financials
    with tab_fin:
        c_fin = financials_df[financials_df["ticker"] == active_ticker].copy()
        if not c_fin.empty:
            piv_fin = c_fin.pivot(index="line_item", columns="cal_year", values="value")
            # Format dollars
            piv_disp = piv_fin.map(lambda v: f"${v / 1e6:,.1f}M" if pd.notna(v) else "—")
            st.dataframe(piv_disp, use_container_width=True)

            # Revenue vs Net Income bar chart
            st.markdown("##### Topline Revenue vs. Net Income ($M)")
            rev_ni = c_fin[c_fin["line_item"].isin(["revenue", "net_income"])].pivot(
                index="cal_year", columns="line_item", values="value"
            ).dropna()

            if not rev_ni.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=rev_ni.index, y=rev_ni["revenue"] / 1e6,
                    name="Revenue ($M)", marker_color="#3b82f6"
                ))
                fig.add_trace(go.Bar(
                    x=rev_ni.index, y=rev_ni["net_income"] / 1e6,
                    name="Net Income ($M)", marker_color="#10b981"
                ))
                fig.update_layout(
                    template="plotly_dark",
                    barmode="group",
                    paper_bgcolor="#0f172a",
                    plot_bgcolor="#1e293b",
                    height=300,
                    margin=dict(l=40, r=20, t=20, b=30),
                )
                st.plotly_chart(fig, use_container_width=True)

    # 2. Financial Ratios
    with tab_rat:
        c_rat = ratios_df[ratios_df["ticker"] == active_ticker].copy()
        if not c_rat.empty:
            piv_rat = c_rat.pivot(index="ratio_name", columns="cal_year", values="value_formatted").fillna("—")
            st.dataframe(piv_rat, use_container_width=True)

    # 3. Anomaly Scores & Full Explanations
    with tab_anom:
        c_anom = anomalies_df[anomalies_df["ticker"] == active_ticker].sort_values(
            ["anomaly_name", "cal_year"], ascending=[True, False]
        )
        if not c_anom.empty:
            piv_anom = c_anom.pivot(index="anomaly_name", columns="cal_year", values="score_formatted").fillna("—")
            st.dataframe(piv_anom, use_container_width=True)

            st.markdown("##### Detailed Explanation Strings (By Model & Year)")
            for a_name in c_anom["anomaly_name"].unique():
                meta = METRIC_METADATA.get(a_name, {})
                st.markdown(f"**{meta.get('label', a_name)}** *({meta.get('adaptation_label', '')})*")
                sub_records = c_anom[c_anom["anomaly_name"] == a_name]
                for _, r in sub_records.iterrows():
                    cls = r["classification"]
                    color = STATUS_COLORS.get(cls, "#64748b")
                    st.markdown(
                        f"""
                        <div style="background-color: #0f172a; padding: 8px 14px; border-left: 3px solid {color}; border-radius: 4px; margin-bottom: 6px; font-size: 13px;">
                            <b>{r['cal_year']}:</b> <span style="color: {color}; font-weight: 700;">[{cls}]</span> {r['score_formatted']}<br>
                            <span style="color: #cbd5e1;">{r['explanation']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
