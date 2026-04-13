import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V3", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & 지표 시뮬레이터 (V3)")
st.markdown("목표 매출(Top-down)을 기준으로 결제 비율(P.rate)과 객단가(ARPPU)를 조절하여 필요 트래픽(DAU, PU)을 유기적으로 역산합니다.")

# --- 1. 사이드바: 탑다운 목표 금액 입력 ---
st.sidebar.header("🎯 연간 목표 매출 입력")
target_year1 = st.sidebar.number_input("Year 1 (2026) Total 목표 (원)", min_value=0, value=94446454545, step=100000000, format="%d")
target_year2 = st.sidebar.number_input("Year 2 (2027) Total 목표 (원)", min_value=0, value=223034224116, step=100000000, format="%d")
target_year3 = st.sidebar.number_input("Year 3 (2028) Total 목표 (원)", min_value=0, value=81088419526, step=100000000, format="%d")

st.sidebar.caption(f"↳ Y1: {target_year1 / 100000000:,.1f}억 / Y2: {target_year2 / 100000000:,.1f}억 / Y3: {target_year3 / 100000000:,.1f}억")
st.sidebar.markdown("---")

# --- 2. 시뮬레이션 파라미터 (P.rate & ARPPU) ---
st.sidebar.header("⚙️ 핵심 지표 연동 설정")
st.sidebar.markdown("아래 지표를 변경하면 DAU와 PU가 즉시 재계산됩니다.")

# P.rate와 ARPPU를 기본값으로 설정 (5% * 70,000 = ARPDAU 3,500)
base_prate = st.sidebar.slider("결제 비율 (P.rate %)", min_value=1.0, max_value=20.0, value=5.0, step=0.1)
base_arppu = st.sidebar.slider("결제 객단가 (ARPPU, 원)", min_value=10000, max_value=300000, value=70000, step=1000)

# 내부적으로 ARPDAU 계산
calculated_arpdau = base_arppu * (base_prate / 100)
st.sidebar.info(f"💡 **현재 환산 ARPDAU:** {calculated_arpdau:,.0f}원")

# --- 3. 데이터 및 가중치 계산 로직 ---
months = pd.date_range(start="2026-10-01", end="2028-12-01", freq="MS")
df = pd.DataFrame({"Date": months})
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Days"] = df["Date"].dt.days_in_month

weights_2026 = [0.5, 0.3, 0.2] 
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

# --- 4. 지표 연산 (DAU, PU 역산) ---
df["P.rate(%)"] = base_prate
df["ARPPU"] = base_arppu
df["ARPDAU"] = calculated_arpdau

# 1) 매출을 채우기 위해 매일 들어와야 하는 전체 유저 (DAU)
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])
# 2) 그 DAU 중에서 결제 비율만큼 결제하는 실제 유저 (PU)
df["Required_PU"] = df["Required_DAU"] * (df["P.rate(%)"] / 100)

# --- 5. 시각화 대시보드 ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("3개년 누적 목표", f"{(target_year1 + target_year2 + target_year3) / 100000000:,.0f}억")
col2.metric("환산 ARPDAU", f"{calculated_arpdau:,.0f}원")
col3.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
col4.metric("평균 필요 PU (결제자)", f"{df['Required_PU'].mean():,.0f}명")

fig = go.Figure()
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출 (원)", yaxis="y1", opacity=0.8))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="전체 유저 (DAU)", yaxis="y2", line=dict(color='red', width=3)))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_PU"], name="결제 유저 (PU)", yaxis="y2", line=dict(color='blue', width=2, dash='dot')))

fig.update_layout(
    title="프로젝트A 월간 매출 및 지표 (DAU & PU) 추이",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="유저 수 (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. 상세 데이터 시트 ---
st.subheader("📅 상세 지표 시트 (Revenue, DAU, PU, P.rate, ARPPU)")
display_df = df[["Date", "Revenue", "P.rate(%)", "ARPPU", "ARPDAU", "Required_DAU", "Required_PU"]].copy()
display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')

st.dataframe(display_df.style.format({
    "Revenue": "{:,.0f}",
    "P.rate(%)": "{:.1f}%",
    "ARPPU": "{:,.0f}",
    "ARPDAU": "{:,.0f}",
    "Required_DAU": "{:,.0f}",
    "Required_PU": "{:,.0f}"
}), use_container_width=True)

csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 V3 시뮬레이션 결과 다운로드 (CSV)",
    data=csv,
    file_name=f"ProjectA_V3_Metrics_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
