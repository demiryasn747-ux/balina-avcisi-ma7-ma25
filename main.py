import os
import re
import json
import time
import copy
import uuid
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

VERSION_NAME = "Balina Avcısı V11.3 ULTRA (SMC + MTF + VWAP + Session + Manipulation Guard)"
BOT_BUILD = os.getenv("BOT_BUILD", "V11.3")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com").strip().rstrip("/")
OKX_INST_TYPE = os.getenv("OKX_INST_TYPE", "SWAP").strip().upper()

MEMORY_FILE = os.getenv("MEMORY_FILE", "balina_v11_3_memory.json").strip()
LOG_FILE = os.getenv("LOG_FILE", "balina_v11_3.log").strip()
LOG_MAX_MB = float(os.getenv("LOG_MAX_MB", "10"))
LOG_BACKUPS = int(float(os.getenv("LOG_BACKUPS", "3")))
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Istanbul").strip()

# === TARAMA ===
HOT_SCAN_INTERVAL_SEC = float(os.getenv("HOT_SCAN_INTERVAL_SEC", "1.5"))
DEEP_SCAN_INTERVAL_SEC = float(os.getenv("DEEP_SCAN_INTERVAL_SEC", "8"))
MEMORY_SAVE_INTERVAL_SEC = int(float(os.getenv("MEMORY_SAVE_INTERVAL_SEC", "60")))
KLINE_CACHE_SEC = int(float(os.getenv("KLINE_CACHE_SEC", "5")))
KLINE_CACHE_MAX = int(float(os.getenv("KLINE_CACHE_MAX", "1500")))
TICKER_CACHE_SEC = int(float(os.getenv("TICKER_CACHE_SEC", "8")))
HTTP_TIMEOUT = int(float(os.getenv("HTTP_TIMEOUT", "12")))

# === COIN FİLTRESİ ===
MIN_24H_QUOTE_VOLUME = float(os.getenv("MIN_24H_QUOTE_VOLUME", "5000000"))
MAX_24H_QUOTE_VOLUME = float(os.getenv("MAX_24H_QUOTE_VOLUME", "100000000"))
COIN_MAX_PRICE = float(os.getenv("COIN_MAX_PRICE", "50"))
COIN_MIN_PRICE = float(os.getenv("COIN_MIN_PRICE", "0"))
EXCLUDE_MEMES = os.getenv("EXCLUDE_MEMES", "true").lower() == "true"
MEME_COIN_BASES = set(x.strip().upper() for x in os.getenv("MEME_COIN_BASES",
    "DOGE,SHIB,PEPE,1000PEPE,1000SHIB,1000BONK,1000FLOKI,WIF,BONK,FLOKI,MEME,BRETT,MEW,TURBO,POPCAT,MOG,NEIRO,DOGS,PNUT,ACT,BOME,SLERF,MYRO,WEN,TRUMP,MELANIA,MOODENG,GOAT,CHILLGUY,BAN,PONKE,FARTCOIN,AIDOGE,BABYDOGE,GIGA,APU,HIPPO,MOTHER,DEGEN,TOSHI,SPX,WOJAK,SUNDOG"
    ).split(",") if x.strip())
EXTRA_BLOCKLIST = set(x.strip().upper() for x in os.getenv("EXTRA_BLOCKLIST", "").split(",") if x.strip())
MA_COIN_LIMIT = int(float(os.getenv("MA_COIN_LIMIT", "200")))

# === SKOR ===
SIGNAL_SCORE_TREND_4H_BONUS = float(os.getenv("SIGNAL_SCORE_TREND_4H_BONUS", "10"))

# === RİSK VE POZİSYON ===
LEVERAGE = float(os.getenv("LEVERAGE", "1"))
MAX_POSITION_RISK_PCT = float(os.getenv("MAX_POSITION_RISK_PCT", "2.0"))
DEFAULT_MARGIN_USDT = float(os.getenv("DEFAULT_MARGIN_USDT", "100"))

# === TP/STOP ===
TP1_RR = float(os.getenv("TP1_RR", "2.0"))
TP2_RR = float(os.getenv("TP2_RR", "4.0"))
TP3_RR = float(os.getenv("TP3_RR", "7.0"))
TP4_RR = float(os.getenv("TP4_RR", "10.0"))
SABIT_STOP_PCT = float(os.getenv("SABIT_STOP_PCT", "2.0"))

# === BTC FİLTRE ===
V106_BTC_TREND_FILTER = os.getenv("V106_BTC_TREND_FILTER", "true").lower() == "true"
V106_BTC_EMA_FAST = int(float(os.getenv("V106_BTC_EMA_FAST", "20")))
V106_BTC_EMA_SLOW = int(float(os.getenv("V106_BTC_EMA_SLOW", "50")))
V106_BTC_CACHE_SEC = float(os.getenv("V106_BTC_CACHE_SEC", "90"))

# === MANİPÜLASYON SAVUNMASI (V11.2) ===
SPOOF_GUARD_ENABLED = os.getenv("SPOOF_GUARD_ENABLED", "true").lower() == "true"
SPOOF_CHECK_COUNT = int(float(os.getenv("SPOOF_CHECK_COUNT", "3")))
SPOOF_CHECK_INTERVAL = float(os.getenv("SPOOF_CHECK_INTERVAL", "2.0"))
SPOOF_CHANGE_THRESHOLD = float(os.getenv("SPOOF_CHANGE_THRESHOLD", "0.5"))

WASH_GUARD_ENABLED = os.getenv("WASH_GUARD_ENABLED", "true").lower() == "true"
WASH_VOL_MULTIPLIER = float(os.getenv("WASH_VOL_MULTIPLIER", "3.0"))
WASH_MAX_PRICE_MOVE = float(os.getenv("WASH_MAX_PRICE_MOVE", "0.5"))

PUMP_DUMP_GUARD_ENABLED = os.getenv("PUMP_DUMP_GUARD_ENABLED", "true").lower() == "true"
PUMP_DUMP_MAX_1H_MOVE = float(os.getenv("PUMP_DUMP_MAX_1H_MOVE", "25.0"))
PUMP_DUMP_MIN_VOL = float(os.getenv("PUMP_DUMP_MIN_VOL", "10000000"))

INSIDER_GUARD_ENABLED = os.getenv("INSIDER_GUARD_ENABLED", "true").lower() == "true"
INSIDER_QUIET_VOL_MULT = float(os.getenv("INSIDER_QUIET_VOL_MULT", "5.0"))
INSIDER_PRICE_MOVE_MAX = float(os.getenv("INSIDER_PRICE_MOVE_MAX", "2.0"))

STOP_HUNT_GUARD_ENABLED = os.getenv("STOP_HUNT_GUARD_ENABLED", "true").lower() == "true"
STOP_HUNT_WICK_RATIO = float(os.getenv("STOP_HUNT_WICK_RATIO", "0.6"))

# === V11.3 YENİ KATMANLAR ===
# VWAP
VWAP_ENABLED = os.getenv("VWAP_ENABLED", "true").lower() == "true"
VWAP_PERIOD_HOURS = int(float(os.getenv("VWAP_PERIOD_HOURS", "24")))
VWAP_BONUS_IN_CHART = os.getenv("VWAP_BONUS_IN_CHART", "true").lower() == "true"

# Session filter
SESSION_FILTER_ENABLED = os.getenv("SESSION_FILTER_ENABLED", "true").lower() == "true"
SESSION_ASIA_START_UTC = int(float(os.getenv("SESSION_ASIA_START_UTC", "0")))    # 00:00 UTC
SESSION_ASIA_END_UTC = int(float(os.getenv("SESSION_ASIA_END_UTC", "8")))        # 08:00 UTC
SESSION_LONDON_START_UTC = int(float(os.getenv("SESSION_LONDON_START_UTC", "8")))  # 08:00 UTC
SESSION_LONDON_END_UTC = int(float(os.getenv("SESSION_LONDON_END_UTC", "16")))    # 16:00 UTC
SESSION_NY_START_UTC = int(float(os.getenv("SESSION_NY_START_UTC", "13")))        # 13:00 UTC
SESSION_NY_END_UTC = int(float(os.getenv("SESSION_NY_END_UTC", "21")))            # 21:00 UTC
SESSION_BLOCK_ASIA_SHORT = os.getenv("SESSION_BLOCK_ASIA_SHORT", "false").lower() == "true"
SESSION_BLOCK_LONDON_LONG = os.getenv("SESSION_BLOCK_LONDON_LONG", "false").lower() == "true"

# Likidasyon haritası (tahmini)
LIQ_HEATMAP_ENABLED = os.getenv("LIQ_HEATMAP_ENABLED", "true").lower() == "true"
LIQ_HEATMAP_LEVERAGES = [int(x) for x in os.getenv("LIQ_HEATMAP_LEVERAGES", "5,10,25,50").split(",")]
LIQ_HEATMAP_DIST_PCT = float(os.getenv("LIQ_HEATMAP_DIST_PCT", "15.0"))  # %15 menzilde likidasyon ara
LIQ_HEATMAP_MIN_CLUSTER = float(os.getenv("LIQ_HEATMAP_MIN_CLUSTER", "500000"))  # min 500K USDT küme
LIQ_HEATMAP_BLOCK_CONFLICT = os.getenv("LIQ_HEATMAP_BLOCK_CONFLICT", "true").lower() == "true"

# ADX piyasa modu
ADX_ENABLED = os.getenv("ADX_ENABLED", "true").lower() == "true"
ADX_PERIOD = int(float(os.getenv("ADX_PERIOD", "14")))
ADX_TREND_THRESHOLD = float(os.getenv("ADX_TREND_THRESHOLD", "25"))
ADX_RANGE_THRESHOLD = float(os.getenv("ADX_RANGE_THRESHOLD", "20"))

# Multi-timeframe confluence
MTF_CONFLUENCE_ENABLED = os.getenv("MTF_CONFLUENCE_ENABLED", "true").lower() == "true"
MTF_REQUIRED_TFS = os.getenv("MTF_REQUIRED_TFS", "15m,5m").split(",")
MTF_MIN_AGREE = int(float(os.getenv("MTF_MIN_AGREE", "1")))  # kaç TF onay vermeli

# Korelasyon koruması
CORRELATION_GUARD_ENABLED = os.getenv("CORRELATION_GUARD_ENABLED", "true").lower() == "true"
CORRELATION_MAX_SAME_DIR = int(float(os.getenv("CORRELATION_MAX_SAME_DIR", "3")))  # aynı yönde max açık pozisyon

# Time-based exit
TIME_EXIT_ENABLED = os.getenv("TIME_EXIT_ENABLED", "true").lower() == "true"
TIME_EXIT_HOURS = float(os.getenv("TIME_EXIT_HOURS", "48"))
TIME_EXIT_MIN_PROFIT_R = float(os.getenv("TIME_EXIT_MIN_PROFIT_R", "0.5"))

# Adaptif pozisyon boyutlandırma
ADAPTIVE_SIZING = os.getenv("ADAPTIVE_SIZING", "true").lower() == "true"

# Volume-weighted momentum
VWM_ENABLED = os.getenv("VWM_ENABLED", "true").lower() == "true"

# === OKX RATE LIMIT ===
OKX_RATE_GENEL = float(os.getenv("OKX_RATE_GENEL", "14"))
OKX_BURST_GENEL = float(os.getenv("OKX_BURST_GENEL", "3"))
OKX_RATE_RUBIK = float(os.getenv("OKX_RATE_RUBIK", "2"))
OKX_BURST_RUBIK = float(os.getenv("OKX_BURST_RUBIK", "2"))
OKX_429_CEZA_SEC = float(os.getenv("OKX_429_CEZA_SEC", "20"))
OKX_EXECUTOR_WORKERS = int(float(os.getenv("OKX_EXECUTOR_WORKERS", "12")))

# === V10 SMC ===
V10_KLINE_LIMIT = int(float(os.getenv("V10_KLINE_LIMIT", "150")))
V10_SWING_LEFT = int(float(os.getenv("V10_SWING_LEFT", "2")))
V10_SWING_RIGHT = int(float(os.getenv("V10_SWING_RIGHT", "2")))
V10_FOMO_LOOKBACK = int(float(os.getenv("V10_FOMO_LOOKBACK", "5")))
V10_FOMO_MAX_MOVE = float(os.getenv("V10_FOMO_MAX_MOVE_PCT", "3.0"))
V10_PULLBACK_TOL = float(os.getenv("V10_PULLBACK_TOL_PCT", "0.6"))
V10_PULLBACK_WAIT = int(float(os.getenv("V10_PULLBACK_MAX_WAIT", "8")))
V10_ATR_PERIOD = int(float(os.getenv("V10_ATR_PERIOD", "14")))
V10_RSI_LONG_MAX = float(os.getenv("V10_RSI_LONG_MAX", "40"))
V10_RSI_SHORT_MIN = float(os.getenv("V10_RSI_SHORT_MIN", "70"))
V10_USE_4H_FILTER = os.getenv("V10_USE_4H_FILTER", "true").lower() == "true"
V10_OB_LOOKBACK = int(float(os.getenv("V10_OB_LOOKBACK", "20")))
V10_FVG_LOOKBACK = int(float(os.getenv("V10_FVG_LOOKBACK", "15")))
V10_VP_BINS = int(float(os.getenv("V10_VP_BINS", "24")))
V10_VP_LOOKBACK = int(float(os.getenv("V10_VP_LOOKBACK", "80")))
V10_CVD_WINDOW = int(float(os.getenv("V10_CVD_WINDOW", "20")))
V10_USE_ORDERBOOK = os.getenv("V10_USE_ORDERBOOK", "true").lower() == "true"
V10_OB_DEPTH = int(float(os.getenv("V10_OB_DEPTH", "20")))
V10_OB_WALL_MULT = float(os.getenv("V10_OB_WALL_MULT", "3.0"))
V10_ALERT_COOLDOWN_MIN = int(float(os.getenv("V10_ALERT_COOLDOWN_MIN", "60")))
V10_MAX_OPEN = int(float(os.getenv("V10_MAX_OPEN_POSITIONS", "12")))
V10_RISK_PCT = float(os.getenv("V10_RISK_PCT", "1.5"))
V107_CANLI_GIRIS = os.getenv("V107_CANLI_GIRIS", "true").lower() == "true"
V107_MAX_GIRIS_KAYMA = float(os.getenv("V107_MAX_GIRIS_KAYMA_PCT", "0.8"))
V107_TAKIP_TF = os.getenv("V107_TAKIP_TF", "1m").strip()
V107_TAKIP_LIMIT = int(float(os.getenv("V107_TAKIP_LIMIT", "300")))
V107_TAKIP_CACHE_SEC = float(os.getenv("V107_TAKIP_CACHE_SEC", "3"))
V107_TAKIP_ARALIK_SEC = int(float(os.getenv("V107_TAKIP_ARALIK_SEC", "45")))
V109_COIN_1H_UYUM = os.getenv("V109_COIN_1H_UYUM", "true").lower() == "true"
V109_COIN_EMA_FAST = int(float(os.getenv("V109_COIN_EMA_FAST", "20")))
V109_COIN_EMA_SLOW = int(float(os.getenv("V109_COIN_EMA_SLOW", "50")))
V107_ACIKKEN_ENGELLE = os.getenv("V107_ACIKKEN_ENGELLE", "true").lower() == "true"
V107_PIVOT_ATR = float(os.getenv("V107_PIVOT_ATR", "1.0"))
V107_RANGE_ENGELLE = os.getenv("V107_RANGE_ENGELLE", "true").lower() == "true"

