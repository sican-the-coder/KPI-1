import streamlit as st
import json, math, calendar
from datetime import datetime
from supabase import create_client
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ─── Supabase ───
SB_URL = st.secrets["supabase"]["url"]
SB_KEY = st.secrets["supabase"]["key"]

@st.cache_resource
def get_sb(): return create_client(SB_URL, SB_KEY)
sb = get_sb()

# ─── Design Tokens ───
C_BG      = "#080c18"
C_CARD    = "#0f1628"
C_CARD2   = "#141d35"
C_BORDER  = "rgba(99,179,237,0.10)"
C_BORDER2 = "rgba(99,179,237,0.20)"
C_TEXT    = "#e2e8f0"
C_SUB     = "#b0bfd4"
C_MUTED   = "#7a8fa8"
C_BLUE    = "#3b82f6"
C_PURPLE  = "#8b5cf6"
C_AMBER   = "#f59e0b"
C_RED     = "#ef4444"
C_GREEN   = "#10b981"
C_TEAL    = "#14b8a6"
CHART_BG  = "rgba(0,0,0,0)"

# ─── Page Config ───
st.set_page_config(page_title="매출 시뮬레이터", layout="wide", initial_sidebar_state="collapsed")

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Noto Sans KR', sans-serif;
    background-color: {C_BG};
}}
.block-container {{ padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px; }}

/* ── 공통 카드 ── */
.card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 16px;
    padding: 20px 22px;
}}
.card-sm {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 12px;
    padding: 14px 16px;
}}

/* ── KPI 카드 ── */
.kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }}
.kpi-card {{
    background: {C_CARD2};
    border: 1px solid {C_BORDER};
    border-radius: 14px;
    padding: 18px 16px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}}
.kpi-card:hover {{ border-color: {C_BORDER2}; }}
.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, {C_BLUE});
    opacity: 0.8;
}}
.kpi-icon {{ font-size: 1.2rem; margin-bottom: 6px; }}
.kpi-label {{ font-size: 0.8rem; color: {C_SUB}; letter-spacing: 0.03em; margin-bottom: 6px; }}
.kpi-value {{ font-size: 1.55rem; font-weight: 700; line-height: 1.1; }}
.kpi-sub {{ font-size: 0.76rem; color: {C_MUTED}; margin-top: 4px; }}

/* ── 타이틀 ── */
.page-title {{
    font-size: 2rem; font-weight: 700;
    letter-spacing: -0.04em;
    background: linear-gradient(135deg, {C_TEXT} 0%, {C_SUB} 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 2px;
}}
.page-meta {{ font-size: 0.88rem; color: {C_SUB}; margin-bottom: 16px; }}
.page-meta span {{ color: {C_SUB}; margin: 0 6px; }}

/* ── 모드 배지 ── */
.badge-admin {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(16,185,129,0.12);
    border: 1px solid rgba(16,185,129,0.30);
    border-radius: 20px; padding: 5px 14px;
    color: {C_GREEN}; font-weight: 600; font-size: 0.8rem;
}}
.badge-view {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(59,130,246,0.10);
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 20px; padding: 5px 14px;
    color: {C_BLUE}; font-weight: 600; font-size: 0.8rem;
}}

/* ── 뷰 모드 전용 ── */
.view-metric {{
    background: {C_CARD2};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
}}
.view-metric-label {{ font-size: 0.78rem; color: {C_SUB}; margin-bottom: 3px; }}
.view-metric-value {{ font-size: 1.1rem; font-weight: 700; color: {C_TEXT}; }}

.bonus-badge {{
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.22);
    border-radius: 20px; padding: 3px 10px;
    font-size: 0.75rem; color: {C_BLUE};
    margin: 2px;
}}
.bonus-badge.neg {{
    background: rgba(239,68,68,0.10);
    border-color: rgba(239,68,68,0.22);
    color: {C_RED};
}}

.month-row {{
    display: flex; align-items: center;
    background: {C_CARD2};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    gap: 12px;
}}
.month-label {{ font-size: 0.85rem; font-weight: 600; color: {C_TEXT}; min-width: 52px; }}
.month-weight {{
    font-size: 0.85rem; font-weight: 700;
    padding: 2px 8px; border-radius: 6px;
    background: rgba(59,130,246,0.12);
    color: {C_BLUE};
}}
.month-weight.high {{
    background: rgba(16,185,129,0.12); color: {C_GREEN};
}}
.month-weight.low {{
    background: rgba(239,68,68,0.10); color: {C_RED};
}}
.month-bonuses {{ flex: 1; display: flex; flex-wrap: wrap; gap: 3px; }}
.month-metrics {{ font-size: 0.78rem; color: {C_SUB}; text-align: right; min-width: 120px; }}

/* ── 연도 헤더 ── */
.year-header {{
    font-size: 0.82rem; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: {C_SUB};
    padding: 8px 0 6px;
    border-bottom: 1px solid {C_BORDER};
    margin-bottom: 8px;
    margin-top: 16px;
}}

/* ── 타겟 카드 (뷰) ── */
.target-card {{
    background: {C_CARD2};
    border: 1px solid {C_BORDER};
    border-radius: 14px;
    padding: 18px;
    text-align: center;
}}
.target-year {{ font-size: 1.2rem; font-weight: 700; color: {C_TEXT}; margin-bottom: 12px; }}
.target-region {{ font-size: 0.78rem; color: {C_SUB}; margin-bottom: 3px; }}
.target-amount {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 10px; }}
.target-divider {{ border: none; border-top: 1px solid {C_BORDER}; margin: 10px 0; }}
.target-total-label {{ font-size: 0.78rem; color: {C_SUB}; }}
.target-total {{ font-size: 1.0rem; font-weight: 700; color: {C_TEXT}; }}

/* ── 커브 파라미터 뷰 ── */
.param-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid {C_BORDER};
}}
.param-row:last-child {{ border-bottom: none; }}
.param-label {{ font-size: 0.84rem; color: {C_SUB}; }}
.param-value {{ font-size: 0.95rem; font-weight: 700; color: {C_TEXT}; }}

/* ── 시즌 계수 그리드 ── */
.season-grid {{
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px;
    margin-top: 10px;
}}
.season-cell {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 8px 4px;
    text-align: center;
}}
.season-month {{ font-size: 0.72rem; color: {C_SUB}; margin-bottom: 2px; }}
.season-val {{ font-size: 0.9rem; font-weight: 700; }}

