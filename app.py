import streamlit as st
import json, math, calendar
from datetime import datetime
from supabase import create_client
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ─── Supabase ───
SB_URL = "https://yxifzucmghsqewopssuv.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4aWZ6dWNtZ2hzcWV3b3Bzc3V2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwMTYwMjMsImV4cCI6MjA5MTU5MjAyM30.6bb8TR6voqCRyDQ2sgTf_D7vhWnlmaDuIw0FDyyHs4c"

@st.cache_resource
def get_sb(): return create_client(SB_URL, SB_KEY)
sb = get_sb()

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

def gen_months(sy, sm, ey, em):
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

# ─── Config ───
st.set_page_config(page_title="매출 시뮬레이터",layout="wide",initial_sidebar_state="collapsed")
st.markdown("<style>.block-container{padding-top:2rem;} div[data-testid='stMetricValue']{font-size:1.4rem!important;}</style>",unsafe_allow_html=True)
for k,v in [("logged_in",False),("cur_proj",None),("admin",False)]:
    if k not in st.session_state: st.session_state[k]=v

# ═══ LOGIN ═══
if not st.session_state.logged_in:
    cfg=get_config()
    _,c,_=st.columns([1,2,1])
    with c:
        st.markdown("## 🚀 매출 시뮬레이터"); st.caption("프로젝트별 매출 시뮬레이션"); st.markdown("---")
        pw=st.text_input("🔒 비밀번호",type="password",key="lpw")
        if st.button("로그인",type="primary"):
            if pw==cfg.get("master_password","1234"): st.session_state.logged_in=True; st.rerun()
            else: st.error("비밀번호 오류")
    st.stop()

# ═══ PROJECT LIST ═══
if st.session_state.cur_proj is None:
    st.markdown("## 🚀 매출 시뮬레이터"); st.caption("프로젝트를 선택하거나 새로 만드세요."); st.markdown("---")
    projects=get_projects()
    with st.expander("➕ 새 프로젝트",expanded=len(projects)==0):
        c1,c2=st.columns(2)
        with c1: nn=st.text_input("프로젝트명",placeholder="예: 프로젝트A")
        with c2: npw=st.text_input("비밀번호",type="password",placeholder="관리자용")
        c3,c4=st.columns(2)
        with c3: ng=st.text_input("장르",placeholder="방치형 RPG")
        with c4: nm=st.text_input("시장",placeholder="한국/글로벌")
        if st.button("✅ 생성",type="primary"):
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
                    if p.get("genre"): st.caption(f"🎮 {p['genre']}")
                    if p.get("market"): st.caption(f"🌍 {p['market']}")
                    st.caption(f"📆 {p['start_year']}.{p['start_month']:02d}~{p['end_year']}.{p['end_month']:02d}")
                    if st.button("📂 열기",key=f"o_{p['id']}"): st.session_state.cur_proj=p["id"]; st.session_state.admin=False; st.rerun()
    else: st.info("프로젝트가 없습니다.")
    if st.button("🚪 로그아웃"): st.session_state.logged_in=False; st.rerun()
    st.stop()

# ═══ SIMULATOR ═══
proj=get_project(st.session_state.cur_proj)
if not proj: st.error("프로젝트를 찾을 수 없습니다."); st.session_state.cur_proj=None; st.rerun()
pid=proj["id"]; adm=st.session_state.admin

# Header
if st.button("← 프로젝트 목록"): st.session_state.cur_proj=None; st.session_state.admin=False; st.rerun()
if adm:
    nt=st.text_input("프로젝트명",value=proj["name"],key="pt",label_visibility="collapsed")
    if nt!=proj["name"]: update_proj(pid,{"name":nt})
else: st.markdown(f"# 🚀 {proj['name']}")
nfo=[]
if proj.get("genre"): nfo.append(f"🎮 {proj['genre']}")
if proj.get("market"): nfo.append(f"🌍 {proj['market']}")
nfo.append(f"📆 {proj['start_year']}.{proj['start_month']:02d}~{proj['end_year']}.{proj['end_month']:02d}")
st.caption(" · ".join(nfo))
if adm:
    c1,c2=st.columns([5,1])
    with c1: st.success("🔓 관리자 모드")
    with c2:
        if st.button("🔒 잠금"): st.session_state.admin=False; st.rerun()
