import os
import json
import time
import copy
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

VERSION_NAME = "Balina Avcısı V8.2 SMA FIX (Gercek MA7/MA25 + Hafiza)"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com").strip().rstrip("/")
OKX_INST_TYPE = os.getenv("OKX_INST_TYPE", "SWAP").strip().upper()

BINANCE_CONFIRM_ENABLED = os.getenv("BINANCE_CONFIRM_ENABLED", "true").lower() == "true"
BINANCE_CONFIRM_REQUIRED = os.getenv("BINANCE_CONFIRM_REQUIRED", "false").lower() == "true"
BINANCE_CONFIRM_BASE_URL = os.getenv("BINANCE_CONFIRM_BASE_URL", "https://data-api.binance.vision").strip().rstrip("/")
BINANCE_CONFIRM_SCORE_PASS = float(os.getenv("BINANCE_CONFIRM_SCORE_PASS", "14"))
BINANCE_CONFIRM_SCORE_SOFT = float(os.getenv("BINANCE_CONFIRM_SCORE_SOFT", "8"))
BINANCE_CONFIRM_FAIL_OPEN_SCORE = float(os.getenv("BINANCE_CONFIRM_FAIL_OPEN_SCORE", "74"))
MAX_BINANCE_OKX_PRICE_GAP_PCT = float(os.getenv("MAX_BINANCE_OKX_PRICE_GAP_PCT", "0.40"))
HARD_BINANCE_OKX_PRICE_GAP_PCT = float(os.getenv("HARD_BINANCE_OKX_PRICE_GAP_PCT", "0.90"))

MEMORY_FILE = os.getenv("MEMORY_FILE", "balina_avcisi_v527_hibrit_onayli_memory.json").strip()
LOG_FILE = os.getenv("LOG_FILE", "balina_avcisi_v527_hibrit_onayli.log").strip()
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Istanbul").strip()

AUTO_START_MESSAGE = os.getenv("AUTO_START_MESSAGE", "true").lower() == "true"
AUTO_HEARTBEAT = os.getenv("AUTO_HEARTBEAT", "true").lower() == "true"
HEARTBEAT_INTERVAL_SEC = int(float(os.getenv("HEARTBEAT_INTERVAL_SEC", "7200")))
HOT_SCAN_INTERVAL_SEC = float(os.getenv("HOT_SCAN_INTERVAL_SEC", "1.5"))
DEEP_SCAN_INTERVAL_SEC = float(os.getenv("DEEP_SCAN_INTERVAL_SEC", "8"))
MEMORY_SAVE_INTERVAL_SEC = int(float(os.getenv("MEMORY_SAVE_INTERVAL_SEC", "60")))
FOLLOWUP_CHECK_INTERVAL_SEC = int(float(os.getenv("FOLLOWUP_CHECK_INTERVAL_SEC", "300")))
FOLLOWUP_DELAY_SEC = int(float(os.getenv("FOLLOWUP_DELAY_SEC", "7200")))
HOT_TTL_SEC = int(float(os.getenv("HOT_TTL_SEC", "1800")))
ALERT_COOLDOWN_MIN = int(float(os.getenv("ALERT_COOLDOWN_MIN", "75")))
SETUP_COOLDOWN_MIN = int(float(os.getenv("SETUP_COOLDOWN_MIN", "45")))
MAX_HOT_CANDIDATES = int(float(os.getenv("MAX_HOT_CANDIDATES", "16")))
MAX_DEEP_ANALYSIS_PER_CYCLE = int(float(os.getenv("MAX_DEEP_ANALYSIS_PER_CYCLE", "12")))

MIN_CANDIDATE_SCORE = float(os.getenv("MIN_CANDIDATE_SCORE", "34"))
MIN_READY_SCORE = float(os.getenv("MIN_READY_SCORE", "50"))
MIN_SIGNAL_SCORE = float(os.getenv("MIN_SIGNAL_SCORE", "68"))

SCORE_OVERRIDE_GAP = float(os.getenv("SCORE_OVERRIDE_GAP", "8"))
PRICE_OVERRIDE_MOVE_PCT = float(os.getenv("PRICE_OVERRIDE_MOVE_PCT", "0.55"))

NO_SIGNAL_DIAG_SEC = int(float(os.getenv("NO_SIGNAL_DIAG_SEC", str(4 * 3600))))

KLINE_CACHE_SEC = int(float(os.getenv("KLINE_CACHE_SEC", "5")))
TICKER_CACHE_SEC = int(float(os.getenv("TICKER_CACHE_SEC", "8")))
HTTP_TIMEOUT = int(float(os.getenv("HTTP_TIMEOUT", "12")))

OKX_INSTRUMENT_CACHE_SEC = int(float(os.getenv("OKX_INSTRUMENT_CACHE_SEC", "1800")))
AUTO_SYMBOL_REFRESH_SEC = int(float(os.getenv("AUTO_SYMBOL_REFRESH_SEC", "1800")))
SYMBOL_FAIL_BLOCK_SEC = int(float(os.getenv("SYMBOL_FAIL_BLOCK_SEC", "900")))
SYMBOL_FAIL_FORGET_SEC = int(float(os.getenv("SYMBOL_FAIL_FORGET_SEC", "43200")))
SYMBOL_FAIL_MAX_STREAK = int(float(os.getenv("SYMBOL_FAIL_MAX_STREAK", "3")))

MIN_24H_QUOTE_VOLUME = float(os.getenv("MIN_24H_QUOTE_VOLUME", "1200000"))

MA_ENGINE_ENABLED = os.getenv("MA_ENGINE_ENABLED", "true").lower() == "true"
MA_COIN_LIMIT = int(float(os.getenv("MA_COIN_LIMIT", "200")))
MA_SCAN_INTERVAL_SEC = float(os.getenv("MA_SCAN_INTERVAL_SEC", "30"))
MA_KLINE_INTERVAL = os.getenv("MA_KLINE_INTERVAL", "1H").strip()
MA_STOP_PCT = float(os.getenv("MA_STOP_PCT", "0.012"))
MA_TP1_PCT = float(os.getenv("MA_TP1_PCT", "0.020"))
MA_TP2_PCT = float(os.getenv("MA_TP2_PCT", "0.035"))
MA_TP3_PCT = float(os.getenv("MA_TP3_PCT", "0.050"))
MA_ENTRY_MAX_DIFF_PCT = float(os.getenv("MA_ENTRY_MAX_DIFF_PCT", "0.30"))
SHORT_MAX_RESISTANCE_DIFF_PCT = float(os.getenv("SHORT_MAX_RESISTANCE_DIFF_PCT", "0.30"))
SHORT_MIN_RESISTANCE_DIFF_PCT = float(os.getenv("SHORT_MIN_RESISTANCE_DIFF_PCT", "0"))   # 0 = kapalı; direnç min uzaklık
SHORT_MIN_SUPPORT_DIFF_PCT = float(os.getenv("SHORT_MIN_SUPPORT_DIFF_PCT", "1.20"))
SHORT_MAX_SUPPORT_DIFF_PCT = float(os.getenv("SHORT_MAX_SUPPORT_DIFF_PCT", "0"))     # 0 = limit yok
LONG_MAX_SUPPORT_DIFF_PCT = float(os.getenv("LONG_MAX_SUPPORT_DIFF_PCT", "0.30"))
LONG_MIN_SUPPORT_DIFF_PCT = float(os.getenv("LONG_MIN_SUPPORT_DIFF_PCT", "0"))           # 0 = kapalı; destek min uzaklık
LONG_MIN_RESISTANCE_DIFF_PCT = float(os.getenv("LONG_MIN_RESISTANCE_DIFF_PCT", "1.20"))
LONG_MAX_RESISTANCE_DIFF_PCT = float(os.getenv("LONG_MAX_RESISTANCE_DIFF_PCT", "0"))  # 0 = limit yok
MA_LONG_ENGINE_ENABLED = os.getenv("MA_LONG_ENGINE_ENABLED", "true").lower() == "true"
MA_SHORT_ENGINE_ENABLED = os.getenv("MA_SHORT_ENGINE_ENABLED", "true").lower() == "true"
MA_SUPPORT_RESISTANCE_LOOKBACK = int(float(os.getenv("MA_SUPPORT_RESISTANCE_LOOKBACK", "50")))
MA_FOLLOWUP_ENABLED = os.getenv("MA_FOLLOWUP_ENABLED", "true").lower() == "true"

LEVERAGE = float(os.getenv("LEVERAGE", "1"))
MAX_POSITION_RISK_PCT = float(os.getenv("MAX_POSITION_RISK_PCT", "2.0"))
MIN_STOP_PCT = float(os.getenv("MIN_STOP_PCT", "0.003"))
MAX_STOP_PCT = float(os.getenv("MAX_STOP_PCT", "0.012"))
LIQUIDATION_BUFFER = float(os.getenv("LIQUIDATION_BUFFER", "2.0"))
DEFAULT_MARGIN_USDT = float(os.getenv("DEFAULT_MARGIN_USDT", "100"))

WHALE_EYE_ENABLED = os.getenv("WHALE_EYE_ENABLED", "true").lower() == "true"
FUNDING_EYE_ENABLED = os.getenv("FUNDING_EYE_ENABLED", "true").lower() == "true"

WHALE_OI_LOOKBACK_MIN = int(float(os.getenv("WHALE_OI_LOOKBACK_MIN", "20")))
WHALE_OI_CACHE_SEC = int(float(os.getenv("WHALE_OI_CACHE_SEC", "30")))
WHALE_OI_HISTORY_MAX = int(float(os.getenv("WHALE_OI_HISTORY_MAX", "180")))
WHALE_OI_BEARISH_DROP_PCT = float(os.getenv("WHALE_OI_BEARISH_DROP_PCT", "-1.5"))
WHALE_OI_BULLISH_RISE_PCT = float(os.getenv("WHALE_OI_BULLISH_RISE_PCT", "1.5"))
WHALE_PRICE_FLAT_UP_MIN_PCT = float(os.getenv("WHALE_PRICE_FLAT_UP_MIN_PCT", "-0.1"))
WHALE_PRICE_FLAT_DOWN_MAX_PCT = float(os.getenv("WHALE_PRICE_FLAT_DOWN_MAX_PCT", "0.1"))
WHALE_SHORT_BONUS = float(os.getenv("WHALE_SHORT_BONUS", "25"))
WHALE_LONG_BONUS = float(os.getenv("WHALE_LONG_BONUS", "25"))

FUNDING_CACHE_SEC = int(float(os.getenv("FUNDING_CACHE_SEC", "1800")))
FUNDING_BEARISH_THRESHOLD = float(os.getenv("FUNDING_BEARISH_THRESHOLD", "0.0005"))
FUNDING_BULLISH_THRESHOLD = float(os.getenv("FUNDING_BULLISH_THRESHOLD", "-0.0005"))
FUNDING_SHORT_BONUS = float(os.getenv("FUNDING_SHORT_BONUS", "20"))
FUNDING_LONG_BONUS = float(os.getenv("FUNDING_LONG_BONUS", "20"))

def calc_leveraged_stop_pct(base_pct: float) -> float:
    return max(MIN_STOP_PCT, min(MAX_STOP_PCT, base_pct))

def calc_liquidation_price(entry: float, direction: str) -> float:
    if direction == "LONG":
        return entry * (1 - (0.9 / LEVERAGE))
    return entry * (1 + (0.9 / LEVERAGE))

def calc_margin_required(position_value_usdt: float) -> float:
    return position_value_usdt / max(LEVERAGE, 1)

def calc_position_size_for_risk(entry: float, stop_price: float, portfolio_usdt: float) -> float:
    stop_pct = abs(pct_change(entry, stop_price))
    if stop_pct <= 0:
        return 0.0
    leveraged_loss_pct = stop_pct * LEVERAGE
    max_loss_usdt = portfolio_usdt * (MAX_POSITION_RISK_PCT / 100)
    position_value = max_loss_usdt / (leveraged_loss_pct / 100)
    return position_value

def check_stop_vs_liquidation(entry: float, stop: float, direction: str) -> Tuple[bool, float]:
    liq = calc_liquidation_price(entry, direction)
    if direction == "LONG":
        gap = abs(pct_change(stop, liq))
        safe = stop > liq and gap >= LIQUIDATION_BUFFER
    else:
        gap = abs(pct_change(liq, stop))
        safe = stop < liq and gap >= LIQUIDATION_BUFFER
    return safe, gap

MA_FOLLOWUP_INTERVAL_SEC = int(float(os.getenv("MA_FOLLOWUP_INTERVAL_SEC", "60")))
DYNAMIC_TOP_200_COIN_POOL = os.getenv("DYNAMIC_TOP_200_COIN_POOL", "true").lower() == "true"
ORIGINAL_V527_ENGINE_ENABLED = os.getenv("ORIGINAL_V527_ENGINE_ENABLED", "true").lower() == "true"
RAW_COINS_ENV = os.getenv("COINS", "").strip()

DEFAULT_COINS = [
    "WIF-USDT-SWAP", "PEPE-USDT-SWAP", "1000PEPE-USDT-SWAP", "FET-USDT-SWAP", "INJ-USDT-SWAP",
    "RUNE-USDT-SWAP", "SEI-USDT-SWAP", "TIA-USDT-SWAP", "JUP-USDT-SWAP", "PYTH-USDT-SWAP",
    "ENA-USDT-SWAP", "PENDLE-USDT-SWAP", "TAO-USDT-SWAP", "WLD-USDT-SWAP", "RENDER-USDT-SWAP",
    "RAY-USDT-SWAP", "STX-USDT-SWAP", "MANTA-USDT-SWAP", "GALA-USDT-SWAP",
    "SAND-USDT-SWAP", "AR-USDT-SWAP", "HBAR-USDT-SWAP", "KAS-USDT-SWAP", "CRV-USDT-SWAP",
    "DYDX-USDT-SWAP", "GMT-USDT-SWAP", "ZIL-USDT-SWAP", "ZRX-USDT-SWAP", "API3-USDT-SWAP",
    "BLUR-USDT-SWAP", "ACH-USDT-SWAP", "PEOPLE-USDT-SWAP", "LDO-USDT-SWAP", "ARKM-USDT-SWAP",
    "MEME-USDT-SWAP", "NFP-USDT-SWAP", "STRK-USDT-SWAP", "PORTAL-USDT-SWAP", "ALT-USDT-SWAP",
    "AI-USDT-SWAP", "MAVIA-USDT-SWAP", "AEVO-USDT-SWAP", "OM-USDT-SWAP", "NOT-USDT-SWAP",
    "TURBO-USDT-SWAP", "BRETT-USDT-SWAP", "MEW-USDT-SWAP", "POLYX-USDT-SWAP", "CHZ-USDT-SWAP",
    "ROSE-USDT-SWAP", "ID-USDT-SWAP", "SXP-USDT-SWAP", "IOST-USDT-SWAP", "ONE-USDT-SWAP",
    "CTSI-USDT-SWAP", "HOT-USDT-SWAP", "CELR-USDT-SWAP", "BEL-USDT-SWAP", "FLM-USDT-SWAP",
    "BAKE-USDT-SWAP", "DUSK-USDT-SWAP", "HOOK-USDT-SWAP", "PHB-USDT-SWAP", "MAGIC-USDT-SWAP",
    "RSR-USDT-SWAP", "FLOW-USDT-SWAP", "CFX-USDT-SWAP", "MASK-USDT-SWAP", "SKL-USDT-SWAP",
]
COINS = [x.strip().upper() for x in (RAW_COINS_ENV or ",".join(DEFAULT_COINS)).split(",") if x.strip()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("balina_avcisi_v527_hibrit_onayli")

TZ = ZoneInfo(TIMEZONE_NAME)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BalinaAvcisiV527HibritOnayli/1.0"})

kline_cache: Dict[str, Tuple[float, List[List[Any]]]] = {}
ticker_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
instrument_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
okx_live_symbols: Dict[str, Dict[str, Any]] = {}
symbol_fail_state: Dict[str, Dict[str, Any]] = {}

oi_history: Dict[str, List[Tuple[float, float]]] = {}
oi_cache: Dict[str, Tuple[float, float]] = {}
funding_cache: Dict[str, Tuple[float, float]] = {}

memory: Dict[str, Any] = {
    "hot": {},
    "signals": {},
    "follows": {},
    "stats": {},
    "daily_short_sent": {},
    "last_signal_ts": 0.0,
    "last_diag_ts": 0.0,
}

stats: Dict[str, Any] = {
    "analyzed": 0,
    "no_data": 0,
    "api_fail": 0,
    "telegram_fail": 0,
    "hot_add": 0,
    "hot_promote": 0,
    "signal_sent": 0,
    "followup_sent": 0,
    "rejected": 0,
    "cooldown_reject": 0,
    "cooldown_override": 0,
    "trend_strong_reject": 0,
    "volume_reject": 0,
    "weak_candidate_reject": 0,
    "weak_ready_reject": 0,
    "weak_signal_reject": 0,
    "binance_confirm_pass": 0,
    "binance_confirm_soft": 0,
    "binance_confirm_fail": 0,
    "binance_confirm_unavailable": 0,
    "signal_downgraded_by_binance": 0,
    "daily_short_block": 0,
    "invalid_symbol_skip": 0,
    "blocked_symbol_skip": 0,
    "okx_symbol_pruned": 0,
    "okx_symbol_refresh": 0,
    "okx_symbol_fail_block": 0,
    "ma_signal_sent": 0,
    "ma_long_sent": 0,
    "ma_short_sent": 0,
    "ma_analyzed": 0,
    "whale_oi_calls": 0,
    "whale_oi_fail": 0,
    "whale_divergence_hit": 0,
    "whale_bearish_divergence": 0,
    "whale_bullish_divergence": 0,
    "whale_warmup_skip": 0,
    "funding_calls": 0,
    "funding_fail": 0,
    "funding_short_bonus_hit": 0,
    "funding_long_bonus_hit": 0,
    "institutional_combo_hit": 0,
}

app = None
deep_pointer = 0
memory_lock = asyncio.Lock()

def tr_now() -> datetime:
    return datetime.now(TZ)

def tr_str(ts: Optional[float] = None) -> str:
    dt = datetime.fromtimestamp(ts, TZ) if ts else tr_now()
    return dt.strftime("%d.%m.%Y %H:%M:%S")

def tr_day_key(ts: Optional[float] = None) -> str:
    dt = datetime.fromtimestamp(ts, TZ) if ts else tr_now()
    return dt.strftime("%Y-%m-%d")

def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))

