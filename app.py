import streamlit as st
import json
import math
from datetime import datetime
from supabase import create_client

# ─── Supabase Config ───
SUPABASE_URL = "https://yxifzucmghsqewopssuv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4aWZ6dWNtZ2hzcWV3b3Bzc3V2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwMTYwMjMsImV4cCI6MjA5MTU5MjAyM30.6bb8TR6voqCRyDQ2sgTf_D7vhWnlmaDuIw0FDyyHs4c"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

sb = get_supabase()

# ─── Constants ───
SEASON_PRESETS = {
    "kr": {"label": "🇰🇷 한국형", "data": [1.3,1.0,0.9,0.85,0.9,0.8,0.95,1.1,0.9,0.95,1.0,1.5]},
    "global": {"label": "🌏 글로벌형", "data": [0.9,0.85,0.9,0.85,0.9,1.0,1.15,1.1,0.95,0.9,1.2,1.4]},
    "flat": {"label": "➖ 플랫", "data": [1,1,1,1,1,1,1,1,1,1,1,1]},
}

DEFAULT_BONUS_CATS = [
    {"id":"season","label":"시즌","desc":"설/추석/연말","value":0.3,"icon":"🎊"},
    {"id":"content","label":"콘텐츠","desc":"대규모 컨텐츠 패치","value":0.25,"icon":"🎮"},
    {"id":"major_update","label":"대규모UP","desc":"대규모 업데이트/확장팩","value":0.4,"icon":"🔥"},
    {"id":"bm","label":"BM","desc":"신규 과금 상품/패키지","value":0.2,"icon":"💎"},
    {"id":"marketing","label":"마케팅","desc":"UA/브랜딩 캠페인","value":0.2,"icon":"📢"},
    {"id":"vacation","label":"방학","desc":"여름/겨울 방학","value":0.15,"icon":"🏖️"},
    {"id":"holiday","label":"연휴","desc":"공휴일/연휴 밀집","value":0.15,"icon":"📅"},
    {"id":"compete","label":"경쟁작","desc":"주요 경쟁 타이틀 (감산)","value":-0.15,"icon":"⚔️"},
    {"id":"feature","label":"피처링","desc":"앱스토어 추천","value":0.2,"icon":"⭐"},
]

# ─── Helpers ───
def gen_months(sy, sm, ey, em):
    months = []
    y, m, i = sy, sm, 0
    while y < ey or (y == ey and m <= em):
        import calendar
        days = calendar.monthrange(y, m)[1]
        months.append({"index": i, "year": y, "month": m, "days": days,
                        "label": f"{y}.{m:02d}", "short": f"{str(y)[2:]}.{m:02d}"})
        i += 1; m += 1
        if m > 12: m = 1; y += 1
    return months

def cal_year_groups(months):
    groups = {}
    for mo in months:
        k = str(mo["year"])
        if k not in groups: groups[k] = []
        groups[k].append(mo["index"])
        mo["cal_year"] = k
    return groups

def decay_curve(month_idx, rate):
    return math.pow(1 - rate/100, month_idx)

def fmt(v):
    if abs(v) >= 1e8: return f"{v/1e8:.1f}억"
    if abs(v) >= 1e4: return f"{v/1e4:.0f}만"
    return f"{v:,.0f}"

def fmt_n(v):
    if abs(v) >= 1e4: return f"{v/1e4:.1f}만"
    return f"{v:,.0f}"

# ─── DB Functions ───
def get_app_config():
    r = sb.table("app_config").select("*").eq("id", "main").execute()
    if r.data: return r.data[0]
    return {"master_password": "1234", "app_title": "매출 시뮬레이터"}

def get_projects():
    r = sb.table("projects").select("*").order("created_at", desc=False).execute()
    return r.data or []

def get_project(pid):
    r = sb.table("projects").select("*").eq("id", pid).execute()
    return r.data[0] if r.data else None