else:
    c1,c2=st.columns([3,2])
    with c1: st.info("👁️ 뷰 모드")
    with c2:
        upw=st.text_input("비밀번호",type="password",key="upw",label_visibility="collapsed",placeholder="비밀번호 → Enter")
        if upw:
            if upw==proj.get("password",""): st.session_state.admin=True; st.rerun()
            else: st.error("오류")
st.markdown("---")

# Load
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

if adm:
    with st.expander("📆 기간 설정"):
        p1,p2,p3,p4,p5=st.columns(5)
        with p1: nsy=st.number_input("시작년",2024,2035,sy,key="nsy")
        with p2: nsm=st.selectbox("시작월",range(1,13),index=sm-1,key="nsm")
        with p3: ney=st.number_input("종료년",2024,2035,ey,key="ney")
        with p4: nem=st.selectbox("종료월",range(1,13),index=em-1,key="nem")
        with p5: st.markdown(""); st.markdown(""); 
        if st.button("저장",type="primary",key="psave"): update_proj(pid,{"start_year":nsy,"start_month":nsm,"end_year":ney,"end_month":nem}); st.rerun()

rv_l=st.radio("권역",["🌐 통합","🇰🇷 한국","🌏 글로벌"],horizontal=True,label_visibility="collapsed")
rv="total" if "통합" in rv_l else ("kr" if "한국" in rv_l else "global")

# Calc
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
        r["dkr"]=r["rkr"]/(r["days"]*r["arpdau"]) if r["arpdau"]>0 else 0
        r["dgl"]=r["rgl"]/(r["days"]*r["arpdau"]) if r["arpdau"]>0 else 0
        r["over"]=r["dau"]>dau_cap

# KPI
rf="rkr" if rv=="kr" else "rgl" if rv=="global" else "rev"
tt=sum((t.get("kr",0) or 0)+(t.get("global",0) or 0) if rv=="total" else (t.get("kr",0) or 0) if rv=="kr" else (t.get("global",0) or 0) for t in targets.values())
ad=sum(r["dau"] for r in rows)/N if N>0 else 0; ap=sum(r["pr"] for r in rows)/N if N>0 else 0; aa=sum(r["ar"] for r in rows)/N if N>0 else 0
oc=sum(1 for r in rows if r["over"])
m1,m2,m3,m4,m5=st.columns(5)
m1.metric("📊 목표",fmt(tt)); m2.metric("👥 평균DAU",fmtn(ad)); m3.metric("💰 P.rate",f"{ap:.1f}%"); m4.metric("💎 ARPPU",fmt(aa))
if oc>0: m5.metric("⚠️ 초과",f"{oc}개월",delta=f"상한{fmtn(dau_cap)}",delta_color="inverse")
else: m5.metric("✅ DAU","정상",delta=f"상한{fmtn(dau_cap)}")

if adm:
    dc1,dc2,dc3=st.columns([1.5,6,1])
    with dc1: st.markdown("🚨 **DAU 상한**")
    with dc2: ncap=st.slider("DAU",min_value=50000,max_value=3000000,value=dau_cap,step=50000,key="dcap",label_visibility="collapsed")
    with dc3: st.markdown(f"**{fmtn(dau_cap)}**")
    if ncap!=dau_cap: update_proj(pid,{"dau_cap":ncap})

# Chart
dn="dkr" if rv=="kr" else "dgl" if rv=="global" else "dau"
xl=[r["label"] for r in rows]
fig=make_subplots(specs=[[{"secondary_y":True}]])
fig.add_trace(go.Bar(x=xl,y=[r[rf] for r in rows],name="매출",marker_color=["#ef4444" if r["over"] else "#3b82f6" for r in rows],opacity=0.7),secondary_y=False)
fig.add_trace(go.Scatter(x=xl,y=[r[dn] for r in rows],name="필요DAU",line=dict(color="#f59e0b",width=2)),secondary_y=True)
fig.add_trace(go.Scatter(x=xl,y=[dau_cap]*N,name="상한선",line=dict(color="#ef4444",width=1,dash="dash")),secondary_y=True)
fig.update_layout(height=350,margin=dict(t=30,b=40),hovermode="x unified",
    legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),xaxis=dict(type="category",tickangle=-45))
