"""
dashboard/components/anomaly_panel.py — Executive Anomaly & Red-Flag Panel.

Features:
  1. Top-of-page prominent executive threat matrix (Distress Zone, Manipulation Risk, Restatements).
  2. Highlighted Forensic Cross-Correlation Container linking Phase 3 outliers with Phase 4 scores.
  3. Interactive Heatmap Matrices for Altman Z-Score Zones and Beneish M-Score Risks.
  4. Detailed audit cards with full numerical explanation strings.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.utils import (
    PEER_COLORS,
    STATUS_COLORS,
    METRIC_METADATA,
)
from dashboard.data_loader import (
    get_company_name,
    load_cross_correlation,
)


def render_anomaly_panel(
    selected_tickers: list[str],
    anomalies_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
) -> None:
    """Render the Anomaly & Red-Flag Panel."""
    st.markdown("### 🚨 Forensic Anomaly & Distress Intelligence")
    st.markdown(
        "Executive overview of balance-sheet solvency distress, earnings-manipulation risk, "
        "and SEC filing restatements. Grounded in adapted financial-institution models."
    )

    # --------------------------------------------------------------------------
    # 1. Prominent Executive Threat Matrix (Top of Page)
    # --------------------------------------------------------------------------
    st.markdown("#### ⚡ Executive Threat Matrix")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div style="background-color: #1e1e2f; padding: 16px; border-radius: 8px; border-left: 5px solid #ef4444;">
                <div style="font-size: 13px; font-weight: 700; color: #f87171; text-transform: uppercase; letter-spacing: 0.5px;">
                    🚨 Solvency Distress Warnings (Z < 1.81)
                </div>
                <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin: 6px 0;">
                    5 of 9 Peers Flagged
                </div>
                <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">
                    • <b>AFRM:</b> FY22–FY25 persistent distress (Z: -0.12 to 1.65)<br>
                    • <b>OPRT:</b> FY22–FY23 subprime credit distress (Z: 0.23–0.35)<br>
                    • <b>PGY:</b> FY24 restatement shock (Z: 0.66)<br>
                    • <b>UPST:</b> FY22–FY23 rate shock & inventory overhang (Z: 0.72–1.39)<br>
                    • <b>SOFI:</b> FY21–FY22 de-SPAC transition burn (Z: 0.14–1.48)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div style="background-color: #1e1e2f; padding: 16px; border-radius: 8px; border-left: 5px solid #f59e0b;">
                <div style="font-size: 13px; font-weight: 700; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.5px;">
                    ⚠️ Elevated Manipulation & Accrual Risk
                </div>
                <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin: 6px 0;">
                    3 Peers Above Cutoff (> -1.78)
                </div>
                <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">
                    • <b>UPST 2022:</b> M-Score <b>+1.28</b> (Receivables build +300% divergence vs revenue, TATA +0.28)<br>
                    • <b>SOFI 2022–2023:</b> M-Score <b>-0.01 to -0.29</b> (+52% rev growth, non-cash accruals > +23% TA)<br>
                    • <b>LC 2024–2025:</b> M-Score <b>-1.62 to -1.74</b> (Accruals ratio +25% of assets)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div style="background-color: #1e1e2f; padding: 16px; border-radius: 8px; border-left: 5px solid #8b5cf6;">
                <div style="font-size: 13px; font-weight: 700; color: #c084fc; text-transform: uppercase; letter-spacing: 0.5px;">
                    📜 Accounting Restatements & Off-BS
                </div>
                <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin: 6px 0;">
                    Genuine 10-K/A & ASC 825
                </div>
                <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">
                    • <b>PGY FY24 Restatement:</b> 10-K/A filed, -$401M net loss, -$944M deficit, -123% ROE<br>
                    • <b>PGY & ENVA Domain Exemption:</b> Receivables off-balance-sheet or ASC 825 FVO; DSRI neutralized to 1.0<br>
                    • <b>SEZL IPO Timing:</b> FY21–22 quarantined as PRE_IPO; 2025 Safe Zone (Z = 8.55)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 2. Highlighted Forensic Cross-Correlation Container
    # --------------------------------------------------------------------------
    st.markdown(
        """
        <div style="background-color: #1e293b; padding: 18px 24px; border: 1px solid #3b82f6; border-radius: 8px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="font-size: 17px; font-weight: 800; color: #60a5fa;">
                    🔬 Forensic Cross-Correlation: Phase 3 Outliers vs. Phase 4 Distress Scores
                </div>
                <span style="background-color: #1d4ed8; color: #ffffff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px;">
                    CORE ANALYTICAL EVIDENCE
                </span>
            </div>
            <div style="font-size: 13px; color: #e2e8f0; margin-top: 8px; line-height: 1.5;">
                In Phase 3, an automated audit identified <b>17 extreme distress ratio observations</b> across the 9 peers.
                Cross-referencing these against Phase 4's adapted models confirms that ratio distortions (negative interest coverage, extreme negative ROE)
                consistently translate into <b>Altman Z-Score Distress Zone</b> placements and high accrual burdens.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    corr_df = load_cross_correlation()
    if not corr_df.empty:
        # Filter for selected tickers if any match
        corr_filtered = corr_df[corr_df["ticker"].isin(selected_tickers)]
        if corr_filtered.empty:
            corr_filtered = corr_df  # Fallback to full audit table if selected tickers have no outliers

        corr_display = corr_filtered[[
            "ticker", "cal_year", "phase3_outlier_reason", "adapted_z_score", "z_zone", "correlation_signal"
        ]].copy()
        corr_display.columns = [
            "Ticker", "Year", "Phase 3 Ratio Outlier Signal", "Adapted Z-Score", "Zone Classification", "Analytical Synthesis"
        ]
        st.dataframe(corr_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 3. Interactive Risk Heatmaps
    # --------------------------------------------------------------------------
    st.markdown("#### 🗺️ Cross-Sectional Risk Heatmaps (2021–2026)")

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.markdown("##### Adapted Altman Z-Score Zones")
        z_df = anomalies_df[anomalies_df["anomaly_name"] == "adapted_altman_z_score"]
        _render_heatmap(
            z_df,
            val_col="classification",
            title="Altman Z-Score Zones (Green=Safe, Yellow=Grey, Red=Distress, Grey=Pre-IPO)",
            color_map={
                "SAFE_ZONE": 3,
                "GREY_ZONE": 2,
                "DISTRESS_ZONE": 1,
                "PRE_IPO_UNAVAILABLE": 0,
                "MISSING_DATA": -1,
            },
            hover_val_col="score_formatted",
        )

    with col_h2:
        st.markdown("##### Adapted Beneish M-Score Risks")
        m_df = anomalies_df[anomalies_df["anomaly_name"] == "adapted_beneish_m_score"]
        _render_heatmap(
            m_df,
            val_col="classification",
            title="Beneish M-Score Risk (Green=Low Risk <= -1.78, Red=Elevated > -1.78)",
            color_map={
                "LOW_MANIPULATION_RISK": 2,
                "ELEVATED_MANIPULATION_RISK": 1,
                "INSUFFICIENT_HISTORY": 0,
                "MISSING_DATA": -1,
            },
            hover_val_col="score_formatted",
        )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 4. Detailed Anomaly Audit Explorer (Explanation Strings with Exact Numbers)
    # --------------------------------------------------------------------------
    st.markdown("#### 🔎 Anomaly Explanation Explorer")
    st.markdown(
        "Inspect the exact mathematical drivers and line-item contributions for any company and model. "
        "Every explanation references actual dollar amounts and growth rates, avoiding generic templates."
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        exp_ticker = st.selectbox(
            "Select Company:",
            options=selected_tickers,
            format_func=lambda t: f"{t} — {get_company_name(t)}",
        )
    with col_f2:
        exp_model = st.selectbox(
            "Select Anomaly Model:",
            options=[
                "adapted_altman_z_score",
                "adapted_beneish_m_score",
                "accruals_ratio",
                "growth_divergence",
            ],
            format_func=lambda m: f"{METRIC_METADATA[m]['label']} ({METRIC_METADATA[m]['adaptation_label']})",
        )

    exp_records = anomalies_df[
        (anomalies_df["ticker"] == exp_ticker) &
        (anomalies_df["anomaly_name"] == exp_model)
    ].sort_values("cal_year", ascending=False)

    for _, row in exp_records.iterrows():
        yr = row["cal_year"]
        score_str = row["score_formatted"]
        cls = row["classification"]
        exp = row["explanation"]

        badge_color = STATUS_COLORS.get(cls, "#64748b")

        with st.expander(f"📅 Calendar Year {yr} — Score: {score_str} [{cls}]", expanded=(yr in [2024, 2025])):
            st.markdown(
                f"""
                <div style="padding: 10px; background-color: #0f172a; border-radius: 6px; border-left: 4px solid {badge_color};">
                    <div style="color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                        Status: <span style="color: {badge_color};">{cls}</span> | Period End: {row.get('fiscal_period_end', 'N/A')}
                    </div>
                    <div style="color: #f1f5f9; font-size: 14px; margin-top: 6px; line-height: 1.5;">
                        {exp}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_heatmap(
    df: pd.DataFrame,
    val_col: str,
    title: str,
    color_map: dict[str, int],
    hover_val_col: str,
) -> None:
    """Render an institutional heatmap for status classifications."""
    pivot_numeric = df.pivot(index="ticker", columns="cal_year", values=val_col).map(lambda v: color_map.get(str(v), -1))
    pivot_hover = df.pivot(index="ticker", columns="cal_year", values=hover_val_col)
    pivot_status = df.pivot(index="ticker", columns="cal_year", values=val_col)

    tickers = pivot_numeric.index.tolist()
    years = pivot_numeric.columns.tolist()
    z_vals = pivot_numeric.values

    # Custom discrete colorscale
    colorscale = [
        [0.0, "#334155"],    # -1: Missing
        [0.2, "#64748b"],    # 0: Pre-IPO / History
        [0.4, "#ef4444"],    # 1: Distress / Elevated
        [0.7, "#f59e0b"],    # 2: Grey Zone / Low Risk
        [1.0, "#10b981"],    # 3: Safe Zone
    ]

    hovertext = []
    for t_idx, t in enumerate(tickers):
        row_text = []
        for y_idx, y in enumerate(years):
            val_str = pivot_hover.loc[t, y]
            stat_str = pivot_status.loc[t, y]
            row_text.append(f"<b>{t} ({y})</b><br>Score: {val_str}<br>Status: {stat_str}")
        hovertext.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=years,
        y=tickers,
        colorscale=colorscale,
        showscale=False,
        hoverinfo="text",
        text=hovertext,
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        margin=dict(l=50, r=20, t=10, b=30),
        height=280,
        xaxis=dict(dtick=1, title="Year"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)
