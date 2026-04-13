import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V9", layout="wide")

st.title("🚀 프로젝트A 3개년 제로섬(Zero-Sum) 시뮬레이터")
st.markdown("특정 월의 효율(P.rate, ARPPU)을 높이면 해당 월의 매출 비중이 커지고, **동일 연도 내 나머지 월의 목표 매출과 트래픽 부담은 자동으로 감소**합니다. (연간 목표 매출 절대 고정)")

# --- 1. 사이드바: 시작 설정 및 연간 목표 ---
st.sidebar.header("📅 시작 월 설정")
start_year = st.sidebar.selectbox("시작 연도", [2025, 2026, 2027], index=1)
start_month = st.sidebar.selectbox("시작 월", list(range(1, 13)), index=9)
start_date = datetime(start_year, start_month, 1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 연간 목표 매출 (고정)")
target_year1 = st.sidebar.number_input("Year 1 Total 목표 (원)", min_value=0, value=94446454545, step=100000000, format="%d")
target_year2 = st.sidebar.number_input("Year 2 Total 목표 (원)", min_value=0, value=223034224116, step=100000000, format="%d")
target_year3 = st.sidebar.number_input("Year 3 Total 목표 (원)", min_value=0, value=81088419526, step=100000000, format="%d")

# --- 2. 데이터 타임라인 세팅 ---
end_date = datetime(start_year + 2, 12, 1)
months = pd.date_range(start=start_date, end=end_date, freq="MS")
df = pd.DataFrame({"Date": months})
df["Year"] = df["Date"].dt.year
df["Days"] = df["Date"].dt.days_in_month

# 각 행에 연간 타겟 금액 매핑
def get_year_target(row):
    if row["Year"] == start_year: return target_year1
    elif row["Year"] == start_year + 1: return target_year2
    else: return target_year3
df["Year_Target"] = df.apply(get_year_target, axis=1)

# 계절성 가중치 (방치형 곡선 베이스)
def get_base_weight(row):
    m = row["Date"].month
    y = row["Date"].year
    if y == start_year:
        # 첫 해는 런칭 초기에 가중치 (예: 10월 시작 시 3, 2, 1 비율)
        return max(13 - m, 1)
    elif y == start_year + 1:
        return [0.08, 0.09, 0.08, 0.08, 0.10, 0.08, 0.09, 0.08, 0.08, 0.08, 0.08, 0.08][m-1]
    else:
        return [0.09, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.09, 0.09, 0.10][m-1]
df["Base_Weight"] = df.apply(get_base_weight, axis=1)

# --- 3. UI 렌더링 순서 세팅 ---
chart_placeholder = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

st.markdown("---")

# --- 4. 화면 최하단: 월별 지표 세부 조정 (펼침 구조) ---
st.subheader("🛠️ 월별 지표 세부 조정")
st.info("💡 팁: 특정 월의 지표를 올리면 해당 월의 매출이 솟고, 같은 연도의 다른 월 매출은 줄어듭니다.")

monthly_configs = {}
for i, row in df.iterrows():
    m_str = row["Date"].strftime('%Y-%m')
    st.markdown(f"#### 📍 {m_str}")
    c1, c2 = st.columns(2)
    pr = c1.slider(f"P.rate (%)", 0.1, 20.0, 5.0, 0.1, key=f"v9_pr_{i}")
    ar = c2.slider(f"ARPPU (원)", 10000, 500000, 70000, 1000, key=f"v9_ar_{i}")
    monthly_configs[i] = {"P.rate": pr, "ARPPU": ar}
    st.markdown("---")

# --- 5. 핵심 로직: 제로섬(Zero-Sum) 파이 나누기 ---
df["P.rate(%)"] = [monthly_configs[i]["P.rate"] for i in range(len(df))]
df["ARPPU"] = [monthly_configs[i]["ARPPU"] for i in range(len(df))]
df["ARPDAU"] = df["ARPPU"] * (df["P.rate(%)"] / 100)

# (1) 각 월의 '상대적 수익 창출력(Power)' 계산
df["Power_Score"] = df["Base_Weight"] * df["ARPDAU"]

# (2) 동일 연도 내의 Power 총합 계산
df["Yearly_Total_Power"] = df.groupby("Year")["Power_Score"].transform("sum")

# (3) [연간 목표 매출]을 [해당 월의 Power 비중]만큼 쪼개서 가져감
df["Revenue"] = df["Year_Target"] * (df["Power_Score"] / df["Yearly_Total_Power"])

# (4) 확정된 매출을 바탕으로 필요 DAU 및 PU 역산
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])
df["Required_PU"] = df["Required_DAU"] * (df["P.rate(%)"] / 100)

# --- 6. 상단 렌더링 채우기 ---
with metrics_placeholder.container():
    m1, m2, m3, m4 = st.columns(4)
    # 연간 목표의 총합 (유저 조작에도 절대 변하지 않음 검증)
    fixed_total = target_year1 + target_year2 + target_year3
    m1.metric("3개년 고정 목표 매출", f"{fixed_total / 100000000:,.1f}억")
    m2.metric("평균 P.rate", f"{df['P.rate(%)'].mean():.1f}%")
    m3.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")
    m4.metric("평균 필요 PU", f"{df['Required_PU'].mean():,.0f}명")

with chart_placeholder.container():
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 할당 매출 (원)", yaxis="y1", marker_color="#4C78A8"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU (명)", yaxis="y2", line=dict(color='#E45756', width=3)))
    fig.update_layout(
        title="제로섬 기반 월별 매출 및 DAU 시뮬레이션",
        yaxis=dict(title="매출 (원)"),
        yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h"),
        hovermode="x unified",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

with table_placeholder.container():
    st.subheader("📅 상세 지표 시트")
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

st.sidebar.markdown("---")
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(label="📥 시뮬레이션 결과 CSV 다운로드", data=csv, file_name=f"ProjectA_ZeroSum_Plan.csv", mime="text/csv")