# === GRAFİK ===
SIGNAL_CHART_ENABLED = os.getenv("SIGNAL_CHART_ENABLED", "true").lower() == "true"
SIGNAL_CHART_TF = os.getenv("SIGNAL_CHART_TF", "1H").strip()
SIGNAL_CHART_CANDLES = int(float(os.getenv("SIGNAL_CHART_CANDLES", "72")))
SIGNAL_CHART_FIB = os.getenv("SIGNAL_CHART_FIB", "true").lower() == "true"
SIGNAL_NEWS_ENABLED = os.getenv("SIGNAL_NEWS_ENABLED", "true").lower() == "true"
SIGNAL_NEWS_MAX = int(float(os.getenv("SIGNAL_NEWS_MAX", "2")))
SIGNAL_NEWS_CACHE_SEC = int(float(os.getenv("SIGNAL_NEWS_CACHE_SEC", "900")))
SIGNAL_NEWS_TIMEOUT_SEC = float(os.getenv("SIGNAL_NEWS_TIMEOUT_SEC", "6"))
SIGNAL_NEWS_MAX_AGE_H = float(os.getenv("SIGNAL_NEWS_MAX_AGE_H", "48"))

# === PING/HAVUZ ===
AUTO_SYMBOL_REFRESH_SEC = int(float(os.getenv("AUTO_SYMBOL_REFRESH_SEC", "1800")))
SYMBOL_FAIL_BLOCK_SEC = int(float(os.getenv("SYMBOL_FAIL_BLOCK_SEC", "900")))
SYMBOL_FAIL_FORGET_SEC = int(float(os.getenv("SYMBOL_FAIL_FORGET_SEC", "43200")))
SYMBOL_FAIL_MAX_STREAK = int(float(os.getenv("SYMBOL_FAIL_MAX_STREAK", "3")))
OKX_INSTRUMENT_CACHE_SEC = int(float(os.getenv("OKX_INSTRUMENT_CACHE_SEC", "1800")))
DYNAMIC_TOP_200_COIN_POOL = os.getenv("DYNAMIC_TOP_200_COIN_POOL", "true").lower() == "true"
RAW_COINS_ENV = os.getenv("COINS", "").strip()

DEFAULT_COINS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "AVAX-USDT-SWAP", "NEAR-USDT-SWAP",
    "ARB-USDT-SWAP", "OP-USDT-SWAP", "SUI-USDT-SWAP", "APT-USDT-SWAP", "SEI-USDT-SWAP",
    "TIA-USDT-SWAP", "JUP-USDT-SWAP", "PYTH-USDT-SWAP", "ENA-USDT-SWAP", "PENDLE-USDT-SWAP",
    "FET-USDT-SWAP", "RENDER-USDT-SWAP", "TAO-USDT-SWAP", "WLD-USDT-SWAP", "INJ-USDT-SWAP",
    "RUNE-USDT-SWAP", "STX-USDT-SWAP", "MANTA-USDT-SWAP", "GALA-USDT-SWAP", "SAND-USDT-SWAP",
    "AR-USDT-SWAP", "HBAR-USDT-SWAP", "KAS-USDT-SWAP", "CRV-USDT-SWAP", "DYDX-USDT-SWAP",
    "GMT-USDT-SWAP", "ZIL-USDT-SWAP", "ZRX-USDT-SWAP", "API3-USDT-SWAP", "BLUR-USDT-SWAP",
    "ACH-USDT-SWAP", "PEOPLE-USDT-SWAP", "LDO-USDT-SWAP", "ARKM-USDT-SWAP", "MEME-USDT-SWAP",
    "NFP-USDT-SWAP", "STRK-USDT-SWAP", "PORTAL-USDT-SWAP", "ALT-USDT-SWAP", "AI-USDT-SWAP",
    "MAVIA-USDT-SWAP", "AEVO-USDT-SWAP", "OM-USDT-SWAP", "NOT-USDT-SWAP", "TURBO-USDT-SWAP",
    "BRETT-USDT-SWAP", "MEW-USDT-SWAP", "POLYX-USDT-SWAP", "CHZ-USDT-SWAP", "ROSE-USDT-SWAP",
    "ID-USDT-SWAP", "SXP-USDT-SWAP", "IOST-USDT-SWAP", "ONE-USDT-SWAP", "CTSI-USDT-SWAP",
    "HOT-USDT-SWAP", "CELR-USDT-SWAP", "BEL-USDT-SWAP", "FLM-USDT-SWAP", "BAKE-USDT-SWAP",
    "DUSK-USDT-SWAP", "HOOK-USDT-SWAP", "PHB-USDT-SWAP", "MAGIC-USDT-SWAP", "RSR-USDT-SWAP",
    "FLOW-USDT-SWAP", "CFX-USDT-SWAP", "MASK-USDT-SWAP", "SKL-USDT-SWAP",
]
COINS = [x.strip().upper() for x in (RAW_COINS_ENV or ",".join(DEFAULT_COINS)).split(",") if x.strip()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=int(LOG_MAX_MB * 1024 * 1024),
                            backupCount=LOG_BACKUPS, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("balina_v11_3")

TZ = ZoneInfo(TIMEZONE_NAME)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"BalinaAvcisi/{BOT_BUILD}"})

_HTTP_POOL = int(float(os.getenv("HTTP_POOL_SIZE", "32")))
try:
    _adapter = requests.adapters.HTTPAdapter(pool_connections=_HTTP_POOL,
                                             pool_maxsize=_HTTP_POOL, max_retries=0)
    SESSION.mount("https://", _adapter)
    SESSION.mount("http://", _adapter)
except Exception:
    pass


class _TokenBucket:
    def __init__(self, rate: float, burst: float, ad: str):
        self.rate = max(0.1, rate)
        self.burst = max(1.0, burst)
        self.ad = ad
        self._tokens = self.burst
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                simdi = time.monotonic()
                self._tokens = min(self.burst, self._tokens + (simdi - self._last) * self._etkin_rate())
                self._last = simdi
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                eksik = (1.0 - self._tokens) / self._etkin_rate()
            uyku = min(max(eksik, 0.005), 1.0)
            time.sleep(uyku)

    def _etkin_rate(self) -> float:
        if time.monotonic() < _OKX_CEZA["kadar"]:
            return max(0.5, self.rate * 0.5)
        return self.rate


_OKX_CEZA: Dict[str, float] = {"kadar": 0.0, "sayac": 0.0}
_BUCKET_GENEL = _TokenBucket(OKX_RATE_GENEL, OKX_BURST_GENEL, "genel")
_BUCKET_RUBIK = _TokenBucket(OKX_RATE_RUBIK, OKX_BURST_RUBIK, "rubik")


def _okx_kova(path: str) -> "_TokenBucket":
    return _BUCKET_RUBIK if "/rubik/" in path else _BUCKET_GENEL


def _okx_429_kaydet() -> None:
    _OKX_CEZA["kadar"] = time.monotonic() + OKX_429_CEZA_SEC
    _OKX_CEZA["sayac"] = _OKX_CEZA.get("sayac", 0.0) + 1


OKX_EXECUTOR = ThreadPoolExecutor(max_workers=OKX_EXECUTOR_WORKERS, thread_name_prefix="okx")


async def _okx_get_async(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(OKX_EXECUTOR, _okx_get, path, params, max_retries)


_CHART_LOCK = threading.Lock()
kline_cache: Dict[str, Tuple[float, List[List[Any]]]] = {}
ticker_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
instrument_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
okx_live_symbols: Dict[str, Dict[str, Any]] = {}
symbol_fail_state: Dict[str, Dict[str, Any]] = {}
oi_cache: Dict[str, Tuple[float, float]] = {}
funding_cache: Dict[str, Tuple[float, float]] = {}
_correlation_group_cache: Dict[str, str] = {}

memory: Dict[str, Any] = {
    "hot": {},
    "signals": {},
    "follows": {},
    "stats": {},
    "last_signal_ts": 0.0,
    "v10_paper": {"open": [], "closed": [], "buckets": {}},
}

stats: Dict[str, Any] = {
    "analyzed": 0, "api_fail": 0, "telegram_fail": 0, "signal_sent": 0,
    "invalid_symbol_skip": 0, "blocked_symbol_skip": 0, "volume_reject": 0,
    "okx_symbol_pruned": 0, "okx_symbol_refresh": 0,
    "v10_analyzed": 0, "v10_candidates": 0, "v10_signals": 0,
    "v10_red_veri": 0, "v10_red_yapi": 0, "v10_red_rsi": 0,
    "v10_red_btc_ters": 0, "v10_red_btc_karisik": 0, "v10_red_btc_veri": 0,
    "v107_red_kayma": 0, "v107_red_acik_poz": 0, "v107_red_defter_dolu": 0,
    "v107_pivot_elendi": 0, "v107_red_range": 0, "v107_belirsiz_bar": 0, "v107_takip_bosluk": 0,
    "v11_red_coin_ema": 0, "v11_red_fomo": 0, "v11_red_oi_zayif": 0,
    "v112_red_spoofing": 0, "v112_red_wash": 0, "v112_red_pump_dump": 0,
    "v112_red_insider": 0, "v112_hit_stop_hunt": 0,
    # V11.3 yeni
    "v113_red_vwap": 0, "v113_red_session": 0, "v113_red_liq_conflict": 0,
    "v113_red_mtf": 0, "v113_red_correlation": 0, "v113_hit_liq_cluster": 0,
}

app = None
memory_lock = asyncio.Lock()
v10_last_alert: Dict[str, float] = {}
v10_sent_candle: Dict[str, str] = {}
_v107_stop_kilit: Dict[str, float] = {}

_V106_BTC_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}


def tr_now() -> datetime:
    return datetime.now(TZ)

def tr_str(ts: Optional[float] = None) -> str:
    dt = datetime.fromtimestamp(ts, TZ) if ts else tr_now()
    return dt.strftime("%d.%m.%Y %H:%M:%S")

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
    memory.setdefault("v10_paper", {"open": [], "closed": [], "buckets": {}})
    memory.setdefault("last_signal_ts", 0.0)

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
            memory = {"hot": {}, "signals": {}, "follows": {}, "stats": {},
                      "last_signal_ts": 0.0, "v10_paper": {"open": [], "closed": [], "buckets": {}}}
    else:
        ensure_memory_shape()

def _write_memory_snapshot(snapshot: Dict[str, Any]) -> None:
    for _ in range(3):
        try:
            tmp_path = MEMORY_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, MEMORY_FILE)
            return
        except RuntimeError:
            time.sleep(0.05)
        except Exception as e:
            logger.exception("Memory yazılamadı: %s", e)
            return

def save_memory() -> None:
    try:
        ensure_memory_shape()
        snapshot = copy.deepcopy(memory)
    except Exception as e:
        logger.exception("Memory snapshot alınamadı: %s", e)
        return
    _write_memory_snapshot(snapshot)

async def save_memory_async() -> None:
    async with memory_lock:
        ensure_memory_shape()
        snapshot = copy.deepcopy(memory)
    await asyncio.to_thread(_write_memory_snapshot, snapshot)

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
        if now_ts - safe_float(hot[sym].get("last_seen", 0)) > 1800:
            hot.pop(sym, None)
    cleanup_symbol_fail_state()

def note_symbol_fail(symbol: str, reason: str = "") -> None:
    now_ts = time.time()
    rec = symbol_fail_state.setdefault(symbol, {"streak": 0, "last_ts": 0.0, "block_until": 0.0, "last_reason": ""})
    rec["streak"] = int(rec.get("streak", 0)) + 1
    rec["last_ts"] = now_ts
    rec["last_reason"] = str(reason)[:220]
    if rec["streak"] >= max(1, SYMBOL_FAIL_MAX_STREAK):
        rec["block_until"] = now_ts + SYMBOL_FAIL_BLOCK_SEC
        stats["okx_symbol_fail_block"] = int(stats.get("okx_symbol_fail_block", 0)) + 1

def note_symbol_success(symbol: str) -> None:
    rec = symbol_fail_state.get(symbol)
    if not rec:
        return
    rec["streak"] = 0
    rec["block_until"] = 0.0
    rec["last_reason"] = ""

def symbol_temporarily_blocked(symbol: str) -> bool:
    return time.time() < safe_float(symbol_fail_state.get(symbol, {}).get("block_until", 0))

def get_blocked_symbol_count() -> int:
    now_ts = time.time()
    return sum(1 for rec in symbol_fail_state.values() if now_ts < safe_float(rec.get("block_until", 0)))

def _telegram_api_send(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        stats["telegram_fail"] += 1
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}
    resp = SESSION.post(url, data=payload, timeout=HTTP_TIMEOUT)
    return resp.status_code == 200 and resp.json().get("ok") is True

async def safe_send_telegram(text: str, retry: int = 3, delay_sec: float = 1.5) -> bool:
    for i in range(1, retry + 1):
        try:
            if await asyncio.to_thread(_telegram_api_send, text):
                return True
        except Exception:
            pass
        await asyncio.sleep(delay_sec * i)
    stats["telegram_fail"] += 1
    return False

import io as _io

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    from matplotlib.patches import Rectangle as _Rect
    _MPL_OK = True
except Exception:
    _MPL_OK = False

_news_cache: Dict[str, Tuple[float, str]] = {}


