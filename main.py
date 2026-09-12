import os
import re
import json
import time
import copy
import uuid
import asyncio
import logging
import threading
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

VERSION_NAME = "Balina Avcısı V11.5.2 ÖLÇÜM LABORATUVARI (SMC + MTF + VWAP + Session + Manipulation Guard)"
BOT_BUILD = os.getenv("BOT_BUILD", "V11.5.2")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com").strip().rstrip("/")
OKX_INST_TYPE = os.getenv("OKX_INST_TYPE", "SWAP").strip().upper()

MEMORY_FILE = os.getenv("MEMORY_FILE", "balina_v11_3_memory.json").strip()
LOG_FILE = os.getenv("LOG_FILE", "balina_v11_3.log").strip()
LOG_MAX_MB = float(os.getenv("LOG_MAX_MB", "10"))
LOG_BACKUPS = int(float(os.getenv("LOG_BACKUPS", "3")))
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Istanbul").strip()

# === KAPI ÖLÇÜM LABORATUVARI ===
OLCUM_MODU = os.getenv("OLCUM_MODU", "false").lower() == "true"
OLCUM_RASTGELE_ORAN = float(os.getenv("OLCUM_RASTGELE_ORAN", "0.10"))
OLCUM_MIN_HUCRE = int(float(os.getenv("OLCUM_MIN_HUCRE", "100")))
OLCUM_DB = os.getenv("OLCUM_DB", "balina_olcum.db").strip()
OLCUM_MAX_OPEN = int(float(os.getenv("OLCUM_MAX_OPEN", "400")))
GOLGE_IZLEME = os.getenv("GOLGE_IZLEME", "true").lower() == "true"
GOLGE_SAAT = float(os.getenv("GOLGE_SAAT", "48"))
GOLGE_ARALIK_SEC = int(float(os.getenv("GOLGE_ARALIK_SEC", "300")))
GOLGE_TF = os.getenv("GOLGE_TF", "15m").strip()

# === TARAMA ===
HOT_SCAN_INTERVAL_SEC = float(os.getenv("HOT_SCAN_INTERVAL_SEC", "1.5"))
DEEP_SCAN_INTERVAL_SEC = float(os.getenv("DEEP_SCAN_INTERVAL_SEC", "8"))
MEMORY_SAVE_INTERVAL_SEC = int(float(os.getenv("MEMORY_SAVE_INTERVAL_SEC", "60")))
KLINE_CACHE_SEC = int(float(os.getenv("KLINE_CACHE_SEC", "5")))
KLINE_CACHE_MAX = int(float(os.getenv("KLINE_CACHE_MAX", "1500")))
TICKER_CACHE_SEC = int(float(os.getenv("TICKER_CACHE_SEC", "8")))
HTTP_TIMEOUT = int(float(os.getenv("HTTP_TIMEOUT", "8")))

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
TP1_WEIGHT = float(os.getenv("TP1_WEIGHT", "0.50"))
TP2_WEIGHT = float(os.getenv("TP2_WEIGHT", "0.30"))
TP3_WEIGHT = float(os.getenv("TP3_WEIGHT", "0.15"))
TP4_WEIGHT = float(os.getenv("TP4_WEIGHT", "0.05"))

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
SPOOF_FIYAT_TOLERANS_PCT = float(os.getenv("SPOOF_FIYAT_TOLERANS_PCT", "0.05"))
SPOOF_MIN_ORAN = float(os.getenv("SPOOF_MIN_ORAN", "0.5"))
SPOOF_GUARD_BLOCK = os.getenv("SPOOF_GUARD_BLOCK", "false").lower() == "true"

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

# === V11.5 KATMANLAR ===
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
LIQ_HEATMAP_FETCH_OI = os.getenv("LIQ_HEATMAP_FETCH_OI", "false").lower() == "true"

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
OKX_EXECUTOR_WORKERS = int(float(os.getenv("OKX_EXECUTOR_WORKERS", "24")))
OKX_CALL_BUDGET_SEC = float(os.getenv("OKX_CALL_BUDGET_SEC", "25"))

# === V10 SMC ===
V10_KLINE_LIMIT = int(float(os.getenv("V10_KLINE_LIMIT", "150")))
V10_SWING_LEFT = int(float(os.getenv("V10_SWING_LEFT", "2")))
V10_SWING_RIGHT = int(float(os.getenv("V10_SWING_RIGHT", "2")))
V10_FOMO_LOOKBACK = int(float(os.getenv("V10_FOMO_LOOKBACK", "5")))
V10_FOMO_MAX_MOVE = float(os.getenv("V10_FOMO_MAX_MOVE_PCT", "3.0"))
V10_PULLBACK_TOL = float(os.getenv("V10_PULLBACK_TOL_PCT", "0.6"))
V10_PULLBACK_WAIT = int(float(os.getenv("V10_PULLBACK_MAX_WAIT", "8")))
V10_ATR_PERIOD = int(float(os.getenv("V10_ATR_PERIOD", "14")))
V10_RSI_LONG_MIN = float(os.getenv("V10_RSI_LONG_MIN", "35"))
V10_RSI_LONG_MAX = float(os.getenv("V10_RSI_LONG_MAX", "75"))
V10_RSI_SHORT_MIN = float(os.getenv("V10_RSI_SHORT_MIN", "25"))
V10_RSI_SHORT_MAX = float(os.getenv("V10_RSI_SHORT_MAX", "65"))
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
logger = logging.getLogger("balina_v11_5")

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


class _AsyncTokenBucket:
    def __init__(self, rate: float, burst: float, ad: str):
        self.rate = max(0.1, rate)
        self.burst = max(1.0, burst)
        self.ad = ad
        self._tokens = self.burst
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                simdi = time.monotonic()
                self._tokens = min(self.burst, self._tokens + (simdi - self._last) * self._etkin_rate())
                self._last = simdi
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                eksik = (1.0 - self._tokens) / self._etkin_rate()
            await asyncio.sleep(min(max(eksik, 0.005), 1.0))

    def _etkin_rate(self) -> float:
        if time.monotonic() < _OKX_CEZA["kadar"]:
            return max(0.5, self.rate * 0.5)
        return self.rate


_OKX_CEZA: Dict[str, float] = {"kadar": 0.0, "sayac": 0.0}
_BUCKET_GENEL = _AsyncTokenBucket(OKX_RATE_GENEL, OKX_BURST_GENEL, "genel")
_BUCKET_RUBIK = _AsyncTokenBucket(OKX_RATE_RUBIK, OKX_BURST_RUBIK, "rubik")


def _okx_kova(path: str) -> "_AsyncTokenBucket":
    return _BUCKET_RUBIK if "/rubik/" in path else _BUCKET_GENEL


def _okx_429_kaydet() -> None:
    _OKX_CEZA["kadar"] = time.monotonic() + OKX_429_CEZA_SEC
    _OKX_CEZA["sayac"] = _OKX_CEZA.get("sayac", 0.0) + 1


OKX_EXECUTOR = ThreadPoolExecutor(max_workers=OKX_EXECUTOR_WORKERS, thread_name_prefix="okx")


async def _okx_get_async(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 1) -> Any:
    loop = asyncio.get_running_loop()
    await _okx_kova(path).acquire()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(OKX_EXECUTOR, _okx_get, path, params, max_retries),
            timeout=max(1.0, OKX_CALL_BUDGET_SEC),
        )
    except asyncio.TimeoutError:
        stats["okx_timeout"] = int(stats.get("okx_timeout", 0)) + 1
        raise


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
    "v107_red_range": 0,
    "v11_red_coin_ema": 0, "v11_red_fomo": 0, "v11_red_oi_zayif": 0,
    "v112_red_spoofing": 0, "v112_red_wash": 0, "v112_red_pump_dump": 0,
    "v112_red_insider": 0, "v112_hit_stop_hunt": 0,
    "v112_spoof_gorulen": 0, "v112_spoof_keserdi": 0,
    # V11.5
    "v113_red_vwap": 0, "v113_red_session": 0,
    "v113_red_mtf": 0, "v113_red_correlation": 0, "v113_hit_liq_cluster": 0,
    "v113_red_vwm": 0, "okx_timeout": 0,
}

app = None
memory_lock = asyncio.Lock()
v10_last_alert: Dict[str, float] = {}
v10_sent_candle: Dict[str, str] = {}
_v107_stop_kilit: Dict[str, float] = {}

_V106_BTC_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}

OLCUM_KAPILARI = (
    "btc_hiza", "wash", "pump", "yapi", "range", "fomo",
    "coin_1h_ema", "pullback", "session", "vwap", "mtf", "vwm",
    "spoof", "rsi", "oi_yorum", "kayma", "korelasyon",
)
_OLCUM_DB_LOCK = threading.Lock()


