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

* { font-family: 'Rajdhani', sans-serif; }
code, .mono { font-family: 'Share Tech Mono', monospace; }

body { background: #070712; }

.block-container { padding-top: 1.5rem; max-width: 1200px; }

.hdr {
    border-bottom: 1px solid #1a1a3a;
    padding-bottom: 0.8rem;
    margin-bottom: 1.2rem;
}
.hdr h1 {
    font-size: 1.8rem; font-weight: 700; letter-spacing: 0.15em;
    background: linear-gradient(90deg, #00f5c4, #7b61ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.hdr-sub { font-size: 0.75rem; color: #444466; letter-spacing: 0.1em; margin-top: 4px; }

.metric-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
    margin-bottom: 1.2rem;
}
.metric-box {
    background: #0d0d1f; border: 1px solid #1a1a3a;
    border-radius: 8px; padding: 0.7rem 1rem;
}
.metric-box .lbl { font-size: 0.68rem; color: #444466; letter-spacing: 0.12em; text-transform: uppercase; }
.metric-box .val { font-size: 1.4rem; font-weight: 700; color: #e0e0ff; font-family: 'Share Tech Mono', monospace; }

.spike-panel {
    background: #120a0a; border: 1px solid #ff3333;
    border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem;
}
.spike-title { font-size: 0.7rem; color: #ff3333; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.6rem; }
.spike-item { border-bottom: 1px solid #1a0a0a; padding: 0.5rem 0; }
.spike-item:last-child { border-bottom: none; }

.mcard {
    background: #0a0a1a; border: 1px solid #1a1a3a;
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
    transition: border-color 0.2s;
}
.mcard:hover { border-color: #333366; }
.mcard.has-spike { border-color: #ff3333 !important; }
.mcard.has-outlier { border-color: #ffaa00 !important; }

.mrank { font-size: 0.65rem; color: #333355; letter-spacing: 0.1em; font-family: 'Share Tech Mono'; }
.mq { font-size: 0.95rem; font-weight: 600; color: #c0c0e0; line-height: 1.4; margin: 4px 0; }
.mcat { font-size: 0.68rem; color: #333355; letter-spacing: 0.08em; margin-bottom: 8px; }

.btn-yes {
    background: #0a1f14; color: #00f5a0; border: 1px solid #00f5a0;
    border-radius: 6px; padding: 5px 16px; font-size: 0.82rem;
    font-weight: 700; letter-spacing: 0.05em; margin-right: 8px;
    font-family: 'Rajdhani', sans-serif;
}
.btn-no {
    background: #1f0a0a; color: #ff5555; border: 1px solid #ff5555;
    border-radius: 6px; padding: 5px 16px; font-size: 0.82rem;
    font-weight: 700; letter-spacing: 0.05em;
    font-family: 'Rajdhani', sans-serif;
}

.prob-yes { font-size: 1.8rem; font-weight: 700; color: #00f5a0; font-family: 'Share Tech Mono'; text-align: center; }
.prob-mid { font-size: 1.8rem; font-weight: 700; color: #ffaa00; font-family: 'Share Tech Mono'; text-align: center; }
.prob-no  { font-size: 1.8rem; font-weight: 700; color: #ff5555; font-family: 'Share Tech Mono'; text-align: center; }

.vol-main { font-size: 1.3rem; font-weight: 700; color: #e0e0ff; font-family: 'Share Tech Mono'; }
.vol-sub  { font-size: 0.68rem; color: #444466; letter-spacing: 0.08em; }
.vol-total { font-size: 0.9rem; color: #888899; font-family: 'Share Tech Mono'; }

.badge-up   { background:#0a2a1a; color:#00f5a0; border:1px solid #00f5a0; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:700; margin-right:4px; font-family:'Share Tech Mono'; }
.badge-down { background:#2a0a0a; color:#ff5555; border:1px solid #ff5555; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:700; margin-right:4px; font-family:'Share Tech Mono'; }
.badge-flat { background:#0d0d1f; color:#444466; border:1px solid #222244; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:700; margin-right:4px; font-family:'Share Tech Mono'; }
.badge-outlier { background:#2a1a00; color:#ffaa00; border:1px solid #ffaa00; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:700; margin-right:4px; font-family:'Share Tech Mono'; }
.badge-spike { background:#2a0000; color:#ff3333; border:1px solid #ff3333; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:700; margin-right:4px; font-family:'Share Tech Mono'; }

.sec-hdr { font-size:0.68rem; color:#333355; letter-spacing:0.15em; text-transform:uppercase; margin:1rem 0 0.5rem; border-top:1px solid #0d0d1f; padding-top:0.8rem; }
.status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────
GAMMA_API    = "https://gamma-api.polymarket.com"
CLOB_API     = "https://clob.polymarket.com"
SUPABASE_URL = "https://llwpjeokrxfuingxiksk.supabase.co"
SUPABASE_KEY = "sb_publishable_ovPph4WdVncPNq6AHztH_A_Ng8SlHlv"
SPIKE_VOL    = 250_000
WINDOW_HRS   = 3
REFRESH_8H   = 8 * 3600
CLEANUP_DAYS = 7

# ── Supabase client ──────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_tables():
    """Create tables if they don't exist via Supabase REST."""
    sb = get_supabase()
    try:
        sb.table("volume_snapshots").select("id").limit(1).execute()
    except:
        pass
    try:
        sb.table("prob_snapshots").select("id").limit(1).execute()
    except:
        pass
    try:
        sb.table("spike_log").select("id").limit(1).execute()
    except:
        pass

# ── Helpers ──────────────────────────────────────────────────
def fmt_vol(n):
    n = float(n or 0)
    if n >= 1e6: return f"${n/1e6:.1f}M"
    if n >= 1e3: return f"${n/1e3:.0f}K"
    return f"${n:.0f}"

def parse_outcomes(m):
    try:
        outcomes = json.loads(m.get("outcomes", "[]"))
        prices   = json.loads(m.get("outcomePrices", "[]"))
        return list(zip(outcomes, [float(p) for p in prices]))
    except:
        return []

def yes_no(pairs):
    yes = next((p for o, p in pairs if o.lower() == "yes"), None)
    no  = next((p for o, p in pairs if o.lower() == "no"),  None)
    return yes, no

def badge_html(label, shift):
    if shift is None:
        return f'<span class="badge-flat">{label}: —</span>'
    direction = "▲" if shift > 0 else "▼"
    cls = "badge-up" if shift > 0 else ("badge-down" if shift < 0 else "badge-flat")
    return f'<span class="{cls}">{direction}{abs(shift*100):.1f}pp {label}</span>'

# ── API calls ────────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_8H)
def fetch_top10():
    r = requests.get(f"{GAMMA_API}/markets", params={
        "active": "true", "closed": "false",
        "limit": 10, "order": "volume24hr", "ascending": "false"
    }, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_clob_history(token_id, interval="1d"):
    try:
        r = requests.get(f"{CLOB_API}/prices-history", params={
            "market": token_id, "interval": interval, "fidelity": 60
        }, timeout=8)
        if r.ok:
            data = r.json().get("history", [])
            return data
    except:
        pass
    return []

def get_prob_shift(token_id, interval):
    """Get probability shift over a given interval from CLOB."""
    history = fetch_clob_history(token_id, interval)
    if len(history) < 2:
        return None
    return history[-1]["p"] - history[0]["p"]

# ── Supabase operations ──────────────────────────────────────
def save_volume_snapshot(market_id, volume, question):
    try:
        sb = get_supabase()
        sb.table("volume_snapshots").insert({
            "market_id": market_id,
            "volume": volume,
            "question": question[:200],
            "ts": datetime.utcnow().isoformat()
        }).execute()
    except:
        pass

def save_prob_snapshot(market_id, prob, question):
    try:
        sb = get_supabase()
        sb.table("prob_snapshots").insert({
            "market_id": market_id,
            "prob": prob,
            "question": question[:200],
            "ts": datetime.utcnow().isoformat()
        }).execute()
    except:
        pass

def get_volume_window(market_id, hours=3):
    """Get volume snapshots from the last N hours."""
    try:
        sb = get_supabase()
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        res = sb.table("volume_snapshots")\
            .select("volume,ts")\
            .eq("market_id", market_id)\
            .gte("ts", since)\
            .order("ts")\
            .execute()
        return res.data or []
    except:
        return []

def get_prob_window(market_id, hours=24):
    """Get prob snapshots from the last N hours to calculate drift rate."""
    try:
        sb = get_supabase()
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        res = sb.table("prob_snapshots")\
            .select("prob,ts")\
            .eq("market_id", market_id)\
            .gte("ts", since)\
            .order("ts")\
            .execute()
        return res.data or []
    except:
        return []

def log_spike(market_id, question, vol_gain, prob_shift, current_prob):
    try:
        sb = get_supabase()
        # Check no duplicate in last hour
        since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        existing = sb.table("spike_log")\
            .select("id")\
            .eq("market_id", market_id)\
            .gte("ts", since)\
            .execute()
        if not existing.data:
            sb.table("spike_log").insert({
                "market_id": market_id,
                "question": question[:200],
                "vol_gain": vol_gain,
                "prob_shift": prob_shift,
                "current_prob": current_prob,
                "ts": datetime.utcnow().isoformat()
            }).execute()
    except:
        pass

def get_recent_spikes(limit=5):
    try:
        sb = get_supabase()
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        res = sb.table("spike_log")\
            .select("*")\
            .gte("ts", since)\
            .order("ts", desc=True)\
            .limit(limit)\
            .execute()
        return res.data or []
    except:
        return []

def cleanup_old_data():
    """Delete snapshots older than 7 days to stay within 500MB."""
    try:
        sb = get_supabase()
        cutoff = (datetime.utcnow() - timedelta(days=CLEANUP_DAYS)).isoformat()
        sb.table("volume_snapshots").delete().lt("ts", cutoff).execute()
        sb.table("prob_snapshots").delete().lt("ts", cutoff).execute()
    except:
        pass

def detect_spike(market_id, current_vol, current_prob, question):
    """
    Spike = $250K+ volume in 3h window AND prob moved 3x its normal drift rate.
    """
    snapshots = get_volume_window(market_id, hours=WINDOW_HRS)
    if len(snapshots) < 2:
        return None

    vol_gain = current_vol - snapshots[0]["volume"]
    if vol_gain < SPIKE_VOL:
        return None

    # Check prob shift vs normal drift
    prob_snaps = get_prob_window(market_id, hours=24)
    if len(prob_snaps) >= 2:
        # Normal drift = average absolute change per hour over last 24h
        total_hours = 24
        total_shift = abs(prob_snaps[-1]["prob"] - prob_snaps[0]["prob"])
        normal_drift = total_shift / total_hours if total_hours > 0 else 0.005

        # Prob shift during spike window
        spike_prob_snaps = [p for p in prob_snaps
                           if p["ts"] >= snapshots[0]["ts"]]
        if len(spike_prob_snaps) >= 2:
            spike_prob_shift = abs(spike_prob_snaps[-1]["prob"] - spike_prob_snaps[0]["prob"])
            spike_hours = WINDOW_HRS
            spike_drift = spike_prob_shift / spike_hours

            # Only flag if prob moved 3x its normal rate during spike
            if normal_drift > 0 and spike_drift < (3 * normal_drift):
                return None
            prob_shift_val = spike_prob_snaps[-1]["prob"] - spike_prob_snaps[0]["prob"]
        else:
            prob_shift_val = None
    else:
        # Not enough history — flag on volume alone for now
        prob_shift_val = None

    log_spike(market_id, question, vol_gain, prob_shift_val, current_prob)
    return {"vol_gain": vol_gain, "prob_shift": prob_shift_val}

def detect_outlier(shifts):
    """
    Outlier = one timeframe moving significantly against the others.
    shifts = {"1h": float|None, "6h": float|None, "1d": float|None}
    """
    vals = {k: v for k, v in shifts.items() if v is not None}
    if len(vals) < 2:
        return False
    values = list(vals.values())
    avg = sum(values) / len(values)
    for v in values:
        if avg != 0 and abs(v - avg) > abs(avg) * 2:
            return True
        if avg == 0 and abs(v) > 0.05:
            return True
    return False

# ── Session state ────────────────────────────────────────────
if "last_poll" not in st.session_state: st.session_state.last_poll = 0
if "db_ready"  not in st.session_state: st.session_state.db_ready  = False

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ CONFIG")
    spike_threshold = st.number_input("Spike threshold ($)", min_value=50_000,
        max_value=2_000_000, value=250_000, step=50_000, format="%d")
    window_hrs = st.slider("Spike window (hrs)", 1, 12, 3)
    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    st.markdown("---")
    st.caption("Top 10 refreshes 3× daily.")
    st.caption("Prices poll every 60s.")
    st.caption("History stored in Supabase.")
    if st.button("🔄 Force refresh"):
        st.cache_data.clear()
        st.rerun()

SPIKE_VOL  = spike_threshold
WINDOW_HRS = window_hrs

# ── Init DB (first run) ──────────────────────────────────────
if not st.session_state.db_ready:
    try:
        init_tables()
        st.session_state.db_ready = True
    except:
        pass

# ── Fetch top 10 ─────────────────────────────────────────────
try:
    markets = fetch_top10()
except Exception as e:
    st.error(f"Cannot reach Polymarket API: {e}")
    st.stop()

# ── Poll + store snapshots every 60s ────────────────────────
now_ts = time.time()
if (now_ts - st.session_state.last_poll) > 60:
    for m in markets:
        mid   = m.get("conditionId") or m.get("id") or m.get("slug", "")
        vol   = float(m.get("volume", 0))
        pairs = parse_outcomes(m)
        yes, _ = yes_no(pairs)
        if yes is None and pairs: yes = pairs[0][1]
        q = m.get("question", "")
        if mid:
            save_volume_snapshot(mid, vol, q)
            if yes is not None:
                save_prob_snapshot(mid, yes, q)
    cleanup_old_data()
    st.session_state.last_poll = now_ts

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="hdr">
  <h1>◈ POLYMARKET TRACKER</h1>
  <div class="hdr-sub">LIVE PREDICTION MARKET INTELLIGENCE · TOP 10 BY 24H VOLUME</div>
</div>
""", unsafe_allow_html=True)

# ── Summary metrics ──────────────────────────────────────────
total_24h  = sum(float(m.get("volume24hr", 0)) for m in markets)
total_vol  = sum(float(m.get("volume", 0)) for m in markets)
spikes     = get_recent_spikes(limit=10)
now_str    = datetime.utcnow().strftime("%H:%M:%S UTC")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-box"><div class="lbl">markets tracked</div><div class="val">10</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box"><div class="lbl">total 24h volume</div><div class="val">{fmt_vol(total_24h)}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box"><div class="lbl">spikes (24h)</div><div class="val">{len(spikes)}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-box"><div class="lbl">last updated</div><div class="val" style="font-size:1rem;">{now_str}</div></div>', unsafe_allow_html=True)

# ── Spike alerts ─────────────────────────────────────────────
if spikes:
    spike_items = ""
    for sp in spikes[:5]:
        age = datetime.utcnow() - datetime.fromisoformat(sp["ts"])
        age_str = f"{int(age.seconds/60)}m ago" if age.seconds < 3600 else f"{int(age.seconds/3600)}h ago"
        ps = sp.get("prob_shift")
        ps_str = ""
        if ps is not None:
            d = "▲" if ps > 0 else "▼"
            c = "#00f5a0" if ps > 0 else "#ff5555"
            ps_str = f'<span style="color:{c};font-weight:700;"> {d}{abs(ps*100):.1f}pp</span>'
        spike_items += f"""
        <div class="spike-item">
          <span style="color:#ff3333;font-weight:700;font-family:'Share Tech Mono'">⚡ +{fmt_vol(sp['vol_gain'])}</span>
          {ps_str}
          <span style="color:#666677;font-size:0.75rem;"> · {age_str}</span><br>
          <span style="color:#aaaacc;font-size:0.82rem;">{sp['question'][:80]}{'…' if len(sp['question'])>80 else ''}</span>
          <span style="color:#555566;font-size:0.75rem;"> · YES: {sp['current_prob']*100:.0f}%</span>
        </div>"""

    st.markdown(f"""
    <div class="spike-panel">
      <div class="spike-title">⚡ volume spike alerts — last 24h</div>
      {spike_items}
    </div>
    """, unsafe_allow_html=True)

# ── Market cards ─────────────────────────────────────────────
st.markdown('<div class="sec-hdr">▸ active markets</div>', unsafe_allow_html=True)

for i, m in enumerate(markets, 1):
    question = m.get("question", "Unknown")
    cat      = m.get("groupItemTitle") or m.get("category") or ""
    v24      = float(m.get("volume24hr", 0))
    vtot     = float(m.get("volume", 0))
    slug     = m.get("slug", "")
    url      = m.get("url") or (f"https://polymarket.com/event/{slug}" if slug else None)
    pairs    = parse_outcomes(m)
    yes, no  = yes_no(pairs)
    mid      = m.get("conditionId") or m.get("id") or slug

    is_binary = (
        len(pairs) == 2 and
        any(o.lower() == "yes" for o, _ in pairs) and
        any(o.lower() == "no"  for o, _ in pairs)
    )

    # Get CLOB-based probability shifts
    token_id = None
    if m.get("clobTokenIds"):
        try:
            ids = json.loads(m["clobTokenIds"])
            token_id = ids[0] if ids else None
        except:
            pass

    shifts = {"1h": None, "6h": None, "7d": None}
    if token_id:
        shifts["1h"] = get_prob_shift(token_id, "1h")
        shifts["6h"] = get_prob_shift(token_id, "6h")
        shifts["7d"] = get_prob_shift(token_id, "1w")

    is_outlier = detect_outlier(shifts)

    # Spike check from Supabase
    has_spike = any(s["market_id"] == mid for s in spikes
                    if (datetime.utcnow() - datetime.fromisoformat(s["ts"])).seconds < WINDOW_HRS * 3600)

    card_class = "mcard"
    if has_spike: card_class += " has-spike"
    elif is_outlier: card_class += " has-outlier"

    col_info, col_prob, col_vol = st.columns([3, 1.2, 1])

    with col_info:
        spike_tag   = '<span class="badge-spike">⚡SPIKE</span>' if has_spike else ''
        outlier_tag = '<span class="badge-outlier">◈ OUTLIER</span>' if is_outlier else ''
        q_text = f'<a href="{url}" target="_blank" style="color:#c0c0e0;text-decoration:none;">{question}</a>' if url else question

        badge_row = (
            badge_html("1h", shifts["1h"]) +
            badge_html("6h", shifts["6h"]) +
            badge_html("7d", shifts["7d"])
        )

        st.markdown(f"""
        <div class="{card_class}">
          <div class="mrank">#{i:02d}</div>
          <div class="mq">{q_text} {spike_tag}{outlier_tag}</div>
          <div class="mcat">{cat.upper()}</div>
          <div style="margin-top:6px;">{badge_row}</div>
        """, unsafe_allow_html=True)

        if is_binary and yes is not None:
            yes_c = int(yes * 100)
            no_c  = 100 - yes_c
            st.markdown(f"""
          <div style="margin-top:10px;">
            <span class="btn-yes">BUY YES {yes_c}¢</span>
            <span class="btn-no">BUY NO {no_c}¢</span>
          </div>
            """, unsafe_allow_html=True)
        elif pairs:
            pills = "".join(
                f'<span style="background:#0d0d1f;border:1px solid #1a1a3a;border-radius:5px;padding:2px 8px;font-size:0.72rem;color:#888899;margin-right:4px;">{o} {int(p*100)}¢</span>'
                for o, p in pairs[:4]
            )
            st.markdown(f'<div style="margin-top:8px;">{pills}</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_prob:
        if is_binary and yes is not None:
            pct = yes * 100
            cls = "prob-yes" if pct >= 65 else ("prob-mid" if pct >= 35 else "prob-no")
            st.markdown(f'<div class="{cls}">{pct:.0f}%</div>', unsafe_allow_html=True)
            st.progress(yes)
            st.caption("YES prob")
        elif pairs:
            for label, prob in pairs[:3]:
                st.caption(f"{label}: {prob*100:.0f}%")
                st.progress(prob)

    with col_vol:
        st.markdown(
            f'<div class="vol-main">{fmt_vol(v24)}</div>'
            f'<div class="vol-sub">24H VOLUME</div>'
            f'<div style="margin-top:8px;"><div class="vol-sub">ALL-TIME</div>'
            f'<div class="vol-total">{fmt_vol(vtot)}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border-color:#0d0d1f;margin:4px 0;'>", unsafe_allow_html=True)

# ── Auto refresh ─────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()