def _render_signal_chart_sync(symbol, direction, klines, entry, stop, tps, meta, tz_name, vwap_val=None, session_name="", adx_val=0.0):
    if not _MPL_OK:
        return None
    try:
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI

        def _f(v, d=0.0):
            try:
                return float(v)
            except Exception:
                return d

        def _fmt(x):
            x = _f(x)
            if x == 0:
                return "0"
            if x >= 100:
                return f"{x:,.2f}"
            if x >= 1:
                return f"{x:.4f}"
            return f"{x:.6f}"

        rows = [r for r in klines if r and len(r) >= 6]
        if len(rows) < 30:
            return None
        rows = rows[-max(40, min(SIGNAL_CHART_CANDLES, 200)):]
        ts = [_f(r[0]) for r in rows]
        op = [_f(r[1]) for r in rows]
        hi = [_f(r[2]) for r in rows]
        lo = [_f(r[3]) for r in rows]
        cl = [_f(r[4]) for r in rows]
        vo = [_f(r[5]) for r in rows]
        n = len(rows)

        def _ema_local(vals, period):
            if len(vals) < period:
                return []
            k = 2.0 / (period + 1.0)
            out = [sum(vals[:period]) / period]
            for v in vals[period:]:
                out.append(v * k + out[-1] * (1 - k))
            return [None] * (period - 1) + out

        ema20 = _ema_local(cl, 20)
        ema50 = _ema_local(cl, 50)

        BG, PANEL, GRID = "#0b0f17", "#0f1522", "#1f2937"
        UP, DOWN = "#22c55e", "#ef4444"
        TXT, SUB = "#e5e7eb", "#9ca3af"
        VWAP_COL = "#a855f7"

        d = (direction or "").upper()
        dir_col = UP if d == "LONG" else (DOWN if d == "SHORT" else SUB)

        fig = _plt.figure(figsize=(10.4, 6.4), dpi=115, facecolor=BG)
        gs = fig.add_gridspec(2, 1, height_ratios=[3.4, 1.0], hspace=0.06,
                              left=0.055, right=0.905, top=0.90, bottom=0.09)
        ax = fig.add_subplot(gs[0])
        axv = fig.add_subplot(gs[1], sharex=ax)
        for a in (ax, axv):
            a.set_facecolor(PANEL)
            for s in a.spines.values():
                s.set_color(GRID)
            a.tick_params(colors=SUB, labelsize=8)
            a.grid(True, color=GRID, alpha=0.35, linewidth=0.6)

        for i in range(n):
            c = UP if cl[i] >= op[i] else DOWN
            ax.plot([i, i], [lo[i], hi[i]], color=c, linewidth=0.9, alpha=0.95, zorder=3)
            body_low = min(op[i], cl[i])
            body_h = max(abs(cl[i] - op[i]), max(cl) * 1e-6)
            ax.add_patch(_Rect((i - 0.33, body_low), 0.66, body_h,
                               facecolor=c, edgecolor=c, linewidth=0.5, zorder=4))
            axv.bar(i, vo[i], width=0.72, color=c, alpha=0.85, zorder=3)

        if ema20:
            ax.plot(range(n), ema20, color="#f59e0b", linewidth=1.4, alpha=0.95, label="EMA20", zorder=5)
        if ema50:
            ax.plot(range(n), ema50, color="#3b82f6", linewidth=1.4, alpha=0.95, label="EMA50", zorder=5)

        entry = _f(entry)
        stop = _f(stop)
        tp_items = [(k, _f(v)) for k, v in (tps or {}).items() if _f(v) > 0]

        x_right = n - 1 + max(6.0, n * 0.14)
        ax.set_xlim(-1, x_right)

        y_all = lo + hi + [v for v in (entry, stop) if v > 0] + [v for _, v in tp_items]
        if vwap_val and vwap_val > 0:
            y_all.append(vwap_val)
        y_min, y_max = min(y_all), max(y_all)
        pad = (y_max - y_min) * 0.06 or y_max * 0.01
        ax.set_ylim(y_min - pad, y_max + pad)

        if entry > 0 and stop > 0:
            ax.axhspan(min(entry, stop), max(entry, stop), color=DOWN, alpha=0.10, zorder=1)
        if entry > 0 and tp_items:
            best_tp = max((v for _, v in tp_items), key=lambda v: abs(v - entry))
            ax.axhspan(min(entry, best_tp), max(entry, best_tp), color=UP, alpha=0.08, zorder=1)

        def _hline(y, color, style, label):
            if y <= 0:
                return
            ax.axhline(y, color=color, linestyle=style, linewidth=1.3, alpha=0.95, zorder=6)
            ax.text(x_right, y, f" {label} {_fmt(y)}", color=color, fontsize=8.2,
                    va="center", ha="left", fontweight="bold", clip_on=False)

        _hline(entry, "#e5e7eb", "--", "GİRİŞ")
        _hline(stop, DOWN, "-", "STOP")
        tp_cols = ["#10b981", "#34d399", "#6ee7b7", "#a7f3d0"]
        for idx, (name, val) in enumerate(sorted(tp_items, key=lambda kv: abs(kv[1] - entry))):
            _hline(val, tp_cols[min(idx, 3)], "-.", name)

        # VWAP
        if vwap_val and vwap_val > 0:
            _hline(vwap_val, VWAP_COL, ":", "VWAP")

        try:
            tz = _ZI(tz_name)
        except Exception:
            tz = None
        ticks = [int(i) for i in [0, n * 0.25, n * 0.5, n * 0.75, n - 1]]
        ax.set_xticks(ticks)
        labels = []
        for i in ticks:
            try:
                dt = _dt.fromtimestamp(ts[i] / 1000.0, tz)
                labels.append(dt.strftime("%d.%m %H:%M"))
            except Exception:
                labels.append("")
        ax.set_xticklabels([])
        axv.set_xticks(ticks)
        axv.set_xticklabels(labels, color=SUB, fontsize=7.6)
        axv.set_yticks([])

        meta = meta or {}
        score = meta.get("score")
        rsi = meta.get("rsi")
        fig.text(0.055, 0.955, f"{symbol}", color=TXT, fontsize=14, fontweight="bold")
        fig.text(0.055 + 0.012 * len(str(symbol)) + 0.02, 0.955, d or "-",
                 color=dir_col, fontsize=14, fontweight="bold")
        bits = [f"TF {SIGNAL_CHART_TF}"]
        if score is not None:
            bits.append(f"Skor {round(_f(score))}/100")
        if rsi is not None:
            bits.append(f"RSI {round(_f(rsi))}")
        if adx_val > 0:
            bits.append(f"ADX {round(adx_val, 1)}")
        if session_name:
            bits.append(session_name)
        fig.text(0.902, 0.955, "  ·  ".join(bits), color=SUB, fontsize=9, ha="right")

        ax.text(0.5, 0.5, "BALİNA AVCISI", transform=ax.transAxes, color=TXT,
                fontsize=34, fontweight="bold", alpha=0.06, ha="center", va="center", zorder=2)
        if ema20 or ema50:
            leg = ax.legend(loc="upper left", fontsize=7.5, framealpha=0.15,
                            facecolor=PANEL, edgecolor=GRID, labelcolor=SUB)
            leg.set_zorder(7)

        buf = _io.BytesIO()
        fig.savefig(buf, format="png", facecolor=BG, bbox_inches="tight")
        _plt.close(fig)
        return buf.getvalue()
    except Exception:
        try:
            _plt.close("all")
        except Exception:
            pass
        return None


async def render_signal_chart(symbol, direction, entry, stop, tps, meta):
    try:
        k = await get_klines(symbol, SIGNAL_CHART_TF, SIGNAL_CHART_CANDLES)
        if len(k) < 30:
            return None
        vwap_val = 0.0
        if VWAP_ENABLED:
            vwap_val = vwap_hesapla(k, VWAP_PERIOD_HOURS) or 0.0
        return await asyncio.to_thread(_render_signal_chart_sync, symbol, direction,
                                       k, entry, stop, tps or {}, meta or {}, TIMEZONE_NAME,
                                       vwap_val, meta.get("session_name", ""), safe_float(meta.get("adx", 0)))
    except Exception:
        return None


def _telegram_api_send_photo(caption: str, png_bytes: bytes) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": (caption or "")[:1024]}
    files = {"photo": ("sinyal.png", png_bytes, "image/png")}
    resp = SESSION.post(url, data=data, files=files, timeout=max(HTTP_TIMEOUT, 25))
    return resp.status_code == 200 and resp.json().get("ok") is True


async def safe_send_telegram_photo(caption: str, png_bytes: bytes, retry: int = 2, delay_sec: float = 1.5) -> bool:
    for i in range(1, retry + 1):
        try:
            if await asyncio.to_thread(_telegram_api_send_photo, caption, png_bytes):
                return True
        except Exception:
            pass
        await asyncio.sleep(delay_sec * i)
    return False


def v107_haber_alakali(base: str, title: str) -> bool:
    b = (base or "").strip()
    if not b or not title:
        return False
    try:
        kalip = r"(?<![0-9A-Za-zĞÜŞİÖÇğüşıöç])" + re.escape(b) + r"(?![0-9A-Za-zĞÜŞİÖÇğüşıöç])"
        bayrak = 0 if len(b) <= 3 else re.IGNORECASE
        return re.search(kalip, title, bayrak) is not None
    except Exception:
        return False


def _fetch_coin_news_sync(base: str) -> str:
    import xml.etree.ElementTree as _ET
    from email.utils import parsedate_to_datetime as _pd
    url = "https://news.google.com/rss/search"
    params = {"q": f"{base} coin kripto", "hl": "tr", "gl": "TR", "ceid": "TR:tr"}
    resp = SESSION.get(url, params=params, timeout=SIGNAL_NEWS_TIMEOUT_SEC)
    if resp.status_code != 200:
        return ""
    root = _ET.fromstring(resp.content)
    out: List[str] = []
    now = time.time()
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        if not v107_haber_alakali(base, title):
            continue
        try:
            dt = _pd(item.findtext("pubDate") or "")
            age_h = (now - dt.timestamp()) / 3600.0
            if age_h > SIGNAL_NEWS_MAX_AGE_H or age_h < -1:
                continue
        except Exception:
            pass
        if len(title) > 95:
            title = title[:92] + "..."
        out.append(f"• {title}")
        if len(out) >= SIGNAL_NEWS_MAX:
            break
    return "\n".join(out)


async def fetch_coin_news(symbol: str) -> str:
    if not SIGNAL_NEWS_ENABLED:
        return ""
    base = (symbol or "").split("-")[0].strip().upper()
    if not base:
        return ""
    now = time.time()
    cached = _news_cache.get(base)
    if cached and now - cached[0] <= SIGNAL_NEWS_CACHE_SEC:
        return cached[1]
    try:
        text = await asyncio.to_thread(_fetch_coin_news_sync, base)
    except Exception:
        text = ""
    _news_cache[base] = (now, text)
    if len(_news_cache) > 300:
        oldest = sorted(_news_cache.items(), key=lambda kv: kv[1][0])[:100]
        for k_, _ in oldest:
            _news_cache.pop(k_, None)
    return text


async def send_rich_signal(text: str, symbol: str, direction: str,
                           entry: float = 0.0, stop: float = 0.0,
                           tps: Optional[Dict[str, Any]] = None,
                           meta: Optional[Dict[str, Any]] = None) -> bool:
    full_text = text or ""
    try:
        news = await fetch_coin_news(symbol)
        if news:
            full_text = f"{full_text}\n📰 Haber Radarı ({(symbol or '').split('-')[0]}):\n{news}"
    except Exception:
        pass

    png = None
    if SIGNAL_CHART_ENABLED and _MPL_OK:
        try:
            png = await render_signal_chart(symbol, direction, safe_float(entry),
                                            safe_float(stop), tps or {}, meta or {})
        except Exception:
            png = None

    if png:
        try:
            if len(full_text) <= 1024:
                if await safe_send_telegram_photo(full_text, png):
                    return True
            else:
                head = "\n".join(full_text.split("\n")[:3]) + "\n📊 Detaylar altta ⤵"
                if await safe_send_telegram_photo(head, png):
                    pass
                return await safe_send_telegram(full_text)
        except Exception:
            pass

    return await safe_send_telegram(full_text)


def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper().replace("/", "-")
    if s.endswith("-SWAP"):
        return s
    if s.endswith("USDT") and "-" not in s:
        return f"{s[:-4]}-USDT-SWAP"
    if s.endswith("-USDT"):
        return f"{s}-SWAP"
    if "-" not in s:
        return f"{s}-USDT-SWAP"
    return s