def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def pct_change(a: float, b: float) -> float:
    if a == 0:
        return 0.0
    return ((b - a) / a) * 100.0

def avg(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def ensure_memory_shape() -> None:
    global memory
    if not isinstance(memory, dict):
        memory = {}
    memory.setdefault("hot", {})
    memory.setdefault("signals", {})
    memory.setdefault("follows", {})
    memory.setdefault("stats", {})
    memory.setdefault("ma_signals", {})
    memory.setdefault("ma_follows", {})
    memory.setdefault("ma_last_candle_ts", {})
    memory.setdefault("daily_short_sent", {})
    memory.setdefault("last_signal_ts", 0.0)
    memory.setdefault("last_diag_ts", 0.0)
    memory["stats"].setdefault("ma_long", 0)
    memory["stats"].setdefault("ma_short", 0)
    memory["stats"].setdefault("ma_analyzed", 0)
    memory["stats"].setdefault("ma_tp", 0)
    memory["stats"].setdefault("ma_stop", 0)
    memory["stats"].setdefault("ma_followup", 0)
    memory["stats"].setdefault("whale_bearish_divergence", 0)
    memory["stats"].setdefault("whale_bullish_divergence", 0)
    memory["stats"].setdefault("funding_short_bonus_hit", 0)
    memory["stats"].setdefault("funding_long_bonus_hit", 0)
    memory["stats"].setdefault("institutional_combo_hit", 0)

def load_memory() -> None:
    global memory
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
            ensure_memory_shape()
            logger.info("Memory yüklendi: %s", MEMORY_FILE)
        except Exception as e:
            logger.exception("Memory yüklenemedi: %s", e)
            memory = {
                "hot": {}, "signals": {}, "follows": {}, "stats": {}, "daily_short_sent": {},
                "last_signal_ts": 0.0, "last_diag_ts": 0.0
            }
    else:
        ensure_memory_shape()

def save_memory() -> None:
    last_err = None
    for attempt in range(3):
        try:
            ensure_memory_shape()
            snapshot = copy.deepcopy(memory)
            tmp_path = MEMORY_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, MEMORY_FILE)
            return
        except RuntimeError as e:
            last_err = e
            time.sleep(0.05)
        except Exception as e:
            logger.exception("Memory kaydedilemedi: %s", e)
            return
    logger.warning("Memory snapshot 3 denemede de başarısız: %s", last_err)

async def save_memory_async() -> None:
    async with memory_lock:
        await asyncio.to_thread(save_memory)

def cleanup_symbol_fail_state() -> None:
    now_ts = time.time()
    for sym in list(symbol_fail_state.keys()):
        rec = symbol_fail_state.get(sym, {})
        last_ts = safe_float(rec.get("last_ts", 0))
        block_until = safe_float(rec.get("block_until", 0))
        if block_until and now_ts >= block_until:
            rec["block_until"] = 0.0
            rec["streak"] = 0
        if last_ts and now_ts - last_ts > SYMBOL_FAIL_FORGET_SEC:
            symbol_fail_state.pop(sym, None)

def cleanup_memory() -> None:
    now_ts = time.time()
    hot = memory.get("hot", {})
    for sym in list(hot.keys()):
        last_seen = safe_float(hot[sym].get("last_seen", 0))
        if now_ts - last_seen > HOT_TTL_SEC:
            hot.pop(sym, None)

    follows = memory.get("follows", {})
    for key in list(follows.keys()):
        created = safe_float(follows[key].get("created_ts", 0))
        if now_ts - created > 3 * 24 * 3600:
            follows.pop(key, None)

    daily_short_sent = memory.get("daily_short_sent", {})
    today_key = tr_day_key()
    for day_key in list(daily_short_sent.keys()):
        if day_key != today_key:
            try:
                day_dt = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=TZ)
                if now_ts - day_dt.timestamp() > 7 * 24 * 3600:
                    daily_short_sent.pop(day_key, None)
            except Exception:
                daily_short_sent.pop(day_key, None)

    cleanup_symbol_fail_state()
    cleanup_whale_funding_state()

def cleanup_whale_funding_state() -> None:
    now_ts = time.time()
    cutoff = now_ts - (WHALE_OI_LOOKBACK_MIN * 60 * 3)
    for sym in list(oi_history.keys()):
        hist = oi_history.get(sym, [])
        if not hist or hist[-1][0] < cutoff:
            oi_history.pop(sym, None)
            oi_cache.pop(sym, None)
    funding_cutoff = now_ts - (FUNDING_CACHE_SEC * 3)
    for sym in list(funding_cache.keys()):
        ts, _ = funding_cache[sym]
        if ts < funding_cutoff:
            funding_cache.pop(sym, None)

def note_symbol_fail(symbol: str, reason: str = "") -> None:
    now_ts = time.time()
    rec = symbol_fail_state.setdefault(symbol, {"streak": 0, "last_ts": 0.0, "block_until": 0.0, "last_reason": ""})
    rec["streak"] = int(rec.get("streak", 0)) + 1
    rec["last_ts"] = now_ts
    rec["last_reason"] = str(reason)[:220]
    if rec["streak"] >= max(1, SYMBOL_FAIL_MAX_STREAK):
        already_blocked = safe_float(rec.get("block_until", 0)) > now_ts
        rec["block_until"] = now_ts + SYMBOL_FAIL_BLOCK_SEC
        if not already_blocked:
            stats["okx_symbol_fail_block"] += 1
            logger.warning("Coin geçici bloklandı %s | sebep=%s", symbol, rec["last_reason"])

def note_symbol_success(symbol: str) -> None:
    rec = symbol_fail_state.get(symbol)
    if not rec:
        return
    rec["streak"] = 0
    rec["block_until"] = 0.0
    rec["last_reason"] = ""

def symbol_temporarily_blocked(symbol: str) -> bool:
    rec = symbol_fail_state.get(symbol, {})
    return time.time() < safe_float(rec.get("block_until", 0))

def get_blocked_symbol_count() -> int:
    now_ts = time.time()
    return sum(1 for rec in symbol_fail_state.values() if now_ts < safe_float(rec.get("block_until", 0)))

def _telegram_api_send(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram token/chat_id eksik")
        stats["telegram_fail"] += 1
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    resp = SESSION.post(url, data=payload, timeout=HTTP_TIMEOUT)
    ok = resp.status_code == 200 and resp.json().get("ok") is True
    if not ok:
        logger.error("Telegram API hata: code=%s body=%s", resp.status_code, resp.text[:500])
    return ok

async def safe_send_telegram(text: str, retry: int = 3, delay_sec: float = 1.5) -> bool:
    for i in range(1, retry + 1):
        try:
            ok = await asyncio.to_thread(_telegram_api_send, text)
            if ok:
                return True
        except Exception as e:
            logger.exception("Telegram gönderim hatası deneme %s/%s: %s", i, retry, e)
        await asyncio.sleep(delay_sec * i)
    stats["telegram_fail"] += 1
    return False

def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper().replace("/", "-")
    if s.endswith("-SWAP"):
        return s
    if s.endswith("USDT") and "-" not in s:
        base = s[:-4]
        return f"{base}-USDT-SWAP"
    if s.endswith("-USDT"):
        return f"{s}-SWAP"
    if "-" not in s:
        return f"{s}-USDT-SWAP"
    return s

def _okx_get(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> Any:
    url = f"{OKX_BASE_URL}{path}"
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = SESSION.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                if attempt < max_retries:
                    time.sleep(0.5 + attempt * 0.5)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            data = resp.json()
            if str(data.get("code", "1")) != "0":
                raise RuntimeError(f"OKX hata: code={data.get('code')} msg={data.get('msg')}")
            return data.get("data", [])
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(0.5 + attempt * 0.5)
                continue
            raise
    if last_err:
        raise last_err
    return []

def _okx_to_kline(row: List[Any]) -> List[Any]:
    return [
        row[0], row[1], row[2], row[3], row[4], row[5],
        row[6] if len(row) > 6 else row[5],
        row[7] if len(row) > 7 else row[6] if len(row) > 6 else row[5],
        row[8] if len(row) > 8 else "1",
    ]

async def get_okx_instruments(force: bool = False) -> Dict[str, Dict[str, Any]]:
    cached = instrument_cache.get("okx_instruments")
    now_ts = time.time()
    if cached and not force and now_ts - cached[0] <= OKX_INSTRUMENT_CACHE_SEC:
        return cached[1]
    try:
        data = await asyncio.to_thread(_okx_get, "/api/v5/public/instruments", {"instType": OKX_INST_TYPE})
        mp: Dict[str, Dict[str, Any]] = {}
        for row in data:
            inst_id = str(row.get("instId", "")).upper().strip()
            state = str(row.get("state", "live")).lower().strip()
            if not inst_id:
                continue
            if state and state not in ("live", "normal"):
                continue
            mp[inst_id] = row
        instrument_cache["okx_instruments"] = (now_ts, mp)
        return mp
    except Exception as e:
        stats["api_fail"] += 1
        logger.warning("OKX instruments alınamadı: %s", e)
        return cached[1] if cached else {}

async def refresh_coin_pool(force: bool = False) -> Tuple[int, int]:
    global COINS, okx_live_symbols
    instruments = await get_okx_instruments(force=force)
    if not instruments:
        return len(COINS), stats.get("okx_symbol_pruned", 0)

    okx_live_symbols.clear()
    okx_live_symbols.update(instruments)

    source_symbols = list(COINS)
    if DYNAMIC_TOP_200_COIN_POOL and not RAW_COINS_ENV:
        tickers = await get_24h_tickers()
        top_symbols = pick_top_200_from_tickers(tickers, instruments)
        if top_symbols:
            source_symbols = top_symbols

    valid: List[str] = []
    invalid: List[str] = []
    seen = set()
    for sym in source_symbols:
        ns = normalize_symbol(sym)
        if ns in seen:
            continue
        seen.add(ns)
        if ns in instruments:
            valid.append(ns)
        else:
            invalid.append(ns)

    if valid:
        COINS = valid[:MA_COIN_LIMIT] if DYNAMIC_TOP_200_COIN_POOL else valid

    stats["okx_symbol_refresh"] += 1
    stats["okx_symbol_pruned"] = len(invalid)

    if invalid:
        logger.warning("OKX dışı/pasif coinler çıkarıldı: %s", ", ".join(invalid[:20]))
    logger.info("Aktif coin havuzu yenilendi | aktif=%s | çıkarılan=%s", len(COINS), len(invalid))
    return len(COINS), len(invalid)

async def symbol_refresh_loop() -> None:
    while True:
        try:
            await refresh_coin_pool(force=True)
        except Exception as e:
            logger.exception("symbol_refresh_loop hata: %s", e)
        await asyncio.sleep(max(300, AUTO_SYMBOL_REFRESH_SEC))

async def get_klines(symbol: str, interval: str, limit: int = 120) -> List[List[Any]]:
    symbol = normalize_symbol(symbol)

    if okx_live_symbols and symbol not in okx_live_symbols:
        stats["invalid_symbol_skip"] += 1
        return []

    if symbol_temporarily_blocked(symbol):
        stats["blocked_symbol_skip"] += 1
        return []

    cache_key = f"{symbol}:{interval}:{limit}"
    cached = kline_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= KLINE_CACHE_SEC:
        return cached[1]
    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/market/candles",
            {"instId": symbol, "bar": interval, "limit": min(limit, 300)},
        )
        rows = [_okx_to_kline(x) for x in reversed(data)]
        if not rows:
            stats["api_fail"] += 1
            note_symbol_fail(symbol, f"{interval}:empty")
            return []
        note_symbol_success(symbol)
        kline_cache[cache_key] = (now_ts, rows)
        return rows
    except Exception as e:
        stats["api_fail"] += 1
        note_symbol_fail(symbol, f"{interval}:{e}")
        logger.warning("OKX kline alınamadı %s %s: %s", symbol, interval, e)
        return []

async def get_24h_tickers() -> Dict[str, Dict[str, Any]]:
    cached = ticker_cache.get("24hr")
    now_ts = time.time()
    if cached and now_ts - cached[0] <= TICKER_CACHE_SEC:
        return cached[1]
    try:
        data = await asyncio.to_thread(_okx_get, "/api/v5/market/tickers", {"instType": OKX_INST_TYPE})
        mp = {str(x.get("instId", "")).upper(): x for x in data if x.get("instId")}
        ticker_cache["24hr"] = (now_ts, mp)
        return mp
    except Exception as e:
        stats["api_fail"] += 1
        logger.warning("OKX 24h ticker alınamadı: %s", e)
        return cached[1] if cached else {}

def quote_volume_from_ticker(row: Dict[str, Any]) -> float:
    last = safe_float(row.get("last", 0))
    vol24h = safe_float(row.get("vol24h", 0))
    vol_ccy_24h = safe_float(row.get("volCcy24h", 0))
    return max(vol_ccy_24h, vol24h * max(last, 1e-12))

def pick_top_200_from_tickers(tickers: Dict[str, Dict[str, Any]], instruments: Dict[str, Dict[str, Any]]) -> List[str]:
    rows: List[Tuple[str, float]] = []
    for sym, row in tickers.items():
        ns = normalize_symbol(sym)
        if not ns.endswith("-USDT-SWAP"):
            continue
        if instruments and ns not in instruments:
            continue
        rows.append((ns, quote_volume_from_ticker(row)))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in rows[:MA_COIN_LIMIT]]

def normalize_binance_symbol(symbol: str) -> str:
    s = normalize_symbol(symbol)
    parts = s.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    return s.replace("-", "")

def _binance_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{BINANCE_CONFIRM_BASE_URL}{path}"
    resp = SESSION.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

async def get_binance_klines(symbol: str, interval: str, limit: int = 120) -> List[List[Any]]:
    symbol = normalize_binance_symbol(symbol)
    cache_key = f"BIN:{symbol}:{interval}:{limit}"
    cached = kline_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= KLINE_CACHE_SEC:
        return cached[1]
    try:
        data = await asyncio.to_thread(
            _binance_get,
            "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
        )
        kline_cache[cache_key] = (now_ts, data)
        return data
    except Exception as e:
        logger.warning("Binance teyit kline alınamadı %s %s: %s", symbol, interval, e)
        return []

async def get_binance_last_price(symbol: str) -> float:
    symbol = normalize_binance_symbol(symbol)
    cache_key = f"BIN_PRICE:{symbol}"
    cached = ticker_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= TICKER_CACHE_SEC:
        rec = cached[1]
        return safe_float(rec.get("price", 0))
    try:
        data = await asyncio.to_thread(_binance_get, "/api/v3/ticker/price", {"symbol": symbol})
        ticker_cache[cache_key] = (now_ts, data)
        return safe_float(data.get("price", 0))
    except Exception as e:
        logger.warning("Binance teyit fiyatı alınamadı %s: %s", symbol, e)
        return 0.0

async def confirm_signal_on_binance(res: Dict[str, Any]) -> Dict[str, Any]:
    if not BINANCE_CONFIRM_ENABLED:
        return {
            "status": "DISABLED",
            "score": 0.0,
            "price_gap_pct": 0.0,
            "binance_symbol": normalize_binance_symbol(res["symbol"]),
            "binance_price": 0.0,
            "reason": "Binance teyidi kapalı.",
        }

    symbol = normalize_binance_symbol(res["symbol"])
    k1 = await get_binance_klines(symbol, "1m", 30)
    k5 = await get_binance_klines(symbol, "5m", 15)
    if len(k1) < 15:
        return {
            "status": "UNAVAILABLE",
            "score": 0.0,
            "price_gap_pct": 0.0,
            "binance_symbol": symbol,
            "binance_price": 0.0,
            "reason": "Binance teyit verisi yok.",
        }

    c1 = closes(k1)
    c5 = closes(k5)
    h1 = highs(k1)
    l1 = lows(k1)

    ema9_1 = ema(c1, 9)
    ema21_1 = ema(c1, 21)
    rsi1 = rsi(c1, 14)
    rsi5 = rsi(c5, 14)

    last_price = c1[-1]
    prev_price = c1[-2]
    okx_price = safe_float(res.get("price", 0))
    price_gap_pct = abs(pct_change(okx_price, last_price)) if okx_price > 0 and last_price > 0 else 0.0

    last_kline = k1[-1]
    prev_kline = k1[-2]
    weak_close = last_price <= safe_float(prev_kline[3]) or last_price < safe_float(last_kline[1])
    bear_cross = ema9_1[-1] < ema21_1[-1] and ema9_1[-2] >= ema21_1[-2]
    micro_bear = last_price < prev_price and last_price < ema9_1[-1]
    rej_score = candle_rejection_score(last_kline)
    pump_20m = pct_change(min(c1[-20:]), last_price)
    structure_turn = lower_highs(h1, 3) and lower_lows(l1, 3)

    score = 0.0
    reasons: List[str] = []

    if price_gap_pct <= MAX_BINANCE_OKX_PRICE_GAP_PCT:
        score += 6.0
        reasons.append(f"Fiyat farkı iyi %{price_gap_pct:.2f}")
    elif price_gap_pct <= HARD_BINANCE_OKX_PRICE_GAP_PCT:
        score -= 2.0
        reasons.append(f"Fiyat farkı orta %{price_gap_pct:.2f}")
    else:
        score -= 16.0
        reasons.append(f"Fiyat farkı yüksek %{price_gap_pct:.2f}")

    if micro_bear:
        score += 4.0
        reasons.append("Binance 1dk zayıflıyor")
    if bear_cross:
        score += 5.0
        reasons.append("Binance EMA9/21 aşağı")
    if last_price < ema9_1[-1]:
        score += 4.0
        reasons.append("Binance EMA9 altı")
    if last_price < ema21_1[-1]:
        score += 4.0
        reasons.append("Binance EMA21 altı")
    if rsi1[-1] < 50:
        score += 4.0
        reasons.append("Binance RSI1 gevşek")
    elif rsi1[-1] < 54:
        score += 2.0
        reasons.append("Binance RSI1 sarkıyor")
    if weak_close:
        score += 4.0
        reasons.append("Binance zayıf kapanış")
    if c5[-1] < c5[-2] and c5[-1] < c5[-3]:
        score += 4.0
        reasons.append("Binance 5dk gevşeme")
    if rej_score >= 10:
        score += 3.0
        reasons.append("Binance iğne/red")
    if structure_turn:
        score += 3.0
        reasons.append("Binance yapı dönüyor")

    if pump_20m > 2.6 and last_price > ema9_1[-1] > ema21_1[-1] and rsi1[-1] > 61 and rsi5[-1] > 62 and not weak_close:
        score -= 8.0
        reasons.append("Binance trend hâlâ güçlü")

    if price_gap_pct > HARD_BINANCE_OKX_PRICE_GAP_PCT:
        status = "HARD_FAIL"
    elif score >= BINANCE_CONFIRM_SCORE_PASS:
        status = "PASS"
    elif score >= BINANCE_CONFIRM_SCORE_SOFT:
        status = "SOFT_PASS"
    else:
        status = "FAIL"

    return {
        "status": status,
        "score": round(score, 2),
        "price_gap_pct": round(price_gap_pct, 2),
        "binance_symbol": symbol,
        "binance_price": last_price,
        "reason": " | ".join(reasons[:8]) if reasons else "Binance teyit nedeni yok.",
    }