fig.update_yaxes(title_text="매출",secondary_y=False); fig.update_yaxes(title_text="DAU",secondary_y=True)
st.plotly_chart(fig,width="stretch")

# Tabs
t_tgt,t_cv,t_wt,t_mt,t_dt=st.tabs(["📊 목표","📈 커브","⚖️ 가중치","⚙️ 지표","📋 데이터"])

with t_tgt:
    st.subheader("연도별 매출 목표")
    if not adm: st.info("🔒 뷰 모드")
    cols=st.columns(len(yls))
    for ci,yl in enumerate(yls):
        with cols[ci]:
            t=targets.get(yl,{"kr":0,"global":0}); idxs=yg[yl]
            st.markdown(f"**{yl}년**"); st.caption(f"{months[idxs[0]]['label']}~{months[idxs[-1]]['label']} ({len(idxs)}개월)")
            if adm:
                kv=st.text_input(f"🇰🇷 한국",value=str(int(t.get("kr",0) or 0)),key=f"tk_{yl}")
                gv=st.text_input(f"🌏 글로벌",value=str(int(t.get("global",0) or 0)),key=f"tg_{yl}")
                try:
                    ki,gi=int(kv),int(gv)
                    if ki!=(t.get("kr",0) or 0) or gi!=(t.get("global",0) or 0): upsert_target(pid,int(yl),ki,gi)
                except: pass
            else: st.metric("🇰🇷",fmt(t.get("kr",0) or 0)); st.metric("🌏",fmt(t.get("global",0) or 0))
            st.metric("합계",fmt((t.get("kr",0) or 0)+(t.get("global",0) or 0)))