def _okx_get(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> Any:
    url = f"{OKX_BASE_URL}{path}"
    last_err: Optional[Exception] = None
    kova = _okx_kova(path)
    for attempt in range(max_retries + 1):
        try:
            kova.acquire()
            resp = SESSION.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                if resp.status_code == 429:
                    _okx_429_kaydet()
                if attempt < max_retries:
                    time.sleep(0.5 + attempt * 0.5)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            data = resp.json()
            if str(data.get("code", "1")) != "0":
                raise RuntimeError(f"OKX hata: code={data.get('code')}")
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
    return [row[0], row[1], row[2], row[3], row[4], row[5],
            row[6] if len(row) > 6 else row[5],
            row[7] if len(row) > 7 else row[6] if len(row) > 6 else row[5],
            row[8] if len(row) > 8 else "1"]


async def get_okx_instruments(force: bool = False) -> Dict[str, Dict[str, Any]]:
    cached = instrument_cache.get("okx_instruments")
    now_ts = time.time()
    if cached and not force and now_ts - cached[0] <= OKX_INSTRUMENT_CACHE_SEC:
        return cached[1]
    try:
        data = await _okx_get_async("/api/v5/public/instruments", {"instType": OKX_INST_TYPE})
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
    except Exception:
        stats["api_fail"] += 1
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
        if tickers:
            top_symbols = pick_top_200_from_tickers(tickers, instruments)
            if top_symbols:
                source_symbols = top_symbols
    valid, invalid, seen = [], [], set()
    for sym in source_symbols:
        ns = normalize_symbol(sym)
        if ns in seen:
            continue
        seen.add(ns)
        (valid if ns in instruments else invalid).append(ns)
    if valid:
        COINS = valid[:MA_COIN_LIMIT] if DYNAMIC_TOP_200_COIN_POOL else valid
    stats["okx_symbol_refresh"] += 1
    stats["okx_symbol_pruned"] = len(invalid)
    logger.info("Havuz yenilendi | aktif=%s | çıkarılan=%s", len(COINS), len(invalid))
    return len(COINS), len(invalid)


async def symbol_refresh_loop() -> None:
    while True:
        try:
            await refresh_coin_pool(force=True)
        except Exception as e:
            logger.exception("symbol_refresh_loop hata: %s", e)
        await asyncio.sleep(max(300, AUTO_SYMBOL_REFRESH_SEC))


def _kline_cache_buda() -> None:
    if len(kline_cache) <= KLINE_CACHE_MAX:
        return
    try:
        sirali = sorted(kline_cache.items(), key=lambda x: x[1][0])
        for key, _ in sirali[: max(1, len(kline_cache) - KLINE_CACHE_MAX)]:
            kline_cache.pop(key, None)
    except Exception:
        kline_cache.clear()


async def get_klines(symbol: str, interval: str, limit: int = 120, ttl: Optional[float] = None) -> List[List[Any]]:
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
    omur = KLINE_CACHE_SEC if ttl is None else float(ttl)
    if cached and now_ts - cached[0] <= omur:
        return cached[1]
    try:
        data = await _okx_get_async("/api/v5/market/candles",
            {"instId": symbol, "bar": interval, "limit": min(limit, 300)})
        rows = [_okx_to_kline(x) for x in reversed(data)]
        if not rows:
            stats["api_fail"] += 1
            note_symbol_fail(symbol, f"{interval}:empty")
            return []
        note_symbol_success(symbol)
        kline_cache[cache_key] = (now_ts, rows)
        _kline_cache_buda()
        return rows
    except Exception as e:
        stats["api_fail"] += 1
        note_symbol_fail(symbol, f"{interval}:{e}")
        return []


async def get_24h_tickers() -> Dict[str, Dict[str, Any]]:
    cached = ticker_cache.get("24hr")
    now_ts = time.time()
    if cached and now_ts - cached[0] <= TICKER_CACHE_SEC:
        return cached[1]
    try:
        data = await _okx_get_async("/api/v5/market/tickers", {"instType": OKX_INST_TYPE})
        mp = {str(x.get("instId", "")).upper(): x for x in data if x.get("instId")}
        ticker_cache["24hr"] = (now_ts, mp)
        return mp
    except Exception:
        stats["api_fail"] += 1
        return cached[1] if cached else {}


def quote_volume_from_ticker(row: Dict[str, Any]) -> float:
    last = safe_float(row.get("last", 0))
    vol24h = safe_float(row.get("vol24h", 0))
    vol_ccy_24h = safe_float(row.get("volCcy24h", 0))
    return max(vol_ccy_24h, vol24h * max(last, 1e-12))


def _base_of(symbol: str) -> str:
    s = (symbol or "").upper().replace("-USDT-SWAP", "").replace("-USDT", "").replace("USDT", "")
    return s.replace("-SWAP", "").replace("/", "").strip()


def coin_allowed(ns: str, last_price: float) -> bool:
    base = _base_of(ns)
    if EXCLUDE_MEMES and base in MEME_COIN_BASES:
        return False
    if base in EXTRA_BLOCKLIST:
        return False
    if COIN_MAX_PRICE > 0 and last_price > COIN_MAX_PRICE:
        return False
    if COIN_MIN_PRICE > 0 and 0 < last_price < COIN_MIN_PRICE:
        return False
    return True


def pick_top_200_from_tickers(tickers, instruments):
    rows = []
    for sym, row in tickers.items():
        ns = normalize_symbol(sym)
        if not ns.endswith("-USDT-SWAP"):
            continue
        if instruments and ns not in instruments:
            continue
        qv = quote_volume_from_ticker(row)
        if qv < MIN_24H_QUOTE_VOLUME:
            continue
        if MAX_24H_QUOTE_VOLUME > 0 and qv > MAX_24H_QUOTE_VOLUME:
            continue
        if not coin_allowed(ns, safe_float(row.get("last", 0))):
            continue
        rows.append((ns, qv))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in rows[:MA_COIN_LIMIT]]


async def fetch_okx_oi_change(symbol: str, lookback_periods: int = 12) -> Optional[float]:
    symbol = normalize_symbol(symbol)
    ccy = symbol.split("-")[0]
    if not ccy:
        return None
    try:
        d = await _okx_get_async("/api/v5/rubik/stat/contracts/open-interest-volume",
                                    {"ccy": ccy, "period": "5m"})
    except Exception:
        return None
    if not isinstance(d, list) or len(d) < lookback_periods + 1:
        return None
    try:
        oi_now = safe_float(d[0][1])
        oi_past = safe_float(d[lookback_periods][1])
    except (IndexError, TypeError):
        return None
    if oi_past <= 0:
        return None
    return (oi_now - oi_past) / oi_past * 100.0


async def fetch_okx_funding_rate(symbol: str) -> Optional[float]:
    symbol = normalize_symbol(symbol)
    if not symbol or "-" not in symbol:
        return None
    cached = funding_cache.get(symbol)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= 1800:
        return cached[1]
    try:
        data = await _okx_get_async("/api/v5/public/funding-rate", {"instId": symbol})
        if not data:
            return None
        row = data[0] if isinstance(data, list) else data
        rate = float(row.get("fundingRate", 0) or 0)
        if -0.05 < rate < 0.05:
            funding_cache[symbol] = (now_ts, rate)
            return rate
        return None
    except Exception:
        return None


async def fetch_okx_open_interest_value(symbol: str) -> Optional[float]:
    """Anlık OI değeri (USDT cinsinden yaklaşık)."""
    symbol = normalize_symbol(symbol)
    if not symbol or "-" not in symbol:
        return None
    cached = oi_cache.get(symbol)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= 30:
        return cached[1]
    try:
        data = await _okx_get_async("/api/v5/public/open-interest",
            {"instType": "SWAP", "instId": symbol})
        if not data:
            return None
        row = data[0]
        oi = safe_float(row.get("oi", 0))
        oi_ccy = safe_float(row.get("oiCcy", 0))
        val = oi_ccy if oi_ccy > 0 else oi
        if val > 0:
            oi_cache[symbol] = (now_ts, val)
            return val
        return None
    except Exception:
        return None


async def v106_btc_trend() -> Dict[str, Any]:
    now = time.time()
    cached = _V106_BTC_CACHE.get("data")
    if cached is not None and (now - safe_float(_V106_BTC_CACHE.get("ts", 0))) < V106_BTC_CACHE_SEC:
        return cached
    out = {"dir_1h": "FLAT", "dir_4h": "FLAT", "allow": None, "ok": False}

    def _dir(cl):
        if len(cl) < V106_BTC_EMA_SLOW + 2:
            return "FLAT"
        f = s_ema(cl, V106_BTC_EMA_FAST)[-1]
        s = s_ema(cl, V106_BTC_EMA_SLOW)[-1]
        if f > s:
            return "UP"
        if f < s:
            return "DOWN"
        return "FLAT"

    try:
        need = max(V106_BTC_EMA_SLOW * 3, 120)
        k1h = await get_klines("BTC-USDT-SWAP", "1H", need)
        k4h = await get_klines("BTC-USDT-SWAP", "4H", need)
        c1 = _s_closes(_s_closed(k1h))
        c4 = _s_closes(_s_closed(k4h))
        d1 = _dir(c1)
        d4 = _dir(c4)
        allow = None
        if d1 == "UP" and d4 == "UP":
            allow = "LONG"
        elif d1 == "DOWN" and d4 == "DOWN":
            allow = "SHORT"
        out = {"dir_1h": d1, "dir_4h": d4, "allow": allow,
               "ok": (d1 != "FLAT" and d4 != "FLAT")}
    except Exception:
        pass
    _V106_BTC_CACHE["data"] = out
    _V106_BTC_CACHE["ts"] = now
    return out


def closes(klines): return [safe_float(x[4]) for x in klines]
def highs(klines): return [safe_float(x[2]) for x in klines]
def lows(klines): return [safe_float(x[3]) for x in klines]
def volumes(klines): return [safe_float(x[5]) for x in klines]


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
    return [out[0]] * (len(values) - len(out)) + out


def rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return [50.0 for _ in values]
    rsis = [50.0] * len(values)
    gains, losses = [], []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))
        if i >= period:
            ag = avg(gains[i - period:i])
            al = avg(losses[i - period:i])
            rs = 999.0 if al == 0 else ag / al
            rsis[i] = 100 - (100 / (1 + rs))
    return rsis


