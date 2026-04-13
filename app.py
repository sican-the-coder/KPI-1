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
C_BG = "#0a0e1a"
C_CARD = "#131a2e"
C_BORDER = "rgba(99,179,237,0.12)"
C_TEXT = "#e2e8f0"
C_SUB = "#94a3b8"
C_MUTED = "#64748b"
C_BLUE = "#3b82f6"
C_PURPLE = "#8b5cf6"
C_AMBER = "#f59e0b"
C_RED = "#ef4444"
C_GREEN = "#10b981"
CHART_BG = "rgba(0,0,0,0)"

# ─── CSS ───
st.set_page_config(page_title="매출 시뮬레이터", layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 1rem; }}
    div[data-testid="stMetricValue"] {{ font-size: 1.6rem !important; font-weight: 700 !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; }}
    .big-title {{ font-size: 2.2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.2rem; }}
    .sub-info {{ font-size: 0.85rem; color: {C_SUB}; margin-bottom: 0.5rem; }}
    .kpi-card {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 12px;
        padding: 16px 18px; text-align: center;
    }}
    .kpi-label {{ font-size: 0.75rem; color: {C_SUB}; margin-bottom: 4px; }}
    .kpi-value {{ font-size: 1.6rem; font-weight: 700; }}
    .kpi-sub {{ font-size: 0.7rem; color: {C_MUTED}; margin-top: 2px; }}
    .section-card {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 12px;
        padding: 18px; margin-bottom: 12px;
    }}
    .mode-badge-admin {{
        background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3);
        border-radius: 8px; padding: 8px 16px; text-align: center;
        color: {C_GREEN}; font-weight: 600; font-size: 0.9rem;
    }}
    .mode-badge-view {{
        background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2);
        border-radius: 8px; padding: 8px 16px; text-align: center;
        color: {C_BLUE}; font-weight: 600; font-size: 0.9rem;
    }}
    hr {{ border-color: {C_BORDER}; margin: 0.8rem 0; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 2px; }}
    .stTabs [data-baseweb="tab"] {{ padding: 8px 16px; font-weight: 600; font-size: 0.85rem; }}
