import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Config ────────────────────────────────────────────────────────────────────
API = "http://localhost:8000/api"

st.set_page_config(
    page_title="Production Quality Dashboard",
    page_icon="🏭",
    layout="wide",
)

# ── Fetch helpers (cache 5 phút) ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch(endpoint: str, params: dict = None):
    resp = requests.get(f"{API}/{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏭 Quality Dashboard")
    st.caption("RFID Defect Analytics · Jan–Jun 2024")
    st.divider()

    if st.button("🔄 Refresh", use_container_width=True):
        requests.post("http://localhost:8000/refresh")
        st.cache_data.clear()
        st.success("Data refreshed!")

    st.divider()
    st.markdown("**Navigate**")
    page = st.radio(
        label="page",
        options=["Overview", "Trend Analysis", "Defect Breakdown", "Repair Cost", "Anomaly Detection"],
        label_visibility="collapsed",
    )

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    summary   = fetch("summary")
    trends    = fetch("trends")
    by_line   = fetch("by-line")
    by_prod   = fetch("by-product", {"top_n": 20})
    loc_sev   = fetch("location-severity")
    anomalies = fetch("anomalies")
except Exception as e:
    st.error(f"❌ Không kết nối được API: {e}")
    st.info("Chạy backend trước: `uvicorn main:app --reload` trong thư mục backend/")
    st.stop()

# ── Convert to DataFrames ─────────────────────────────────────────────────────
df_trend    = pd.DataFrame(trends["data"])
df_line     = pd.DataFrame(by_line)
df_prod     = pd.DataFrame(by_prod)
df_locsev   = pd.DataFrame(loc_sev["data"])
df_anomaly  = pd.DataFrame(anomalies)