/* ── 지표 카드 (뷰) ── */
.metric-card {{
    background: {C_CARD2};
    border: 1px solid {C_BORDER};
    border-radius: 12px;
    padding: 14px;
}}
.metric-month {{ font-size: 0.8rem; font-weight: 700; color: {C_TEXT}; margin-bottom: 8px; }}
.metric-row {{ display: flex; justify-content: space-between; padding: 4px 0; }}
.metric-key {{ font-size: 0.78rem; color: {C_SUB}; }}
.metric-val {{ font-size: 0.84rem; font-weight: 600; color: {C_TEXT}; }}

/* ── Streamlit 오버라이드 ── */
div[data-testid="stMetricValue"] {{ font-size: 1.4rem !important; font-weight: 700 !important; }}
div[data-testid="stMetricLabel"] {{ font-size: 0.75rem !important; color: {C_SUB} !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; background: transparent; }}
.stTabs [data-baseweb="tab"] {{
    padding: 8px 18px; font-weight: 600; font-size: 0.82rem;
    border-radius: 8px 8px 0 0;
}}
hr {{ border-color: {C_BORDER}; margin: 1rem 0; }}
.stExpander {{ border: 1px solid {C_BORDER} !important; border-radius: 10px !important; }}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {{
    background: {C_CARD2} !important;
    border-color: {C_BORDER2} !important;
}}
</style>""", unsafe_allow_html=True)

# ─── Constants ───
SEASON_PRESETS = {
    "kr":     {"label": "🇰🇷 한국형",  "data": [1.3,1.0,0.9,0.85,0.9,0.8,0.95,1.1,0.9,0.95,1.0,1.5]},
    "global": {"label": "🌏 글로벌형", "data": [0.9,0.85,0.9,0.85,0.9,1.0,1.15,1.1,0.95,0.9,1.2,1.4]},
    "flat":   {"label": "➖ 플랫",      "data": [1,1,1,1,1,1,1,1,1,1,1,1]},
}

def get_all_presets(proj):
    """기본 프리셋 + 프로젝트 커스텀 프리셋 합치기"""
    custom = proj.get("custom_season_presets", [])
    if isinstance(custom, str):
        try: custom = json.loads(custom)
        except: custom = []
    merged = dict(SEASON_PRESETS)
    for cp in custom:
        merged[cp["id"]] = {"label": cp["label"], "data": cp["data"]}
    return merged

def get_safe_preset_index(presets, key, fallback_key):
    """프리셋 키가 없을 때 안전하게 fallback"""
    keys = list(presets.keys())
    if key in keys: return keys.index(key)
    if fallback_key in keys: return keys.index(fallback_key)
    return 0
DEFAULT_BONUS = [
    {"id":"season",       "label":"시즌",     "value":0.3,   "icon":"🎊"},
    {"id":"content",      "label":"콘텐츠",   "value":0.25,  "icon":"🎮"},
    {"id":"major_update", "label":"대규모UP", "value":0.4,   "icon":"🔥"},
    {"id":"bm",           "label":"BM",       "value":0.2,   "icon":"💎"},
    {"id":"marketing",    "label":"마케팅",   "value":0.2,   "icon":"📢"},
    {"id":"vacation",     "label":"방학",     "value":0.15,  "icon":"🏖️"},
    {"id":"holiday",      "label":"연휴",     "value":0.15,  "icon":"📅"},
    {"id":"compete",      "label":"경쟁작",   "value":-0.15, "icon":"⚔️"},
    {"id":"feature",      "label":"피처링",   "value":0.2,   "icon":"⭐"},
]

# ─── Helpers ───
def gen_months(sy, sm, ey, em):
    ms = []; y, m, i = sy, sm, 0
    while y < ey or (y == ey and m <= em):
        ms.append({"idx": i, "year": y, "month": m,
                   "days": calendar.monthrange(y, m)[1],
                   "label": f"{y}.{m:02d}", "short": f"{str(y)[2:]}.{m:02d}"})
        i += 1; m += 1
        if m > 12: m = 1; y += 1
    return ms

def year_groups(months):
    g = {}
    for mo in months:
        k = str(mo["year"])
        if k not in g: g[k] = []
        g[k].append(mo["idx"]); mo["cy"] = k
    return g

def dc(i, rate): return math.pow(1 - rate / 100, i)
def fmt(v):
    if abs(v) >= 1e8: return f"{v/1e8:.1f}억"
    if abs(v) >= 1e4: return f"{v/1e4:.0f}만"
    return f"{v:,.0f}"
def fmtn(v):
    if abs(v) >= 1e4: return f"{v/1e4:.1f}만"
    return f"{v:,.0f}"
def season_color(v):
    if v >= 1.3: return C_GREEN
    if v >= 1.1: return C_TEAL
    if v <= 0.7: return C_RED
    if v <= 0.9: return C_AMBER
    return C_SUB
def weight_class(v):
    if v >= 1.5: return "high"
    if v <= 0.7: return "low"
    return ""

# ─── DB ───
def get_config():
    r = sb.table("app_config").select("*").eq("id", "main").execute()
    return r.data[0] if r.data else {"master_password": "1234"}

def get_projects():
    return sb.table("projects").select("*").order("created_at").execute().data or []

def get_project(pid):
    r = sb.table("projects").select("*").eq("id", pid).execute()
    return r.data[0] if r.data else None

def create_project(name, pw, genre="", market=""):
    r = sb.table("projects").insert({"name": name, "password": pw, "genre": genre, "market": market}).execute()
    if r.data:
        pid = r.data[0]["id"]
        for y in [2026, 2027, 2028, 2029]:
            sb.table("yearly_targets").insert({"project_id": pid, "year": y,
                "target_kr": 50000000000, "target_global": 20000000000}).execute()
        return pid
    return None

def update_proj(pid, data):
    sb.table("projects").update({**data, "updated_at": datetime.now().isoformat()}).eq("id", pid).execute()

def get_targets(pid):
    r = sb.table("yearly_targets").select("*").eq("project_id", pid).order("year").execute()
    return {str(t["year"]): {"kr": t["target_kr"], "global": t["target_global"]} for t in (r.data or [])}

def upsert_target(pid, year, kr, gl):
    sb.table("yearly_targets").upsert(
        {"project_id": pid, "year": year, "target_kr": kr, "target_global": gl},
        on_conflict="project_id,year").execute()

def get_monthly(pid):
    r = sb.table("monthly_data").select("*").eq("project_id", pid).execute()
    return {d["month_index"]: d for d in (r.data or [])}

def save_monthly(pid, idx, adj=0, bonuses=None, pr=5.0, ar=70000):
    sb.table("monthly_data").upsert(
        {"project_id": pid, "month_index": idx, "manual_adj": adj,
         "bonuses": json.dumps(bonuses or {}), "p_rate": pr, "arppu": ar},
        on_conflict="project_id,month_index").execute()

# ─── Plotly Theme ───
def styled_layout(**kwargs):
    base = dict(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(family="Noto Sans KR, sans-serif", color=C_TEXT, size=12),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11, color=C_SUB)),
        xaxis=dict(type="category", tickangle=-45,
                   tickfont=dict(size=10, color=C_SUB),
                   gridcolor="rgba(148,163,184,0.06)"),
        yaxis=dict(tickfont=dict(size=10, color=C_SUB),
                   gridcolor="rgba(148,163,184,0.06)"),
    )
    base.update(kwargs)
    return base

# ─── KPI HTML ───
def kpi_card(icon, label, value, sub="", color=C_BLUE):
    return f"""<div class="kpi-card" style="--accent:{color};">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color};">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

