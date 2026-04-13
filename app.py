# --- 1. 사이드바: 탑다운 목표 금액 입력 ---
st.sidebar.header("🎯 연간 목표 매출 입력 (탑다운)")
st.sidebar.markdown("목표 금액을 수정하면 하위 지표가 자동 재계산됩니다.")

target_2026_q4 = st.sidebar.number_input(
    "2026 Q4 목표 (원)", 
    min_value=0, 
    value=94446454545, 
    step=100000000, # 1억 단위 조작
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

# 입력된 금액을 보기 쉽게 텍스트로 한번 더 표시 (선택 사항)
st.sidebar.caption(f"↳ 26년 Q4: {target_2026_q4 / 100000000:,.1f}억 원")
st.sidebar.caption(f"↳ 27년: {target_2027 / 100000000:,.1f}억 원")
st.sidebar.caption(f"↳ 28년: {target_2028 / 100000000:,.1f}억 원")