def create_project(name, password, genre="", market=""):
    r = sb.table("projects").insert({
        "name": name, "password": password, "genre": genre, "market": market
    }).execute()
    if r.data:
        pid = r.data[0]["id"]
        # Create default yearly targets
        for year in [2026, 2027, 2028, 2029]:
            sb.table("yearly_targets").insert({
                "project_id": pid, "year": year,
                "target_kr": 50000000000, "target_global": 20000000000
            }).execute()
        return pid
    return None

def update_project(pid, data):
    sb.table("projects").update({**data, "updated_at": datetime.now().isoformat()}).eq("id", pid).execute()

def get_yearly_targets(pid):
    r = sb.table("yearly_targets").select("*").eq("project_id", pid).order("year").execute()
    return {str(t["year"]): {"kr": t["target_kr"], "global": t["target_global"]} for t in (r.data or [])}

def upsert_yearly_target(pid, year, kr, gl):
    sb.table("yearly_targets").upsert({
        "project_id": pid, "year": year, "target_kr": kr, "target_global": gl
    }, on_conflict="project_id,year").execute()

def get_monthly_data(pid):
    r = sb.table("monthly_data").select("*").eq("project_id", pid).execute()
    return {d["month_index"]: d for d in (r.data or [])}

def upsert_monthly(pid, idx, manual_adj=0, bonuses=None, p_rate=5.0, arppu=70000):
    sb.table("monthly_data").upsert({
        "project_id": pid, "month_index": idx,
        "manual_adj": manual_adj,
        "bonuses": json.dumps(bonuses or {}),
        "p_rate": p_rate, "arppu": arppu
    }, on_conflict="project_id,month_index").execute()