# ─── Session ───
for k, v in [("logged_in", False), ("cur_proj", None), ("admin", False)]:
    if k not in st.session_state: st.session_state[k] = v

# ═══════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════
if not st.session_state.logged_in:
    cfg = get_config()
    _, c, _ = st.columns([1, 1.4, 1])
    with c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="page-title" style="text-align:center;font-size:2.4rem;">🚀 매출 시뮬레이터</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="page-meta" style="text-align:center;font-size:0.9rem;">프로젝트별 매출 목표 시뮬레이션</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            pw = st.text_input("🔒 비밀번호", type="password", key="lpw")
            if st.button("로그인", type="primary", use_container_width=True):
                if pw == cfg.get("master_password", "1234"):
                    st.session_state.logged_in = True; st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
    st.stop()

# ═══════════════════════════════════════════════════
# PROJECT LIST
# ═══════════════════════════════════════════════════
if st.session_state.cur_proj is None:
    st.markdown('<div class="page-title">🚀 매출 시뮬레이터</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-meta">프로젝트를 선택하거나 새로 만드세요.</div>', unsafe_allow_html=True)
    st.markdown("---")
    projects = get_projects()

    with st.expander("➕ 새 프로젝트 만들기", expanded=len(projects) == 0):
        c1, c2 = st.columns(2)
        with c1: nn = st.text_input("프로젝트명", placeholder="예: 프로젝트A")
        with c2: npw = st.text_input("비밀번호", type="password", placeholder="관리자용")
        c3, c4 = st.columns(2)
        with c3: ng = st.text_input("장르", placeholder="방치형 RPG")
        with c4: nm = st.text_input("시장", placeholder="한국/글로벌")
        if st.button("✅ 프로젝트 생성", type="primary"):
            if nn and npw:
                pid = create_project(nn, npw, ng, nm)
                if pid: st.session_state.cur_proj = pid; st.rerun()
            else: st.warning("프로젝트명/비밀번호 필수")

    st.markdown("---")
    if projects:
        cols = st.columns(min(len(projects), 3))
        for i, p in enumerate(projects):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"### {p['name']}")
                    meta = []
                    if p.get("genre"): meta.append(f"🎮 {p['genre']}")
                    if p.get("market"): meta.append(f"🌍 {p['market']}")
                    meta.append(f"📆 {p['start_year']}.{p['start_month']:02d}~{p['end_year']}.{p['end_month']:02d}")
                    st.caption(" · ".join(meta))
                    if st.button("📂 열기", key=f"o_{p['id']}", use_container_width=True):
                        st.session_state.cur_proj = p["id"]
                        st.session_state.admin = False; st.rerun()
    else:
        st.info("프로젝트가 없습니다. 위에서 새로 만들어주세요.")

    st.markdown("---")
    col_pw, col_logout = st.columns([3, 1])
    with col_pw:
        with st.expander("🔧 공통 비밀번호 변경"):
            cfg = get_config()
            cur_pw  = st.text_input("현재 비밀번호", type="password", key="cur_mpw")
            new_pw  = st.text_input("새 비밀번호",   type="password", key="new_mpw")
            new_pw2 = st.text_input("새 비밀번호 확인", type="password", key="new_mpw2")
            if st.button("비밀번호 변경", key="chg_mpw"):
                if cur_pw != cfg.get("master_password", "1234"):
                    st.error("현재 비밀번호가 틀렸습니다.")
                elif not new_pw or len(new_pw) < 4:
                    st.warning("새 비밀번호는 4자 이상 입력하세요.")
                elif new_pw != new_pw2:
                    st.error("새 비밀번호가 일치하지 않습니다.")
                else:
                    sb.table("app_config").update({"master_password": new_pw}).eq("id", "main").execute()
                    st.success("✅ 비밀번호가 변경되었습니다.")
    with col_logout:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()
    st.stop()

# ═══════════════════════════════════════════════════
# SIMULATOR — 공통 데이터 로드
# ═══════════════════════════════════════════════════
proj = get_project(st.session_state.cur_proj)
if not proj:
    st.error("프로젝트를 찾을 수 없습니다.")
    st.session_state.cur_proj = None; st.rerun()

pid = proj["id"]
adm = st.session_state.admin

sy, sm, ey, em = proj["start_year"], proj["start_month"], proj["end_year"], proj["end_month"]
months = gen_months(sy, sm, ey, em)
N = len(months)
yg = year_groups(months)
yls = list(yg.keys())
targets = get_targets(pid)
mdb = get_monthly(pid)

