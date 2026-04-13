import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V11", layout="wide")

# CSS를 활용한 간격 강제 축소
st.markdown("""
    <style>
    .stSlider { margin-bottom: -15px; }
    .stNumberInput { margin-bottom: -10px; }
    [data-testid="stVerticalBlock"] > div { padding-top: 0.1rem; padding-bottom: 0.1rem; }
    hr { margin: 0.5em 0px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 프로젝트A 제로섬 시뮬레이터 (V11)")

# --- 1. 사이드바 설정 ---
st.sidebar.header("🎯 연간 고정 목표")
target_year1 = st.sidebar.number_input("Year 1 목표 (원)", value=94446454545, step=100000000)
target_year2 = st.sidebar.number_input("Year 2 목표 (원)", value=223034224116, step=100000000)
target_year3 = st.sidebar.number_input("Year 3 목표 (원)", value=81088419526, step=100000000)

start_year, start_month = 2026, 10 # 기본값 고정 (필요시 변경)
months = pd.date_range(start=datetime(start_year, start_month, 1), periods=36, freq="MS")

# 세션 상태 초기화 (지표 보존)
if "weights" not in st.session_state:
    st.session_state.weights = [10] * 36
    st.session_state.prates = [5.0] * 36
    st.session_state.arppus = [70000] * 36

# --- 2. 상단 차트 영역 ---
chart_placeholder = st.empty()

# --- 3. 월별 흐름 가중치 (슬라이더 영역) ---
st.subheader("📊 1. 월별 흐름 가중치 (1~100)")
st.caption("레퍼런스에 따른 트래픽 강도를 조절하세요. (전체 연도 통합 제로섬 계산)")
w_cols = st.columns(12) # 12개월씩 끊어서 표시
for i in range(36):
    col_idx = i % 12
    with w_cols[col_idx]:
        st.session_state.weights[i] = st.slider(f"{months[i].strftime('%y.%m')}", 1, 100, st.session_state.weights[i], key=f"w_{i}", label_visibility="visible")

st.markdown("---")

# --- 4. 월별 지표 세부 조정 (압축 레이아웃) ---
st.subheader("⚙️ 2. 월별 지표 세부 조정 (P.rate / ARPPU)")
st.caption("간격을 좁게 재설계했습니다.")

# 3개월씩 한 행에 배치하여 수직 길이 단축
for row_idx in range(0, 36, 3):
    cols = st.columns(3)
    for i in range(3):
        idx = row_idx + i
        if idx < 36:
            with cols[i]:
                with st.container():
                    m_label = months[idx].strftime('%Y년 %m월')
                    st.markdown(f"**{m_label}**")
                    c1, c2 = st.columns(2)
                    st.session_state.prates[idx] = c1.number_input("P.rate(%)", 0.1, 20.0, st.session_state.prates[idx], 0.1, key=f"pr_{idx}")
                    st.session_state.arppus[idx] = c2.number_input("ARPPU(원)", 1000, 500000, st.session_state.arppus[idx], 1000, key=f"ar_{idx}")
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# --- 5. 계산 로직 ---
data = []
for i in range(36):
    y = months[i].year
    target = target_year1 if y == start_year else (target_year2 if y == start_year+1 else target_year3)
    days = months[i].days_in_month
    arpdau = st.session_state.arppus[i] * (st.session_state.prates[i] / 100)
    power = st.session_state.weights[i] * arpdau
    data.append({
        "Date": months[i],
        "Year": y,
        "Year_Target": target,
        "Days": days,
        "Weight": st.session_state.weights[i],
        "ARPDAU": arpdau,
        "Power": power
    })

df = pd.DataFrame(data)
df["Yearly_Total_Power"] = df.groupby("Year")["Power"].transform("sum")
df["Revenue"] = df["Year_Target"] * (df["Power"] / df["Yearly_Total_Power"])
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])

# --- 6. 차트 업데이트 ---
with chart_placeholder.container():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="매출(원)", yaxis="y1", marker_color="#4C78A8"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="DAU(명)", yaxis="y2", line=dict(color='#E45756', width=2)))
    fig.update_layout(
        height=400, margin=dict(t=20, b=20),
        yaxis=dict(title="매출"), yaxis2=dict(overlaying="y", side="right", title="DAU"),
        hovermode="x unified", legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)