SEVERITY_ORDER = ["Minor", "Moderate", "Critical"]
MONTH_ORDER    = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
LINE_COLORS    = {"Line-1": "#3498db", "Line-2": "#2ecc71",
                  "Line-3": "#e67e22", "Line-4": "#e74c3c"}

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("📊 Production Quality Overview")
    st.caption(f"Data period: {summary['date_range_start']} → {summary['date_range_end']}")
    st.divider()

    # KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Defects",        f"{summary['total_defects']:,}")
    c2.metric("Total Repair Cost",    f"${summary['total_repair_cost']:,.0f}")
    c3.metric("Avg Cost / Defect",    f"${summary['avg_repair_cost']:,.0f}")
    c4.metric("Defect Rate",          f"{summary['defect_rate_pct']:.2f}%")
    c5.metric("Worst Line",           summary['most_defective_line'])

    st.divider()
    col1, col2 = st.columns(2)

    # Mini trend line
    with col1:
        st.subheader("📈 Defect Trend (Jan–Jun)")
        fig = px.line(
            df_trend, x="month_name", y="defect_count",
            markers=True, text="defect_count",
            color_discrete_sequence=["#3498db"],
        )
        fig.update_traces(textposition="top center", line_width=2.5, marker_size=8)
        fig.update_layout(
            xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
            xaxis_title="", yaxis_title="Defects",
            margin=dict(t=20, b=20), height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Defects by line — donut
    with col2:
        st.subheader("🏭 Defects by Production Line")
        fig = px.pie(
            df_line, names="production_line", values="defect_count",
            hole=0.55,
            color="production_line",
            color_discrete_map=LINE_COLORS,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20), height=280)
        st.plotly_chart(fig, use_container_width=True)

    # Line stats table
    st.subheader("📋 Production Line Summary")
    display_line = df_line.rename(columns={
        "production_line": "Line",
        "defect_count": "Defects",
        "total_repair_cost": "Total Cost ($)",
        "avg_repair_cost": "Avg Cost ($)",
        "defect_rate_pct": "Defect Rate (%)",
        "top_defect_type": "Top Defect Type",
    })
    st.dataframe(
        display_line.style.format({
            "Total Cost ($)": "{:,.0f}",
            "Avg Cost ($)": "{:,.0f}",
            "Defect Rate (%)": "{:.4f}",
        }).background_gradient(subset=["Defects"], cmap="Reds"),
        use_container_width=True, hide_index=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — TREND ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Trend Analysis":
    st.title("📈 Trend Analysis — Jan to Jun 2024")

    trend_label = {
        "increasing": "⬆️ Increasing — cần chú ý kiểm soát chất lượng",
        "decreasing": "⬇️ Decreasing — dấu hiệu tích cực",
        "stable":     "➡️ Stable — dao động trong mức bình thường",
    }
    st.info(f"**Overall trend:** {trend_label.get(trends['overall_trend'], trends['overall_trend'])}")

    # Main trend chart with anomaly highlight
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_trend["month_name"], y=df_trend["defect_count"],
        mode="lines+markers+text",
        text=df_trend["defect_count"],
        textposition="top center",
        line=dict(color="#3498db", width=2.5),
        marker=dict(size=10),
        name="Defect Count",
    ))

    # Highlight anomaly months
    anomaly_rows = df_trend[df_trend["is_anomaly"] == True]
    if not anomaly_rows.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_rows["month_name"], y=anomaly_rows["defect_count"],
            mode="markers", marker=dict(size=16, color="red", symbol="star"),
            name="⚠️ Anomaly",
        ))

    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
        xaxis_title="Month", yaxis_title="Number of Defects",
        height=380, margin=dict(t=20),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # MoM change bar
    st.subheader("📊 Month-over-Month Change (%)")
    df_mom = df_trend.dropna(subset=["mom_change_pct"]).copy()
    df_mom["color"] = df_mom["mom_change_pct"].apply(
        lambda x: "#e74c3c" if x > 0 else "#2ecc71"
    )
    fig2 = go.Figure(go.Bar(
        x=df_mom["month_name"], y=df_mom["mom_change_pct"],
        marker_color=df_mom["color"],
        text=df_mom["mom_change_pct"].apply(lambda x: f"{x:+.1f}%"),
        textposition="outside",
    ))
    fig2.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
        xaxis_title="", yaxis_title="MoM Change (%)",
        height=300, margin=dict(t=20),
        shapes=[dict(type="line", x0=-0.5, x1=5.5, y0=0, y1=0,
                     line=dict(color="gray", dash="dash"))],
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Data table
    with st.expander("📄 Raw trend data"):
        st.dataframe(df_trend, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — DEFECT BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Defect Breakdown":
    st.title("🔍 Defect Breakdown")

    tab1, tab2, tab3 = st.tabs(["📍 Location × Severity", "🏭 By Production Line", "📦 By Product"])

    # ── Tab 1: Heatmap + chi-square ──
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Heatmap: Defect Location × Severity")
            pivot = df_locsev.pivot(
                index="defect_location", columns="severity", values="count"
            ).reindex(columns=SEVERITY_ORDER).fillna(0)

            fig = px.imshow(
                pivot, text_auto=True,
                color_continuous_scale="YlOrRd",
                aspect="auto",
            )
            fig.update_layout(
                xaxis_title="Severity", yaxis_title="Defect Location",
                height=320, margin=dict(t=20),
                coloraxis_colorbar=dict(title="Count"),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Chi-Square Test")
            st.metric("Chi² Statistic", f"{loc_sev['chi2']:.4f}")
            st.metric("P-Value", f"{loc_sev['p_value']:.6f}")
            if loc_sev["is_significant"]:
                st.success("✅ Có mối quan hệ thống kê giữa defect location và severity (p < 0.05)")
            else:
                st.warning("⚠️ Không đủ bằng chứng thống kê (p ≥ 0.05)")

            st.divider()
            st.markdown("**Diễn giải:**")
            st.markdown(
                "Nếu p < 0.05, vị trí lỗi và mức độ nghiêm trọng **không độc lập** — "
                "tức là biết lỗi xảy ra ở đâu giúp dự đoán được mức độ nguy hiểm."
            )

        # Stacked bar
        st.subheader("Stacked Bar: Severity distribution theo Location")
        fig2 = px.bar(
            df_locsev,
            x="defect_location", y="count", color="severity",
            color_discrete_map={
                "Minor": "#f1c40f", "Moderate": "#e67e22", "Critical": "#e74c3c"
            },
            category_orders={"severity": SEVERITY_ORDER},
            barmode="stack",
        )

        # Tính tổng của mỗi Location
        df_total = (
            df_locsev.groupby("defect_location", as_index=False)["count"]
            .sum()
            .rename(columns={"count": "total"})
        )

        # Thêm nhãn tổng trên đầu mỗi cột
        fig2.add_scatter(
            x=df_total["defect_location"],
            y=df_total["total"],
            mode="text",
            text=df_total["total"],
            textposition="top center",
            showlegend=False,
            hoverinfo="skip",
        )

        fig2.update_layout(
            xaxis_title="Defect Location", yaxis_title="Count",
            height=400, margin=dict(t=20),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 2: By production line ──
    with tab2:
        st.subheader("Defect Count & Rate theo Production Line")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=df_line["production_line"], y=df_line["defect_count"],
                name="Defect Count",
                marker_color=[LINE_COLORS.get(l, "#999") for l in df_line["production_line"]],
                text=df_line["defect_count"], textposition="outside",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=df_line["production_line"], y=df_line["defect_rate_pct"],
                name="Defect Rate (%)",
                mode="lines+markers",
                line=dict(color="#8e44ad", width=2),
                marker=dict(size=10),
            ),
            secondary_y=True,
        )
        fig.update_layout(height=380, margin=dict(t=20), legend=dict(orientation="h", y=1.1))
        fig.update_yaxes(title_text="Defect Count", secondary_y=False)
        fig.update_yaxes(title_text="Defect Rate (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 3: Top products ──
    with tab3:
        st.subheader("Top 20 Products by Defect Count")
        top_n = st.slider("Số sản phẩm hiển thị", 5, 20, 10)
        df_top = df_prod.head(top_n)

        fig = px.bar(
            df_top.sort_values("defect_count"),
            x="defect_count", y="product_name",
            orientation="h",
            color="production_line",
            color_discrete_map=LINE_COLORS,
            text="defect_count",
            hover_data=["category", "total_repair_cost"],
        )
        fig.update_layout(
            xaxis_title="Defect Count", yaxis_title="",
            height=max(350, top_n * 35),
            margin=dict(t=20), legend_title="Line",
        )
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — REPAIR COST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Repair Cost":
    st.title("💰 Repair Cost Analysis")

    group_option = st.segmented_control(
        "Group by",
        options=["production_line", "category", "severity", "defect_type"],
        default="production_line",
    )

    cost_data = fetch("repair-cost", {"group_by": group_option})
    df_cost = pd.DataFrame(cost_data)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Total Repair Cost")
        fig = px.pie(
            df_cost, names="group", values="total_cost",
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, height=350, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Avg Cost per Defect")
        fig2 = px.bar(
            df_cost.sort_values("avg_cost", ascending=True),
            x="avg_cost", y="group", orientation="h",
            color="avg_cost", color_continuous_scale="Reds",
            text=df_cost.sort_values("avg_cost")["avg_cost"].apply(lambda x: f"${x:,.0f}"),
        )
        fig2.update_layout(
            xaxis_title="Avg Cost ($)", yaxis_title="",
            height=350, margin=dict(t=20), coloraxis_showscale=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📋 Cost Breakdown Table")
    st.dataframe(
        df_cost.rename(columns={
            "group": group_option.replace("_", " ").title(),
            "total_cost": "Total Cost ($)",
            "avg_cost": "Avg Cost ($)",
            "defect_count": "Defect Count",
        }).style.format({
            "Total Cost ($)": "{:,.2f}",
            "Avg Cost ($)": "{:,.2f}",
        }).background_gradient(subset=["Total Cost ($)"], cmap="Oranges"),
        use_container_width=True, hide_index=True,
    )

    # Export button
    st.divider()
    st.subheader("📥 Export Data")
    export_resp = requests.get("http://localhost:8000/api/export/csv")
    st.download_button(
        label="⬇️ Download Full Dataset (CSV)",
        data=export_resp.content,
        file_name="defect_data_2024.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ANOMALY DETECTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Anomaly Detection":
    st.title("⚠️ Anomaly Detection")
    st.info(
        "Tháng được đánh dấu anomaly khi số lượng defects vượt ngưỡng **mean ± 1.5 × std** "
        "(z-score > 1.5 hoặc < -1.5)."
    )

    mean_val = df_anomaly["defect_count"].mean()
    std_val  = df_anomaly["defect_count"].std()
    upper    = mean_val + 1.5 * std_val
    lower    = max(0, mean_val - 1.5 * std_val)

    fig = go.Figure()

    # Control band
    fig.add_hrect(
        y0=lower, y1=upper,
        fillcolor="rgba(52,152,219,0.1)",
        line_width=0,
        annotation_text="Normal range",
        annotation_position="top left",
    )
    fig.add_hline(y=mean_val, line_dash="dash", line_color="gray",
                  annotation_text=f"Mean: {mean_val:.0f}")
    fig.add_hline(y=upper, line_dash="dot", line_color="#e74c3c",
                  annotation_text=f"Upper: {upper:.0f}")

    # Line
    fig.add_trace(go.Scatter(
        x=df_anomaly["month_name"], y=df_anomaly["defect_count"],
        mode="lines+markers", name="Defect Count",
        line=dict(color="#3498db", width=2.5),
        marker=dict(size=10),
    ))

    # Anomaly points
    anom = df_anomaly[df_anomaly["is_anomaly"] == True]
    if not anom.empty:
        fig.add_trace(go.Scatter(
            x=anom["month_name"], y=anom["defect_count"],
            mode="markers+text",
            marker=dict(size=18, color="#e74c3c", symbol="star"),
            text=anom["month_name"],
            textposition="top center",
            name="⚠️ Anomaly",
        ))

    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
        xaxis_title="Month", yaxis_title="Defect Count",
        height=420, margin=dict(t=20),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Z-score table
    st.subheader("📋 Z-Score Table")
    display_anom = df_anomaly[["month_name", "defect_count", "z_score", "is_anomaly"]].rename(columns={
        "month_name": "Month",
        "defect_count": "Defect Count",
        "z_score": "Z-Score",
        "is_anomaly": "Anomaly?",
    })

    def highlight_anomaly(row):
        color = "background-color: #fde8e8" if row["Anomaly?"] else ""
        return [color] * len(row)

    st.dataframe(
        display_anom.style
            .apply(highlight_anomaly, axis=1)
            .format({"Z-Score": "{:.3f}"}),
        use_container_width=True, hide_index=True,
    )

    n_anomalies = int(df_anomaly["is_anomaly"].sum())
    if n_anomalies > 0:
        months = anom["month_name"].tolist()
        st.error(f"⚠️ Phát hiện **{n_anomalies} tháng bất thường**: {', '.join(months)}")
    else:
        st.success("✅ Không phát hiện tháng nào bất thường trong kỳ Jan–Jun 2024")