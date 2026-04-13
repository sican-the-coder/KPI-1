import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & DAU 시뮬레이터 (Yearly)")
st.markdown("연도별 목표 매출(Total)을 입력하면 월별 가중치에 따라 필요 지표가 자동으로 역산됩니다.")

# --- 1. 사이드바: 탑다운 목표 금액 입력 (Year 1, 2, 3) ---
st.sidebar.header("🎯 연간 목표 매출 입력 (탑다운)")
st.sidebar.markdown("각 연도별 Total 목표를 입력하세요.")

# Year 1 (2026) - 10~12월분
target_year1 = st.sidebar.number_input(
    "Year 1 (2026) Total 목표 (원)", 
    min_value=0, 
    value=94446454545, 
    step=100000000, 
    format="%d"
)

# Year 2 (2027) - 1~12월분
target_year2 = st.sidebar.number_input(
    "Year 2 (2027) Total 목표 (원)", 
    min_value=0, 
    value=223034224116, 
    step=100000000,
    format="%d"
)

# Year 3 (2028) - 1~12월분
target_year3 = st.sidebar.number_input(
    "Year 3 (2028) Total 목표 (원)", 
    min_value=0, 
    value=81088419526, 
    step=100000000,
    format="%d"
)

st.sidebar.markdown("---")
st.sidebar.caption(f"💡 **Year 1 (2026):** {target_year1 / 100000000:,.1f}억 원")
st.sidebar.caption(f"💡 **Year 2 (2027):** {target_year2 / 100000000:,.1f}억 원")
st.sidebar.caption(f"💡 **Year 3 (2028):** {target_year3 / 100000000:,.1f}억 원")

# --- 2. 시뮬레이션 파라미터 설정 ---
st.sidebar.header("⚙️ 지표 설정")
base_arpdau = st.sidebar.slider("기본 ARPDAU 설정 (원)", 1000, 10000, 3500, step=100)

# --- 3. 데이터 및 가중치 계산 로직 ---
months = pd.date_range(start="2026-10-01", end="2028-12-01", freq="MS")
df = pd.DataFrame({"Date": months})
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Days"] = df["Date"].dt.days_in_month

# 연도별/월별 매출 비중 가중치
weights_2026 = [0.5, 0.3, 0.2] # 10, 11, 12월
weights_2027 = [0.08, 0.09, 0.08, 0.08, 0.10, 0.08, 0.09, 0.08, 0.08, 0.08, 0.08, 0.08]
weights_2028 = [0.09, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.09, 0.09, 0.10]

def calculate_revenue(row):
    if row["Year"] == 2026:
        return target_year1 * weights_2026[row["Month"]-10]
    elif row["Year"] == 2027:
        return target_year2 * weights_2027[row["Month"]-1]
    else:
        return target_year3 * weights_2028[row["Month"]-1]

df["Revenue"] = df.apply(calculate_revenue, axis=1)

# --- 4. 개별 월 ARPDAU 조정 ---
with st.expander("📊 월별 ARPDAU 세부 조정 (필요 시)"):
    arpdau_list = []
    cols = st.columns(4)
    for i, date in enumerate(df["Date"]):
        with cols[i % 4]:
            val = st.number_input(f"{date.strftime('%Y-%m')}", value=base_arpdau, step=100, key=f"arp_{i}")
            arpdau_list.append(val)
    df["ARPDAU"] = arpdau_list

# DAU 역산
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])

# --- 5. 시각화 및 대시보드 ---
col1, col2, col3 = st.columns(3)
total_sum = target_year1 + target_year2 + target_year3
col1.metric("3개년 누적 목표", f"{total_sum / 100000000:,.1f}억 원")
col2.metric("전체 평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
col3.metric("최고 매출 달성월", f"{df.loc[df['Revenue'].idxmax(), 'Date'].strftime('%Y-%m')}")

fig = go.Figure()
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 목표 매출 (원)", yaxis="y1"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU (명)", yaxis="y2", line=dict(color='red', width=3)))

fig.update_layout(
    title="프로젝트A 3개년 시뮬레이션 결과",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. 데이터 시트 및 CSV 출력 ---
st.subheader("📅 상세 지표 시트")
display_df = df[["Date", "Revenue", "ARPDAU", "Required_DAU"]].copy()
display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')

st.dataframe(display_df.style.format({
    "Revenue": "{:,.0f}",
    "ARPDAU": "{:,.0f}",
    "Required_DAU": "{:,.0f}"
}), use_container_width=True)

csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 프로젝트A 시뮬레이션 결과 다운로드 (CSV)",
    data=csv,
    file_name=f"ProjectA_3Year_Plan_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