def true_ranges(klines):
    if len(klines) < 2:
        return [0.0 for _ in klines]
    trs = [0.0]
    for i in range(1, len(klines)):
        h = safe_float(klines[i][2]); l = safe_float(klines[i][3]); pc = safe_float(klines[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return trs


def atr(klines, period: int = 14):
    return ema(true_ranges(klines), period)


def s_ema(values, period):
    if not values:
        return []
    if period <= 1:
        return list(values)
    k = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def _s_closed(klines):
    return klines[:-1] if len(klines) > 1 else klines


def _s_closes(klines):
    return [safe_float(r[4]) for r in klines]


def _v10_fmt(x):
    x = safe_float(x)
    if x == 0:
        return "0"
    if x >= 100:
        return f"{x:.2f}"
    if x >= 1:
        return f"{x:.4f}"
    return f"{x:.6f}"


# ============================================================================
#  V11.3 — ULTRA KATMANLAR
# ============================================================================

def adx_hesapla(klines: List[List[Any]], period: int = 14) -> float:
    """ADX: >25 trend, <20 range. Piyasa modu tespiti için."""
    if len(klines) < period * 2 + 2:
        return 0.0
    highs_v = highs(klines); lows_v = lows(klines); closes_v = closes(klines)
    trs, plus_dm, minus_dm = [], [], []
    for i in range(1, len(klines)):
        h, l, pc = highs_v[i], lows_v[i], closes_v[i - 1]
        up_move = h - highs_v[i - 1]
        down_move = lows_v[i - 1] - l
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return 0.0
    # Wilder smoothing
    atr_v = sum(trs[:period]) / period
    pdm = sum(plus_dm[:period]) / period
    mdm = sum(minus_dm[:period]) / period
    dxs = []
    for i in range(period, len(trs)):
        atr_v = (atr_v * (period - 1) + trs[i]) / period
        pdm = (pdm * (period - 1) + plus_dm[i]) / period
        mdm = (mdm * (period - 1) + minus_dm[i]) / period
        if atr_v <= 0:
            continue
        pdi = 100 * pdm / atr_v
        mdi = 100 * mdm / atr_v
        di_sum = pdi + mdi
        dxs.append(0.0 if di_sum == 0 else 100 * abs(pdi - mdi) / di_sum)
    if not dxs:
        return 0.0
    return sum(dxs[-period:]) / min(period, len(dxs[-period:]))


def vwap_hesapla(klines: List[List[Any]], period_hours: int = 24) -> Optional[float]:
    """Rolling VWAP: son N saat. Fiyat VWAP üstünde = alıcılar kontrolde."""
    if not klines:
        return None
    seg = klines[-period_hours:] if len(klines) > period_hours else klines
    if len(seg) < 3:
        return None
    toplam_pv = 0.0
    toplam_v = 0.0
    for r in seg:
        h = safe_float(r[2]); l = safe_float(r[3]); c = safe_float(r[4]); v = safe_float(r[5])
        typical = (h + l + c) / 3.0
        toplam_pv += typical * v
        toplam_v += v
    if toplam_v <= 0:
        return None
    return toplam_pv / toplam_v


def session_belirle() -> Tuple[str, int]:
    """UTC saatine göre piyasa seansı. Döner: (isim, ağırlık_çarpanı)"""
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour
    if SESSION_ASIA_START_UTC <= h < SESSION_ASIA_END_UTC:
        return "Asya", 1
    if SESSION_LONDON_START_UTC <= h < SESSION_LONDON_END_UTC:
        return "Londra", 2
    if SESSION_NY_START_UTC <= h < SESSION_NY_END_UTC:
        return "NewYork", 3
    return "Geçiş", 1


def session_yon_uygun(side: str) -> Tuple[bool, str]:
    """V11.3: Bazı seanslarda bazı yönler riskli."""
    if not SESSION_FILTER_ENABLED:
        return True, "kapalı"
    name, _ = session_belirle()
    if name == "Asya" and SESSION_BLOCK_ASIA_SHORT and side == "SHORT":
        stats["v113_red_session"] = int(stats.get("v113_red_session", 0)) + 1
        return False, "Asya seansında SHORT riskli"
    if name == "Londra" and SESSION_BLOCK_LONDON_LONG and side == "LONG":
        stats["v113_red_session"] = int(stats.get("v113_red_session", 0)) + 1
        return False, "Londra seansında LONG riskli"
    return True, name


def likidasyon_haritasi(symbol: str, klines: List[List[Any]], oi_value: float) -> Dict[str, Any]:
    """
    Tahmini likidasyon haritası.
    OI'nin belirli kaldıraç seviyelerinde yoğunlaştığını varsayarak,
    mevcut fiyatın çevresinde likidasyon kümeleri hesaplar.
    """
    sonuç = {"clusters": [], "top_bid_cluster": 0.0, "top_ask_cluster": 0.0}
    if not LIQ_HEATMAP_ENABLED or oi_value <= 0 or len(klines) < 20:
        return sonuç
    price = safe_float(klines[-1][4])
    if price <= 0:
        return sonuç

    # OI'yi kabaca long/short yarı yarıya kabul et (kaba tahmin)
    oi_per_side = oi_value / 2.0

    # Her kaldıraç seviyesi için likidasyon mesafesi = 1/lev - bakım marjı
    for lev in LIQ_HEATMAP_LEVERAGES:
        liq_distance_pct = (1.0 / lev) * 100.0 - 0.5  # %0.5 bakım marjı çıkarıldı
        if liq_distance_pct <= 0:
            continue
        # Long likidasyonlar: fiyatın altında
        long_liq_price = price * (1 - liq_distance_pct / 100.0)
        # Short likidasyonlar: fiyatın üstünde
        short_liq_price = price * (1 + liq_distance_pct / 100.0)

        # Menzil kontrolü
        if abs(pct_change(price, long_liq_price)) <= LIQ_HEATMAP_DIST_PCT:
            sonuç["clusters"].append({
                "side": "LONG_LIQ", "price": long_liq_price,
                "value": oi_per_side * (1.0 / len(LIQ_HEATMAP_LEVERAGES)),
                "lev": lev,
            })
        if abs(pct_change(price, short_liq_price)) <= LIQ_HEATMAP_DIST_PCT:
            sonuç["clusters"].append({
                "side": "SHORT_LIQ", "price": short_liq_price,
                "value": oi_per_side * (1.0 / len(LIQ_HEATMAP_LEVERAGES)),
                "lev": lev,
            })

    # En büyük alt ve üst küme
    alt = [c for c in sonuç["clusters"] if c["side"] == "LONG_LIQ"]
    ust = [c for c in sonuç["clusters"] if c["side"] == "SHORT_LIQ"]
    if alt:
        sonuç["top_bid_cluster"] = max(alt, key=lambda x: x["value"])["price"]
    if ust:
        sonuç["top_ask_cluster"] = max(ust, key=lambda x: x["value"])["price"]
    return sonuç


def likidasyon_cakismasi(side: str, entry: float, liq_map: Dict[str, Any]) -> Tuple[bool, str]:
    """
    LONG açacaksan, fiyatın HEMEN üstünde büyük SHORT likidasyon kümesi olması İYİ (magnet).
    LONG açacaksan, fiyatın HEMEN altında büyük LONG likidasyon kümesi olması KÖTÜ (kendini yakarsın).
    """
    if not LIQ_HEATMAP_ENABLED:
        return False, "kapalı"
    top_bid = safe_float(liq_map.get("top_bid_cluster"))
    top_ask = safe_float(liq_map.get("top_ask_cluster"))
    if side == "LONG" and top_bid > 0:
        # Altımızda long likidasyon kümesi var mı? Varsa kendimizi riske atıyoruz.
        if top_bid < entry and abs(pct_change(top_bid, entry)) < SABIT_STOP_PCT * 1.5:
            stats["v113_red_liq_conflict"] = int(stats.get("v113_red_liq_conflict", 0)) + 1
            return True, f"LONG likidasyon kümesi çok yakın ({_v10_fmt(top_bid)})"
    if side == "SHORT" and top_ask > 0:
        if top_ask > entry and abs(pct_change(entry, top_ask)) < SABIT_STOP_PCT * 1.5:
            stats["v113_red_liq_conflict"] = int(stats.get("v113_red_liq_conflict", 0)) + 1
            return True, f"SHORT likidasyon kümesi çok yakın ({_v10_fmt(top_ask)})"
    return False, "temiz"


def mtf_confluence(k1h: List[List[Any]], side: str) -> Tuple[bool, str, int]:
    """
    Multi-timeframe confluence:
    15m ve 5m EMA9 > EMA21 mi kontrol et (side yönüne göre).
    Döner: (uygun_mu, not, onay_sayısı)
    """
    if not MTF_CONFLUENCE_ENABLED:
        return True, "kapalı", 0
    # Şu an sadece 1H var, gerçek MTF için 15m ve 5m çekilir
    return True, "ok", 0


async def mtf_confluence_async(symbol: str, side: str) -> Tuple[bool, str, int]:
    if not MTF_CONFLUENCE_ENABLED:
        return True, "kapalı", 0
    onay = 0
    detay = []
    for tf in MTF_REQUIRED_TFS:
        tf = tf.strip()
        if not tf:
            continue
        k = await get_klines(symbol, tf, 60)
        if len(k) < 30:
            continue
        c = closes(_s_closed(k))
        if len(c) < 22:
            continue
        e9 = s_ema(c, 9)[-1]
        e21 = s_ema(c, 21)[-1]
        if side == "LONG" and e9 > e21:
            onay += 1
            detay.append(f"{tf}✅")
        elif side == "SHORT" and e9 < e21:
            onay += 1
            detay.append(f"{tf}✅")
        else:
            detay.append(f"{tf}▫️")
    if onay < MTF_MIN_AGREE:
        stats["v113_red_mtf"] = int(stats.get("v113_red_mtf", 0)) + 1
        return False, f"MTF onay yok ({onay}/{len(MTF_REQUIRED_TFS)})", onay
    return True, " ".join(detay), onay


def korelasyon_grubu(symbol: str) -> str:
    """Basit korelasyon grubu tahmini."""
    base = _base_of(symbol)
    if base in ("BTC", "ETH"):
        return "majors"
    if base in ("SOL", "AVAX", "NEAR", "SUI", "APT", "SEI", "TIA", "DOT", "ATOM", "INJ"):
        return "L1"
    if base in ("ARB", "OP", "MATIC", "STRK", "ZK", "MANTA"):
        return "L2"
    if base in ("FET", "RNDR", "TAO", "WLD", "AGIX"):
        return "ai"
    if base in ("DOGE", "SHIB", "PEPE", "WIF", "BONK"):
        return "memes"
    return "diğer"


def korelasyon_kilidi(symbol: str, side: str) -> Tuple[bool, str]:
    """Aynı yönde çok fazla korele pozisyon açılmasını engelle."""
    if not CORRELATION_GUARD_ENABLED:
        return False, "kapalı"
    mp = _v10_mem()
    grup = korelasyon_grubu(symbol)
    ayni = [p for p in mp.get("open", []) if korelasyon_grubu(p.get("symbol", "")) == grup
            and p.get("side") == side]
    if len(ayni) >= CORRELATION_MAX_SAME_DIR:
        stats["v113_red_correlation"] = int(stats.get("v113_red_correlation", 0)) + 1
        return True, f"{grup} grubunda {len(ayni)} açık {side} pozisyon"
    return False, "ok"


def adaptif_pozisyon_carpani(skor: float, volatilite: str, session_weight: int) -> float:
    """Pozisyon boyutu çarpanı: skor yüksekse büyüt, vol yüksekse küçült, aktif seansta büyüt."""
    if not ADAPTIVE_SIZING:
        return 1.0
    # Skor bazlı: 70→0.7, 90→1.3
    skor_mult = clamp(0.5 + (skor - 50) / 40 * 0.8, 0.5, 1.3)
    # Volatilite bazlı
    vol_mult = 0.7 if volatilite == "HIGH" else (1.2 if volatilite == "LOW" else 1.0)
    # Session bazlı
    ses_mult = 1.0 + (session_weight - 1) * 0.1
    return round(skor_mult * vol_mult * ses_mult, 3)


def volume_weighted_momentum(klines: List[List[Any]], side: str, window: int = 10) -> Tuple[bool, float]:
    """Hacim ağırlıklı momentum. Yüksek hacimli mumlar yönü belirler."""
    if not VWM_ENABLED or len(klines) < window + 1:
        return True, 0.0
    seg = klines[-window:]
    vwm = 0.0
    for i, r in enumerate(seg):
        o = safe_float(r[1]); c = safe_float(r[4]); v = safe_float(r[5])
        vwm += (1 if c >= o else -1) * v
    top_vol = sum(safe_float(r[5]) for r in seg)
    if top_vol > 0:
        vwm_norm = vwm / top_vol
    else:
        vwm_norm = 0.0
    if side == "LONG" and vwm_norm < -0.3:
        return False, vwm_norm
    if side == "SHORT" and vwm_norm > 0.3:
        return False, vwm_norm
    return True, vwm_norm


def v10_market_structure(k):
    try:
        _a = atr(k, V10_ATR_PERIOD)[-1] if V107_PIVOT_ATR > 0 else 0.0
    except Exception:
        _a = 0.0
    H, L, n = highs(k), lows(k), len(k)
    min_fark = _a * V107_PIVOT_ATR if (_a and _a > 0) else 0.0
    sw = []
    for i in range(V10_SWING_LEFT, n - V10_SWING_RIGHT):
        wh = H[i - V10_SWING_LEFT:i + V10_SWING_RIGHT + 1]
        wl = L[i - V10_SWING_LEFT:i + V10_SWING_RIGHT + 1]
        if H[i] == max(wh) and wh.count(H[i]) == 1:
            sw.append(("H", i, H[i]))
        elif L[i] == min(wl) and wl.count(L[i]) == 1:
            sw.append(("L", i, L[i]))
    # Mikro pivot eleme
    temiz = []
    for kind, idx, price in sw:
        if not temiz:
            temiz.append((kind, idx, price)); continue
        ok, oi, op = temiz[-1]
        if kind == ok:
            if (kind == "H" and price >= op) or (kind == "L" and price <= op):
                temiz[-1] = (kind, idx, price)
            continue
        if min_fark > 0 and abs(price - op) < min_fark:
            continue
        temiz.append((kind, idx, price))
    res = {"trend": "RANGE", "last_sh": 0.0, "last_sh_idx": -1,
           "last_sl": 0.0, "last_sl_idx": -1, "prev_sh": 0.0, "prev_sl": 0.0,
           "event": None, "event_side": None, "event_level": 0.0, "event_idx": -1,
           "range_break": False, "atr": _a}
    hs = [t for t in temiz if t[0] == "H"]
    ls = [t for t in temiz if t[0] == "L"]
    if hs:
        res["last_sh"], res["last_sh_idx"] = hs[-1][2], hs[-1][1]
        if len(hs) >= 2:
            res["prev_sh"] = hs[-2][2]
            res["hh"] = hs[-1][2] > hs[-2][2]
            res["lh"] = hs[-1][2] < hs[-2][2]
    if ls:
        res["last_sl"], res["last_sl_idx"] = ls[-1][2], ls[-1][1]
        if len(ls) >= 2:
            res["prev_sl"] = ls[-2][2]
            res["hl"] = ls[-1][2] > ls[-2][2]
            res["ll"] = ls[-1][2] < ls[-2][2]
    if res.get("hh") and res.get("hl"):
        res["trend"] = "UP"
    elif res.get("lh") and res.get("ll"):
        res["trend"] = "DOWN"
    lc = closes(k)[-1]
    if res["last_sh"] > 0 and lc > res["last_sh"]:
        res["event"] = "CHoCH" if res["trend"] == "DOWN" else "BOS"
        res["event_side"] = "UP"
        res["event_level"] = res["last_sh"]
        res["event_idx"] = res["last_sh_idx"]
        res["range_break"] = (res["trend"] == "RANGE")
    elif res["last_sl"] > 0 and lc < res["last_sl"]:
        res["event"] = "CHoCH" if res["trend"] == "UP" else "BOS"
        res["event_side"] = "DOWN"
        res["event_level"] = res["last_sl"]
        res["event_idx"] = res["last_sl_idx"]
        res["range_break"] = (res["trend"] == "RANGE")
    return res


def v10_structure_allows(side, ms):
    ev, es = ms.get("event"), ms.get("event_side")
    rb = bool(ms.get("range_break"))
    if ev == "BOS":
        aciklama = "RANGE kırılımı — devam edecek trend YOK" if rb else "devam"
    else:
        aciklama = "dönüş"
    if side == "LONG" and es == "UP" and ev in ("BOS", "CHoCH"):
        return True, f"Boğa {ev} ({aciklama})"
    if side == "SHORT" and es == "DOWN" and ev in ("BOS", "CHoCH"):
        return True, f"Ayı {ev} ({aciklama})"
    return False, ""


def v10_fomo_block(side, k):
    c = closes(k)
    if len(c) < V10_FOMO_LOOKBACK + 1:
        return False, 0.0
    mv = (c[-1] - c[-1 - V10_FOMO_LOOKBACK]) / c[-1 - V10_FOMO_LOOKBACK] * 100.0
    if side == "LONG" and mv > V10_FOMO_MAX_MOVE:
        return True, mv
    if side == "SHORT" and mv < -V10_FOMO_MAX_MOVE:
        return True, mv
    return False, mv


def v10_pullback(side, k, ms):
    lvl = safe_float(ms.get("event_level"))
    if lvl <= 0 or ms.get("event_side") not in ("UP", "DOWN"):
        return False, ""
    ev_idx = int(ms.get("event_idx", -1))
    n = len(k)
    seg = k[max(ev_idx + 1, n - V10_PULLBACK_WAIT):]
    if len(seg) < 2:
        return False, ""
    tol = V10_PULLBACK_TOL / 100.0
    last = k[-1]
    lc, ll, lh, lo = safe_float(last[4]), safe_float(last[3]), safe_float(last[2]), safe_float(last[1])
    if side == "LONG":
        touched = any(safe_float(r[3]) <= lvl * (1 + tol) for r in seg)
        if (touched and lc > lvl and lc > lo) or (lc > lvl and ll <= lvl * (1 + tol)):
            return True, f"retest @ {lvl:.6g}"
    else:
        touched = any(safe_float(r[2]) >= lvl * (1 - tol) for r in seg)
        if (touched and lc < lvl and lc < lo) or (lc < lvl and lh >= lvl * (1 - tol)):
            return True, f"retest @ {lvl:.6g}"
    return False, ""


def v10_detect_order_block(side, k):
    n = len(k)
    seg = k[max(0, n - V10_OB_LOOKBACK):]
    zone = None
    for r in reversed(seg):
        o, c = safe_float(r[1]), safe_float(r[4])
        if side == "LONG" and c < o:
            zone = (safe_float(r[3]), safe_float(r[2])); break
        if side == "SHORT" and c > o:
            zone = (safe_float(r[3]), safe_float(r[2])); break
    if not zone:
        return 0.0
    lo, hi = zone
    price = safe_float(k[-1][4])
    tol = (hi - lo) * 0.5 if hi > lo else price * 0.003
    if side == "LONG":
        return 1.0 if lo - tol <= price <= hi + tol else 0.3 if price > hi else 0.0
    return 1.0 if lo - tol <= price <= hi + tol else 0.3 if price < lo else 0.0


def v10_detect_fvg(side, k):
    n = len(k)
    best = False
    for i in range(max(1, n - V10_FVG_LOOKBACK), n - 1):
        if i + 1 >= n:
            break
        if side == "LONG":
            h0, l2 = safe_float(k[i - 1][2]), safe_float(k[i + 1][3])
            if h0 < l2 and not any(safe_float(k[j][3]) <= h0 for j in range(i + 2, n)):
                best = True
        else:
            l0, h2 = safe_float(k[i - 1][3]), safe_float(k[i + 1][2])
            if l0 > h2 and not any(safe_float(k[j][2]) >= l0 for j in range(i + 2, n)):
                best = True
    return 1.0 if best else 0.0


def v10_volume_profile(k):
    seg = k[-V10_VP_LOOKBACK:] if len(k) > V10_VP_LOOKBACK else k
    H, L = highs(seg), lows(seg)
    lo, hi = min(L), max(H)
    if hi <= lo:
        return None
    w = (hi - lo) / V10_VP_BINS
    prof = [0.0] * V10_VP_BINS
    for r in seg:
        mid = (safe_float(r[2]) + safe_float(r[3])) / 2
        v = safe_float(r[5])
        idx = min(V10_VP_BINS - 1, max(0, int((mid - lo) / w)))
        prof[idx] += v
    poc_idx = max(range(V10_VP_BINS), key=lambda i: prof[i])
    poc = lo + (poc_idx + 0.5) * w
    return {"poc": poc}


def v10_vp_score(side, price, vp):
    if not vp:
        return 0.5
    if side == "LONG":
        return 1.0 if price > vp["poc"] else 0.5
    return 1.0 if price < vp["poc"] else 0.5


def v10_cvd_proxy(k):
    seg = k[-V10_CVD_WINDOW:]
    cvd = 0.0
    for r in seg:
        o, c, v = safe_float(r[1]), safe_float(r[4]), safe_float(r[5])
        cvd += v if c >= o else -v
    return cvd


def v109_coin_1h_yon(k1h):
    try:
        c = closes(_s_closed(k1h))
        if len(c) < V109_COIN_EMA_SLOW + 2:
            return "FLAT"
        f = ema(c, V109_COIN_EMA_FAST)[-1]
        y = ema(c, V109_COIN_EMA_SLOW)[-1]
        if f > y:
            return "UP"
        if f < y:
            return "DOWN"
    except Exception:
        pass
    return "FLAT"


def v107_oi_skor(side, oi_pct, fiyat_pct):
    if abs(oi_pct) < 0.05:
        return 0.2, "OI yatay"
    oi_up = oi_pct > 0
    fiyat_up = fiyat_pct >= 0
    if oi_up and fiyat_up:
        return (1.0, "yeni long girişi") if side == "LONG" else (0.3, "yeni long girişi — ters")
    if oi_up and not fiyat_up:
        return (1.0, "yeni short girişi") if side == "SHORT" else (0.3, "yeni short girişi — ters")
    if (not oi_up) and fiyat_up:
        return (0.5, "short kapanışı — zayıf ralli") if side == "LONG" else (0.4, "short kapanışı")
    return (0.5, "long likidasyonu — zayıf düşüş") if side == "SHORT" else (0.4, "long likidasyonu")


def v10_quality_score(side, k, ms, ext):
    p, bayrak = {}, {}
    ok, _ = v10_structure_allows(side, ms)
    s = 18.0 if ok else 0.0
    if ok and ms.get("event") == "CHoCH":
        s *= 0.85
    p["structure"] = s

    vols = [safe_float(r[5]) for r in k[-21:-1]]
    av = sum(vols) / len(vols) if vols else 0.0
    lv = safe_float(k[-1][5])
    p["volume"] = 2.0 * min(1.0, max(0.0, (lv / av - 0.8) / 0.7)) if av > 0 else 0.0
    bayrak["volume"] = bool(av > 0 and lv > av)

    r = rsi(closes(k))[-1]
    if side == "LONG":
        p["rsi"] = 7.0 * (1.0 if 45 <= r <= 65 else 0.5 if 35 <= r <= 75 else 0.1)
    else:
        p["rsi"] = 7.0 * (1.0 if 35 <= r <= 55 else 0.5 if 25 <= r <= 65 else 0.1)

    oi = safe_float(ext.get("oi_change_pct"))
    son = k[-1]
    fiyat_pct = 0.0
    _o = safe_float(son[1])
    if _o > 0:
        fiyat_pct = (safe_float(son[4]) - _o) / _o * 100.0
    oi_carpan, oi_not = v107_oi_skor(side, oi, fiyat_pct)
    p["oi"] = 9.0 * oi_carpan
    bayrak["oi"] = oi_carpan >= 1.0
    ext["oi_yorum"] = oi_not

    fr = safe_float(ext.get("funding"))
    if side == "LONG":
        p["funding"] = 7.0 * (0.2 if fr > 0.0008 else 1.0 if fr < 0 else 0.7)
    else:
        p["funding"] = 7.0 * (0.2 if fr < -0.0008 else 1.0 if fr > 0 else 0.7)

    btc4h = str(ext.get("btc_dir", "FLAT")).upper()
    btc1h = str(ext.get("btc_dir_1h", "FLAT")).upper()
    if side == "LONG":
        btc_mult = 1.0 if (btc4h == "UP" and btc1h == "UP") else 0.7 if (btc4h == "UP" or btc1h == "UP") else 0.15 if (btc4h == "DOWN" and btc1h == "DOWN") else 0.5
    else:
        btc_mult = 1.0 if (btc4h == "DOWN" and btc1h == "DOWN") else 0.7 if (btc4h == "DOWN" or btc1h == "DOWN") else 0.15 if (btc4h == "UP" and btc1h == "UP") else 0.5
    p["btc"] = 14.0 * btc_mult

    ob = ext.get("orderbook") or {}
    imb = safe_float(ob.get("imbalance"))
    if side == "LONG":
        obs = (0.6 if imb > 0.15 else 0.3 if imb > 0 else 0.0) + (0.4 if ob.get("bid_wall") else 0.0)
    else:
        obs = (0.6 if imb < -0.15 else 0.3 if imb < 0 else 0.0) + (0.4 if ob.get("ask_wall") else 0.0)
    p["orderbook"] = 7.0 * min(1.0, obs)
    bayrak["orderbook"] = obs > 0.0

    _ob_ham = v10_detect_order_block(side, k)
    p["order_block"] = 11.0 * _ob_ham
    bayrak["order_block"] = _ob_ham >= 1.0

    _fvg_ham = v10_detect_fvg(side, k)
    p["fvg"] = 8.0 * _fvg_ham
    bayrak["fvg"] = _fvg_ham > 0.0

    _vp_ham = v10_vp_score(side, safe_float(k[-1][4]), v10_volume_profile(k))
    p["volume_profile"] = 5.0 * _vp_ham
    bayrak["volume_profile"] = _vp_ham >= 1.0

    cv = v10_cvd_proxy(k)
    _cvd_uyum = (cv > 0 and side == "LONG") or (cv < 0 and side == "SHORT")
    p["cvd"] = 5.0 * (1.0 if _cvd_uyum else 0.2)
    bayrak["cvd"] = bool(_cvd_uyum)

    sweep_skor = 0.0
    if side == "LONG" and ms.get("last_sl", 0) > 0:
        son_sl = ms.get("last_sl")
        for r_ in k[-6:]:
            if safe_float(r_[3]) < son_sl and safe_float(r_[4]) > son_sl:
                sweep_skor = 1.0; break
    elif side == "SHORT" and ms.get("last_sh", 0) > 0:
        son_sh = ms.get("last_sh")
        for r_ in k[-6:]:
            if safe_float(r_[2]) > son_sh and safe_float(r_[4]) < son_sh:
                sweep_skor = 1.0; break
    p["sweep"] = 7.0 * sweep_skor
    bayrak["sweep"] = sweep_skor > 0.0

    return (round(sum(p.values()), 1),
            {kk: round(vv, 1) for kk, vv in p.items()},
            round(r, 1), bayrak)


def v10_targets(side, entry):
    stop_pct = SABIT_STOP_PCT / 100.0
    stop = entry * (1 - stop_pct) if side == "LONG" else entry * (1 + stop_pct)
    risk = abs(entry - stop)
    if side == "LONG":
        tp1 = entry + risk * TP1_RR; tp2 = entry + risk * TP2_RR
        tp3 = entry + risk * TP3_RR; tp4 = entry + risk * TP4_RR
    else:
        tp1 = entry - risk * TP1_RR; tp2 = entry - risk * TP2_RR
        tp3 = entry - risk * TP3_RR; tp4 = entry - risk * TP4_RR
    return {"stop": stop, "stop_pct": round(SABIT_STOP_PCT, 2), "risk": risk,
            "tp1": tp1, "tp2": tp2, "tp3": tp3, "tp4": tp4,
            "tp1_rr": TP1_RR, "tp2_rr": TP2_RR, "tp3_rr": TP3_RR, "tp4_rr": TP4_RR}


async def v10_fetch_orderbook(symbol):
    blank = {"imbalance": 0.0, "bid_wall": False, "ask_wall": False, "mid": 0.0, "bid": 0.0, "ask": 0.0}
    if not V10_USE_ORDERBOOK:
        return blank
    try:
        data = await _okx_get_async("/api/v5/market/books", {"instId": symbol, "sz": V10_OB_DEPTH})
        if not data:
            return blank
        book = data[0]
        bsz = [safe_float(x[1]) for x in book.get("bids", [])[:V10_OB_DEPTH]]
        asz = [safe_float(x[1]) for x in book.get("asks", [])[:V10_OB_DEPTH]]
        bids, asks = sum(bsz), sum(asz)
        tot = bids + asks
        imb = (bids - asks) / tot if tot > 0 else 0.0
        bmean = bids / len(bsz) if bsz else 0
        amean = asks / len(asz) if asz else 0
        try:
            bid = safe_float(book.get("bids", [[0]])[0][0])
            ask = safe_float(book.get("asks", [[0]])[0][0])
        except Exception:
            bid = ask = 0.0
        mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else 0.0
        return {"imbalance": imb,
                "bid_wall": (max(bsz) > bmean * V10_OB_WALL_MULT) if bsz and bmean > 0 else False,
                "ask_wall": (max(asz) > amean * V10_OB_WALL_MULT) if asz and amean > 0 else False,
                "mid": mid, "bid": bid, "ask": ask}
    except Exception:
        return blank


async def v112_spoof_tespit(symbol: str) -> Tuple[bool, str]:
    if not SPOOF_GUARD_ENABLED or not V10_USE_ORDERBOOK:
        return False, "kapalı"
    try:
        snapshots = []
        for _ in range(SPOOF_CHECK_COUNT):
            data = await _okx_get_async("/api/v5/market/books", {"instId": symbol, "sz": 5})
            if not data:
                return False, "veri yok"
            book = data[0]
            top_bids = [(safe_float(b[0]), safe_float(b[1])) for b in book.get("bids", [])[:3]]
            top_asks = [(safe_float(a[0]), safe_float(a[1])) for a in book.get("asks", [])[:3]]
            snapshots.append({"bids": top_bids, "asks": top_asks})
            await asyncio.sleep(SPOOF_CHECK_INTERVAL)
        if len(snapshots) < 2:
            return False, "yetersiz"
        ilk, son = snapshots[0], snapshots[-1]
        degisim = toplam = 0
        for i in range(min(3, len(ilk["bids"]))):
            toplam += 1
            if ilk["bids"][i][0] != son["bids"][i][0]:
                degisim += 1
        for i in range(min(3, len(ilk["asks"]))):
            toplam += 1
            if ilk["asks"][i][0] != son["asks"][i][0]:
                degisim += 1
        if toplam > 0 and (degisim / toplam) >= SPOOF_CHANGE_THRESHOLD:
            return True, f"spoofing şüphesi ({degisim}/{toplam})"
        return False, "stabil"
    except Exception:
        return False, "hata"


def v112_wash_tespit(symbol: str, klines) -> Tuple[bool, str]:
    if not WASH_GUARD_ENABLED or len(klines) < 30:
        return False, "kapalı"
    try:
        vols = [safe_float(r[5]) for r in klines[-30:-1]]
        ort_vol = sum(vols) / len(vols) if vols else 0.0
        son_vol = safe_float(klines[-1][5])
        if ort_vol <= 0 or son_vol < ort_vol * WASH_VOL_MULTIPLIER:
            return False, "normal"
        fiyat_degisim = abs(pct_change(safe_float(klines[-11][4]), safe_float(klines[-1][4])))
        if fiyat_degisim < WASH_MAX_PRICE_MOVE:
            return True, f"wash trading (hacim {son_vol/ort_vol:.1f}x, fiyat %{fiyat_degisim:.2f})"
        return False, "normal"
    except Exception:
        return False, "hata"


def v112_pump_dump_tespit(symbol, klines, tickers24) -> Tuple[bool, str]:
    if not PUMP_DUMP_GUARD_ENABLED or len(klines) < 13:
        return False, "kapalı"
    try:
        hareket = abs(pct_change(safe_float(klines[-13][4]), safe_float(klines[-1][4])))
        if hareket < PUMP_DUMP_MAX_1H_MOVE:
            return False, "normal"
        vol_24h = quote_volume_from_ticker(tickers24.get(symbol, {}))
        if vol_24h >= PUMP_DUMP_MIN_VOL:
            return False, "likidite yeterli"
        return True, f"pump/dump (1h %{hareket:.1f}, hacim {vol_24h/1e6:.1f}M)"
    except Exception:
        return False, "hata"


def v112_insider_tespit(symbol, klines) -> Tuple[bool, str]:
    if not INSIDER_GUARD_ENABLED or len(klines) < 30:
        return False, ""
    try:
        vols = [safe_float(r[5]) for r in klines[-30:-3]]
        ort_vol = sum(vols) / len(vols) if vols else 0.0
        son_3_vol = sum(safe_float(r[5]) for r in klines[-3:]) / 3.0
        if ort_vol <= 0 or son_3_vol < ort_vol * INSIDER_QUIET_VOL_MULT:
            return False, ""
        fiyat_degisim = abs(pct_change(safe_float(klines[-4][4]), safe_float(klines[-1][4])))
        if fiyat_degisim < INSIDER_PRICE_MOVE_MAX:
            return True, f"sessiz birikim ({son_3_vol/ort_vol:.1f}x hacim, %{fiyat_degisim:.2f})"
        return False, ""
    except Exception:
        return False, ""


def v112_stop_hunt_tespit(klines) -> Tuple[bool, str]:
    if not STOP_HUNT_GUARD_ENABLED or len(klines) < 2:
        return False, ""
    try:
        k = klines[-1]
        o, h, l, c = safe_float(k[1]), safe_float(k[2]), safe_float(k[3]), safe_float(k[4])
        rng = h - l
        if rng <= 0:
            return False, ""
        alt_fitil = min(o, c) - l
        ust_fitil = h - max(o, c)
        if alt_fitil / rng >= STOP_HUNT_WICK_RATIO and c > o:
            return True, f"boğa stop avı (%{alt_fitil/rng*100:.0f} alt fitil)"
        if ust_fitil / rng >= STOP_HUNT_WICK_RATIO and c < o:
            return True, f"ayı stop avı (%{ust_fitil/rng*100:.0f} üst fitil)"
        return False, ""
    except Exception:
        return False, ""


def v107_canli_giris(k1h, ob, referans):
    if not V107_CANLI_GIRIS:
        return referans, "kapanis"
    ref = safe_float(referans)
    mid = safe_float((ob or {}).get("mid"))
    if mid > 0 and ref > 0 and abs(mid - ref) / ref <= 0.10:
        return mid, "orderbook"
    try:
        forming = safe_float(k1h[-1][4])
    except Exception:
        forming = 0.0
    if forming > 0 and ref > 0 and abs(forming - ref) / ref <= 0.30:
        return forming, "canli mum"
    return ref, "kapanis"


def v10_structure_gate(symbol, k1h, k4h, allowed_side=None):
    k = _s_closed(k1h)
    if len(k) < 40:
        return None
    ms = v10_market_structure(k)
    trend4 = "FLAT"
    if V10_USE_4H_FILTER and k4h and len(k4h) >= 52:
        c4 = closes(_s_closed(k4h))
        e = ema(c4, min(50, len(c4) - 1))
        trend4 = "UP" if c4[-1] > e[-1] else "DOWN"
    if V107_RANGE_ENGELLE and ms.get("range_break"):
        stats["v107_red_range"] = int(stats.get("v107_red_range", 0)) + 1
        return None
    for side in ("LONG", "SHORT"):
        ok, why = v10_structure_allows(side, ms)
        if not ok:
            continue
        if allowed_side and side != allowed_side:
            stats["v10_red_btc_ters"] = int(stats.get("v10_red_btc_ters", 0)) + 1
            continue
        if V10_USE_4H_FILTER and trend4 != "FLAT":
            if side == "LONG" and trend4 != "UP":
                continue
            if side == "SHORT" and trend4 != "DOWN":
                continue
        blk, mv = v10_fomo_block(side, k)
        if blk:
            stats["v11_red_fomo"] = int(stats.get("v11_red_fomo", 0)) + 1
            continue
        if V109_COIN_1H_UYUM:
            _cy = v109_coin_1h_yon(k1h)
            if (side == "LONG" and _cy != "UP") or (side == "SHORT" and _cy != "DOWN"):
                stats["v11_red_coin_ema"] = int(stats.get("v11_red_coin_ema", 0)) + 1
                continue
        pb, note = v10_pullback(side, k, ms)
        if not pb:
            continue
        return {"side": side, "ms": ms, "why": why, "trend4": trend4,
                "fomo": round(mv, 2), "pullback": note, "k": k,
                "coin_1h_ema": v109_coin_1h_yon(k1h)}
    return None


async def analyze_v10_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    symbol = normalize_symbol(symbol)

    # BTC trend filtresi
    allowed_side = None
    btc_1h = btc_4h = "FLAT"
    if V106_BTC_TREND_FILTER:
        bt = await v106_btc_trend()
        btc_1h = bt.get("dir_1h", "FLAT")
        btc_4h = bt.get("dir_4h", "FLAT")
        if not bt.get("ok"):
            stats["v10_red_btc_veri"] = int(stats.get("v10_red_btc_veri", 0)) + 1
            return None
        allowed_side = bt.get("allow")
        if not allowed_side:
            stats["v10_red_btc_karisik"] = int(stats.get("v10_red_btc_karisik", 0)) + 1
            return None
    else:
        bt = await v106_btc_trend()
        btc_1h = bt.get("dir_1h", "FLAT")
        btc_4h = bt.get("dir_4h", "FLAT")

    k1h = await get_klines(symbol, "1H", V10_KLINE_LIMIT)
    if len(k1h) < 40:
        stats["v10_red_veri"] = int(stats.get("v10_red_veri", 0)) + 1
        return None

    # V11.2 savunmaları
    wash_hit, wash_note = v112_wash_tespit(symbol, k1h)
    if wash_hit:
        stats["v112_red_wash"] = int(stats.get("v112_red_wash", 0)) + 1
        return None

    tickers24 = await get_24h_tickers()
    pump_hit, pump_note = v112_pump_dump_tespit(symbol, k1h, tickers24)
    if pump_hit:
        stats["v112_red_pump_dump"] = int(stats.get("v112_red_pump_dump", 0)) + 1
        return None

    k4h = await get_klines(symbol, "4H", 120, ttl=180) if V10_USE_4H_FILTER else None
    gate = v10_structure_gate(symbol, k1h, k4h, allowed_side)
    if not gate:
        stats["v10_red_yapi"] = int(stats.get("v10_red_yapi", 0)) + 1
        return None

    side = gate["side"]
    k = gate["k"]

    # V11.3 yeni katmanlar
    # ADX
    adx_v = adx_hesapla(k, ADX_PERIOD) if ADX_ENABLED else 0.0
    piyasa_modu = "TREND" if adx_v >= ADX_TREND_THRESHOLD else "RANGE" if adx_v < ADX_RANGE_THRESHOLD else "GEÇİŞ"

    # Session
    session_ok, session_note = session_yon_uygun(side)
    if not session_ok:
        return None
    session_name, session_weight = session_belirle()

    # VWAP
    vwap_v = vwap_hesapla(k, VWAP_PERIOD_HOURS) if VWAP_ENABLED else None
    if VWAP_ENABLED and vwap_v:
        entry_tmp = safe_float(k[-1][4])
        if side == "LONG" and entry_tmp < vwap_v:
            stats["v113_red_vwap"] = int(stats.get("v113_red_vwap", 0)) + 1
            return None
        if side == "SHORT" and entry_tmp > vwap_v:
            stats["v113_red_vwap"] = int(stats.get("v113_red_vwap", 0)) + 1
            return None

    # MTF confluence
    mtf_ok, mtf_note, mtf_count = await mtf_confluence_async(symbol, side)
    if not mtf_ok:
        return None

    # VWM (hacim ağırlıklı momentum)
    vwm_ok, vwm_val = volume_weighted_momentum(k, side)
    if not vwm_ok:
        return None

    oi = await fetch_okx_oi_change(symbol, 12)
    funding = await fetch_okx_funding_rate(symbol)
    ob = await v10_fetch_orderbook(symbol)

    # Spoofing
    spoof_hit, spoof_note = await v112_spoof_tespit(symbol)
    if spoof_hit:
        stats["v112_red_spoofing"] = int(stats.get("v112_red_spoofing", 0)) + 1
        return None

    ext = {"oi_change_pct": oi if oi is not None else 0.0,
           "funding": funding, "btc_dir": btc_4h, "btc_dir_1h": btc_1h,
           "orderbook": ob}

    score, parts, r, bayrak = v10_quality_score(side, k, gate["ms"], ext)

    if (side == "LONG" and r > V10_RSI_LONG_MAX) or (side == "SHORT" and r < V10_RSI_SHORT_MIN):
        stats["v10_red_rsi"] = int(stats.get("v10_red_rsi", 0)) + 1
        return None

    oi_yorum = ext.get("oi_yorum", "")
    if side == "LONG" and "short kapanışı" in oi_yorum:
        stats["v11_red_oi_zayif"] = int(stats.get("v11_red_oi_zayif", 0)) + 1
        return None
    if side == "SHORT" and "long likidasyonu" in oi_yorum:
        stats["v11_red_oi_zayif"] = int(stats.get("v11_red_oi_zayif", 0)) + 1
        return None

    entry_ref = closes(k)[-1]
    entry, giris_kaynak = v107_canli_giris(k1h, ob, entry_ref)
    kayma = (abs(entry - entry_ref) / entry_ref * 100.0) if entry_ref > 0 else 0.0
    if V107_MAX_GIRIS_KAYMA > 0 and kayma > V107_MAX_GIRIS_KAYMA:
        stats["v107_red_kayma"] = int(stats.get("v107_red_kayma", 0)) + 1
        return None

    # Likidasyon haritası
    oi_value = await fetch_okx_open_interest_value(symbol) if LIQ_HEATMAP_ENABLED else None
    liq_map = likidasyon_haritasi(symbol, k, oi_value or 0.0) if oi_value else {}
    liq_conflict, liq_note = likidasyon_cakismasi(side, entry, liq_map)
    if liq_conflict and LIQ_HEATMAP_BLOCK_CONFLICT:
        return None

    # Korelasyon koruması
    kor_block, kor_note = korelasyon_kilidi(symbol, side)
    if kor_block:
        return None

    # Insider / Stop-hunt (bilgi amaçlı)
    insider_hit, insider_note = v112_insider_tespit(symbol, k1h)
    if insider_hit:
        stats["v112_red_insider"] = int(stats.get("v112_red_insider", 0)) + 1
    stop_hunt_hit, stop_hunt_note = v112_stop_hunt_tespit(k1h)
    if stop_hunt_hit:
        stats["v112_hit_stop_hunt"] = int(stats.get("v112_hit_stop_hunt", 0)) + 1

    tgt = v10_targets(side, entry)

    return {"symbol": symbol, "direction": side, "entry": entry, "strategy": "V11.3_ULTRA",
            "entry_ref": entry_ref, "entry_kaynak": giris_kaynak, "entry_kayma_pct": round(kayma, 3),
            "event": gate["ms"]["event"], "structure": gate["why"],
            "range_break": bool(gate["ms"].get("range_break")),
            "trend_1h": gate["ms"]["trend"], "trend_4h": gate["trend4"],
            "fomo_move_pct": gate["fomo"], "pullback": gate["pullback"],
            "score": score, "score_parts": parts, "bayrak": bayrak, "rsi": r,
            "candle_ts": str(k[-1][0]), "oi_change_pct": ext["oi_change_pct"],
            "oi_yorum": ext.get("oi_yorum", ""),
            "coin_1h_ema": gate.get("coin_1h_ema", "-"),
            "funding": funding, "ob_imbalance": ob.get("imbalance", 0),
            "btc_4h": btc_4h, "btc_1h": btc_1h,
            "trend_uyum": True,
            "spoof_guard": spoof_note,
            "wash_guard": wash_note,
            "pump_guard": pump_note,
            "insider_uyari": insider_note if insider_hit else "",
            "stop_hunt": stop_hunt_note if stop_hunt_hit else "",
            "adx": round(adx_v, 2),
            "piyasa_modu": piyasa_modu,
            "session_name": session_name,
            "session_weight": session_weight,
            "vwap": round(vwap_v, 8) if vwap_v else 0.0,
            "mtf_note": mtf_note,
            "mtf_count": mtf_count,
            "vwm": round(vwm_val, 3),
            "liq_map": liq_map,
            "liq_note": liq_note,
            **tgt}


def build_v10_message(sig):
    b = sig.get("bayrak") or {}
    p = sig["score_parts"]
    tag = lambda key, lbl: f"{lbl}{'✅' if b.get(key, p.get(key, 0) > 0) else '▫️'}"
    conf = " ".join([tag("order_block", "OB"), tag("fvg", "FVG"), tag("volume_profile", "VP"),
                     tag("cvd", "CVD"), tag("sweep", "Sweep"), tag("orderbook", "OBflow")])
    fund = safe_float(sig.get("funding"))
    trend_line = "Trend Uyumu: BTC ile AYNI YÖN ✅\n"
    _kay = safe_float(sig.get("entry_kayma_pct"))
    kayma_mark = f" (mum kapanışından %{_kay:+.2f})" if abs(_kay) >= 0.05 else ""

    # V11.3 ek bilgiler
    savunma_lines = ["🛡 Spoof✅ Wash✅ Pump✅"]
    if sig.get("insider_uyari"):
        savunma_lines.append(f"⚠️ Insider: {sig['insider_uyari']}")
    if sig.get("stop_hunt"):
        savunma_lines.append(f"🎯 {sig['stop_hunt']}")
    vwap_line = f"📊 VWAP: {_v10_fmt(sig.get('vwap', 0))}" if sig.get('vwap') else ""
    adx_line = f"📈 ADX: {sig.get('adx', 0)} ({sig.get('piyasa_modu', '-')})" if sig.get('adx') else ""
    session_line = f"🕐 Seans: {sig.get('session_name', '-')}"
    mtf_line = f"🔀 MTF: {sig.get('mtf_note', '-')}"
    vwm_line = f"📉 VWM: {sig.get('vwm', 0):+.2f}"
    liq_line = ""
    if sig.get("liq_note") and sig.get("liq_note") != "temiz":
        liq_line = f"💥 Likidite: {sig['liq_note']}"

    return (f"{trend_line}"
            f"🎯 {VERSION_NAME}\n🆕 V11.3 ULTRA | {sig['direction']} | {sig['symbol']}\n"
            f"Yapı: {sig['structure']} | 1H:{sig['trend_1h']} 4H:{sig['trend_4h']}\n"
            f"BTC: 1H:{sig.get('btc_1h','-')} 4H:{sig.get('btc_4h','-')}"
            + (f" | Coin 1H EMA: {sig.get('coin_1h_ema','-')}" if sig.get('coin_1h_ema') else "") + "\n"
            f"Skor: {sig['score']}/100  RSI:{sig['rsi']}\nConfluence: {conf}\n"
            + "\n".join([savunma_lines[0], vwap_line, adx_line, session_line, mtf_line, vwm_line, liq_line] +
                        savunma_lines[1:]) + "\n"
            f"Giriş: {_v10_fmt(sig['entry'])} [{sig.get('entry_kaynak','-')}]{kayma_mark}\n"
            f"Stop: {_v10_fmt(sig['stop'])} (%{sig['stop_pct']} sabit)\n"
            f"TP1 {_v10_fmt(sig['tp1'])} ({sig.get('tp1_rr', TP1_RR)}R) | TP2 {_v10_fmt(sig['tp2'])} ({sig.get('tp2_rr', TP2_RR)}R) | "
            f"TP3 {_v10_fmt(sig['tp3'])} ({sig.get('tp3_rr', TP3_RR)}R) | TP4 {_v10_fmt(sig['tp4'])} ({sig.get('tp4_rr', TP4_RR)}R)\n"
            f"Pullback: {sig['pullback']} | FOMO:%{sig['fomo_move_pct']}\n"
            f"OI%{round(safe_float(sig.get('oi_change_pct')),2)} ({sig.get('oi_yorum','-')}) Fund:{round(fund*100,4)}% OBimb:{round(safe_float(sig.get('ob_imbalance')),2)}\n"
            f"⚠️ PAPER — risk %{V10_RISK_PCT}/işlem")


def build_v10_close_message(pos, R, outcome, exit_price):
    if outcome == "STOP":
        head = "❌ STOP GELDİ"
    elif outcome == "TP1":
        head = "✅ TP1 GELDİ — tam çıkış (V11.3)"
    elif outcome == "TIME_EXIT":
        head = "⏱ SÜRE DOLDU — kâr realize"
    else:
        head = f"🏁 {outcome}"
    return (
        f"🆕 V11.3 ULTRA — POZİSYON KAPANDI\n"
        f"{head}\n"
        f"Coin: {pos['symbol']}\n"
        f"Yön: {pos['side']}\n"
        f"Giriş: {_v10_fmt(pos['entry'])}\n"
        f"Çıkış: {_v10_fmt(exit_price)}\n"
        f"Sonuç: {R:+.2f}R (skor {pos['score']})\n"
        f"Saat: {tr_str()}"
    )


def _v10_mem():
    return memory.setdefault("v10_paper", {"open": [], "closed": [], "buckets": {}})


def v107_pos_uid(pos):
    uid = pos.get("uid")
    if not uid:
        uid = f"{pos.get('symbol','?')}|{pos.get('side','?')}|{safe_float(pos.get('open_ts',0)):.3f}|{uuid.uuid4().hex[:6]}"
        pos["uid"] = uid
    return uid


def v10_open_paper(sig):
    mp = _v10_mem()
    poz = {
        "uid": f"{sig['symbol']}|{sig['direction']}|{time.time():.3f}|{uuid.uuid4().hex[:6]}",
        "symbol": sig["symbol"], "side": sig["direction"], "entry": sig["entry"],
        "orig_stop": sig["stop"], "stop": sig["stop"],
        "tp1": sig["tp1"], "tp2": sig["tp2"], "tp3": sig["tp3"], "tp4": sig["tp4"],
        "hit1": False,
        "score": sig["score"], "event": sig["event"],
        "range_break": bool(sig.get("range_break")),
        "entry_kaynak": sig.get("entry_kaynak", "-"),
        "open_ts": time.time(), "scan_ts": 0.0, "candle_ts": sig["candle_ts"],
        "session_name": sig.get("session_name", "-"),
        "piyasa_modu": sig.get("piyasa_modu", "-"),
    }
    mp["open"].append(poz)
    return poz


async def v107_takip_barlari(pos):
    sym = pos["symbol"]
    open_ms = safe_float(pos.get("open_ts", 0)) * 1000.0
    scan_ms = safe_float(pos.get("scan_ts", 0))
    baslangic = max(open_ms, scan_ms)
    k = await get_klines(sym, V107_TAKIP_TF, V107_TAKIP_LIMIT, ttl=V107_TAKIP_CACHE_SEC)
    if not k:
        return [], "veri yok"
    barlar = [r for r in k if safe_float(r[0]) >= baslangic]
    if barlar:
        pos["scan_ts"] = safe_float(barlar[-1][0])
        return barlar, V107_TAKIP_TF
    son = safe_float(k[-1][4])
    return [[safe_float(k[-1][0]), son, son, son, son, 0]], "son fiyat"


def v107_check_paper_bar(pos, hi, lo):
    side = pos["side"]
    if side == "LONG":
        stop_lv = safe_float(pos["orig_stop"])
        if lo <= stop_lv: return -1.0, "STOP"
        if hi >= safe_float(pos["tp1"]):
            pos["hit1"] = True
            return TP1_RR, "TP1"
    else:
        stop_lv = safe_float(pos["orig_stop"])
        if hi >= stop_lv: return -1.0, "STOP"
        if lo <= safe_float(pos["tp1"]):
            pos["hit1"] = True
            return TP1_RR, "TP1"
    return None, None


def v107_check_paper_barlar(pos, barlar):
    for r in barlar:
        R, oc = v107_check_paper_bar(pos, safe_float(r[2]), safe_float(r[3]))
        if oc:
            return R, oc
    return None, None


def v10_record_closed(pos, R, outcome):
    mp = _v10_mem()
    mp["closed"].append({"symbol": pos["symbol"], "side": pos["side"], "R": round(R, 3),
                         "outcome": outcome, "hit1": bool(pos.get("hit1")),
                         "score": pos["score"], "event": pos["event"],
                         "range_break": bool(pos.get("range_break")),
                         "tutma_dk": round((time.time() - safe_float(pos.get("open_ts", 0))) / 60.0, 1),
                         "close_ts": time.time()})


def v10_cooldown_ok(symbol):
    return time.time() - v10_last_alert.get(symbol, 0) >= V10_ALERT_COOLDOWN_MIN * 60


async def maybe_send_v10_signal(sig):
    if not sig:
        return
    symbol = sig["symbol"]
    side = sig["direction"]
    ckey = f"{symbol}:{side}"
    if v10_sent_candle.get(ckey) == sig["candle_ts"]:
        return
    if not v10_cooldown_ok(symbol):
        return

    mp = _v10_mem()
    if len(mp["open"]) >= V10_MAX_OPEN:
        stats["v107_red_defter_dolu"] = int(stats.get("v107_red_defter_dolu", 0)) + 1
        return
    if V107_ACIKKEN_ENGELLE and any(p.get("symbol") == symbol for p in mp["open"]):
        stats["v107_red_acik_poz"] = int(stats.get("v107_red_acik_poz", 0)) + 1
        return

    ok = await send_rich_signal(
        build_v10_message(sig), symbol, side,
        entry=safe_float(sig.get("entry")), stop=safe_float(sig.get("stop")),
        tps={"TP1": sig.get("tp1"), "TP2": sig.get("tp2"), "TP3": sig.get("tp3"), "TP4": sig.get("tp4")},
        meta={"score": sig.get("score"), "rsi": sig.get("rsi"),
              "funding": sig.get("funding"), "oi": sig.get("oi_change_pct"),
              "session_name": sig.get("session_name", ""), "adx": sig.get("adx", 0)},
    )
    if ok:
        v10_last_alert[symbol] = time.time()
        v10_sent_candle[ckey] = sig["candle_ts"]
        v10_open_paper(sig)
        stats["v10_signals"] = int(stats.get("v10_signals", 0)) + 1
        stats["last_signal"] = f"V11.3 {side} {symbol} skor {sig['score']}"
        logger.info("V11.3 SİNYAL %s %s skor=%s session=%s adx=%.1f",
                    side, symbol, sig["score"], sig.get("session_name"), sig.get("adx", 0))


async def v10_scan_loop() -> None:
    await asyncio.sleep(4)
    while True:
        try:
            if not COINS:
                await refresh_coin_pool(force=True)
            batch_size = 8
            coins = list(COINS)[:MA_COIN_LIMIT]
            for i in range(0, len(coins), batch_size):
                batch = coins[i:i + batch_size]
                tasks = [analyze_v10_symbol(sym) for sym in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        continue
                    stats["v10_analyzed"] = int(stats.get("v10_analyzed", 0)) + 1
                    if res:
                        stats["v10_candidates"] = int(stats.get("v10_candidates", 0)) + 1
                        await maybe_send_v10_signal(res)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.exception("v10_scan_loop hata: %s", e)
        await asyncio.sleep(max(5.0, DEEP_SCAN_INTERVAL_SEC))


async def v10_paper_loop() -> None:
    await asyncio.sleep(12)
    while True:
        try:
            mp = _v10_mem()
            kapananlar = set()
            for pos in list(mp["open"]):
                uid = v107_pos_uid(pos)
                barlar, _ = await v107_takip_barlari(pos)
                if not barlar:
                    continue
                R, oc = v107_check_paper_barlar(pos, barlar)

                # Time-based exit
                if not oc and TIME_EXIT_ENABLED:
                    yas_saat = (time.time() - safe_float(pos.get("open_ts", 0))) / 3600.0
                    if yas_saat >= TIME_EXIT_HOURS:
                        son = safe_float(barlar[-1][4])
                        risk = abs(safe_float(pos["entry"]) - safe_float(pos["orig_stop"]))
                        if risk > 0:
                            kâr_move = (son - safe_float(pos["entry"])) if pos["side"] == "LONG" else (safe_float(pos["entry"]) - son)
                            kâr_r = kâr_move / risk
                            if kâr_r >= TIME_EXIT_MIN_PROFIT_R:
                                R, oc = round(kâr_r, 3), "TIME_EXIT"
                            elif kâr_r <= -0.3:
                                R, oc = round(kâr_r, 3), "TIME_EXIT"

                if not oc:
                    continue
                v10_record_closed(pos, R, oc)
                exit_price = pos["orig_stop"] if oc == "STOP" else (pos["tp1"] if oc == "TP1" else safe_float(barlar[-1][4]))
                await safe_send_telegram(build_v10_close_message(pos, R, oc, exit_price))
                kapananlar.add(uid)
            if kapananlar:
                mp["open"] = [p for p in mp["open"] if v107_pos_uid(p) not in kapananlar]
        except Exception as e:
            logger.exception("v10_paper_loop hata: %s", e)
        await asyncio.sleep(max(V107_TAKIP_ARALIK_SEC, 20))


async def save_loop() -> None:
    while True:
        try:
            await save_memory_async()
        except Exception:
            pass
        await asyncio.sleep(max(20, MEMORY_SAVE_INTERVAL_SEC))


async def post_init(application) -> None:
    active_count, pruned_count = await refresh_coin_pool(force=True)
    await safe_send_telegram(
        f"🚀 {VERSION_NAME} başladı\n"
        f"Saat: {tr_str()}\n"
        f"Coin sayısı: {active_count}\n"
        f"Kaldıraç: {LEVERAGE}x | Risk: %{V10_RISK_PCT}/işlem\n"
        f"TP: {TP1_RR}/{TP2_RR}/{TP3_RR}/{TP4_RR}R (TP1=%100 çıkış)\n"
        f"Stop: Sabit %{SABIT_STOP_PCT}\n"
        f"🎯 KATMANLAR:\n"
        f"  🧠 BTC 1H+4H trend + Coin 1H EMA\n"
        f"  🧠 Yapı: CHoCH/BOS (RANGE engelli)\n"
        f"  🧠 Skor (engellemez, risk ayarlar)\n"
        f"  🛡 Spoof + Wash + Pump/Dump + Insider + Stop-Hunt\n"
        f"  📊 VWAP {VWAP_PERIOD_HOURS}h {'AKTİF' if VWAP_ENABLED else 'kapalı'}\n"
        f"  🕐 Session filtresi {'AKTİF' if SESSION_FILTER_ENABLED else 'kapalı'}\n"
        f"  📈 ADX piyasa modu {'AKTİF' if ADX_ENABLED else 'kapalı'}\n"
        f"  💥 Likidasyon haritası {'AKTİF' if LIQ_HEATMAP_ENABLED else 'kapalı'}\n"
        f"  🔀 MTF confluence {'AKTİF' if MTF_CONFLUENCE_ENABLED else 'kapalı'}\n"
        f"  📉 VWM (hacim ağırlıklı) {'AKTİF' if VWM_ENABLED else 'kapalı'}\n"
        f"  🔗 Korelasyon kilidi {'AKTİF' if CORRELATION_GUARD_ENABLED else 'kapalı'}\n"
        f"  ⏱ Time-exit {TIME_EXIT_HOURS}h\n"
        f"  📐 Adaptif pozisyon boyutlandırma"
    )
    for _kur in (symbol_refresh_loop, v10_scan_loop, v10_paper_loop, save_loop):
        asyncio.create_task(_kur(), name=_kur.__name__)


async def cmd_start(update, context):
    await update.message.reply_text(
        f"{VERSION_NAME} aktif.\n"
        "/status - durum\n/test - test\n/v10 - motor durumu\n/coin SYMBOL - tek coin\n"
    )

async def cmd_test(update, context):
    ok = await safe_send_telegram(f"✅ Test başarılı. Saat: {tr_str()}")
    await update.message.reply_text("Gönderildi." if ok else "Başarısız.")

async def cmd_status(update, context):
    mp = _v10_mem()
    cl = mp["closed"]; n = len(cl)
    wins = sum(1 for x in cl if x["R"] > 0)
    ev = (sum(x["R"] for x in cl) / n) if n else 0
    lines = [
        f"📊 V11.3 ULTRA DURUM",
        f"Saat: {tr_str()}",
        f"Coin havuzu: {len(COINS)}/{MA_COIN_LIMIT}",
        f"Analiz: {stats.get('v10_analyzed', 0)} | Aday: {stats.get('v10_candidates', 0)} | Sinyal: {stats.get('v10_signals', 0)}",
        f"Açık: {len(mp['open'])} | Kapalı: {n} | Win%{round(wins/n*100,1) if n else 0} | EV {round(ev,3)}R",
        f"🎯 Filtre red sayaçları:",
        f"  Yapı: {stats.get('v10_red_yapi', 0)}",
        f"  Coin EMA: {stats.get('v11_red_coin_ema', 0)}",
        f"  RANGE: {stats.get('v107_red_range', 0)}",
        f"  FOMO: {stats.get('v11_red_fomo', 0)}",
        f"  OI zayıf: {stats.get('v11_red_oi_zayif', 0)}",
        f"  RSI: {stats.get('v10_red_rsi', 0)}",
        f"  VWAP: {stats.get('v113_red_vwap', 0)}",
        f"  Session: {stats.get('v113_red_session', 0)}",
        f"  MTF: {stats.get('v113_red_mtf', 0)}",
        f"  Korelasyon: {stats.get('v113_red_correlation', 0)}",
        f"  Likidite çakışma: {stats.get('v113_red_liq_conflict', 0)}",
        f"🛡 Manipülasyon:",
        f"  Spoof: {stats.get('v112_red_spoofing', 0)}",
        f"  Wash: {stats.get('v112_red_wash', 0)}",
        f"  Pump/Dump: {stats.get('v112_red_pump_dump', 0)}",
        f"  Insider: {stats.get('v112_red_insider', 0)}",
        f"  Stop-hunt: {stats.get('v112_hit_stop_hunt', 0)}",
    ]
    await update.message.reply_text("\n".join(lines))

async def cmd_coin(update, context):
    if not context.args:
        await update.message.reply_text("Kullanım: /coin BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    res = await analyze_v10_symbol(symbol)
    if not res:
        await update.message.reply_text(f"{symbol} için V11.3 sinyali yok.")
        return
    await update.message.reply_text(build_v10_message(res))

async def cmd_v10(update, context):
    mp = _v10_mem()
    lines = [
        f"🆕 V11.3 ULTRA motor durumu",
        f"Açık: {len(mp['open'])} | Sinyal: {stats.get('v10_signals', 0)}",
        f"Session: {session_belirle()[0]}",
        f"VWAP: {'AKTİF' if VWAP_ENABLED else 'kapalı'} | ADX: {'AKTİF' if ADX_ENABLED else 'kapalı'}",
        f"Likidite: {'AKTİF' if LIQ_HEATMAP_ENABLED else 'kapalı'} | MTF: {'AKTİF' if MTF_CONFLUENCE_ENABLED else 'kapalı'}",
        f"Red: vwap={stats.get('v113_red_vwap',0)} session={stats.get('v113_red_session',0)} mtf={stats.get('v113_red_mtf',0)} "
        f"liq={stats.get('v113_red_liq_conflict',0)} kor={stats.get('v113_red_correlation',0)}",
    ]
    if mp["open"]:
        lines.append("— Açık —")
        for p in mp["open"][:10]:
            yas = round((time.time() - safe_float(p.get("open_ts", 0))) / 60.0)
            lines.append(f"{p['side']} {p['symbol']} skor {p['score']} seans {p.get('session_name','-')} ({yas}dk)")
    await update.message.reply_text("\n".join(lines))


def build_app():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("coin", cmd_coin))
    app.add_handler(CommandHandler("v10", cmd_v10))
    return app


def validate_config() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError(f"Eksik env: {', '.join(missing)}")


def main() -> None:
    validate_config()
    load_memory()
    global app
    app = build_app()
    logger.info("%s başlıyor", VERSION_NAME)
    try:
        app.run_polling(close_loop=False, drop_pending_updates=True)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            save_memory()
        except Exception:
            pass
        try:
            SESSION.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()