with t_cv:
    st.subheader("감소커브 × 시즌 계수")
    if not adm: st.info("🔒 뷰 모드")
    cc1,cc2=st.columns(2)
    with cc1:
        st.markdown("**🇰🇷 한국**")
        if adm:
            ndkr=st.slider("KR 감소율",min_value=0.0,max_value=15.0,value=dkr,step=0.5,key="ndkr",format="%.1f%%")
            nbkr=st.slider("KR 부스트",min_value=0.0,max_value=2.0,value=bkr,step=0.1,key="nbkr")
            spkr=st.selectbox("프리셋",list(SEASON_PRESETS.keys()),format_func=lambda x:SEASON_PRESETS[x]["label"],index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_kr","kr")),key="spkr")
            if ndkr!=dkr or nbkr!=bkr: update_proj(pid,{"decay_kr":ndkr,"launch_boost_kr":nbkr})
            if spkr!=proj.get("season_preset_kr","kr"): update_proj(pid,{"season_preset_kr":spkr,"season_kr":json.dumps(SEASON_PRESETS[spkr]["data"])}); st.rerun()
        else: st.metric("감소율",f"{dkr}%/월"); st.metric("부스트",f"+{bkr}")
    with cc2:
        st.markdown("**🌏 글로벌**")
        if adm:
            ndgl=st.slider("GL 감소율",min_value=0.0,max_value=15.0,value=dgl,step=0.5,key="ndgl",format="%.1f%%")
            nbgl=st.slider("GL 부스트",min_value=0.0,max_value=2.0,value=bgl,step=0.1,key="nbgl")
            spgl=st.selectbox("프리셋",list(SEASON_PRESETS.keys()),format_func=lambda x:SEASON_PRESETS[x]["label"],index=list(SEASON_PRESETS.keys()).index(proj.get("season_preset_global","global")),key="spgl")
            if ndgl!=dgl or nbgl!=bgl: update_proj(pid,{"decay_global":ndgl,"launch_boost_global":nbgl})
            if spgl!=proj.get("season_preset_global","global"): update_proj(pid,{"season_preset_global":spgl,"season_global":json.dumps(SEASON_PRESETS[spgl]["data"])}); st.rerun()
        else: st.metric("감소율",f"{dgl}%/월"); st.metric("부스트",f"+{bgl}")
    st.markdown("**📈 커브 프리뷰**")
    cf=go.Figure()
    cf.add_trace(go.Scatter(x=xl,y=[r["bw_kr"] for r in rows],name="한국",line=dict(color="#3b82f6")))
    cf.add_trace(go.Scatter(x=xl,y=[r["bw_gl"] for r in rows],name="글로벌",line=dict(color="#8b5cf6")))
    cf.update_layout(height=220,margin=dict(t=20,b=40),hovermode="x unified",xaxis=dict(type="category",tickangle=-45))
    st.plotly_chart(cf,width="stretch")
    if adm:
        with st.expander("🔧 시즌 수정"):
            sr=st.radio("권역",["한국","글로벌"],horizontal=True,key="ser")
            sd=list(skr) if sr=="한국" else list(sgl); ch=False
            sc=st.columns(6)
            for mi in range(12):
                with sc[mi%6]:
                    nv=st.number_input(f"{mi+1}월",0.1,3.0,float(sd[mi]),0.05,key=f"se_{sr}_{mi}")
                    if nv!=sd[mi]: sd[mi]=nv; ch=True
            if ch: update_proj(pid,{"season_kr" if sr=="한국" else "season_global":json.dumps(sd)})

with t_wt:
    st.subheader("가중치 조정")
    st.caption("자동 + 보너스 = 최종 가중치")
    if not adm: st.info("🔒 뷰 모드")
    with st.expander("📋 보너스 항목"):
        for c in all_cats: st.caption(f"{c['icon']} {c['label']} ({'+' if c['value']>0 else ''}{c['value']})")
        if adm:
            st.markdown("---")
            a1,a2,a3,a4=st.columns([1,3,2,2])
            with a1: ci=st.text_input("아이콘","🏷️",key="cbi")
            with a2: cn=st.text_input("항목명",key="cbn")
            with a3: cv=st.number_input("값",-1.0,2.0,0.2,0.05,key="cbv")
            with a4: st.markdown(""); st.markdown("")
            if st.button("추가",key="cba") and cn:
                nc=ccats+[{"id":f"c_{int(datetime.now().timestamp())}","label":cn,"value":cv,"icon":ci}]
                update_proj(pid,{"custom_bonus_cats":json.dumps(nc)}); st.rerun()
    for yl in yls:
        idxs=yg[yl]
        with st.expander(f"**{yl}년** ({months[idxs[0]]['label']}~{months[idxs[-1]]['label']})",expanded=(yl==yls[0])):
            for idx in idxs:
                r=rows[idx]
                st.markdown(f"**{r['short']}** — KR:`{r['bw_kr']:.2f}` GL:`{r['bw_gl']:.2f}` 최종:**{r['fw_kr']:.2f}**")
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
                    if ab: st.caption(" ".join(ab))

with t_mt:
    st.subheader("P.rate / ARPPU")
    if not adm: st.info("🔒 뷰 모드")
    if adm:
        with st.expander("⚡ 일괄 적용"):
            b1,b2=st.columns(2)
            with b1:
                bpr=st.number_input("P.rate(%)",0.1,20.0,5.0,0.1,key="bpr"); bpry=st.selectbox("연도",yls,key="bpry")
                if st.button("P.rate 적용",key="bpra"):
                    for j in yg[bpry]:
                        md=mdb.get(j,{}); bn=md.get("bonuses","{}");
                        if isinstance(bn,str): bn=json.loads(bn)
                        save_monthly(pid,j,float(md.get("manual_adj",0) or 0),bn,bpr,int(md.get("arppu",70000) or 70000))
                    st.rerun()
            with b2:
                bar=st.number_input("ARPPU(원)",10000,500000,70000,1000,key="bar"); bary=st.selectbox("연도",yls,key="bary")
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

with t_dt:
    st.subheader("데이터 시트")
    df=pd.DataFrame([{"월":r["short"],"연도":r["cy"],"매출":round(r["rev"]),"한국":round(r["rkr"]),"글로벌":round(r["rgl"]),
        "W(KR)":round(r["fw_kr"],2),"W(GL)":round(r["fw_gl"],2),"보너스":round(r["bns"],2),
        "P.rate":round(r["pr"],1),"ARPPU":r["ar"],"ARPDAU":round(r["arpdau"]),"필요DAU":round(r["dau"]),
        "상태":"⚠️" if r["over"] else "✅"} for r in rows])
    st.dataframe(df.style.format({"매출":"{:,.0f}","한국":"{:,.0f}","글로벌":"{:,.0f}","ARPPU":"{:,}","ARPDAU":"{:,}","필요DAU":"{:,.0f}"}),height=500)
    csv=df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV",csv,f"sim_{proj['name']}_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")
