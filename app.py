import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V5", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & 지표 시뮬레이터 (V5)")

# --- 1. 사이드바: 시작 월 및 연간 목표 설정 ---
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

# --- 2. 데이터 타임라인 생성 및 초기화 ---
end_date = datetime(start_year + 2, 12, 1)
months = pd.date_range(start=start_date, end=end_date, freq="MS")
df = pd.DataFrame({"Date": months})
df["Days"] = df["Date"].dt.days_in_month

def get_initial_revenue(row):
    if row["Date"].year == start_year:
        return target_year1 / (13 - start_month)
    elif row["Date"].year == start_year + 1:
        return target_year2 / 12
    else:
        return target_year3 / 12

df["Revenue"] = df.apply(get_initial_revenue, axis=1)

# --- 3. 월별 지표 세부 조정 (슬라이더 방식) ---
st.markdown("---")
st.subheader("🛠️ 월별 지표 세부 조정")
st.info("각 월별로 결제 비율과 객단가를 좌우로 스크롤하여 조정하세요.")

# 사용자가 조정한 값을 저장할 딕셔너리
monthly_configs = {}

# 월별로 슬라이더 배치 (가독성을 위해 expander 사용)
with st.container():
    for i, row in df.iterrows():
        month_str = row["Date"].strftime('%Y-%m')
        with st.expander(f"📍 {month_str} 지표 설정"):
            col1, col2 = st.columns(2)
            # 요청대로 상단과 동일한 텍스트 '결제 비율', '결제 객단가' 사용
            pr = col1.slider(f"결제 비율 (%) - {month_str}", 0.1, 20.0, 5.0, 0.1, key=f"pr_{i}")
            ar = col2.slider(f"결제 객단가 (원) - {month_str}", 10000, 500000, 70000, 1000, key=f"ar_{i}")
            monthly_configs[i] = {"P.rate(%)": pr, "ARPPU": ar}

# --- 4. 최종 계산 반영 ---
df["P.rate(%)"] = [monthly_configs[i]["P.rate(%)"] for i in range(len(df))]
df["ARPPU"] = [monthly_configs[i]["ARPPU"] for i in range(len(df))]
df["ARPDAU"] = df["ARPPU"] * (df["P.rate(%)"] / 100)
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])
df["Required_PU"] = df["Required_DAU"] * (df["P.rate(%)"] / 100)

# --- 5. 시각화 및 결과 출력 ---
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("누적 목표 매출", f"{(target_year1 + target_year2 + target_year3) / 100000000:,.1f}억")
col2.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
col3.metric("평균 필요 PU", f"{df['Required_PU'].mean():,.0f}명")

fig = go.Figure()
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출 목표", yaxis="y1", opacity=0.7))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU", yaxis="y2", line=dict(color='red', width=3)))
fig.update_layout(
    title="프로젝트A 시뮬레이션 결과 (V5)",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📅 상세 지표 시트")
display_df = df[["Date", "Revenue", "P.rate(%)", "ARPPU", "Required_DAU", "Required_PU"]].copy()
display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')
st.dataframe(display_df.style.format({
    "Revenue": "{:,.0f}",
    "P.rate(%)": "{:.1f}%",
    "ARPPU": "{:,.0f}",
    "Required_DAU": "{:,.0f}",
    "Required_PU": "{:,.0f}"
}), use_container_width=True)

csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(label="📥 시뮬레이션 결과 CSV 다운로드", data=csv, file_name=f"ProjectA_V5_Plan.csv", mime="text/csv")