def olcum_db_init() -> None:
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS olcum_pozisyon (
                uid TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                kontrol INTEGER NOT NULL DEFAULT 0,
                open_ts REAL NOT NULL,
                close_ts REAL,
                durum TEXT NOT NULL DEFAULT 'ACIK',
                r_value REAL NOT NULL DEFAULT 0,
                mfe_pct REAL NOT NULL DEFAULT 0,
                mae_pct REAL NOT NULL DEFAULT 0,
                kapi_json TEXT NOT NULL
            )
        """)
        mevcut_kolonlar = {row[1] for row in conn.execute("PRAGMA table_info(olcum_pozisyon)")}
        yeni_kolonlar = {
            "golge_durum": "TEXT",
            "golge_tp": "INTEGER",
            "golge_mfe_pct": "REAL",
            "golge_mae_pct": "REAL",
            "golge_tp1_dk": "REAL",
            "golge_bitis_ts": "REAL",
        }
        for kolon, tur in yeni_kolonlar.items():
            if kolon not in mevcut_kolonlar:
                conn.execute(f"ALTER TABLE olcum_pozisyon ADD COLUMN {kolon} {tur}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_olcum_durum ON olcum_pozisyon(durum)")


def olcum_db_pozisyon_ac(pos: Dict[str, Any]) -> None:
    if not OLCUM_MODU and not GOLGE_IZLEME:
        return
    payload = json.dumps(pos.get("kapi_sonuclari", {}), ensure_ascii=False, sort_keys=True)
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO olcum_pozisyon
            (uid,symbol,side,kontrol,open_ts,durum,r_value,mfe_pct,mae_pct,kapi_json)
            VALUES (?,?,?,?,?,'ACIK',?,?,?,?)
        """, (v107_pos_uid(pos), pos["symbol"], pos["side"], int(bool(pos.get("kontrol"))),
              safe_float(pos.get("open_ts")), safe_float(pos.get("current_r")),
              safe_float(pos.get("mfe_pct")), safe_float(pos.get("mae_pct")), payload))


def olcum_db_pozisyon_guncelle(pos: Dict[str, Any], durum: str = "ACIK",
                               r_value: Optional[float] = None) -> None:
    if not OLCUM_MODU and not GOLGE_IZLEME:
        return
    close_ts = time.time() if durum != "ACIK" else None
    rv = safe_float(pos.get("current_r")) if r_value is None else safe_float(r_value)
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        mevcut = conn.execute("SELECT kapi_json FROM olcum_pozisyon WHERE uid=?",
                              (v107_pos_uid(pos),)).fetchone()
        try:
            payload = json.loads(mevcut[0] or "{}") if mevcut else {}
        except Exception:
            payload = {}
        for idx in range(1, 5):
            payload[f"_hit{idx}"] = bool(pos.get(f"hit{idx}"))
        conn.execute("""
            UPDATE olcum_pozisyon SET durum=?, close_ts=?, r_value=?, mfe_pct=?, mae_pct=?, kapi_json=?
            WHERE uid=?
        """, (durum, close_ts, rv, safe_float(pos.get("mfe_pct")),
              safe_float(pos.get("mae_pct")), json.dumps(payload, ensure_ascii=False, sort_keys=True),
              v107_pos_uid(pos)))


def olcum_db_golge_baslat(pos: Dict[str, Any]) -> None:
    if not GOLGE_IZLEME or not os.path.exists(OLCUM_DB):
        return
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("""
            UPDATE olcum_pozisyon
            SET golge_durum='IZLENIYOR', golge_tp=0, golge_mfe_pct=0,
                golge_mae_pct=0, golge_tp1_dk=NULL, golge_bitis_ts=NULL
            WHERE uid=?
        """, (v107_pos_uid(pos),))


def olcum_db_golge_guncelle(golge: Dict[str, Any], bitti: bool = False) -> None:
    if not GOLGE_IZLEME or not os.path.exists(OLCUM_DB):
        return
    durum = "BITTI" if bitti else "IZLENIYOR"
    bitis_ts = time.time() if bitti else None
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("""
            UPDATE olcum_pozisyon
            SET golge_durum=?, golge_tp=?, golge_mfe_pct=?, golge_mae_pct=?,
                golge_tp1_dk=?, golge_bitis_ts=?
            WHERE uid=?
        """, (durum, int(golge.get("golge_tp", 0)), safe_float(golge.get("golge_mfe_pct")),
              safe_float(golge.get("golge_mae_pct")), golge.get("golge_tp1_dk"), bitis_ts,
              str(golge.get("uid", ""))))


def olcum_db_tp_satirlari() -> List[Tuple[Any, ...]]:
    if not os.path.exists(OLCUM_DB):
        return []
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        return conn.execute("""
            SELECT kontrol,mfe_pct,mae_pct,kapi_json,durum,golge_durum,golge_tp,
                   golge_mfe_pct,golge_mae_pct,golge_tp1_dk
            FROM olcum_pozisyon
        """).fetchall()


def olcum_db_satirlari() -> List[Tuple[Any, ...]]:
    if not os.path.exists(OLCUM_DB):
        return []
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        return conn.execute(
            "SELECT kontrol,r_value,mfe_pct,mae_pct,kapi_json,durum FROM olcum_pozisyon"
        ).fetchall()


def olcum_db_acik_durum(uid: str) -> Optional[Tuple[Any, ...]]:
    if not os.path.exists(OLCUM_DB):
        return None
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        return conn.execute(
            "SELECT kontrol,r_value,mfe_pct,mae_pct,kapi_json FROM olcum_pozisyon WHERE uid=? AND durum='ACIK'",
            (uid,),
        ).fetchone()


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

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

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
    memory["v10_paper"].setdefault("golge", [])
    memory.setdefault("last_signal_ts", 0.0)
    memory.setdefault("runtime", {})

def load_memory() -> None:
    global memory, stats, v10_last_alert, v10_sent_candle
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
            ensure_memory_shape()
            saved_stats = memory.get("stats", {})
            if isinstance(saved_stats, dict):
                stats.update(saved_stats)
            runtime = memory.get("runtime", {})
            if isinstance(runtime, dict):
                v10_last_alert.update({str(k): safe_float(v) for k, v in runtime.get("last_alert", {}).items()})
                v10_sent_candle.update({str(k): str(v) for k, v in runtime.get("sent_candle", {}).items()})
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
        memory["stats"] = copy.deepcopy(stats)
        memory["runtime"] = {"last_alert": copy.deepcopy(v10_last_alert),
                             "sent_candle": copy.deepcopy(v10_sent_candle)}
        snapshot = json_memory_snapshot()
    except Exception as e:
        logger.exception("Memory snapshot alınamadı: %s", e)
        return
    _write_memory_snapshot(snapshot)

async def save_memory_async() -> None:
    async with memory_lock:
        ensure_memory_shape()
        memory["stats"] = copy.deepcopy(stats)
        memory["runtime"] = {"last_alert": copy.deepcopy(v10_last_alert),
                             "sent_candle": copy.deepcopy(v10_sent_candle)}
        snapshot = json_memory_snapshot()
    await asyncio.to_thread(_write_memory_snapshot, snapshot)


def json_memory_snapshot() -> Dict[str, Any]:
    """Ölçüm alanlarını JSON'dan ayırır; ana kayıt yalnız SQLite'ta kalır."""
    snapshot = copy.deepcopy(memory)
    measurement_keys = {"kapi_sonuclari", "kontrol", "mfe_pct", "mae_pct", "current_r"}
    paper = snapshot.get("v10_paper", {})
    for bucket in (paper.get("open", []), paper.get("closed", [])):
        for rec in bucket:
            for key in measurement_keys:
                rec.pop(key, None)
    return snapshot

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


def _render_signal_chart_unlocked(symbol, direction, klines, entry, stop, tps, meta, tz_name, vwap_val=None, session_name="", adx_val=0.0):
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


def _render_signal_chart_sync(symbol, direction, klines, entry, stop, tps, meta,
                              tz_name, vwap_val=None, session_name="", adx_val=0.0):
    # Matplotlib eşzamanlı çizimde güvenli değildir.
    with _CHART_LOCK:
        return _render_signal_chart_unlocked(symbol, direction, klines, entry, stop,
                                             tps, meta, tz_name, vwap_val,
                                             session_name, adx_val)


async def render_signal_chart(symbol, direction, entry, stop, tps, meta):
    try:
        k = await get_klines(symbol, SIGNAL_CHART_TF, SIGNAL_CHART_CANDLES)
        if len(k) < 30:
            return None
        vwap_val = 0.0
        if VWAP_ENABLED:
            vwap_bars = max(1, int((VWAP_PERIOD_HOURS * 60) / interval_minutes(SIGNAL_CHART_TF)))
            vwap_val = vwap_hesapla(k, vwap_bars) or 0.0
        return await asyncio.to_thread(_render_signal_chart_sync, symbol, direction,
                                       k, entry, stop, tps or {}, meta or {}, TIMEZONE_NAME,
                                       vwap_val if VWAP_BONUS_IN_CHART else 0.0,
                                       meta.get("session_name", ""), safe_float(meta.get("adx", 0)))
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


def _okx_get(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 1) -> Any:
    url = f"{OKX_BASE_URL}{path}"
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = SESSION.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                if resp.status_code == 429:
                    _okx_429_kaydet()
                if attempt < max_retries:
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


def quote_volume_from_ticker(row: Dict[str, Any], instrument: Optional[Dict[str, Any]] = None) -> float:
    """OKX SWAP hacmini yaklaşık USDT notional'a çevirir."""
    last = safe_float(row.get("last", 0))
    vol24h = safe_float(row.get("vol24h", 0))
    vol_ccy_24h = safe_float(row.get("volCcy24h", 0))
    inst = instrument or {}
    ct_val = safe_float(inst.get("ctVal", 0))
    ct_type = str(inst.get("ctType", "")).lower()
    # Linear USDT swap: volCcy24h temel para miktarıdır; fiyatla çarpılır.
    if vol_ccy_24h > 0 and last > 0:
        return vol_ccy_24h * last
    if vol24h > 0 and last > 0 and ct_val > 0:
        return vol24h * ct_val * last if ct_type != "inverse" else vol24h * ct_val
    return 0.0


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
        qv = quote_volume_from_ticker(row, instruments.get(ns, {}) if instruments else {})
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
        ordered = sorted(d, key=lambda row: safe_float(row[0]), reverse=True)
        oi_now = safe_float(ordered[0][1])
        oi_past = safe_float(ordered[lookback_periods][1])
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
    """Anlık OI değerini OKX'in oiUsd alanından USD notional olarak döndürür."""
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
        val = safe_float(row.get("oiUsd", 0))
        if val <= 0:
            oi_ccy = safe_float(row.get("oiCcy", 0))
            ticker = (await get_24h_tickers()).get(symbol, {})
            val = oi_ccy * safe_float(ticker.get("last", 0))
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
    if not klines:
        return []
    confirmed = [row for row in klines if len(row) > 8 and str(row[8]) == "1"]
    if confirmed:
        return confirmed
    return klines[:-1] if len(klines) > 1 else []


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
#  V11.5 — ULTRA KATMANLAR
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
    if len(dxs) < period:
        return 0.0
    adx_value = sum(dxs[:period]) / period
    for dx in dxs[period:]:
        adx_value = (adx_value * (period - 1) + dx) / period
    return adx_value


