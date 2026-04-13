import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V6", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & 지표 시뮬레이터 (V6)")

# --- 1. 사이드바: 시작 설정 및 연간 목표 ---
st.sidebar.header("📅 시작 월 설정")
start_year = st.sidebar.selectbox("시작 연도", [2025, 2026, 2027], index=1)
start_month = st.sidebar.selectbox("시작 월", list(range(1, 13)), index=9)
start_date = datetime(start_year, start_month, 1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 연간 목표 매출 입력")
target_year1 = st.sidebar.number_input("Year 1 Total 목표 (원)", min_value=0, value=94446454545, step=100000000, format="%d")
target_year2 = st.sidebar.number_input("Year 2 Total 목표 (원)", min_value=0, value=223034224116, step=100000000, format="%d")
target_year3 = st.sidebar.number_input("Year 3 Total 목표 (원)", min_value=0, value=81088419526, step=100000000, format="%d")

# --- 2. 데이터 타임라인 및 기초 매출 계산 ---
end_date = datetime(start_year + 2, 12, 1)
months = pd.date_range(start=start_date, end=end_date, freq="MS")
df = pd.DataFrame({"Date": months})
df["Days"] = df["Date"].dt.days_in_month

def get_monthly_revenue(row):
    curr_year = row["Date"].year
    if curr_year == start_year:
        return target_year1 / (13 - start_month)
    elif curr_year == start_year + 1:
        return target_year2 / 12
    else:
        return target_year3 / 12

df["Revenue"] = df.apply(get_monthly_revenue, axis=1)

# --- 3. UI 순서 정의 (지표 조정 섹션은 맨 아래로) ---

# (A) 결과 대시보드 먼저 렌더링을 위해 변수 선언 영역
chart_placeholder = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

st.markdown("---")

# (B) 화면 최하단: 월별 지표 세부 조정 (펼침 구조)
st.subheader("🛠️ 월별 지표 세부 조정")
st.info("각 월별로 결제 비율과 객단가를 조정하세요. 모든 수치는 상단 차트에 실시간 반영됩니다.")

monthly_configs = {}
# 모든 달을 루프로 돌며 슬라이더 배치 (에코디언 없이 평면 구조)
for i, row in df.iterrows():
    m_str = row["Date"].strftime('%Y-%m')
    st.markdown(f"#### 📍 {m_str}")
    c1, c2 = st.columns(2)
    # 텍스트 통일: 결제 비율 (%), 결제 객단가 (원)
    pr = c1.slider(f"결제 비율 (%)", 0.1, 20.0, 5.0, 0.1, key=f"v6_pr_{i}")
    ar = c2.slider(f"결제 객단가 (원)", 10000, 500000, 70000, 1000, key=f"v6_ar_{i}")
    monthly_configs[i] = {"P.rate": pr, "ARPPU": ar}
    st.markdown("---")

# --- 4. 최종 계산 로직 ---
df["P.rate(%)"] = [monthly_configs[i]["P.rate"] for i in range(len(df))]
df["ARPPU"] = [monthly_configs[i]["ARPPU"] for i in range(len(df))]
df["ARPDAU"] = df["ARPPU"] * (df["P.rate(%)"] / 100)
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])
df["Required_PU"] = df["Required_DAU"] * (df["P.rate(%)"] / 100)

# --- 5. 상단 렌더링 (Placeholder 채우기) ---

# 핵심 지표 카드
with metrics_placeholder.container():
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("누적 목표 매출", f"{(target_year1 + target_year2 + target_year3) / 100000000:,.1f}억")
    m2.metric("평균 결제 비율", f"{df['P.rate(%)'].mean():.1f}%")
    m3.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
    m4.metric("평균 필요 PU", f"{df['Required_PU'].mean():,.0f}명")

# 메인 그래프
with chart_placeholder.container():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출 목표 (원)", yaxis="y1", opacity=0.7))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU (명)", yaxis="y2", line=dict(color='red', width=3)))
    fig.update_layout(
        title="프로젝트A 시뮬레이션 결과 추이",
        yaxis=dict(title="매출 (원)"),
        yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        hovermode="x unified",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

# 상세 표
with table_placeholder.container():
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

# 다운로드 버튼
st.sidebar.markdown("---")
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(label="📥 결과 CSV 다운로드", data=csv, file_name=f"ProjectA_V6_Plan.csv", mime="text/csv")