dkr  = float(proj.get("decay_kr", 4.0) or 4.0)
dgl  = float(proj.get("decay_global", 3.0) or 3.0)
bkr  = float(proj.get("launch_boost_kr", 0.5) or 0.5)
bgl  = float(proj.get("launch_boost_global", 0.3) or 0.3)
skr  = proj.get("season_kr", SEASON_PRESETS["kr"]["data"])
sgl  = proj.get("season_global", SEASON_PRESETS["global"]["data"])
if isinstance(skr, str): skr = json.loads(skr)
if isinstance(sgl, str): sgl = json.loads(sgl)
dau_cap = int(proj.get("dau_cap", 1000000) or 1000000)
ccats = proj.get("custom_bonus_cats", [])
if isinstance(ccats, str): ccats = json.loads(ccats)
all_cats = DEFAULT_BONUS + ccats

# ─── 계산 ───
rows = []
for mo in months:
    i = mo["idx"]; md = mdb.get(i, {})
    d_kr = dc(i, dkr); d_gl = dc(i, dgl)
    s_kr = float(skr[mo["month"]-1]) if mo["month"]-1 < len(skr) else 1.0
    s_gl = float(sgl[mo["month"]-1]) if mo["month"]-1 < len(sgl) else 1.0
    lb_kr = bkr if i < 3 else 0; lb_gl = bgl if i < 3 else 0
    bw_kr = max(0.05, round(d_kr*s_kr + lb_kr, 4))
    bw_gl = max(0.05, round(d_gl*s_gl + lb_gl, 4))
    manual = float(md.get("manual_adj", 0) or 0)
    bn = md.get("bonuses", "{}")
    if isinstance(bn, str): bn = json.loads(bn)
    bns = sum(float(c["value"]) for c in all_cats if bn.get(c["id"]))
    fw_kr = max(0.1, bw_kr + manual + bns)
    fw_gl = max(0.1, bw_gl + manual + bns)
    pr = float(md.get("p_rate", 5.0) or 5.0)
    ar = int(md.get("arppu", 70000) or 70000)
    arpdau = ar * (pr / 100)
    rows.append({**mo, "bw_kr": bw_kr, "bw_gl": bw_gl,
                 "manual": manual, "bn": bn, "bns": bns,
                 "fw_kr": fw_kr, "fw_gl": fw_gl,
                 "pr": pr, "ar": ar, "arpdau": arpdau})

for yl, idxs in yg.items():
    t = targets.get(yl, {"kr": 0, "global": 0})
    tw_kr = sum(rows[j]["fw_kr"] for j in idxs) or 1
    tw_gl = sum(rows[j]["fw_gl"] for j in idxs) or 1
    for j in idxs:
        r = rows[j]
        r["rkr"] = (t.get("kr", 0) or 0) * (r["fw_kr"] / tw_kr)
        r["rgl"] = (t.get("global", 0) or 0) * (r["fw_gl"] / tw_gl)
        r["rev"] = r["rkr"] + r["rgl"]
        r["dau"]    = r["rev"]  / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["dau_kr"] = r["rkr"]  / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["dau_gl"] = r["rgl"]  / (r["days"] * r["arpdau"]) if r["arpdau"] > 0 else 0
        r["over"]   = r["dau"] > dau_cap

# ═══════════════════════════════════════════════════
# SHARED HEADER (공통)
# ═══════════════════════════════════════════════════
if st.button("← 프로젝트 목록"):
    st.session_state.cur_proj = None; st.session_state.admin = False; st.rerun()

# 프로젝트명
if adm:
    nt = st.text_input("프로젝트명 수정", value=proj["name"], key="pt", label_visibility="collapsed")
    if nt != proj["name"]: update_proj(pid, {"name": nt})
    proj_name = nt
else:
    proj_name = proj["name"]

st.markdown(f'<div class="page-title">🚀 {proj_name}</div>', unsafe_allow_html=True)
nfo = []
if proj.get("genre"):  nfo.append(f"🎮 {proj['genre']}")
if proj.get("market"): nfo.append(f"🌍 {proj['market']}")
nfo.append(f"📆 {proj['start_year']}.{proj['start_month']:02d} ~ {proj['end_year']}.{proj['end_month']:02d}")
st.markdown(f'<div class="page-meta">{"<span>·</span>".join(nfo)}</div>', unsafe_allow_html=True)

# 모드 배지 + 비밀번호
hc1, hc2 = st.columns([4, 2])
with hc1:
    if adm:
        st.markdown('<div class="badge-admin">🔓 관리자 모드</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-view">👁️ 뷰 모드</div>', unsafe_allow_html=True)
with hc2:
    if adm:
        if st.button("🔒 잠금", use_container_width=True):
            st.session_state.admin = False; st.rerun()
    else:
        upw = st.text_input("비밀번호", type="password", key="upw",
                            label_visibility="collapsed", placeholder="관리자 비밀번호 입력")
        if upw:
            if upw == proj.get("password", ""): st.session_state.admin = True; st.rerun()
            else: st.error("비밀번호 오류")

st.markdown("---")

# 기간 설정 (관리자만)
if adm:
    with st.expander("📆 시뮬레이션 기간 설정"):
        p1, p2, p3, p4 = st.columns(4)
        with p1: nsy = st.number_input("시작 연도", 2024, 2035, sy, key="nsy")
        with p2: nsm = st.selectbox("시작 월", range(1, 13), index=sm-1, key="nsm")
        with p3: ney = st.number_input("종료 연도", 2024, 2035, ey, key="ney")
        with p4: nem = st.selectbox("종료 월", range(1, 13), index=em-1, key="nem")
        if st.button("기간 저장", type="primary"):
            update_proj(pid, {"start_year": nsy, "start_month": nsm,
                              "end_year": ney, "end_month": nem}); st.rerun()

# 권역 토글
rv_l = st.radio("권역", ["🌐 통합", "🇰🇷 한국", "🌏 글로벌"],
                horizontal=True, label_visibility="collapsed")
rv = "total" if "통합" in rv_l else ("kr" if "한국" in rv_l else "global")
rf = "rkr" if rv == "kr" else "rgl" if rv == "global" else "rev"
dn = "dau_kr" if rv == "kr" else "dau_gl" if rv == "global" else "dau"

# ─── KPI ───
tt = sum(
    (t.get("kr", 0) or 0) + (t.get("global", 0) or 0) if rv == "total"
    else (t.get("kr", 0) or 0) if rv == "kr"
    else (t.get("global", 0) or 0)
    for t in targets.values()
)
ad = sum(r["dau"] for r in rows) / N if N > 0 else 0
ap = sum(r["pr"] for r in rows) / N if N > 0 else 0
aa = sum(r["ar"] for r in rows) / N if N > 0 else 0
oc = sum(1 for r in rows if r["over"])

