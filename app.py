import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V14", layout="wide")

# CSS 최적화
st.markdown("""
    <style>
    .stSlider { margin-bottom: -10px; padding-top: 0px; }
    [data-testid="stVerticalBlock"] > div { padding-top: 0.05rem; padding-bottom: 0.05rem; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    hr { margin: 0.5em 0px; }
    .stDataFrame { margin-top: -10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 프로젝트A 제로섬 시뮬레이터 (V14)")

# --- 1. 사이드바 설정 ---
st.sidebar.header("🎯 연간 고정 목표")
target_year1 = st.sidebar.number_input("Year 1 목표 (원)", value=94446454545, step=100000000)
target_year2 = st.sidebar.number_input("Year 2 목표 (원)", value=223034224116, step=100000000)
target_year3 = st.sidebar.number_input("Year 3 목표 (원)", value=81088419526, step=100000000)

start_year, start_month = 2026, 10 
months = pd.date_range(start=datetime(start_year, start_month, 1), periods=36, freq="MS")

if "weights" not in st.session_state:
    st.session_state.weights = [10] * 36
    st.session_state.prates = [5.0] * 36
    st.session_state.arppus = [70000] * 36

# --- 2. 상단 대시보드 (지표 & 차트) ---
metrics_container = st.container()
chart_container = st.container()
table_container = st.container() # 데이터 시트용 컨테이너 추가

st.markdown("---")

# --- 3. 설정 섹션 (가중치 & 지표 슬라이더) ---
st.subheader("📊 1. 월별 흐름 가중치 (Weight)")
w_cols = st.columns(12) 
for i in range(36):
    col_idx = i % 12
    with w_cols[col_idx]:
        st.session_state.weights[i] = st.slider(f"{months[i].strftime('%y.%m')}", 1, 100, st.session_state.weights[i], key=f"w_{i}")

st.markdown("---")

st.subheader("⚙️ 2. 월별 지표 세부 조정 (P.rate / ARPPU)")
for row_idx in range(0, 36, 3):
    cols = st.columns(3)
    for i in range(3):
        idx = row_idx + i
        if idx < 36:
            with cols[i]:
                m_label = months[idx].strftime('%Y년 %m월')
                st.markdown(f"**{m_label}**")
                st.session_state.prates[idx] = st.slider(f"PR_{idx}", 0.1, 20.0, st.session_state.prates[idx], 0.1, key=f"pr_s_{idx}", label_visibility="collapsed")
                st.session_state.arppus[idx] = st.slider(f"AR_{idx}", 10000, 500000, st.session_state.arppus[idx], 1000, key=f"ar_s_{idx}", label_visibility="collapsed")
                st.caption(f"P.rate: {st.session_state.prates[idx]}% / ARPPU: {st.session_state.arppus[idx]:,.0f}원")

# --- 4. 계산 로직 ---
data = []
for i in range(36):
    y = months[i].year
    target = target_year1 if y == start_year else (target_year2 if y == start_year+1 else target_year3)
    days = months[i].days_in_month
    arpdau = st.session_state.arppus[i] * (st.session_state.prates[i] / 100)
    power = st.session_state.weights[i] * arpdau
    data.append({
        "Date": months[i], "Year": y, "Year_Target": target, "Days": days,
        "Weight": st.session_state.weights[i], "Prate": st.session_state.prates[i], 
        "Arppu": st.session_state.arppus[i], "ARPDAU": arpdau, "Power": power
    })

df = pd.DataFrame(data)
df["Yearly_Total_Power"] = df.groupby("Year")["Power"].transform("sum")
df["Revenue"] = df["Year_Target"] * (df["Power"] / df["Yearly_Total_Power"])
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"].apply(lambda x: max(x, 1)))

# --- 5. 결과 렌더링 (순서: 지표 -> 차트 -> 테이블) ---
with metrics_container:
    m1, m2, m3, m4 = st.columns(4)
    total_target = target_year1 + target_year2 + target_year3
    m1.metric("3개년 고정 목표", f"{total_target / 100000000:,.1f}억")
    m2.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
    m3.metric("평균 P.rate", f"{df['Prate'].mean():.1f}%")
    m4.metric("평균 ARPPU", f"{df['Arppu'].mean():,.0f}원")

with chart_container:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="매출(원)", yaxis="y1", marker_color="#4C78A8"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="DAU(명)", yaxis="y2", line=dict(color='#E45756', width=2.5)))
    fig.update_layout(
        height=400, margin=dict(t=30, b=10, l=50, r=50), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="매출 (원)"),
        yaxis2=dict(title="필요 DAU (명)", side="right", overlaying="y", showgrid=False)
    )
    st.plotly_chart(fig, use_container_width=True)

with table_container:
    st.subheader("📅 상세 데이터 시트")
    display_df = df[["Date", "Revenue", "Weight", "Prate", "Arppu", "ARPDAU", "Required_DAU"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')
    st.dataframe(display_df.style.format({
        "Revenue": "{:,.0f}", "Prate": "{:.1f}%", "Arppu": "{:,.0f}",
        "ARPDAU": "{:,.0f}", "Required_DAU": "{:,.0f}"
    }), use_container_width=True, height=300)

# CSV 다운로드 버튼 (사이드바 하단)
st.sidebar.markdown("---")
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(label="📥 시뮬레이션 결과 CSV 다운로드", data=csv, file_name=f"ProjectA_Plan_V14.csv", mime="text/csv")
