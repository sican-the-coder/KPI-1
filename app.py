import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="프로젝트A 시뮬레이터", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & DAU 시뮬레이터")
st.markdown("2026년 10월부터 2028년 12월까지의 목표 매출을 기반으로 월별 필요 지표를 역산합니다.")

# --- 1. 사이드바: 고정 목표 설정 ---
st.sidebar.header("📌 연간 목표 매출 (프로젝트A)")
target_2026_q4 = 94_446_454_545
target_2027 = 223_034_224_116
target_2028 = 81_088_419_526

st.sidebar.write(f"**2026 Q4:** {target_2026_q4:,.0f}원")
st.sidebar.write(f"**2027 Total:** {target_2027:,.0f}원")
st.sidebar.write(f"**2028 Total:** {target_2028:,.0f}원")

# --- 2. 시뮬레이션 파라미터 ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 시뮬레이션 설정")
base_arpdau = st.sidebar.slider("기본 ARPDAU 설정 (원)", 1000, 10000, 3500, step=100)

# 월별 데이터 생성 로직
months = pd.date_range(start="2026-10-01", end="2028-12-01", freq="MS")
df = pd.DataFrame({"Date": months})
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Days"] = df["Date"].dt.days_in_month

# 월별 매출 비중 가중치 (프로젝트 라이프사이클 반영)
weights_2026 = [0.5, 0.3, 0.2]
weights_2027 = [0.08, 0.09, 0.08, 0.08, 0.10, 0.08, 0.09, 0.08, 0.08, 0.08, 0.08, 0.08]
weights_2028 = [0.09, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.09, 0.09, 0.10]

def calculate_revenue(row):
    if row["Year"] == 2026:
        return target_2026_q4 * weights_2026[row["Month"]-10]
    elif row["Year"] == 2027:
        return target_2027 * weights_2027[row["Month"]-1]
    else:
        return target_2028 * weights_2028[row["Month"]-1]

df["Revenue"] = df.apply(calculate_revenue, axis=1)

# --- 3. 월별 ARPDAU 개별 조정 ---
with st.expander("📊 월별 ARPDAU 세부 조정"):
    st.write("각 월의 ARPDAU를 직접 조정할 수 있습니다.")
    arpdau_list = []
    cols = st.columns(4)
    for i, date in enumerate(df["Date"]):
        with cols[i % 4]:
            val = st.number_input(f"{date.strftime('%Y-%m')}", value=base_arpdau, step=100, key=f"arp_{i}")
            arpdau_list.append(val)
    df["ARPDAU"] = arpdau_list

# DAU 역산
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])

# --- 4. 시각화 ---
col1, col2, col3 = st.columns(3)
col1.metric("전체 목표 매출", f"{ (target_2026_q4+target_2027+target_2028)/100000000:,.1f}억")
col2.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
col3.metric("최고 매출 월", f"{df.loc[df['Revenue'].idxmax(), 'Date'].strftime('%Y-%m')}")

fig = go.Figure()
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출", yaxis="y1"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU", yaxis="y2", line=dict(color='red', width=3)))

fig.update_layout(
    title="프로젝트A 3개년 매출 및 필요 DAU 추이",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- 5. 데이터 테이블 및 다운로드 ---
st.subheader("📅 상세 시뮬레이션 데이터 (프로젝트A)")
display_df = df[["Date", "Revenue", "ARPDAU", "Required_DAU"]].copy()
display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')
st.dataframe(display_df.style.format({
    "Revenue": "{:,.0f}",
    "ARPDAU": "{:,.0f}",
    "Required_DAU": "{:,.0f}"
}), use_container_width=True)

# CSV 다운로드 버튼
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 프로젝트A 시뮬레이션 결과 CSV 다운로드",
    data=csv,
    file_name=f"ProjectA_Simulation_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