kpi_cols = st.columns(5)
kpi_data = [
    ("📊", "목표 매출",      fmt(tt),       f"{len(yls)}개년 합계",        C_BLUE),
    ("👥", "평균 필요 DAU",  fmtn(ad),      f"상한 {fmtn(dau_cap)}",       C_RED if oc > 0 else C_GREEN),
    ("💰", "평균 결제율",    f"{ap:.1f}%",  "전체 기간",                   C_PURPLE),
    ("💎", "평균 ARPPU",     fmt(aa),       "전체 기간",                   C_AMBER),
    ("⚠️" if oc > 0 else "✅",
     "DAU 초과" if oc > 0 else "DAU 상태",
     f"{oc}개월" if oc > 0 else "정상",
     "상한선 초과" if oc > 0 else "초과 없음",
     C_RED if oc > 0 else C_GREEN),
]
for col, (icon, label, val, sub, color) in zip(kpi_cols, kpi_data):
    with col:
        st.markdown(kpi_card(icon, label, val, sub, color), unsafe_allow_html=True)

st.markdown("")

# DAU 상한 (관리자)
if adm:
    dc1, dc2, dc3 = st.columns([1.5, 6, 1])
    with dc1: st.markdown(f"🚨 **DAU 상한**")
    with dc2:
        ncap = st.slider("DAU", min_value=50000, max_value=3000000,
                         value=dau_cap, step=50000, key="dcap",
                         label_visibility="collapsed")
    with dc3: st.markdown(f"**{fmtn(dau_cap)}**")
    if ncap != dau_cap: update_proj(pid, {"dau_cap": ncap})

# ─── 메인 차트 ───
xl = [r["label"] for r in rows]
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(
    x=xl, y=[r[rf] for r in rows], name="매출",
    marker_color=[C_RED if r["over"] else C_BLUE for r in rows],
    opacity=0.75), secondary_y=False)
fig.add_trace(go.Scatter(
    x=xl, y=[r[dn] for r in rows], name="필요 DAU",
    line=dict(color=C_AMBER, width=2.5)), secondary_y=True)
fig.add_trace(go.Scatter(
    x=xl, y=[dau_cap] * N, name="DAU 상한선",
    line=dict(color=C_RED, width=1.5, dash="dash")), secondary_y=True)
fig.update_layout(**styled_layout(height=360, margin=dict(t=30, b=50)))
fig.update_yaxes(title_text="매출", secondary_y=False,
                 title_font=dict(size=11, color=C_SUB))
fig.update_yaxes(title_text="DAU",  secondary_y=True,
                 title_font=dict(size=11, color=C_SUB))
st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════
t_tgt, t_cv, t_wt, t_mt, t_dt = st.tabs(["📊 목표", "📈 커브", "⚖️ 가중치", "⚙️ 지표", "📋 데이터"])

# ══════════════════════════
# TAB 1 — 목표
# ══════════════════════════
with t_tgt:
    st.subheader("연도별 매출 목표")

    if adm:
        # ── 관리자 뷰 ──
        cols = st.columns(len(yls))
        for ci, yl in enumerate(yls):
            with cols[ci]:
                with st.container(border=True):
                    t = targets.get(yl, {"kr": 0, "global": 0})
                    idxs = yg[yl]
                    st.markdown(f"**{yl}년**")
                    st.caption(f"{months[idxs[0]]['label']} ~ {months[idxs[-1]]['label']} ({len(idxs)}개월)")
                    kv = st.text_input("🇰🇷 한국",  value=str(int(t.get("kr", 0) or 0)), key=f"tk_{yl}")
                    gv = st.text_input("🌏 글로벌", value=str(int(t.get("global", 0) or 0)), key=f"tg_{yl}")
                    try:
                        ki, gi = int(kv), int(gv)
                        if ki != (t.get("kr", 0) or 0) or gi != (t.get("global", 0) or 0):
                            upsert_target(pid, int(yl), ki, gi)
                    except: pass
                    st.markdown("---")
                    total_yr = (t.get("kr", 0) or 0) + (t.get("global", 0) or 0)
                    st.markdown(f"**합계: {fmt(total_yr)}**")
    else:
        # ── 뷰 모드 ──
        cols = st.columns(len(yls))
        for ci, yl in enumerate(yls):
            with cols[ci]:
                t = targets.get(yl, {"kr": 0, "global": 0})
                idxs = yg[yl]
                kr_v  = t.get("kr", 0) or 0
                gl_v  = t.get("global", 0) or 0
                tot_v = kr_v + gl_v
                st.markdown(f"""<div class="target-card">
                    <div class="target-year">{yl}년</div>
                    <div style="font-size:0.72rem;color:{C_MUTED};margin-bottom:10px;">
                        {months[idxs[0]]['label']} ~ {months[idxs[-1]]['label']} · {len(idxs)}개월
                    </div>
                    <div class="target-region">🇰🇷 한국</div>
                    <div class="target-amount" style="color:{C_BLUE};">{fmt(kr_v)}</div>
                    <div class="target-region">🌏 글로벌</div>
                    <div class="target-amount" style="color:{C_PURPLE};">{fmt(gl_v)}</div>
                    <hr class="target-divider">
                    <div class="target-total-label">합계</div>
                    <div class="target-total">{fmt(tot_v)}</div>
                </div>""", unsafe_allow_html=True)

    # 연도별 매출 바 차트 (공통)
    st.markdown("")
    yf = go.Figure()
    yr_kr  = [(targets.get(yl, {}).get("kr", 0) or 0) for yl in yls]
    yr_gl  = [(targets.get(yl, {}).get("global", 0) or 0) for yl in yls]
    yf.add_trace(go.Bar(x=yls, y=yr_kr, name="한국",   marker_color=C_BLUE,   opacity=0.8))
    yf.add_trace(go.Bar(x=yls, y=yr_gl, name="글로벌", marker_color=C_PURPLE, opacity=0.8))
    yf.update_layout(**styled_layout(height=240, barmode="group", margin=dict(t=20, b=40)))
    st.plotly_chart(yf, use_container_width=True)