# ─── Page Config ───
st.set_page_config(page_title="매출 시뮬레이터", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
    [data-testid="stSidebar"] { min-width: 280px; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .block-container { padding-top: 1.5rem; }
</style>""", unsafe_allow_html=True)

# ─── Session State Init ───
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_project" not in st.session_state:
    st.session_state.current_project = None
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

# ═══════════════════════════════════════════
# PAGE 1: LOGIN
# ═══════════════════════════════════════════
if not st.session_state.logged_in:
    config = get_app_config()
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🚀 매출 시뮬레이터")
        st.markdown("프로젝트별 매출 목표를 시뮬레이션하고 관리합니다.")
        st.markdown("---")
        pw = st.text_input("🔒 비밀번호를 입력하세요", type="password", key="login_pw")
        if st.button("로그인", width="stretch", type="primary"):
            if pw == config.get("master_password", "1234"):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()

# ═══════════════════════════════════════════
# PAGE 2: PROJECT LIST
# ═══════════════════════════════════════════
if st.session_state.current_project is None:
    st.markdown("## 🚀 매출 시뮬레이터")
    st.markdown("프로젝트를 선택하거나 새로 만들어주세요.")
    st.markdown("---")
    
    projects = get_projects()
    
    # New project form
    with st.expander("➕ 새 프로젝트 만들기", expanded=len(projects) == 0):
        nc1, nc2 = st.columns(2)
        with nc1:
            new_name = st.text_input("프로젝트명", placeholder="예: 프로젝트A")
            new_genre = st.text_input("장르", placeholder="예: 방치형 RPG")
        with nc2:
            new_pw = st.text_input("프로젝트 비밀번호", type="password", placeholder="관리자 모드 진입용")
            new_market = st.text_input("타겟 시장", placeholder="예: 한국/글로벌")
        if st.button("✅ 프로젝트 생성", type="primary"):
            if new_name and new_pw:
                pid = create_project(new_name, new_pw, new_genre, new_market)
                if pid:
                    st.session_state.current_project = pid
                    st.rerun()
            else:
                st.warning("프로젝트명과 비밀번호를 입력해주세요.")
    
    st.markdown("---")
    
    # Project cards
    if projects:
        cols = st.columns(min(len(projects), 3))
        for i, proj in enumerate(projects):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"### {proj['name']}")
                    if proj.get("genre"): st.caption(f"🎮 {proj['genre']}")
                    if proj.get("market"): st.caption(f"🌍 {proj['market']}")
                    period = f"{proj['start_year']}.{proj['start_month']:02d} ~ {proj['end_year']}.{proj['end_month']:02d}"
                    st.caption(f"📆 {period}")
                    st.caption(f"🔒 {'잠금' if proj.get('is_locked', True) else '해제'}")
                    if st.button("📂 열기", key=f"open_{proj['id']}", width="stretch"):
                        st.session_state.current_project = proj["id"]
                        st.session_state.admin_mode = False
                        st.rerun()
    else:
        st.info("아직 프로젝트가 없습니다. 위에서 새 프로젝트를 만들어주세요.")
    
    st.markdown("---")
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# ═══════════════════════════════════════════
# PAGE 3: PROJECT SIMULATOR
# ═══════════════════════════════════════════
proj = get_project(st.session_state.current_project)
if not proj:
    st.error("프로젝트를 찾을 수 없습니다.")
    st.session_state.current_project = None
    st.rerun()

pid = proj["id"]
is_admin = st.session_state.admin_mode

# ─── Header ───
# Row 1: Back button + Title
hc_back, hc_title = st.columns([1, 5])
with hc_back:
    if st.button("← 목록으로", key="back_btn"):
        st.session_state.current_project = None
        st.session_state.admin_mode = False
        st.rerun()
with hc_title:
    if is_admin:
        new_title = st.text_input("프로젝트명", value=proj["name"], key="proj_title", label_visibility="collapsed")
        if new_title != proj["name"]:
            update_project(pid, {"name": new_title})
    else:
        st.markdown(f"## 🚀 {proj['name']}")

# Row 2: Info + Mode toggle
hc_info, hc_mode = st.columns([3, 3])
with hc_info:
    info_parts = []
    if proj.get("genre"): info_parts.append(f"🎮 {proj['genre']}")
    if proj.get("market"): info_parts.append(f"🌍 {proj['market']}")
    info_parts.append(f"📆 {sy}.{sm:02d} ~ {ey}.{em:02d} ({N}개월)")
    st.caption(" · ".join(info_parts))

with hc_mode:
    if is_admin:
        mc_left, mc_right = st.columns([3, 1])
        with mc_left:
            st.success("🔓 관리자 모드")
        with mc_right:
            if st.button("🔒 잠금", key="lock_btn"):
                st.session_state.admin_mode = False
                st.rerun()
    else:
        mc_left, mc_right = st.columns([3, 2])
        with mc_left:
            st.info("👁️ 뷰 모드")
        with mc_right:
            unlock_pw = st.text_input("비밀번호", type="password", key="unlock_pw", label_visibility="collapsed", placeholder="비밀번호 입력")
            if unlock_pw:
                if unlock_pw == proj.get("password", ""):
                    st.session_state.admin_mode = True
                    st.rerun()
                else:
                    st.error("비밀번호 오류")

st.markdown("---")

# ─── Load Data ───
sy, sm = proj["start_year"], proj["start_month"]
ey, em = proj["end_year"], proj["end_month"]
months = gen_months(sy, sm, ey, em)
N = len(months)
yg = cal_year_groups(months)
year_labels = list(yg.keys())

targets = get_yearly_targets(pid)
monthly_db = get_monthly_data(pid)

# Project settings
decay_kr = proj.get("decay_kr", 4.0)
decay_gl = proj.get("decay_global", 3.0)
boost_kr = proj.get("launch_boost_kr", 0.5)
boost_gl = proj.get("launch_boost_global", 0.3)
season_kr = proj.get("season_kr", SEASON_PRESETS["kr"]["data"])
season_gl = proj.get("season_global", SEASON_PRESETS["global"]["data"])
if isinstance(season_kr, str): season_kr = json.loads(season_kr)
if isinstance(season_gl, str): season_gl = json.loads(season_gl)
dau_cap = proj.get("dau_cap", 1000000)
custom_cats = proj.get("custom_bonus_cats", [])
if isinstance(custom_cats, str): custom_cats = json.loads(custom_cats)
all_bonus_cats = DEFAULT_BONUS_CATS + custom_cats

# ─── Period Settings (Admin) ───
if is_admin:
    with st.expander("📆 시뮬레이션 기간 설정"):
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        with pc1: new_sy = st.number_input("시작 연도", 2024, 2035, sy, key="sy")
        with pc2: new_sm = st.selectbox("시작 월", range(1,13), index=sm-1, key="sm")
        with pc3: new_ey = st.number_input("종료 연도", 2024, 2035, ey, key="ey")
        with pc4: new_em = st.selectbox("종료 월", range(1,13), index=em-1, key="em")
        with pc5:
            st.markdown("")
            st.markdown("")
            if st.button("기간 저장", type="primary"):
                update_project(pid, {"start_year": new_sy, "start_month": new_sm, "end_year": new_ey, "end_month": new_em})
                st.rerun()

# ─── Region View Toggle ───
region_view = st.radio("권역 보기", ["🌐 통합", "🇰🇷 한국", "🌏 글로벌"], horizontal=True, label_visibility="collapsed")
rv = "total" if "통합" in region_view else ("kr" if "한국" in region_view else "global")

# ─── Calculations ───
calc_rows = []
for mo in months:
    i = mo["index"]
    md = monthly_db.get(i, {})
    
    # Base weights from decay × season
    d_kr = decay_curve(i, decay_kr)
    d_gl = decay_curve(i, decay_gl)
    s_kr = season_kr[mo["month"]-1] if mo["month"]-1 < len(season_kr) else 1.0
    s_gl = season_gl[mo["month"]-1] if mo["month"]-1 < len(season_gl) else 1.0
    lb_kr = boost_kr if i < 3 else 0
    lb_gl = boost_gl if i < 3 else 0
    bw_kr = max(0.05, round(d_kr * s_kr + lb_kr, 4))
    bw_gl = max(0.05, round(d_gl * s_gl + lb_gl, 4))
    
    manual = md.get("manual_adj", 0) or 0
    bonuses_raw = md.get("bonuses", "{}")
    if isinstance(bonuses_raw, str): bonuses_raw = json.loads(bonuses_raw)
    bonus_sum = sum(cat["value"] for cat in all_bonus_cats if bonuses_raw.get(cat["id"]))
    
    fw_kr = max(0.1, bw_kr + manual + bonus_sum)
    fw_gl = max(0.1, bw_gl + manual + bonus_sum)
    
    p_rate = md.get("p_rate", 5.0) or 5.0
    arppu = md.get("arppu", 70000) or 70000
    arpdau = arppu * (p_rate / 100)
    
    calc_rows.append({
        **mo, "bw_kr": bw_kr, "bw_gl": bw_gl, "manual": manual,
        "bonuses": bonuses_raw, "bonus_sum": bonus_sum,
        "fw_kr": fw_kr, "fw_gl": fw_gl,
        "p_rate": p_rate, "arppu": arppu, "arpdau": arpdau,
    })

# Revenue distribution
for yl, indices in yg.items():
    t = targets.get(yl, {"kr": 0, "global": 0})
    tw_kr = sum(calc_rows[j]["fw_kr"] for j in indices) or 1
    tw_gl = sum(calc_rows[j]["fw_gl"] for j in indices) or 1
    for j in indices:
        r = calc_rows[j]
        r["rev_kr"] = (t.get("kr",0) or 0) * (r["fw_kr"] / tw_kr)
        r["rev_gl"] = (t.get("global",0) or 0) * (r["fw_gl"] / tw_gl)
        r["revenue"] = r["rev_kr"] + r["rev_gl"]
        r["dau"] = r["revenue"] / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["dau_kr"] = r["rev_kr"] / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["dau_gl"] = r["rev_gl"] / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["over_cap"] = r["dau"] > dau_cap

# ─── KPI Cards ───
total_tgt = sum(
    (t.get("kr",0) or 0) + (t.get("global",0) or 0) if rv == "total"
    else (t.get("kr",0) or 0) if rv == "kr"
    else (t.get("global",0) or 0)
    for t in targets.values()
)
avg_dau = sum(r["dau"] for r in calc_rows) / N if N > 0 else 0
avg_pr = sum(r["p_rate"] for r in calc_rows) / N if N > 0 else 0
avg_ar = sum(r["arppu"] for r in calc_rows) / N if N > 0 else 0
over_count = sum(1 for r in calc_rows if r["over_cap"])

mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("📊 목표 매출", fmt(total_tgt))
mc2.metric("👥 평균 필요 DAU", fmt_n(avg_dau))
mc3.metric("💰 평균 P.rate", f"{avg_pr:.1f}%")
mc4.metric("💎 평균 ARPPU", fmt(avg_ar))
if over_count > 0:
    mc5.metric("⚠️ DAU 초과", f"{over_count}개월", delta=f"상한 {fmt_n(dau_cap)}", delta_color="inverse")
else:
    mc5.metric("✅ DAU 상태", "정상", delta=f"상한 {fmt_n(dau_cap)}")

# ─── DAU Cap Slider (always visible) ───
if is_admin:
    dau_cols = st.columns([1, 5, 1])
    with dau_cols[0]:
        st.markdown("🚨 **DAU 상한**")
    with dau_cols[1]:
        new_cap = st.slider("DAU 상한선", min_value=50000, max_value=3000000, value=int(dau_cap), step=50000, key="dau_cap_main", label_visibility="collapsed")
        if new_cap != dau_cap:
            update_project(pid, {"dau_cap": new_cap})
    with dau_cols[2]:
        st.markdown(f"**{fmt_n(dau_cap)}**")

# ─── Main Chart ───
import plotly.graph_objects as go
from plotly.subplots import make_subplots

rev_field = "rev_kr" if rv == "kr" else "rev_gl" if rv == "global" else "revenue"
dau_field = "dau_kr" if rv == "kr" else "dau_gl" if rv == "global" else "dau"

x_labels = [r["label"] for r in calc_rows]  # "2026.10" format

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(
    x=x_labels,
    y=[r[rev_field] for r in calc_rows],
    name="매출",
    marker_color=["#ef4444" if r["over_cap"] else "#3b82f6" for r in calc_rows],
    opacity=0.7,
), secondary_y=False)
fig.add_trace(go.Scatter(
    x=x_labels,
    y=[r[dau_field] for r in calc_rows],
    name="필요 DAU", line=dict(color="#f59e0b", width=2),
), secondary_y=True)
fig.add_trace(go.Scatter(
    x=x_labels,
    y=[dau_cap] * N,
    name="DAU 상한선", line=dict(color="#ef4444", width=1, dash="dash"),
), secondary_y=True)
fig.update_layout(
    height=350, margin=dict(t=30, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(type="category", tickangle=-45),
)
fig.update_yaxes(title_text="매출", secondary_y=False)
fig.update_yaxes(title_text="DAU", secondary_y=True)
st.plotly_chart(fig, width="stretch")

# ─── Tabs ───
tab_targets, tab_curve, tab_weights, tab_metrics, tab_data = st.tabs(
    ["📊 연도별 목표", "📈 감소커브", "⚖️ 가중치", "⚙️ 지표", "📋 데이터"]
)

# ═══ TAB: TARGETS ═══
with tab_targets:
    st.subheader("연도별 권역 매출 목표")
    if not is_admin:
        st.info("🔒 뷰 모드 — 수정하려면 관리자 모드로 전환하세요")
    
    cols = st.columns(len(year_labels))
    for ci, yl in enumerate(year_labels):
        with cols[ci]:
            t = targets.get(yl, {"kr": 0, "global": 0})
            st.markdown(f"**{yl}년**")
            indices = yg[yl]
            st.caption(f"{months[indices[0]]['label']} ~ {months[indices[-1]]['label']} ({len(indices)}개월)")
            
            if is_admin:
                kr_val = st.number_input(f"🇰🇷 한국 ({yl})", value=int(t.get("kr",0) or 0), step=1000000000, key=f"tkr_{yl}", format="%d")
                gl_val = st.number_input(f"🌏 글로벌 ({yl})", value=int(t.get("global",0) or 0), step=1000000000, key=f"tgl_{yl}", format="%d")
                if kr_val != t.get("kr",0) or gl_val != t.get("global",0):
                    upsert_yearly_target(pid, int(yl), kr_val, gl_val)
            else:
                st.metric("🇰🇷 한국", fmt(t.get("kr",0) or 0))
                st.metric("🌏 글로벌", fmt(t.get("global",0) or 0))
            
            st.metric("합계", fmt((t.get("kr",0) or 0) + (t.get("global",0) or 0)))

# ═══ TAB: CURVE ═══
with tab_curve:
    st.subheader("자연감소 커브 × 시즌 계수")
    st.caption("기본 가중치 = 자연감소 커브 × 시즌 계수 (자동 계산)")
    
    if not is_admin:
        st.info("🔒 뷰 모드")
    
    cc1, cc2 = st.columns(2)
    
    with cc1:
        st.markdown("**🇰🇷 한국**")
        if is_admin:
            new_dkr = st.slider("KR 월간 감소율", min_value=0.0, max_value=15.0, value=float(decay_kr), step=0.5, key="dkr", format="%.1f%%")
            new_bkr = st.slider("KR 론칭 부스트", min_value=0.0, max_value=2.0, value=float(boost_kr), step=0.1, key="bkr", format="%.1f")
            sp_kr = st.selectbox("시즌 프리셋", list(SEASON_PRESETS.keys()),
                                  format_func=lambda x: SEASON_PRESETS[x]["label"],
                                  index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_kr","kr")),
                                  key="sp_kr")
            if new_dkr != decay_kr or new_bkr != boost_kr:
                update_project(pid, {"decay_kr": new_dkr, "launch_boost_kr": new_bkr})
            if sp_kr != proj.get("season_preset_kr","kr"):
                update_project(pid, {"season_preset_kr": sp_kr, "season_kr": json.dumps(SEASON_PRESETS[sp_kr]["data"])})
                st.rerun()
        else:
            st.metric("감소율", f"{decay_kr}%/월")
            st.metric("론칭 부스트", f"+{boost_kr}")
    
    with cc2:
        st.markdown("**🌏 글로벌**")
        if is_admin:
            new_dgl = st.slider("GL 월간 감소율", min_value=0.0, max_value=15.0, value=float(decay_gl), step=0.5, key="dgl", format="%.1f%%")
            new_bgl = st.slider("GL 론칭 부스트", min_value=0.0, max_value=2.0, value=float(boost_gl), step=0.1, key="bgl", format="%.1f")
            sp_gl = st.selectbox("시즌 프리셋", list(SEASON_PRESETS.keys()),
                                  format_func=lambda x: SEASON_PRESETS[x]["label"],
                                  index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_global","global")),
                                  key="sp_gl")
            if new_dgl != decay_gl or new_bgl != boost_gl:
                update_project(pid, {"decay_global": new_dgl, "launch_boost_global": new_bgl})
            if sp_gl != proj.get("season_preset_global","global"):
                update_project(pid, {"season_preset_global": sp_gl, "season_global": json.dumps(SEASON_PRESETS[sp_gl]["data"])})
                st.rerun()
        else:
            st.metric("감소율", f"{decay_gl}%/월")
            st.metric("론칭 부스트", f"+{boost_gl}")
    
    # Curve preview
    st.markdown("**📈 기본 가중치 커브 프리뷰**")
    import plotly.graph_objects as go2
    cx_labels = [r["label"] for r in calc_rows]
    cfig = go2.Figure()
    cfig.add_trace(go2.Scatter(x=cx_labels, y=[r["bw_kr"] for r in calc_rows],
                               name="한국", line=dict(color="#3b82f6")))
    cfig.add_trace(go2.Scatter(x=cx_labels, y=[r["bw_gl"] for r in calc_rows],
                               name="글로벌", line=dict(color="#8b5cf6")))
    cfig.update_layout(height=250, margin=dict(t=20, b=40), hovermode="x unified",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(type="category", tickangle=-45))
    st.plotly_chart(cfig, width="stretch")
    
    # Season edit
    if is_admin:
        with st.expander("🔧 시즌 계수 직접 수정"):
            se_region = st.radio("권역", ["한국", "글로벌"], horizontal=True, key="se_r")
            se_data = list(season_kr) if se_region == "한국" else list(season_gl)
            changed = False
            se_cols = st.columns(6)
            for mi in range(12):
                with se_cols[mi % 6]:
                    nv = st.number_input(f"{mi+1}월", 0.1, 3.0, float(se_data[mi]), 0.05, key=f"se_{se_region}_{mi}")
                    if nv != se_data[mi]:
                        se_data[mi] = nv
                        changed = True
            if changed:
                field = "season_kr" if se_region == "한국" else "season_global"
                update_project(pid, {field: json.dumps(se_data)})

# ═══ TAB: WEIGHTS ═══
with tab_weights:
    st.subheader("월별 가중치 조정")
    st.caption("자동 계산된 가중치 + 수동 조정 + 보너스 = 최종 가중치")
    
    if not is_admin:
        st.info("🔒 뷰 모드")
    
    # Bonus legend
    with st.expander("📋 보너스 항목 목록", expanded=False):
        for cat in all_bonus_cats:
            sign = "+" if cat["value"] > 0 else ""
            st.caption(f"{cat['icon']} **{cat['label']}** — {cat['desc']} ({sign}{cat['value']})")
        
        if is_admin:
            st.markdown("---")
            st.markdown("**커스텀 항목 추가**")
            ac1, ac2, ac3, ac4 = st.columns([1, 3, 2, 2])
            with ac1: ci = st.text_input("아이콘", "🏷️", key="cb_icon")
            with ac2: cn = st.text_input("항목명", key="cb_name")
            with ac3: cv = st.number_input("배율값", -1.0, 2.0, 0.2, 0.05, key="cb_val")
            with ac4:
                st.markdown("")
                st.markdown("")
                if st.button("추가", key="cb_add"):
                    if cn:
                        new_cats = custom_cats + [{"id": f"c_{int(datetime.now().timestamp())}", "label": cn, "desc": "사용자 정의", "value": cv, "icon": ci}]
                        update_project(pid, {"custom_bonus_cats": json.dumps(new_cats)})
                        st.rerun()
    
    # Year-by-year expandable
    for yl in year_labels:
        indices = yg[yl]
        with st.expander(f"**{yl}년** ({months[indices[0]]['label']} ~ {months[indices[-1]]['label']})", expanded=(yl == year_labels[0])):
            for idx in indices:
                r = calc_rows[idx]
                wcols = st.columns([1.2, 1, 1, 4, 1])
                with wcols[0]:
                    st.markdown(f"**{r['short']}**")
                with wcols[1]:
                    st.caption(f"KR: {r['bw_kr']:.2f}")
                with wcols[2]:
                    st.caption(f"GL: {r['bw_gl']:.2f}")
                with wcols[3]:
                    if is_admin:
                        # Bonus toggles
                        bonus_state = r["bonuses"]
                        b_cols = st.columns(len(all_bonus_cats))
                        for bi, cat in enumerate(all_bonus_cats):
                            with b_cols[bi]:
                                active = bonus_state.get(cat["id"], False)
                                if st.checkbox(f"{cat['icon']}{cat['label']}", value=active, key=f"b_{idx}_{cat['id']}", label_visibility="visible"):
                                    if not active:
                                        bonus_state[cat["id"]] = True
                                        upsert_monthly(pid, idx, r["manual"], bonus_state, r["p_rate"], r["arppu"])
                                else:
                                    if active:
                                        bonus_state[cat["id"]] = False
                                        upsert_monthly(pid, idx, r["manual"], bonus_state, r["p_rate"], r["arppu"])
                    else:
                        active_bonuses = [cat["icon"]+cat["label"] for cat in all_bonus_cats if r["bonuses"].get(cat["id"])]
                        st.caption(" ".join(active_bonuses) if active_bonuses else "-")
                with wcols[4]:
                    color = "🔵" if r["fw_kr"] > 1.5 else "🟡" if r["fw_kr"] < 0.7 else ""
                    st.markdown(f"{color} **{r['fw_kr']:.2f}**")

# ═══ TAB: METRICS ═══
with tab_metrics:
    st.subheader("P.rate / ARPPU 조정")
    
    if not is_admin:
        st.info("🔒 뷰 모드")
    
    if is_admin:
        # Bulk apply
        with st.expander("⚡ 일괄 적용"):
            bc1, bc2 = st.columns(2)
            with bc1:
                bulk_pr = st.number_input("P.rate (%)", 0.1, 20.0, 5.0, 0.1, key="bulk_pr")
                bulk_pr_year = st.selectbox("적용 연도", year_labels, key="bpr_y")
                if st.button("P.rate 일괄 적용", key="bpr_apply"):
                    for j in yg[bulk_pr_year]:
                        md = monthly_db.get(j, {})
                        bonuses_raw = md.get("bonuses", "{}")
                        if isinstance(bonuses_raw, str): bonuses_raw = json.loads(bonuses_raw)
                        upsert_monthly(pid, j, md.get("manual_adj", 0), bonuses_raw, bulk_pr, md.get("arppu", 70000))
                    st.rerun()
            with bc2:
                bulk_ar = st.number_input("ARPPU (원)", 10000, 500000, 70000, 1000, key="bulk_ar")
                bulk_ar_year = st.selectbox("적용 연도", year_labels, key="bar_y")
                if st.button("ARPPU 일괄 적용", key="bar_apply"):
                    for j in yg[bulk_ar_year]:
                        md = monthly_db.get(j, {})
                        bonuses_raw = md.get("bonuses", "{}")
                        if isinstance(bonuses_raw, str): bonuses_raw = json.loads(bonuses_raw)
                        upsert_monthly(pid, j, md.get("manual_adj", 0), bonuses_raw, md.get("p_rate", 5.0), bulk_ar)
                    st.rerun()
    
    # Monthly grid
    m_cols_per_row = 4
    for row_start in range(0, N, m_cols_per_row):
        cols = st.columns(m_cols_per_row)
        for ci in range(m_cols_per_row):
            idx = row_start + ci
            if idx >= N: break
            r = calc_rows[idx]
            with cols[ci]:
                with st.container(border=True):
                    st.markdown(f"**{r['short']}**")
                    if r["over_cap"]:
                        st.error(f"DAU {fmt_n(r['dau'])} ⚠️")
                    else:
                        st.caption(f"DAU {fmt_n(r['dau'])}")
                    
                    if is_admin:
                        new_pr = st.slider("P.rate", 0.1, 20.0, r["p_rate"], 0.1, key=f"pr_{idx}")
                        new_ar = st.slider("ARPPU", 10000, 500000, r["arppu"], 1000, key=f"ar_{idx}")
                        if new_pr != r["p_rate"] or new_ar != r["arppu"]:
                            upsert_monthly(pid, idx, r["manual"], r["bonuses"], new_pr, new_ar)
                    else:
                        st.metric("P.rate", f"{r['p_rate']:.1f}%")
                        st.metric("ARPPU", f"{r['arppu']:,}원")

# ═══ TAB: DATA ═══
with tab_data:
    st.subheader("상세 데이터 시트")
    
    import pandas as pd
    df = pd.DataFrame([{
        "월": r["short"],
        "연도": r["cal_year"],
        "매출(통합)": round(r["revenue"]),
        "한국": round(r["rev_kr"]),
        "글로벌": round(r["rev_gl"]),
        "W(KR)": round(r["fw_kr"], 2),
        "W(GL)": round(r["fw_gl"], 2),
        "보너스": round(r["bonus_sum"], 2),
        "P.rate(%)": round(r["p_rate"], 1),
        "ARPPU": r["arppu"],
        "ARPDAU": round(r["arpdau"]),
        "필요DAU": round(r["dau"]),
        "초과": "⚠️" if r["over_cap"] else "✅",
    } for r in calc_rows])
    
    st.dataframe(df.style.format({
        "매출(통합)": "{:,.0f}",
        "한국": "{:,.0f}",
        "글로벌": "{:,.0f}",
        "ARPPU": "{:,}",
        "ARPDAU": "{:,}",
        "필요DAU": "{:,.0f}",
    }), width="stretch", height=500)
    
    # CSV download
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, f"simulation_{proj['name']}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