def interval_minutes(interval: str) -> int:
    m = re.fullmatch(r"(?i)(\d+)(m|h|d)", (interval or "").strip())
    if not m:
        return 60
    value, unit = int(m.group(1)), m.group(2).lower()
    return value * (1 if unit == "m" else 60 if unit == "h" else 1440)


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
    # Çakışan 13:00-16:00 UTC aralığında daha yüksek hacimli NY seansı önceliklidir.
    if SESSION_NY_START_UTC <= h < SESSION_NY_END_UTC:
        return "NewYork", 3
    if SESSION_LONDON_START_UTC <= h < SESSION_LONDON_END_UTC:
        return "Londra", 2
    return "Geçiş", 1


def session_yon_uygun(side: str, force: bool = False) -> Tuple[bool, str]:
    """V11.5: Bazı seanslarda bazı yönler riskli."""
    if not SESSION_FILTER_ENABLED and not force:
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
    sonuç = {"clusters": [], "top_bid_cluster": 0.0, "top_ask_cluster": 0.0,
             "estimated": True, "can_block": False}
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
        cluster_value = oi_per_side / max(1, len(LIQ_HEATMAP_LEVERAGES))
        if cluster_value >= LIQ_HEATMAP_MIN_CLUSTER and abs(pct_change(price, long_liq_price)) <= LIQ_HEATMAP_DIST_PCT:
            sonuç["clusters"].append({
                "side": "LONG_LIQ", "price": long_liq_price,
                "value": cluster_value,
                "lev": lev,
            })
        if cluster_value >= LIQ_HEATMAP_MIN_CLUSTER and abs(pct_change(price, short_liq_price)) <= LIQ_HEATMAP_DIST_PCT:
            sonuç["clusters"].append({
                "side": "SHORT_LIQ", "price": short_liq_price,
                "value": cluster_value,
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
    """Tahmini harita yalnızca bilgi verir; hiçbir koşulda sinyal kesmez."""
    return False, "tahmini — bilgi amaçlı"


async def mtf_confluence_async(symbol: str, side: str, force: bool = False) -> Tuple[bool, str, int]:
    if not MTF_CONFLUENCE_ENABLED and not force:
        return True, "kapalı", 0
    onay = 0
    olculen = 0
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
        olculen += 1
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
    if olculen == 0:
        stats["v113_red_mtf"] = int(stats.get("v113_red_mtf", 0)) + 1
        return False, "MTF veri yok", 0
    if onay < MTF_MIN_AGREE:
        stats["v113_red_mtf"] = int(stats.get("v113_red_mtf", 0)) + 1
        return False, f"MTF onay yok ({onay}/{olculen})", onay
    return True, " ".join(detay), onay


def korelasyon_grubu(symbol: str) -> str:
    """Basit korelasyon grubu tahmini."""
    base = _base_of(symbol)
    if base in _correlation_group_cache:
        return _correlation_group_cache[base]
    grup = "diğer"
    if base in ("BTC", "ETH"):
        grup = "majors"
    elif base in ("SOL", "AVAX", "NEAR", "SUI", "APT", "SEI", "TIA", "DOT", "ATOM", "INJ"):
        grup = "L1"
    elif base in ("ARB", "OP", "MATIC", "STRK", "ZK", "MANTA"):
        grup = "L2"
    elif base in ("FET", "RNDR", "TAO", "WLD", "AGIX"):
        grup = "ai"
    elif base in ("DOGE", "SHIB", "PEPE", "WIF", "BONK"):
        grup = "memes"
    _correlation_group_cache[base] = grup
    return grup


def korelasyon_kilidi(symbol: str, side: str, force: bool = False) -> Tuple[bool, str]:
    """Aynı yönde çok fazla korele pozisyon açılmasını engelle."""
    if not CORRELATION_GUARD_ENABLED and not force:
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


def volume_weighted_momentum(klines: List[List[Any]], side: str, window: int = 10,
                             force: bool = False) -> Tuple[bool, float]:
    """Hacim ağırlıklı momentum. Yüksek hacimli mumlar yönü belirler."""
    if (not VWM_ENABLED and not force) or len(klines) < window + 1:
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
    cls = closes(k)
    lc = cls[-1]
    recent_start = max(1, len(cls) - V10_PULLBACK_WAIT - 2)
    up_break_idx = next((i for i in range(len(cls) - 1, recent_start - 1, -1)
                         if cls[i - 1] <= res["last_sh"] < cls[i]), -1) if res["last_sh"] > 0 else -1
    down_break_idx = next((i for i in range(len(cls) - 1, recent_start - 1, -1)
                           if cls[i - 1] >= res["last_sl"] > cls[i]), -1) if res["last_sl"] > 0 else -1
    if up_break_idx >= 0:
        res["event"] = "CHoCH" if res["trend"] == "DOWN" else "BOS"
        res["event_side"] = "UP"
        res["event_level"] = res["last_sh"]
        res["event_idx"] = up_break_idx
        res["range_break"] = (res["trend"] == "RANGE")
    elif down_break_idx >= 0:
        res["event"] = "CHoCH" if res["trend"] == "UP" else "BOS"
        res["event_side"] = "DOWN"
        res["event_level"] = res["last_sl"]
        res["event_idx"] = down_break_idx
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


async def v112_spoof_tespit(symbol: str, force: bool = False) -> Tuple[bool, str]:
    if (not SPOOF_GUARD_ENABLED and not force) or not V10_USE_ORDERBOOK:
        return False, "kapalı"
    try:
        snapshots = []
        for _ in range(SPOOF_CHECK_COUNT):
            data = await _okx_get_async("/api/v5/market/books", {"instId": symbol, "sz": 20})
            if not data:
                return False, "veri yok"
            book = data[0]
            top_bids = [(safe_float(b[0]), safe_float(b[1])) for b in book.get("bids", [])[:10]]
            top_asks = [(safe_float(a[0]), safe_float(a[1])) for a in book.get("asks", [])[:10]]
            bid0 = top_bids[0][0] if top_bids else 0.0
            ask0 = top_asks[0][0] if top_asks else 0.0
            snapshots.append({"bids": top_bids, "asks": top_asks,
                              "mid": (bid0 + ask0) / 2.0 if bid0 and ask0 else 0.0})
            if len(snapshots) < SPOOF_CHECK_COUNT:
                await asyncio.sleep(SPOOF_CHECK_INTERVAL)
        if len(snapshots) < 2:
            return False, "yetersiz"
        ilk, son = snapshots[0], snapshots[-1]
        kaybolan = toplam = 0
        for side_name in ("bids", "asks"):
            first_levels = ilk[side_name]
            mean_size = avg([q for _, q in first_levels])
            for price, qty in first_levels:
                if mean_size <= 0 or qty < mean_size * V10_OB_WALL_MULT:
                    continue
                toplam += 1
                tolerance = price * max(0.0, SPOOF_FIYAT_TOLERANS_PCT) / 100.0
                final_qty = sum(q for p, q in son[side_name] if abs(p - price) <= tolerance)
                if qty > 0 and (qty - final_qty) / qty >= SPOOF_CHANGE_THRESHOLD:
                    kaybolan += 1
        mid_move = abs(pct_change(safe_float(ilk.get("mid")), safe_float(son.get("mid"))))
        if toplam > 0 and (kaybolan / toplam) >= clamp(SPOOF_MIN_ORAN, 0.0, 1.0) and mid_move < 0.30:
            return True, f"spoofing şüphesi ({kaybolan}/{toplam} büyük duvar kayboldu)"
        return False, "stabil"
    except Exception:
        return False, "hata"


def v112_wash_tespit(symbol: str, klines, force: bool = False) -> Tuple[bool, str]:
    if (not WASH_GUARD_ENABLED and not force) or len(klines) < 30:
        return False, "kapalı"
    try:
        klines = _s_closed(klines)
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


def v112_pump_dump_tespit(symbol, klines, tickers24, force: bool = False) -> Tuple[bool, str]:
    klines = _s_closed(klines)
    if (not PUMP_DUMP_GUARD_ENABLED and not force) or len(klines) < 2:
        return False, "kapalı"
    try:
        hareket = abs(pct_change(safe_float(klines[-2][4]), safe_float(klines[-1][4])))
        if hareket < PUMP_DUMP_MAX_1H_MOVE:
            return False, "normal"
        vol_24h = quote_volume_from_ticker(tickers24.get(symbol, {}), okx_live_symbols.get(symbol, {}))
        if vol_24h >= PUMP_DUMP_MIN_VOL:
            return False, "likidite yeterli"
        return True, f"pump/dump (1h %{hareket:.1f}, hacim {vol_24h/1e6:.1f}M)"
    except Exception:
        return False, "hata"


def v112_insider_tespit(symbol, klines) -> Tuple[bool, str]:
    if not INSIDER_GUARD_ENABLED or len(klines) < 30:
        return False, ""
    try:
        klines = _s_closed(klines)
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
        k = _s_closed(klines)[-1]
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
    max_gap_ratio = max(0.0, V107_MAX_GIRIS_KAYMA) / 100.0
    if mid > 0 and ref > 0 and abs(mid - ref) / ref <= max_gap_ratio:
        return mid, "orderbook"
    try:
        forming = safe_float(k1h[-1][4])
    except Exception:
        forming = 0.0
    if forming > 0 and ref > 0 and abs(forming - ref) / ref <= max_gap_ratio:
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


def _kapi_durum(value: Optional[bool]) -> str:
    if value is None:
        return "olcumsuz"
    return "gecti" if value else "kesti"


def kapi_olc(symbol: str, side: str, k: List[List[Any]], ext: Dict[str, Any]) -> Dict[str, str]:
    """Bütün kapıları bloklama yolundan bağımsız ve erken çıkış yapmadan ölçer."""
    sonuc: Dict[str, str] = {}
    for ad in OLCUM_KAPILARI:
        if ad == "yapi":
            ms = ext.get("ms") or v10_market_structure(k)
            value = v10_structure_allows(side, ms)[0]
        elif ad == "range":
            value = not bool((ext.get("ms") or {}).get("range_break"))
        elif ad == "fomo":
            value = not v10_fomo_block(side, k)[0]
        elif ad == "pullback":
            ms = ext.get("ms") or {}
            value = v10_pullback(side, k, ms)[0]
        elif ad == "rsi":
            rv = rsi(closes(k))[-1] if k else None
            value = None if rv is None else ((V10_RSI_LONG_MIN <= rv <= V10_RSI_LONG_MAX)
                    if side == "LONG" else (V10_RSI_SHORT_MIN <= rv <= V10_RSI_SHORT_MAX))
        else:
            value = ext.get(f"{ad}_ok")
        sonuc[ad] = _kapi_durum(value)
    return sonuc


def _olcum_trend4(k4h: Optional[List[List[Any]]]) -> str:
    if not k4h or len(k4h) < 52:
        return "FLAT"
    c4 = closes(_s_closed(k4h))
    e4 = ema(c4, min(50, len(c4) - 1))
    return "UP" if c4[-1] > e4[-1] else "DOWN"


def _olcum_pozisyon_boyutu(score: float, k: List[List[Any]], entry: float,
                            session_weight: int) -> Dict[str, Any]:
    atr_now = safe_float(atr(k, V10_ATR_PERIOD)[-1])
    atr_pct = (atr_now / entry * 100.0) if entry > 0 else 0.0
    volatilite = "HIGH" if atr_pct >= 3.0 else "LOW" if atr_pct <= 1.0 else "NORMAL"
    size_mult = adaptif_pozisyon_carpani(score, volatilite, session_weight)
    risk_pct = min(max(0.0, V10_RISK_PCT * size_mult), max(0.0, MAX_POSITION_RISK_PCT))
    risk_usdt = round(DEFAULT_MARGIN_USDT * risk_pct / 100.0, 2)
    notional = round(risk_usdt / max(SABIT_STOP_PCT / 100.0, 1e-9), 2)
    return {"volatilite": volatilite, "position_multiplier": round(size_mult, 3),
            "margin_usdt": round(notional / max(1.0, LEVERAGE), 2),
            "notional_usdt": notional, "estimated_risk_usdt": risk_usdt,
            "effective_risk_pct": round(risk_pct, 3)}


async def analyze_olcum_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Ölçüm yoludur: yön için asgari yapı dışında hiçbir kapı sinyali kesmez."""
    symbol = normalize_symbol(symbol)
    k1h = await get_klines(symbol, "1H", V10_KLINE_LIMIT)
    if len(k1h) < 40:
        stats["v10_red_veri"] = int(stats.get("v10_red_veri", 0)) + 1
        return None
    k = _s_closed(k1h)
    ms = v10_market_structure(k)
    kontrol = random.random() < clamp(OLCUM_RASTGELE_ORAN, 0.0, 1.0)
    yapisal_yon = "LONG" if ms.get("event_side") == "UP" else "SHORT" if ms.get("event_side") == "DOWN" else None
    if not yapisal_yon and not kontrol:
        stats["v10_red_yapi"] = int(stats.get("v10_red_yapi", 0)) + 1
        return None

    side = random.choice(("LONG", "SHORT")) if kontrol else yapisal_yon
    entry_ref = closes(k)[-1]

    if kontrol:
        entry = entry_ref
        tgt = v10_targets(side, entry)
        kapilar = kapi_olc(symbol, side, k, {"ms": ms})
        size = _olcum_pozisyon_boyutu(50.0, k, entry, 1)
        return {"symbol": symbol, "direction": side, "entry": entry, "strategy": "V11.5_KONTROL",
                "entry_ref": entry_ref, "entry_kaynak": "kontrol", "entry_kayma_pct": 0.0,
                "event": "CONTROL", "structure": "Rastgele kontrol grubu", "range_break": False,
                "trend_1h": ms.get("trend", "RANGE"), "trend_4h": "FLAT", "fomo_move_pct": 0.0,
                "pullback": "ölçümsüz", "score": 50.0, "score_parts": {}, "bayrak": {},
                "rsi": round(rsi(closes(k))[-1], 1), "candle_ts": str(k[-1][0]),
                "oi_change_pct": 0.0, "oi_yorum": "ölçümsüz", "coin_1h_ema": "-",
                "funding": None, "ob_imbalance": 0.0, "btc_4h": "-", "btc_1h": "-",
                "trend_uyum": False, "spoof_guard": "ölçümsüz", "wash_guard": "ölçümsüz",
                "pump_guard": "ölçümsüz", "insider_uyari": "", "stop_hunt": "",
                "adx": round(adx_hesapla(k, ADX_PERIOD), 2), "piyasa_modu": "KONTROL",
                "session_name": session_belirle()[0], "session_weight": 1, "vwap": 0.0,
                "mtf_note": "ölçümsüz", "mtf_count": 0, "vwm": 0.0, "liq_map": {},
                "liq_note": "ölçümsüz", "kapi_sonuclari": kapilar, "kontrol": True,
                **size, **tgt}

    bt = await v106_btc_trend()
    btc_1h, btc_4h = bt.get("dir_1h", "FLAT"), bt.get("dir_4h", "FLAT")
    allowed_side = bt.get("allow")
    wash_hit, wash_note = v112_wash_tespit(symbol, k1h, force=True)
    tickers24 = await get_24h_tickers()
    pump_hit, pump_note = v112_pump_dump_tespit(symbol, k1h, tickers24, force=True)
    k4h = await get_klines(symbol, "4H", 120, ttl=180) if V10_USE_4H_FILTER else None
    trend4 = _olcum_trend4(k4h)
    fomo_hit, fomo_mv = v10_fomo_block(side, k)
    pb_ok, pb_note = v10_pullback(side, k, ms)
    coin_yon = v109_coin_1h_yon(k1h)
    session_ok, _ = session_yon_uygun(side, force=True)
    session_name, session_weight = session_belirle()
    vwap_v = vwap_hesapla(k, VWAP_PERIOD_HOURS)
    vwap_ok = None if not vwap_v else ((entry_ref >= vwap_v) if side == "LONG" else (entry_ref <= vwap_v))
    mtf_ok, mtf_note, mtf_count = await mtf_confluence_async(symbol, side, force=True)
    vwm_ok, vwm_val = volume_weighted_momentum(k, side, force=True)
    oi = await fetch_okx_oi_change(symbol, 12)
    funding = await fetch_okx_funding_rate(symbol)
    ob = await v10_fetch_orderbook(symbol)
    spoof_hit, spoof_note = await v112_spoof_tespit(symbol, force=True)
    entry, giris_kaynak = v107_canli_giris(k1h, ob, entry_ref)
    kayma = abs(entry - entry_ref) / entry_ref * 100.0 if entry_ref > 0 else 0.0
    kor_block, _ = korelasyon_kilidi(symbol, side, force=True)
    ext = {"oi_change_pct": oi if oi is not None else 0.0, "funding": funding,
           "btc_dir": btc_4h, "btc_dir_1h": btc_1h, "orderbook": ob}
    score, parts, r_value, bayrak = v10_quality_score(side, k, ms, ext)
    oi_yorum = ext.get("oi_yorum", "")
    rsi_ok = ((V10_RSI_LONG_MIN <= r_value <= V10_RSI_LONG_MAX) if side == "LONG"
              else (V10_RSI_SHORT_MIN <= r_value <= V10_RSI_SHORT_MAX))
    gate_ext = {"ms": ms,
                "btc_hiza_ok": None if not bt.get("ok") else allowed_side == side,
                "wash_ok": None if wash_note in ("hata", "veri yok", "kapalı") else not wash_hit,
                "pump_ok": None if pump_note in ("hata", "veri yok", "kapalı") else not pump_hit,
                "coin_1h_ema_ok": None if coin_yon == "FLAT" else
                    ((coin_yon == "UP") if side == "LONG" else (coin_yon == "DOWN")),
                "session_ok": session_ok, "vwap_ok": vwap_ok,
                "mtf_ok": None if "veri yok" in mtf_note.lower() else mtf_ok,
                "vwm_ok": vwm_ok,
                "spoof_ok": None if spoof_note in ("hata", "veri yok", "yetersiz", "kapalı") else not spoof_hit,
                "rsi_ok": rsi_ok,
                "oi_yorum_ok": None if oi is None else not ((side == "LONG" and "short kapanışı" in oi_yorum) or
                                                             (side == "SHORT" and "long likidasyonu" in oi_yorum)),
                "kayma_ok": True if V107_MAX_GIRIS_KAYMA <= 0 else kayma <= V107_MAX_GIRIS_KAYMA,
                "korelasyon_ok": not kor_block}
    kapilar = kapi_olc(symbol, side, k, gate_ext)
    oi_value = await fetch_okx_open_interest_value(symbol) if (LIQ_HEATMAP_ENABLED and LIQ_HEATMAP_FETCH_OI) else None
    liq_map = likidasyon_haritasi(symbol, k, oi_value or 0.0) if oi_value else {}
    insider_hit, insider_note = v112_insider_tespit(symbol, k1h)
    stop_hunt_hit, stop_hunt_note = v112_stop_hunt_tespit(k1h)
    tgt = v10_targets(side, entry)
    size = _olcum_pozisyon_boyutu(score, k, entry, session_weight)
    return {"symbol": symbol, "direction": side, "entry": entry, "strategy": "V11.5_OLCUM",
            "entry_ref": entry_ref, "entry_kaynak": giris_kaynak, "entry_kayma_pct": round(kayma, 3),
            "event": ms.get("event"), "structure": v10_structure_allows(side, ms)[1],
            "range_break": bool(ms.get("range_break")), "trend_1h": ms.get("trend", "RANGE"),
            "trend_4h": trend4, "fomo_move_pct": round(fomo_mv, 2), "pullback": pb_note or "yok",
            "score": score, "score_parts": parts, "bayrak": bayrak, "rsi": r_value,
            "candle_ts": str(k[-1][0]), "oi_change_pct": ext["oi_change_pct"], "oi_yorum": oi_yorum,
            "coin_1h_ema": coin_yon, "funding": funding, "ob_imbalance": ob.get("imbalance", 0),
            "btc_4h": btc_4h, "btc_1h": btc_1h, "trend_uyum": allowed_side == side,
            "spoof_guard": spoof_note, "wash_guard": wash_note, "pump_guard": pump_note,
            "insider_uyari": insider_note if insider_hit else "", "stop_hunt": stop_hunt_note if stop_hunt_hit else "",
            "adx": round(adx_hesapla(k, ADX_PERIOD), 2), "piyasa_modu": "OLCUM",
            "session_name": session_name, "session_weight": session_weight,
            "vwap": round(vwap_v, 8) if vwap_v else 0.0, "mtf_note": mtf_note,
            "mtf_count": mtf_count, "vwm": round(vwm_val, 3), "liq_map": liq_map,
            "liq_note": "tahmini — bilgi amaçlı", "kapi_sonuclari": kapilar,
            "kontrol": False, **size, **tgt}


async def analyze_v10_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    if OLCUM_MODU:
        return await analyze_olcum_symbol(symbol)
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

    # V11.5 katmanlar
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
        stats["v113_red_vwm"] = int(stats.get("v113_red_vwm", 0)) + 1
        return None

    # RSI yerel mumlardan hazır; pahalı OI/funding/orderbook/spoof çağrılarından önce ele.
    r_pre = round(rsi(closes(k))[-1], 1)
    if ((side == "LONG" and not (V10_RSI_LONG_MIN <= r_pre <= V10_RSI_LONG_MAX)) or
            (side == "SHORT" and not (V10_RSI_SHORT_MIN <= r_pre <= V10_RSI_SHORT_MAX))):
        stats["v10_red_rsi"] = int(stats.get("v10_red_rsi", 0)) + 1
        return None

    oi = await fetch_okx_oi_change(symbol, 12)
    funding = await fetch_okx_funding_rate(symbol)
    ob = await v10_fetch_orderbook(symbol)

    # Spoofing
    spoof_hit, spoof_note = await v112_spoof_tespit(symbol)
    if spoof_hit:
        stats["v112_spoof_gorulen"] = int(stats.get("v112_spoof_gorulen", 0)) + 1
        if SPOOF_GUARD_BLOCK:
            stats["v112_red_spoofing"] = int(stats.get("v112_red_spoofing", 0)) + 1
            return None
        stats["v112_spoof_keserdi"] = int(stats.get("v112_spoof_keserdi", 0)) + 1

    ext = {"oi_change_pct": oi if oi is not None else 0.0,
           "funding": funding, "btc_dir": btc_4h, "btc_dir_1h": btc_1h,
           "orderbook": ob}

    score, parts, r, bayrak = v10_quality_score(side, k, gate["ms"], ext)
    if ((side == "LONG" and gate.get("trend4") == "UP") or
            (side == "SHORT" and gate.get("trend4") == "DOWN")):
        score = round(min(100.0, score + SIGNAL_SCORE_TREND_4H_BONUS), 1)
        parts["trend_4h_bonus"] = round(SIGNAL_SCORE_TREND_4H_BONUS, 1)

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
    oi_value = await fetch_okx_open_interest_value(symbol) if (LIQ_HEATMAP_ENABLED and LIQ_HEATMAP_FETCH_OI) else None
    liq_map = likidasyon_haritasi(symbol, k, oi_value or 0.0) if oi_value else {}
    if liq_map.get("clusters"):
        stats["v113_hit_liq_cluster"] = int(stats.get("v113_hit_liq_cluster", 0)) + 1
    liq_conflict, liq_note = likidasyon_cakismasi(side, entry, liq_map)

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

    atr_now = safe_float(atr(k, V10_ATR_PERIOD)[-1])
    atr_pct = (atr_now / entry * 100.0) if entry > 0 else 0.0
    volatilite = "HIGH" if atr_pct >= 3.0 else "LOW" if atr_pct <= 1.0 else "NORMAL"
    size_mult = adaptif_pozisyon_carpani(score, volatilite, session_weight)
    risk_pct = min(max(0.0, V10_RISK_PCT * size_mult), max(0.0, MAX_POSITION_RISK_PCT))
    estimated_risk_usdt = round(DEFAULT_MARGIN_USDT * risk_pct / 100.0, 2)
    notional_usdt = round(estimated_risk_usdt / max(SABIT_STOP_PCT / 100.0, 1e-9), 2)
    margin_usdt = round(notional_usdt / max(1.0, LEVERAGE), 2)

    return {"symbol": symbol, "direction": side, "entry": entry, "strategy": "V11.5_ULTRA",
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
            "volatilite": volatilite,
            "position_multiplier": round(size_mult, 3),
            "margin_usdt": margin_usdt,
            "notional_usdt": notional_usdt,
            "estimated_risk_usdt": estimated_risk_usdt,
            "effective_risk_pct": round(risk_pct, 3),
            **tgt}


def build_v10_message(sig):
    b = sig.get("bayrak") or {}
    p = sig["score_parts"]
    tag = lambda key, lbl: f"{lbl}{'✅' if b.get(key, p.get(key, 0) > 0) else '▫️'}"
    conf = " ".join([tag("order_block", "OB"), tag("fvg", "FVG"), tag("volume_profile", "VP"),
                     tag("cvd", "CVD"), tag("sweep", "Sweep"), tag("orderbook", "OBflow")])
    fund = safe_float(sig.get("funding"))
    trend_line = ("🎲 KONTROL GRUBU — yön rastgele\n" if sig.get("kontrol") else
                  ("Trend Uyumu: BTC ile AYNI YÖN ✅\n" if sig.get("trend_uyum") else
                   "Trend Uyumu: normalde geçmezdi\n"))
    _kay = safe_float(sig.get("entry_kayma_pct"))
    kayma_mark = f" (mum kapanışından %{_kay:+.2f})" if abs(_kay) >= 0.05 else ""

    # V11.5 ek bilgiler
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
    keserdi = [ad for ad, durum in (sig.get("kapi_sonuclari") or {}).items() if durum == "kesti"]
    olcum_line = f"🧪 Normalde KESERDİ: {', '.join(keserdi) if keserdi else 'yok'}\n" if OLCUM_MODU else ""

    return (f"{trend_line}"
            f"🎯 {VERSION_NAME}\n🆕 V11.5 | {sig['direction']} | {sig['symbol']}\n"
            f"Yapı: {sig['structure']} | 1H:{sig['trend_1h']} 4H:{sig['trend_4h']}\n"
            f"BTC: 1H:{sig.get('btc_1h','-')} 4H:{sig.get('btc_4h','-')}"
            + (f" | Coin 1H EMA: {sig.get('coin_1h_ema','-')}" if sig.get('coin_1h_ema') else "") + "\n"
            f"Skor: {sig['score']}/100  RSI:{sig['rsi']}\nConfluence: {conf}\n"
            + "\n".join([savunma_lines[0], vwap_line, adx_line, session_line, mtf_line, vwm_line, liq_line] +
                        savunma_lines[1:]) + "\n"
            f"{olcum_line}"
            f"Giriş: {_v10_fmt(sig['entry'])} [{sig.get('entry_kaynak','-')}]{kayma_mark}\n"
            f"Stop: {_v10_fmt(sig['stop'])} (%{sig['stop_pct']} sabit)\n"
            f"TP1 {_v10_fmt(sig['tp1'])} ({sig.get('tp1_rr', TP1_RR)}R) | TP2 {_v10_fmt(sig['tp2'])} ({sig.get('tp2_rr', TP2_RR)}R) | "
            f"TP3 {_v10_fmt(sig['tp3'])} ({sig.get('tp3_rr', TP3_RR)}R) | TP4 {_v10_fmt(sig['tp4'])} ({sig.get('tp4_rr', TP4_RR)}R)\n"
            f"Pullback: {sig['pullback']} | FOMO:%{sig['fomo_move_pct']}\n"
            f"OI%{round(safe_float(sig.get('oi_change_pct')),2)} ({sig.get('oi_yorum','-')}) Fund:{round(fund*100,4)}% OBimb:{round(safe_float(sig.get('ob_imbalance')),2)}\n"
            f"Pozisyon: {sig.get('position_multiplier',1)}x ayar | Marjin ≈{sig.get('margin_usdt',0)} USDT | Risk ≈{sig.get('estimated_risk_usdt',0)} USDT\n"
            f"⚠️ PAPER — risk %{V10_RISK_PCT}/işlem")


def build_v10_close_message(pos, R, outcome, exit_price):
    if outcome == "STOP":
        head = "❌ STOP GELDİ"
    elif outcome == "TP4":
        head = "✅ TP4 GELDİ — kademeli çıkış tamamlandı"
    elif outcome == "TIME_EXIT":
        head = "⏱ SÜRE DOLDU — kâr realize"
    else:
        head = f"🏁 {outcome}"
    return (
        f"🆕 V11.5 — POZİSYON KAPANDI\n"
        f"{head}\n"
        f"Coin: {pos['symbol']}\n"
        f"Yön: {pos['side']}\n"
        f"Giriş: {_v10_fmt(pos['entry'])}\n"
        f"Çıkış: {_v10_fmt(exit_price)}\n"
        f"Sonuç: {R:+.2f}R (skor {pos['score']})\n"
        f"Saat: {tr_str()}"
    )


def _v10_mem():
    mp = memory.setdefault("v10_paper", {"open": [], "closed": [], "buckets": {}})
    mp.setdefault("golge", [])
    return mp


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
        "orig_stop": sig["stop"],
        "tp1": sig["tp1"], "tp2": sig["tp2"], "tp3": sig["tp3"], "tp4": sig["tp4"],
        "hit1": False, "hit2": False, "hit3": False, "hit4": False,
        "notified_hits": [],
        "score": sig["score"], "event": sig["event"],
        "range_break": bool(sig.get("range_break")),
        "entry_kaynak": sig.get("entry_kaynak", "-"),
        "open_ts": time.time(), "scan_ts": 0.0, "candle_ts": sig["candle_ts"],
        "session_name": sig.get("session_name", "-"),
        "piyasa_modu": sig.get("piyasa_modu", "-"),
        "kapi_sonuclari": copy.deepcopy(sig.get("kapi_sonuclari", {})),
        "kontrol": bool(sig.get("kontrol")),
        "mfe_pct": 0.0, "mae_pct": 0.0, "current_r": 0.0,
    }
    mp["open"].append(poz)
    olcum_db_pozisyon_ac(poz)
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


def _tp_weights() -> List[float]:
    raw = [max(0.0, TP1_WEIGHT), max(0.0, TP2_WEIGHT),
           max(0.0, TP3_WEIGHT), max(0.0, TP4_WEIGHT)]
    total = sum(raw)
    return [x / total for x in raw] if total > 0 else [0.5, 0.3, 0.15, 0.05]


def _paper_realized_r(pos, stop_remaining: bool) -> float:
    weights = _tp_weights()
    rrs = [TP1_RR, TP2_RR, TP3_RR, TP4_RR]
    realized = sum(weights[i] * rrs[i] for i in range(4) if pos.get(f"hit{i + 1}"))
    remaining = sum(weights[i] for i in range(4) if not pos.get(f"hit{i + 1}"))
    return realized - remaining if stop_remaining else realized


def _paper_time_exit_r(pos, current_r: float) -> float:
    weights = _tp_weights()
    rrs = [TP1_RR, TP2_RR, TP3_RR, TP4_RR]
    realized = sum(weights[i] * rrs[i] for i in range(4) if pos.get(f"hit{i + 1}"))
    remaining = sum(weights[i] for i in range(4) if not pos.get(f"hit{i + 1}"))
    return realized + remaining * current_r


def v107_check_paper_bar(pos, hi, lo):
    side = pos["side"]
    stop_lv = safe_float(pos["orig_stop"])
    if side == "LONG":
        if lo <= stop_lv:
            return round(_paper_realized_r(pos, True), 3), "STOP"
        reached = lambda level: hi >= safe_float(pos[level])
    else:
        if hi >= stop_lv:
            return round(_paper_realized_r(pos, True), 3), "STOP"
        reached = lambda level: lo <= safe_float(pos[level])
    for idx in range(1, 5):
        if not pos.get(f"hit{idx}") and reached(f"tp{idx}"):
            pos[f"hit{idx}"] = True
            pos.setdefault("pending_hits", []).append(idx)
    if pos.get("hit4"):
        return round(_paper_realized_r(pos, False), 3), "TP4"
    return None, None


def v107_check_paper_barlar(pos, barlar):
    for r in barlar:
        R, oc = v107_check_paper_bar(pos, safe_float(r[2]), safe_float(r[3]))
        if oc:
            return R, oc
    return None, None


def v10_update_excursions(pos: Dict[str, Any], barlar: List[List[Any]]) -> None:
    entry = safe_float(pos.get("entry"))
    risk = abs(entry - safe_float(pos.get("orig_stop")))
    if entry <= 0 or not barlar:
        return
    max_hi = max(safe_float(r[2]) for r in barlar)
    min_lo = min(safe_float(r[3]) for r in barlar)
    last = safe_float(barlar[-1][4])
    if pos.get("side") == "LONG":
        favorable = max(0.0, (max_hi - entry) / entry * 100.0)
        adverse = max(0.0, (entry - min_lo) / entry * 100.0)
        move = last - entry
    else:
        favorable = max(0.0, (entry - min_lo) / entry * 100.0)
        adverse = max(0.0, (max_hi - entry) / entry * 100.0)
        move = entry - last
    pos["mfe_pct"] = round(max(safe_float(pos.get("mfe_pct")), favorable), 6)
    pos["mae_pct"] = round(max(safe_float(pos.get("mae_pct")), adverse), 6)
    pos["current_r"] = round(move / risk, 6) if risk > 0 else 0.0
    olcum_db_pozisyon_guncelle(pos)


def v10_record_closed(pos, R, outcome):
    mp = _v10_mem()
    mp["closed"].append({"symbol": pos["symbol"], "side": pos["side"], "R": round(R, 3),
                         "outcome": outcome, "hit1": bool(pos.get("hit1")),
                         "hit2": bool(pos.get("hit2")), "hit3": bool(pos.get("hit3")),
                         "hit4": bool(pos.get("hit4")),
                         "score": pos["score"], "event": pos["event"],
                         "range_break": bool(pos.get("range_break")),
                         "tutma_dk": round((time.time() - safe_float(pos.get("open_ts", 0))) / 60.0, 1),
                         "close_ts": time.time()})
    olcum_db_pozisyon_guncelle(pos, outcome, R)


def v10_cooldown_ok(symbol):
    if OLCUM_MODU:
        return True
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
    limit = OLCUM_MAX_OPEN if OLCUM_MODU else V10_MAX_OPEN
    if len(mp["open"]) >= limit:
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
        stats["last_signal"] = f"V11.5 {side} {symbol} skor {sig['score']}"
        logger.info("V11.5 SİNYAL %s %s skor=%s session=%s adx=%.1f",
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
                await asyncio.sleep(max(0.1, min(HOT_SCAN_INTERVAL_SEC, 2.0)))
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
                v10_update_excursions(pos, barlar)
                R, oc = v107_check_paper_barlar(pos, barlar)
                pending_hits = list(pos.pop("pending_hits", []))
                notified = pos.setdefault("notified_hits", [])
                for idx in pending_hits:
                    if idx in notified:
                        continue
                    notified.append(idx)
                    await safe_send_telegram(
                        f"✅ TP{idx} GELDİ | {pos['side']} | {pos['symbol']}\n"
                        f"Seviye: {_v10_fmt(pos.get(f'tp{idx}'))} | Saat: {tr_str()}"
                    )

                # Time-based exit
                if not oc and TIME_EXIT_ENABLED:
                    yas_saat = (time.time() - safe_float(pos.get("open_ts", 0))) / 3600.0
                    if yas_saat >= TIME_EXIT_HOURS:
                        son = safe_float(barlar[-1][4])
                        risk = abs(safe_float(pos["entry"]) - safe_float(pos["orig_stop"]))
                        if risk > 0:
                            kâr_move = (son - safe_float(pos["entry"])) if pos["side"] == "LONG" else (safe_float(pos["entry"]) - son)
                            kâr_r = kâr_move / risk
                            # Süre dolduğunda sonuç ne olursa olsun pozisyon kapanır.
                            R, oc = round(_paper_time_exit_r(pos, kâr_r), 3), "TIME_EXIT"

                if not oc:
                    continue
                v10_record_closed(pos, R, oc)
                if oc == "STOP" and GOLGE_IZLEME:
                    stop_ts = time.time()
                    golge = {
                        "uid": uid,
                        "symbol": pos["symbol"], "side": pos["side"],
                        "entry": pos["entry"],
                        "tp1": pos["tp1"], "tp2": pos["tp2"],
                        "tp3": pos["tp3"], "tp4": pos["tp4"],
                        "stop_ts": stop_ts, "scan_ts": 0.0,
                        "kontrol": bool(pos.get("kontrol")),
                        "golge_tp": 0, "golge_mfe_pct": 0.0,
                        "golge_mae_pct": 0.0, "golge_tp1_dk": None,
                    }
                    mp["golge"].append(golge)
                    olcum_db_golge_baslat(pos)
                exit_price = pos["orig_stop"] if oc == "STOP" else (pos["tp4"] if oc == "TP4" else safe_float(barlar[-1][4]))
                await safe_send_telegram(build_v10_close_message(pos, R, oc, exit_price))
                kapananlar.add(uid)
            if kapananlar:
                mp["open"] = [p for p in mp["open"] if v107_pos_uid(p) not in kapananlar]
        except Exception as e:
            logger.exception("v10_paper_loop hata: %s", e)
        await asyncio.sleep(max(V107_TAKIP_ARALIK_SEC, 20))


def golge_kaydi_guncelle(golge: Dict[str, Any], barlar: List[List[Any]]) -> None:
    entry = safe_float(golge.get("entry"))
    stop_ms = safe_float(golge.get("stop_ts")) * 1000.0
    scan_ms = safe_float(golge.get("scan_ts"))
    yeni_barlar = [r for r in barlar if safe_float(r[0]) > stop_ms and safe_float(r[0]) > scan_ms]
    if entry <= 0 or not yeni_barlar:
        return
    max_hi = max(safe_float(r[2]) for r in yeni_barlar)
    min_lo = min(safe_float(r[3]) for r in yeni_barlar)
    if golge.get("side") == "LONG":
        lehe = max(0.0, (max_hi - entry) / entry * 100.0)
        aleyhe = max(0.0, (entry - min_lo) / entry * 100.0)
        degdi = lambda r, seviye: safe_float(r[2]) >= seviye
    else:
        lehe = max(0.0, (entry - min_lo) / entry * 100.0)
        aleyhe = max(0.0, (max_hi - entry) / entry * 100.0)
        degdi = lambda r, seviye: safe_float(r[3]) <= seviye
    golge["golge_mfe_pct"] = round(max(safe_float(golge.get("golge_mfe_pct")), lehe), 6)
    golge["golge_mae_pct"] = round(max(safe_float(golge.get("golge_mae_pct")), aleyhe), 6)
    for idx in range(1, 5):
        seviye = safe_float(golge.get(f"tp{idx}"))
        if seviye <= 0:
            continue
        ilk_bar = next((r for r in yeni_barlar if degdi(r, seviye)), None)
        if ilk_bar is not None:
            golge["golge_tp"] = max(int(golge.get("golge_tp", 0)), idx)
            if idx == 1 and golge.get("golge_tp1_dk") is None:
                golge["golge_tp1_dk"] = round(
                    max(0.0, (safe_float(ilk_bar[0]) / 1000.0 - safe_float(golge.get("stop_ts"))) / 60.0), 3
                )
    golge["scan_ts"] = max(safe_float(r[0]) for r in yeni_barlar)


async def golge_loop() -> None:
    await asyncio.sleep(15)
    while True:
        try:
            if GOLGE_IZLEME:
                mp = _v10_mem()
                gruplar: Dict[str, List[Dict[str, Any]]] = {}
                for golge in list(mp.get("golge", [])):
                    gruplar.setdefault(str(golge.get("symbol", "")), []).append(golge)
                biten_uidler = set()
                simdi = time.time()
                for symbol, kayitlar in gruplar.items():
                    barlar = await get_klines(symbol, GOLGE_TF, 300, ttl=max(10.0, GOLGE_ARALIK_SEC * 0.8))
                    for golge in kayitlar:
                        if barlar:
                            golge_kaydi_guncelle(golge, barlar)
                        bitti = simdi >= safe_float(golge.get("stop_ts")) + max(0.0, GOLGE_SAAT) * 3600.0
                        olcum_db_golge_guncelle(golge, bitti)
                        if bitti:
                            biten_uidler.add(str(golge.get("uid", "")))
                if biten_uidler:
                    mp["golge"] = [g for g in mp.get("golge", [])
                                   if str(g.get("uid", "")) not in biten_uidler]
        except Exception as e:
            logger.exception("golge_loop hata: %s", e)
        await asyncio.sleep(max(1, GOLGE_ARALIK_SEC))


async def save_loop() -> None:
    while True:
        try:
            await save_memory_async()
        except Exception:
            pass
        await asyncio.sleep(max(20, MEMORY_SAVE_INTERVAL_SEC))


def kapi_raporu_uret() -> str:
    rows = olcum_db_satirlari()
    if not rows:
        return "🧪 KAPI LABORATUVARI\nHenüz ölçüm kaydı yok."
    lines = [f"🧪 KAPI LABORATUVARI | Toplam örnek: {len(rows)} | Min hücre: {OLCUM_MIN_HUCRE}"]
    kontrol_rows = [(safe_float(r[1]), safe_float(r[2])) for r in rows if int(r[0] or 0) == 1]
    if len(kontrol_rows) >= OLCUM_MIN_HUCRE:
        lines.append(f"🎲 Kontrol n={len(kontrol_rows)} | Ort.R {avg([x[0] for x in kontrol_rows]):+.3f} | Ort.MFE %{avg([x[1] for x in kontrol_rows]):.3f}")
    else:
        lines.append(f"🎲 Kontrol: ölçülemez (n={len(kontrol_rows)})")
    for gate in OLCUM_KAPILARI:
        lines.append(f"\n• {gate}")
        for kontrol_degeri, grup_adi in ((0, "Normal"), (1, "Kontrol")):
            cells: Dict[str, List[Tuple[float, float]]] = {"gecti": [], "kesti": []}
            for kontrol, rv, mfe, _mae, raw_json, _durum in rows:
                if int(kontrol or 0) != kontrol_degeri:
                    continue
                try:
                    durum = json.loads(raw_json or "{}").get(gate, "olcumsuz")
                except Exception:
                    durum = "olcumsuz"
                if durum in cells:
                    cells[durum].append((safe_float(rv), safe_float(mfe)))
            g, k_ = cells["gecti"], cells["kesti"]
            lines.append(f"  {grup_adi} | geçen n={len(g)} | kesen n={len(k_)}")
            if len(g) < OLCUM_MIN_HUCRE:
                lines.append(f"    Geçen: ölçülemez (n={len(g)})")
            else:
                lines.append(f"    Geçen: Ort.R {avg([x[0] for x in g]):+.3f} | Ort.MFE %{avg([x[1] for x in g]):.3f}")
            if len(k_) < OLCUM_MIN_HUCRE:
                lines.append(f"    Kesen: ölçülemez (n={len(k_)})")
            else:
                lines.append(f"    Kesen: Ort.R {avg([x[0] for x in k_]):+.3f} | Ort.MFE %{avg([x[1] for x in k_]):.3f}")
            if len(g) >= OLCUM_MIN_HUCRE and len(k_) >= OLCUM_MIN_HUCRE:
                lines.append(f"    Fark: ΔR {avg([x[0] for x in g])-avg([x[0] for x in k_]):+.3f} | ΔMFE %{avg([x[1] for x in g])-avg([x[1] for x in k_]):+.3f}")
    return "\n".join(lines)


def telegram_parcala(text: str, limit: int = 4000) -> List[str]:
    parts, current = [], ""
    for line in (text or "").splitlines(keepends=True):
        if len(line) > limit:
            if current:
                parts.append(current.rstrip())
                current = ""
            parts.extend(line[i:i + limit] for i in range(0, len(line), limit))
        elif len(current) + len(line) > limit:
            parts.append(current.rstrip())
            current = line
        else:
            current += line
    if current:
        parts.append(current.rstrip())
    return parts or [""]


def yuzdelik(values: List[float], oran: float) -> float:
    if not values:
        return 0.0
    sirali = sorted(values)
    konum = (len(sirali) - 1) * clamp(oran, 0.0, 1.0)
    alt = int(konum)
    ust = min(alt + 1, len(sirali) - 1)
    pay = konum - alt
    return sirali[alt] * (1.0 - pay) + sirali[ust] * pay


def tp_raporu_uret() -> str:
    rows = olcum_db_tp_satirlari()
    lines = ["📊 TP RAPORU"]
    for kontrol_degeri, grup_adi in ((0, "NORMAL"), (1, "KONTROL")):
        grup = [r for r in rows if int(r[0] or 0) == kontrol_degeri]
        kapali = [r for r in grup if r[4] != "ACIK"]
        acik = [r for r in grup if r[4] == "ACIK"]

        def hit_sayisi(veriler: List[Tuple[Any, ...]], idx: int) -> int:
            toplam = 0
            for row in veriler:
                try:
                    toplam += int(bool(json.loads(row[3] or "{}").get(f"_hit{idx}")))
                except Exception:
                    pass
            return toplam

        def tp_satiri(baslik: str, veriler: List[Tuple[Any, ...]]) -> str:
            n = len(veriler)
            parcalar = []
            for idx in range(1, 5):
                sayi = hit_sayisi(veriler, idx)
                yuzde = sayi / n * 100.0 if n else 0.0
                parcalar.append(f"TP{idx} {sayi} (%{yuzde:.1f})")
            return f"{baslik} n={n} | " + " | ".join(parcalar)

        mfe = [safe_float(r[1]) for r in grup]
        mae = [safe_float(r[2]) for r in grup]
        stopa_yapisan = sum(1 for x in mae if x >= 2.0)
        stoplar = [r for r in grup if r[4] == "STOP"]
        biten = [r for r in stoplar if r[5] == "BITTI"]
        golge_mfe = [safe_float(r[7]) for r in stoplar if r[5] in ("IZLENIYOR", "BITTI")]
        golge_mae = [safe_float(r[8]) for r in stoplar if r[5] in ("IZLENIYOR", "BITTI")]
        golge_tp1_dk = [safe_float(r[9]) for r in stoplar if r[9] is not None]

        lines.append(f"\n{grup_adi}")
        lines.append(tp_satiri("Kapanmış", kapali))
        lines.append(tp_satiri("Açık", acik))
        lines.append(
            f"MFE n={len(mfe)} | medyan %{yuzdelik(mfe, 0.50):.3f} | ortalama %{avg(mfe):.3f} | "
            f"p75 %{yuzdelik(mfe, 0.75):.3f} | p90 %{yuzdelik(mfe, 0.90):.3f}"
        )
        lines.append(
            f"MAE n={len(mae)} | medyan %{yuzdelik(mae, 0.50):.3f} | ortalama %{avg(mae):.3f} | "
            f"stopa yapışan {stopa_yapisan}"
        )
        lines.append("STOP SONRASI")
        lines.append(f"Stop {len(stoplar)} | İzlemesi biten {len(biten)}")
        for idx in range(1, 5):
            sayi = sum(1 for r in stoplar if int(r[6] or 0) >= idx)
            yuzde = sayi / len(stoplar) * 100.0 if stoplar else 0.0
            lines.append(f"TP{idx} {sayi} (%{yuzde:.1f})")
        lines.append(
            f"Gölge MFE n={len(golge_mfe)} | medyan %{yuzdelik(golge_mfe, 0.50):.3f} | "
            f"ortalama %{avg(golge_mfe):.3f} | p75 %{yuzdelik(golge_mfe, 0.75):.3f} | "
            f"p90 %{yuzdelik(golge_mfe, 0.90):.3f}"
        )
        lines.append(f"Gölge MAE medyan %{yuzdelik(golge_mae, 0.50):.3f}")
        lines.append(f"TP1 süresi medyan {yuzdelik(golge_tp1_dk, 0.50):.1f} dk")
    return "\n".join(lines)


async def post_init(application) -> None:
    olcum_db_init()
    if OLCUM_MODU:
        for pos in _v10_mem().get("open", []):
            saved = olcum_db_acik_durum(v107_pos_uid(pos))
            if saved:
                kontrol, rv, mfe, mae, raw_json = saved
                try:
                    pos["kapi_sonuclari"] = json.loads(raw_json or "{}")
                except Exception:
                    pos["kapi_sonuclari"] = {ad: "olcumsuz" for ad in OLCUM_KAPILARI}
                pos["kontrol"] = bool(kontrol)
                pos["current_r"] = safe_float(rv)
                pos["mfe_pct"] = safe_float(mfe)
                pos["mae_pct"] = safe_float(mae)
            else:
                pos["kapi_sonuclari"] = {ad: "olcumsuz" for ad in OLCUM_KAPILARI}
                pos["kontrol"] = False
                pos["mfe_pct"] = pos["mae_pct"] = pos["current_r"] = 0.0
                olcum_db_pozisyon_ac(pos)
    active_count, pruned_count = await refresh_coin_pool(force=True)
    olcum_kayit_sayisi = len(olcum_db_satirlari())
    olcum_db_dizin = os.path.abspath(os.path.dirname(OLCUM_DB) or ".")
    olcum_kalici_uyari = ""
    if OLCUM_MODU and (not olcum_db_dizin.startswith("/data") or not os.access(olcum_db_dizin, os.W_OK)):
        olcum_kalici_uyari = "\n⚠️ OLCUM_DB kalıcı diskte değil — deploy'da veri silinir"
    await safe_send_telegram(
        f"🚀 {VERSION_NAME} başladı\n"
        f"Saat: {tr_str()}\n"
        f"Coin sayısı: {active_count}\n"
        f"Kaldıraç: {LEVERAGE}x | Risk: %{V10_RISK_PCT}/işlem\n"
        f"TP: {TP1_RR}/{TP2_RR}/{TP3_RR}/{TP4_RR}R "
        f"(paylar %{TP1_WEIGHT*100:.0f}/%{TP2_WEIGHT*100:.0f}/%{TP3_WEIGHT*100:.0f}/%{TP4_WEIGHT*100:.0f})\n"
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
        f"\n🧪 Ölçüm modu: {'AKTİF' if OLCUM_MODU else 'kapalı'} | Kontrol oranı: %{OLCUM_RASTGELE_ORAN*100:.1f}"
        f"\nÖlçüm kaydı: {olcum_kayit_sayisi} pozisyon"
        f"{olcum_kalici_uyari}"
    )
    for _kur in (symbol_refresh_loop, v10_scan_loop, v10_paper_loop, golge_loop, save_loop):
        asyncio.create_task(_kur(), name=_kur.__name__)


async def cmd_start(update, context):
    if not telegram_yetkili(update):
        return
    await update.message.reply_text(
        f"{VERSION_NAME} aktif.\n"
        "/status - durum\n/test - test\n/v10 - motor durumu\n/coin SYMBOL - tek coin\n"
        "/kapi - kapı ölçüm raporu\n/tp - TP ve stop sonrası ölçüm raporu\n"
    )

async def cmd_test(update, context):
    if not telegram_yetkili(update):
        return
    ok = await safe_send_telegram(f"✅ Test başarılı. Saat: {tr_str()}")
    await update.message.reply_text("Gönderildi." if ok else "Başarısız.")

async def cmd_status(update, context):
    if not telegram_yetkili(update):
        return
    mp = _v10_mem()
    cl = mp["closed"]; n = len(cl)
    wins = sum(1 for x in cl if x["R"] > 0)
    ev = (sum(x["R"] for x in cl) / n) if n else 0
    lines = [
        f"📊 V11.5 ULTRA DURUM",
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
        f"  VWM: {stats.get('v113_red_vwm', 0)}",
        f"  Korelasyon: {stats.get('v113_red_correlation', 0)}",
        f"🛡 Manipülasyon:",
        f"  Spoof: {stats.get('v112_red_spoofing', 0)}",
        f"  Spoof görülen: {stats.get('v112_spoof_gorulen', 0)} | Keserdi: {stats.get('v112_spoof_keserdi', 0)}",
        f"  Wash: {stats.get('v112_red_wash', 0)}",
        f"  Pump/Dump: {stats.get('v112_red_pump_dump', 0)}",
        f"  Insider: {stats.get('v112_red_insider', 0)}",
        f"  Stop-hunt: {stats.get('v112_hit_stop_hunt', 0)}",
        f"  OKX timeout: {stats.get('okx_timeout', 0)}",
    ]
    await update.message.reply_text("\n".join(lines))

async def cmd_coin(update, context):
    if not telegram_yetkili(update):
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /coin BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    res = await analyze_v10_symbol(symbol)
    if not res:
        await update.message.reply_text(f"{symbol} için V11.5 sinyali yok.")
        return
    await update.message.reply_text(build_v10_message(res))

async def cmd_v10(update, context):
    if not telegram_yetkili(update):
        return
    mp = _v10_mem()
    lines = [
        f"🆕 V11.5 ULTRA motor durumu",
        f"Açık: {len(mp['open'])} | Sinyal: {stats.get('v10_signals', 0)}",
        f"Session: {session_belirle()[0]}",
        f"VWAP: {'AKTİF' if VWAP_ENABLED else 'kapalı'} | ADX: {'AKTİF' if ADX_ENABLED else 'kapalı'}",
        f"Likidite: {'AKTİF' if LIQ_HEATMAP_ENABLED else 'kapalı'} | MTF: {'AKTİF' if MTF_CONFLUENCE_ENABLED else 'kapalı'}",
        f"Red: vwap={stats.get('v113_red_vwap',0)} session={stats.get('v113_red_session',0)} mtf={stats.get('v113_red_mtf',0)} "
        f"vwm={stats.get('v113_red_vwm',0)} kor={stats.get('v113_red_correlation',0)}",
    ]
    if mp["open"]:
        lines.append("— Açık —")
        for p in mp["open"][:10]:
            yas = round((time.time() - safe_float(p.get("open_ts", 0))) / 60.0)
            lines.append(f"{p['side']} {p['symbol']} skor {p['score']} seans {p.get('session_name','-')} ({yas}dk)")
    await update.message.reply_text("\n".join(lines))


async def cmd_kapi(update, context):
    if not telegram_yetkili(update):
        return
    try:
        rapor = await asyncio.to_thread(kapi_raporu_uret)
        for parca in telegram_parcala(rapor, 4000):
            await update.message.reply_text(parca)
    except Exception as e:
        logger.exception("/kapi rapor hatası: %s", e)
        await update.message.reply_text("Kapı raporu hazırlanamadı.")


async def cmd_tp(update, context):
    if not telegram_yetkili(update):
        return
    try:
        rapor = await asyncio.to_thread(tp_raporu_uret)
        for parca in telegram_parcala(rapor, 4000):
            await update.message.reply_text(parca)
    except Exception as e:
        logger.exception("/tp rapor hatası: %s", e)
        await update.message.reply_text("TP raporu hazırlanamadı.")


def telegram_yetkili(update: Update) -> bool:
    chat = getattr(update, "effective_chat", None)
    return bool(chat and str(chat.id) == str(TELEGRAM_CHAT_ID))


def build_app():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("coin", cmd_coin))
    app.add_handler(CommandHandler("v10", cmd_v10))
    app.add_handler(CommandHandler("kapi", cmd_kapi))
    app.add_handler(CommandHandler("tp", cmd_tp))
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