# ══════════════════════════
# TAB 2 — 커브
# ══════════════════════════
with t_cv:
    st.subheader("자연감소 커브 × 시즌 계수")
    st.caption("기본 가중치 = 감소커브 × 시즌계수 + 론칭부스트")

    cc1, cc2 = st.columns(2)

    if adm:
        # 프리셋 목록 (기본 + 커스텀)
        all_presets = get_all_presets(proj)
        preset_keys   = list(all_presets.keys())
        preset_labels = [all_presets[k]["label"] for k in preset_keys]

        # ── 관리자 뷰 ──
        with cc1:
            with st.container(border=True):
                st.markdown("**🇰🇷 한국**")
                ndkr = st.slider("감소율 (%/월)", 0.0, 15.0, dkr, 0.5, key="ndkr", format="%.1f%%")
                nbkr = st.slider("론칭 부스트",   0.0, 2.0,  bkr, 0.1, key="nbkr")
                cur_spkr = proj.get("season_preset_kr", "kr")
                spkr_idx = get_safe_preset_index(all_presets, cur_spkr, "kr")
                spkr = st.selectbox("시즌 프리셋 (한국)", preset_keys,
                    format_func=lambda x: all_presets[x]["label"],
                    index=spkr_idx, key="spkr")
                if ndkr != dkr or nbkr != bkr:
                    update_proj(pid, {"decay_kr": ndkr, "launch_boost_kr": nbkr})
                if spkr != cur_spkr:
                    update_proj(pid, {
                        "season_preset_kr": spkr,
                        "season_kr": json.dumps(all_presets[spkr]["data"])
                    }); st.rerun()

        with cc2:
            with st.container(border=True):
                st.markdown("**🌏 글로벌**")
                ndgl = st.slider("감소율 (%/월)", 0.0, 15.0, dgl, 0.5, key="ndgl", format="%.1f%%")
                nbgl = st.slider("론칭 부스트",   0.0, 2.0,  bgl, 0.1, key="nbgl")
                cur_spgl = proj.get("season_preset_global", "global")
                spgl_idx = get_safe_preset_index(all_presets, cur_spgl, "global")
                spgl = st.selectbox("시즌 프리셋 (글로벌)", preset_keys,
                    format_func=lambda x: all_presets[x]["label"],
                    index=spgl_idx, key="spgl")
                if ndgl != dgl or nbgl != bgl:
                    update_proj(pid, {"decay_global": ndgl, "launch_boost_global": nbgl})
                if spgl != cur_spgl:
                    update_proj(pid, {
                        "season_preset_global": spgl,
                        "season_global": json.dumps(all_presets[spgl]["data"])
                    }); st.rerun()

        # ── 커스텀 프리셋 관리 ──
        with st.expander("⭐ 커스텀 프리셋 관리"):
            custom_presets = proj.get("custom_season_presets", [])
            if isinstance(custom_presets, str):
                try: custom_presets = json.loads(custom_presets)
                except: custom_presets = []

            # 기존 커스텀 프리셋 목록 + 삭제
            if custom_presets:
                st.markdown("**저장된 커스텀 프리셋**")
                for cp in custom_presets:
                    cp_c1, cp_c2 = st.columns([5, 1])
                    with cp_c1:
                        st.markdown(f"**{cp['label']}** — {', '.join(f'{v:.2f}' for v in cp['data'])}")
                    with cp_c2:
                        if st.button("🗑️", key=f"del_preset_{cp['id']}"):
                            new_customs = [x for x in custom_presets if x["id"] != cp["id"]]
                            update_proj(pid, {"custom_season_presets": json.dumps(new_customs)})
                            # 삭제된 프리셋을 쓰고 있으면 기본값으로 복구
                            reset_data = {}
                            if proj.get("season_preset_kr") == cp["id"]:
                                reset_data["season_preset_kr"] = "kr"
                                reset_data["season_kr"] = json.dumps(SEASON_PRESETS["kr"]["data"])
                            if proj.get("season_preset_global") == cp["id"]:
                                reset_data["season_preset_global"] = "global"
                                reset_data["season_global"] = json.dumps(SEASON_PRESETS["global"]["data"])
                            if reset_data: update_proj(pid, reset_data)
                            st.rerun()
                st.markdown("---")

            # 새 프리셋 저장 — 현재 시즌 계수에서
            st.markdown("**현재 시즌 계수로 새 프리셋 저장**")
            st.caption("아래에서 먼저 계수를 조정한 후 이름을 입력하고 저장하세요.")
            np_src = st.radio("기준 권역", ["한국", "글로벌"], horizontal=True, key="np_src")
            np_name = st.text_input("프리셋 이름", key="np_name", placeholder="예: 여름 이벤트형")
            if st.button("💾 프리셋 저장", key="save_preset"):
                if np_name.strip():
                    base_data = list(skr) if np_src == "한국" else list(sgl)
                    new_id = f"custom_{int(datetime.now().timestamp())}"
                    new_preset = {"id": new_id, "label": f"✨ {np_name.strip()}", "data": base_data}
                    updated = custom_presets + [new_preset]
                    update_proj(pid, {"custom_season_presets": json.dumps(updated)})
                    st.success(f"✅ '{np_name}' 저장 완료!")
                    st.rerun()
                else:
                    st.warning("프리셋 이름을 입력해주세요.")

        # ── 시즌 계수 직접 수정 ──
        with st.expander("🔧 시즌 계수 직접 수정"):
            ser = st.radio("권역", ["한국", "글로벌"], horizontal=True, key="ser")
            sd = list(skr) if ser == "한국" else list(sgl); ch = False
            sc = st.columns(6)
            for mi in range(12):
                with sc[mi % 6]:
                    nv = st.number_input(f"{mi+1}월", 0.1, 3.0, float(sd[mi]), 0.05, key=f"se_{ser}_{mi}")
                    if nv != sd[mi]: sd[mi] = nv; ch = True
            if ch:
                update_proj(pid, {"season_kr" if ser == "한국" else "season_global": json.dumps(sd)})

    else:
        # ── 뷰 모드 ──
        all_presets_view = get_all_presets(proj)
        with cc1:
            spkr_label = all_presets_view.get(proj.get("season_preset_kr", "kr"), {}).get("label", "—")
            st.markdown(f"""<div class="card">
                <div style="font-size:0.95rem;font-weight:700;margin-bottom:12px;">🇰🇷 한국</div>
                <div class="param-row">
                    <span class="param-label">감소율</span>
                    <span class="param-value" style="color:{C_AMBER};">{dkr}%/월</span>
                </div>
                <div class="param-row">
                    <span class="param-label">론칭 부스트</span>
                    <span class="param-value" style="color:{C_GREEN};">+{bkr}</span>
                </div>
                <div class="param-row">
                    <span class="param-label">시즌 프리셋</span>
                    <span class="param-value">{spkr_label}</span>
                </div>
                <div style="font-size:0.78rem;color:{C_SUB};margin-top:12px;margin-bottom:6px;">월별 시즌 계수</div>
                <div class="season-grid">
                    {"".join(f'<div class="season-cell"><div class="season-month">{i+1}월</div><div class="season-val" style="color:{season_color(float(skr[i]))}">{float(skr[i]):.2f}</div></div>' for i in range(12))}
                </div>
            </div>""", unsafe_allow_html=True)
        with cc2:
            spgl_label = all_presets_view.get(proj.get("season_preset_global", "global"), {}).get("label", "—")
            st.markdown(f"""<div class="card">
                <div style="font-size:0.95rem;font-weight:700;margin-bottom:12px;">🌏 글로벌</div>
                <div class="param-row">
                    <span class="param-label">감소율</span>
                    <span class="param-value" style="color:{C_AMBER};">{dgl}%/월</span>
                </div>
                <div class="param-row">
                    <span class="param-label">론칭 부스트</span>
                    <span class="param-value" style="color:{C_GREEN};">+{bgl}</span>
                </div>
                <div class="param-row">
                    <span class="param-label">시즌 프리셋</span>
                    <span class="param-value">{spgl_label}</span>
                </div>
                <div style="font-size:0.78rem;color:{C_SUB};margin-top:12px;margin-bottom:6px;">월별 시즌 계수</div>
                <div class="season-grid">
                    {"".join(f'<div class="season-cell"><div class="season-month">{i+1}월</div><div class="season-val" style="color:{season_color(float(sgl[i]))}">{float(sgl[i]):.2f}</div></div>' for i in range(12))}
                </div>
            </div>""", unsafe_allow_html=True)

    # 커브 프리뷰 (공통)
    st.markdown(""); st.markdown("**📈 커브 프리뷰**")
    cf = go.Figure()
    cf.add_trace(go.Scatter(x=xl, y=[r["bw_kr"] for r in rows], name="한국",
        line=dict(color=C_BLUE, width=2.5), fill="tozeroy", fillcolor="rgba(59,130,246,0.08)"))
    cf.add_trace(go.Scatter(x=xl, y=[r["bw_gl"] for r in rows], name="글로벌",
        line=dict(color=C_PURPLE, width=2.5), fill="tozeroy", fillcolor="rgba(139,92,246,0.08)"))
    cf.update_layout(**styled_layout(height=220, margin=dict(t=20, b=50)))
    st.plotly_chart(cf, use_container_width=True)

