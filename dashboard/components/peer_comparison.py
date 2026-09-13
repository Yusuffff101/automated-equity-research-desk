"""
dashboard/components/peer_comparison.py — Interactive Peer Comparison View.

Features:
  1. Side-by-side comparison across 2+ companies over calendar years 2021–2026.
  2. Prominent inline adaptation labels for Adapted Altman Z and Beneish M-Scores.
  3. Outlier scaling/clipping toggle (default: clipped to readable axis range with true value on hover).
  4. Explicit visual states for PRE_IPO_UNAVAILABLE, MISSING_DATA, and NOT_APPLICABLE.
  5. Color-coded side-by-side data table with quality flags.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.utils import (
    PEER_COLORS,
    METRIC_METADATA,
    prepare_chart_series,
    format_metric_value,
)
from dashboard.data_loader import (
    get_company_name,
    get_peer_ratio_timeseries,
    get_peer_anomaly_timeseries,
)


def render_peer_comparison(
    selected_tickers: list[str],
    year_range: tuple[int, int],
    clip_outliers: bool,
    ratios_df: pd.DataFrame,
    anomalies_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> None:
    """Render the Peer Comparison tab."""
    st.markdown("### 📊 Peer Comparison & Fundamental Trends")
    st.markdown(
        "Compare operational ratios, credit leverage, and forensic anomaly scores across selected fintech peers. "
        "All adapted scores prominently disclose non-standard financial institution adjustments inline."
    )

    if len(selected_tickers) < 2:
        st.warning("⚠️ Please select at least 2 companies in the sidebar to compare peers.")
        return

    # Category Selection
    cat_tabs = st.tabs([
        "🛡️ Distress & Health (Altman Z)",
        "🔍 Earnings Quality (Beneish M & Accruals)",
        "📈 Profitability (ROE, ROA, Margins)",
        "⚖️ Leverage (Debt, Coverage)",
        "⚡ Efficiency (Turnover)",
    ])

    min_yr, max_yr = year_range

    # --------------------------------------------------------------------------
    # Tab 1: Distress & Health (Adapted Altman Z)
    # --------------------------------------------------------------------------
    with cat_tabs[0]:
        _render_metric_view(
            metric_key="adapted_altman_z_score",
            source_df=anomalies_df,
            is_anomaly=True,
            selected_tickers=selected_tickers,
            min_yr=min_yr,
            max_yr=max_yr,
            clip_outliers=clip_outliers,
            show_zones="altman",
        )

    # --------------------------------------------------------------------------
    # Tab 2: Earnings Quality (Beneish M-Score, Accruals, Growth Divergence)
    # --------------------------------------------------------------------------
    with cat_tabs[1]:
        sub_metric = st.radio(
            "Select Forensic Model:",
            options=["adapted_beneish_m_score", "accruals_ratio", "growth_divergence"],
            format_func=lambda k: f"{METRIC_METADATA[k]['label']} — {METRIC_METADATA[k]['adaptation_label']}",
            horizontal=True,
        )
        _render_metric_view(
            metric_key=sub_metric,
            source_df=anomalies_df,
            is_anomaly=True,
            selected_tickers=selected_tickers,
            min_yr=min_yr,
            max_yr=max_yr,
            clip_outliers=clip_outliers,
            show_zones="beneish" if sub_metric == "adapted_beneish_m_score" else None,
        )

    # --------------------------------------------------------------------------
    # Tab 3: Profitability (ROE, ROA, Net Margin)
    # --------------------------------------------------------------------------
    with cat_tabs[2]:
        sub_metric = st.radio(
            "Select Profitability Metric:",
            options=["roe", "roa", "net_margin"],
            format_func=lambda k: f"{METRIC_METADATA[k]['label']} — {METRIC_METADATA[k]['adaptation_label']}",
            horizontal=True,
        )
        _render_metric_view(
            metric_key=sub_metric,
            source_df=ratios_df,
            is_anomaly=False,
            selected_tickers=selected_tickers,
            min_yr=min_yr,
            max_yr=max_yr,
            clip_outliers=clip_outliers,
        )

    # --------------------------------------------------------------------------
    # Tab 4: Leverage (Debt-to-Equity, Interest Coverage)
    # --------------------------------------------------------------------------
    with cat_tabs[3]:
        sub_metric = st.radio(
            "Select Leverage Metric:",
            options=["interest_coverage", "debt_to_equity"],
            format_func=lambda k: f"{METRIC_METADATA[k]['label']} — {METRIC_METADATA[k]['adaptation_label']}",
            horizontal=True,
        )
        _render_metric_view(
            metric_key=sub_metric,
            source_df=ratios_df,
            is_anomaly=False,
            selected_tickers=selected_tickers,
            min_yr=min_yr,
            max_yr=max_yr,
            clip_outliers=clip_outliers,
        )

    # --------------------------------------------------------------------------
    # Tab 5: Efficiency (Asset & Receivables Turnover)
    # --------------------------------------------------------------------------
    with cat_tabs[4]:
        sub_metric = st.radio(
            "Select Efficiency Metric:",
            options=["asset_turnover", "receivables_turnover"],
            format_func=lambda k: f"{METRIC_METADATA[k]['label']} — {METRIC_METADATA[k]['adaptation_label']}",
            horizontal=True,
        )
        _render_metric_view(
            metric_key=sub_metric,
            source_df=ratios_df,
            is_anomaly=False,
            selected_tickers=selected_tickers,
            min_yr=min_yr,
            max_yr=max_yr,
            clip_outliers=clip_outliers,
        )


def _render_metric_view(
    metric_key: str,
    source_df: pd.DataFrame,
    is_anomaly: bool,
    selected_tickers: list[str],
    min_yr: int,
    max_yr: int,
    clip_outliers: bool,
    show_zones: str | None = None,
) -> None:
    """Render chart, explanation badge, and comparative table for a metric."""
    meta = METRIC_METADATA.get(metric_key, {})
    label = meta.get("label", metric_key)
    adaptation = meta.get("adaptation_label", "")
    tooltip = meta.get("tooltip", "")

    # Adaptation callout container
    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 12px 18px; border-left: 4px solid #3b82f6; border-radius: 6px; margin: 12px 0;">
            <div style="font-weight: 700; color: #f8fafc; font-size: 15px;">
                {label} <span style="color: #93c5fd; font-weight: 500; font-size: 13px;">— {adaptation}</span>
            </div>
            <div style="color: #cbd5e1; font-size: 13px; margin-top: 4px;">
                {tooltip}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter raw data
    if is_anomaly:
        sub_df = get_peer_anomaly_timeseries(source_df, selected_tickers, metric_key)
    else:
        sub_df = get_peer_ratio_timeseries(source_df, selected_tickers, metric_key)

    sub_df = sub_df[(sub_df["cal_year"] >= min_yr) & (sub_df["cal_year"] <= max_yr)]

    if sub_df.empty:
        st.info("No data available for the selected period range.")
        return

    # Prepare chart dataframe with clipping and N/A metadata
    plot_df = prepare_chart_series(sub_df, metric_key, clip_outliers=clip_outliers)

    # 1. Interactive Plotly Line Chart
    fig = go.Figure()

    # Optional Zone Shading for Altman Z
    if show_zones == "altman":
        fig.add_hrect(
            y0=-5, y1=1.81,
            fillcolor="#ef4444", opacity=0.08, line_width=0,
            annotation_text="Distress Zone (Z < 1.81)", annotation_position="top left",
            annotation_font=dict(size=11, color="#ef4444"),
        )
        fig.add_hrect(
            y0=1.81, y1=2.99,
            fillcolor="#f59e0b", opacity=0.08, line_width=0,
            annotation_text="Grey Zone (1.81 - 2.99)", annotation_position="top left",
            annotation_font=dict(size=11, color="#f59e0b"),
        )
        fig.add_hrect(
            y0=2.99, y1=15,
            fillcolor="#10b981", opacity=0.08, line_width=0,
            annotation_text="Safe Zone (Z > 2.99)", annotation_position="top left",
            annotation_font=dict(size=11, color="#10b981"),
        )

    # Optional Reference Line for Beneish M
    if show_zones == "beneish":
        fig.add_hline(
            y=-1.78, line_dash="dash", line_color="#ef4444", line_width=1.5,
            annotation_text="Directional Cutoff (-1.78): Scores above indicate elevated risk",
            annotation_position="bottom right",
            annotation_font=dict(size=11, color="#ef4444"),
        )

    # Plot lines per company
    has_clipped_points = False
    for ticker in selected_tickers:
        comp_data = plot_df[plot_df["ticker"] == ticker].sort_values("cal_year")
        color = PEER_COLORS.get(ticker, "#3b82f6")

        # Valid numeric points
        valid_points = comp_data[comp_data["data_state"] == "VALID"]
        if not valid_points.empty:
            customdata = list(zip(
                valid_points["hover_note"],
                valid_points["is_clipped"],
                valid_points["cal_year"],
            ))
            if any(valid_points["is_clipped"]):
                has_clipped_points = True

            fig.add_trace(go.Scatter(
                x=valid_points["cal_year"],
                y=valid_points["plot_value"],
                mode="lines+markers",
                name=f"{ticker} ({get_company_name(ticker)})",
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color),
                customdata=customdata,
                hovertemplate="<b>%{fullData.name}</b><br>Year: %{customdata[2]}<br>%{customdata[0]}<extra></extra>",
            ))

        # Explicit N/A Points (PRE_IPO, MISSING_DATA, NOT_APPLICABLE)
        na_points = comp_data[comp_data["data_state"] != "VALID"]
        if not na_points.empty:
            # Place markers on a subtle bottom baseline
            na_custom = list(zip(
                na_points["hover_note"],
                na_points["data_state"],
                na_points["cal_year"],
            ))
            fig.add_trace(go.Scatter(
                x=na_points["cal_year"],
                y=[0.0] * len(na_points),
                mode="markers",
                name=f"{ticker} (N/A States)",
                showlegend=False,
                marker=dict(
                    size=10,
                    symbol="square-open",
                    color="#94a3b8",
                    line=dict(width=2, color="#94a3b8"),
                ),
                customdata=na_custom,
                hovertemplate="<b>" + ticker + " [%{customdata[1]}]</b><br>Year: %{customdata[2]}<br>%{customdata[0]}<extra></extra>",
            ))

    if has_clipped_points and clip_outliers:
        st.caption("ℹ️ *Notice: Extreme outlier points are visually capped on the axis to preserve peer readability. Hover over any point to inspect the true unclipped value.*")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        margin=dict(l=40, r=40, t=30, b=40),
        height=420,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        xaxis=dict(
            title="Calendar Year",
            dtick=1,
            gridcolor="#334155",
            showgrid=True,
        ),
        yaxis=dict(
            title=label,
            gridcolor="#334155",
            showgrid=True,
            zeroline=True,
            zerolinecolor="#475569",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 2. Side-by-Side Comparison Pivot Table
    st.markdown("##### 📋 Side-by-Side Comparison Table")
    
    val_col = "score_formatted" if is_anomaly else "value_formatted"
    pivot_df = sub_df.pivot(index="ticker", columns="cal_year", values=val_col)
    pivot_df.index = [f"{t} ({get_company_name(t)})" for t in pivot_df.index]
    pivot_df = pivot_df.fillna("—")

    st.dataframe(pivot_df, use_container_width=True)
