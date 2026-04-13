import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & DAU 시뮬레이터")
st.markdown("상단에 연간 목표 매출을 입력하면, 월별 가중치에 따라 필요 지표(DAU)가 역산됩니다.")

# --- 1. 사이드바: 탑다운 목표 금액 입력 ---
st.sidebar.header("🎯 연간 목표 매출 입력 (탑다운)")
st.sidebar.markdown("목표 금액을 수정하면 하위 지표가 자동 재계산됩니다.")

# 1억 단위로 조작 가능한 입력창 (value=초기값)
target_2026_q4 = st.sidebar.number_input(
    "2026 Q4 목표 (원)", 
    min_value=0, 
    value=94446454545, 
    step=100000000, 
    format="%d"
)
target_2027 = st.sidebar.number_input(
    "2027 Total 목표 (원)", 
    min_value=0, 
    value=223034224116, 
    step=100000000,
    format="%d"
)
target_2028 = st.sidebar.number_input(
    "2028 Total 목표 (원)", 
    min_value=0, 
    value=81088419526, 
    step=100000000,
    format="%d"
)

st.sidebar.caption(f"↳ 26년 Q4: {target_2026_q4 / 100000000:,.1f}억 원")
st.sidebar.caption(f"↳ 27년: {target_2027 / 100000000:,.1f}억 원")
st.sidebar.caption(f"↳ 28년: {target_2028 / 100000000:,.1f}억 원")

# --- 2. 시뮬레이션 파라미터 (ARPDAU) ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 시뮬레이션 설정")
base_arpdau = st.sidebar.slider("기본 ARPDAU 설정 (원)", 1000, 10000, 3500, step=100)

# --- 3. 월별 데이터 및 가중치 생성 ---
months = pd.date_range(start="2026-10-01", end="2028-12-01", freq="MS")
df = pd.DataFrame({"Date": months})
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Days"] = df["Date"].dt.days_in_month

# 프로젝트 라이프사이클 반영 월별 매출 비중 가중치
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

# 탑다운 입력값 * 가중치 = 월간 매출 할당
df["Revenue"] = df.apply(calculate_revenue, axis=1)

# --- 4. 월별 ARPDAU 개별 조정 ---
with st.expander("📊 월별 ARPDAU 세부 조정"):
    st.write("각 월의 ARPDAU를 직접 조정할 수 있습니다. (기본값은 좌측 슬라이더 설정값)")
    arpdau_list = []
    cols = st.columns(4)
    for i, date in enumerate(df["Date"]):
        with cols[i % 4]:
            val = st.number_input(f"{date.strftime('%Y-%m')}", value=base_arpdau, step=100, key=f"arp_{i}")
            arpdau_list.append(val)
    df["ARPDAU"] = arpdau_list

# DAU 역산 (월간 매출 / (일수 * ARPDAU))
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])

# --- 5. 시각화 (그래프 및 핵심 지표) ---
col1, col2, col3 = st.columns(3)
total_target = target_2026_q4 + target_2027 + target_2028
col1.metric("3개년 목표 총 매출", f"{total_target / 100000000:,.1f}억 원")
col2.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
col3.metric("최고 매출 발생 월", f"{df.loc[df['Revenue'].idxmax(), 'Date'].strftime('%Y-%m')}")

fig = go.Figure()
# 바 차트: 월 매출
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출 (원)", yaxis="y1"))
# 라인 차트: 필요 DAU
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU (명)", yaxis="y2", line=dict(color='red', width=3)))

fig.update_layout(
    title="프로젝트A 3개년 매출 및 필요 DAU 추이",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. 데이터 테이블 및 다운로드 ---
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