# ══════════════════════════
# TAB 3 — 가중치
# ══════════════════════════
with t_wt:
    st.subheader("월별 가중치 조정")
    st.caption("자동 가중치 + 보너스 = 최종 가중치")

    # 보너스 항목 목록
    with st.expander("📋 보너스 항목 목록"):
        bcols = st.columns(3)
        for bi, c in enumerate(all_cats):
            with bcols[bi % 3]:
                s = "+" if c["value"] > 0 else ""
                st.caption(f"{c['icon']} **{c['label']}** ({s}{c['value']})")
        if adm:
            st.markdown("---")
            a1, a2 = st.columns([3, 2])
            with a1: cn = st.text_input("항목명", key="cbn", placeholder="새 항목 이름")
            with a2: cv = st.number_input("배율", -1.0, 2.0, 0.2, 0.05, key="cbv")
            if st.button("➕ 추가", key="cba") and cn:
                nc = ccats + [{"id": f"c_{int(datetime.now().timestamp())}", "label": cn, "value": cv, "icon": "🏷️"}]
                update_proj(pid, {"custom_bonus_cats": json.dumps(nc)}); st.rerun()

    for yl in yls:
        idxs = yg[yl]
        with st.expander(f"**{yl}년** ({months[idxs[0]]['label']} ~ {months[idxs[-1]]['label']})", expanded=(yl == yls[0])):
            if adm:
                # ── 관리자: 체크박스 ──
                for idx in idxs:
                    r = rows[idx]
                    col_info, col_bonus, col_result = st.columns([2, 6, 1])
                    with col_info:
                        st.markdown(f"**{r['short']}**")
                        st.caption(f"KR:{r['bw_kr']:.2f} GL:{r['bw_gl']:.2f}")
                    with col_bonus:
                        bn = dict(r["bn"]); bc = st.columns(len(all_cats)); chg = False
                        for bi2, cat in enumerate(all_cats):
                            with bc[bi2]:
                                act = bn.get(cat["id"], False)
                                nv = st.checkbox(cat["icon"], value=act, key=f"b_{idx}_{cat['id']}")
                                if nv != act: bn[cat["id"]] = nv; chg = True
                        if chg: save_monthly(pid, idx, r["manual"], bn, r["pr"], r["ar"])
                    with col_result:
                        color = C_GREEN if r["fw_kr"] >= 1.5 else C_RED if r["fw_kr"] < 0.7 else C_TEXT
                        st.markdown(f"<div style='text-align:right;font-weight:700;font-size:1.1rem;color:{color};padding-top:8px;'>{r['fw_kr']:.2f}</div>", unsafe_allow_html=True)
            else:
                # ── 뷰 모드: 배지 레이아웃 ──
                html_rows = ""
                for idx in idxs:
                    r = rows[idx]
                    wc = weight_class(r["fw_kr"])
                    # 활성 보너스 배지
                    badges = ""
                    for cat in all_cats:
                        if r["bn"].get(cat["id"]):
                            neg = "neg" if cat["value"] < 0 else ""
                            s = "+" if cat["value"] > 0 else ""
                            badges += f'<span class="bonus-badge {neg}">{cat["icon"]} {cat["label"]} {s}{cat["value"]}</span>'
                    if not badges:
                        badges = f'<span style="font-size:0.75rem;color:{C_MUTED};">보너스 없음</span>'

                    html_rows += f"""<div class="month-row">
                        <div class="month-label">{r['short']}</div>
                        <div class="month-weight {wc}">{r['fw_kr']:.2f}</div>
                        <div class="month-bonuses">{badges}</div>
                        <div class="month-metrics">
                            KR {r['bw_kr']:.2f} · GL {r['bw_gl']:.2f}<br>
                            <span style="color:{C_AMBER};">보너스 {'+' if r['bns']>=0 else ''}{r['bns']:.2f}</span>
                        </div>
                    </div>"""
                st.markdown(html_rows, unsafe_allow_html=True)