async def fetch_okx_open_interest(symbol: str) -> Optional[float]:
    """
    OKX /api/v5/public/open-interest?instType=SWAP&instId={symbol}
    OKX v5 kuralları: instType (ZORUNLU) + instId (ZORUNLU) birlikte gönderilir.
    JSON yanıt data[0].oi / data[0].oiCcy try-except içinde güvenli okunur, float döner.
    """
    symbol = normalize_symbol(symbol)
    if not symbol or "-" not in symbol:
        return None
    if symbol_temporarily_blocked(symbol):
        return None

    cached = oi_cache.get(symbol)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= WHALE_OI_CACHE_SEC:
        return cached[1]

    stats["whale_oi_calls"] += 1
    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/public/open-interest",
            {"instType": "SWAP", "instId": symbol},
        )
        if not isinstance(data, list) or len(data) == 0:
            stats["whale_oi_fail"] += 1
            return None

        row = data[0]
        if not isinstance(row, dict):
            stats["whale_oi_fail"] += 1
            return None

        oi_val = 0.0
        oi_str = row.get("oi")
        if oi_str is not None and str(oi_str).strip() != "":
            try:
                oi_val = float(oi_str)
            except (TypeError, ValueError):
                pass

        if oi_val <= 0:
            oi_ccy_str = row.get("oiCcy")
            if oi_ccy_str is not None and str(oi_ccy_str).strip() != "":
                try:
                    oi_ccy_val = float(oi_ccy_str)
                    if oi_ccy_val > 0:
                        oi_val = oi_ccy_val
                except (TypeError, ValueError):
                    pass

        if oi_val > 0:
            oi_cache[symbol] = (now_ts, oi_val)
            return oi_val

        stats["whale_oi_fail"] += 1
        return None
    except Exception as e:
        stats["whale_oi_fail"] += 1
        logger.warning("OKX OI alınamadı %s: %s", symbol, e)
        return None

async def fetch_okx_funding_rate(symbol: str) -> Optional[float]:
    symbol = normalize_symbol(symbol)
    if not symbol or "-" not in symbol:
        return None
    if symbol_temporarily_blocked(symbol):
        return None

    cached = funding_cache.get(symbol)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= FUNDING_CACHE_SEC:
        return cached[1]

    stats["funding_calls"] += 1
    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/public/funding-rate",
            {"instId": symbol},
        )
        if not data:
            stats["funding_fail"] += 1
            return None
        try:
            row = data[0] if isinstance(data, list) else data
            rate = float(row.get("fundingRate", 0) or 0)
        except (TypeError, ValueError, KeyError, IndexError) as e:
            logger.warning("Funding JSON parse hatası %s: %s", symbol, e)
            stats["funding_fail"] += 1
            return None

        if -0.05 < rate < 0.05:
            funding_cache[symbol] = (now_ts, rate)
            return rate
        stats["funding_fail"] += 1
        return None
    except Exception as e:
        stats["funding_fail"] += 1
        logger.warning("OKX funding alınamadı %s: %s", symbol, e)
        return None

def record_oi_snapshot(symbol: str, oi_val: float) -> None:
    if oi_val <= 0:
        return
    now_ts = time.time()
    hist = oi_history.setdefault(symbol, [])
    if hist and now_ts - hist[-1][0] < 1.0:
        return
    hist.append((now_ts, oi_val))
    cutoff = now_ts - (WHALE_OI_LOOKBACK_MIN * 60 * 2)
    if len(hist) > WHALE_OI_HISTORY_MAX or (hist and hist[0][0] < cutoff):
        new_hist = [(t, v) for t, v in hist if t >= cutoff]
        if len(new_hist) > WHALE_OI_HISTORY_MAX:
            new_hist = new_hist[-WHALE_OI_HISTORY_MAX:]
        oi_history[symbol] = new_hist

def calc_oi_change_pct(symbol: str, lookback_sec: float) -> Optional[float]:
    hist = oi_history.get(symbol, [])
    if len(hist) < 2:
        return None
    now_ts = time.time()
    target_ts = now_ts - lookback_sec
    old_entry = None
    for t, v in hist:
        if t <= target_ts:
            old_entry = (t, v)
        else:
            break
    if old_entry is None:
        if now_ts - hist[0][0] < lookback_sec * 0.5:
            return None
        old_entry = hist[0]
    if old_entry[1] <= 0:
        return None
    latest = hist[-1]
    return pct_change(old_entry[1], latest[1])

def detect_whale_divergence(symbol: str, price_change_pct: float) -> Dict[str, Any]:
    base = {
        "divergence": False,
        "type": "NONE",
        "oi_change_pct": 0.0,
        "price_change_pct": round(price_change_pct, 2),
        "short_bonus": 0.0,
        "long_bonus": 0.0,
        "note": "",
    }
    if not WHALE_EYE_ENABLED:
        base["type"] = "DISABLED"
        return base

    oi_change = calc_oi_change_pct(symbol, WHALE_OI_LOOKBACK_MIN * 60)
    if oi_change is None:
        stats["whale_warmup_skip"] += 1
        base["type"] = "NO_DATA"
        base["note"] = f"OI warmup (~{WHALE_OI_LOOKBACK_MIN}dk gerekli)"
        return base

    base["oi_change_pct"] = round(oi_change, 2)

    if price_change_pct >= WHALE_PRICE_FLAT_UP_MIN_PCT and oi_change <= WHALE_OI_BEARISH_DROP_PCT:
        stats["whale_bearish_divergence"] += 1
        stats["whale_divergence_hit"] += 1
        return {
            "divergence": True,
            "type": "BEARISH_DIVERGENCE",
            "oi_change_pct": round(oi_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "short_bonus": WHALE_SHORT_BONUS,
            "long_bonus": 0.0,
            "note": f"🐋 BEARISH DIVERGENCE: Fiyat %{price_change_pct:+.2f} (yatay/yukarı) + OI %{oi_change:+.2f} (sert düşüş) → SHORT +{WHALE_SHORT_BONUS:.0f}",
        }

    if price_change_pct <= WHALE_PRICE_FLAT_DOWN_MAX_PCT and oi_change >= WHALE_OI_BULLISH_RISE_PCT:
        stats["whale_bullish_divergence"] += 1
        stats["whale_divergence_hit"] += 1
        return {
            "divergence": True,
            "type": "BULLISH_DIVERGENCE",
            "oi_change_pct": round(oi_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "short_bonus": 0.0,
            "long_bonus": WHALE_LONG_BONUS,
            "note": f"🐋 BULLISH DIVERGENCE: Fiyat %{price_change_pct:+.2f} (yatay/aşağı) + OI %{oi_change:+.2f} (sert yükseliş) → LONG +{WHALE_LONG_BONUS:.0f}",
        }

    if (price_change_pct > 0 and oi_change > 0) or (price_change_pct < 0 and oi_change < 0):
        base["type"] = "ALIGNED"
        base["note"] = f"OI ile fiyat aynı yönde (%{oi_change:+.2f} / %{price_change_pct:+.2f})"
        return base

    base["type"] = "QUIET"
    return base

def detect_funding_signal(funding_rate: Optional[float]) -> Dict[str, Any]:
    base = {
        "type": "DISABLED" if not FUNDING_EYE_ENABLED else "NO_DATA",
        "funding_rate": 0.0,
        "funding_pct_8h": 0.0,
        "annual_pct": 0.0,
        "short_bonus": 0.0,
        "long_bonus": 0.0,
        "note": "",
    }
    if not FUNDING_EYE_ENABLED or funding_rate is None:
        return base

    base["funding_rate"] = funding_rate
    base["funding_pct_8h"] = round(funding_rate * 100, 4)
    base["annual_pct"] = round(funding_rate * 100 * 3 * 365, 2)

    if funding_rate > FUNDING_BEARISH_THRESHOLD:
        stats["funding_short_bonus_hit"] += 1
        return {
            **base,
            "type": "SHORT_BONUS",
            "short_bonus": FUNDING_SHORT_BONUS,
            "long_bonus": 0.0,
            "note": f"💰 EXTREME POSITIVE FUNDING %{funding_rate*100:+.4f}/8h (yıllık ≈%{base['annual_pct']:+.0f}) → SHORT +{FUNDING_SHORT_BONUS:.0f}",
        }
    if funding_rate < FUNDING_BULLISH_THRESHOLD:
        stats["funding_long_bonus_hit"] += 1
        return {
            **base,
            "type": "LONG_BONUS",
            "short_bonus": 0.0,
            "long_bonus": FUNDING_LONG_BONUS,
            "note": f"💰 EXTREME NEGATIVE FUNDING %{funding_rate*100:+.4f}/8h (yıllık ≈%{base['annual_pct']:+.0f}) → LONG +{FUNDING_LONG_BONUS:.0f}",
        }

    base["type"] = "NEUTRAL"
    return base

async def update_whale_oi(symbol: str) -> Tuple[Optional[float], Optional[float]]:
    oi_now = await fetch_okx_open_interest(symbol)
    if oi_now and oi_now > 0:
        record_oi_snapshot(symbol, oi_now)
    oi_change = calc_oi_change_pct(symbol, WHALE_OI_LOOKBACK_MIN * 60)
    return oi_now, oi_change

def closes(klines: List[List[Any]]) -> List[float]:
    return [safe_float(x[4]) for x in klines]

def highs(klines: List[List[Any]]) -> List[float]:
    return [safe_float(x[2]) for x in klines]

def lows(klines: List[List[Any]]) -> List[float]:
    return [safe_float(x[3]) for x in klines]

def volumes(klines: List[List[Any]]) -> List[float]:
    return [safe_float(x[5]) for x in klines]

def ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    if len(values) < period:
        base = avg(values)
        return [base for _ in values]
    alpha = 2 / (period + 1)
    out = [avg(values[:period])]
    for v in values[period:]:
        out.append((v * alpha) + (out[-1] * (1 - alpha)))
    pad = [out[0]] * (len(values) - len(out))
    return pad + out

def rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return [50.0 for _ in values]
    rsis = [50.0] * len(values)
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))
        if i >= period:
            avg_gain = avg(gains[i - period:i])
            avg_loss = avg(losses[i - period:i])
            rs = 999.0 if avg_loss == 0 else avg_gain / avg_loss
            rsis[i] = 100 - (100 / (1 + rs))
    return rsis

