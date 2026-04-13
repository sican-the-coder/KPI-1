import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="프로젝트A 시뮬레이터 V4", layout="wide")

st.title("🚀 프로젝트A 3개년 매출 & 지표 시뮬레이터 (V4)")

# --- 1. 사이드바: 시작 월 및 연간 목표 설정 ---
st.sidebar.header("📅 시작 월 설정")
start_year = st.sidebar.selectbox("시작 연도", [2025, 2026, 2027], index=1)
start_month = st.sidebar.selectbox("시작 월", list(range(1, 13)), index=9) # 기본값 10월
start_date = datetime(start_year, start_month, 1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 연간 목표 매출 입력")

target_year1 = st.sidebar.number_input("Year 1 Total 목표 (원)", min_value=0, value=94446454545, step=100000000, format="%d")
target_year2 = st.sidebar.number_input("Year 2 Total 목표 (원)", min_value=0, value=223034224116, step=100000000, format="%d")
target_year3 = st.sidebar.number_input("Year 3 Total 목표 (원)", min_value=0, value=81088419526, step=100000000, format="%d")

# --- 2. 데이터 타임라인 및 기초 매출 배분 생성 ---
# 시작 월부터 3개년차 12월까지 (예: 26년 10월 시작 시 28년 12월까지)
end_year = start_year + 2
end_date = datetime(end_year, 12, 1)

months = pd.date_range(start=start_date, end=end_date, freq="MS")
df = pd.DataFrame({"Date": months})
df["Year_Label"] = df["Date"].apply(lambda x: f"Year 1" if x.year == start_year else (f"Year 2" if x.year == start_year + 1 else "Year 3"))
df["Days"] = df["Date"].dt.days_in_month

# 가중치 계산 함수 (연도별로 n분의 1을 기본으로 하되, Year 1은 시작 월에 맞춰 배분)
def get_monthly_revenue(row):
    year_idx = row["Date"].year
    if year_idx == start_year:
        # Year 1의 남은 개월 수 확인
        remaining_months = 13 - start_month
        return target_year1 / remaining_months
    elif year_idx == start_year + 1:
        return target_year2 / 12
    else:
        return target_year3 / 12

df["Revenue"] = df.apply(get_monthly_revenue, axis=1)

# --- 3. 상세 지표 수정 섹션 (P.rate, ARPPU) ---
# 세션 상태를 사용하여 사용자가 수정한 값을 유지
if 'editor_df' not in st.session_state:
    st.session_state.editor_df = pd.DataFrame({
        "Month": df["Date"].dt.strftime('%Y-%m'),
        "P.rate(%)": [5.0] * len(df),
        "ARPPU": [70000] * len(df)
    })

# --- 메인 화면 레이아웃 ---
# (상단) 그래프 섹션
chart_placeholder = st.empty()

# (중단) 상세 지표 시트
st.subheader("📅 상세 지표 시트")
table_placeholder = st.empty()

st.markdown("---")

# (하단) 월별 지표 세부 조정 섹션
st.subheader("🛠️ 월별 지표 세부 조정")
st.info("아래 표의 P.rate(%)와 ARPPU 칸을 더블 클릭해서 수정하세요. 수정 즉시 상단 그래프와 지표가 반영됩니다.")

# 데이터 에디터 배치
edited_df = st.data_editor(
    st.session_state.editor_df,
    column_config={
        "Month": st.column_config.TextColumn("연월", disabled=True),
        "P.rate(%)": st.column_config.NumberColumn("결제 비율 (%)", min_value=0.1, max_value=100.0, step=0.1, format="%.1f%%"),
        "ARPPU": st.column_config.NumberColumn("결제 객단가 (원)", min_value=1000, step=1000, format="%d")
    },
    hide_index=True,
    use_container_width=True,
    key="metrics_editor"
)

# --- 4. 최종 계산 및 시각화 업데이트 ---
# 수정한 값 반영
df["P.rate(%)"] = edited_df["P.rate(%)"]
df["ARPPU"] = edited_df["ARPPU"]
df["ARPDAU"] = df["ARPPU"] * (df["P.rate(%)"] / 100)
df["Required_DAU"] = df["Revenue"] / (df["Days"] * df["ARPDAU"])
df["Required_PU"] = df["Required_DAU"] * (df["P.rate(%)"] / 100)

# 핵심 지표 카드
col1, col2, col3, col4 = st.columns(4)
col1.metric("누적 목표 매출", f"{(target_year1 + target_year2 + target_year3) / 100000000:,.1f}억")
col2.metric("평균 P.rate", f"{df['P.rate(%)'].mean():.1f}%")
col3.metric("평균 ARPPU", f"{df['ARPPU'].mean():,.0f}원")
col4.metric("평균 필요 DAU", f"{df['Required_DAU'].mean():,.0f}명")

# 그래프 업데이트
fig = go.Figure()
fig.add_trace(go.Bar(x=df["Date"], y=df["Revenue"], name="월 매출 목표", yaxis="y1", opacity=0.7))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Required_DAU"], name="필요 DAU", yaxis="y2", line=dict(color='red', width=3)))
fig.update_layout(
    title="프로젝트A 시뮬레이션 결과",
    yaxis=dict(title="매출 (원)"),
    yaxis2=dict(title="DAU (명)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.1, orientation="h"),
    hovermode="x unified"
)
chart_placeholder.plotly_chart(fig, use_container_width=True)

# 상세 시트 업데이트
display_df = df[["Date", "Revenue", "P.rate(%)", "ARPPU", "Required_DAU", "Required_PU"]].copy()
display_df["Date"] = display_df["Date"].dt.strftime('%Y-%m')
table_placeholder.dataframe(display_df.style.format({
    "Revenue": "{:,.0f}",
    "P.rate(%)": "{:.1f}%",
    "ARPPU": "{:,.0f}",
    "Required_DAU": "{:,.0f}",
    "Required_PU": "{:,.0f}"
}), use_container_width=True)

# CSV 다운로드
csv = display_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 시뮬레이션 결과 CSV 다운로드",
    data=csv,
    file_name=f"ProjectA_V4_Plan_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
