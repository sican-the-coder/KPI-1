import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V12", layout="wide")

# CSS를 활용한 간격 강제 축소 (슬라이더 간격 및 컨테이너 패딩 최적화)
st.markdown("""
    <style>
    .stSlider { margin-bottom: -10px; padding-top: 0px; }
    [data-testid="stVerticalBlock"] > div { padding-top: 0.05rem; padding-bottom: 0.05rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    hr { margin: 0.5em 0px; }
    .stMarkdown { line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 프로젝트A 제로섬 시뮬레이터 (V12 - 풀 슬라이더 버전)")

# --- 1. 사이드바 설정 (연간 목표) ---
st.sidebar.header("🎯 연간 고정 목표")
target_year1 = st.sidebar.number_input("Year 1 목표 (원)", value=94446454545, step=100000000)
target_year2 = st.sidebar.number_input("Year 2 목표 (원)", value=223034224116, step=100000000)
target_year3 = st.sidebar.number_input("Year 3 목표 (원)", value=81088419526, step=100000000)

start_year, start_month = 2026, 10 
months = pd.date_range(start=datetime(start_year, start_month, 1), periods=36, freq="MS")

# 세션 상태 초기화 (지표 보존)
if "weights" not in st.session_state:
    st.session_state.weights = [10] * 36
    st.session_state.prates = [5.0] * 36
    st.session_state.arppus = [70000] * 36

# --- 2. 상단 차트 영역 ---
chart_placeholder = st.empty()

# --- 3. [섹션 1] 월별 흐름 가중치 슬라이더 (1~100) ---
st.subheader("📊 1. 월별 흐름 가중치 (Weight)")
st.caption("레퍼런스 기반 트래픽 강도 (12개월씩 3개 행 배치)")
w_cols = st.columns(12) 
for i in range(36):
    col_idx = i % 12
    with w_cols[col_idx]:
        # 월 표시를 더 작게 하여 공간 절약
        st.session_state.weights[i] = st.slider(f"{months[i].strftime('%y.%m')}", 1, 100, st.session_state.weights[i], key=f"w_{i}")

st.markdown("---")

# --- 4. [섹션 2] 월별 지표 세부 조정 (P.rate / ARPPU 슬라이더) ---
st.subheader("⚙️ 2. 월별 지표 세부 조정 (Efficiency)")
st.caption("한 줄에 3개월씩 배치하여 수직 간격을 압축했습니다.")

for row_idx in range(0, 36, 3):
    cols = st.columns(3)
    for i in range(3):
        idx = row_idx + i
        if idx < 36:
            with cols[i]:
                # 월별 카드 스타일 구현
                m_label = months[idx].strftime('%Y년 %m월')
                st.markdown(f"**{m_label}**")
                # P.rate와 ARPPU를 슬라이더로 배치
                st.session_state.prates[idx] = st.slider("P.rate(%)", 0.1, 20.0, st.session_state.prates[idx], 0.1, key=f"pr_s_{idx}")
                st.session_state.arppus[idx] = st.slider("ARPPU(원)", 10000, 300000, st.session_state.arppus[idx], 1000, key=f"ar_s_{idx}")
    st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)

# --- 5. 계산 로직 (기존과 동일) ---
data = []
for i in range(36):
    y = months[i].year
    target = target_year1 if y == start_year else (target_year2 if y == start_year+1 else target_year3)
    days = months[i].days_in_month
    arpdau = st.session_state.arppus[i] * (st.session_state.prates[i] / 100)
    power = st.session_state.weights[i] * arpdau
    data.append({
        "Date": months[i], "Year": y, "Year_Target": target, "Days": days,
        "Weight": st.session_state.weights[i], "ARPDAU": arpdau, "Power": power
    })

df = pd.DataFrame(data)
df["Yearly_Total_Power"] = df.groupby("Year")["Power"].transform("sum")
df["Revenue"] = df["Year_Target"] * (df["Power"] / df["Yearly_Total_Power"])
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])

# --- 6. 차트 업데이트 ---
with chart_placeholder.container():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="매출(원)", yaxis="y1", marker_color="#4C78A8"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="DAU(명)", yaxis="y2", line=dict(color='#E45756', width=2.5)))
    fig.update_layout(
        height=450, margin=dict(t=30, b=20),
        yaxis=dict(title="매출 (원)", titlefont=dict(color="#4C78A8"), tickfont=dict(color="#4C78A8")),
        yaxis2=dict(title="필요 DAU (명)", overlaying="y", side="right", titlefont=dict(color="#E45756"), tickfont=dict(color="#E45756")),
        hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0)
    )
    st.plotly_chart(fig, use_container_width=True)

# 결과 요약 지표
col_a, col_b, col_c = st.columns(3)
col_a.metric("최고 필요 DAU", f"{df['Required_DAU'].max():,.0f}명")
col_b.metric("최저 필요 DAU", f"{df['Required_DAU'].min():,.0f}명")
col_c.metric("평균 ARPDAU", f"{df['ARPDAU'].mean():,.0f}원")