</style>""", unsafe_allow_html=True)

# ─── Constants ───
SEASON_PRESETS = {
    "kr": {"label": "🇰🇷 한국형", "data": [1.3,1.0,0.9,0.85,0.9,0.8,0.95,1.1,0.9,0.95,1.0,1.5]},
    "global": {"label": "🌏 글로벌형", "data": [0.9,0.85,0.9,0.85,0.9,1.0,1.15,1.1,0.95,0.9,1.2,1.4]},
    "flat": {"label": "➖ 플랫", "data": [1,1,1,1,1,1,1,1,1,1,1,1]},
}
DEFAULT_BONUS = [
    {"id":"season","label":"시즌","value":0.3,"icon":"🎊"},
    {"id":"content","label":"콘텐츠","value":0.25,"icon":"🎮"},
    {"id":"major_update","label":"대규모UP","value":0.4,"icon":"🔥"},
    {"id":"bm","label":"BM","value":0.2,"icon":"💎"},
    {"id":"marketing","label":"마케팅","value":0.2,"icon":"📢"},
    {"id":"vacation","label":"방학","value":0.15,"icon":"🏖️"},
    {"id":"holiday","label":"연휴","value":0.15,"icon":"📅"},
    {"id":"compete","label":"경쟁작","value":-0.15,"icon":"⚔️"},
    {"id":"feature","label":"피처링","value":0.2,"icon":"⭐"},
]

# ─── Helpers ───
def gen_months(sy,sm,ey,em):
    ms=[]; y,m,i=sy,sm,0
    while y<ey or (y==ey and m<=em):
        ms.append({"idx":i,"year":y,"month":m,"days":calendar.monthrange(y,m)[1],
            "label":f"{y}.{m:02d}","short":f"{str(y)[2:]}.{m:02d}"})
        i+=1; m+=1
        if m>12: m=1; y+=1
    return ms

def year_groups(months):
    g={}
    for mo in months:
        k=str(mo["year"])
        if k not in g: g[k]=[]
        g[k].append(mo["idx"]); mo["cy"]=k
    return g

def dc(i,rate): return math.pow(1-rate/100,i)
def fmt(v):
    if abs(v)>=1e8: return f"{v/1e8:.1f}억"
    if abs(v)>=1e4: return f"{v/1e4:.0f}만"
    return f"{v:,.0f}"
def fmtn(v):
    if abs(v)>=1e4: return f"{v/1e4:.1f}만"
    return f"{v:,.0f}"

# ─── DB ───
def get_config():
    r=sb.table("app_config").select("*").eq("id","main").execute()
    return r.data[0] if r.data else {"master_password":"1234"}
def get_projects(): return sb.table("projects").select("*").order("created_at").execute().data or []
def get_project(pid):
    r=sb.table("projects").select("*").eq("id",pid).execute()
    return r.data[0] if r.data else None
def create_project(name,pw,genre="",market=""):
    r=sb.table("projects").insert({"name":name,"password":pw,"genre":genre,"market":market}).execute()
    if r.data:
        pid=r.data[0]["id"]
        for y in [2026,2027,2028,2029]:
            sb.table("yearly_targets").insert({"project_id":pid,"year":y,"target_kr":50000000000,"target_global":20000000000}).execute()
        return pid
    return None
def update_proj(pid,data): sb.table("projects").update({**data,"updated_at":datetime.now().isoformat()}).eq("id",pid).execute()
def get_targets(pid):
    r=sb.table("yearly_targets").select("*").eq("project_id",pid).order("year").execute()
    return {str(t["year"]):{"kr":t["target_kr"],"global":t["target_global"]} for t in (r.data or [])}
def upsert_target(pid,year,kr,gl): sb.table("yearly_targets").upsert({"project_id":pid,"year":year,"target_kr":kr,"target_global":gl},on_conflict="project_id,year").execute()
def get_monthly(pid):
    r=sb.table("monthly_data").select("*").eq("project_id",pid).execute()
    return {d["month_index"]:d for d in (r.data or [])}
def save_monthly(pid,idx,adj=0,bonuses=None,pr=5.0,ar=70000):
    sb.table("monthly_data").upsert({"project_id":pid,"month_index":idx,"manual_adj":adj,"bonuses":json.dumps(bonuses or {}),"p_rate":pr,"arppu":ar},on_conflict="project_id,month_index").execute()

# ─── Plotly theme helper ───
def styled_layout(**kwargs):
    base = dict(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(family="Noto Sans KR, sans-serif", color=C_TEXT, size=12),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color=C_SUB)),
        xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=10, color=C_SUB),
                   gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(tickfont=dict(size=10, color=C_SUB), gridcolor="rgba(148,163,184,0.08)"),
    )
    base.update(kwargs)
    return base

# ─── KPI HTML ───
def kpi_html(label, value, sub="", color=C_BLUE):
    return f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color};">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

# ─── Session ───
for k,v in [("logged_in",False),("cur_proj",None),("admin",False)]:
    if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════
# LOGIN
# ═══════════════════════════════════
if not st.session_state.logged_in:
    cfg=get_config()
    _,c,_=st.columns([1,1.5,1])
    with c:
        st.markdown("")
        st.markdown('<div class="big-title" style="text-align:center;">🚀 매출 시뮬레이터</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sub-info" style="text-align:center;">프로젝트별 매출 목표 시뮬레이션</div>', unsafe_allow_html=True)
        st.markdown("---")
        pw=st.text_input("🔒 비밀번호", type="password", key="lpw")
        if st.button("로그인", type="primary", use_container_width=True):
            if pw==cfg.get("master_password","1234"): st.session_state.logged_in=True; st.rerun()
            else: st.error("비밀번호가 틀렸습니다.")
    st.stop()

# ═══════════════════════════════════
# PROJECT LIST
# ═══════════════════════════════════
if st.session_state.cur_proj is None:
    st.markdown('<div class="big-title">🚀 매출 시뮬레이터</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-info">프로젝트를 선택하거나 새로 만드세요.</div>', unsafe_allow_html=True)
    st.markdown("---")
    projects=get_projects()
    with st.expander("➕ 새 프로젝트 만들기", expanded=len(projects)==0):
        c1,c2=st.columns(2)
        with c1: nn=st.text_input("프로젝트명",placeholder="예: 프로젝트A")
        with c2: npw=st.text_input("비밀번호",type="password",placeholder="관리자용")
        c3,c4=st.columns(2)
        with c3: ng=st.text_input("장르",placeholder="방치형 RPG")
        with c4: nm=st.text_input("시장",placeholder="한국/글로벌")
        if st.button("✅ 프로젝트 생성", type="primary"):
            if nn and npw:
                pid=create_project(nn,npw,ng,nm)
                if pid: st.session_state.cur_proj=pid; st.rerun()
            else: st.warning("프로젝트명/비밀번호 필수")
    st.markdown("---")
    if projects:
        cols=st.columns(min(len(projects),3))
        for i,p in enumerate(projects):
            with cols[i%3]:
                with st.container(border=True):
                    st.markdown(f"### {p['name']}")
                    meta=[]
                    if p.get("genre"): meta.append(f"🎮 {p['genre']}")
                    if p.get("market"): meta.append(f"🌍 {p['market']}")
                    meta.append(f"📆 {p['start_year']}.{p['start_month']:02d}~{p['end_year']}.{p['end_month']:02d}")
                    st.caption(" · ".join(meta))
                    if st.button("📂 열기",key=f"o_{p['id']}",use_container_width=True):
                        st.session_state.cur_proj=p["id"]; st.session_state.admin=False; st.rerun()
    else: st.info("프로젝트가 없습니다. 위에서 새로 만들어주세요.")
    st.markdown("---")
    if st.button("🚪 로그아웃"): st.session_state.logged_in=False; st.rerun()
    st.stop()

# ═══════════════════════════════════
# SIMULATOR
# ═══════════════════════════════════
proj=get_project(st.session_state.cur_proj)
if not proj: st.error("프로젝트를 찾을 수 없습니다."); st.session_state.cur_proj=None; st.rerun()
pid=proj["id"]; adm=st.session_state.admin

# ─── Header ───
if st.button("← 프로젝트 목록"):
    st.session_state.cur_proj=None; st.session_state.admin=False; st.rerun()

if adm:
    nt=st.text_input("프로젝트명 수정",value=proj["name"],key="pt",label_visibility="collapsed")
    if nt!=proj["name"]: update_proj(pid,{"name":nt})
    st.markdown(f'<div class="big-title">🚀 {proj["name"]}</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="big-title">🚀 {proj["name"]}</div>', unsafe_allow_html=True)

nfo=[]
if proj.get("genre"): nfo.append(f"🎮 {proj['genre']}")
if proj.get("market"): nfo.append(f"🌍 {proj['market']}")
nfo.append(f"📆 {proj['start_year']}.{proj['start_month']:02d} ~ {proj['end_year']}.{proj['end_month']:02d}")
st.markdown(f'<div class="sub-info">{" · ".join(nfo)}</div>', unsafe_allow_html=True)

# Mode toggle
if adm:
    c1,c2=st.columns([6,1])
    with c1: st.markdown('<div class="mode-badge-admin">🔓 관리자 모드</div>', unsafe_allow_html=True)
    with c2:
        if st.button("🔒 잠금"): st.session_state.admin=False; st.rerun()
else:
    c1,c2=st.columns([3,2])
    with c1: st.markdown('<div class="mode-badge-view">👁️ 뷰 모드 (읽기 전용)</div>', unsafe_allow_html=True)
    with c2:
        upw=st.text_input("비밀번호",type="password",key="upw",label_visibility="collapsed",placeholder="비밀번호 → Enter")
        if upw:
            if upw==proj.get("password",""): st.session_state.admin=True; st.rerun()
            else: st.error("비밀번호 오류")

st.markdown("---")

# ─── Load ───
sy,sm,ey,em=proj["start_year"],proj["start_month"],proj["end_year"],proj["end_month"]
months=gen_months(sy,sm,ey,em); N=len(months); yg=year_groups(months); yls=list(yg.keys())
targets=get_targets(pid); mdb=get_monthly(pid)
dkr=float(proj.get("decay_kr",4.0) or 4.0); dgl=float(proj.get("decay_global",3.0) or 3.0)
bkr=float(proj.get("launch_boost_kr",0.5) or 0.5); bgl=float(proj.get("launch_boost_global",0.3) or 0.3)
skr=proj.get("season_kr",SEASON_PRESETS["kr"]["data"]); sgl=proj.get("season_global",SEASON_PRESETS["global"]["data"])
if isinstance(skr,str): skr=json.loads(skr)
if isinstance(sgl,str): sgl=json.loads(sgl)
dau_cap=int(proj.get("dau_cap",1000000) or 1000000)
ccats=proj.get("custom_bonus_cats",[]); 
if isinstance(ccats,str): ccats=json.loads(ccats)
all_cats=DEFAULT_BONUS+ccats

# Period settings
if adm:
    with st.expander("📆 시뮬레이션 기간 설정"):
        p1,p2,p3,p4=st.columns(4)
        with p1: nsy=st.number_input("시작 연도",2024,2035,sy,key="nsy")
        with p2: nsm=st.selectbox("시작 월",range(1,13),index=sm-1,key="nsm")
        with p3: ney=st.number_input("종료 연도",2024,2035,ey,key="ney")
        with p4: nem=st.selectbox("종료 월",range(1,13),index=em-1,key="nem")
        if st.button("기간 저장",type="primary"):
            update_proj(pid,{"start_year":nsy,"start_month":nsm,"end_year":ney,"end_month":nem}); st.rerun()

# Region toggle
rv_l=st.radio("권역",["🌐 통합","🇰🇷 한국","🌏 글로벌"],horizontal=True,label_visibility="collapsed")
rv="total" if "통합" in rv_l else ("kr" if "한국" in rv_l else "global")

# ─── Calc ───
rows=[]
for mo in months:
    i=mo["idx"]; md=mdb.get(i,{})
    d_kr=dc(i,dkr); d_gl=dc(i,dgl)
    s_kr=float(skr[mo["month"]-1]) if mo["month"]-1<len(skr) else 1.0
    s_gl=float(sgl[mo["month"]-1]) if mo["month"]-1<len(sgl) else 1.0
    lb_kr=bkr if i<3 else 0; lb_gl=bgl if i<3 else 0
    bw_kr=max(0.05,round(d_kr*s_kr+lb_kr,4)); bw_gl=max(0.05,round(d_gl*s_gl+lb_gl,4))
    manual=float(md.get("manual_adj",0) or 0)
    bn=md.get("bonuses","{}");
    if isinstance(bn,str): bn=json.loads(bn)
    bns=sum(float(c["value"]) for c in all_cats if bn.get(c["id"]))
    fw_kr=max(0.1,bw_kr+manual+bns); fw_gl=max(0.1,bw_gl+manual+bns)
    pr=float(md.get("p_rate",5.0) or 5.0); ar=int(md.get("arppu",70000) or 70000)
    arpdau=ar*(pr/100)
    rows.append({**mo,"bw_kr":bw_kr,"bw_gl":bw_gl,"manual":manual,"bn":bn,"bns":bns,
        "fw_kr":fw_kr,"fw_gl":fw_gl,"pr":pr,"ar":ar,"arpdau":arpdau})

for yl,idxs in yg.items():
    t=targets.get(yl,{"kr":0,"global":0})
    tw_kr=sum(rows[j]["fw_kr"] for j in idxs) or 1; tw_gl=sum(rows[j]["fw_gl"] for j in idxs) or 1
    for j in idxs:
        r=rows[j]
        r["rkr"]=(t.get("kr",0) or 0)*(r["fw_kr"]/tw_kr); r["rgl"]=(t.get("global",0) or 0)*(r["fw_gl"]/tw_gl)
        r["rev"]=r["rkr"]+r["rgl"]
        r["dau"]=r["rev"]/(r["days"]*r["arpdau"]) if r["arpdau"]>0 else 0
        r["dau_kr"]=r["rkr"]/(r["days"]*r["arpdau"]) if r["arpdau"]>0 else 0
        r["dau_gl"]=r["rgl"]/(r["days"]*r["arpdau"]) if r["arpdau"]>0 else 0
        r["over"]=r["dau"]>dau_cap

# ─── KPI Cards ───
rf="rkr" if rv=="kr" else "rgl" if rv=="global" else "rev"
tt=sum((t.get("kr",0) or 0)+(t.get("global",0) or 0) if rv=="total" else (t.get("kr",0) or 0) if rv=="kr" else (t.get("global",0) or 0) for t in targets.values())
ad=sum(r["dau"] for r in rows)/N if N>0 else 0
ap=sum(r["pr"] for r in rows)/N if N>0 else 0
aa=sum(r["ar"] for r in rows)/N if N>0 else 0
oc=sum(1 for r in rows if r["over"])

k1,k2,k3,k4,k5=st.columns(5)
with k1: st.markdown(kpi_html("📊 목표 매출",fmt(tt),f"{len(yls)}개년",C_BLUE),unsafe_allow_html=True)
with k2: st.markdown(kpi_html("👥 평균 필요 DAU",fmtn(ad),f"상한 {fmtn(dau_cap)}",C_RED if oc>0 else C_GREEN),unsafe_allow_html=True)
with k3: st.markdown(kpi_html("💰 평균 P.rate",f"{ap:.1f}%","전체 기간",C_PURPLE),unsafe_allow_html=True)
with k4: st.markdown(kpi_html("💎 평균 ARPPU",fmt(aa),"전체 기간",C_AMBER),unsafe_allow_html=True)
with k5:
    if oc>0: st.markdown(kpi_html("⚠️ DAU 초과",f"{oc}개월","상한선 초과",C_RED),unsafe_allow_html=True)
    else: st.markdown(kpi_html("✅ DAU 상태","정상","초과 없음",C_GREEN),unsafe_allow_html=True)

st.markdown("")

# DAU Cap
if adm:
    dc1,dc2,dc3=st.columns([1.5,6,1])
    with dc1: st.markdown(f"🚨 **DAU 상한**")
    with dc2: ncap=st.slider("DAU",min_value=50000,max_value=3000000,value=dau_cap,step=50000,key="dcap",label_visibility="collapsed")
    with dc3: st.markdown(f"**{fmtn(dau_cap)}**")
    if ncap!=dau_cap: update_proj(pid,{"dau_cap":ncap})

# ─── Main Chart ───
dn="dau_kr" if rv=="kr" else "dau_gl" if rv=="global" else "dau"
xl=[r["label"] for r in rows]

fig=make_subplots(specs=[[{"secondary_y":True}]])
fig.add_trace(go.Bar(x=xl,y=[r[rf] for r in rows],name="매출",
    marker_color=[C_RED if r["over"] else C_BLUE for r in rows],opacity=0.75),secondary_y=False)
fig.add_trace(go.Scatter(x=xl,y=[r[dn] for r in rows],name="필요 DAU",
    line=dict(color=C_AMBER,width=2.5)),secondary_y=True)
fig.add_trace(go.Scatter(x=xl,y=[dau_cap]*N,name="DAU 상한선",
    line=dict(color=C_RED,width=1.5,dash="dash")),secondary_y=True)
fig.update_layout(**styled_layout(height=380,margin=dict(t=30,b=50)))
fig.update_yaxes(title_text="매출",secondary_y=False,title_font=dict(size=11,color=C_SUB))
fig.update_yaxes(title_text="DAU",secondary_y=True,title_font=dict(size=11,color=C_SUB))
st.plotly_chart(fig,use_container_width=True)

# ─── Tabs ───
t_tgt,t_cv,t_wt,t_mt,t_dt=st.tabs(["📊 목표","📈 커브","⚖️ 가중치","⚙️ 지표","📋 데이터"])

# ═══ TARGETS ═══
with t_tgt:
    st.subheader("연도별 매출 목표")
    if not adm: st.info("🔒 뷰 모드 — 수정은 관리자 모드에서")
    cols=st.columns(len(yls))
    for ci,yl in enumerate(yls):
        with cols[ci]:
            with st.container(border=True):
                t=targets.get(yl,{"kr":0,"global":0}); idxs=yg[yl]
                st.markdown(f"**{yl}년**")
                st.caption(f"{months[idxs[0]]['label']} ~ {months[idxs[-1]]['label']} ({len(idxs)}개월)")
                if adm:
                    kv=st.text_input(f"🇰🇷 한국",value=str(int(t.get("kr",0) or 0)),key=f"tk_{yl}")
                    gv=st.text_input(f"🌏 글로벌",value=str(int(t.get("global",0) or 0)),key=f"tg_{yl}")
                    try:
                        ki,gi=int(kv),int(gv)
                        if ki!=(t.get("kr",0) or 0) or gi!=(t.get("global",0) or 0): upsert_target(pid,int(yl),ki,gi)
                    except: pass
                else:
                    st.metric("🇰🇷 한국",fmt(t.get("kr",0) or 0))
                    st.metric("🌏 글로벌",fmt(t.get("global",0) or 0))
                st.markdown("---")
                total_yr=(t.get("kr",0) or 0)+(t.get("global",0) or 0)
                st.markdown(f"**합계: {fmt(total_yr)}**")

# ═══ CURVE ═══
with t_cv:
    st.subheader("자연감소 커브 × 시즌 계수")
    st.caption("기본 가중치 = 감소커브 × 시즌계수 + 론칭부스트")
    if not adm: st.info("🔒 뷰 모드")
    cc1,cc2=st.columns(2)
    with cc1:
        with st.container(border=True):
            st.markdown(f"**🇰🇷 한국**")
            if adm:
                ndkr=st.slider("감소율 (%/월)",min_value=0.0,max_value=15.0,value=dkr,step=0.5,key="ndkr",format="%.1f%%")
                nbkr=st.slider("론칭 부스트",min_value=0.0,max_value=2.0,value=bkr,step=0.1,key="nbkr")
                spkr=st.selectbox("시즌 프리셋",list(SEASON_PRESETS.keys()),format_func=lambda x:SEASON_PRESETS[x]["label"],
                    index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_kr","kr")),key="spkr")
                if ndkr!=dkr or nbkr!=bkr: update_proj(pid,{"decay_kr":ndkr,"launch_boost_kr":nbkr})
                if spkr!=proj.get("season_preset_kr","kr"):
                    update_proj(pid,{"season_preset_kr":spkr,"season_kr":json.dumps(SEASON_PRESETS[spkr]["data"])}); st.rerun()
            else: st.metric("감소율",f"{dkr}%/월"); st.metric("부스트",f"+{bkr}")
    with cc2:
        with st.container(border=True):
            st.markdown(f"**🌏 글로벌**")
            if adm:
                ndgl=st.slider("감소율 (%/월)",min_value=0.0,max_value=15.0,value=dgl,step=0.5,key="ndgl",format="%.1f%%")
                nbgl=st.slider("론칭 부스트",min_value=0.0,max_value=2.0,value=bgl,step=0.1,key="nbgl")
                spgl=st.selectbox("시즌 프리셋",list(SEASON_PRESETS.keys()),format_func=lambda x:SEASON_PRESETS[x]["label"],
                    index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_global","global")),key="spgl")
                if ndgl!=dgl or nbgl!=bgl: update_proj(pid,{"decay_global":ndgl,"launch_boost_global":nbgl})
                if spgl!=proj.get("season_preset_global","global"):
                    update_proj(pid,{"season_preset_global":spgl,"season_global":json.dumps(SEASON_PRESETS[spgl]["data"])}); st.rerun()
            else: st.metric("감소율",f"{dgl}%/월"); st.metric("부스트",f"+{bgl}")

    st.markdown(""); st.markdown("**📈 커브 프리뷰**")
    cf=go.Figure()
    cf.add_trace(go.Scatter(x=xl,y=[r["bw_kr"] for r in rows],name="한국",
        line=dict(color=C_BLUE,width=2.5),fill="tozeroy",fillcolor="rgba(59,130,246,0.1)"))
    cf.add_trace(go.Scatter(x=xl,y=[r["bw_gl"] for r in rows],name="글로벌",
        line=dict(color=C_PURPLE,width=2.5),fill="tozeroy",fillcolor="rgba(139,92,246,0.1)"))
    cf.update_layout(**styled_layout(height=240,margin=dict(t=20,b=50)))
    st.plotly_chart(cf,use_container_width=True)

    if adm:
        with st.expander("🔧 시즌 계수 직접 수정"):
            sr=st.radio("권역",["한국","글로벌"],horizontal=True,key="ser")
            sd=list(skr) if sr=="한국" else list(sgl); ch=False
            sc=st.columns(6)
            for mi in range(12):
                with sc[mi%6]:
                    nv=st.number_input(f"{mi+1}월",0.1,3.0,float(sd[mi]),0.05,key=f"se_{sr}_{mi}")
                    if nv!=sd[mi]: sd[mi]=nv; ch=True
            if ch: update_proj(pid,{"season_kr" if sr=="한국" else "season_global":json.dumps(sd)})

# ═══ WEIGHTS ═══
with t_wt:
    st.subheader("월별 가중치 조정")
    st.caption("자동 가중치 + 보너스 체크 = 최종 가중치")
    if not adm: st.info("🔒 뷰 모드")
    with st.expander("📋 보너스 항목 목록"):
        bcols=st.columns(3)
        for bi,c in enumerate(all_cats):
            with bcols[bi%3]:
                s="+" if c["value"]>0 else ""
                st.caption(f"{c['icon']} **{c['label']}** ({s}{c['value']})")
        if adm:
            st.markdown("---")
            a1,a2,a3=st.columns([3,2,1])
            with a1: cn=st.text_input("항목명",key="cbn",placeholder="새 항목 이름")
            with a2: cv=st.number_input("배율",-1.0,2.0,0.2,0.05,key="cbv")
            with a3: st.markdown(""); st.markdown("")
            if st.button("➕ 추가",key="cba") and cn:
                nc=ccats+[{"id":f"c_{int(datetime.now().timestamp())}","label":cn,"value":cv,"icon":"🏷️"}]
                update_proj(pid,{"custom_bonus_cats":json.dumps(nc)}); st.rerun()
    for yl in yls:
        idxs=yg[yl]
        with st.expander(f"**{yl}년** ({months[idxs[0]]['label']} ~ {months[idxs[-1]]['label']})",expanded=(yl==yls[0])):
            for idx in idxs:
                r=rows[idx]
                col_info,col_bonus,col_result=st.columns([2,6,1])
                with col_info:
                    st.markdown(f"**{r['short']}**")
                    st.caption(f"KR:{r['bw_kr']:.2f} GL:{r['bw_gl']:.2f}")
                with col_bonus:
                    if adm:
                        bn=dict(r["bn"]); bc=st.columns(len(all_cats)); chg=False
                        for bi,cat in enumerate(all_cats):
                            with bc[bi]:
                                act=bn.get(cat["id"],False)
                                nv=st.checkbox(cat["icon"],value=act,key=f"b_{idx}_{cat['id']}")
                                if nv!=act: bn[cat["id"]]=nv; chg=True
                        if chg: save_monthly(pid,idx,r["manual"],bn,r["pr"],r["ar"])
                    else:
                        ab=[c["icon"] for c in all_cats if r["bn"].get(c["id"])]
                        st.caption(" ".join(ab) if ab else "—")
                with col_result:
                    color=C_BLUE if r["fw_kr"]>1.5 else C_AMBER if r["fw_kr"]<0.7 else C_TEXT
                    st.markdown(f"<div style='text-align:right;font-weight:700;font-size:1.1rem;color:{color};padding-top:8px;'>{r['fw_kr']:.2f}</div>",unsafe_allow_html=True)

# ═══ METRICS ═══
with t_mt:
    st.subheader("P.rate / ARPPU 조정")
    if not adm: st.info("🔒 뷰 모드")
    if adm:
        with st.expander("⚡ 일괄 적용"):
            b1,b2=st.columns(2)
            with b1:
                bpr=st.number_input("P.rate(%)",0.1,20.0,5.0,0.1,key="bpr")
                bpry=st.selectbox("적용 연도",yls,key="bpry")
                if st.button("P.rate 적용",key="bpra"):
                    for j in yg[bpry]:
                        md=mdb.get(j,{}); bn=md.get("bonuses","{}");
                        if isinstance(bn,str): bn=json.loads(bn)
                        save_monthly(pid,j,float(md.get("manual_adj",0) or 0),bn,bpr,int(md.get("arppu",70000) or 70000))
                    st.rerun()
            with b2:
                bar=st.number_input("ARPPU(원)",10000,500000,70000,1000,key="bar")
                bary=st.selectbox("적용 연도",yls,key="bary")
                if st.button("ARPPU 적용",key="bara"):
                    for j in yg[bary]:
                        md=mdb.get(j,{}); bn=md.get("bonuses","{}");
                        if isinstance(bn,str): bn=json.loads(bn)
                        save_monthly(pid,j,float(md.get("manual_adj",0) or 0),bn,float(md.get("p_rate",5.0) or 5.0),bar)
                    st.rerun()
    for rs in range(0,N,4):
        cols=st.columns(4)
        for ci in range(4):
            idx=rs+ci
            if idx>=N: break
            r=rows[idx]
            with cols[ci]:
                with st.container(border=True):
                    st.markdown(f"**{r['short']}**")
                    if r["over"]: st.error(f"DAU {fmtn(r['dau'])} ⚠️")
                    else: st.caption(f"DAU {fmtn(r['dau'])}")
                    if adm:
                        npr=st.slider("P.rate",min_value=0.1,max_value=20.0,value=float(r["pr"]),step=0.1,key=f"pr_{idx}")
                        nar=st.slider("ARPPU",min_value=10000,max_value=500000,value=int(r["ar"]),step=1000,key=f"ar_{idx}")
                        if npr!=r["pr"] or nar!=r["ar"]: save_monthly(pid,idx,r["manual"],r["bn"],npr,nar)
                    else: st.metric("P.rate",f"{r['pr']:.1f}%"); st.metric("ARPPU",f"{r['ar']:,}원")

# ═══ DATA ═══
with t_dt:
    st.subheader("상세 데이터 시트")
    df=pd.DataFrame([{"월":r["short"],"연도":r["cy"],"매출":round(r["rev"]),"한국":round(r["rkr"]),"글로벌":round(r["rgl"]),
        "W(KR)":round(r["fw_kr"],2),"W(GL)":round(r["fw_gl"],2),"보너스":round(r["bns"],2),
        "P.rate":round(r["pr"],1),"ARPPU":r["ar"],"ARPDAU":round(r["arpdau"]),"필요DAU":round(r["dau"]),
        "상태":"⚠️" if r["over"] else "✅"} for r in rows])
    st.dataframe(df.style.format({"매출":"{:,.0f}","한국":"{:,.0f}","글로벌":"{:,.0f}","ARPPU":"{:,}","ARPDAU":"{:,}","필요DAU":"{:,.0f}"}),height=500,use_container_width=True)
    csv=df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드",csv,f"sim_{proj['name']}_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")
