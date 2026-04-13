import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V8", layout="wide")

st.title("🚀 프로젝트A 3개년 지표 & 수익 시뮬레이터 (V8)")
st.markdown("목표 트래픽(Baseline DAU) 하에서 효율 지표(P.rate, ARPPU) 변화에 따른 **예상 매출 변동**을 시뮬레이션합니다.")

# --- 1. 사이드바: 시작 설정 및 연간 목표 ---
st.sidebar.header("📅 시작 월 설정")
start_year = st.sidebar.selectbox("시작 연도", [2025, 2026, 2027], index=1)
start_month = st.sidebar.selectbox("시작 월", list(range(1, 13)), index=9)
start_date = datetime(start_year, start_month, 1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 연간 목표 매출 입력")
# 요청대로 (2026) 텍스트 제거
target_year1 = st.sidebar.number_input("Year 1 Total 목표 (원)", min_value=0, value=94446454545, step=100000000, format="%d")
target_year2 = st.sidebar.number_input("Year 2 Total 목표 (원)", min_value=0, value=223034224116, step=100000000, format="%d")
target_year3 = st.sidebar.number_input("Year 3 Total 목표 (원)", min_value=0, value=81088419526, step=100000000, format="%d")

# --- 2. 데이터 타임라인 및 Baseline DAU 산출 ---
end_date = datetime(start_year + 2, 12, 1)
months = pd.date_range(start=start_date, end=end_date, freq="MS")
df = pd.DataFrame({"Date": months})
df["Days"] = df["Date"].dt.days_in_month

# 초기 기준 지표 (Baseline 설정용)
DEFAULT_PRATE = 5.0
DEFAULT_ARPPU = 70000
DEFAULT_ARPDAU = DEFAULT_ARPPU * (DEFAULT_PRATE / 100)

def calculate_baseline_dau(row):
    curr_year = row["Date"].year
    if curr_year == start_year:
        monthly_target = target_year1 / (13 - start_month)
    elif curr_year == start_year + 1:
        monthly_target = target_year2 / 12
    else:
        monthly_target = target_year3 / 12
    # 목표 매출을 달성하기 위한 고정 트래픽 기준점 산출
    return monthly_target / (row["Days"] * DEFAULT_ARPDAU)

df["Baseline_DAU"] = df.apply(calculate_baseline_dau, axis=1)

# --- 3. UI 렌더링 순서 세팅 ---
chart_placeholder = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

st.markdown("---")

# --- 4. 화면 최하단: 월별 지표 세부 조정 (펼침 구조) ---
st.subheader("🛠️ 월별 지표 세부 조정")
st.info("P.rate(%)와 ARPPU를 조정하면 해당 월의 '예상 매출'이 즉시 재계산됩니다.")

monthly_configs = {}
for i, row in df.iterrows():
    m_str = row["Date"].strftime('%Y-%m')
    st.markdown(f"#### 📍 {m_str}")
    c1, c2 = st.columns(2)
    # 요청대로 명칭 변경: P.rate(%), ARPPU
    pr = c1.slider(f"P.rate (%) - {m_str}", 0.1, 20.0, DEFAULT_PRATE, 0.1, key=f"v8_pr_{i}")
    ar = c2.slider(f"ARPPU - {m_str}", 10000, 500000, DEFAULT_ARPPU, 1000, key=f"v8_ar_{i}")
    monthly_configs[i] = {"P.rate": pr, "ARPPU": ar}
    st.markdown("---")

# --- 5. 최종 계산 로직 (Bottom-Up Revenue) ---
df["P.rate(%)"] = [monthly_configs[i]["P.rate"] for i in range(len(df))]
df["ARPPU"] = [monthly_configs[i]["ARPPU"] for i in range(len(df))]
df["ARPDAU"] = df["ARPPU"] * (df["P.rate(%)"] / 100) # ARPDAU 복구

# 수정된 공식: 고정된 DAU 하에서 효율 변화에 따른 '예상 매출' 산출
df["Adjusted_Revenue"] = df["Baseline_DAU"] * df["Days"] * df["ARPDAU"]
df["Required_PU"] = df["Baseline_DAU"] * (df["P.rate(%)"] / 100)

# --- 6. 상단 렌더링 채우기 ---
with metrics_placeholder.container():
    m1, m2, m3, m4 = st.columns(4)
    total_revenue = df["Adjusted_Revenue"].sum()
    m1.metric("시뮬레이션 누적 매출", f"{total_revenue / 100000000:,.1f}억")
    m2.metric("평균 ARPDAU", f"{df['ARPDAU'].mean():,.0f}원")
    m3.metric("고정 Baseline DAU", f"{df['Baseline_DAU'].mean():,.0f}명")
    m4.metric("평균 예상 PU", f"{df['Required_PU'].mean():,.0f}명")

with chart_placeholder.container():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Adjusted_Revenue"], name="예상 매출 (원)", yaxis="y1", opacity=0.7))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Baseline_DAU"], name="기준 트래픽 (DAU)", yaxis="y2", line=dict(color='red', width=3)))
    fig.update_layout(
        title="효율 변화에 따른 예상 매출 변동 추이",
        yaxis=dict(title="매출 (원)"),
        yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        hovermode="x unified",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

with table_placeholder.container():
    st.subheader("📅 상세 지표 시트")
    display_df = df[["Date", "Adjusted_Revenue", "P.rate(%)", "ARPPU", "ARPDAU", "Baseline_DAU", "Required_PU"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')
    st.dataframe(display_df.style.format({
        "Adjusted_Revenue": "{:,.0f}",
        "P.rate(%)": "{:.1f}%",
        "ARPPU": "{:,.0f}",
        "ARPDAU": "{:,.0f}",
        "Baseline_DAU": "{:,.0f}",
        "Required_PU": "{:,.0f}"
    }), use_container_width=True)

st.sidebar.markdown("---")
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(label="📥 시뮬레이션 결과 CSV 다운로드", data=csv, file_name=f"ProjectA_V8_BottomUp.csv", mime="text/csv")