# ══════════════════════════
# TAB 4 — 지표
# ══════════════════════════
with t_mt:
    st.subheader("P.rate / ARPPU")

    if adm:
        # ── 관리자: 일괄 적용 ──
        with st.expander("⚡ 일괄 적용"):
            b1, b2 = st.columns(2)
            with b1:
                bpr  = st.number_input("P.rate(%)", 0.1, 20.0, 5.0, 0.1, key="bpr")
                bpry = st.selectbox("적용 연도", yls, key="bpry")
                if st.button("P.rate 적용", key="bpra"):
                    for j in yg[bpry]:
                        md2 = mdb.get(j, {}); bn2 = md2.get("bonuses", "{}")
                        if isinstance(bn2, str): bn2 = json.loads(bn2)
                        save_monthly(pid, j, float(md2.get("manual_adj", 0) or 0), bn2, bpr, int(md2.get("arppu", 70000) or 70000))
                    st.rerun()
            with b2:
                bar  = st.number_input("ARPPU(원)", 10000, 500000, 70000, 1000, key="bar")
                bary = st.selectbox("적용 연도", yls, key="bary")
                if st.button("ARPPU 적용", key="bara"):
                    for j in yg[bary]:
                        md2 = mdb.get(j, {}); bn2 = md2.get("bonuses", "{}")
                        if isinstance(bn2, str): bn2 = json.loads(bn2)
                        save_monthly(pid, j, float(md2.get("manual_adj", 0) or 0), bn2, float(md2.get("p_rate", 5.0) or 5.0), bar)
                    st.rerun()

        for rs in range(0, N, 4):
            cols = st.columns(4)
            for ci in range(4):
                idx = rs + ci
                if idx >= N: break
                r = rows[idx]
                with cols[ci]:
                    with st.container(border=True):
                        st.markdown(f"**{r['short']}**")
                        if r["over"]: st.error(f"DAU {fmtn(r['dau'])} ⚠️")
                        else: st.caption(f"DAU {fmtn(r['dau'])}")
                        npr = st.slider("P.rate", 0.1, 20.0, float(r["pr"]), 0.1, key=f"pr_{idx}")
                        nar = st.slider("ARPPU",  10000, 500000, int(r["ar"]), 1000, key=f"ar_{idx}")
                        if npr != r["pr"] or nar != r["ar"]:
                            save_monthly(pid, idx, r["manual"], r["bn"], npr, nar)
    else:
        # ── 뷰 모드: 카드 그리드 ──
        # P.rate / ARPPU 추이 차트
        pf = make_subplots(specs=[[{"secondary_y": True}]])
        pf.add_trace(go.Scatter(x=xl, y=[r["pr"] for r in rows], name="P.rate(%)",
            line=dict(color=C_PURPLE, width=2.5)), secondary_y=False)
        pf.add_trace(go.Bar(x=xl, y=[r["ar"] for r in rows], name="ARPPU(원)",
            marker_color=C_AMBER, opacity=0.6), secondary_y=True)
        pf.update_layout(**styled_layout(height=240, margin=dict(t=20, b=50)))
        pf.update_yaxes(title_text="P.rate (%)", secondary_y=False, title_font=dict(size=11, color=C_SUB))
        pf.update_yaxes(title_text="ARPPU (원)", secondary_y=True,  title_font=dict(size=11, color=C_SUB))
        st.plotly_chart(pf, use_container_width=True)

        # 카드 그리드
        for rs in range(0, N, 4):
            cols = st.columns(4)
            for ci in range(4):
                idx = rs + ci
                if idx >= N: break
                r = rows[idx]
                with cols[ci]:
                    dau_color = C_RED if r["over"] else C_GREEN
                    dau_icon  = "⚠️" if r["over"] else "✅"
                    st.markdown(f"""<div class="metric-card">
                        <div class="metric-month">{r['short']}</div>
                        <div class="metric-row">
                            <span class="metric-key">결제율</span>
                            <span class="metric-val" style="color:{C_PURPLE};">{r['pr']:.1f}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-key">ARPPU</span>
                            <span class="metric-val" style="color:{C_AMBER};">{r['ar']:,}원</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-key">ARPDAU</span>
                            <span class="metric-val">{r['arpdau']:,.0f}원</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-key">필요 DAU {dau_icon}</span>
                            <span class="metric-val" style="color:{dau_color};">{fmtn(r['dau'])}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("")

# ══════════════════════════
# TAB 5 — 데이터
# ══════════════════════════
with t_dt:
    st.subheader("상세 데이터 시트")
    df = pd.DataFrame([{
        "월": r["short"], "연도": r["cy"],
        "매출": round(r["rev"]), "한국": round(r["rkr"]), "글로벌": round(r["rgl"]),
        "W(KR)": round(r["fw_kr"], 2), "W(GL)": round(r["fw_gl"], 2),
        "보너스": round(r["bns"], 2),
        "P.rate": round(r["pr"], 1), "ARPPU": r["ar"],
        "ARPDAU": round(r["arpdau"]), "필요DAU": round(r["dau"]),
        "상태": "⚠️" if r["over"] else "✅"
    } for r in rows])
    st.dataframe(
        df.style.format({
            "매출": "{:,.0f}", "한국": "{:,.0f}", "글로벌": "{:,.0f}",
            "ARPPU": "{:,}", "ARPDAU": "{:,}", "필요DAU": "{:,.0f}"
        }),
        height=500, use_container_width=True
    )
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 CSV 다운로드", csv,
        f"sim_{proj['name']}_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )
