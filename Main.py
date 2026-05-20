
import os
import json
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================================================
# BALINA AVCISI V5.2.7 HIBRIT ONAYLI - TEK PARCA SURUM
# Amac:
# - Bilindik / buyuk coinleri cikarmak
# - Ayni coin icin surekli SHORT AL tekrarini kapatmak
# - Veri tarafini koruyup API fail patlamasini azaltmak
# - Ana analiz mantigina minimum dokunmak
# =========================================================

VERSION_NAME = "Balina Avcısı V5.2.7 HİBRİT ONAYLI + MA7/MA25 3M SİNYAL + 15M/1H YÖN 200 COIN"
CODE_ID = "MA3M_15M_1H_YON_FIX_V2"

# -------------------------
# ENV / AYARLAR
# -------------------------
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

# Eski V5.2.7 mantigi korunuyor
MIN_CANDIDATE_SCORE = float(os.getenv("MIN_CANDIDATE_SCORE", "34"))
MIN_READY_SCORE = float(os.getenv("MIN_READY_SCORE", "50"))
MIN_SIGNAL_SCORE = float(os.getenv("MIN_SIGNAL_SCORE", "68"))

SCORE_OVERRIDE_GAP = float(os.getenv("SCORE_OVERRIDE_GAP", "8"))
PRICE_OVERRIDE_MOVE_PCT = float(os.getenv("PRICE_OVERRIDE_MOVE_PCT", "0.55"))

NO_SIGNAL_DIAG_SEC = int(float(os.getenv("NO_SIGNAL_DIAG_SEC", str(4 * 3600))))

KLINE_CACHE_SEC = int(float(os.getenv("KLINE_CACHE_SEC", "12")))
TICKER_CACHE_SEC = int(float(os.getenv("TICKER_CACHE_SEC", "8")))
HTTP_TIMEOUT = int(float(os.getenv("HTTP_TIMEOUT", "12")))

# Veri koruma katmani
OKX_INSTRUMENT_CACHE_SEC = int(float(os.getenv("OKX_INSTRUMENT_CACHE_SEC", "1800")))
AUTO_SYMBOL_REFRESH_SEC = int(float(os.getenv("AUTO_SYMBOL_REFRESH_SEC", "1800")))
SYMBOL_FAIL_BLOCK_SEC = int(float(os.getenv("SYMBOL_FAIL_BLOCK_SEC", "900")))
SYMBOL_FAIL_FORGET_SEC = int(float(os.getenv("SYMBOL_FAIL_FORGET_SEC", "43200")))
SYMBOL_FAIL_MAX_STREAK = int(float(os.getenv("SYMBOL_FAIL_MAX_STREAK", "2")))

MIN_24H_QUOTE_VOLUME = float(os.getenv("MIN_24H_QUOTE_VOLUME", "1200000"))

# MA7/MA25 1H 200 COIN MOTORU
# Bu bölüm ikinci dosyadaki MA7/MA25 1 saatlik LONG/SHORT motorunu korur.
MA_ENGINE_ENABLED = os.getenv("MA_ENGINE_ENABLED", "true").lower() == "true"
MA_COIN_LIMIT = int(float(os.getenv("MA_COIN_LIMIT", "200")))
MA_SCAN_INTERVAL_SEC = float(os.getenv("MA_SCAN_INTERVAL_SEC", "60"))
MA_KLINE_INTERVAL = os.getenv("MA_KLINE_INTERVAL", "1H").strip()
MA_SIGNAL_INTERVAL = os.getenv("MA_SIGNAL_INTERVAL", "3m").strip()
MA_CONFIRM_INTERVAL = os.getenv("MA_CONFIRM_INTERVAL", "15m").strip()
MA_TREND_INTERVAL = os.getenv("MA_TREND_INTERVAL", "1H").strip()
MA_STOP_PCT = float(os.getenv("MA_STOP_PCT", "0.008"))
MA_TP1_PCT = float(os.getenv("MA_TP1_PCT", "0.015"))
MA_TP2_PCT = float(os.getenv("MA_TP2_PCT", "0.020"))
MA_TP3_PCT = float(os.getenv("MA_TP3_PCT", "0.025"))
MA_ENTRY_MAX_DIFF_PCT = float(os.getenv("MA_ENTRY_MAX_DIFF_PCT", "0.30"))
SHORT_MAX_RESISTANCE_DIFF_PCT = float(os.getenv("SHORT_MAX_RESISTANCE_DIFF_PCT", "0.30"))
SHORT_MIN_SUPPORT_DIFF_PCT = float(os.getenv("SHORT_MIN_SUPPORT_DIFF_PCT", "1.00"))
LONG_MAX_SUPPORT_DIFF_PCT = float(os.getenv("LONG_MAX_SUPPORT_DIFF_PCT", "0.30"))
LONG_MIN_RESISTANCE_DIFF_PCT = float(os.getenv("LONG_MIN_RESISTANCE_DIFF_PCT", "1.00"))
MA_LONG_ENGINE_ENABLED = os.getenv("MA_LONG_ENGINE_ENABLED", "true").lower() == "true"
MA_SHORT_ENGINE_ENABLED = os.getenv("MA_SHORT_ENGINE_ENABLED", "true").lower() == "true"
MA_SUPPORT_RESISTANCE_LOOKBACK = int(float(os.getenv("MA_SUPPORT_RESISTANCE_LOOKBACK", "50")))
MA_FOLLOWUP_ENABLED = os.getenv("MA_FOLLOWUP_ENABLED", "true").lower() == "true"
MA_FOLLOWUP_INTERVAL_SEC = int(float(os.getenv("MA_FOLLOWUP_INTERVAL_SEC", "60")))
DYNAMIC_TOP_200_COIN_POOL = os.getenv("DYNAMIC_TOP_200_COIN_POOL", "true").lower() == "true"
ORIGINAL_V527_ENGINE_ENABLED = os.getenv("ORIGINAL_V527_ENGINE_ENABLED", "true").lower() == "true"
RAW_COINS_ENV = os.getenv("COINS", "").strip()

# Buyuk / bilindik coinler silinmis liste
DEFAULT_COINS = [
    "WIF-USDT-SWAP", "PEPE-USDT-SWAP", "1000PEPE-USDT-SWAP", "FET-USDT-SWAP", "INJ-USDT-SWAP",
    "RUNE-USDT-SWAP", "SEI-USDT-SWAP", "TIA-USDT-SWAP", "JUP-USDT-SWAP", "PYTH-USDT-SWAP",
    "ENA-USDT-SWAP", "PENDLE-USDT-SWAP", "TAO-USDT-SWAP", "WLD-USDT-SWAP", "RENDER-USDT-SWAP",
    "RAY-USDT-SWAP", "STX-USDT-SWAP", "RNDR-USDT-SWAP", "MANTA-USDT-SWAP", "GALA-USDT-SWAP",
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

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("balina_avcisi_v527_hibrit_onayli")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

# -------------------------
# GLOBAL STATE
# -------------------------
TZ = ZoneInfo(TIMEZONE_NAME)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BalinaAvcisiV527HibritOnayli/1.0"})

kline_cache: Dict[str, Tuple[float, List[List[Any]]]] = {}
ticker_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
instrument_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
okx_live_symbols: Dict[str, Dict[str, Any]] = {}
symbol_fail_state: Dict[str, Dict[str, Any]] = {}

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
}

app = None
deep_pointer = 0


# =========================================================
# GENEL YARDIMCILAR
# =========================================================
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
    memory.setdefault("daily_short_sent", {})
    memory.setdefault("last_signal_ts", 0.0)
    memory.setdefault("last_diag_ts", 0.0)
    memory["stats"].setdefault("ma_long", 0)
    memory["stats"].setdefault("ma_short", 0)
    memory["stats"].setdefault("ma_analyzed", 0)
    memory["stats"].setdefault("ma_tp", 0)
    memory["stats"].setdefault("ma_stop", 0)
    memory["stats"].setdefault("ma_followup", 0)


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
    try:
        ensure_memory_shape()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Memory kaydedilemedi: %s", e)


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


# =========================================================
# TELEGRAM GÖNDERİMİ
# =========================================================
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


# =========================================================
# OKX DATA
# =========================================================
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


def _okx_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{OKX_BASE_URL}{path}"
    resp = SESSION.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if str(data.get("code", "1")) != "0":
        raise RuntimeError(f"OKX hata: code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", [])


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
    k1 = await get_binance_klines(symbol, "1m", 80)
    k5 = await get_binance_klines(symbol, "5m", 80)
    if len(k1) < 30 or len(k5) < 30:
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


# =========================================================
# TEKNİK HESAPLAR
# =========================================================
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


# =========================================================
# ANALİZ
# =========================================================
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
    last_atr1 = max(atr1[-1], last_price * 0.0014)
    last_atr5 = max(atr5[-1], last_price * 0.0019)

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
    stop = entry + (last_atr1 * 1.45)
    tp1 = entry - (last_atr1 * 1.15)
    tp2 = entry - (last_atr1 * 2.20)
    tp3 = entry - (last_atr5 * 1.80)
    rr = (entry - tp1) / max(stop - entry, 1e-9)

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
        "reason": " | ".join(reasons[:10]) if reasons else "Sebep yok",
    }



# =========================================================
# MA7 / MA25 3M SİNYAL + 15M/1H YÖN 200 COIN MOTORU
# =========================================================
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
    if direction == "SHORT":
        return {
            "stop": entry * (1 + MA_STOP_PCT),
            "tp1": entry * (1 - MA_TP1_PCT),
            "tp2": entry * (1 - MA_TP2_PCT),
            "tp3": entry * (1 - MA_TP3_PCT),
        }
    return {
        "stop": entry * (1 - MA_STOP_PCT),
        "tp1": entry * (1 + MA_TP1_PCT),
        "tp2": entry * (1 + MA_TP2_PCT),
        "tp3": entry * (1 + MA_TP3_PCT),
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


def _direction_ok_for_timeframe(direction: str, klines: List[List[Any]], ma7_values: List[float]) -> bool:
    # Yön filtresi: burada MA7'nin MA25 üstünde/altında olması şart değildir.
    # LONG için o zaman diliminde fiyat ve MA7 yukarı eğimli olmalı.
    # SHORT için o zaman diliminde fiyat ve MA7 aşağı eğimli olmalı.
    if len(klines) < 3 or len(ma7_values) < 3:
        return False
    prev_close = safe_float(klines[-2][4])
    cur_close = safe_float(klines[-1][4])
    prev_ma7 = safe_float(ma7_values[-2])
    cur_ma7 = safe_float(ma7_values[-1])
    if prev_close <= 0 or cur_close <= 0 or prev_ma7 <= 0 or cur_ma7 <= 0:
        return False
    if direction == "LONG":
        return cur_close > prev_close and cur_ma7 >= prev_ma7
    if direction == "SHORT":
        return cur_close < prev_close and cur_ma7 <= prev_ma7
    return False


def _build_ma_result(
    symbol: str,
    direction: str,
    signal_klines: List[List[Any]],
    signal_ma7: List[float],
    signal_ma25: List[float],
    confirm_klines: List[List[Any]],
    confirm_ma7: List[float],
    trend_klines: List[List[Any]],
    trend_ma7: List[float],
) -> Optional[Dict[str, Any]]:
    prev_ma7 = signal_ma7[-2]
    prev_ma25 = signal_ma25[-2]
    cur_ma7 = signal_ma7[-1]
    cur_ma25 = signal_ma25[-1]

    confirm_cur_ma7 = confirm_ma7[-1]
    trend_cur_ma7 = trend_ma7[-1]
    confirm_cur_close = safe_float(confirm_klines[-1][4])
    trend_cur_close = safe_float(trend_klines[-1][4])

    last_candle = signal_klines[-1]
    candle_ts = str(last_candle[0])
    candle_open = safe_float(last_candle[1])
    candle_high = safe_float(last_candle[2])
    candle_low = safe_float(last_candle[3])
    last_price = safe_float(last_candle[4])

    entry = 0.0
    entry_note = ""
    entry_diff_pct = 0.0

    if direction == "SHORT":
        # 3 dakikalık MA7, MA25 altında olacak.
        # 15 dakikalık ve 1 saatlik yön aşağı olacak. MA7'nin MA25 altında olması şart değildir.
        if not (cur_ma7 <= cur_ma25):
            return None
        if not _direction_ok_for_timeframe("SHORT", confirm_klines, confirm_ma7):
            return None
        if not _direction_ok_for_timeframe("SHORT", trend_klines, trend_ma7):
            return None
        if candle_high <= 0 or last_price <= 0:
            return None
        entry_diff_pct = abs(((candle_high - last_price) / candle_high) * 100.0)
        if entry_diff_pct > MA_ENTRY_MAX_DIFF_PCT:
            return None
        entry = last_price
        entry_note = f"SHORT giriş: 3m MA7, MA25 altında + güncel fiyat 3 dakikalık mum tepesine en fazla %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın"

    elif direction == "LONG":
        # 3 dakikalık MA7, MA25 üstünde olacak.
        # 15 dakikalık ve 1 saatlik yön yukarı olacak. MA7'nin MA25 üstünde olması şart değildir.
        if not (cur_ma7 >= cur_ma25):
            return None
        if not _direction_ok_for_timeframe("LONG", confirm_klines, confirm_ma7):
            return None
        if not _direction_ok_for_timeframe("LONG", trend_klines, trend_ma7):
            return None
        if candle_low <= 0 or last_price <= 0:
            return None
        entry_diff_pct = abs(((last_price - candle_low) / candle_low) * 100.0)
        if entry_diff_pct > MA_ENTRY_MAX_DIFF_PCT:
            return None
        entry = last_price
        entry_note = f"LONG giriş: 3m MA7, MA25 üstünde + güncel fiyat 3 dakikalık mum dibine en fazla %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın"
    else:
        return None

    if entry <= 0:
        return None

    targets = calc_ma_targets(entry, direction)
    sr = calc_support_resistance(signal_klines, entry)

    if direction == "SHORT":
        if safe_float(sr.get("resistance_diff_pct", 0)) > SHORT_MAX_RESISTANCE_DIFF_PCT:
            return None
        if safe_float(sr.get("support_diff_pct", 0)) < SHORT_MIN_SUPPORT_DIFF_PCT:
            return None

    if direction == "LONG":
        if safe_float(sr.get("support_diff_pct", 0)) > LONG_MAX_SUPPORT_DIFF_PCT:
            return None
        if safe_float(sr.get("resistance_diff_pct", 0)) < LONG_MIN_RESISTANCE_DIFF_PCT:
            return None

    trend_text = "15m + 1H YÖN AŞAĞI" if direction == "SHORT" else "15m + 1H YÖN YUKARI"

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
        "ma7": cur_ma7,
        "ma25": cur_ma25,
        "prev_ma7": prev_ma7,
        "prev_ma25": prev_ma25,
        "confirm_ma7": confirm_cur_ma7,
        "confirm_close": confirm_cur_close,
        "trend_ma7": trend_cur_ma7,
        "trend_close": trend_cur_close,
        "trend_text": trend_text,
        "candle_ts": candle_ts,
        "timeframe": MA_SIGNAL_INTERVAL,
        "confirm_timeframe": MA_CONFIRM_INTERVAL,
        "trend_timeframe": MA_TREND_INTERVAL,
        "entry_note": entry_note,
    }


async def _prepare_ma_data(symbol: str) -> Optional[Tuple[str, List[List[Any]], List[float], List[float], List[List[Any]], List[float], List[List[Any]], List[float]]]:
    symbol = normalize_symbol(symbol)
    signal_klines = await get_klines(symbol, MA_SIGNAL_INTERVAL, 80)
    confirm_klines = await get_klines(symbol, MA_CONFIRM_INTERVAL, 80)
    trend_klines = await get_klines(symbol, MA_TREND_INTERVAL, 80)
    if len(signal_klines) < 30 or len(confirm_klines) < 30 or len(trend_klines) < 30:
        return None

    signal_c = closes(signal_klines)
    confirm_c = closes(confirm_klines)
    trend_c = closes(trend_klines)

    signal_ma7 = sma(signal_c, 7)
    signal_ma25 = sma(signal_c, 25)
    confirm_ma7 = sma(confirm_c, 7)
    trend_ma7 = sma(trend_c, 7)

    if signal_ma7[-1] <= 0 or signal_ma25[-1] <= 0:
        return None
    if confirm_ma7[-1] <= 0 or trend_ma7[-1] <= 0:
        return None
    return symbol, signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7


async def analyze_ma_long_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7 = prepared
    return _build_ma_result(sym, "LONG", signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7)


async def analyze_ma_short_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7 = prepared
    return _build_ma_result(sym, "SHORT", signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7)


async def analyze_ma_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    prepared = await _prepare_ma_data(symbol)
    if not prepared:
        return None
    sym, signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7 = prepared
    long_res = _build_ma_result(sym, "LONG", signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7)
    if long_res:
        return long_res
    return _build_ma_result(sym, "SHORT", signal_klines, signal_ma7, signal_ma25, confirm_klines, confirm_ma7, trend_klines, trend_ma7)


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
        "timeframe": res.get("timeframe", MA_SIGNAL_INTERVAL),
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
    return (
        f"🚨 {VERSION_NAME} - MA7/MA25 {res['timeframe']} + {res.get('trend_timeframe', MA_TREND_INTERVAL)} YÖN - {res['direction']} AL\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"Motor: {res['direction']} MOTORU\n"
        f"Sinyal veri: {res['timeframe']} | Yön filtre: {res.get('trend_timeframe', MA_TREND_INTERVAL)}\n"
        f"Kural: 3m MA7/MA25 durumu + 15m/1H yön filtresi\n"
        f"{res['entry_note']}\n"
        f"3m MA7: {fmt_num(res['ma7'])}\n"
        f"3m MA25: {fmt_num(res['ma25'])}\n"
        f"15m yön MA7: {fmt_num(safe_float(res.get('confirm_ma7', 0)))} | 15m fiyat: {fmt_num(safe_float(res.get('confirm_close', 0)))}\n"
        f"1H yön MA7: {fmt_num(safe_float(res.get('trend_ma7', 0)))} | 1H fiyat: {fmt_num(safe_float(res.get('trend_close', 0)))}\n"
        f"Yön filtresi: {res.get('trend_text', '-')}\n"
        f"1H MA7: {fmt_num(safe_float(res.get('trend_ma7', 0)))}\n"
        f"1H MA25: {fmt_num(safe_float(res.get('trend_ma25', 0)))}\n"
        f"Yön filtresi: {res.get('trend_text', '-')}\n"
        f"Mum tepe: {fmt_num(res['candle_high'])}\n"
        f"Mum dip: {fmt_num(res['candle_low'])}\n"
        f"Güncel: {fmt_num(res['last_price'])}\n"
        f"Dip/tepe farkı: %{safe_float(res.get('entry_diff_pct', 0)):.2f} / max %{safe_float(res.get('max_entry_diff_pct', MA_ENTRY_MAX_DIFF_PCT)):.2f}\n"
        f"Destek: {fmt_num(safe_float(res.get('support', 0)))} | fark %{safe_float(res.get('support_diff_pct', 0)):.2f}\n"
        f"Direnç: {fmt_num(safe_float(res.get('resistance', 0)))} | fark %{safe_float(res.get('resistance_diff_pct', 0)):.2f}\n"
        f"SHORT S/R: direnç max %{SHORT_MAX_RESISTANCE_DIFF_PCT:.2f} | destek min %{SHORT_MIN_SUPPORT_DIFF_PCT:.2f}\n"
        f"LONG S/R: destek max %{LONG_MAX_SUPPORT_DIFF_PCT:.2f} | direnç min %{LONG_MIN_RESISTANCE_DIFF_PCT:.2f}\n"
        f"Entry: {fmt_num(res['entry'])}\n"
        f"Stop: {fmt_num(res['stop'])} (%0.80)\n"
        f"TP1: {fmt_num(res['tp1'])} (%1.5)\n"
        f"TP2: {fmt_num(res['tp2'])} (%2)\n"
        f"TP3: {fmt_num(res['tp3'])} (%2.5)"
    )


async def maybe_send_ma_signal(res: Dict[str, Any]) -> None:
    if ma_already_sent(res):
        return
    ok = await safe_send_telegram(build_ma_signal_message(res))
    if ok:
        mark_ma_sent(res)
        save_memory()
        logger.info("MA7/MA25 sinyal gönderildi: %s %s", res["symbol"], res["direction"])


def detect_ma_followup_result(rec: Dict[str, Any], klines_1m: List[List[Any]]) -> Optional[Dict[str, Any]]:
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
        hit = detect_ma_followup_result(rec, k1m)
        if not hit:
            continue
        ok = await safe_send_telegram(build_ma_followup_message(rec, hit))
        if ok:
            rec["done"] = True
            rec["result"] = hit.get("result")
            rec["result_price"] = hit.get("price")
            rec["touch_ts"] = hit.get("touch_ts")
            memory.setdefault("stats", {})["ma_followup"] = int(memory.get("stats", {}).get("ma_followup", 0)) + 1
            if str(hit.get("result")) == "STOP":
                memory["stats"]["ma_stop"] = int(memory["stats"].get("ma_stop", 0)) + 1
            elif str(hit.get("result")).startswith("TP"):
                memory["stats"]["ma_tp"] = int(memory["stats"].get("ma_tp", 0)) + 1
            save_memory()

# =========================================================
# MEMORY / COOLDOWN
# =========================================================
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


# =========================================================
# MESAJ FORMATLARI
# =========================================================
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
    return (
        f"🚨 {VERSION_NAME} SHORT AL\n"
        f"Saat: {tr_str()}\n"
        f"Coin: {res['symbol']}\n"
        f"Veri motoru: {data_engine}\n"
        f"Binance teyit: {confirm_status}\n"
        f"Binance sembol: {binance_symbol}\n"
        f"Skor: {res['score']}\n"
        f"Aday/Hazır/Doğrula: {res['candidate_score']} / {res['ready_score']} / {res['verify_score']}\n"
        f"OKX fiyat: {fmt_num(res['price'])}\n"
        f"Binance fiyat: {fmt_num(binance_price) if binance_price > 0 else '-'}\n"
        f"OKX-Binance farkı: %{binance_gap:.2f}\n"
        f"Entry: {fmt_num(res['price'])}\n"
        f"Stop: {fmt_num(res['stop'])}\n"
        f"TP1: {fmt_num(res['tp1'])}\n"
        f"TP2: {fmt_num(res['tp2'])}\n"
        f"TP3: {fmt_num(res['tp3'])}\n"
        f"RR(TP1): {res['rr']}\n"
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
    return (
        f"💓 {VERSION_NAME} DURUM\n"
        f"Saat: {tr_str()}\n"
        f"Kod ID: {CODE_ID}\n"
        f"MA veri: sinyal={MA_SIGNAL_INTERVAL} | yön={MA_CONFIRM_INTERVAL}+{MA_TREND_INTERVAL}\n"
        f"Toplam coin: {len(COINS)} / hedef {MA_COIN_LIMIT}\n"
        f"MA motoru: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'}\n"
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


# =========================================================
# SİNYAL İŞLEME
# =========================================================
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


# =========================================================
# TARAMA DÖNGÜLERİ
# =========================================================
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
            for sym in list(COINS)[:MA_COIN_LIMIT]:
                res = await analyze_ma_long_symbol(sym)
                stats["ma_analyzed"] += 1
                memory.setdefault("stats", {})["ma_analyzed"] = int(memory.get("stats", {}).get("ma_analyzed", 0)) + 1
                if not res:
                    continue
                await maybe_send_ma_signal(res)
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
            for sym in list(COINS)[:MA_COIN_LIMIT]:
                res = await analyze_ma_short_symbol(sym)
                stats["ma_analyzed"] += 1
                memory.setdefault("stats", {})["ma_analyzed"] = int(memory.get("stats", {}).get("ma_analyzed", 0)) + 1
                if not res:
                    continue
                await maybe_send_ma_signal(res)
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


async def ma_scan_loop() -> None:
    return


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
            save_memory()
        except Exception as e:
            logger.exception("save_loop hata: %s", e)
        await asyncio.sleep(max(20, MEMORY_SAVE_INTERVAL_SEC))


# =========================================================
# TELEGRAM KOMUTLARI
# =========================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"{VERSION_NAME} aktif.\n"
        f"Kod ID: {CODE_ID}\n"
        f"MA veri: sinyal={MA_SIGNAL_INTERVAL} | yön={MA_CONFIRM_INTERVAL}+{MA_TREND_INTERVAL}\n"
        "Komutlar:\n"
        "/status - durum\n"
        "/test - test mesajı\n"
        "/scan - kısa özet tarama\n"
        "/coin BTCUSDT - tek coin analiz\n"
        "/hot - sıcak coinler\n"
        "/ma BTCUSDT - MA7/MA25 15m tek coin\n"
        "/ma_status - MA7/MA25 3m sinyal + 15m/1H yön motor durumu\n"
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
        await update.message.reply_text(f"{symbol} için şu an 3m MA7/MA25 durumu + 15m/1H yön şartı yok.")


async def cmd_ma_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ma_perf = ma_performance_summary()
    await update.message.reply_text(
        f"💓 MA7/MA25 3M SİNYAL + 15M/1H YÖN 200 COIN DURUM\n"
        f"Saat: {tr_str()}\n"
        f"Kod ID: {CODE_ID}\n"
        f"Motor: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'}\n"
        f"LONG motor: {'AÇIK' if MA_LONG_ENGINE_ENABLED else 'KAPALI'} | SHORT motor: {'AÇIK' if MA_SHORT_ENGINE_ENABLED else 'KAPALI'}\n"
        f"TP/Stop takip: {'AÇIK' if MA_FOLLOWUP_ENABLED else 'KAPALI'}\n"
        f"Coin: {len(COINS)} / {MA_COIN_LIMIT}\n"
        f"Kural: 3m MA7<MA25 = SHORT | 3m MA7>MA25 = LONG\n"
        f"Yön: 15m ve 1H yukarıysa LONG | 15m ve 1H aşağıysa SHORT\n"
        f"Not: 15m/1H yön filtresinde MA7'nin MA25 üstünde/altında olması şart değil\n"
        f"Veri: sinyal={MA_SIGNAL_INTERVAL} | yön={MA_CONFIRM_INTERVAL}+{MA_TREND_INTERVAL}\n"
        f"Entry: SHORT 3m tepeye max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın | LONG 3m dibe max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın\n"
        f"SHORT S/R: direnç max %{SHORT_MAX_RESISTANCE_DIFF_PCT:.2f} | destek min %{SHORT_MIN_SUPPORT_DIFF_PCT:.2f}\n"
        f"LONG S/R: destek max %{LONG_MAX_SUPPORT_DIFF_PCT:.2f} | direnç min %{LONG_MIN_RESISTANCE_DIFF_PCT:.2f}\n"
        f"Stop: %0.80\n"
        f"TP1/TP2/TP3: %1.5 / %2 / %2.5\n"
        f"LONG sinyal: {ma_perf['long_sent']} | Başarı: %{ma_perf['long_success']:.1f} | TP={ma_perf['long_tp']} Stop={ma_perf['long_stop']}\n"
        f"SHORT sinyal: {ma_perf['short_sent']} | Başarı: %{ma_perf['short_success']:.1f} | TP={ma_perf['short_tp']} Stop={ma_perf['short_stop']}\n"
        f"MA analiz: {memory.get('stats', {}).get('ma_analyzed', 0)}"
    )


# =========================================================
# BAŞLATMA
# =========================================================
async def post_init(application) -> None:
    active_count, pruned_count = await refresh_coin_pool(force=True)

    if AUTO_START_MESSAGE:
        await safe_send_telegram(
            f"🚀 {VERSION_NAME} başladı\n"
            f"Saat: {tr_str()}\n"
            f"Coin sayısı: {active_count}\n"
            f"Çıkarılan coin: {pruned_count}\n"
            f"Veri kaynağı: OKX {OKX_INST_TYPE}\n"
            f"Motorlar: sıcak takip + derin analiz + teşhis + heartbeat + symbol refresh + MA7/MA25 3M + 15M/1H yön\n"
            f"MA7/MA25: {'AÇIK' if MA_ENGINE_ENABLED else 'KAPALI'} | hedef coin={MA_COIN_LIMIT}\n"
            f"MA LONG motor: {'AÇIK' if MA_LONG_ENGINE_ENABLED else 'KAPALI'} | MA SHORT motor: {'AÇIK' if MA_SHORT_ENGINE_ENABLED else 'KAPALI'}\n"
            f"MA TP/Stop takip: {'AÇIK' if MA_FOLLOWUP_ENABLED else 'KAPALI'}\n"
            f"MA veri: sinyal={MA_SIGNAL_INTERVAL} | yön={MA_CONFIRM_INTERVAL}+{MA_TREND_INTERVAL}\n"
            f"MA Entry: SHORT 3m tepeye max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın | LONG 3m dibe max %{MA_ENTRY_MAX_DIFF_PCT:.2f} yakın\n"
            f"MA Stop/TP: stop %0.80 | TP1 %1.5 | TP2 %2 | TP3 %2.5\n"
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



async def cmd_versiyon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"✅ AKTİF KOD\n"
        f"Version: {VERSION_NAME}\n"
        f"Kod ID: {CODE_ID}\n"
        f"Dosya: main.py\n"
        f"Sinyal veri: {MA_SIGNAL_INTERVAL}\n"
        f"Yön filtre: {MA_CONFIRM_INTERVAL}+{MA_TREND_INTERVAL}\n"
        f"Saat: {tr_str()}"
    )

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
    application.add_handler(CommandHandler("versiyon", cmd_versiyon))
    return application


def main() -> None:
    validate_config()
    load_memory()
    global app
    app = build_app()
    logger.info("%s polling başlıyor", VERSION_NAME)
    app.run_polling(close_loop=False, drop_pending_updates=True)


if __name__ == "__main__":
    main()
