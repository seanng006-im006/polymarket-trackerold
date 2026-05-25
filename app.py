import streamlit as st
import requests
import json
import time
from datetime import datetime, timedelta
from supabase import create_client

st.set_page_config(page_title="Polymarket Tracker", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');
* { font-family: 'Rajdhani', sans-serif; box-sizing: border-box; }
.block-container { padding: 1rem 1.5rem; max-width: 100%; }
.hdr h1 {
    font-size:1.6rem; font-weight:700; letter-spacing:0.15em;
    background:linear-gradient(90deg,#00f5c4,#7b61ff);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0;
}
.hdr-sub { font-size:0.72rem; color:#8888aa; letter-spacing:0.1em; margin-top:2px; border-bottom:1px solid #1a1a3a; padding-bottom:0.8rem; }
.mbox { background:#0d0d1f; border:1px solid #1a1a3a; border-radius:8px; padding:0.6rem 1rem; margin-bottom:0.5rem; }
.mbox .lbl { font-size:0.65rem; color:#8888aa; letter-spacing:0.12em; text-transform:uppercase; }
.mbox .val { font-size:1.3rem; font-weight:700; color:#e0e0ff; font-family:'Share Tech Mono',monospace; }
.spike-panel { background:#120a0a; border:1px solid #ff3333; border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.8rem; }
.spike-title { font-size:0.65rem; color:#ff3333; letter-spacing:0.15em; text-transform:uppercase; margin-bottom:0.4rem; }
.spike-row { border-bottom:1px solid #1a0808; padding:0.35rem 0; font-size:0.8rem; }
.spike-row:last-child { border-bottom:none; }
.card { background:#0a0a1a; border:1px solid #1a1a3a; border-radius:12px; padding:0.9rem 1rem; margin-bottom:0.5rem; }
.card-hero { background:#0a0a1a; border:1px solid #1a1a3a; border-radius:14px; padding:1.3rem 1.5rem; margin-bottom:0.8rem; }
.card-spike { border-color:#ff3333 !important; }
.card-outlier { border-color:#ffaa00 !important; }
.crank { font-size:0.62rem; color:#7777aa; font-family:'Share Tech Mono'; }
.cq { font-size:0.88rem; font-weight:600; color:#e0e0ff; line-height:1.35; margin:3px 0 8px; }
.cq-hero { font-size:1.1rem; font-weight:700; color:#f0f0ff; line-height:1.4; margin:4px 0 10px; }
.ccat { font-size:0.65rem; color:#9999bb; letter-spacing:0.08em; margin-bottom:4px; }
.banner { border-radius:6px; padding:3px 10px; font-size:0.65rem; font-weight:700; letter-spacing:0.1em; margin-bottom:6px; display:inline-block; }
.b-spike   { background:#2a0000; border:1px solid #ff3333; color:#ff4444; }
.b-outlier { background:#1a1000; border:1px solid #ffaa00; color:#ffaa00; }
.b-lambda  { background:#001a2a; border:1px solid #00aaff; color:#00aaff; }
.yn { display:flex; align-items:center; gap:6px; margin:2px 0; }
.yn-lbl { font-size:0.72rem; color:#9999bb; width:22px; }
.yn-track { flex:1; height:4px; background:#111122; border-radius:2px; overflow:hidden; }
.yn-fill-y { height:100%; background:#00f5a0; border-radius:2px; }
.yn-fill-n { height:100%; background:#7b61ff; border-radius:2px; }
.yn-pct { font-size:0.78rem; font-weight:700; color:#e0e0ff; font-family:'Share Tech Mono'; width:40px; text-align:right; }
.badges { display:flex; flex-wrap:wrap; gap:3px; margin:5px 0; }
.badge { border-radius:4px; padding:1px 6px; font-size:0.65rem; font-weight:700; font-family:'Share Tech Mono'; white-space:nowrap; }
.bv  { background:#0a2010; color:#00cc80; border:1px solid #00cc80; }
.bv0 { background:#0d0d1f; color:#8888aa; border:1px solid #1a1a3a; }
.bu  { background:#0a2010; color:#00f5a0; border:1px solid #00f5a0; }
.bd  { background:#200a0a; color:#ff5555; border:1px solid #ff5555; }
.bn  { background:#0d0d1f; color:#8888aa; border:1px solid #1a1a3a; }
.blbl { font-size:0.6rem; color:#8888aa; letter-spacing:0.08em; text-transform:uppercase; margin-right:3px; }
.stats { display:grid; grid-template-columns:1fr 1fr; gap:5px; margin:7px 0 4px; }
.sbox { background:#070712; border-radius:5px; padding:4px 7px; }
.slbl { font-size:0.58rem; color:#8888aa; letter-spacing:0.08em; text-transform:uppercase; }
.sval { font-size:0.85rem; font-weight:700; color:#e0e0ff; font-family:'Share Tech Mono'; }
.meta { display:grid; grid-template-columns:1fr 1fr; gap:5px; }
.mlbl { font-size:0.58rem; color:#8888aa; letter-spacing:0.08em; text-transform:uppercase; }
.mval { font-size:0.78rem; color:#aaaacc; font-family:'Share Tech Mono'; }
.sec { font-size:0.65rem; color:#7777aa; letter-spacing:0.15em; text-transform:uppercase; margin:0.8rem 0 0.4rem; border-top:1px solid #0d0d1f; padding-top:0.6rem; }
div[data-testid="stMetricValue"] { font-size:1.2rem !important; }
</style>
""", unsafe_allow_html=True)

GAMMA_API    = "https://gamma-api.polymarket.com"
CLOB_API     = "https://clob.polymarket.com"
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
TG_TOKEN     = st.secrets["TG_TOKEN"]
TG_CHAT_ID   = st.secrets["TG_CHAT_ID"]
REFRESH_8H   = 8 * 3600
VOL_THRESHOLDS = {"1h":100_000,"3h":250_000,"6h":500_000,"24h":2_000_000}

@st.cache_resource
def get_sb(): return create_client(SUPABASE_URL, SUPABASE_KEY)

def fmt_vol(n):
    n=float(n or 0)
    if n>=1e6: return f"${n/1e6:.1f}M"
    if n>=1e3: return f"${n/1e3:.0f}K"
    return f"${n:.0f}"

def parse_outcomes(m):
    try:
        o=json.loads(m.get("outcomes","[]"))
        p=json.loads(m.get("outcomePrices","[]"))
        return list(zip(o,[float(x) for x in p]))
    except: return []

def yes_no(pairs):
    y=next((p for o,p in pairs if o.lower()=="yes"),None)
    n=next((p for o,p in pairs if o.lower()=="no"),None)
    return y,n

def get_token_id(m):
    try:
        ids=json.loads(m.get("clobTokenIds","[]"))
        return ids[0] if ids else None
    except: return None

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT_ID,"text":msg,"parse_mode":"HTML"},timeout=5)
    except: pass

@st.cache_data(ttl=300)
def clob_history(token_id, interval):
    try:
        r=requests.get(f"{CLOB_API}/prices-history",
            params={"market":token_id,"interval":interval,"fidelity":60},timeout=8)
        if r.ok: return r.json().get("history",[])
    except: pass
    return []

def prob_shift_clob(token_id, interval):
    h=clob_history(token_id,interval)
    if len(h)<2: return None
    return h[-1]["p"]-h[0]["p"]

def save_snapshot(mid, vol, prob, question, end_date, liq):
    try:
        get_sb().table("volume_snapshots").insert({
            "market_id":mid,"volume":vol,"prob":prob,
            "question":question[:200],"end_date":end_date,"liquidity":liq,
            "ts":datetime.utcnow().isoformat()
        }).execute()
    except: pass

def get_snaps(mid, hours):
    try:
        since=(datetime.utcnow()-timedelta(hours=hours)).isoformat()
        r=get_sb().table("volume_snapshots")\
            .select("volume,prob,ts").eq("market_id",mid)\
            .gte("ts",since).order("ts").execute()
        return r.data or []
    except: return []

def get_lambdas(mid):
    try:
        since=(datetime.utcnow()-timedelta(hours=24)).isoformat()
        r=get_sb().table("lambda_log").select("lambda_val")\
            .eq("market_id",mid).gte("ts",since).execute()
        return [x["lambda_val"] for x in (r.data or [])]
    except: return []

def save_lambda(mid, win, lam):
    try:
        get_sb().table("lambda_log").insert({
            "market_id":mid,"win":win,"lambda_val":lam,
            "ts":datetime.utcnow().isoformat()
        }).execute()
    except: pass

def get_spikes():
    try:
        since=(datetime.utcnow()-timedelta(hours=24)).isoformat()
        r=get_sb().table("spike_log").select("*")\
            .gte("ts",since).order("ts",desc=True).limit(10).execute()
        return r.data or []
    except: return []

def log_spike(mid, question, vg, ps, prob, win, lam):
    try:
        since=(datetime.utcnow()-timedelta(hours=1)).isoformat()
        ex=get_sb().table("spike_log").select("id")\
            .eq("market_id",mid).eq("win",win).gte("ts",since).execute()
        if not ex.data:
            get_sb().table("spike_log").insert({
                "market_id":mid,"question":question[:200],
                "vol_gain":vg,"prob_shift":ps,"current_prob":prob,
                "win":win,"lambda_val":lam,
                "ts":datetime.utcnow().isoformat()
            }).execute()
    except: pass

def cleanup():
    try:
        cutoff=(datetime.utcnow()-timedelta(days=7)).isoformat()
        get_sb().table("volume_snapshots").delete().lt("ts",cutoff).execute()
        get_sb().table("lambda_log").delete().lt("ts",cutoff).execute()
    except: pass

def compute_kyle(mid, cur_vol, cur_prob, question, win_label, hours):
    snaps=get_snaps(mid,hours)
    if len(snaps)<2: return None,None,None
    vg=cur_vol-snaps[0]["volume"]
    old_prob=snaps[0].get("prob")
    if old_prob is None: return vg,None,None
    ps=cur_prob-old_prob
    if vg<=0 or abs(ps)<0.001: return vg,ps,None
    lam=abs(ps)/vg
    hist=get_lambdas(mid)
    save_lambda(mid,win_label,lam)
    above=False
    if len(hist)>=5:
        avg=sum(hist)/len(hist)
        above=lam>avg*1.5
    threshold=VOL_THRESHOLDS.get(win_label,250_000)
    if vg>=threshold and abs(ps)>0.005:
        log_spike(mid,question,vg,ps,cur_prob,win_label,lam)
        if win_label=="3h" and vg>=250_000:
            tg_key = f"{mid}_3h"
            last_sent = st.session_state.tg_sent.get(tg_key)
            now_dt = datetime.utcnow()
            if last_sent is None or (now_dt - last_sent).seconds > 10800:
                d="📈 YES" if ps>0 else "📉 NO"
                send_telegram(
                    f"⚡ <b>POLYMARKET SPIKE</b>\n\n<b>{question[:80]}</b>\n\n"
                    f"💰 +{fmt_vol(vg)} in 3h\n"
                    f"📊 {'+' if ps>0 else ''}{ps*100:.1f}pp {d}\n"
                    f"YES: <b>{cur_prob*100:.1f}%</b>"
                )
                st.session_state.tg_sent[tg_key] = now_dt
    return vg,ps,lam if above else None

@st.cache_data(ttl=REFRESH_8H)
def fetch_top10():
    r=requests.get(f"{GAMMA_API}/markets",params={
        "active":"true","closed":"false","limit":10,
        "order":"volume24hr","ascending":"false"},timeout=10)
    r.raise_for_status()
    return r.json()

def card_html(m, rank, spikes, is_hero=False):
    question = m.get("question","Unknown")
    cat      = m.get("groupItemTitle") or m.get("category") or ""
    v24      = float(m.get("volume24hr",0))
    vtot     = float(m.get("volume",0))
    liq      = float(m.get("liquidity") or m.get("liquidityClob") or 0)
    end_date = m.get("endDate") or m.get("endDateIso","")
    slug     = m.get("slug","")
    mid      = m.get("conditionId") or m.get("id") or slug
    pairs    = parse_outcomes(m)
    yes, no  = yes_no(pairs)
    token_id = get_token_id(m)

    is_binary=(len(pairs)==2 and
        any(o.lower()=="yes" for o,_ in pairs) and
        any(o.lower()=="no"  for o,_ in pairs))

    end_str=""
    if end_date:
        try:
            dt=datetime.fromisoformat(end_date.replace("Z",""))
            end_str=dt.strftime("%b %d, %Y")
        except: end_str=end_date[:10]

    cur_vol  = float(m.get("volume",0))
    cur_prob = yes if yes is not None else (pairs[0][1] if pairs else 0.5)

    vg,ps,lams={},{},{}
    for wl,wh in [("1h",1),("3h",3),("6h",6),("24h",24)]:
        v,p,l=compute_kyle(mid,cur_vol,cur_prob,question,wl,wh)
        vg[wl]=v; ps[wl]=p; lams[wl]=l

    ps_7d=prob_shift_clob(token_id,"1w") if token_id else None

    has_spike=any(s["market_id"]==mid for s in spikes
        if (datetime.utcnow()-datetime.fromisoformat(s["ts"].replace("Z","").split("+")[0])).seconds<10800)
    has_lam=any(v is not None for v in lams.values())
    pp_vals=[v for v in [ps.get("1h"),ps.get("6h"),ps.get("24h")] if v is not None]
    has_outlier=False
    if len(pp_vals)>=3:
        avg=sum(pp_vals)/len(pp_vals)
        has_outlier=any(abs(v-avg)>abs(avg)*2 and abs(v)>0.01 for v in pp_vals)

    cls="card-hero" if is_hero else "card"
    if has_spike: cls+=" card-spike"
    elif has_outlier: cls+=" card-outlier"

    # banners
    ban=""
    if has_spike:   ban+='<span class="banner b-spike">⚡ VOLUME SPIKE</span> '
    if has_outlier: ban+='<span class="banner b-outlier">◈ OUTLIER</span> '
    if has_lam:     ban+='<span class="banner b-lambda">λ KYLE ABOVE BASELINE</span>'
    if ban: ban=f'<div style="margin-bottom:6px;">{ban}</div>'

    # yes/no bars
    if is_binary and yes is not None:
        yp=yes*100; np_=(1-yes)*100
        yn=(f'<div class="yn"><span class="yn-lbl">Yes</span>'
            f'<div class="yn-track"><div class="yn-fill-y" style="width:{yp:.1f}%"></div></div>'
            f'<span class="yn-pct">{yp:.1f}%</span></div>'
            f'<div class="yn"><span class="yn-lbl">No</span>'
            f'<div class="yn-track"><div class="yn-fill-n" style="width:{np_:.1f}%"></div></div>'
            f'<span class="yn-pct">{np_:.1f}%</span></div>')
    elif pairs:
        yn="".join(
            f'<div class="yn"><span class="yn-lbl" style="width:55px;font-size:0.65rem;">{o[:7]}</span>'
            f'<div class="yn-track"><div class="yn-fill-y" style="width:{p*100:.0f}%"></div></div>'
            f'<span class="yn-pct">{p*100:.0f}%</span></div>'
            for o,p in pairs[:4])
    else:
        yn='<span style="color:#8888aa;font-size:0.72rem;">No data</span>'

    # vol badges
    vb='<div class="badges"><span class="blbl">VOL Δ</span>'
    for wl in ["1h","3h","6h","24h"]:
        v=vg.get(wl)
        if v and v>0: vb+=f'<span class="badge bv">+{fmt_vol(v)} {wl}</span>'
        else:         vb+=f'<span class="badge bv0">+$0 {wl}</span>'
    vb+='</div>'

    # prob badges
    pb='<div class="badges"><span class="blbl">PP Δ</span>'
    for wl,val in [("1h",ps.get("1h")),("3h",ps.get("3h")),
                   ("6h",ps.get("6h")),("24h",ps.get("24h")),("7d",ps_7d)]:
        if val is None:      pb+=f'<span class="badge bn">— {wl}</span>'
        elif val>0.001:      pb+=f'<span class="badge bu">▲{abs(val*100):.2f}pp {wl}</span>'
        elif val<-0.001:     pb+=f'<span class="badge bd">▼{abs(val*100):.2f}pp {wl}</span>'
        else:                pb+=f'<span class="badge bn">0pp {wl}</span>'
    pb+='</div>'

    qcls="cq-hero" if is_hero else "cq"

    html=f"""
    <div class="{cls}">
      {ban}
      <div class="crank">#{rank:02d}</div>
      <div class="ccat">{cat.upper()}</div>
      <div class="{qcls}">{question}</div>
      {yn}
      {vb}
      {pb}
      <div class="stats">
        <div class="sbox"><div class="slbl">24H VOL</div><div class="sval">{fmt_vol(v24)}</div></div>
        <div class="sbox"><div class="slbl">TOTAL VOL</div><div class="sval">{fmt_vol(vtot)}</div></div>
      </div>
      <div class="meta">
        <div><div class="mlbl">LIQUIDITY</div><div class="mval">{fmt_vol(liq) if liq else '—'}</div></div>
        <div><div class="mlbl">ENDS</div><div class="mval">{end_str if end_str else '—'}</div></div>
      </div>
    </div>"""
    return html

if "last_poll" not in st.session_state: st.session_state.last_poll=0
if "tg_sent" not in st.session_state: st.session_state.tg_sent={}

with st.sidebar:
    st.markdown("### ⚙ CONFIG")
    auto_refresh=st.toggle("Auto-refresh (60s)",value=False)
    st.markdown("---")
    st.caption("Top 10 refreshes 3× daily.")
    st.caption("Snapshots stored in Supabase.")
    st.caption("Telegram alerts on 3h $250K spike.")
    if st.button("🔄 Force refresh"):
        st.cache_data.clear(); st.rerun()

try: markets=fetch_top10()
except Exception as e:
    st.error(f"API error: {e}"); st.stop()

now_ts=time.time()
if (now_ts-st.session_state.last_poll)>60:
    for m in markets:
        mid=m.get("conditionId") or m.get("id") or m.get("slug","")
        vol=float(m.get("volume",0))
        liq=float(m.get("liquidity") or m.get("liquidityClob") or 0)
        end=m.get("endDate") or m.get("endDateIso","")
        pairs=parse_outcomes(m)
        y,_=yes_no(pairs)
        prob=y if y is not None else (pairs[0][1] if pairs else 0.5)
        if mid: save_snapshot(mid,vol,prob,m.get("question",""),end,liq)
    cleanup()
    st.session_state.last_poll=now_ts

spikes=get_spikes()
total_24h=sum(float(m.get("volume24hr",0)) for m in markets)
now_str=datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")

st.markdown(f"""
<div class="hdr">
  <h1>◈ POLYMARKET TRACKER</h1>
  <div class="hdr-sub">LIVE PREDICTION MARKET INTELLIGENCE · TOP 10 BY 24H VOLUME · {now_str}</div>
</div>""", unsafe_allow_html=True)

c1,c2,c3,c4=st.columns(4)
for col,lbl,val in [(c1,"MARKETS","10"),(c2,"24H VOLUME",fmt_vol(total_24h)),
                    (c3,"SPIKES (24H)",str(len(spikes))),
                    (c4,"TG ALERTS",str(len([s for s in spikes if s.get("win")=="3h"])))]:
    col.markdown(f'<div class="mbox"><div class="lbl">{lbl}</div><div class="val">{val}</div></div>',
                 unsafe_allow_html=True)

if spikes:
    rows=""
    for sp in spikes[:5]:
        age=datetime.utcnow()-datetime.fromisoformat(sp["ts"].replace("Z","").split("+")[0])
        age_str=f"{int(age.seconds/60)}m ago" if age.seconds<3600 else f"{int(age.seconds/3600)}h ago"
        ps=sp.get("prob_shift") or 0
        col="#00f5a0" if ps>0 else "#ff5555"
        rows+=(f'<div class="spike-row">'
               f'<span style="color:#ff3333;font-weight:700;font-family:\'Share Tech Mono\'">⚡ +{fmt_vol(sp["vol_gain"])}</span>'
               f'<span style="color:#666;font-size:0.7rem"> · {sp.get("win","?")}w · {age_str}</span>'
               f'<span style="color:{col};font-weight:700"> {"▲" if ps>0 else "▼"}{abs(ps*100):.1f}pp</span><br>'
               f'<span style="color:#aaaacc;font-size:0.78rem">{sp["question"][:70]}{"…" if len(sp["question"])>70 else ""}</span>'
               f'</div>')
    st.markdown(f'<div class="spike-panel"><div class="spike-title">⚡ spike log — last 24h</div>{rows}</div>',
                unsafe_allow_html=True)

st.markdown('<div class="sec">▸ #1 most active market</div>',unsafe_allow_html=True)
st.markdown(card_html(markets[0],1,spikes,is_hero=True),unsafe_allow_html=True)

st.markdown('<div class="sec">▸ top markets</div>',unsafe_allow_html=True)
rest=markets[1:10]
rows_=[rest[i:i+3] for i in range(0,len(rest),3)]
for row in rows_:
    cols=st.columns(3)
    for j,m in enumerate(row):
        with cols[j]:
            st.markdown(card_html(m,markets.index(m)+1,spikes,is_hero=False),
                       unsafe_allow_html=True)

if auto_refresh:
    time.sleep(60); st.rerun()
