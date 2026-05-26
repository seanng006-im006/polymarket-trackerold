"""
Polymarket Background Collector
--------------------------------
Runs every 5 minutes via GitHub Actions.
Polls Polymarket, writes to Supabase, detects spikes, sends Telegram alerts.
"""

import requests
import json
import os
import logging
from datetime import datetime, timedelta
from supabase import create_client

# ── Configuration (from GitHub Secrets) ──────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TG_TOKEN     = os.environ["TG_TOKEN"]
TG_CHAT_ID   = os.environ["TG_CHAT_ID"]

GAMMA_API    = "https://gamma-api.polymarket.com"
CLEANUP_DAYS = 7
VOL_THRESHOLDS = {"1h": 100_000, "3h": 250_000, "6h": 500_000, "24h": 2_000_000}

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Supabase ──────────────────────────────────────────────────
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Helpers ───────────────────────────────────────────────────
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
    except: return []

def yes_prob(pairs):
    return next((p for o, p in pairs if o.lower() == "yes"), None)

def send_telegram(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=5
        )
        log.info(f"Telegram: {'sent' if r.ok else r.text}")
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ── API ───────────────────────────────────────────────────────
def fetch_top10():
    r = requests.get(f"{GAMMA_API}/markets", params={
        "active": "true", "closed": "false",
        "limit": 10, "order": "volume24hr", "ascending": "false"
    }, timeout=10)
    r.raise_for_status()
    return r.json()

# ── Supabase ops ──────────────────────────────────────────────
def save_snapshot(mid, vol, prob, question, end_date, liq):
    try:
        sb.table("volume_snapshots").insert({
            "market_id": mid, "volume": vol, "prob": prob,
            "question": question[:200], "end_date": end_date,
            "liquidity": liq, "ts": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        log.error(f"save_snapshot: {e}")

def get_snaps(mid, hours):
    try:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        r = sb.table("volume_snapshots")\
            .select("volume,prob,ts")\
            .eq("market_id", mid)\
            .gte("ts", since)\
            .order("ts").execute()
        return r.data or []
    except: return []

def get_lambdas(mid):
    try:
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        r = sb.table("lambda_log")\
            .select("lambda_val")\
            .eq("market_id", mid)\
            .gte("ts", since).execute()
        return [x["lambda_val"] for x in (r.data or [])]
    except: return []

def save_lambda(mid, win, lam):
    try:
        sb.table("lambda_log").insert({
            "market_id": mid, "win": win,
            "lambda_val": lam, "ts": datetime.utcnow().isoformat()
        }).execute()
    except: pass

def log_spike(mid, question, vg, ps, prob, win, lam):
    now   = datetime.utcnow()
    since = (now - timedelta(hours=3)).isoformat()
    try:
        ex = sb.table("spike_log").select("id")\
            .eq("market_id", mid)\
            .eq("win", win)\
            .gte("ts", since).execute()
        if ex.data:
            return False
        sb.table("spike_log").insert({
            "market_id": mid, "question": question[:200],
            "vol_gain": vg, "prob_shift": ps,
            "current_prob": prob, "win": win,
            "lambda_val": lam, "ts": now.isoformat()
        }).execute()
        return True
    except Exception as e:
        log.error(f"log_spike: {e}")
        return False

def cleanup():
    try:
        cutoff = (datetime.utcnow() - timedelta(days=CLEANUP_DAYS)).isoformat()
        sb.table("volume_snapshots").delete().lt("ts", cutoff).execute()
        sb.table("lambda_log").delete().lt("ts", cutoff).execute()
        log.info("Cleanup done")
    except Exception as e:
        log.error(f"Cleanup: {e}")

# ── Process each market ───────────────────────────────────────
def process_market(m):
    mid      = m.get("conditionId") or m.get("id") or m.get("slug", "")
    vol      = float(m.get("volume24hr", 0))  # use 24h volume as it updates more frequently
    liq      = float(m.get("liquidity") or m.get("liquidityClob") or 0)
    end_date = m.get("endDate") or m.get("endDateIso", "")
    question = m.get("question", "")
    pairs    = parse_outcomes(m)
    prob     = yes_prob(pairs) or (pairs[0][1] if pairs else 0.5)

    save_snapshot(mid, vol, prob, question, end_date, liq)

    for win_label, hours in [("1h", 1), ("3h", 3), ("6h", 6), ("24h", 24)]:
        snaps = get_snaps(mid, hours)
        if len(snaps) < 2: continue

        vg       = vol - snaps[0]["volume"]
        old_prob = snaps[0].get("prob")
        if old_prob is None: continue

        ps = prob - old_prob
        if vg <= 0 or abs(ps) < 0.001: continue

        lam  = abs(ps) / vg
        hist = get_lambdas(mid)
        save_lambda(mid, win_label, lam)

        threshold = VOL_THRESHOLDS.get(win_label, 250_000)
        if vg >= threshold and abs(ps) > 0.005:
            logged = log_spike(mid, question, vg, ps, prob, win_label, lam)
            log.info(f"Spike: {question[:50]} | {win_label} | +{fmt_vol(vg)} | {ps*100:.1f}%")

            if win_label == "3h" and vg >= 250_000 and logged:
                d = "📈 YES" if ps > 0 else "📉 NO"
                send_telegram(
                    f"⚡ <b>POLYMARKET SPIKE</b>\n\n"
                    f"<b>{question[:80]}</b>\n\n"
                    f"💰 +{fmt_vol(vg)} in 3h\n"
                    f"📊 {'+' if ps>0 else ''}{ps*100:.1f}% {d}\n"
                    f"YES: <b>{prob*100:.1f}%</b>"
                )

# ── Main (runs once per GitHub Actions trigger) ───────────────
if __name__ == "__main__":
    log.info("=== Collector run started ===")
    try:
        markets = fetch_top10()
        log.info(f"Fetched {len(markets)} markets")
        for m in markets:
            process_market(m)
        cleanup()
    except Exception as e:
        log.error(f"Fatal error: {e}")
        raise
    log.info("=== Collector run complete ===")