def true_ranges(klines: List[List[Any]]) -> List[float]:
    if len(klines) < 2:
        return [0.0 for _ in klines]
    trs = [0.0]
    for i in range(1, len(klines)):
        high = safe_float(klines[i][2])
        low = safe_float(klines[i][3])
        prev_close = safe_float(klines[i - 1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return trs

def atr(klines: List[List[Any]], period: int = 14) -> List[float]:
    trs = true_ranges(klines)
    return ema(trs, period)

def candle_rejection_score(kline: List[Any]) -> float:
    o = safe_float(kline[1])
    h = safe_float(kline[2])
    l = safe_float(kline[3])
    c = safe_float(kline[4])
    rng = max(h - l, 1e-9)
    upper_wick = h - max(o, c)
    body = abs(c - o)
    score = 0.0
    score += clamp((upper_wick / rng) * 60.0, 0.0, 35.0)
    if c < o:
        score += 10.0
    if body / rng < 0.35:
        score += 5.0
    return score

def lower_highs(values: List[float], n: int = 3) -> bool:
    if len(values) < n:
        return False
    sub = values[-n:]
    return all(sub[i] < sub[i - 1] for i in range(1, len(sub)))

def lower_lows(values: List[float], n: int = 3) -> bool:
    if len(values) < n:
        return False
    sub = values[-n:]
    return all(sub[i] < sub[i - 1] for i in range(1, len(sub)))

def hot_memory_bonus(symbol: str, price: float) -> Tuple[float, float, float, List[str]]:
    rec = memory.get("hot", {}).get(symbol, {})
    if not rec:
        return 0.0, 0.0, 0.0, []
    updates = int(rec.get("updates", 0))
    prev_best = safe_float(rec.get("score", 0))
    first_price = safe_float(rec.get("first_price", 0))
    last_price = safe_float(rec.get("last_price", 0))
    reasons: List[str] = []

    cand_bonus = 0.0
    ready_bonus = 0.0
    verify_bonus = 0.0

    if updates >= 2:
        cand_bonus += 2.0
        ready_bonus += 2.0
        reasons.append("Sıcak hafıza devam")
    if updates >= 4:
        ready_bonus += 2.0
        verify_bonus += 1.0
        reasons.append("Takipte tekrar teyit")
    if prev_best >= MIN_READY_SCORE:
        verify_bonus += 2.0
        reasons.append("Önceki güçlü skor izi")
    if first_price > 0 and price > 0:
        rise_from_first = pct_change(first_price, price)
        if rise_from_first >= 1.0:
            cand_bonus += 2.0
            ready_bonus += 1.0
            reasons.append("İzlemden sonra ekstra şişme")
    if last_price > 0 and price > 0 and price < last_price:
        verify_bonus += 1.0
        reasons.append("Sıcak coin geri kıvırıyor")

    return cand_bonus, ready_bonus, verify_bonus, reasons

async def analyze_symbol(symbol: str, tickers24: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    symbol = normalize_symbol(symbol)

    if okx_live_symbols and symbol not in okx_live_symbols:
        stats["invalid_symbol_skip"] += 1
        return None

    if symbol_temporarily_blocked(symbol):
        stats["blocked_symbol_skip"] += 1
        return None

    if tickers24 and symbol not in tickers24:
        stats["invalid_symbol_skip"] += 1
        return None

    k1 = await get_klines(symbol, "1m", 120)
    k5 = await get_klines(symbol, "5m", 120)
    k15 = await get_klines(symbol, "15m", 120)

    if len(k1) < 50 or len(k5) < 50 or len(k15) < 50:
        stats["no_data"] += 1
        return None

    c1 = closes(k1)
    c5 = closes(k5)
    c15 = closes(k15)
    h1 = highs(k1)
    l1 = lows(k1)
    v1 = volumes(k1)
    v5 = volumes(k5)

    ema9_1 = ema(c1, 9)
    ema21_1 = ema(c1, 21)
    ema50_5 = ema(c5, 50)
    rsi1 = rsi(c1, 14)
    rsi5 = rsi(c5, 14)
    rsi15 = rsi(c15, 14)
    atr1 = atr(k1, 14)
    atr5 = atr(k5, 14)

    last_price = c1[-1]
    prev_price = c1[-2]
    last_rsi1 = rsi1[-1]
    prev_rsi1 = rsi1[-2]
    last_rsi5 = rsi5[-1]
    last_rsi15 = rsi15[-1]
    last_ema9_1 = ema9_1[-1]
    last_ema21_1 = ema21_1[-1]
    last_ema50_5 = ema50_5[-1]
    last_atr1 = max(atr1[-1], last_price * 0.003)
    last_atr5 = max(atr5[-1], last_price * 0.004)

    t24 = tickers24.get(symbol, {})
    last_px_24 = safe_float(t24.get("last", 0)) or last_price
    vol24h = safe_float(t24.get("vol24h", 0))
    vol_ccy_24h = safe_float(t24.get("volCcy24h", 0))
    quote_vol = max(vol_ccy_24h, vol24h * max(last_px_24, 1e-9))
    if quote_vol < MIN_24H_QUOTE_VOLUME:
        stats["volume_reject"] += 1
        return None

    pump_10m = pct_change(min(c1[-10:]), last_price)
    pump_20m = pct_change(min(c1[-20:]), last_price)
    pump_1h = pct_change(min(c5[-12:]), last_price)
    dist_from_ema21 = pct_change(last_ema21_1, last_price)
    vol_ratio_1m = safe_float(v1[-1]) / max(avg(v1[-20:-1]), 1e-9)
    vol_ratio_5m = safe_float(v5[-1]) / max(avg(v5[-12:-1]), 1e-9)

    recent_high_20 = max(h1[-21:-1])
    last_kline = k1[-1]
    prev_kline = k1[-2]
    rej_score = candle_rejection_score(last_kline)

    failed_breakout = safe_float(last_kline[2]) > recent_high_20 and last_price < recent_high_20
    micro_bear = last_price < prev_price and last_price < last_ema9_1
    bear_cross = last_ema9_1 < last_ema21_1 and ema9_1[-2] >= ema21_1[-2]
    losing_momentum = last_rsi1 < prev_rsi1 and last_rsi1 < 60
    weak_close = last_price <= safe_float(prev_kline[3]) or last_price < safe_float(last_kline[1])
    structure_turn = lower_highs(h1, 3) and lower_lows(l1, 3)

    strong_breakout_continue = (
        pump_20m > 2.8 and
        last_price > last_ema9_1 > last_ema21_1 and
        last_rsi1 > 66 and
        last_rsi5 > 66 and
        rej_score < 10 and
        not weak_close and
        not structure_turn
    )

    if strong_breakout_continue:
        stats["trend_strong_reject"] += 1
        return {
            "symbol": symbol,
            "stage": "RED",
            "reason": "Trend çok güçlü, short için erken değil geç kalınır.",
            "score": 0,
        }

    candidate_score = 0.0
    ready_score = 0.0
    verify_score = 0.0
    reasons: List[str] = []

    if pump_10m >= 0.8:
        candidate_score += 9
        reasons.append(f"10dk pump %{pump_10m:.2f}")
    if pump_20m >= 1.35:
        candidate_score += 11
        reasons.append(f"20dk pump %{pump_20m:.2f}")
    if pump_1h >= 2.5:
        candidate_score += 10
        reasons.append(f"1s pump %{pump_1h:.2f}")
    if last_rsi5 >= 64:
        candidate_score += 9
        reasons.append(f"5dk RSI {last_rsi5:.1f}")
    if dist_from_ema21 >= 0.55:
        candidate_score += 9
        reasons.append(f"EMA21 üstü %{dist_from_ema21:.2f}")
    if vol_ratio_1m >= 1.45:
        candidate_score += 8
        reasons.append(f"1dk hacim x{vol_ratio_1m:.2f}")
    if vol_ratio_5m >= 1.25:
        candidate_score += 6
        reasons.append(f"5dk hacim x{vol_ratio_5m:.2f}")

    if rej_score >= 10:
        ready_score += clamp(rej_score, 0, 18)
        reasons.append(f"İğne/red {rej_score:.1f}")
    if failed_breakout:
        ready_score += 13
        reasons.append("Sahte kırılım")
    if micro_bear:
        ready_score += 9
        reasons.append("1dk zayıf kapanış")
    if bear_cross:
        ready_score += 9
        reasons.append("EMA9/21 kısa zayıflama")
    if losing_momentum:
        ready_score += 7
        reasons.append("RSI momentum düşüşü")
    if structure_turn:
        ready_score += 10
        reasons.append("Alt yapı bozuluyor")

    if last_price < last_ema9_1:
        verify_score += 10
        reasons.append("Fiyat EMA9 altı")
    if last_price < last_ema21_1:
        verify_score += 8
        reasons.append("Fiyat EMA21 altı")
    if last_rsi1 < 50:
        verify_score += 8
        reasons.append("1dk RSI 50 altı")
    elif last_rsi1 < 54:
        verify_score += 4
        reasons.append("1dk RSI gevşiyor")
    if weak_close:
        verify_score += 8
        reasons.append("Zayıf son mum")
    if c5[-1] < c5[-2] and c5[-1] < c5[-3]:
        verify_score += 8
        reasons.append("5dk gevşeme")
    if last_rsi15 >= 56:
        verify_score += 5
        reasons.append("15dk hâlâ şişkin")
    if last_price > last_ema50_5:
        verify_score += 4
        reasons.append("5dk EMA50 üstünde, dönüş alanı var")

    cand_bonus, ready_bonus, verify_bonus, bonus_reasons = hot_memory_bonus(symbol, last_price)
    candidate_score += cand_bonus
    ready_score += ready_bonus
    verify_score += verify_bonus
    reasons.extend(bonus_reasons)

    if WHALE_EYE_ENABLED and len(c1) >= WHALE_OI_LOOKBACK_MIN + 1:
        price_change_for_whale = pct_change(c1[-(WHALE_OI_LOOKBACK_MIN + 1)], last_price)
    else:
        price_change_for_whale = pump_20m

    whale_oi_value: Optional[float] = None
    whale_payload: Dict[str, Any] = {
        "divergence": False, "type": "DISABLED", "oi_change_pct": 0.0,
        "price_change_pct": round(price_change_for_whale, 2),
        "short_bonus": 0.0, "long_bonus": 0.0, "note": "",
    }
    funding_rate_value: Optional[float] = None
    funding_payload: Dict[str, Any] = {
        "type": "DISABLED", "funding_rate": 0.0, "funding_pct_8h": 0.0,
        "annual_pct": 0.0, "short_bonus": 0.0, "long_bonus": 0.0, "note": "",
    }

    if WHALE_EYE_ENABLED:
        try:
            whale_oi_value, _ = await update_whale_oi(symbol)
            whale_payload = detect_whale_divergence(symbol, price_change_for_whale)
            whale_short_bonus = safe_float(whale_payload.get("short_bonus", 0))
            if whale_short_bonus > 0:
                verify_score += whale_short_bonus
                if whale_payload.get("note"):
                    reasons.append(whale_payload["note"])
        except Exception as e:
            logger.warning("Whale Eye hata %s: %s", symbol, e)

    if FUNDING_EYE_ENABLED:
        try:
            funding_rate_value = await fetch_okx_funding_rate(symbol)
            funding_payload = detect_funding_signal(funding_rate_value)
            funding_short_bonus = safe_float(funding_payload.get("short_bonus", 0))
            if funding_short_bonus > 0:
                verify_score += funding_short_bonus
                if funding_payload.get("note"):
                    reasons.append(funding_payload["note"])
        except Exception as e:
            logger.warning("Funding Eye hata %s: %s", symbol, e)

    institutional_combo_short = (
        whale_payload.get("type") == "BEARISH_DIVERGENCE"
        and funding_payload.get("type") == "SHORT_BONUS"
    )
    if institutional_combo_short:
        stats["institutional_combo_hit"] += 1
        reasons.append("🐋💰 KURUMSAL KOMBO: OI Bearish Divergence + Extreme Positive Funding")

    if pump_10m < 0.55 and pump_20m < 1.0:
        candidate_score -= 4
        reasons.append("Pump zayıf")
    if vol_ratio_1m < 0.95 and vol_ratio_5m < 0.95:
        ready_score -= 3
        reasons.append("Hacim sönük")
    if last_rsi15 < 49:
        candidate_score -= 3
        reasons.append("15dk çok şişkin değil")

    candidate_score = max(candidate_score, 0.0)
    ready_score = max(ready_score, 0.0)
    verify_score = max(verify_score, 0.0)

    total_score = candidate_score + ready_score + verify_score

    if candidate_score < MIN_CANDIDATE_SCORE:
        stats["weak_candidate_reject"] += 1
        stage = "IGNORE"
    elif (candidate_score + ready_score) < MIN_READY_SCORE:
        stage = "HOT"
        stats["hot_add"] += 1
    elif total_score < MIN_SIGNAL_SCORE:
        stage = "READY"
        stats["weak_signal_reject"] += 1
    else:
        stage = "SIGNAL"

    entry = last_price

    base_stop_dist = last_atr1 * 2.5
    base_stop_pct = base_stop_dist / entry
    adjusted_stop_pct = calc_leveraged_stop_pct(base_stop_pct)
    adjusted_stop_dist = entry * adjusted_stop_pct

    stop = entry + adjusted_stop_dist
    tp1 = entry - (adjusted_stop_dist * 1.8)
    tp2 = entry - (adjusted_stop_dist * 3.0)
    tp3 = entry - (adjusted_stop_dist * 4.0)
    rr = (entry - tp1) / max(stop - entry, 1e-9)

    liq_safe_v5, liq_gap_v5 = check_stop_vs_liquidation(entry, stop, "SHORT")
    if not liq_safe_v5 and LEVERAGE > 1:
        logger.warning("V5 sinyal RED (likidasyon riski): %s | kaldıraç=%sx | gap=%.2f%%", symbol, LEVERAGE, liq_gap_v5)
        return None

    if rr < 0.72 and stage == "SIGNAL":
        stage = "READY"
        total_score -= 5
        reasons.append("RR zayıf, sinyal kademe düşürüldü")

    return {
        "symbol": symbol,
        "stage": stage,
        "score": round(total_score, 2),
        "candidate_score": round(candidate_score, 2),
        "ready_score": round(ready_score, 2),
        "verify_score": round(verify_score, 2),
        "price": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr": round(rr, 2),
        "pump_10m": round(pump_10m, 2),
        "pump_20m": round(pump_20m, 2),
        "pump_1h": round(pump_1h, 2),
        "rsi1": round(last_rsi1, 2),
        "rsi5": round(last_rsi5, 2),
        "rsi15": round(last_rsi15, 2),
        "vol_ratio_1m": round(vol_ratio_1m, 2),
        "vol_ratio_5m": round(vol_ratio_5m, 2),
        "quote_volume": quote_vol,
        "whale_enabled": WHALE_EYE_ENABLED,
        "whale_divergence": bool(whale_payload.get("divergence", False)),
        "whale_type": whale_payload.get("type", "NONE"),
        "whale_oi_value": whale_oi_value if whale_oi_value is not None else 0.0,
        "whale_oi_change_pct": safe_float(whale_payload.get("oi_change_pct", 0)),
        "whale_price_change_pct": safe_float(whale_payload.get("price_change_pct", 0)),
        "whale_short_bonus": safe_float(whale_payload.get("short_bonus", 0)),
        "whale_long_bonus": safe_float(whale_payload.get("long_bonus", 0)),
        "whale_note": whale_payload.get("note", ""),
        "funding_enabled": FUNDING_EYE_ENABLED,
        "funding_type": funding_payload.get("type", "NONE"),
        "funding_rate": safe_float(funding_payload.get("funding_rate", 0)),
        "funding_pct_8h": safe_float(funding_payload.get("funding_pct_8h", 0)),
        "funding_annual_pct": safe_float(funding_payload.get("annual_pct", 0)),
        "funding_short_bonus": safe_float(funding_payload.get("short_bonus", 0)),
        "funding_long_bonus": safe_float(funding_payload.get("long_bonus", 0)),
        "funding_note": funding_payload.get("note", ""),
        "institutional_combo": institutional_combo_short,
        "reason": " | ".join(reasons[:10]) if reasons else "Sebep yok",
    }

def sma(values: List[float], period: int) -> List[float]:
    out: List[float] = []
    for i in range(len(values)):
        if i + 1 < period:
            out.append(0.0)
        else:
            window = values[i + 1 - period:i + 1]
            out.append(sum(window) / period)
    return out

def calc_ma_targets(entry: float, direction: str) -> Dict[str, float]:
    stop_pct = calc_leveraged_stop_pct(MA_STOP_PCT)
    tp1_pct = max(MA_TP1_PCT, stop_pct * 1.8)
    tp2_pct = max(MA_TP2_PCT, stop_pct * 3.0)
    tp3_pct = max(MA_TP3_PCT, stop_pct * 4.5)

    if direction == "SHORT":
        return {
            "stop": entry * (1 + stop_pct),
            "tp1": entry * (1 - tp1_pct),
            "tp2": entry * (1 - tp2_pct),
            "tp3": entry * (1 - tp3_pct),
            "stop_pct": round(stop_pct * 100, 2),
            "tp1_pct": round(tp1_pct * 100, 2),
            "tp2_pct": round(tp2_pct * 100, 2),
            "tp3_pct": round(tp3_pct * 100, 2),
        }
    return {
        "stop": entry * (1 - stop_pct),
        "tp1": entry * (1 + tp1_pct),
        "tp2": entry * (1 + tp2_pct),
        "tp3": entry * (1 + tp3_pct),
        "stop_pct": round(stop_pct * 100, 2),
        "tp1_pct": round(tp1_pct * 100, 2),
        "tp2_pct": round(tp2_pct * 100, 2),
        "tp3_pct": round(tp3_pct * 100, 2),
    }

def calc_support_resistance(klines: List[List[Any]], price: float, lookback: int = MA_SUPPORT_RESISTANCE_LOOKBACK) -> Dict[str, float]:
    prev_rows = klines[:-1]
    if not prev_rows:
        return {"support": 0.0, "resistance": 0.0, "support_diff_pct": 0.0, "resistance_diff_pct": 0.0}

    rows = prev_rows[-max(5, lookback):]
    low_values = [safe_float(x[3]) for x in rows if safe_float(x[3]) > 0]
    high_values = [safe_float(x[2]) for x in rows if safe_float(x[2]) > 0]

    below_supports = [x for x in low_values if x <= price]
    above_resistances = [x for x in high_values if x >= price]

    support = max(below_supports) if below_supports else (min(low_values) if low_values else 0.0)
    resistance = min(above_resistances) if above_resistances else (max(high_values) if high_values else 0.0)

    support_diff = abs(pct_change(support, price)) if support > 0 and price > 0 else 0.0
    resistance_diff = abs(pct_change(price, resistance)) if resistance > 0 and price > 0 else 0.0

    return {
        "support": support,
        "resistance": resistance,
        "support_diff_pct": round(support_diff, 4),
        "resistance_diff_pct": round(resistance_diff, 4),
    }

def _build_ma_result(symbol: str, direction: str, k1h: List[List[Any]], ma7: List[float], ma25: List[float]) -> Optional[Dict[str, Any]]:
    if len(k1h) < 3 or len(ma7) < 3 or len(ma25) < 3:
        return None

    prev_ma7 = ma7[-3]
    prev_ma25 = ma25[-3]
    cur_ma7 = ma7[-2]
    cur_ma25 = ma25[-2]

    last_candle = k1h[-2]
    candle_ts = str(last_candle[0])
    candle_open = safe_float(last_candle[1])
    candle_high = safe_float(last_candle[2])
    candle_low = safe_float(last_candle[3])
    last_price = safe_float(last_candle[4])

    ts_key = f"{symbol}:{direction}"
    if memory.get("ma_last_candle_ts", {}).get(ts_key) == candle_ts:
        return None

    entry = 0.0
    entry_note = ""
    entry_diff_pct = 0.0

    if direction == "SHORT":
        if not (prev_ma7 >= prev_ma25 and cur_ma7 <= cur_ma25):
            return None
        if candle_high <= 0 or last_price <= 0:
            return None
        entry_diff_pct = abs(((candle_high - last_price) / candle_high) * 100.0)
        if entry_diff_pct > MA_ENTRY_MAX_DIFF_PCT:
            return None
        entry = last_price
        entry_note = f"SHORT giriş: güncel fiyat {MA_KLINE_INTERVAL} mum tepesine en fazla %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın"

    elif direction == "LONG":
        if not (prev_ma7 <= prev_ma25 and cur_ma7 >= cur_ma25):
            return None
        if candle_low <= 0 or last_price <= 0:
            return None
        entry_diff_pct = abs(((last_price - candle_low) / candle_low) * 100.0)
        if entry_diff_pct > MA_ENTRY_MAX_DIFF_PCT:
            return None
        entry = last_price
        entry_note = f"LONG giriş: güncel fiyat {MA_KLINE_INTERVAL} mum dibine en fazla %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın"
    else:
        return None

    if entry <= 0:
        return None

    targets = calc_ma_targets(entry, direction)

    liq_safe, liq_gap = check_stop_vs_liquidation(entry, targets["stop"], direction)
    if not liq_safe and LEVERAGE > 1:
        logger.warning("MA sinyal RED (likidasyon riski): %s %s | stop=%s liq=%s | kaldıraç=%sx | mesafe=%.2f%%",
                       symbol, direction, fmt_num(targets["stop"]),
                       fmt_num(calc_liquidation_price(entry, direction)), LEVERAGE, liq_gap)
        return None

    sr = calc_support_resistance(k1h, entry)

    if direction == "SHORT":
        if safe_float(sr.get("resistance_diff_pct", 0)) > SHORT_MAX_RESISTANCE_DIFF_PCT:
            return None
        if safe_float(sr.get("support_diff_pct", 0)) < SHORT_MIN_SUPPORT_DIFF_PCT:
            return None
        # Yeni: destek üst limiti (0 = limit yok)
        if SHORT_MAX_SUPPORT_DIFF_PCT > 0 and safe_float(sr.get("support_diff_pct", 0)) > SHORT_MAX_SUPPORT_DIFF_PCT:
            return None
        # Yeni: direnç alt limiti (0 = kapalı)
        if SHORT_MIN_RESISTANCE_DIFF_PCT > 0 and safe_float(sr.get("resistance_diff_pct", 0)) < SHORT_MIN_RESISTANCE_DIFF_PCT:
            return None

    if direction == "LONG":
        if safe_float(sr.get("support_diff_pct", 0)) > LONG_MAX_SUPPORT_DIFF_PCT:
            return None
        if safe_float(sr.get("resistance_diff_pct", 0)) < LONG_MIN_RESISTANCE_DIFF_PCT:
            return None
        # Yeni: direnç üst limiti (0 = limit yok)
        if LONG_MAX_RESISTANCE_DIFF_PCT > 0 and safe_float(sr.get("resistance_diff_pct", 0)) > LONG_MAX_RESISTANCE_DIFF_PCT:
            return None
        # Yeni: destek alt limiti (0 = kapalı)
        if LONG_MIN_SUPPORT_DIFF_PCT > 0 and safe_float(sr.get("support_diff_pct", 0)) < LONG_MIN_SUPPORT_DIFF_PCT:
            return None

    liq_price = calc_liquidation_price(entry, direction)
    position_value = calc_position_size_for_risk(entry, targets["stop"], DEFAULT_MARGIN_USDT * LEVERAGE)
    margin_needed = calc_margin_required(position_value)

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "last_price": last_price,
        "candle_open": candle_open,
        "candle_high": candle_high,
        "candle_low": candle_low,
        "entry_diff_pct": round(entry_diff_pct, 4),
        "max_entry_diff_pct": MA_ENTRY_MAX_DIFF_PCT,
        "support": sr["support"],
        "resistance": sr["resistance"],
        "support_diff_pct": sr["support_diff_pct"],
        "resistance_diff_pct": sr["resistance_diff_pct"],
        "short_max_resistance_diff_pct": SHORT_MAX_RESISTANCE_DIFF_PCT,
        "short_min_support_diff_pct": SHORT_MIN_SUPPORT_DIFF_PCT,
        "long_max_support_diff_pct": LONG_MAX_SUPPORT_DIFF_PCT,
        "long_min_resistance_diff_pct": LONG_MIN_RESISTANCE_DIFF_PCT,
        "stop": targets["stop"],
        "tp1": targets["tp1"],
        "tp2": targets["tp2"],
        "tp3": targets["tp3"],
        "stop_pct": targets.get("stop_pct", MA_STOP_PCT * 100),
        "tp1_pct": targets.get("tp1_pct", MA_TP1_PCT * 100),
        "tp2_pct": targets.get("tp2_pct", MA_TP2_PCT * 100),
        "tp3_pct": targets.get("tp3_pct", MA_TP3_PCT * 100),
        "leverage": LEVERAGE,
        "liquidation_price": liq_price,
        "liq_gap_pct": round(abs(pct_change(targets["stop"], liq_price)), 2),
        "margin_example": round(margin_needed, 2),
        "position_value_example": round(position_value, 2),
        "max_risk_pct": MAX_POSITION_RISK_PCT,
        "ma7": cur_ma7,
        "ma25": cur_ma25,
        "prev_ma7": prev_ma7,
        "prev_ma25": prev_ma25,
        "candle_ts": candle_ts,
        "timeframe": MA_KLINE_INTERVAL,
        "entry_note": entry_note,
    }

async def _prepare_ma_data(symbol: str) -> Optional[Tuple[str, List[List[Any]], List[float], List[float]]]:
    symbol = normalize_symbol(symbol)
    k1h = await get_klines(symbol, MA_KLINE_INTERVAL, 80)
    if len(k1h) < 30:
        return None

    c = closes(k1h)
    # DÜZELTME: Grafikteki MA7/MA25 çizgileri SMA'dır (basit ortalama).
    # Önceden ema() kullanılıyordu — bu, grafikte görünen MA ile farklı değer
    # ürettiği için "grafikte cross yok ama bot sinyal atıyor" sorununa yol açıyordu.
    ma7 = sma(c, 7)
    ma25 = sma(c, 25)
    if ma7[-2] <= 0 or ma25[-2] <= 0 or ma7[-1] <= 0 or ma25[-1] <= 0:
        return None
    return symbol, k1h, ma7, ma25

async def analyze_ma_long_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, k1h, ma7, ma25 = prepared
    return _build_ma_result(sym, "LONG", k1h, ma7, ma25)

async def analyze_ma_short_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, k1h, ma7, ma25 = prepared
    return _build_ma_result(sym, "SHORT", k1h, ma7, ma25)

async def analyze_ma_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, k1h, ma7, ma25 = prepared
    long_res = _build_ma_result(sym, "LONG", k1h, ma7, ma25)
    if long_res:
        return long_res
    return _build_ma_result(sym, "SHORT", k1h, ma7, ma25)

def ma_signal_key(res: Dict[str, Any]) -> str:
    return f"MA:{res['symbol']}:{res['direction']}:{res['candle_ts']}"

def ma_already_sent(res: Dict[str, Any]) -> bool:
    return bool(memory.get("ma_signals", {}).get(ma_signal_key(res)))

def mark_ma_sent(res: Dict[str, Any]) -> None:
    key = ma_signal_key(res)
    sent_ts = time.time()
    memory.setdefault("ma_signals", {})[key] = {
        "ts": sent_ts,
        "symbol": res["symbol"],
        "direction": res["direction"],
        "entry": res["entry"],
        "candle_ts": res["candle_ts"],
    }
    memory.setdefault("ma_follows", {})[key] = {
        "done": False,
        "sent_ts": sent_ts,
        "key": key,
        "symbol": res["symbol"],
        "direction": res["direction"],
        "entry": res["entry"],
        "stop": res["stop"],
        "tp1": res["tp1"],
        "tp2": res["tp2"],
        "tp3": res["tp3"],
        "support": res.get("support", 0),
        "resistance": res.get("resistance", 0),
        "timeframe": res.get("timeframe", MA_KLINE_INTERVAL),
    }
    memory.setdefault("stats", {})["ma_analyzed"] = int(memory.get("stats", {}).get("ma_analyzed", 0))
    if res["direction"] == "SHORT":
        memory["stats"]["ma_short"] = int(memory["stats"].get("ma_short", 0)) + 1
        stats["ma_short_sent"] += 1
    else:
        memory["stats"]["ma_long"] = int(memory["stats"].get("ma_long", 0)) + 1
        stats["ma_long_sent"] += 1
    stats["ma_signal_sent"] += 1
    memory["last_signal_ts"] = sent_ts
    memory.setdefault("ma_last_candle_ts", {})[f"{res['symbol']}:{res['direction']}"] = res.get("candle_ts", "")

    # /hafiza için sayaç
    h = memory.setdefault("ma_hafiza", {})
    h["total_sent"] = int(h.get("total_sent", 0)) + 1
    if res["direction"] == "SHORT":
        h["short_sent"] = int(h.get("short_sent", 0)) + 1
    else:
        h["long_sent"] = int(h.get("long_sent", 0)) + 1

async def enrich_ma_with_institutional(res: Dict[str, Any]) -> Dict[str, Any]:
    if not res:
        return res
    symbol = res.get("symbol", "")
    direction = res.get("direction", "")
    if not symbol or not direction:
        return res

    res.setdefault("institutional_oi_change_pct", 0.0)
    res.setdefault("institutional_oi_bonus", 0.0)
    res.setdefault("institutional_funding_rate", 0.0)
    res.setdefault("institutional_funding_pct_8h", 0.0)
    res.setdefault("institutional_funding_annual_pct", 0.0)
    res.setdefault("institutional_funding_bonus", 0.0)
    res.setdefault("institutional_total_bonus", 0.0)
    res.setdefault("institutional_confirmed", False)
    res.setdefault("institutional_notes", [])

    if WHALE_EYE_ENABLED:
        try:
            oi_now = await fetch_okx_open_interest(symbol)
            if oi_now and oi_now > 0:
                record_oi_snapshot(symbol, oi_now)
            oi_change = calc_oi_change_pct(symbol, WHALE_OI_LOOKBACK_MIN * 60)
            if oi_change is not None:
                res["institutional_oi_change_pct"] = round(oi_change, 2)
                k1m = await get_klines(symbol, "1m", WHALE_OI_LOOKBACK_MIN + 5)
                if len(k1m) >= WHALE_OI_LOOKBACK_MIN + 1:
                    c = closes(k1m)
                    price_change = pct_change(c[-(WHALE_OI_LOOKBACK_MIN + 1)], c[-1])
                    if direction == "LONG":
                        if (price_change <= WHALE_PRICE_FLAT_DOWN_MAX_PCT
                                and oi_change >= WHALE_OI_BULLISH_RISE_PCT):
                            res["institutional_oi_bonus"] = WHALE_LONG_BONUS
                            res["institutional_notes"].append(
                                f"🐋 BULLISH DIVERGENCE: Fiyat %{price_change:+.2f} + OI %{oi_change:+.2f} → +{WHALE_LONG_BONUS:.0f}"
                            )
                            stats["whale_bullish_divergence"] += 1
                            stats["whale_divergence_hit"] += 1
                    elif direction == "SHORT":
                        if (price_change >= WHALE_PRICE_FLAT_UP_MIN_PCT
                                and oi_change <= WHALE_OI_BEARISH_DROP_PCT):
                            res["institutional_oi_bonus"] = WHALE_SHORT_BONUS
                            res["institutional_notes"].append(
                                f"🐋 BEARISH DIVERGENCE: Fiyat %{price_change:+.2f} + OI %{oi_change:+.2f} → +{WHALE_SHORT_BONUS:.0f}"
                            )
                            stats["whale_bearish_divergence"] += 1
                            stats["whale_divergence_hit"] += 1
        except Exception as e:
            logger.warning("MA institutional OI enrichment hata %s: %s", symbol, e)

    if FUNDING_EYE_ENABLED:
        try:
            funding_rate = await fetch_okx_funding_rate(symbol)
            if funding_rate is not None:
                res["institutional_funding_rate"] = funding_rate
                res["institutional_funding_pct_8h"] = round(funding_rate * 100, 4)
                res["institutional_funding_annual_pct"] = round(funding_rate * 100 * 3 * 365, 2)
                f_signal = detect_funding_signal(funding_rate)
                if direction == "LONG" and f_signal.get("type") == "LONG_BONUS":
                    res["institutional_funding_bonus"] = FUNDING_LONG_BONUS
                    res["institutional_notes"].append(f_signal.get("note", ""))
                elif direction == "SHORT" and f_signal.get("type") == "SHORT_BONUS":
                    res["institutional_funding_bonus"] = FUNDING_SHORT_BONUS
                    res["institutional_notes"].append(f_signal.get("note", ""))
        except Exception as e:
            logger.warning("MA institutional funding enrichment hata %s: %s", symbol, e)

    total_bonus = res["institutional_oi_bonus"] + res["institutional_funding_bonus"]
    res["institutional_total_bonus"] = total_bonus
    if res["institutional_oi_bonus"] > 0 and res["institutional_funding_bonus"] > 0:
        res["institutional_confirmed"] = True
        stats["institutional_combo_hit"] += 1
        res["institutional_notes"].append(
            f"🐋💰 KURUMSAL KOMBO TEYİDİ — OI + Funding aynı yönde (+{total_bonus:.0f} toplam bonus)"
        )

    return res

async def maybe_send_ma_signal(res: Dict[str, Any]) -> None:
    if not res:
        return
    symbol = res.get("symbol", "")
    direction = res.get("direction", "")

    if ma_already_sent(res):
        return

    try:
        res = await enrich_ma_with_institutional(res)
    except Exception as e:
        logger.warning("MA institutional enrichment hata %s %s: %s", symbol, direction, e)

    try:
        msg = build_ma_signal_message(res)
    except Exception as e:
        logger.exception("MA mesajı oluşturulamadı %s %s: %s", symbol, direction, e)
        return

    ok = await safe_send_telegram(msg)
    if ok:
        async with memory_lock:
            mark_ma_sent(res)
        logger.info("MA TELEGRAM GÖNDERİLDİ %s %s entry=%s candle=%s",
                    symbol, direction, fmt_num(safe_float(res.get("entry", 0))), res.get("candle_ts", "-"))
    else:
        logger.warning("MA TELEGRAM GÖNDERİLEMEDİ %s %s", symbol, direction)

def ma_performance_summary() -> Dict[str, Any]:
    stats_mem = memory.setdefault("stats", {})
    long_sent = int(stats_mem.get("ma_long", 0))
    short_sent = int(stats_mem.get("ma_short", 0))

    long_tp = 0
    long_stop = 0
    short_tp = 0
    short_stop = 0

    follows = memory.get("ma_follows", {})
    if isinstance(follows, dict):
        for rec in follows.values():
            if not isinstance(rec, dict) or not rec.get("done"):
                continue
            direction = str(rec.get("direction", "")).upper()
            result = str(rec.get("result", "")).upper()
            if direction == "LONG":
                if result.startswith("TP"):
                    long_tp += 1
                elif result == "STOP":
                    long_stop += 1
            elif direction == "SHORT":
                if result.startswith("TP"):
                    short_tp += 1
                elif result == "STOP":
                    short_stop += 1

    long_resolved = long_tp + long_stop
    short_resolved = short_tp + short_stop
    long_success = (long_tp / long_resolved * 100.0) if long_resolved > 0 else 0.0
    short_success = (short_tp / short_resolved * 100.0) if short_resolved > 0 else 0.0

    return {
        "long_sent": long_sent,
        "short_sent": short_sent,
        "long_tp": long_tp,
        "long_stop": long_stop,
        "short_tp": short_tp,
        "short_stop": short_stop,
        "long_resolved": long_resolved,
        "short_resolved": short_resolved,
        "long_success": long_success,
        "short_success": short_success,
    }

def build_ma_signal_message(res: Dict[str, Any]) -> str:
    lev = safe_float(res.get('leverage', 1))
    stop_pct = safe_float(res.get('stop_pct', MA_STOP_PCT * 100))
    tp1_pct = safe_float(res.get('tp1_pct', MA_TP1_PCT * 100))
    tp2_pct = safe_float(res.get('tp2_pct', MA_TP2_PCT * 100))
    tp3_pct = safe_float(res.get('tp3_pct', MA_TP3_PCT * 100))
    liq = safe_float(res.get('liquidation_price', 0))
    liq_gap = safe_float(res.get('liq_gap_pct', 0))
    margin_ex = safe_float(res.get('margin_example', 0))
    pos_val = safe_float(res.get('position_value_example', 0))
    max_risk = safe_float(res.get('max_risk_pct', MAX_POSITION_RISK_PCT))

    position_loss_at_stop = stop_pct * lev

    risk_warning = ""
    if lev >= 20:
        risk_warning = f"⚠️ YÜKSEK KALDIRAÇ {lev}x | Pozisyon kaybı stopta: %{position_loss_at_stop:.1f}\n"

    institutional_block = ""
    inst_oi_bonus = safe_float(res.get("institutional_oi_bonus", 0))
    inst_funding_bonus = safe_float(res.get("institutional_funding_bonus", 0))
    inst_total = safe_float(res.get("institutional_total_bonus", 0))
    inst_oi_change = safe_float(res.get("institutional_oi_change_pct", 0))
    inst_funding_pct = safe_float(res.get("institutional_funding_pct_8h", 0))
    inst_funding_annual = safe_float(res.get("institutional_funding_annual_pct", 0))

    if inst_oi_bonus > 0 or inst_funding_bonus > 0:
        institutional_block += "---\n"
        if res.get("institutional_confirmed"):
            institutional_block += f"🐋💰 KURUMSAL KOMBO TEYİDİ (toplam +{inst_total:.0f} bonus)\n"
        if inst_oi_bonus > 0:
            institutional_block += f"🐋 OI Divergence: +{inst_oi_bonus:.0f} | OI {WHALE_OI_LOOKBACK_MIN}dk: %{inst_oi_change:+.2f}\n"
        if inst_funding_bonus > 0:
            institutional_block += f"💰 Funding bonus: +{inst_funding_bonus:.0f} | %{inst_funding_pct:+.4f}/8h (yıllık ≈%{inst_funding_annual:+.0f})\n"

    return (
        f"🚨 {VERSION_NAME} - MA7/MA25 {res['timeframe']} - {res['direction']} AL\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"Motor: {res['direction']} MOTORU\n"
        f"Zaman dilimi: {res.get('timeframe', MA_KLINE_INTERVAL)}\n"
        f"Kural: MA7 / MA25 KAPANMIŞ mum kesişimi (repainting önlendi)\n"
        f"{res['entry_note']}\n"
        f"MA7: {fmt_num(res['ma7'])}\n"
        f"MA25: {fmt_num(res['ma25'])}\n"
        f"Mum tepe: {fmt_num(res['candle_high'])}\n"
        f"Mum dip: {fmt_num(res['candle_low'])}\n"
        f"Güncel: {fmt_num(res['last_price'])}\n"
        f"Dip/tepe farkı: %{safe_float(res.get('entry_diff_pct', 0)):.2f} / max %{safe_float(res.get('max_entry_diff_pct', MA_ENTRY_MAX_DIFF_PCT)):.2f}\n"
        f"Destek: {fmt_num(safe_float(res.get('support', 0)))} | fark %{safe_float(res.get('support_diff_pct', 0)):.2f}\n"
        f"Direnç: {fmt_num(safe_float(res.get('resistance', 0)))} | fark %{safe_float(res.get('resistance_diff_pct', 0)):.2f}\n"
        f"SHORT S/R: direnç max %{SHORT_MAX_RESISTANCE_DIFF_PCT:.2f} | destek min %{SHORT_MIN_SUPPORT_DIFF_PCT:.2f}\n"
        f"LONG S/R: destek max %{LONG_MAX_SUPPORT_DIFF_PCT:.2f} | direnç min %{LONG_MIN_RESISTANCE_DIFF_PCT:.2f}\n"
        f"{institutional_block}"
        f"---\n"
        f"KALDIRAÇ: {lev}x | Max Risk/Pozisyon: %{max_risk:.1f}\n"
        f"{risk_warning}"
        f"Entry: {fmt_num(res['entry'])}\n"
        f"Stop: {fmt_num(res['stop'])} (%{stop_pct:.2f})\n"
        f"TP1: {fmt_num(res['tp1'])} (%{tp1_pct:.2f})\n"
        f"TP2: {fmt_num(res['tp2'])} (%{tp2_pct:.2f})\n"
        f"TP3: {fmt_num(res['tp3'])} (%{tp3_pct:.2f})\n"
        f"Likidasyon: {fmt_num(liq)} (stop ile arası: %{liq_gap:.2f})\n"
        f"Örnek: {pos_val:.0f} USDT pozisyon = {margin_ex:.2f} USDT marj"
    )

def detect_ma_followup_events(rec: Dict[str, Any], klines_1m: List[List[Any]]) -> List[Dict[str, Any]]:
    """TP1/TP2/TP3 ve Stop olaylarını sırasıyla yakalar.
    Daha önce kaydedilmemiş olayları döner. rec içine zaman damgalarını yazar.
    """
    direction = str(rec.get("direction", "")).upper()
    entry = safe_float(rec.get("entry", 0))
    stop = safe_float(rec.get("stop", 0))
    tp1 = safe_float(rec.get("tp1", 0))
    tp2 = safe_float(rec.get("tp2", 0))
    tp3 = safe_float(rec.get("tp3", 0))
    if direction not in ("LONG", "SHORT") or entry <= 0 or stop <= 0 or tp1 <= 0:
        return []

    sent_ts = safe_float(rec.get("sent_ts", 0))
    start_ms = max(0.0, (sent_ts - 60.0) * 1000.0)

    tp1_done = safe_float(rec.get("tp1_hit_ts", 0)) > 0
    tp2_done = safe_float(rec.get("tp2_hit_ts", 0)) > 0
    tp3_done = safe_float(rec.get("tp3_hit_ts", 0)) > 0

    events: List[Dict[str, Any]] = []

    for row in klines_1m:
        row_ts_ms = safe_float(row[0])
        if row_ts_ms < start_ms:
            continue
        ts_sec = row_ts_ms / 1000.0
        high = safe_float(row[2])
        low = safe_float(row[3])
        if high <= 0 or low <= 0:
            continue

        hit_stop = (low <= stop) if direction == "LONG" else (high >= stop)

        new_tps: List[Tuple[str, float]] = []
        if direction == "LONG":
            if not tp1_done and high >= tp1:
                new_tps.append(("TP1", tp1)); tp1_done = True
            if not tp2_done and high >= tp2:
                new_tps.append(("TP2", tp2)); tp2_done = True
            if not tp3_done and high >= tp3:
                new_tps.append(("TP3", tp3)); tp3_done = True
        else:
            if not tp1_done and low <= tp1:
                new_tps.append(("TP1", tp1)); tp1_done = True
            if not tp2_done and low <= tp2:
                new_tps.append(("TP2", tp2)); tp2_done = True
            if not tp3_done and low <= tp3:
                new_tps.append(("TP3", tp3)); tp3_done = True

        for lvl, price in new_tps:
            rec[f"{lvl.lower()}_hit_ts"] = ts_sec
            events.append({"type": lvl, "price": price, "ts": ts_sec})

        if hit_stop:
            if tp1_done or tp2_done or tp3_done:
                rec["stop_after_tp_ts"] = ts_sec
                events.append({"type": "STOP_AFTER_TP", "price": stop, "ts": ts_sec})
            else:
                rec["stop_ts"] = ts_sec
                events.append({"type": "STOP", "price": stop, "ts": ts_sec})
            break

        if tp3_done:
            break

    return events


def detect_ma_followup_result(rec: Dict[str, Any], klines_1m: List[List[Any]]) -> Optional[Dict[str, Any]]:
    """Geriye uyumluluk: ilk olayı döndür (eski fonksiyonun davranışını korur)."""
    direction = str(rec.get("direction", "")).upper()
    sent_ts = safe_float(rec.get("sent_ts", 0))
    entry = safe_float(rec.get("entry", 0))
    stop = safe_float(rec.get("stop", 0))
    tp1 = safe_float(rec.get("tp1", 0))
    tp2 = safe_float(rec.get("tp2", 0))
    tp3 = safe_float(rec.get("tp3", 0))
    if direction not in ("LONG", "SHORT") or entry <= 0 or stop <= 0 or tp1 <= 0:
        return None

    start_ms = max(0.0, (sent_ts - 60.0) * 1000.0)
    for row in klines_1m:
        row_ts = safe_float(row[0])
        if row_ts < start_ms:
            continue
        high = safe_float(row[2])
        low = safe_float(row[3])
        if high <= 0 or low <= 0:
            continue

        hit_stop = False
        hit_tp = ""
        hit_price = 0.0

        if direction == "LONG":
            hit_stop = low <= stop
            if high >= tp3:
                hit_tp = "TP3"
                hit_price = tp3
            elif high >= tp2:
                hit_tp = "TP2"
                hit_price = tp2
            elif high >= tp1:
                hit_tp = "TP1"
                hit_price = tp1
        else:
            hit_stop = high >= stop
            if low <= tp3:
                hit_tp = "TP3"
                hit_price = tp3
            elif low <= tp2:
                hit_tp = "TP2"
                hit_price = tp2
            elif low <= tp1:
                hit_tp = "TP1"
                hit_price = tp1

        if hit_stop and hit_tp:
            return {
                "result": "AYNI_1M_MUMDA_STOP_TP",
                "level": hit_tp,
                "price": hit_price,
                "stop": stop,
                "touch_ts": row_ts / 1000.0,
            }
        if hit_tp:
            return {"result": hit_tp, "level": hit_tp, "price": hit_price, "touch_ts": row_ts / 1000.0}
        if hit_stop:
            return {"result": "STOP", "level": "STOP", "price": stop, "touch_ts": row_ts / 1000.0}

    return None

def build_ma_followup_message(rec: Dict[str, Any], hit: Dict[str, Any]) -> str:
    direction = str(rec.get("direction", ""))
    entry = safe_float(rec.get("entry", 0))
    result = str(hit.get("result", ""))
    result_price = safe_float(hit.get("price", 0))
    if result == "STOP":
        pnl_pct = pct_change(entry, result_price)
        if direction == "SHORT":
            pnl_pct *= -1
        title = "❌ STOP GELDİ"
    elif result == "AYNI_1M_MUMDA_STOP_TP":
        pnl_pct = pct_change(entry, result_price)
        if direction == "SHORT":
            pnl_pct *= -1
        title = f"⚠️ AYNI 1M MUMDA STOP VE {hit.get('level', 'TP')} TEMASI"
    else:
        pnl_pct = pct_change(entry, result_price)
        if direction == "SHORT":
            pnl_pct *= -1
        title = f"✅ {result} GELDİ"

    return (
        f"⏱ MA7/MA25 TP/STOP TAKİP\n"
        f"{title}\n"
        f"Saat: {tr_str()} | İlk temas: {tr_str(safe_float(hit.get('touch_ts', 0)))}\n"
        f"Coin: {rec.get('symbol')}\n"
        f"Yön: {direction}\n"
        f"Entry: {fmt_num(entry)}\n"
        f"Sonuç fiyatı: {fmt_num(result_price)}\n"
        f"Stop: {fmt_num(safe_float(rec.get('stop', 0)))}\n"
        f"TP1: {fmt_num(safe_float(rec.get('tp1', 0)))}\n"
        f"TP2: {fmt_num(safe_float(rec.get('tp2', 0)))}\n"
        f"TP3: {fmt_num(safe_float(rec.get('tp3', 0)))}\n"
        f"Destek: {fmt_num(safe_float(rec.get('support', 0)))}\n"
        f"Direnç: {fmt_num(safe_float(rec.get('resistance', 0)))}\n"
        f"Sonuç: {result}\n"
        f"Fiyat hareketi: %{pnl_pct:.2f}"
    )

async def check_ma_followups() -> None:
    if not MA_FOLLOWUP_ENABLED:
        return
    follows = memory.get("ma_follows", {})
    if not follows:
        return

    for key, rec in list(follows.items()):
        if rec.get("done"):
            continue
        symbol = str(rec.get("symbol", ""))
        if not symbol:
            continue
        k1m = await get_klines(symbol, "1m", 300)
        if not k1m:
            continue

        events = detect_ma_followup_events(rec, k1m)
        if not events:
            continue

        h = memory.setdefault("ma_hafiza", {})
        direction_key = str(rec.get("direction", "")).lower()
        any_msg = False

        for ev in events:
            ev_type = str(ev.get("type", ""))

            if ev_type == "TP1":
                # Eskisi gibi tam mesaj
                msg = build_ma_followup_message(rec, {
                    "result": "TP1", "level": "TP1",
                    "price": ev["price"], "touch_ts": ev["ts"],
                })
                await safe_send_telegram(msg)
                any_msg = True
                h["total_tp1"] = int(h.get("total_tp1", 0)) + 1
                h[f"{direction_key}_tp1"] = int(h.get(f"{direction_key}_tp1", 0)) + 1
                # Eski sayaçları da çalıştır
                memory.setdefault("stats", {})["ma_followup"] = int(memory.get("stats", {}).get("ma_followup", 0)) + 1
                memory["stats"]["ma_tp"] = int(memory["stats"].get("ma_tp", 0)) + 1
                rec["result"] = "TP1"
                rec["result_price"] = ev["price"]
                rec["touch_ts"] = ev["ts"]

            elif ev_type == "TP2":
                # Sessiz — sadece hafıza
                h["total_tp2"] = int(h.get("total_tp2", 0)) + 1
                h[f"{direction_key}_tp2"] = int(h.get(f"{direction_key}_tp2", 0)) + 1

            elif ev_type == "TP3":
                # Sessiz — sadece hafıza, takip biter
                h["total_tp3"] = int(h.get("total_tp3", 0)) + 1
                h[f"{direction_key}_tp3"] = int(h.get(f"{direction_key}_tp3", 0)) + 1
                rec["done"] = True

            elif ev_type == "STOP":
                # Hiç TP yokken stop — tam mesaj
                msg = build_ma_followup_message(rec, {
                    "result": "STOP", "level": "STOP",
                    "price": ev["price"], "touch_ts": ev["ts"],
                })
                await safe_send_telegram(msg)
                any_msg = True
                h["total_stop"] = int(h.get("total_stop", 0)) + 1
                h[f"{direction_key}_stop"] = int(h.get(f"{direction_key}_stop", 0)) + 1
                memory.setdefault("stats", {})["ma_followup"] = int(memory.get("stats", {}).get("ma_followup", 0)) + 1
                memory["stats"]["ma_stop"] = int(memory["stats"].get("ma_stop", 0)) + 1
                rec["result"] = "STOP"
                rec["result_price"] = ev["price"]
                rec["touch_ts"] = ev["ts"]
                rec["done"] = True

            elif ev_type == "STOP_AFTER_TP":
                # Kısa mesaj — TP sonrası stop
                tp_list = []
                if safe_float(rec.get("tp1_hit_ts", 0)) > 0:
                    tp_list.append("TP1")
                if safe_float(rec.get("tp2_hit_ts", 0)) > 0:
                    tp_list.append("TP2")
                tp_str = "+".join(tp_list) if tp_list else "TP"
                short_msg = (
                    f"⚠️ {symbol} {rec.get('direction', '')}: {tp_str} sonrası STOP\n"
                    f"Stop fiyat: {fmt_num(ev['price'])}"
                )
                await safe_send_telegram(short_msg)
                any_msg = True
                h["total_stop_after_tp"] = int(h.get("total_stop_after_tp", 0)) + 1
                h[f"{direction_key}_stop_after_tp"] = int(h.get(f"{direction_key}_stop_after_tp", 0)) + 1
                rec["done"] = True

        await save_memory_async()

def signal_key(symbol: str, stage: str) -> str:
    return f"{symbol}:{stage}"

def get_signal_record(symbol: str, stage: str) -> Dict[str, Any]:
    return memory.get("signals", {}).get(signal_key(symbol, stage), {})

def setup_record(symbol: str) -> Dict[str, Any]:
    return memory.get("signals", {}).get(f"setup:{symbol}", {})

def setup_in_cooldown(symbol: str) -> bool:
    rec = setup_record(symbol)
    ts = safe_float(rec.get("ts", 0))
    return time.time() - ts < SETUP_COOLDOWN_MIN * 60

def better_than_previous(symbol: str, stage: str, payload: Dict[str, Any]) -> bool:
    prev = get_signal_record(symbol, stage)
    prev_score = safe_float(prev.get("score", 0))
    prev_price = safe_float(prev.get("price", 0))
    cur_score = safe_float(payload.get("score", 0))
    cur_price = safe_float(payload.get("price", 0))

    price_move_pct = abs(pct_change(prev_price, cur_price)) if prev_price > 0 and cur_price > 0 else 0.0
    if cur_score >= prev_score + SCORE_OVERRIDE_GAP:
        return True
    if cur_score >= prev_score + (SCORE_OVERRIDE_GAP * 0.7) and price_move_pct >= PRICE_OVERRIDE_MOVE_PCT:
        return True
    return False

def daily_short_record(symbol: str, day_key: Optional[str] = None) -> Dict[str, Any]:
    return memory.get("daily_short_sent", {}).get(day_key or tr_day_key(), {}).get(symbol, {})

def daily_short_already_sent(symbol: str, day_key: Optional[str] = None) -> bool:
    return bool(daily_short_record(symbol, day_key))

def set_daily_short_sent(symbol: str, payload: Dict[str, Any]) -> None:
    day_key = tr_day_key()
    daily = memory.setdefault("daily_short_sent", {}).setdefault(day_key, {})
    daily[symbol] = {
        "ts": time.time(),
        "score": payload.get("score"),
        "price": payload.get("price"),
        "reason": payload.get("reason", ""),
    }

def get_today_short_sent_count() -> int:
    return len(memory.get("daily_short_sent", {}).get(tr_day_key(), {}))

def should_block_signal(symbol: str, stage: str, payload: Dict[str, Any]) -> bool:
    if stage == "SIGNAL" and daily_short_already_sent(symbol):
        return True

    now_ts = time.time()
    sig_rec = get_signal_record(symbol, stage)
    sig_ts = safe_float(sig_rec.get("ts", 0))
    if sig_ts and now_ts - sig_ts < ALERT_COOLDOWN_MIN * 60:
        if better_than_previous(symbol, stage, payload):
            stats["cooldown_override"] += 1
            return False
        return True

    if setup_in_cooldown(symbol):
        if better_than_previous(symbol, stage, payload):
            stats["cooldown_override"] += 1
            return False
        return True

    return False

def set_signal_memory(symbol: str, stage: str, payload: Dict[str, Any]) -> None:
    memory.setdefault("signals", {})[signal_key(symbol, stage)] = {
        "ts": time.time(),
        "stage": stage,
        "price": payload.get("price"),
        "score": payload.get("score"),
    }
    memory.setdefault("signals", {})[f"setup:{symbol}"] = {
        "ts": time.time(),
        "stage": stage,
        "price": payload.get("price"),
        "score": payload.get("score"),
    }
    if stage == "SIGNAL":
        set_daily_short_sent(symbol, payload)
    memory["last_signal_ts"] = time.time()

def update_hot_memory(res: Dict[str, Any]) -> None:
    sym = res["symbol"]
    hot = memory.setdefault("hot", {})
    rec = hot.get(sym, {})
    old_price = safe_float(rec.get("first_price", 0))
    if old_price <= 0:
        old_price = safe_float(res.get("price", 0))
    hot[sym] = {
        "first_seen": rec.get("first_seen", time.time()),
        "last_seen": time.time(),
        "first_price": old_price,
        "last_price": res.get("price"),
        "score": max(safe_float(rec.get("score", 0)), safe_float(res.get("score", 0))),
        "reason": res.get("reason", ""),
        "updates": int(rec.get("updates", 0)) + 1,
        "last_rise_notice_ts": safe_float(rec.get("last_rise_notice_ts", 0)),
    }

def fmt_num(v: float) -> str:
    if v >= 1000:
        return f"{v:,.4f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if v >= 1:
        return f"{v:.4f}"
    return f"{v:.6f}"

def build_signal_message(res: Dict[str, Any]) -> str:
    confirm_status = str(res.get("binance_confirm_status", "YOK"))
    binance_symbol = str(res.get("binance_symbol", "-"))
    binance_price = safe_float(res.get("binance_price", 0))
    binance_gap = safe_float(res.get("binance_price_gap_pct", 0))
    binance_reason = str(res.get("binance_confirm_reason", "-"))
    data_engine = str(res.get("data_engine", "OKX SWAP"))

    stop_pct_v5 = abs(pct_change(res['price'], res['stop']))
    pos_loss_v5 = stop_pct_v5 * LEVERAGE
    liq_v5 = calc_liquidation_price(res['price'], "SHORT")
    liq_gap_v5 = abs(pct_change(res['stop'], liq_v5))

    risk_line = ""
    if LEVERAGE >= 20:
        risk_line = f"⚠️ YÜKSEK KALDIRAÇ {LEVERAGE}x | Stopta pozisyon kaybı: %{pos_loss_v5:.1f}\n"

    whale_line = ""
    if res.get("whale_enabled"):
        whale_type = str(res.get("whale_type", "NONE"))
        whale_oi_change = safe_float(res.get("whale_oi_change_pct", 0))
        whale_price_change = safe_float(res.get("whale_price_change_pct", 0))
        whale_short_bonus = safe_float(res.get("whale_short_bonus", 0))
        if res.get("whale_divergence") and whale_short_bonus > 0:
            whale_line = (
                f"🐋 BEARISH DIVERGENCE (+{whale_short_bonus:.0f} puan)\n"
                f"   Fiyat {WHALE_OI_LOOKBACK_MIN}dk: %{whale_price_change:+.2f} | OI: %{whale_oi_change:+.2f}\n"
            )
        elif whale_type == "NO_DATA":
            whale_line = f"🐋 Whale Eye: OI warmup devam ediyor\n"
        elif whale_type == "ALIGNED":
            whale_line = f"🐋 Whale Eye: OI ve fiyat aynı yönde (divergence yok)\n"

    funding_line = ""
    if res.get("funding_enabled"):
        funding_type = str(res.get("funding_type", "NONE"))
        funding_pct_8h = safe_float(res.get("funding_pct_8h", 0))
        funding_annual = safe_float(res.get("funding_annual_pct", 0))
        funding_short_bonus = safe_float(res.get("funding_short_bonus", 0))
        if funding_type == "SHORT_BONUS" and funding_short_bonus > 0:
            funding_line = (
                f"💰 EXTREME POSITIVE FUNDING (+{funding_short_bonus:.0f} puan)\n"
                f"   Funding: %{funding_pct_8h:+.4f}/8h | Yıllık ≈%{funding_annual:+.1f}\n"
            )
        elif funding_type == "NEUTRAL":
            funding_line = f"💰 Funding: NEUTRAL (%{funding_pct_8h:+.4f}/8h)\n"

    combo_line = ""
    if res.get("institutional_combo"):
        combo_line = "🐋💰 KURUMSAL KOMBO TEYİDİ: OI Bearish + Funding Crowded Long\n"

    return (
        f"🚨 {VERSION_NAME} SHORT AL\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"KALDIRAÇ: {LEVERAGE}x | Max Risk/Pozisyon: %{MAX_POSITION_RISK_PCT:.1f}\n"
        f"{risk_line}"
        f"{whale_line}"
        f"{funding_line}"
        f"{combo_line}"
        f"Veri motoru: {data_engine}\n"
        f"Binance teyit: {confirm_status}\n"
        f"Binance sembol: {binance_symbol}\n"
        f"Skor: {res['score']}\n"
        f"Aday/Hazır/Doğrula: {res['candidate_score']} / {res['ready_score']} / {res['verify_score']}\n"
        f"OKX fiyat: {fmt_num(res['price'])}\n"
        f"Binance fiyat: {fmt_num(binance_price) if binance_price > 0 else '-'}\n"
        f"OKX-Binance farkı: %{binance_gap:.2f}\n"
        f"Entry: {fmt_num(res['price'])}\n"
        f"Stop: {fmt_num(res['stop'])} (%{stop_pct_v5:.2f})\n"
        f"TP1: {fmt_num(res['tp1'])}\n"
        f"TP2: {fmt_num(res['tp2'])}\n"
        f"TP3: {fmt_num(res['tp3'])}\n"
        f"RR(TP1): {res['rr']}\n"
        f"Likidasyon: {fmt_num(liq_v5)} (stop ile arası: %{liq_gap_v5:.2f})\n"
        f"10dk/20dk/1s Pump: %{res['pump_10m']} / %{res['pump_20m']} / %{res['pump_1h']}\n"
        f"RSI 1/5/15: {res['rsi1']} / {res['rsi5']} / {res['rsi15']}\n"
        f"Hacim 1/5: x{res['vol_ratio_1m']} / x{res['vol_ratio_5m']}\n"
        f"Not: {res['reason']}\n"
        f"Binance notu: {binance_reason}"
    )

def build_hot_message(res: Dict[str, Any]) -> str:
    return (
        f"🔥 SICAK TAKİP\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"Skor: {res['score']}\n"
        f"Fiyat: {fmt_num(res['price'])}\n"
        f"Durum: Şimdilik net short AL değil, ama sıcak takibe alındı.\n"
        f"Not: {res['reason']}"
    )

def build_ready_message(res: Dict[str, Any]) -> str:
    return (
        f"🟠 İNCE TAKİP\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"Skor: {res['score']}\n"
        f"Fiyat: {fmt_num(res['price'])}\n"
        f"Not: Zemin oluşuyor ama son teyit bekleniyor. {res['reason']}"
    )

def build_heartbeat_message() -> str:
    hot_count = len(memory.get("hot", {}))
    last_sig = safe_float(memory.get("last_signal_ts", 0))
    last_sig_txt = tr_str(last_sig) if last_sig else "Yok"
    ma_perf = ma_performance_summary()
    oi_coins_tracked = len(oi_history)
    return (
        f"💓 {VERSION_NAME} DURUM\n"
        f"Saat: {tr_str()}\n"
        f"KALDIRAÇ: {LEVERAGE}x | Max Risk/Pozisyon: %{MAX_POSITION_RISK_PCT:.1f}\n"
        f"Toplam coin: {len(COINS)} / hedef {MA_COIN_LIMIT}\n"
        f"MA motoru: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'}\n"
        f"🐋 Whale Eye: {'AÇIK' if WHALE_EYE_ENABLED else 'KAPALI'} | İzlenen: {oi_coins_tracked} | Lookback: {WHALE_OI_LOOKBACK_MIN}dk\n"
        f"🐋 OI çağrı/fail: {stats['whale_oi_calls']} / {stats['whale_oi_fail']}\n"
        f"🐋 Bearish/Bullish div: {stats['whale_bearish_divergence']} / {stats['whale_bullish_divergence']} | Warmup skip: {stats['whale_warmup_skip']}\n"
        f"💰 Funding Eye: {'AÇIK' if FUNDING_EYE_ENABLED else 'KAPALI'}\n"
        f"💰 Funding çağrı/fail: {stats['funding_calls']} / {stats['funding_fail']}\n"
        f"💰 SHORT/LONG bonus hit: {stats['funding_short_bonus_hit']} / {stats['funding_long_bonus_hit']}\n"
        f"🐋💰 Kurumsal Kombo: {stats['institutional_combo_hit']}\n"
        f"LONG sinyal: {ma_perf['long_sent']} | Başarı: %{ma_perf['long_success']:.1f} | TP={ma_perf['long_tp']} Stop={ma_perf['long_stop']}\n"
        f"SHORT sinyal: {ma_perf['short_sent']} | Başarı: %{ma_perf['short_success']:.1f} | TP={ma_perf['short_tp']} Stop={ma_perf['short_stop']}\n"
        f"Sıcak coin: {hot_count}\n"
        f"Bloklu coin: {get_blocked_symbol_count()}\n"
        f"Çıkarılan coin: {stats['okx_symbol_pruned']}\n"
        f"Son sinyal: {last_sig_txt}\n"
        f"Analiz: {stats['analyzed']}\n"
        f"Gönderilen sinyal: {stats['signal_sent']}\n"
        f"Takibe alınan: {stats['hot_add']}\n"
        f"Bugün atılan short coin: {get_today_short_sent_count()}\n"
        f"Cooldown override: {stats['cooldown_override']}\n"
        f"Binance teyit pass/soft/fail: {stats['binance_confirm_pass']} / {stats['binance_confirm_soft']} / {stats['binance_confirm_fail']}\n"
        f"Binance teyit yok: {stats['binance_confirm_unavailable']}\n"
        f"API fail: {stats['api_fail']}\n"
        f"Telegram fail: {stats['telegram_fail']}\n"
        f"Red: weak_candidate={stats['weak_candidate_reject']}, weak_signal={stats['weak_signal_reject']}, cooldown={stats['cooldown_reject']}, daily_short={stats['daily_short_block']}, invalid={stats['invalid_symbol_skip']}, blocked={stats['blocked_symbol_skip']}"
    )

def build_diagnostic_message() -> str:
    hot_count = len(memory.get("hot", {}))
    last_sig = safe_float(memory.get("last_signal_ts", 0))
    no_sig_min = int((time.time() - last_sig) / 60) if last_sig else -1
    return (
        f"🛠 SİNYAL TEŞHİS RAPORU\n"
        f"Saat: {tr_str()}\n"
        f"Son AL üzerinden geçen süre: {no_sig_min if no_sig_min >= 0 else 'Hiç yok'} dk\n"
        f"Sıcak coin sayısı: {hot_count}\n"
        f"Bloklu coin: {get_blocked_symbol_count()}\n"
        f"Çıkarılan coin: {stats['okx_symbol_pruned']}\n"
        f"Analiz: {stats['analyzed']}\n"
        f"Zayıf aday red: {stats['weak_candidate_reject']}\n"
        f"Hazır ama final değil: {stats['weak_signal_reject']}\n"
        f"Cooldown red: {stats['cooldown_reject']}\n"
        f"Günlük short blok: {stats['daily_short_block']}\n"
        f"Cooldown override: {stats['cooldown_override']}\n"
        f"Binance teyit fail: {stats['binance_confirm_fail']}\n"
        f"Binance teyit yok: {stats['binance_confirm_unavailable']}\n"
        f"Trend çok güçlü red: {stats['trend_strong_reject']}\n"
        f"Hacim red: {stats['volume_reject']}\n"
        f"Geçersiz coin skip: {stats['invalid_symbol_skip']}\n"
        f"Geçici blok skip: {stats['blocked_symbol_skip']}\n"
        f"Fail yüzünden bloklanan coin: {stats['okx_symbol_fail_block']}\n"
        f"API fail: {stats['api_fail']}\n"
        f"Telegram fail: {stats['telegram_fail']}\n"
        f"Yorum: Bu sürümde analiz mantığı korunur; sadece veri tarafı temizlenir ve aynı coin tekrar spam yapmaz."
    )

async def maybe_send_signal(res: Dict[str, Any]) -> None:
    symbol = res["symbol"]
    stage = res["stage"]

    if stage == "SIGNAL":
        logger.info("SIGNAL ÜRETİLDİ %s skor=%s", symbol, res.get("score"))

        if daily_short_already_sent(symbol):
            stats["daily_short_block"] += 1
            logger.info("GÜNLÜK SHORT KİLİDİ %s", symbol)
            return

        confirm = await confirm_signal_on_binance(res)
        res["data_engine"] = "OKX SWAP"
        res["binance_confirm_status"] = confirm.get("status", "YOK")
        res["binance_confirm_score"] = confirm.get("score", 0)
        res["binance_symbol"] = confirm.get("binance_symbol", normalize_binance_symbol(symbol))
        res["binance_price"] = confirm.get("binance_price", 0)
        res["binance_price_gap_pct"] = confirm.get("price_gap_pct", 0)
        res["binance_confirm_reason"] = confirm.get("reason", "-")

        confirm_status = str(confirm.get("status", "YOK"))
        if confirm_status == "PASS":
            stats["binance_confirm_pass"] += 1
        elif confirm_status == "SOFT_PASS":
            stats["binance_confirm_soft"] += 1
        elif confirm_status in ("FAIL", "HARD_FAIL"):
            stats["binance_confirm_fail"] += 1
            stats["signal_downgraded_by_binance"] += 1
            logger.info("BINANCE TEYİDİ RED %s status=%s", symbol, confirm_status)
            downgraded = dict(res)
            downgraded["stage"] = "READY"
            downgraded["reason"] = f"{res.get('reason', '')} | Binance teyidi zayıf: {confirm.get('reason', '-')}"
            update_hot_memory(downgraded)
            return
        elif confirm_status == "UNAVAILABLE":
            stats["binance_confirm_unavailable"] += 1
            if BINANCE_CONFIRM_REQUIRED and safe_float(res.get("score", 0)) < BINANCE_CONFIRM_FAIL_OPEN_SCORE:
                stats["signal_downgraded_by_binance"] += 1
                logger.info("BINANCE TEYİDİ YOK, SİNYAL DÜŞÜRÜLDÜ %s", symbol)
                downgraded = dict(res)
                downgraded["stage"] = "READY"
                downgraded["reason"] = f"{res.get('reason', '')} | Binance teyidi yok, takipte tutuldu."
                update_hot_memory(downgraded)
                return
        elif confirm_status == "DISABLED":
            pass

        if should_block_signal(symbol, "SIGNAL", res):
            stats["cooldown_reject"] += 1
            logger.info("COOLDOWN RED %s skor=%s", symbol, res.get("score"))
            return

        ok = await safe_send_telegram(build_signal_message(res))
        if ok:
            logger.info("TELEGRAM GÖNDERİLDİ %s", symbol)
            stats["signal_sent"] += 1
            set_signal_memory(symbol, "SIGNAL", res)
            memory.setdefault("follows", {})[symbol] = {
                "created_ts": time.time(),
                "symbol": symbol,
                "entry": res["price"],
                "stop": res["stop"],
                "tp1": res["tp1"],
                "tp2": res["tp2"],
                "tp3": res["tp3"],
                "stage": "SIGNAL",
                "done": False,
                "sent_ts": time.time(),
            }
            memory.get("hot", {}).pop(symbol, None)
        else:
            logger.warning("TELEGRAM GÖNDERİLEMEDİ %s", symbol)
        return

    if stage in ("READY", "HOT"):
        logger.info("TAKİP AŞAMASI %s stage=%s skor=%s", symbol, stage, res.get("score"))
        update_hot_memory(res)
        return

async def maybe_send_hot_rise_updates() -> None:
    hot = memory.get("hot", {})
    if not hot:
        return
    tickers24 = await get_24h_tickers()
    now_ts = time.time()
    for sym, rec in list(hot.items()):
        first_price = safe_float(rec.get("first_price", 0))
        last_notice = safe_float(rec.get("last_rise_notice_ts", 0))
        t = tickers24.get(sym, {})
        cur = safe_float(t.get("last", 0))
        if first_price <= 0 or cur <= 0:
            continue
        rise_pct = pct_change(first_price, cur)
        if rise_pct >= 1.2 and (now_ts - last_notice > 1800):
            text = (
                f"📈 SICAK COIN GÜNCELLEME\n"
                f"Saat: {tr_str()}\n"
                f"Coin: {sym}\n"
                f"İlk fiyat: {fmt_num(first_price)}\n"
                f"Güncel fiyat: {fmt_num(cur)}\n"
                f"Hareket: %{rise_pct:.2f}\n"
                f"Not: Coin sıcak izleniyordu, yukarı devam etti. Short için henüz kör atlama yok; yeni teyit aranıyor."
            )
            ok = await safe_send_telegram(text)
            if ok:
                rec["last_rise_notice_ts"] = now_ts

async def check_followups() -> None:
    follows = memory.get("follows", {})
    if not follows:
        return
    tickers24 = await get_24h_tickers()
    now_ts = time.time()
    for sym, rec in list(follows.items()):
        if rec.get("done"):
            continue
        sent_ts = safe_float(rec.get("sent_ts", 0))
        if now_ts - sent_ts < FOLLOWUP_DELAY_SEC:
            continue
        t = tickers24.get(sym, {})
        cur = safe_float(t.get("last", 0))
        if cur <= 0:
            continue
        entry = safe_float(rec.get("entry", 0))
        stop = safe_float(rec.get("stop", 0))
        tp1 = safe_float(rec.get("tp1", 0))
        outcome = "NÖTR"
        pnl_pct = pct_change(entry, cur) * -1
        if cur >= stop:
            outcome = "STOP"
        elif cur <= tp1:
            outcome = "KÂRDA"
        text = (
            f"⏱ 2 SAAT SONRA TAKİP\n"
            f"Saat: {tr_str()}\n"
            f"Coin: {sym}\n"
            f"Entry: {fmt_num(entry)}\n"
            f"Güncel: {fmt_num(cur)}\n"
            f"Sonuç: {outcome}\n"
            f"Kısa yön tahmini değişim: %{pnl_pct:.2f}"
        )
        ok = await safe_send_telegram(text)
        if ok:
            stats["followup_sent"] += 1
            rec["done"] = True

def get_hot_symbols(limit: int = MAX_HOT_CANDIDATES) -> List[str]:
    hot = memory.get("hot", {})
    items = sorted(hot.items(), key=lambda x: safe_float(x[1].get("score", 0)), reverse=True)
    return [k for k, _ in items[:limit]]

def pick_general_symbols(batch_size: int = MAX_DEEP_ANALYSIS_PER_CYCLE) -> List[str]:
    global deep_pointer
    if not COINS:
        return []
    out = []
    n = len(COINS)
    for _ in range(min(batch_size, n)):
        out.append(COINS[deep_pointer % n])
        deep_pointer += 1
    return out

async def hot_scan_loop() -> None:
    if not ORIGINAL_V527_ENGINE_ENABLED:
        return
    while True:
        try:
            cleanup_memory()
            tickers24 = await get_24h_tickers()
            hot_syms = get_hot_symbols(MAX_HOT_CANDIDATES)
            if not hot_syms:
                await asyncio.sleep(HOT_SCAN_INTERVAL_SEC)
                continue
            for sym in hot_syms:
                res = await analyze_symbol(sym, tickers24)
                if not res:
                    continue
                stats["analyzed"] += 1
                if res["stage"] in ("SIGNAL", "READY", "HOT"):
                    logger.info("HOT LOOP %s stage=%s skor=%s", sym, res["stage"], res.get("score"))
                    await maybe_send_signal(res)
            await maybe_send_hot_rise_updates()
        except Exception as e:
            logger.exception("hot_scan_loop hata: %s", e)
        await asyncio.sleep(HOT_SCAN_INTERVAL_SEC)

async def deep_scan_loop() -> None:
    if not ORIGINAL_V527_ENGINE_ENABLED:
        return
    while True:
        try:
            cleanup_memory()
            tickers24 = await get_24h_tickers()
            batch = pick_general_symbols(MAX_DEEP_ANALYSIS_PER_CYCLE)
            for sym in batch:
                res = await analyze_symbol(sym, tickers24)
                if not res:
                    continue
                stats["analyzed"] += 1
                if res["stage"] == "SIGNAL":
                    logger.info("DEEP LOOP %s stage=%s skor=%s", sym, res["stage"], res.get("score"))
                    await maybe_send_signal(res)
                elif res["stage"] in ("HOT", "READY"):
                    logger.info("DEEP LOOP %s stage=%s skor=%s", sym, res["stage"], res.get("score"))
                    update_hot_memory(res)
                else:
                    stats["rejected"] += 1
        except Exception as e:
            logger.exception("deep_scan_loop hata: %s", e)
        await asyncio.sleep(DEEP_SCAN_INTERVAL_SEC)

async def ma_long_scan_loop() -> None:
    if not MA_ENGINE_ENABLED or not MA_LONG_ENGINE_ENABLED:
        return
    while True:
        try:
            if not COINS:
                await refresh_coin_pool(force=True)

            batch_size = 8
            coins = list(COINS)[:MA_COIN_LIMIT]
            for i in range(0, len(coins), batch_size):
                batch = coins[i:i+batch_size]
                tasks = [analyze_ma_long_symbol(sym) for sym in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.warning("MA LONG batch hata: %s", res)
                        continue
                    stats["ma_analyzed"] += 1
                    memory.setdefault("stats", {})["ma_analyzed"] = int(memory.get("stats", {}).get("ma_analyzed", 0)) + 1
                    if res:
                        await maybe_send_ma_signal(res)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.exception("ma_long_scan_loop hata: %s", e)
        await asyncio.sleep(max(5.0, MA_SCAN_INTERVAL_SEC))

async def ma_short_scan_loop() -> None:
    if not MA_ENGINE_ENABLED or not MA_SHORT_ENGINE_ENABLED:
        return
    while True:
        try:
            if not COINS:
                await refresh_coin_pool(force=True)

            batch_size = 8
            coins = list(COINS)[:MA_COIN_LIMIT]
            for i in range(0, len(coins), batch_size):
                batch = coins[i:i+batch_size]
                tasks = [analyze_ma_short_symbol(sym) for sym in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.warning("MA SHORT batch hata: %s", res)
                        continue
                    stats["ma_analyzed"] += 1
                    memory.setdefault("stats", {})["ma_analyzed"] = int(memory.get("stats", {}).get("ma_analyzed", 0)) + 1
                    if res:
                        await maybe_send_ma_signal(res)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.exception("ma_short_scan_loop hata: %s", e)
        await asyncio.sleep(max(5.0, MA_SCAN_INTERVAL_SEC))

async def ma_followup_loop() -> None:
    if not MA_FOLLOWUP_ENABLED:
        return
    while True:
        try:
            await check_ma_followups()
        except Exception as e:
            logger.exception("ma_followup_loop hata: %s", e)
        await asyncio.sleep(max(10, MA_FOLLOWUP_INTERVAL_SEC))

async def heartbeat_loop() -> None:
    if not AUTO_HEARTBEAT:
        return
    while True:
        try:
            await safe_send_telegram(build_heartbeat_message())
        except Exception as e:
            logger.exception("heartbeat_loop hata: %s", e)
        await asyncio.sleep(max(60, HEARTBEAT_INTERVAL_SEC))

async def diagnostic_loop() -> None:
    while True:
        try:
            last_sig = safe_float(memory.get("last_signal_ts", 0))
            last_diag = safe_float(memory.get("last_diag_ts", 0))
            now_ts = time.time()
            if (last_sig == 0 or now_ts - last_sig >= NO_SIGNAL_DIAG_SEC) and (now_ts - last_diag >= NO_SIGNAL_DIAG_SEC):
                ok = await safe_send_telegram(build_diagnostic_message())
                if ok:
                    memory["last_diag_ts"] = now_ts
        except Exception as e:
            logger.exception("diagnostic_loop hata: %s", e)
        await asyncio.sleep(600)

async def followup_loop() -> None:
    while True:
        try:
            await check_followups()
        except Exception as e:
            logger.exception("followup_loop hata: %s", e)
        await asyncio.sleep(max(60, FOLLOWUP_CHECK_INTERVAL_SEC))

async def save_loop() -> None:
    while True:
        try:
            await save_memory_async()
        except Exception as e:
            logger.exception("save_loop hata: %s", e)
        await asyncio.sleep(max(20, MEMORY_SAVE_INTERVAL_SEC))

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"{VERSION_NAME} aktif.\n"
        "Komutlar:\n"
        "/status - durum\n"
        "/test - test mesajı\n"
        "/scan - kısa özet tarama\n"
        "/coin BTCUSDT - tek coin analiz\n"
        "/hot - sıcak coinler\n"
        "/ma BTCUSDT - MA7/MA25 1H tek coin\n"
        "/ma_status - MA7/MA25 motor durumu\n"
        "/whale - 🐋 Whale Eye genel durum\n"
        "/whale BTC - 🐋 coin bazlı OI + Funding analizi\n"
        "/funding BTC - 💰 coin bazlı funding rate\n"
        "Not: Veri OKX SWAP, işlem teyidi Binance tarafında."
    )

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ok = await safe_send_telegram(f"✅ Test mesajı başarılı. Saat: {tr_str()}")
    await update.message.reply_text("Test mesajı gönderildi." if ok else "Test mesajı gönderilemedi.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_heartbeat_message())

async def cmd_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    hot = memory.get("hot", {})
    if not hot:
        await update.message.reply_text("Şu an sıcak coin yok.")
        return
    items = sorted(hot.items(), key=lambda x: safe_float(x[1].get("score", 0)), reverse=True)[:10]
    lines = ["🔥 Sıcak coinler:"]
    for sym, rec in items:
        lines.append(
            f"- {sym} | skor={safe_float(rec.get('score', 0)):.1f} | ilk={fmt_num(safe_float(rec.get('first_price', 0)))} | son={fmt_num(safe_float(rec.get('last_price', 0)))}"
        )
    await update.message.reply_text("\n".join(lines))

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tickers24 = await get_24h_tickers()
    syms = pick_general_symbols(8)
    out = ["🔎 Hızlı tarama:"]
    for sym in syms:
        res = await analyze_symbol(sym, tickers24)
        if not res:
            continue
        out.append(f"- {sym} | {res['stage']} | skor={res['score']} | fiyat={fmt_num(res['price'])}")
    await update.message.reply_text("\n".join(out[:25]))

async def cmd_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Kullanım: /coin BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    tickers24 = await get_24h_tickers()
    res = await analyze_symbol(symbol, tickers24)
    if not res:
        await update.message.reply_text(f"{symbol} analiz edilemedi.")
        return
    if res["stage"] == "SIGNAL":
        confirm = await confirm_signal_on_binance(res)
        res["data_engine"] = "OKX SWAP"
        res["binance_confirm_status"] = confirm.get("status", "YOK")
        res["binance_symbol"] = confirm.get("binance_symbol", normalize_binance_symbol(symbol))
        res["binance_price"] = confirm.get("binance_price", 0)
        res["binance_price_gap_pct"] = confirm.get("price_gap_pct", 0)
        res["binance_confirm_reason"] = confirm.get("reason", "-")
        await update.message.reply_text(build_signal_message(res))
    elif res["stage"] == "READY":
        await update.message.reply_text(build_ready_message(res))
    elif res["stage"] == "HOT":
        await update.message.reply_text(build_hot_message(res))
    else:
        await update.message.reply_text(
            f"{symbol} şu an short için zayıf.\n"
            f"Skor: {res.get('score', 0)}\n"
            f"Sebep: {res.get('reason', 'Yok')}"
        )

async def cmd_ma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Kullanım: /ma BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    res = await analyze_ma_symbol(symbol)
    if res:
        await update.message.reply_text(build_ma_signal_message(res))
    else:
        await update.message.reply_text(f"{symbol} için şu an 1 saatlik MA7/MA25 temas-kesişim yok.")

async def cmd_ma_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ma_perf = ma_performance_summary()
    stop_pct_dyn = calc_leveraged_stop_pct(MA_STOP_PCT)
    tp1_dyn = max(MA_TP1_PCT, stop_pct_dyn * 1.8)
    tp2_dyn = max(MA_TP2_PCT, stop_pct_dyn * 3.0)
    tp3_dyn = max(MA_TP3_PCT, stop_pct_dyn * 4.5)
    await update.message.reply_text(
        f"💓 MA7/MA25 1H 200 COIN DURUM\n"
        f"Saat: {tr_str()}\n"
        f"KALDIRAÇ: {LEVERAGE}x | Max Pozisyon Riski: %{MAX_POSITION_RISK_PCT:.1f}\n"
        f"Motor: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'}\n"
        f"LONG motor: {'AÇIK' if MA_LONG_ENGINE_ENABLED else 'KAPALI'} | SHORT motor: {'AÇIK' if MA_SHORT_ENGINE_ENABLED else 'KAPALI'}\n"
        f"TP/Stop takip: {'AÇIK' if MA_FOLLOWUP_ENABLED else 'KAPALI'}\n"
        f"Coin: {len(COINS)} / {MA_COIN_LIMIT}\n"
        f"Kural: MA7 altına MA25 = SHORT | MA7 üstüne MA25 = LONG\n"
        f"MA Entry: SHORT tepeye max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın | LONG dibe max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın\n"
        f"MA Stop/TP: stop %{stop_pct_dyn*100:.2f} | TP1 %{tp1_dyn*100:.2f} | TP2 %{tp2_dyn*100:.2f} | TP3 %{tp3_dyn*100:.2f}\n"
        f"Likidasyon koruması: min %{LIQUIDATION_BUFFER:.2f} mesafe\n"
        f"LONG sinyal: {ma_perf['long_sent']} | Başarı: %{ma_perf['long_success']:.1f} | TP={ma_perf['long_tp']} Stop={ma_perf['long_stop']}\n"
        f"SHORT sinyal: {ma_perf['short_sent']} | Başarı: %{ma_perf['short_success']:.1f} | TP={ma_perf['short_tp']} Stop={ma_perf['short_stop']}\n"
        f"MA analiz: {memory.get('stats', {}).get('ma_analyzed', 0)}"
    )


async def cmd_hafiza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    h = memory.get("ma_hafiza", {})

    total_sent = int(h.get("total_sent", 0))
    total_tp1 = int(h.get("total_tp1", 0))
    total_tp2 = int(h.get("total_tp2", 0))
    total_tp3 = int(h.get("total_tp3", 0))
    total_stop = int(h.get("total_stop", 0))
    total_stop_after_tp = int(h.get("total_stop_after_tp", 0))

    long_sent = int(h.get("long_sent", 0))
    long_tp1 = int(h.get("long_tp1", 0))
    long_tp2 = int(h.get("long_tp2", 0))
    long_tp3 = int(h.get("long_tp3", 0))
    long_stop = int(h.get("long_stop", 0))
    long_stop_after_tp = int(h.get("long_stop_after_tp", 0))

    short_sent = int(h.get("short_sent", 0))
    short_tp1 = int(h.get("short_tp1", 0))
    short_tp2 = int(h.get("short_tp2", 0))
    short_tp3 = int(h.get("short_tp3", 0))
    short_stop = int(h.get("short_stop", 0))
    short_stop_after_tp = int(h.get("short_stop_after_tp", 0))

    # Tamamlanmış işlemler: TP1 olmuş veya direkt stop yemiş
    completed = total_tp1 + total_stop
    win_rate = (total_tp1 / completed * 100.0) if completed > 0 else 0.0
    bekleyen = total_sent - completed

    msg = (
        f"📊 MA HAFIZA\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Toplam Sinyal: {total_sent}\n"
        f"Bekleyen (henüz sonuç yok): {bekleyen}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ TP1 olan: {total_tp1}\n"
        f"   ↳ TP2'ye ulaşan: {total_tp2}\n"
        f"   ↳ TP3'e ulaşan: {total_tp3}\n"
        f"   ↳ TP sonrası stop: {total_stop_after_tp}\n"
        f"❌ Direkt stop: {total_stop}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Win rate (TP1 yakalama): %{win_rate:.1f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🟢 LONG: {long_sent} sinyal\n"
        f"   TP1: {long_tp1} | TP2: {long_tp2} | TP3: {long_tp3}\n"
        f"   Stop: {long_stop} | TP sonrası stop: {long_stop_after_tp}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔴 SHORT: {short_sent} sinyal\n"
        f"   TP1: {short_tp1} | TP2: {short_tp2} | TP3: {short_tp3}\n"
        f"   Stop: {short_stop} | TP sonrası stop: {short_stop_after_tp}"
    )

    await update.message.reply_text(msg)


async def cmd_whale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not WHALE_EYE_ENABLED and not FUNDING_EYE_ENABLED:
        await update.message.reply_text("🐋 Whale Eye ve Funding Eye motorları kapalı")
        return
    if not context.args:
        await update.message.reply_text(
            f"🐋💰 INSTITUTIONAL EYE DURUM\n"
            f"Whale OI: {'AÇIK' if WHALE_EYE_ENABLED else 'KAPALI'}\n"
            f"Funding: {'AÇIK' if FUNDING_EYE_ENABLED else 'KAPALI'}\n"
            f"OI Lookback: {WHALE_OI_LOOKBACK_MIN} dk\n"
            f"İzlenen coin (OI history): {len(oi_history)}\n"
            f"--- OI ---\n"
            f"OI çağrı: {stats['whale_oi_calls']} | fail: {stats['whale_oi_fail']}\n"
            f"Bearish divergence (SHORT): {stats['whale_bearish_divergence']}\n"
            f"Bullish divergence (LONG):  {stats['whale_bullish_divergence']}\n"
            f"Warmup skip: {stats['whale_warmup_skip']}\n"
            f"--- FUNDING ---\n"
            f"Funding çağrı: {stats['funding_calls']} | fail: {stats['funding_fail']}\n"
            f"SHORT bonus hit: {stats['funding_short_bonus_hit']}\n"
            f"LONG bonus hit: {stats['funding_long_bonus_hit']}\n"
            f"--- KOMBO ---\n"
            f"Kurumsal kombo: {stats['institutional_combo_hit']}\n"
            f"---\n"
            f"Eşikler: OI ±{abs(WHALE_OI_BEARISH_DROP_PCT):.1f}%, Funding ±{FUNDING_BEARISH_THRESHOLD*100:.4f}%\n"
            f"Bonus: OI +{WHALE_SHORT_BONUS:.0f}, Funding +{FUNDING_SHORT_BONUS:.0f}\n"
            f"Kullanım: /whale BTC veya /whale BTC-USDT-SWAP"
        )
        return

    symbol = normalize_symbol(context.args[0])

    oi_task = fetch_okx_open_interest(symbol)
    funding_task = fetch_okx_funding_rate(symbol)
    oi_now, funding_rate = await asyncio.gather(oi_task, funding_task)

    if oi_now is None and funding_rate is None:
        await update.message.reply_text(
            f"🐋💰 {symbol}\nVeri çekilemedi (geçersiz coin veya API hatası).\n"
            f"OKX'te bu coin SWAP olarak listeleniyor mu kontrol edin."
        )
        return

    lines = [f"🐋💰 INSTITUTIONAL EYE — {symbol}", f"Saat: {tr_str()}"]

    if oi_now is not None and oi_now > 0:
        record_oi_snapshot(symbol, oi_now)
        hist = oi_history.get(symbol, [])
        warmup_min = (time.time() - hist[0][0]) / 60 if hist else 0
        lines.append("--- 🐋 OPEN INTEREST ---")
        lines.append(f"OI şimdi: {oi_now:,.2f}")
        lines.append(f"Snapshot: {len(hist)} (warmup: {warmup_min:.1f}dk)")
        try:
            k1 = await get_klines(symbol, "1m", WHALE_OI_LOOKBACK_MIN + 5)
            if len(k1) >= WHALE_OI_LOOKBACK_MIN + 1:
                c = closes(k1)
                price_change = pct_change(c[-(WHALE_OI_LOOKBACK_MIN + 1)], c[-1])
                payload = detect_whale_divergence(symbol, price_change)
                lines.append(f"Fiyat son {WHALE_OI_LOOKBACK_MIN}dk: %{price_change:+.2f}")
                lines.append(f"OI son {WHALE_OI_LOOKBACK_MIN}dk: %{payload.get('oi_change_pct', 0):+.2f}")
                lines.append(f"Durum: {payload.get('type', 'NONE')}")
                if payload.get('short_bonus', 0) > 0:
                    lines.append(f"→ SHORT bonus: +{payload['short_bonus']:.0f}")
                if payload.get('long_bonus', 0) > 0:
                    lines.append(f"→ LONG bonus: +{payload['long_bonus']:.0f}")
            else:
                lines.append("Fiyat verisi yetersiz")
        except Exception as e:
            lines.append(f"Fiyat verisi hata: {e}")
    else:
        lines.append("--- 🐋 OPEN INTEREST ---")
        lines.append("OI verisi alınamadı")

    lines.append("--- 💰 FUNDING RATE ---")
    if funding_rate is not None:
        f_signal = detect_funding_signal(funding_rate)
        lines.append(f"Funding: %{funding_rate*100:+.4f}/8h")
        lines.append(f"Yıllık ≈ %{f_signal.get('annual_pct', 0):+.1f}")
        lines.append(f"Durum: {f_signal.get('type', 'NONE')}")
        if f_signal.get('short_bonus', 0) > 0:
            lines.append(f"→ SHORT bonus: +{f_signal['short_bonus']:.0f}")
        if f_signal.get('long_bonus', 0) > 0:
            lines.append(f"→ LONG bonus: +{f_signal['long_bonus']:.0f}")
    else:
        lines.append("Funding verisi alınamadı")

    await update.message.reply_text("\n".join(lines))

async def cmd_funding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not FUNDING_EYE_ENABLED:
        await update.message.reply_text("💰 Funding Eye motoru kapalı (FUNDING_EYE_ENABLED=false)")
        return
    if not context.args:
        await update.message.reply_text(
            f"💰 FUNDING EYE\n"
            f"Çağrı: {stats['funding_calls']} | fail: {stats['funding_fail']}\n"
            f"SHORT bonus hit: {stats['funding_short_bonus_hit']}\n"
            f"LONG bonus hit: {stats['funding_long_bonus_hit']}\n"
            f"Eşikler: SHORT > +{FUNDING_BEARISH_THRESHOLD*100:.4f}% | LONG < {FUNDING_BULLISH_THRESHOLD*100:.4f}%\n"
            f"Bonus: SHORT +{FUNDING_SHORT_BONUS:.0f} | LONG +{FUNDING_LONG_BONUS:.0f}\n"
            f"Kullanım: /funding BTC"
        )
        return

    symbol = normalize_symbol(context.args[0])
    funding_rate = await fetch_okx_funding_rate(symbol)
    if funding_rate is None:
        await update.message.reply_text(f"💰 {symbol} için funding verisi alınamadı.")
        return

    f_signal = detect_funding_signal(funding_rate)
    await update.message.reply_text(
        f"💰 FUNDING — {symbol}\n"
        f"Saat: {tr_str()}\n"
        f"Funding: %{funding_rate*100:+.4f} / 8h\n"
        f"Yıllık ≈ %{f_signal.get('annual_pct', 0):+.1f}\n"
        f"Durum: {f_signal.get('type', 'NONE')}\n"
        f"SHORT bonus: +{f_signal.get('short_bonus', 0):.0f}\n"
        f"LONG bonus: +{f_signal.get('long_bonus', 0):.0f}\n"
        f"Not: {f_signal.get('note', '-') or '-'}"
    )

async def post_init(application) -> None:
    active_count, pruned_count = await refresh_coin_pool(force=True)

    if AUTO_START_MESSAGE:
        await safe_send_telegram(
            f"🚀 {VERSION_NAME} başladı\n"
            f"Saat: {tr_str()}\n"
            f"Coin sayısı: {active_count}\n"
            f"Çıkarılan coin: {pruned_count}\n"
            f"Veri kaynağı: OKX {OKX_INST_TYPE}\n"
            f"Motorlar: sıcak takip + derin analiz + teşhis + heartbeat + symbol refresh + MA7/MA25 1H + 🐋💰 Institutional Eye\n"
            f"MA7/MA25: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'} | hedef coin={MA_COIN_LIMIT}\n"
            f"MA LONG motor: {'AÇIK' if MA_LONG_ENGINE_ENABLED else 'KAPALI'} | MA SHORT motor: {'AÇIK' if MA_SHORT_ENGINE_ENABLED else 'KAPALI'}\n"
            f"MA TP/Stop takip: {'AÇIK' if MA_FOLLOWUP_ENABLED else 'KAPALI'}\n"
            f"MA Entry: SHORT tepeye max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın | LONG dibe max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın\n"
            f"🐋 Whale Eye: {'AÇIK' if WHALE_EYE_ENABLED else 'KAPALI'} | OI Lookback: {WHALE_OI_LOOKBACK_MIN}dk\n"
            f"🐋 OI eşikleri: SHORT için OI ≤ {WHALE_OI_BEARISH_DROP_PCT:.1f}%, LONG için OI ≥ +{WHALE_OI_BULLISH_RISE_PCT:.1f}%\n"
            f"🐋 OI bonus: SHORT +{WHALE_SHORT_BONUS:.0f}, LONG +{WHALE_LONG_BONUS:.0f}\n"
            f"💰 Funding Eye: {'AÇIK' if FUNDING_EYE_ENABLED else 'KAPALI'}\n"
            f"💰 Funding eşik: SHORT > +{FUNDING_BEARISH_THRESHOLD*100:.4f}%, LONG < {FUNDING_BULLISH_THRESHOLD*100:.4f}%\n"
            f"💰 Funding bonus: SHORT +{FUNDING_SHORT_BONUS:.0f}, LONG +{FUNDING_LONG_BONUS:.0f}\n"
            f"Kaldıraç: {LEVERAGE}x | Max Risk/Pozisyon: %{MAX_POSITION_RISK_PCT:.1f} | Likidasyon tamponu: %{LIQUIDATION_BUFFER:.1f}\n"
            f"V8.1 ULTIMATE: OI + Funding kurumsal motor, LONG mirror, retry'lı OKX API\n"
            f"Günlük short kilidi: aynı coin gün boyu 1 kez\n"
            f"Veri koruması: geçersiz coin temizliği + fail coin geçici blok"
        )

    asyncio.create_task(hot_scan_loop())
    asyncio.create_task(deep_scan_loop())
    asyncio.create_task(symbol_refresh_loop())
    asyncio.create_task(ma_long_scan_loop())
    asyncio.create_task(ma_short_scan_loop())
    asyncio.create_task(ma_followup_loop())
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(diagnostic_loop())
    asyncio.create_task(followup_loop())
    asyncio.create_task(save_loop())
    logger.info("Arka plan döngüleri başlatıldı")

def validate_config() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError(f"Eksik env: {', '.join(missing)}")

def build_app():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("test", cmd_test))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("scan", cmd_scan))
    application.add_handler(CommandHandler("coin", cmd_coin))
    application.add_handler(CommandHandler("hot", cmd_hot))
    application.add_handler(CommandHandler("ma", cmd_ma))
    application.add_handler(CommandHandler("ma_status", cmd_ma_status))
    application.add_handler(CommandHandler("hafiza", cmd_hafiza))
    application.add_handler(CommandHandler("whale", cmd_whale))
    application.add_handler(CommandHandler("funding", cmd_funding))
    return application

def main() -> None:
    validate_config()
    load_memory()
    global app
    app = build_app()
    logger.info("%s polling başlıyor", VERSION_NAME)
    try:
        app.run_polling(close_loop=False, drop_pending_updates=True)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Kapanma sinyali alındı")
    finally:
        try:
            save_memory()
            logger.info("Memory kapanışta kaydedildi")
        except Exception as e:
            logger.exception("Kapanış memory save hatası: %s", e)
        try:
            SESSION.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
