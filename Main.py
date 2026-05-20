#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║     BALİNA AVCISI V6.0 - WHALE EYE PRO                 ║
║     Open Interest + Funding Rate + Spoofing Motorlu     ║
║     Gerçek Balina Takip Sistemi                         ║
║     6 Aylık Emeğin Zirvesi                              ║
╚══════════════════════════════════════════════════════════╝

YENİ MOTORLAR (V6.0):
  - OPEN INTEREST DELTA: Fiyat-OI uyumsuzluğu balina izi
  - FUNDING RATE DEDEKTÖRÜ: Aşırı fonlama ters işlem sinyali
  - ORDERBOOK SPOOFING: Sahte emir duvarı tespiti
  - CVD (Cumulative Volume Delta): Agresif alış/satış dengesi
"""

import signal
import copy
import os
import json
import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import hmac
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# =========================================================
# VERSİYON
# =========================================================
VERSION_NAME = "Balina Avcısı V5.2.7.4 PRO WS - HELAL FİLTRE - 200 COIN HAVUZ + ERKEN GİRİŞ BÖLGESİ V7"

# =========================================================
# ENV / AYARLAR
# =========================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Binance API (YENI - OI ve Funding için)
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "").strip()
BINANCE_FAPI_BASE = os.getenv("BINANCE_FAPI_BASE", "https://fapi.binance.com").strip().rstrip("/")
BINANCE_DAPI_BASE = os.getenv("BINANCE_DAPI_BASE", "https://dapi.binance.com").strip().rstrip("/")
BINANCE_SPOT_BASE = os.getenv("BINANCE_SPOT_BASE", "https://api.binance.com").strip().rstrip("/")

OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com").strip().rstrip("/")
OKX_INST_TYPE = os.getenv("OKX_INST_TYPE", "SWAP").strip().upper()

BINANCE_CONFIRM_ENABLED = os.getenv("BINANCE_CONFIRM_ENABLED", "true").lower() == "true"
BINANCE_CONFIRM_REQUIRED = os.getenv("BINANCE_CONFIRM_REQUIRED", "false").lower() == "true"
BINANCE_CONFIRM_BASE_URL = os.getenv("BINANCE_CONFIRM_BASE_URL", "https://data-api.binance.vision").strip().rstrip("/")
BINANCE_CONFIRM_SCORE_PASS = float(os.getenv("BINANCE_CONFIRM_SCORE_PASS", "11"))
BINANCE_CONFIRM_SCORE_SOFT = float(os.getenv("BINANCE_CONFIRM_SCORE_SOFT", "7"))
BINANCE_CONFIRM_FAIL_OPEN_SCORE = float(os.getenv("BINANCE_CONFIRM_FAIL_OPEN_SCORE", "80"))
MAX_BINANCE_OKX_PRICE_GAP_PCT = float(os.getenv("MAX_BINANCE_OKX_PRICE_GAP_PCT", "0.40"))
HARD_BINANCE_OKX_PRICE_GAP_PCT = float(os.getenv("HARD_BINANCE_OKX_PRICE_GAP_PCT", "0.80"))

MEMORY_FILE = os.getenv("MEMORY_FILE", "balina_avcisi_v6_memory.json").strip()
LOG_FILE = os.getenv("LOG_FILE", "balina_avcisi_v6.log").strip()
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Istanbul").strip()

AUTO_START_MESSAGE = os.getenv("AUTO_START_MESSAGE", "true").lower() == "true"
AUTO_HEARTBEAT = os.getenv("AUTO_HEARTBEAT", "false").lower() == "true"
HEARTBEAT_INTERVAL_SEC = int(float(os.getenv("HEARTBEAT_INTERVAL_SEC", "7200")))
HOT_SCAN_INTERVAL_SEC = float(os.getenv("HOT_SCAN_INTERVAL_SEC", "1.5"))
DEEP_SCAN_INTERVAL_SEC = float(os.getenv("DEEP_SCAN_INTERVAL_SEC", "2"))
MEMORY_SAVE_INTERVAL_SEC = int(float(os.getenv("MEMORY_SAVE_INTERVAL_SEC", "60")))
FOLLOWUP_CHECK_INTERVAL_SEC = int(float(os.getenv("FOLLOWUP_CHECK_INTERVAL_SEC", "300")))
FOLLOWUP_DELAY_SEC = int(float(os.getenv("FOLLOWUP_DELAY_SEC", "7200")))
HOT_TTL_SEC = int(float(os.getenv("HOT_TTL_SEC", "1800")))
ALERT_COOLDOWN_MIN = int(float(os.getenv("ALERT_COOLDOWN_MIN", "150")))
SETUP_COOLDOWN_MIN = int(float(os.getenv("SETUP_COOLDOWN_MIN", "90")))
MAX_HOT_CANDIDATES = int(float(os.getenv("MAX_HOT_CANDIDATES", "60")))
MAX_DEEP_ANALYSIS_PER_CYCLE = int(float(os.getenv("MAX_DEEP_ANALYSIS_PER_CYCLE", "60")))

MIN_CANDIDATE_SCORE = float(os.getenv("MIN_CANDIDATE_SCORE", "29"))
MIN_READY_SCORE = float(os.getenv("MIN_READY_SCORE", "44"))
MIN_SIGNAL_SCORE = float(os.getenv("MIN_SIGNAL_SCORE", "55"))
MIN_VERIFY_SCORE_FOR_SIGNAL = float(os.getenv("MIN_VERIFY_SCORE_FOR_SIGNAL", "21"))
MIN_QUALITY_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "5.5"))
DAILY_SHORT_TOTAL_LIMIT = int(float(os.getenv("DAILY_SHORT_TOTAL_LIMIT", "7")))
MAX_SIGNAL_PER_SCAN = int(float(os.getenv("MAX_SIGNAL_PER_SCAN", "1")))
SIGNAL_SPACING_SEC = int(float(os.getenv("SIGNAL_SPACING_SEC", "0")))
# SIGNAL_SPACING_SEC=0 olsa bile hot/deep döngüleri aynı anda sinyal basmasın diye iç koruma.
INTERNAL_SIGNAL_SPACING_SEC = float(os.getenv("INTERNAL_SIGNAL_SPACING_SEC", "2.0"))
WHY_HISTORY_LIMIT = int(float(os.getenv("WHY_HISTORY_LIMIT", "30")))
WHY_ACTIVE_TTL_SEC = int(float(os.getenv("WHY_ACTIVE_TTL_SEC", "7200")))
WHY_SHOW_ONLY_BEST_PER_SYMBOL = os.getenv("WHY_SHOW_ONLY_BEST_PER_SYMBOL", "true").lower() == "true"
WHY_MIN_NEAR_MISS_RATIO = float(os.getenv("WHY_MIN_NEAR_MISS_RATIO", "0.45"))
WHY_HIDE_EMPTY_IGNORE = os.getenv("WHY_HIDE_EMPTY_IGNORE", "true").lower() == "true"

# =========================================================
# YENI MOTOR AYARLARI - V6 WHALE EYE
# =========================================================

# --- OPEN INTEREST MOTORU ---
OI_ENGINE_ENABLED = os.getenv("OI_ENGINE_ENABLED", "true").lower() == "true"
OI_SHORT_MIN_DIVERGENCE_SCORE = float(os.getenv("OI_SHORT_MIN_DIVERGENCE_SCORE", "6.0"))
OI_LONG_MIN_DIVERGENCE_SCORE = float(os.getenv("OI_LONG_MIN_DIVERGENCE_SCORE", "6.0"))
OI_DELTA_LOOKBACK_MIN = int(float(os.getenv("OI_DELTA_LOOKBACK_MIN", "15")))
OI_CACHE_SEC = int(float(os.getenv("OI_CACHE_SEC", "30")))
OI_MIN_CHANGE_PCT = float(os.getenv("OI_MIN_CHANGE_PCT", "0.45"))
OI_BEARISH_PRICE_DROP_PCT = float(os.getenv("OI_BEARISH_PRICE_DROP_PCT", "0.30"))
OI_BULLISH_PRICE_RISE_PCT = float(os.getenv("OI_BULLISH_PRICE_RISE_PCT", "0.30"))

# --- FUNDING RATE MOTORU ---
FUNDING_ENGINE_ENABLED = os.getenv("FUNDING_ENGINE_ENABLED", "true").lower() == "true"
FUNDING_SHORT_THRESHOLD = float(os.getenv("FUNDING_SHORT_THRESHOLD", "0.0500"))
FUNDING_LONG_THRESHOLD = float(os.getenv("FUNDING_LONG_THRESHOLD", "-0.0300"))
FUNDING_CACHE_SEC = int(float(os.getenv("FUNDING_CACHE_SEC", "60")))
FUNDING_SHORT_BONUS = float(os.getenv("FUNDING_SHORT_BONUS", "8.0"))
FUNDING_LONG_BONUS = float(os.getenv("FUNDING_LONG_BONUS", "8.0"))
FUNDING_EXTREME_SHORT_BONUS = float(os.getenv("FUNDING_EXTREME_SHORT_BONUS", "14.0"))
FUNDING_EXTREME_LONG_BONUS = float(os.getenv("FUNDING_EXTREME_LONG_BONUS", "14.0"))
FUNDING_EXTREME_THRESHOLD = float(os.getenv("FUNDING_EXTREME_THRESHOLD", "0.1000"))

# --- ORDERBOOK SPOOFING MOTORU ---
SPOOFING_ENGINE_ENABLED = os.getenv("SPOOFING_ENGINE_ENABLED", "true").lower() == "true"
SPOOFING_CACHE_SEC = float(os.getenv("SPOOFING_CACHE_SEC", "1.5"))
SPOOFING_MIN_WALL_SIZE_MULT = float(os.getenv("SPOOFING_MIN_WALL_SIZE_MULT", "3.0"))
SPOOFING_WALL_VANISH_SEC = float(os.getenv("SPOOFING_WALL_VANISH_SEC", "3.0"))
SPOOFING_SHORT_SCORE_BONUS = float(os.getenv("SPOOFING_SHORT_SCORE_BONUS", "5.0"))
SPOOFING_LONG_SCORE_BONUS = float(os.getenv("SPOOFING_LONG_SCORE_BONUS", "5.0"))

# --- CVD (Cumulative Volume Delta) MOTORU ---
CVD_ENGINE_ENABLED = os.getenv("CVD_ENGINE_ENABLED", "true").lower() == "true"
CVD_CACHE_SEC = int(float(os.getenv("CVD_CACHE_SEC", "15")))
CVD_LOOKBACK_MIN = int(float(os.getenv("CVD_LOOKBACK_MIN", "30")))
CVD_SHORT_DIVERGENCE_SCORE = float(os.getenv("CVD_SHORT_DIVERGENCE_SCORE", "3.0"))
CVD_LONG_DIVERGENCE_SCORE = float(os.getenv("CVD_LONG_DIVERGENCE_SCORE", "3.0"))

ONE_ACTIVE_TRADE_MODE = os.getenv("ONE_ACTIVE_TRADE_MODE", "false").lower() == "true"
ACTIVE_TRADE_BLOCK_SEC = int(float(os.getenv("ACTIVE_TRADE_BLOCK_SEC", "0")))
SCORE_OVERRIDE_GAP = float(os.getenv("SCORE_OVERRIDE_GAP", "12"))
PRICE_OVERRIDE_MOVE_PCT = float(os.getenv("PRICE_OVERRIDE_MOVE_PCT", "0.90"))
TREND_GUARD_ENABLED = os.getenv("TREND_GUARD_ENABLED", "true").lower() == "true"
TREND_GUARD_MIN_PUMP_10M = float(os.getenv("TREND_GUARD_MIN_PUMP_10M", "0.90"))
TREND_GUARD_MIN_PUMP_20M = float(os.getenv("TREND_GUARD_MIN_PUMP_20M", "1.35"))
TREND_GUARD_MIN_RSI_1M = float(os.getenv("TREND_GUARD_MIN_RSI_1M", "60"))
TREND_GUARD_MIN_RSI_5M = float(os.getenv("TREND_GUARD_MIN_RSI_5M", "57"))
TREND_GUARD_SCORE_BLOCK = float(os.getenv("TREND_GUARD_SCORE_BLOCK", "6.5"))
TREND_BREAKDOWN_MIN_SCORE = float(os.getenv("TREND_BREAKDOWN_MIN_SCORE", "6.5"))
TREND_WATCH_TTL_SEC = int(float(os.getenv("TREND_WATCH_TTL_SEC", "3600")))
MIN_RED_CANDLES_FOR_SHORT = int(float(os.getenv("MIN_RED_CANDLES_FOR_SHORT", "1")))

SHORT_STOP_ATR_MULT = float(os.getenv("SHORT_STOP_ATR_MULT", "2.55"))
SHORT_STOP_WICK_ATR_BUFFER = float(os.getenv("SHORT_STOP_WICK_ATR_BUFFER", "0.75"))
SHORT_MIN_STOP_PCT = float(os.getenv("SHORT_MIN_STOP_PCT", "0.80"))
SHORT_MAX_STOP_PCT = float(os.getenv("SHORT_MAX_STOP_PCT", "3.20"))
SHORT_TP1_R_MULT = float(os.getenv("SHORT_TP1_R_MULT", "1.20"))
SHORT_TP2_R_MULT = float(os.getenv("SHORT_TP2_R_MULT", "1.75"))
SHORT_TP3_R_MULT = float(os.getenv("SHORT_TP3_R_MULT", "2.55"))
MIN_RR_TP1 = float(os.getenv("MIN_RR_TP1", "0.90"))

BREAKDOWN_ASSIST_ENABLED = os.getenv("BREAKDOWN_ASSIST_ENABLED", "true").lower() == "true"
BREAKDOWN_ASSIST_MIN_SCORE = float(os.getenv("BREAKDOWN_ASSIST_MIN_SCORE", "6.2"))
BREAKDOWN_ASSIST_STRONG_SCORE = float(os.getenv("BREAKDOWN_ASSIST_STRONG_SCORE", "8.2"))
BREAKDOWN_ASSIST_CANDIDATE_FLOOR = float(os.getenv("BREAKDOWN_ASSIST_CANDIDATE_FLOOR", "26"))
BREAKDOWN_ASSIST_READY_FLOOR = float(os.getenv("BREAKDOWN_ASSIST_READY_FLOOR", "44"))
BREAKDOWN_ASSIST_VERIFY_BONUS = float(os.getenv("BREAKDOWN_ASSIST_VERIFY_BONUS", "3"))
BREAKDOWN_ASSIST_STRONG_VERIFY_BONUS = float(os.getenv("BREAKDOWN_ASSIST_STRONG_VERIFY_BONUS", "5"))

GORUNMEYEN_YUZ_ENABLED = os.getenv("GORUNMEYEN_YUZ_ENABLED", "true").lower() == "true"
GORUNMEYEN_YUZ_REQUIRE_FOR_SIGNAL = os.getenv("GORUNMEYEN_YUZ_REQUIRE_FOR_SIGNAL", "true").lower() == "true"
GORUNMEYEN_YUZ_ALLOW_RISKY_SCALP = os.getenv("GORUNMEYEN_YUZ_ALLOW_RISKY_SCALP", "true").lower() == "true"
GORUNMEYEN_YUZ_MIN_CLEAN_SCORE = float(os.getenv("GORUNMEYEN_YUZ_MIN_CLEAN_SCORE", "72"))
GORUNMEYEN_YUZ_MIN_SCALP_SCORE = float(os.getenv("GORUNMEYEN_YUZ_MIN_SCALP_SCORE", "58"))
GORUNMEYEN_YUZ_MIN_WATCH_SCORE = float(os.getenv("GORUNMEYEN_YUZ_MIN_WATCH_SCORE", "43"))
GORUNMEYEN_YUZ_MIN_DROP_FROM_PEAK = float(os.getenv("GORUNMEYEN_YUZ_MIN_DROP_FROM_PEAK", "0.08"))
GORUNMEYEN_YUZ_MAX_DROP_FROM_PEAK = float(os.getenv("GORUNMEYEN_YUZ_MAX_DROP_FROM_PEAK", "1.15"))
GORUNMEYEN_YUZ_TOO_LATE_DROP = float(os.getenv("GORUNMEYEN_YUZ_TOO_LATE_DROP", "1.45"))
GORUNMEYEN_YUZ_MIN_RR_TP1 = float(os.getenv("GORUNMEYEN_YUZ_MIN_RR_TP1", "0.80"))
GORUNMEYEN_YUZ_ORDERBOOK_ENABLED = os.getenv("GORUNMEYEN_YUZ_ORDERBOOK_ENABLED", "true").lower() == "true"
GORUNMEYEN_YUZ_TRADES_ENABLED = os.getenv("GORUNMEYEN_YUZ_TRADES_ENABLED", "true").lower() == "true"
GORUNMEYEN_YUZ_FLOW_PREFILTER_SCORE = float(os.getenv("GORUNMEYEN_YUZ_FLOW_PREFILTER_SCORE", "35"))
GORUNMEYEN_YUZ_BINANCE_FAIL_OVERRIDE = os.getenv("GORUNMEYEN_YUZ_BINANCE_FAIL_OVERRIDE", "true").lower() == "true"
GORUNMEYEN_YUZ_BOOK_CACHE_SEC = float(os.getenv("GORUNMEYEN_YUZ_BOOK_CACHE_SEC", "2.0"))
GORUNMEYEN_YUZ_TRADE_CACHE_SEC = float(os.getenv("GORUNMEYEN_YUZ_TRADE_CACHE_SEC", "2.0"))

TEPE_ERKEN_MOD_ENABLED = os.getenv("TEPE_ERKEN_MOD_ENABLED", "true").lower() == "true"
TEPE_ERKEN_MIN_PUMP_20M = float(os.getenv("TEPE_ERKEN_MIN_PUMP_20M", "0.85"))
TEPE_ERKEN_MIN_PUMP_1H = float(os.getenv("TEPE_ERKEN_MIN_PUMP_1H", "1.20"))
TEPE_ERKEN_MIN_DROP_FROM_PEAK = float(os.getenv("TEPE_ERKEN_MIN_DROP_FROM_PEAK", "0.03"))
TEPE_ERKEN_MAX_DROP_FROM_PEAK = float(os.getenv("TEPE_ERKEN_MAX_DROP_FROM_PEAK", "1.05"))
TEPE_ERKEN_TOO_LATE_DROP = float(os.getenv("TEPE_ERKEN_TOO_LATE_DROP", "1.45"))
TEPE_ERKEN_MAX_PEAK_AGE_CANDLES = int(float(os.getenv("TEPE_ERKEN_MAX_PEAK_AGE_CANDLES", "14")))
TEPE_ERKEN_MIN_EXIT_SCORE = float(os.getenv("TEPE_ERKEN_MIN_EXIT_SCORE", "8.0"))
TEPE_ERKEN_BLOCK_LOCAL_LOW_BOUNCE = float(os.getenv("TEPE_ERKEN_BLOCK_LOCAL_LOW_BOUNCE", "0.25"))

RISKY_SCALP_CLOSE_TP_ENABLED = os.getenv("RISKY_SCALP_CLOSE_TP_ENABLED", "true").lower() == "true"
RISKY_SCALP_TP1_PCT = float(os.getenv("RISKY_SCALP_TP1_PCT", "0.45"))
RISKY_SCALP_TP2_PCT = float(os.getenv("RISKY_SCALP_TP2_PCT", "0.65"))
RISKY_SCALP_TP3_PCT = float(os.getenv("RISKY_SCALP_TP3_PCT", "0.90"))
RISKY_SCALP_MIN_RR_TP1 = float(os.getenv("RISKY_SCALP_MIN_RR_TP1", "0.35"))

CLOSE_CONFIRM_GATE_ENABLED = os.getenv("CLOSE_CONFIRM_GATE_ENABLED", "true").lower() == "true"
CLOSE_CONFIRM_REQUIRE_5M = os.getenv("CLOSE_CONFIRM_REQUIRE_5M", "true").lower() == "true"
CLOSE_CONFIRM_REQUIRE_15M = os.getenv("CLOSE_CONFIRM_REQUIRE_15M", "false").lower() == "true"
CLOSE_CONFIRM_MIN_5M_SCORE = float(os.getenv("CLOSE_CONFIRM_MIN_5M_SCORE", "1.8"))
CLOSE_CONFIRM_MIN_15M_SCORE = float(os.getenv("CLOSE_CONFIRM_MIN_15M_SCORE", "2.0"))
CLOSE_CONFIRM_CLEAN_5M_SCORE = float(os.getenv("CLOSE_CONFIRM_CLEAN_5M_SCORE", "5.0"))
CLOSE_CONFIRM_CLEAN_15M_SCORE = float(os.getenv("CLOSE_CONFIRM_CLEAN_15M_SCORE", "2.4"))

ICT_ENGINE_ENABLED = os.getenv("ICT_ENGINE_ENABLED", "true").lower() == "true"
LONG_ENGINE_ENABLED = os.getenv("LONG_ENGINE_ENABLED", "true").lower() == "true"
SHORT_ICT_CONTEXT_ENABLED = os.getenv("SHORT_ICT_CONTEXT_ENABLED", "true").lower() == "true"

ICT_SWING_LOOKBACK_5M = int(float(os.getenv("ICT_SWING_LOOKBACK_5M", "72")))
ICT_LIQUIDITY_LOOKBACK_1M = int(float(os.getenv("ICT_LIQUIDITY_LOOKBACK_1M", "24")))
ICT_DISCOUNT_FIB_LOW = float(os.getenv("ICT_DISCOUNT_FIB_LOW", "0.50"))
ICT_DISCOUNT_FIB_HIGH = float(os.getenv("ICT_DISCOUNT_FIB_HIGH", "0.618"))
ICT_PREMIUM_FIB_LOW = float(os.getenv("ICT_PREMIUM_FIB_LOW", "0.382"))
ICT_PREMIUM_FIB_HIGH = float(os.getenv("ICT_PREMIUM_FIB_HIGH", "0.50"))
ICT_ZONE_TOLERANCE_PCT = float(os.getenv("ICT_ZONE_TOLERANCE_PCT", "0.18"))
ICT_MIN_RANGE_PCT = float(os.getenv("ICT_MIN_RANGE_PCT", "1.10"))
ICT_MIN_SWEEP_PCT = float(os.getenv("ICT_MIN_SWEEP_PCT", "0.03"))
ICT_MIN_CHOCH_SCORE = float(os.getenv("ICT_MIN_CHOCH_SCORE", "5.0"))
ICT_MIN_FVG_BODY_ATR = float(os.getenv("ICT_MIN_FVG_BODY_ATR", "0.75"))

ICT_PRO_MODE_ENABLED = os.getenv("ICT_PRO_MODE_ENABLED", "true").lower() == "true"
ICT_PIVOT_LEFT = int(float(os.getenv("ICT_PIVOT_LEFT", "2")))
ICT_PIVOT_RIGHT = int(float(os.getenv("ICT_PIVOT_RIGHT", "2")))
ICT_EQUAL_LEVEL_TOLERANCE_PCT = float(os.getenv("ICT_EQUAL_LEVEL_TOLERANCE_PCT", "0.08"))
ICT_ORDER_BLOCK_LOOKBACK = int(float(os.getenv("ICT_ORDER_BLOCK_LOOKBACK", "28")))
ICT_FVG_LOOKBACK = int(float(os.getenv("ICT_FVG_LOOKBACK", "36")))
ICT_MIN_DISPLACEMENT_ATR = float(os.getenv("ICT_MIN_DISPLACEMENT_ATR", "1.05"))
ICT_MAX_OB_DISTANCE_PCT = float(os.getenv("ICT_MAX_OB_DISTANCE_PCT", "1.10"))
ICT_MAX_FVG_DISTANCE_PCT = float(os.getenv("ICT_MAX_FVG_DISTANCE_PCT", "1.20"))
ICT_SHORT_MIN_PRO_SCORE = float(os.getenv("ICT_SHORT_MIN_PRO_SCORE", "8.0"))
ICT_LONG_MIN_PRO_SCORE = float(os.getenv("ICT_LONG_MIN_PRO_SCORE", "8.0"))
ICT_REQUIRE_PRO_CONTEXT_FOR_SIGNAL = os.getenv("ICT_REQUIRE_PRO_CONTEXT_FOR_SIGNAL", "false").lower() == "true"
ICT_KILLZONE_ENABLED = os.getenv("ICT_KILLZONE_ENABLED", "true").lower() == "true"
ICT_LONDON_KILLZONE_START = int(float(os.getenv("ICT_LONDON_KILLZONE_START", "10")))
ICT_LONDON_KILLZONE_END = int(float(os.getenv("ICT_LONDON_KILLZONE_END", "13")))
ICT_NY_KILLZONE_START = int(float(os.getenv("ICT_NY_KILLZONE_START", "15")))
ICT_NY_KILLZONE_END = int(float(os.getenv("ICT_NY_KILLZONE_END", "19")))

LONG_DAILY_TOTAL_LIMIT = int(float(os.getenv("LONG_DAILY_TOTAL_LIMIT", "7")))
LONG_MIN_CANDIDATE_SCORE = float(os.getenv("LONG_MIN_CANDIDATE_SCORE", "24"))
LONG_MIN_READY_SCORE = float(os.getenv("LONG_MIN_READY_SCORE", "30"))
LONG_MIN_SIGNAL_SCORE = float(os.getenv("LONG_MIN_SIGNAL_SCORE", "74"))
LONG_MIN_VERIFY_SCORE = float(os.getenv("LONG_MIN_VERIFY_SCORE", "22"))
LONG_MIN_QUALITY_SCORE = float(os.getenv("LONG_MIN_QUALITY_SCORE", "6.0"))
LONG_MIN_DROP_20M = float(os.getenv("LONG_MIN_DROP_20M", "0.55"))
LONG_MIN_DROP_1H = float(os.getenv("LONG_MIN_DROP_1H", "1.10"))
LONG_MAX_BOUNCE_FROM_LOW_PCT = float(os.getenv("LONG_MAX_BOUNCE_FROM_LOW_PCT", "1.35"))
LONG_MIN_BUY_TO_SELL = float(os.getenv("LONG_MIN_BUY_TO_SELL", "1.18"))
LONG_MIN_5M_CONFIRM_SCORE = float(os.getenv("LONG_MIN_5M_CONFIRM_SCORE", "3.0"))
LONG_MIN_15M_CONFIRM_SCORE = float(os.getenv("LONG_MIN_15M_CONFIRM_SCORE", "0.5"))
LONG_REQUIRE_5M_CONFIRM = os.getenv("LONG_REQUIRE_5M_CONFIRM", "true").lower() == "true"
LONG_REQUIRE_15M_CONFIRM = os.getenv("LONG_REQUIRE_15M_CONFIRM", "false").lower() == "true"
LONG_STOP_ATR_MULT = float(os.getenv("LONG_STOP_ATR_MULT", "2.10"))
LONG_STOP_WICK_ATR_BUFFER = float(os.getenv("LONG_STOP_WICK_ATR_BUFFER", "0.55"))
LONG_MIN_STOP_PCT = float(os.getenv("LONG_MIN_STOP_PCT", "0.55"))
LONG_MAX_STOP_PCT = float(os.getenv("LONG_MAX_STOP_PCT", "3.10"))
LONG_TP1_R_MULT = float(os.getenv("LONG_TP1_R_MULT", "1.15"))
LONG_TP2_R_MULT = float(os.getenv("LONG_TP2_R_MULT", "1.75"))
LONG_TP3_R_MULT = float(os.getenv("LONG_TP3_R_MULT", "2.50"))
LONG_MIN_RR_TP1 = float(os.getenv("LONG_MIN_RR_TP1", "1.05"))

# =========================================================
# ERKEN GİRİŞ BÖLGESİ MOTORU V7
# Amaç: Sinyali engellemek değil, SHORT'u kırmızı mumun üst/başlangıç
# bölgesinde; LONG'u yeşil dönüş mumunun alt/başlangıç bölgesinde yakalamaktır.
# Geç kalmış mum dibi/tepe kovalamaları dışarı AL olarak gönderilmez.
# =========================================================
ENTRY_LOCATION_GUARD_ENABLED = os.getenv("ENTRY_LOCATION_GUARD_ENABLED", "true").lower() == "true"
ENTRY_LOCATION_BONUS_ENABLED = os.getenv("ENTRY_LOCATION_BONUS_ENABLED", "true").lower() == "true"
ENTRY_LOCATION_LATE_BLOCK_ENABLED = os.getenv("ENTRY_LOCATION_LATE_BLOCK_ENABLED", "true").lower() == "true"
ENTRY_LOCATION_TF = os.getenv("ENTRY_LOCATION_TF", "15m").strip().lower()

# SHORT: kırmızı/reddeden mumun üst/başlangıç bölgesi
SHORT_ENTRY_UPPER_START_MIN_POS = float(os.getenv("SHORT_ENTRY_UPPER_START_MIN_POS", "0.52"))
SHORT_ENTRY_LATE_LOW_MAX_POS = float(os.getenv("SHORT_ENTRY_LATE_LOW_MAX_POS", "0.38"))
SHORT_ENTRY_MIN_REJECTION_WICK = float(os.getenv("SHORT_ENTRY_MIN_REJECTION_WICK", "0.18"))
SHORT_ENTRY_CANDIDATE_BONUS = float(os.getenv("SHORT_ENTRY_CANDIDATE_BONUS", "4"))
SHORT_ENTRY_READY_BONUS = float(os.getenv("SHORT_ENTRY_READY_BONUS", "7"))
SHORT_ENTRY_VERIFY_BONUS = float(os.getenv("SHORT_ENTRY_VERIFY_BONUS", "4"))

# LONG: yeşil/dönen mumun alt/başlangıç bölgesi
LONG_ENTRY_LOWER_START_MAX_POS = float(os.getenv("LONG_ENTRY_LOWER_START_MAX_POS", "0.48"))
LONG_ENTRY_LATE_HIGH_MIN_POS = float(os.getenv("LONG_ENTRY_LATE_HIGH_MIN_POS", "0.68"))
LONG_ENTRY_MIN_LOWER_WICK = float(os.getenv("LONG_ENTRY_MIN_LOWER_WICK", "0.18"))
LONG_ENTRY_CANDIDATE_BONUS = float(os.getenv("LONG_ENTRY_CANDIDATE_BONUS", "5"))
LONG_ENTRY_READY_BONUS = float(os.getenv("LONG_ENTRY_READY_BONUS", "8"))
LONG_ENTRY_VERIFY_BONUS = float(os.getenv("LONG_ENTRY_VERIFY_BONUS", "4"))


# ALGO örneği düzeltmesi: BEARISH yapı + satıcı akışı + zayıf hacim varken
# ICT discount/FVG/OB tek başına LONG AL üretemez.
LONG_BEARISH_CONTEXT_HARD_BLOCK_ENABLED = os.getenv("LONG_BEARISH_CONTEXT_HARD_BLOCK_ENABLED", "true").lower() == "true"
LONG_SELL_TO_BUY_HARD_BLOCK = float(os.getenv("LONG_SELL_TO_BUY_HARD_BLOCK", "1.20"))
LONG_WEAK_VOL_1M_BLOCK = float(os.getenv("LONG_WEAK_VOL_1M_BLOCK", "0.40"))
LONG_WEAK_VOL_5M_BLOCK = float(os.getenv("LONG_WEAK_VOL_5M_BLOCK", "0.25"))
LONG_REQUIRE_TRUE_STRUCTURE_UP = os.getenv("LONG_REQUIRE_TRUE_STRUCTURE_UP", "true").lower() == "true"

FIXED_TP1_PCT = float(os.getenv("FIXED_TP1_PCT", "1.0"))
FIXED_TP2_PCT = float(os.getenv("FIXED_TP2_PCT", "1.5"))
FIXED_TP3_PCT = float(os.getenv("FIXED_TP3_PCT", "2.0"))

# =========================================================
# MA7 / MA25 KESİŞİM GİRİŞ MOTORU V9
# Kullanıcı kuralı:
# - SHORT: 1m MA7 yukarıdan aşağı MA25'i tam kestiği yerde sinyal.
# - LONG: 1m MA7 aşağıdan yukarı MA25'i tam kestiği yerde sinyal.
# - 15m çizgilerin kesişmesine/dokunmasına gerek yok; sadece yön doğru olacak.
# - Stop her coinde sabit %0.80 kabul edilecek.
# =========================================================
MA_CROSS_ENTRY_ENABLED = os.getenv("MA_CROSS_ENTRY_ENABLED", "true").lower() == "true"
MA_CROSS_FAST_PERIOD = int(float(os.getenv("MA_CROSS_FAST_PERIOD", "7")))
MA_CROSS_SLOW_PERIOD = int(float(os.getenv("MA_CROSS_SLOW_PERIOD", "25")))
MA_CROSS_REQUIRE_15M_DIRECTION = os.getenv("MA_CROSS_REQUIRE_15M_DIRECTION", "true").lower() == "true"
MA_CROSS_SIGNAL_BONUS = float(os.getenv("MA_CROSS_SIGNAL_BONUS", "18"))
MA_CROSS_VERIFY_BONUS = float(os.getenv("MA_CROSS_VERIFY_BONUS", "8"))
MA_CROSS_MAX_GAP_PCT = float(os.getenv("MA_CROSS_MAX_GAP_PCT", "0.22"))
MA_CROSS_USE_CLOSED_15M = os.getenv("MA_CROSS_USE_CLOSED_15M", "true").lower() == "true"
MA_CROSS_IGNORE_15M_CANDLE_LOCATION_BLOCK = os.getenv("MA_CROSS_IGNORE_15M_CANDLE_LOCATION_BLOCK", "true").lower() == "true"
FIXED_STOP_PCT_ENABLED = os.getenv("FIXED_STOP_PCT_ENABLED", "true").lower() == "true"
FIXED_STOP_PCT = float(os.getenv("FIXED_STOP_PCT", "0.80"))
SHORT_STRUCTURE_EXTRA_BUFFER_PCT = float(os.getenv("SHORT_STRUCTURE_EXTRA_BUFFER_PCT", "0.18"))
LONG_STRUCTURE_EXTRA_BUFFER_PCT = float(os.getenv("LONG_STRUCTURE_EXTRA_BUFFER_PCT", "0.18"))

# =========================================================
# DIŞ YORUM KATMANI YOK - HATA HAFIZASI VAR
# =========================================================
# Kullanıcı tercihi: TP1'de tamamı kapatılabilir; ama sinyal kalitesi için TP2/TP3 potansiyeli ayrıca raporlanır.
FOLLOWUP_CLOSE_ALL_AT_TP1 = os.getenv("FOLLOWUP_CLOSE_ALL_AT_TP1", "true").lower() == "true"
# Net AL kuralı: riskli/çelişkili mesaj dışarı çıkmasın.
STRICT_CLEAN_SIGNAL_ONLY = os.getenv("STRICT_CLEAN_SIGNAL_ONLY", "true").lower() == "true"
STRICT_BLOCK_RISKY_CLOSE_FOR_SIGNAL = os.getenv("STRICT_BLOCK_RISKY_CLOSE_FOR_SIGNAL", "true").lower() == "true"
STRICT_BLOCK_NEGATIVE_15M_SCORE = os.getenv("STRICT_BLOCK_NEGATIVE_15M_SCORE", "true").lower() == "true"
STRICT_MIN_SHORT_ICT_EDGE = float(os.getenv("STRICT_MIN_SHORT_ICT_EDGE", "1.50"))
STRICT_MIN_LONG_ICT_EDGE = float(os.getenv("STRICT_MIN_LONG_ICT_EDGE", "1.50"))

# Hata hafızası: dış yorum motoru değildir; sadece sonuçları hatırlar.
MISTAKE_MEMORY_ENABLED = os.getenv("MISTAKE_MEMORY_ENABLED", "true").lower() == "true"
MISTAKE_MIN_PATTERN_SAMPLES = int(float(os.getenv("MISTAKE_MIN_PATTERN_SAMPLES", "3")))
MISTAKE_PATTERN_STOP_RATE_BLOCK = float(os.getenv("MISTAKE_PATTERN_STOP_RATE_BLOCK", "0.60"))
MISTAKE_MIN_COIN_SAMPLES = int(float(os.getenv("MISTAKE_MIN_COIN_SAMPLES", "3")))
MISTAKE_COIN_STOP_RATE_BLOCK = float(os.getenv("MISTAKE_COIN_STOP_RATE_BLOCK", "0.67"))
MISTAKE_RECENT_WINDOW = int(float(os.getenv("MISTAKE_RECENT_WINDOW", "25")))
MISTAKE_MAX_RECENT_STOPS = int(float(os.getenv("MISTAKE_MAX_RECENT_STOPS", "2")))
MISTAKE_MEMORY_BLOCK_SCORE = float(os.getenv("MISTAKE_MEMORY_BLOCK_SCORE", "3.0"))


# =========================================================
# PRO PLUS OPSİYONEL MODÜLLER
# Rejim + makro korelasyon + destek/direnç + pozisyon yönetimi + backtest
# =========================================================
MARKET_REGIME_ENGINE_ENABLED = os.getenv("MARKET_REGIME_ENGINE_ENABLED", "true").lower() == "true"
REGIME_BLOCK_COUNTER_TREND = os.getenv("REGIME_BLOCK_COUNTER_TREND", "true").lower() == "true"
REGIME_TREND_EMA_GAP_PCT = float(os.getenv("REGIME_TREND_EMA_GAP_PCT", "0.35"))
REGIME_BREAKOUT_ATR_MULT = float(os.getenv("REGIME_BREAKOUT_ATR_MULT", "1.35"))
REGIME_RANGE_MAX_WIDTH_PCT = float(os.getenv("REGIME_RANGE_MAX_WIDTH_PCT", "1.35"))
REGIME_MIN_CONFIRM_SCORE = float(os.getenv("REGIME_MIN_CONFIRM_SCORE", "2.0"))

MACRO_CORRELATION_ENGINE_ENABLED = os.getenv("MACRO_CORRELATION_ENGINE_ENABLED", "true").lower() == "true"
MACRO_SYMBOLS = [x.strip().upper() for x in os.getenv("MACRO_SYMBOLS", "BTC-USDT-SWAP,ETH-USDT-SWAP").split(",") if x.strip()]
MACRO_BTC_DROP_BLOCK_LONG_PCT = float(os.getenv("MACRO_BTC_DROP_BLOCK_LONG_PCT", "0.45"))
MACRO_BTC_PUMP_BLOCK_SHORT_PCT = float(os.getenv("MACRO_BTC_PUMP_BLOCK_SHORT_PCT", "0.55"))
MACRO_BTC_FAST_MOVE_5M_PCT = float(os.getenv("MACRO_BTC_FAST_MOVE_5M_PCT", "0.28"))
MACRO_HIGH_CORR_MIN = float(os.getenv("MACRO_HIGH_CORR_MIN", "0.55"))
MACRO_BLOCK_IF_HIGH_CORR_COUNTER = os.getenv("MACRO_BLOCK_IF_HIGH_CORR_COUNTER", "true").lower() == "true"

SR_ENGINE_ENABLED = os.getenv("SR_ENGINE_ENABLED", "true").lower() == "true"
SR_PIVOT_LEFT = int(float(os.getenv("SR_PIVOT_LEFT", "2")))
SR_PIVOT_RIGHT = int(float(os.getenv("SR_PIVOT_RIGHT", "2")))
SR_LOOKBACK_1M = int(float(os.getenv("SR_LOOKBACK_1M", "90")))
SR_LOOKBACK_5M = int(float(os.getenv("SR_LOOKBACK_5M", "72")))
SR_CLUSTER_PCT = float(os.getenv("SR_CLUSTER_PCT", "0.18"))
SR_NEAR_LEVEL_PCT = float(os.getenv("SR_NEAR_LEVEL_PCT", "0.45"))
SR_TP1_ROOM_BUFFER_PCT = float(os.getenv("SR_TP1_ROOM_BUFFER_PCT", "0.18"))
SR_STOP_BEHIND_LEVEL_PCT = float(os.getenv("SR_STOP_BEHIND_LEVEL_PCT", "0.08"))
SR_MIN_LEVEL_SCORE = float(os.getenv("SR_MIN_LEVEL_SCORE", "2.0"))
SR_BLOCK_IF_TP1_WALL = os.getenv("SR_BLOCK_IF_TP1_WALL", "true").lower() == "true"
SR_BLOCK_WEAK_ZONE_LOW_FLOW = os.getenv("SR_BLOCK_WEAK_ZONE_LOW_FLOW", "true").lower() == "true"

POSITION_MANAGER_ENABLED = os.getenv("POSITION_MANAGER_ENABLED", "true").lower() == "true"
POSITION_MANAGER_CHECK_INTERVAL_SEC = int(float(os.getenv("POSITION_MANAGER_CHECK_INTERVAL_SEC", "90")))
POSITION_PM_MIN_AGE_SEC = int(float(os.getenv("POSITION_PM_MIN_AGE_SEC", "90")))
POSITION_TP1_PARTIAL_PCT = float(os.getenv("POSITION_TP1_PARTIAL_PCT", "50"))
POSITION_TP2_PARTIAL_PCT = float(os.getenv("POSITION_TP2_PARTIAL_PCT", "30"))
POSITION_MOVE_STOP_BE_AFTER_TP1 = os.getenv("POSITION_MOVE_STOP_BE_AFTER_TP1", "true").lower() == "true"
POSITION_TRAILING_ENABLED = os.getenv("POSITION_TRAILING_ENABLED", "true").lower() == "true"
POSITION_TRAIL_ATR_MULT = float(os.getenv("POSITION_TRAIL_ATR_MULT", "1.20"))
POSITION_TRAIL_AFTER_PROFIT_PCT = float(os.getenv("POSITION_TRAIL_AFTER_PROFIT_PCT", "0.55"))
POSITION_SEND_PM_ALERTS = os.getenv("POSITION_SEND_PM_ALERTS", "true").lower() == "true"

BACKTEST_ENGINE_ENABLED = os.getenv("BACKTEST_ENGINE_ENABLED", "true").lower() == "true"
BACKTEST_DEFAULT_BARS = int(float(os.getenv("BACKTEST_DEFAULT_BARS", "240")))
BACKTEST_FORWARD_BARS = int(float(os.getenv("BACKTEST_FORWARD_BARS", "45")))
BACKTEST_MIN_SIGNAL_GAP_BARS = int(float(os.getenv("BACKTEST_MIN_SIGNAL_GAP_BARS", "12")))
BACKTEST_RISK_STOP_PCT = float(os.getenv("BACKTEST_RISK_STOP_PCT", "0.80"))
BACKTEST_TP1_PCT = float(os.getenv("BACKTEST_TP1_PCT", "1.00"))
BACKTEST_TP2_PCT = float(os.getenv("BACKTEST_TP2_PCT", "1.50"))
BACKTEST_TP3_PCT = float(os.getenv("BACKTEST_TP3_PCT", "2.00"))


# =========================================================
# PRO WS + GERÇEKÇİ MALİYET/BACKTEST + GELİŞMİŞ LONG AYARLARI
# Yapay zeka yoktur. Bu bölüm sadece gerçek zamanlı veri, maliyet modeli,
# pozisyon/backtest gerçekçiliği ve hata hafızası kalitesini artırır.
# =========================================================
PRO_WS_ENABLED = os.getenv("PRO_WS_ENABLED", "true").lower() == "true"
PRO_WS_OKX_URL = os.getenv("PRO_WS_OKX_URL", "wss://ws.okx.com:8443/ws/v5/public").strip()
PRO_WS_BOOK_CHANNEL = os.getenv("PRO_WS_BOOK_CHANNEL", "books5").strip()
PRO_WS_TRADE_CHANNEL = os.getenv("PRO_WS_TRADE_CHANNEL", "trades").strip()
PRO_WS_MAX_SYMBOLS = int(float(os.getenv("PRO_WS_MAX_SYMBOLS", "200")))
PRO_WS_BATCH_SIZE = int(float(os.getenv("PRO_WS_BATCH_SIZE", "20")))
PRO_WS_STALE_SEC = float(os.getenv("PRO_WS_STALE_SEC", "8.0"))
PRO_WS_RECONNECT_SEC = float(os.getenv("PRO_WS_RECONNECT_SEC", "5.0"))
PRO_WS_HISTORY_LEN = int(float(os.getenv("PRO_WS_HISTORY_LEN", "80")))
PRO_WS_TRADE_HISTORY_LEN = int(float(os.getenv("PRO_WS_TRADE_HISTORY_LEN", "240")))
PRO_WS_USE_FOR_ORDERBOOK = os.getenv("PRO_WS_USE_FOR_ORDERBOOK", "true").lower() == "true"
PRO_WS_USE_FOR_TRADES = os.getenv("PRO_WS_USE_FOR_TRADES", "true").lower() == "true"

PRO_SPOOFING_WS_REQUIRED_FOR_STRONG = os.getenv("PRO_SPOOFING_WS_REQUIRED_FOR_STRONG", "true").lower() == "true"
PRO_SPOOF_WALL_MULT = float(os.getenv("PRO_SPOOF_WALL_MULT", "2.8"))
PRO_SPOOF_VANISH_RATIO = float(os.getenv("PRO_SPOOF_VANISH_RATIO", "0.38"))
PRO_SPOOF_STACK_RATIO = float(os.getenv("PRO_SPOOF_STACK_RATIO", "2.20"))
PRO_SPOOF_WINDOW_SEC = float(os.getenv("PRO_SPOOF_WINDOW_SEC", "6.0"))
PRO_SPOOF_MIN_HISTORY = int(float(os.getenv("PRO_SPOOF_MIN_HISTORY", "4")))

PRO_COST_MODEL_ENABLED = os.getenv("PRO_COST_MODEL_ENABLED", "true").lower() == "true"
PRO_TAKER_FEE_PCT = float(os.getenv("PRO_TAKER_FEE_PCT", "0.05"))       # Tek yön taker ücret varsayımı
PRO_MAKER_FEE_PCT = float(os.getenv("PRO_MAKER_FEE_PCT", "0.02"))       # Bilgi amaçlı
PRO_SLIPPAGE_BASE_PCT = float(os.getenv("PRO_SLIPPAGE_BASE_PCT", "0.04"))
PRO_SLIPPAGE_VOL_MULT = float(os.getenv("PRO_SLIPPAGE_VOL_MULT", "0.25"))
PRO_SPREAD_SLIPPAGE_MULT = float(os.getenv("PRO_SPREAD_SLIPPAGE_MULT", "0.50"))
PRO_FUNDING_HOLD_HOURS = float(os.getenv("PRO_FUNDING_HOLD_HOURS", "2.0"))
PRO_DEFAULT_FUNDING_PCT_8H = float(os.getenv("PRO_DEFAULT_FUNDING_PCT_8H", "0.01"))
PRO_BACKTEST_INITIAL_EQUITY = float(os.getenv("PRO_BACKTEST_INITIAL_EQUITY", "1000"))
PRO_BACKTEST_RISK_PER_TRADE_PCT = float(os.getenv("PRO_BACKTEST_RISK_PER_TRADE_PCT", "1.0"))
PRO_BACKTEST_INCLUDE_COSTS = os.getenv("PRO_BACKTEST_INCLUDE_COSTS", "true").lower() == "true"
PRO_BACKTEST_USE_PARTIALS = os.getenv("PRO_BACKTEST_USE_PARTIALS", "true").lower() == "true"
PRO_BACKTEST_TP1_CLOSE_PCT = float(os.getenv("PRO_BACKTEST_TP1_CLOSE_PCT", "50"))
PRO_BACKTEST_TP2_CLOSE_PCT = float(os.getenv("PRO_BACKTEST_TP2_CLOSE_PCT", "30"))
PRO_BACKTEST_TP3_CLOSE_PCT = float(os.getenv("PRO_BACKTEST_TP3_CLOSE_PCT", "20"))
PRO_BACKTEST_SAME_CANDLE_POLICY = os.getenv("PRO_BACKTEST_SAME_CANDLE_POLICY", "STOP_FIRST").strip().upper()

PRO_LONG_STRICT_ENABLED = os.getenv("PRO_LONG_STRICT_ENABLED", "true").lower() == "true"
PRO_LONG_MIN_BUY_TO_SELL = float(os.getenv("PRO_LONG_MIN_BUY_TO_SELL", "1.15"))
PRO_LONG_MAX_SELL_TO_BUY = float(os.getenv("PRO_LONG_MAX_SELL_TO_BUY", "1.25"))
PRO_LONG_MIN_VOL1 = float(os.getenv("PRO_LONG_MIN_VOL1", "0.35"))
PRO_LONG_MIN_VOL5 = float(os.getenv("PRO_LONG_MIN_VOL5", "0.25"))
PRO_LONG_BLOCK_STRONG_BEAR_REGIME = os.getenv("PRO_LONG_BLOCK_STRONG_BEAR_REGIME", "true").lower() == "true"
PRO_LONG_REQUIRE_SR_SUPPORT = os.getenv("PRO_LONG_REQUIRE_SR_SUPPORT", "true").lower() == "true"
PRO_LONG_REQUIRE_WS_NOT_BEARISH = os.getenv("PRO_LONG_REQUIRE_WS_NOT_BEARISH", "true").lower() == "true"


BLOCKED_COIN_BASE_KEYWORDS = tuple(
    x.strip().upper()
    for x in os.getenv(
        "BLOCKED_COIN_BASE_KEYWORDS",
        "PEPE,1000PEPE,DOGE,SHIB,FLOKI,BONK,WIF,MEME,TURBO,MEW,BRETT,NOT,"
        "BOME,TRUMP,FARTCOIN,PNUT,GOAT,MELANIA,AI16Z,VINE,GRIFFAIN,PIPPIN,"
        "CASINO,BET,GAMBLE,ADULT,PORN,XXX,LOTTO,LOTTERY"
    ).split(",")
    if x.strip()
)

# Kullanıcı kararı / helal hassasiyet filtresi:
# Bu coinler kaldıraç-türev, faiz/yield, NFT/metaverse/gaming gibi şüpheli alanlara yakın görüldüğü için
# sadece DEFAULT_COINS listesinden çıkarılmaz; COINS env içine yanlışlıkla yazılsa bile zorunlu bloklanır.
ETHICAL_BLOCKED_COIN_BASE_KEYWORDS = tuple(
    x.strip().upper()
    for x in os.getenv(
        "ETHICAL_BLOCKED_COIN_BASE_KEYWORDS",
        "DYDX,JUP,COMP,PENDLE,LDO,CRV,BLUR,GALA,SAND,MANA,"
        "AAVE,MKR,UNI,GMX,PERP,SNX,CAKE,SUSHI,1INCH,BAL,FXS,RPL,"
        "ETHFI,REZ,AEVO,MORPHO,EIGEN,USUAL"
    ).split(",")
    if x.strip()
)

MIN_24H_QUOTE_VOLUME = float(os.getenv("MIN_24H_QUOTE_VOLUME", "300000"))
KLINE_CACHE_SEC = int(float(os.getenv("KLINE_CACHE_SEC", "12")))
TICKER_CACHE_SEC = int(float(os.getenv("TICKER_CACHE_SEC", "2")))
HTTP_TIMEOUT = int(float(os.getenv("HTTP_TIMEOUT", "12")))
OKX_INSTRUMENT_CACHE_SEC = int(float(os.getenv("OKX_INSTRUMENT_CACHE_SEC", "1800")))
AUTO_SYMBOL_REFRESH_SEC = int(float(os.getenv("AUTO_SYMBOL_REFRESH_SEC", "1800")))
SYMBOL_FAIL_BLOCK_SEC = int(float(os.getenv("SYMBOL_FAIL_BLOCK_SEC", "900")))
SYMBOL_FAIL_FORGET_SEC = int(float(os.getenv("SYMBOL_FAIL_FORGET_SEC", "43200")))
SYMBOL_FAIL_MAX_STREAK = int(float(os.getenv("SYMBOL_FAIL_MAX_STREAK", "2")))

DEFAULT_COINS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BNB-USDT-SWAP', 'SOL-USDT-SWAP', 'XRP-USDT-SWAP',
    'ADA-USDT-SWAP', 'AVAX-USDT-SWAP', 'LINK-USDT-SWAP', 'LTC-USDT-SWAP', 'TRX-USDT-SWAP',
    'DOT-USDT-SWAP', 'ATOM-USDT-SWAP', 'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'SUI-USDT-SWAP',
    'SEI-USDT-SWAP', 'TIA-USDT-SWAP', 'INJ-USDT-SWAP', 'FIL-USDT-SWAP', 'ETC-USDT-SWAP',
    'BCH-USDT-SWAP', 'EOS-USDT-SWAP', 'NEO-USDT-SWAP', 'GAS-USDT-SWAP', 'XLM-USDT-SWAP',
    'HBAR-USDT-SWAP', 'ALGO-USDT-SWAP', 'VET-USDT-SWAP', 'IOTA-USDT-SWAP', 'CHZ-USDT-SWAP',
    'ZIL-USDT-SWAP', 'ZRX-USDT-SWAP', 'ARB-USDT-SWAP', 'OP-USDT-SWAP', 'FLOW-USDT-SWAP',
    'ROSE-USDT-SWAP', 'CFX-USDT-SWAP', 'SKL-USDT-SWAP', 'ANKR-USDT-SWAP', 'CELR-USDT-SWAP',
    'IOST-USDT-SWAP', 'ONE-USDT-SWAP', 'SXP-USDT-SWAP', 'CTSI-USDT-SWAP', 'RSR-USDT-SWAP',
    'ACH-USDT-SWAP', 'API3-USDT-SWAP', 'GMT-USDT-SWAP', 'LRC-USDT-SWAP', 'KAVA-USDT-SWAP',
    'MINA-USDT-SWAP', 'WOO-USDT-SWAP', 'BAND-USDT-SWAP', 'STORJ-USDT-SWAP', 'MASK-USDT-SWAP',
    'ID-USDT-SWAP', 'ARPA-USDT-SWAP', 'ONT-USDT-SWAP', 'QTUM-USDT-SWAP', 'BAT-USDT-SWAP',
    'ENJ-USDT-SWAP', 'RVN-USDT-SWAP', 'KNC-USDT-SWAP', 'ENA-USDT-SWAP', 'PYTH-USDT-SWAP',
    'STRK-USDT-SWAP', 'ARKM-USDT-SWAP', 'OM-USDT-SWAP', 'POLYX-USDT-SWAP', 'HOT-USDT-SWAP',
    'DUSK-USDT-SWAP', 'HOOK-USDT-SWAP', 'PHB-USDT-SWAP', 'MAGIC-USDT-SWAP', 'XTZ-USDT-SWAP',
    'ICP-USDT-SWAP', 'EGLD-USDT-SWAP', 'KSM-USDT-SWAP', 'ASTR-USDT-SWAP', 'GLMR-USDT-SWAP',
    'MOVR-USDT-SWAP', 'CELO-USDT-SWAP', 'COTI-USDT-SWAP', 'CKB-USDT-SWAP', 'KAS-USDT-SWAP',
    'XEC-USDT-SWAP', 'SC-USDT-SWAP', 'AR-USDT-SWAP', 'NKN-USDT-SWAP', 'RLC-USDT-SWAP',
    'FET-USDT-SWAP', 'TAO-USDT-SWAP', 'GLM-USDT-SWAP', 'RNDR-USDT-SWAP', 'AKT-USDT-SWAP',
    'AIOZ-USDT-SWAP', 'NMR-USDT-SWAP', 'LPT-USDT-SWAP', 'THETA-USDT-SWAP', 'TFUEL-USDT-SWAP',
    'CHR-USDT-SWAP', 'CTXC-USDT-SWAP', 'MDT-USDT-SWAP', 'RSS3-USDT-SWAP', 'CQT-USDT-SWAP',
    'POND-USDT-SWAP', 'CSPR-USDT-SWAP', 'KDA-USDT-SWAP', 'FLUX-USDT-SWAP', 'HIVE-USDT-SWAP',
    'STEEM-USDT-SWAP', 'JASMY-USDT-SWAP', 'IOTX-USDT-SWAP', 'REQ-USDT-SWAP', 'POWR-USDT-SWAP',
    'DENT-USDT-SWAP', 'MTL-USDT-SWAP', 'STMX-USDT-SWAP', 'CVC-USDT-SWAP', 'DATA-USDT-SWAP',
    'KEY-USDT-SWAP', 'ONG-USDT-SWAP', 'SYS-USDT-SWAP', 'DGB-USDT-SWAP', 'XNO-USDT-SWAP',
    'XEM-USDT-SWAP', 'ALPHA-USDT-SWAP', 'BADGER-USDT-SWAP', 'BEL-USDT-SWAP', 'BICO-USDT-SWAP',
    'BOND-USDT-SWAP', 'BSV-USDT-SWAP', 'C98-USDT-SWAP', 'DODO-USDT-SWAP', 'FORTH-USDT-SWAP',
    'FRONT-USDT-SWAP', 'HFT-USDT-SWAP', 'LOKA-USDT-SWAP', 'LTO-USDT-SWAP', 'MBOX-USDT-SWAP',
    'NULS-USDT-SWAP', 'OXT-USDT-SWAP', 'PROM-USDT-SWAP', 'PUNDIX-USDT-SWAP', 'QI-USDT-SWAP',
    'RAD-USDT-SWAP', 'RARE-USDT-SWAP', 'RIF-USDT-SWAP', 'SFP-USDT-SWAP', 'STG-USDT-SWAP',
    'SUPER-USDT-SWAP', 'IMX-USDT-SWAP', 'KLAY-USDT-SWAP', 'KMD-USDT-SWAP', 'FLM-USDT-SWAP',
    'UTK-USDT-SWAP', 'WAXP-USDT-SWAP', 'AERGO-USDT-SWAP', 'FIO-USDT-SWAP', 'FIRO-USDT-SWAP',
    'PHA-USDT-SWAP', 'CFG-USDT-SWAP', 'OAS-USDT-SWAP', 'ACA-USDT-SWAP', 'RAY-USDT-SWAP',
    'MERL-USDT-SWAP', 'ZETA-USDT-SWAP', 'ALT-USDT-SWAP', 'ZK-USDT-SWAP', 'ZRO-USDT-SWAP',
    'WLD-USDT-SWAP', 'BB-USDT-SWAP', 'SAGA-USDT-SWAP', 'OMNI-USDT-SWAP', 'TAIKO-USDT-SWAP',
    'IO-USDT-SWAP', 'ACE-USDT-SWAP', 'W-USDT-SWAP', 'PORTAL-USDT-SWAP', 'MANTA-USDT-SWAP',
    'METIS-USDT-SWAP', 'LSK-USDT-SWAP', 'WAVES-USDT-SWAP', 'ICX-USDT-SWAP', 'OCEAN-USDT-SWAP',
    'AGIX-USDT-SWAP', 'AUDIO-USDT-SWAP', 'KERNEL-USDT-SWAP', 'KAITO-USDT-SWAP', 'BERA-USDT-SWAP',
    'COOKIE-USDT-SWAP', 'ME-USDT-SWAP', 'MOVE-USDT-SWAP', 'KAIA-USDT-SWAP', 'SCR-USDT-SWAP',
    'INIT-USDT-SWAP', 'SHELL-USDT-SWAP', 'VANA-USDT-SWAP', 'SONIC-USDT-SWAP', 'XAI-USDT-SWAP',
]
def coin_base_from_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper().replace("/", "-")
    if s.endswith("-SWAP"):
        s = s[:-5]
    if "-" in s:
        return s.split("-")[0]
    if s.endswith("USDT"):
        return s[:-4]
    return s


def is_blocked_coin_symbol(symbol: str) -> bool:
    base = coin_base_from_symbol(symbol)
    all_blocked = tuple(BLOCKED_COIN_BASE_KEYWORDS) + tuple(ETHICAL_BLOCKED_COIN_BASE_KEYWORDS)
    return any(key and key in base for key in all_blocked)


def filter_coin_universe(symbols: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in symbols:
        sym = (raw or "").strip().upper()
        if not sym or is_blocked_coin_symbol(sym):
            continue
        if sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


COINS = filter_coin_universe([x.strip().upper() for x in os.getenv("COINS", ",".join(DEFAULT_COINS)).split(",") if x.strip()])

# =========================================================
# LOGGING
# =========================================================
LOG_MAX_BYTES = int(float(os.getenv("LOG_MAX_BYTES", "5242880")))
LOG_BACKUP_COUNT = int(float(os.getenv("LOG_BACKUP_COUNT", "5")))

file_log_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
    encoding="utf-8",
)
stream_log_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[file_log_handler, stream_log_handler],
)
logger = logging.getLogger("balina_avcisi_v6")

# =========================================================
# GLOBAL STATE
# =========================================================
TZ = ZoneInfo(TIMEZONE_NAME)

import threading as _threading
_thread_local = _threading.local()

def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({"User-Agent": "BalinaAvcisiV6WhaleEye/1.0"})
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=6,
            pool_maxsize=12,
            max_retries=0,
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _thread_local.session = s
    return _thread_local.session

kline_cache: Dict[str, Tuple[float, List[List[Any]]]] = {}
ticker_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
orderbook_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
trades_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
orderbook_memory: Dict[str, Dict[str, Any]] = {}
instrument_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
okx_live_symbols: Dict[str, Dict[str, Any]] = {}
symbol_fail_state: Dict[str, Dict[str, Any]] = {}

# V6 YENI: OI / Funding / CVD cache'leri
oi_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
funding_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
cvd_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
spoofing_memory: Dict[str, Dict[str, Any]] = {}


# PRO WS canlı veri hafızası. REST kodunu bozmaz; WebSocket yoksa otomatik REST'e düşer.
ws_orderbook_state: Dict[str, Dict[str, Any]] = {}
ws_orderbook_history: Dict[str, List[Dict[str, Any]]] = {}
ws_trade_state: Dict[str, List[Dict[str, Any]]] = {}
ws_runtime_state: Dict[str, Any] = {
    "enabled": False,
    "installed": False,
    "connected": False,
    "last_msg_ts": 0.0,
    "last_error": "",
    "reconnects": 0,
    "symbols": [],
}

memory: Dict[str, Any] = {
    "hot": {},
    "trend_watch": {},
    "signals": {},
    "follows": {},
    "stats": {},
    "daily_short_sent": {},
    "daily_long_sent": {},
    "last_signal_ts": 0.0,
    "last_signal_attempt_ts": 0.0,
    "last_diag_ts": 0.0,
    "mistake_memory": {"patterns": {}, "coins": {}, "recent": []},
    "lifetime_stats": {},
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
    "trend_guard_block_signal": 0,
    "trend_guard_watch": 0,
    "trend_breakdown_pass": 0,
    "breakdown_candidate_assist": 0,
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
    "daily_total_block": 0,
    "quality_gate_block": 0,
    "rr_block": 0,
    "invisible_face_clean": 0,
    "invisible_face_scalp": 0,
    "invisible_face_watch": 0,
    "invisible_face_block": 0,
    "invisible_face_promote": 0,
    "invisible_face_downgrade": 0,
    "tepe_early_signal": 0,
    "tepe_late_block": 0,
    "orderbook_ok": 0,
    "orderbook_fail": 0,
    "trades_ok": 0,
    "trades_fail": 0,
    "scan_signal_suppressed": 0,
    "global_gap_block": 0,
    "active_trade_block": 0,
    "invalid_symbol_skip": 0,
    "blocked_symbol_skip": 0,
    "okx_symbol_pruned": 0,
    "okx_symbol_refresh": 0,
    "okx_symbol_fail_block": 0,
    "blocked_coin_skip": 0,
    "close_confirm_block": 0,
    "close_confirm_risky": 0,
    "long_signal_sent": 0,
    "long_candidate": 0,
    "long_ready": 0,
    "long_reject": 0,
    "long_ict_signal": 0,
    "long_quality_block": 0,
    "long_close_confirm_block": 0,
    "long_conflict_block": 0,
    # V6 YENI
    "oi_short_diverge": 0,
    "oi_long_diverge": 0,
    "funding_short_bonus": 0,
    "funding_long_bonus": 0,
    "spoofing_detected": 0,
    "cvd_diverge_short": 0,
    "cvd_diverge_long": 0,
    "whale_eye_block": 0,
    "whale_eye_pass": 0,
    "regime_pass": 0,
    "regime_block": 0,
    "macro_pass": 0,
    "macro_block": 0,
    "sr_pass": 0,
    "sr_block": 0,
    "pm_alert_sent": 0,
    "backtest_run": 0,
    "mistake_memory_pass": 0,
    "mistake_memory_block": 0,
    "mistake_memory_learn": 0,
    "ws_connect": 0,
    "ws_reconnect": 0,
    "ws_msg": 0,
    "ws_book_update": 0,
    "ws_trade_update": 0,
    "ws_orderbook_used": 0,
    "ws_trade_used": 0,
    "ws_spoofing_detected": 0,
    "pro_backtest_run": 0,
    "pro_cost_applied": 0,
    "pro_long_block": 0,
    "why_blocked_recorded": 0,
    "entry_location_early": 0,
    "entry_location_late_block": 0,
    "ma_cross_pass": 0,
    "ma_cross_block": 0,
    "ma_cross_15m_block": 0,
    "fixed_stop_used": 0,
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
        if v is None:
            return default
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


def fmt_num(v: float) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "0.0000"
    if abs(v) >= 1000:
        int_part = int(v)
        frac = abs(v - int_part)
        int_str = f"{int_part:,}".replace(",", ".")
        if frac > 1e-12:
            frac_str = f"{frac:.4f}"[1:].replace(".", ",")
            return f"{int_str}{frac_str}"
        return int_str
    if abs(v) >= 1:
        return f"{v:.4f}"
    if abs(v) >= 0.0001:
        return f"{v:.6f}"
    return f"{v:.8f}"



def default_lifetime_stats() -> Dict[str, Any]:
    now_ts = time.time()
    return {
        "activated_ts": now_ts,
        "total_signals": 0,
        "short_signals": 0,
        "long_signals": 0,
        "tp_total": 0,
        "stop_total": 0,
        "neutral_total": 0,
        "tp1": 0,
        "tp2": 0,
        "tp3": 0,
        "last_signal_ts": 0.0,
        "last_result_ts": 0.0,
    }


def normalize_lifetime_stats() -> Dict[str, Any]:
    ensure_memory_shape()
    ls = memory.setdefault("lifetime_stats", default_lifetime_stats())
    if not isinstance(ls, dict):
        memory["lifetime_stats"] = default_lifetime_stats()
        ls = memory["lifetime_stats"]
    defaults = default_lifetime_stats()
    for k, v in defaults.items():
        ls.setdefault(k, v)
    # Sayısal alanlar bozuk gelirse 0'a çek.
    for k in ("total_signals", "short_signals", "long_signals", "tp_total", "stop_total", "neutral_total", "tp1", "tp2", "tp3"):
        ls[k] = int(safe_float(ls.get(k, 0), 0))
    for k in ("activated_ts", "last_signal_ts", "last_result_ts"):
        ls[k] = safe_float(ls.get(k, 0), 0)
    return ls


def format_duration_from_ts(ts: float) -> str:
    ts = safe_float(ts, 0)
    if ts <= 0:
        return "-"
    sec = max(0, int(time.time() - ts))
    days = sec // 86400
    hours = (sec % 86400) // 3600
    mins = (sec % 3600) // 60
    if days > 0:
        return f"{days}g {hours}s"
    if hours > 0:
        return f"{hours}s {mins}dk"
    return f"{mins}dk"


def record_lifetime_signal_sent(symbol: str, payload: Dict[str, Any]) -> None:
    ls = normalize_lifetime_stats()
    direction = str(payload.get("direction", "SHORT")).upper()
    ls["total_signals"] = int(safe_float(ls.get("total_signals", 0), 0)) + 1
    if direction == "LONG":
        ls["long_signals"] = int(safe_float(ls.get("long_signals", 0), 0)) + 1
    else:
        ls["short_signals"] = int(safe_float(ls.get("short_signals", 0), 0)) + 1
    ls["last_signal_ts"] = time.time()


def record_lifetime_signal_outcome(rec: Dict[str, Any], outcome: str) -> None:
    """2 saat takip sonucu bir kere toplam istatistiğe yazılır."""
    if not isinstance(rec, dict):
        return
    if rec.get("lifetime_outcome_recorded"):
        return
    ls = normalize_lifetime_stats()
    outcome = str(outcome or "NÖTR").upper()
    if outcome.startswith("TP"):
        ls["tp_total"] = int(safe_float(ls.get("tp_total", 0), 0)) + 1
        if outcome == "TP1":
            ls["tp1"] = int(safe_float(ls.get("tp1", 0), 0)) + 1
        elif outcome == "TP2":
            ls["tp2"] = int(safe_float(ls.get("tp2", 0), 0)) + 1
        elif outcome == "TP3":
            ls["tp3"] = int(safe_float(ls.get("tp3", 0), 0)) + 1
    elif outcome == "STOP":
        ls["stop_total"] = int(safe_float(ls.get("stop_total", 0), 0)) + 1
    else:
        ls["neutral_total"] = int(safe_float(ls.get("neutral_total", 0), 0)) + 1
    ls["last_result_ts"] = time.time()
    rec["lifetime_outcome_recorded"] = True

def ensure_memory_shape() -> None:
    global memory
    if not isinstance(memory, dict):
        memory = {}
    memory.setdefault("hot", {})
    memory.setdefault("trend_watch", {})
    memory.setdefault("signals", {})
    memory.setdefault("follows", {})
    memory.setdefault("stats", {})
    memory.setdefault("daily_short_sent", {})
    memory.setdefault("daily_long_sent", {})
    memory.setdefault("last_signal_ts", 0.0)
    memory.setdefault("last_signal_attempt_ts", 0.0)
    memory.setdefault("last_diag_ts", 0.0)
    # Eski sürümlerden kalmış dış yorum katmanı kayıtlarını temizle.
    for _legacy_key in ("a" + "i_auto_sent_lock", "a" + "i_auto_scan", "hasan_" + "ai"):
        memory.pop(_legacy_key, None)
    memory.setdefault("mistake_memory", {"patterns": {}, "coins": {}, "recent": []})
    if not isinstance(memory.get("mistake_memory"), dict):
        memory["mistake_memory"] = {"patterns": {}, "coins": {}, "recent": []}
    memory["mistake_memory"].setdefault("patterns", {})
    memory["mistake_memory"].setdefault("coins", {})
    memory["mistake_memory"].setdefault("recent", [])
    memory.setdefault("position_manager", {})
    memory.setdefault("backtests", {})
    memory.setdefault("market_context", {})
    ls = memory.setdefault("lifetime_stats", default_lifetime_stats())
    if not isinstance(ls, dict):
        memory["lifetime_stats"] = default_lifetime_stats()
        ls = memory["lifetime_stats"]
    for _k, _v in default_lifetime_stats().items():
        ls.setdefault(_k, _v)
    memory.setdefault("why_blocked", {"latest": [], "by_symbol": {}})
    memory["why_blocked"].setdefault("latest", [])
    memory["why_blocked"].setdefault("by_symbol", {})



def _why_positive_note_score(note: str, direction: str) -> float:
    n = (note or "").lower()
    score = 0.0
    common_words = ("choch", "mss", "bos", "ema9", "ema21", "rsi", "orderbook", "savunma", "baskın", "fitil", "ict")
    for w in common_words:
        if w in n:
            score += 2.0
    if direction == "LONG":
        for w in ("alıcı", "alış", "discount", "destek", "toparlanıyor", "yukarı"):
            if w in n:
                score += 3.0
    else:
        for w in ("satış", "kırılım", "tepe", "red", "üst fitil", "aşağı", "short"):
            if w in n:
                score += 3.0
    return min(score, 20.0)



def _deep_get_numeric(obj: Any, paths: List[List[str]], default: Optional[float] = None) -> Optional[float]:
    for path in paths:
        cur = obj
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur.get(key)
            else:
                ok = False
                break
        if ok:
            val = safe_float(cur, None)
            if val is not None:
                return val
    return default


def _read_long_metric(res: Dict[str, Any], metric: str) -> Optional[float]:
    metric = metric.lower().strip()
    path_map = {
        "candidate": [
            ["long_candidate_score"], ["long_candidate"], ["candidate_long_score"],
            ["long_scores", "candidate"], ["long_scores", "candidate_score"],
            ["long", "candidate"], ["long", "candidate_score"],
            ["long_result", "candidate"], ["long_result", "candidate_score"],
            ["long_analysis", "candidate"], ["long_analysis", "candidate_score"],
        ],
        "ready": [
            ["long_ready_score"], ["long_ready"], ["ready_long_score"],
            ["long_scores", "ready"], ["long_scores", "ready_score"],
            ["long", "ready"], ["long", "ready_score"],
            ["long_result", "ready"], ["long_result", "ready_score"],
            ["long_analysis", "ready"], ["long_analysis", "ready_score"],
        ],
        "signal": [
            ["long_signal_score"], ["long_score"], ["signal_long_score"],
            ["long_scores", "signal"], ["long_scores", "signal_score"], ["long_scores", "score"],
            ["long", "signal"], ["long", "signal_score"], ["long", "score"],
            ["long_result", "signal"], ["long_result", "signal_score"], ["long_result", "score"],
            ["long_analysis", "signal"], ["long_analysis", "signal_score"], ["long_analysis", "score"],
        ],
        "verify": [
            ["long_verify_score"], ["long_verify"], ["verify_long_score"],
            ["long_scores", "verify"], ["long_scores", "verify_score"],
            ["long", "verify"], ["long", "verify_score"],
            ["long_result", "verify"], ["long_result", "verify_score"],
            ["long_analysis", "verify"], ["long_analysis", "verify_score"],
        ],
        "quality": [
            ["long_quality_score"], ["long_quality"], ["quality_long_score"],
            ["long_scores", "quality"], ["long_scores", "quality_score"],
            ["long", "quality"], ["long", "quality_score"],
            ["long_result", "quality"], ["long_result", "quality_score"],
            ["long_analysis", "quality"], ["long_analysis", "quality_score"],
        ],
    }
    val = _deep_get_numeric(res, path_map.get(metric, []), None)
    if val is not None:
        return val

    fallback_keys = {
        "candidate": "candidate_score",
        "ready": "ready_score",
        "signal": "score",
        "verify": "verify_score",
        "quality": "quality_score",
    }
    key = fallback_keys.get(metric)
    if key in res:
        fv = safe_float(res.get(key), None)
        if fv is not None and fv > 0:
            return fv
    return None


def _estimate_long_candidate_from_note(note: str) -> float:
    n = (note or "").lower()
    score = 0.0
    if "ict discount" in n:
        score += 4
    if "alıcı savunması" in n:
        score += 4
    if "alış baskın" in n:
        score += 4
    if "orderbook bid" in n:
        score += 3
    if "choch yukarı" in n:
        score += 4
    if "ema9 üstü" in n:
        score += 2
    if "ema21 üstü" in n:
        score += 2
    if "rsi toparlanıyor" in n:
        score += 2
    if "alt fitil" in n:
        score += 2
    return min(score, LONG_MIN_CANDIDATE_SCORE - 0.01)


def _normalize_why_gate(
    res: Dict[str, Any],
    blocker: str,
    actual: Any = None,
    required: Any = None,
    note: str = "",
) -> Tuple[str, Any, Any, str]:
    """
    IGNORE gibi belirsiz kayıtları gerçek kapıya çevirir.
    Böylece /neden içinde 'IGNORE' yerine LONG_MIN_SIGNAL_SCORE, MIN_CANDIDATE_SCORE vb. görünür.
    """
    direction = str(res.get("direction", "SHORT")).upper()
    b = str(blocker or res.get("why_blocker") or "").strip()
    n = str(note or res.get("why_note") or res.get("reason") or "").strip()

    # Zaten gerçek kapı geldiyse bozma.
    real_gate_keywords = ("SCORE", "QUALITY", "RR", "CONFIRM", "GUARD", "BINANCE", "TREND", "ICT", "MA", "SR", "REGIME", "MACRO", "ENTRY")
    if b and b.upper() != "IGNORE" and any(k in b.upper() for k in real_gate_keywords):
        return b, actual, required, n or "-"

    cand = safe_float(res.get("candidate_score", 0))
    ready = safe_float(res.get("ready_score", 0))
    verify = safe_float(res.get("verify_score", 0))
    total_score = safe_float(res.get("score", 0))
    quality = safe_float(res.get("quality_score", 0))
    rr = safe_float(res.get("rr", 0))

    if direction == "LONG":
        long_cand = _read_long_metric(res, "candidate")
        long_ready = _read_long_metric(res, "ready")
        long_signal = _read_long_metric(res, "signal")
        long_verify = _read_long_metric(res, "verify")
        long_quality = _read_long_metric(res, "quality")

        estimated = False
        if long_cand is None:
            est = _estimate_long_candidate_from_note(n)
            if est > 0:
                long_cand = est
                estimated = True

        if long_cand is None:
            return "LONG_MIN_CANDIDATE_SCORE", "OKUNAMADI", LONG_MIN_CANDIDATE_SCORE, "Long aday skoru koddan okunamadı; not var ama skor alanı bulunamadı." + (f" | {n}" if n else "")

        extra = " (notlardan tahmini)" if estimated else ""
        if long_cand < LONG_MIN_CANDIDATE_SCORE:
            return "LONG_MIN_CANDIDATE_SCORE", long_cand, LONG_MIN_CANDIDATE_SCORE, f"Long aday skoru eşik altında kaldı{extra}." + (f" | {n}" if n else "")
        if long_ready is not None and long_ready < LONG_MIN_READY_SCORE:
            return "LONG_MIN_READY_SCORE", long_ready, LONG_MIN_READY_SCORE, "Long hazır skoru eşik altında kaldı." + (f" | {n}" if n else "")
        if long_signal is not None and long_signal < LONG_MIN_SIGNAL_SCORE:
            return "LONG_MIN_SIGNAL_SCORE", long_signal, LONG_MIN_SIGNAL_SCORE, "Long sinyal skoru eşik altında kaldı." + (f" | {n}" if n else "")
        if long_verify is not None and long_verify < LONG_MIN_VERIFY_SCORE:
            return "LONG_MIN_VERIFY_SCORE", long_verify, LONG_MIN_VERIFY_SCORE, "Long doğrulama skoru eşik altında kaldı." + (f" | {n}" if n else "")
        if long_quality is not None and long_quality < LONG_MIN_QUALITY_SCORE:
            return "LONG_MIN_QUALITY_SCORE", long_quality, LONG_MIN_QUALITY_SCORE, "Long kalite skoru eşik altında kaldı." + (f" | {n}" if n else "")
        return "LONG_FINAL_FILTER", long_signal if long_signal is not None else long_cand, LONG_MIN_SIGNAL_SCORE, n or "Long final filtreden geçmedi."

    # SHORT
    if cand < MIN_CANDIDATE_SCORE:
        return "MIN_CANDIDATE_SCORE", cand, MIN_CANDIDATE_SCORE, "Aday skoru eşik altında kaldı." + (f" | {n}" if n else "")
    if ready < MIN_READY_SCORE:
        return "MIN_READY_SCORE", ready, MIN_READY_SCORE, "Hazır skoru eşik altında kaldı." + (f" | {n}" if n else "")
    if total_score < MIN_SIGNAL_SCORE:
        return "MIN_SIGNAL_SCORE", total_score, MIN_SIGNAL_SCORE, "Sinyal skoru eşik altında kaldı." + (f" | {n}" if n else "")
    if verify < MIN_VERIFY_SCORE_FOR_SIGNAL:
        return "MIN_VERIFY_SCORE_FOR_SIGNAL", verify, MIN_VERIFY_SCORE_FOR_SIGNAL, "Doğrulama skoru eşik altında kaldı." + (f" | {n}" if n else "")
    if quality < MIN_QUALITY_SCORE:
        return "MIN_QUALITY_SCORE", quality, MIN_QUALITY_SCORE, "Kalite skoru eşik altında kaldı." + (f" | {n}" if n else "")
    if rr and rr < MIN_RR_TP1:
        return "MIN_RR_TP1", rr, MIN_RR_TP1, "RR eşik altında kaldı." + (f" | {n}" if n else "")
    return b or "FINAL_FILTER", actual, required, n or "Final filtreden geçmedi."


def _why_rank_from_record(rec: Dict[str, Any]) -> float:
    stage = str(rec.get("stage", "")).upper()
    direction = str(rec.get("direction", "")).upper()
    blocker = str(rec.get("blocker", "")).upper()
    note = str(rec.get("note", ""))

    rank = 0.0
    if stage == "SIGNAL":
        rank += 100
    elif stage == "READY":
        rank += 80
    elif stage == "HOT":
        rank += 60
    else:
        rank += 20

    actual = safe_float(rec.get("actual", 0), 0)
    required = safe_float(rec.get("required", 0), 0)
    if required > 0:
        ratio = actual / required
        rank += clamp(ratio, 0, 1.25) * 30

    rank += _why_positive_note_score(note, direction)

    # Sinyal eşiğine çok uzak ham gürültüyü düşük sırala.
    if blocker in ("MIN_CANDIDATE_SCORE", "LONG_MIN_CANDIDATE_SCORE") and required > 0:
        if actual / required < WHY_MIN_NEAR_MISS_RATIO:
            rank -= 20

    # Belirsiz IGNORE artık normalde kalmamalı; kalırsa alta düşsün.
    if blocker == "IGNORE":
        rank -= 30

    return rank


def _choose_better_why_record(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not a:
        return b
    if not b:
        return a

    ra = _why_rank_from_record(a)
    rb = _why_rank_from_record(b)

    if abs(ra - rb) > 5:
        return a if ra > rb else b

    # Yakın güçteyse daha yeni canlı görüleni seç.
    la = safe_float(a.get("last_seen_ts", a.get("ts", 0)), 0)
    lb = safe_float(b.get("last_seen_ts", b.get("ts", 0)), 0)
    return a if la >= lb else b


def remember_why_blocked(
    res: Optional[Dict[str, Any]],
    blocker: str,
    actual: Any = None,
    required: Any = None,
    note: str = "",
) -> None:
    """
    /neden komutu için son gönderilmeyen adayları hafızaya alır.

    V4:
    - Bulduğum saat = fırsatın ilk yakalandığı saat.
    - /neden yazılan saat değildir.
    - IGNORE yerine gerçek LONG/SHORT kapısı yazılır.
    - Aynı coin aynı mesajda hem LONG hem SHORT olarak şişirilmez; /neden gösterirken en güçlü aktif fırsat seçilir.
    """
    try:
        if not isinstance(res, dict):
            return
        symbol = normalize_symbol(str(res.get("symbol", "")))
        if not symbol:
            return

        direction = str(res.get("direction", "SHORT")).upper()
        blocker_name, actual_v, required_v, note_v = _normalize_why_gate(res, blocker, actual, required, note)

        if WHY_HIDE_EMPTY_IGNORE and blocker_name == "IGNORE" and not note_v:
            return

        now_ts = time.time()
        dir_key = f"{direction}:{symbol}"
        key = f"{direction}:{symbol}:{blocker_name}"

        wb = memory.setdefault("why_blocked", {"latest": [], "by_symbol": {}})
        wb.setdefault("latest", [])
        wb.setdefault("by_symbol", {})

        # Fırsat ilk saatini korumak için aynı coin+yön kaydını esas al.
        old_rec = (
            wb["by_symbol"].get(key)
            or wb["by_symbol"].get(dir_key)
            or {}
        )

        raw_found_ts = (
            res.get("found_ts")
            or res.get("candidate_found_ts")
            or res.get("first_seen_ts")
            or res.get("signal_candidate_ts")
            or 0
        )
        found_ts = safe_float(raw_found_ts, 0)

        current_entry = safe_float(res.get("entry", res.get("price", res.get("last_price", 0))), 0)
        found_entry = safe_float(
            res.get("found_entry", res.get("candidate_found_entry", res.get("first_seen_entry", 0))),
            0
        )

        same_setup = False
        if found_ts <= 0 and old_rec:
            old_entry = safe_float(old_rec.get("found_entry", old_rec.get("entry", 0)), 0)
            new_entry = current_entry
            old_direction = str(old_rec.get("direction", "")).upper()
            same_setup = old_direction == direction
            if same_setup and old_entry > 0 and new_entry > 0:
                diff_pct = abs(pct_change(old_entry, new_entry))
                same_setup = diff_pct <= 0.75
            if same_setup:
                found_ts = safe_float(old_rec.get("found_ts", old_rec.get("ts", 0)), 0)
                found_entry = safe_float(old_rec.get("found_entry", old_rec.get("entry", 0)), 0)

        if found_ts <= 0:
            found_ts = now_ts

        # Bulduğum saat ile Giriş aynı ana ait olmalı.
        # Aynı fırsat tekrar görülürse ilk saat ve ilk giriş korunur.
        if found_entry <= 0:
            found_entry = current_entry

        rec = {
            "ts": now_ts,
            "found_ts": found_ts,
            "last_seen_ts": now_ts,
            "symbol": symbol,
            "direction": direction,
            "stage": str(res.get("stage", "-")),
            "blocker": blocker_name,
            "actual": actual_v,
            "required": required_v,
            "note": str(note_v or "-")[:600],
            "score": safe_float(res.get("score", 0)),
            "candidate_score": safe_float(res.get("candidate_score", 0)),
            "ready_score": safe_float(res.get("ready_score", 0)),
            "verify_score": safe_float(res.get("verify_score", 0)),
            "quality_score": safe_float(res.get("quality_score", 0)),
            "entry": found_entry,
            "found_entry": found_entry,
            "last_entry": current_entry,
            "rr": safe_float(res.get("rr", 0)),
            "close5": safe_float((res.get("close_confirm_gate") or {}).get("score5", 0)) if isinstance(res.get("close_confirm_gate"), dict) else 0,
            "close15": safe_float((res.get("close_confirm_gate") or {}).get("score15", 0)) if isinstance(res.get("close_confirm_gate"), dict) else 0,
        }
        rec["rank"] = _why_rank_from_record(rec)

        # latest içinde aynı coin+yön+kapı tekrar çoğalmasın.
        cleaned_latest = []
        for x in wb.get("latest", []):
            if not isinstance(x, dict):
                continue
            x_key = f"{str(x.get('direction', '')).upper()}:{normalize_symbol(str(x.get('symbol', '')))}:{str(x.get('blocker', ''))}"
            if x_key == key:
                continue
            cleaned_latest.append(x)
        cleaned_latest.append(rec)

        limit = max(5, int(WHY_HISTORY_LIMIT))
        wb["latest"] = cleaned_latest[-limit:]

        wb["by_symbol"][key] = rec
        wb["by_symbol"][dir_key] = _choose_better_why_record(wb["by_symbol"].get(dir_key), rec) or rec
        wb["by_symbol"][symbol] = _choose_better_why_record(wb["by_symbol"].get(symbol), rec) or rec

        stats["why_blocked_recorded"] = stats.get("why_blocked_recorded", 0) + 1
    except Exception as e:
        logger.warning("Neden hafızası yazılamadı: %s", e)


def _fmt_why_value(v: Any) -> str:
    if v is None or v == "":
        return "-"
    try:
        fv = float(v)
        return f"{fv:.2f}"
    except Exception:
        return str(v)


def format_why_record(rec: Dict[str, Any], idx: int = 1) -> str:
    # Bulduğum saat = adayın ilk bulunduğu saat.
    # /neden yazıldığı an veya son tarama saati değildir.
    ts = safe_float(rec.get("found_ts", rec.get("ts", 0)), 0)
    if ts:
        try:
            found_time = datetime.fromtimestamp(ts, TZ).strftime("%H.%M")
        except Exception:
            found_time = tr_str(ts)
    else:
        found_time = "-"

    actual = _fmt_why_value(rec.get("actual"))
    required = _fmt_why_value(rec.get("required"))
    compare = f"{actual} / {required}" if required != "-" else actual

    entry_val = safe_float(rec.get("found_entry", rec.get("entry", 0)), 0)
    entry_txt = fmt_num(entry_val) if entry_val > 0 else "-"

    last_entry_val = safe_float(rec.get("last_entry", 0), 0)
    last_line = ""
    if last_entry_val > 0 and entry_val > 0 and abs(pct_change(entry_val, last_entry_val)) >= 0.35:
        last_line = f"Son görülen fiyat: {fmt_num(last_entry_val)}\n"

    return (
        f"{rec.get('symbol', '-')} | {rec.get('direction', '-')}\n"
        f"Bulduğum saat: {found_time}\n"
        f"Giriş: {entry_txt}\n"
        f"{last_line}"
        f"Kapı: {rec.get('blocker', '-')}\n"
        f"Değer: {compare}\n"
        f"Not: {rec.get('note', '-')}"
    )


async def cmd_neden(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_memory_shape()
    wb = memory.get("why_blocked", {})
    latest = [x for x in list(wb.get("latest", [])) if isinstance(x, dict)]
    by_symbol = wb.get("by_symbol", {})

    now_ts = time.time()

    def is_active_rec(r: Dict[str, Any]) -> bool:
        last_seen = safe_float(r.get("last_seen_ts", r.get("ts", 0)), 0)
        if not last_seen:
            return False
        return now_ts - last_seen <= WHY_ACTIVE_TTL_SEC

    def best_for_symbol(sym: str) -> Optional[Dict[str, Any]]:
        sym = normalize_symbol(sym)
        candidates: List[Dict[str, Any]] = []
        for r in latest:
            if normalize_symbol(str(r.get("symbol", ""))) == sym and is_active_rec(r):
                candidates.append(r)
        for k, r in by_symbol.items():
            if isinstance(r, dict) and normalize_symbol(str(r.get("symbol", ""))) == sym and is_active_rec(r):
                candidates.append(r)
        best = None
        for r in candidates:
            best = _choose_better_why_record(best, r)
        return best

    if context.args:
        raw = context.args[0].upper().replace("/", "-")
        sym = normalize_symbol(raw)
        rec = best_for_symbol(sym)
        if not rec:
            await update.message.reply_text(f"{sym} için aktif kayıtlı engel sebebi yok.")
            return
        await update.message.reply_text("🧾 SON ENGEL SEBEBİ\n\n" + format_why_record(rec, 1))
        return

    if not latest:
        await update.message.reply_text("Henüz kayıtlı engellenen aday yok. Bot adayları gördükçe /neden burada dolacak.")
        return

    # Aktif kayıtları sembol bazında tek fırsata indir.
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in latest:
        if not is_active_rec(r):
            continue
        sym = normalize_symbol(str(r.get("symbol", "")))
        if not sym:
            continue
        if WHY_SHOW_ONLY_BEST_PER_SYMBOL:
            grouped[sym] = _choose_better_why_record(grouped.get(sym), r) or r
        else:
            grouped[f"{sym}:{r.get('direction')}:{r.get('blocker')}"] = r

    rows = list(grouped.values())
    rows.sort(key=lambda r: safe_float(r.get("last_seen_ts", r.get("ts", 0)), 0), reverse=True)
    rows = rows[:8]

    if not rows:
        await update.message.reply_text("Şu an aktif gönderilmeyen fırsat kaydı yok.")
        return

    text_msg = "🧾 SON GÖNDERİLMEYEN FIRSATLAR\n\n" + "\n\n".join(format_why_record(r, i + 1) for i, r in enumerate(rows))
    if len(text_msg) > 3900:
        text_msg = text_msg[:3900] + "\n..."
    await update.message.reply_text(text_msg)



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
                "hot": {}, "trend_watch": {}, "signals": {}, "follows": {}, "stats": {}, "daily_short_sent": {}, "daily_long_sent": {},
                "last_signal_ts": 0.0, "last_diag_ts": 0.0
            }
    else:
        ensure_memory_shape()


def save_memory() -> None:
    try:
        ensure_memory_shape()
        def clean_for_json(obj):
            import datetime as dt
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(v) for v in obj]
            elif isinstance(obj, (dt.datetime, dt.date)):
                return obj.isoformat()
            elif isinstance(obj, set):
                return list(obj)
            elif hasattr(obj, '__dict__'):
                return str(obj)
            return obj
        clean_memory = clean_for_json(memory)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_memory, f, ensure_ascii=False, indent=2)
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
        if is_blocked_coin_symbol(sym):
            hot.pop(sym, None)
            continue
        last_seen = safe_float(hot[sym].get("last_seen", 0))
        if now_ts - last_seen > HOT_TTL_SEC:
            hot.pop(sym, None)
    trend_watch = memory.get("trend_watch", {})
    for sym in list(trend_watch.keys()):
        if is_blocked_coin_symbol(sym):
            trend_watch.pop(sym, None)
            continue
        last_seen = safe_float(trend_watch[sym].get("last_seen", 0))
        if now_ts - last_seen > TREND_WATCH_TTL_SEC:
            trend_watch.pop(sym, None)
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
    daily_long_sent = memory.get("daily_long_sent", {})
    for day_key in list(daily_long_sent.keys()):
        if day_key != today_key:
            try:
                day_dt = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=TZ)
                if now_ts - day_dt.timestamp() > 7 * 24 * 3600:
                    daily_long_sent.pop(day_key, None)
            except Exception:
                daily_long_sent.pop(day_key, None)
    cleanup_symbol_fail_state()


def cleanup_runtime_caches() -> Dict[str, int]:
    """REST polling cache'lerini periyodik temizler; uzun çalışmada bellek şişmesini azaltır."""
    now_ts = time.time()
    removed = {"kline": 0, "ticker": 0, "orderbook": 0, "trades": 0, "oi": 0, "funding": 0, "cvd": 0}

    def prune_tuple_cache(cache: Dict[str, Tuple[float, Any]], ttl: float, key: str) -> None:
        for ck in list(cache.keys()):
            try:
                ts = safe_float(cache[ck][0], 0)
            except Exception:
                ts = 0
            if not ts or now_ts - ts > ttl:
                cache.pop(ck, None)
                removed[key] += 1

    prune_tuple_cache(kline_cache, max(60, KLINE_CACHE_SEC * 20), "kline")
    prune_tuple_cache(ticker_cache, max(60, TICKER_CACHE_SEC * 20), "ticker")
    prune_tuple_cache(orderbook_cache, max(30, GORUNMEYEN_YUZ_BOOK_CACHE_SEC * 40), "orderbook")
    prune_tuple_cache(trades_cache, max(30, GORUNMEYEN_YUZ_TRADE_CACHE_SEC * 40), "trades")
    prune_tuple_cache(oi_cache, max(120, OI_CACHE_SEC * 10), "oi")
    prune_tuple_cache(funding_cache, max(300, FUNDING_CACHE_SEC * 10), "funding")
    prune_tuple_cache(cvd_cache, max(120, CVD_CACHE_SEC * 10), "cvd")

    # Orderbook/spoofing hafızası küçük kalsın.
    for mp in (orderbook_memory, spoofing_memory):
        for sym in list(mp.keys()):
            ts = safe_float(mp.get(sym, {}).get("ts", 0), 0)
            if not ts or now_ts - ts > 3600:
                mp.pop(sym, None)

    return removed


async def cache_cleanup_loop() -> None:
    while True:
        try:
            removed = cleanup_runtime_caches()
            total_removed = sum(removed.values())
            if total_removed:
                logger.info("Cache temizlendi: %s", removed)
        except Exception as e:
            logger.exception("cache_cleanup_loop hata: %s", e)
        await asyncio.sleep(300)


def note_symbol_fail(symbol: str, reason: str = "") -> None:
    now_ts = time.time()
    rec = symbol_fail_state.setdefault(symbol, {"streak": 0, "last_ts": 0.0, "block_until": 0.0, "last_reason": ""})
    rec["streak"] = int(safe_float(rec.get("streak", 0))) + 1
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
# BINANCE FUTURES API (YENI - V6 WHALE EYE)
# =========================================================
def _binance_fapi_sign(params: Dict[str, Any]) -> str:
    query = urlencode(params)
    return hmac.new(
        BINANCE_SECRET_KEY.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def _binance_fapi_get(path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Any:
    url = f"{BINANCE_FAPI_BASE}{path}"
    session = _get_session()
    headers = {}
    if signed and BINANCE_API_KEY:
        headers["X-MBX-APIKEY"] = BINANCE_API_KEY
        if params is None:
            params = {}
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = _binance_fapi_sign(params)
    resp = session.get(url, params=params or {}, headers=headers, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


async def get_open_interest(symbol: str) -> Dict[str, Any]:
    """Open Interest verisi.

    Önce Binance Futures denenir. Binance verisi gelmezse OKX public open-interest
    endpointine otomatik düşer. Böylece BTC-USDT-SWAP gibi OKX sembollerinde Whale Eye
    OI kör kalmaz.
    """
    if not OI_ENGINE_ENABLED:
        return {"enabled": False, "source": "KAPALI", "oi": 0, "oi_change_pct": 0, "reason": "OI motoru kapalı"}

    okx_symbol = normalize_symbol(symbol)
    binance_symbol = normalize_binance_symbol(symbol)
    cache_key = f"OI:{okx_symbol}"
    cached = oi_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= OI_CACHE_SEC:
        return cached[1]

    errors: List[str] = []

    # 1) Binance USD-M Futures OI
    try:
        data = await asyncio.to_thread(
            _binance_fapi_get,
            "/fapi/v1/openInterest",
            {"symbol": binance_symbol}
        )
        oi = safe_float(data.get("openInterest", 0))
        if oi > 0:
            result = {
                "enabled": True,
                "source": "BINANCE_FAPI",
                "oi": oi,
                "timestamp": now_ts,
                "reason": "Binance Futures OI okundu",
            }
            oi_cache[cache_key] = (now_ts, result)
            return result
        errors.append("Binance OI boş/0 döndü")
    except Exception as e:
        err = f"Binance OI hata: {type(e).__name__}: {str(e)[:160]}"
        errors.append(err)
        logger.warning("%s %s", err, binance_symbol)

    # 2) OKX SWAP OI fallback
    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/public/open-interest",
            {"instType": OKX_INST_TYPE, "instId": okx_symbol},
        )
        row = data[0] if data else {}
        oi = safe_float(row.get("oi", 0))
        oi_ccy = safe_float(row.get("oiCcy", 0))
        oi_usd = safe_float(row.get("oiUsd", 0))
        chosen_oi = oi if oi > 0 else (oi_ccy if oi_ccy > 0 else oi_usd)
        if chosen_oi > 0:
            row_ts = safe_float(row.get("ts", 0))
            result = {
                "enabled": True,
                "source": "OKX_PUBLIC",
                "oi": chosen_oi,
                "oi_contracts": oi,
                "oi_ccy": oi_ccy,
                "oi_usd": oi_usd,
                "timestamp": (row_ts / 1000.0) if row_ts > 10_000_000_000 else now_ts,
                "reason": "Binance OI yoktu; OKX open-interest fallback okundu",
                "fallback_errors": " | ".join(errors[:3]),
            }
            oi_cache[cache_key] = (now_ts, result)
            return result
        errors.append("OKX OI boş/0 döndü")
    except Exception as e:
        err = f"OKX OI hata: {type(e).__name__}: {str(e)[:160]}"
        errors.append(err)
        logger.warning("%s %s", err, okx_symbol)

    return {
        "enabled": False,
        "source": "VERI_YOK",
        "oi": 0,
        "oi_change_pct": 0,
        "reason": "OI verisi alınamadı: " + " | ".join(errors[:4]),
    }


async def get_funding_rate(symbol: str) -> Dict[str, Any]:
    """Funding rate verisi.

    Önce Binance Futures premiumIndex denenir. Binance verisi gelmezse OKX public
    funding-rate endpointine düşer. Oran yüzde olarak döner: 0.0100 = %0.0100.
    """
    if not FUNDING_ENGINE_ENABLED:
        return {"enabled": False, "source": "KAPALI", "rate": 0.0, "reason": "Funding motoru kapalı"}

    okx_symbol = normalize_symbol(symbol)
    binance_symbol = normalize_binance_symbol(symbol)
    cache_key = f"FUNDING:{okx_symbol}"
    cached = funding_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= FUNDING_CACHE_SEC:
        return cached[1]

    errors: List[str] = []

    # 1) Binance funding
    try:
        data = await asyncio.to_thread(
            _binance_fapi_get,
            "/fapi/v1/premiumIndex",
            {"symbol": binance_symbol}
        )
        if isinstance(data, dict) and "lastFundingRate" in data:
            rate = safe_float(data.get("lastFundingRate", 0)) * 100.0
            result = {
                "enabled": True,
                "source": "BINANCE_FAPI",
                "rate": rate,
                "next_funding_time": safe_float(data.get("nextFundingTime", 0)),
                "mark_price": safe_float(data.get("markPrice", 0)),
                "reason": "Binance Futures funding okundu",
            }
            funding_cache[cache_key] = (now_ts, result)
            return result
        errors.append("Binance funding boş/alan yok")
    except Exception as e:
        err = f"Binance Funding hata: {type(e).__name__}: {str(e)[:160]}"
        errors.append(err)
        logger.warning("%s %s", err, binance_symbol)

    # 2) OKX funding fallback
    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/public/funding-rate",
            {"instId": okx_symbol},
        )
        row = data[0] if data else {}
        if row and "fundingRate" in row:
            rate = safe_float(row.get("fundingRate", 0)) * 100.0
            result = {
                "enabled": True,
                "source": "OKX_PUBLIC",
                "rate": rate,
                "next_funding_time": safe_float(row.get("nextFundingTime", 0)),
                "funding_time": safe_float(row.get("fundingTime", 0)),
                "reason": "Binance funding yoktu; OKX funding-rate fallback okundu",
                "fallback_errors": " | ".join(errors[:3]),
            }
            funding_cache[cache_key] = (now_ts, result)
            return result
        errors.append("OKX funding boş/alan yok")
    except Exception as e:
        err = f"OKX Funding hata: {type(e).__name__}: {str(e)[:160]}"
        errors.append(err)
        logger.warning("%s %s", err, okx_symbol)

    return {
        "enabled": False,
        "source": "VERI_YOK",
        "rate": 0.0,
        "reason": "Funding verisi alınamadı: " + " | ".join(errors[:4]),
    }
# =========================================================
# V6 WHALE EYE MOTORLARI
# =========================================================

async def analyze_whale_eye_open_interest(
    symbol: str,
    price: float,
    price_change_5m: float,
    direction: str = "SHORT"
) -> Dict[str, Any]:
    """
    OPEN INTEREST DELTA ANALİZİ
    Balinaların gerçek pozisyon değişimini OI-Price uyumsuzluğundan okur.

    DÖRT SENARYO:
    1. Fiyat DÜŞÜYOR + OI ARTIYOR = Balinalar SHORT açıyor (En güçlü SHORT sinyali)
    2. Fiyat YÜKSELİYOR + OI DÜŞÜYOR = Balinalar LONG kapıyor (TEPE sinyali)
    3. Fiyat DÜŞÜYOR + OI DÜŞÜYOR = Long likidasyonu (Panik, trend devam edebilir)
    4. Fiyat YÜKSELİYOR + OI ARTIYOR = Yeni LONG girişi (Trend devam)
    """
    if not OI_ENGINE_ENABLED:
        return {"enabled": False, "score": 0, "divergence_type": "KAPALI", "reason": "OI motoru kapalı"}

    oi_data = await get_open_interest(symbol)
    if not oi_data.get("enabled"):
        return {
            "enabled": False,
            "score": 0,
            "divergence_type": "VERI_YOK",
            "reason": oi_data.get("reason", "OI verisi alınamadı"),
            "source": oi_data.get("source", "VERI_YOK"),
            "current_oi": 0,
            "prev_oi": 0,
            "oi_change_pct": 0,
            "price_change_pct": 0,
        }

    # Önceki OI değerini memory'den al
    oi_memory_key = f"oi_history:{symbol}"
    prev_oi_rec = memory.get("signals", {}).get(oi_memory_key, {})
    prev_oi = safe_float(prev_oi_rec.get("oi", 0))
    prev_price = safe_float(prev_oi_rec.get("price", 0))
    current_oi = safe_float(oi_data.get("oi", 0))

    # Şimdiki OI'yi kaydet
    memory.setdefault("signals", {})[oi_memory_key] = {
        "oi": current_oi,
        "price": price,
        "ts": time.time()
    }

    if prev_oi <= 0 or prev_price <= 0:
        return {
            "enabled": True,
            "score": 0,
            "divergence_type": "BEKLIYOR",
            "reason": f"OI takip başladı. Güncel OI: {current_oi:,.0f} | Kaynak: {oi_data.get('source', '-')}",
            "source": oi_data.get("source", "-"),
            "current_oi": current_oi,
            "prev_oi": 0,
            "oi_change_pct": 0,
            "price_change_pct": 0
        }

    oi_change_pct = pct_change(prev_oi, current_oi)
    price_change_pct = pct_change(prev_price, price)

    score = 0.0
    divergence_type = "NÖTR"
    reasons: List[str] = []

    # SENARYO 1: Fiyat düşüyor, OI artıyor = BALİNA SHORT AÇIYOR
    if price_change_pct <= -OI_BEARISH_PRICE_DROP_PCT and oi_change_pct >= OI_MIN_CHANGE_PCT:
        divergence_type = "BALINA_SHORT_ACIYOR"
        score += 12.0
        reasons.append(f"🐋 Fiyat %{price_change_pct:.2f} düşerken OI %{oi_change_pct:.2f} arttı")
        reasons.append("Balinalar agresif short açıyor - en güçlü short sinyali")
        stats["oi_short_diverge"] += 1

    # SENARYO 2: Fiyat yükseliyor, OI düşüyor = BALİNA LONG KAPATIYOR (TEPE)
    elif price_change_pct >= OI_BULLISH_PRICE_RISE_PCT and oi_change_pct <= -OI_MIN_CHANGE_PCT:
        divergence_type = "BALINA_LONG_KAPATIYOR"
        score += 10.0
        reasons.append(f"🐋 Fiyat %{price_change_pct:.2f} yükselirken OI %{oi_change_pct:.2f} düştü")
        reasons.append("Balinalar long pozisyonlarını zirvede kapatıyor - TEPE uyarısı")
        stats["oi_short_diverge"] += 1

    # SENARYO 3: Fiyat düşüyor, OI düşüyor = Long likidasyonu
    elif price_change_pct <= -OI_BEARISH_PRICE_DROP_PCT and oi_change_pct <= -OI_MIN_CHANGE_PCT:
        divergence_type = "LONG_LIKIDASYONU"
        score += 4.0
        reasons.append(f"📉 Fiyat %{price_change_pct:.2f} düşerken OI %{oi_change_pct:.2f} düştü - Long'lar likidite oluyor")

    # SENARYO 4: Fiyat yükseliyor, OI artıyor = Yeni long girişi
    elif price_change_pct >= OI_BULLISH_PRICE_RISE_PCT and oi_change_pct >= OI_MIN_CHANGE_PCT:
        divergence_type = "YENI_LONG_GIRISI"
        score += 2.0
        reasons.append(f"📈 Fiyat %{price_change_pct:.2f} yükselirken OI %{oi_change_pct:.2f} arttı - Yeni long pozisyonları")

    if direction == "LONG":
        # Long için tersine çevir
        if divergence_type == "BALINA_SHORT_ACIYOR":
            score = -8.0  # Long için negatif
        elif divergence_type == "BALINA_LONG_KAPATIYOR":
            score = -6.0
        elif divergence_type == "LONG_LIKIDASYONU":
            score = 8.0  # Long'lar likidite oldu, dipten long fırsatı
            divergence_type = "LONG_FIRSATI_LIKIDASYON_SONRASI"
            stats["oi_long_diverge"] += 1

    return {
        "enabled": True,
        "score": round(score, 2),
        "divergence_type": divergence_type,
        "reason": (" | ".join(reasons) if reasons else "OI fiyat uyumlu, balina izi yok") + f" | Kaynak: {oi_data.get('source', '-')}",
        "source": oi_data.get("source", "-"),
        "current_oi": current_oi,
        "prev_oi": prev_oi,
        "oi_change_pct": round(oi_change_pct, 2),
        "price_change_pct": round(price_change_pct, 2)
    }


async def analyze_whale_eye_funding(
    symbol: str,
    price: float,
    direction: str = "SHORT"
) -> Dict[str, Any]:
    """
    FUNDING RATE DEDEKTÖRÜ
    Aşırı fonlama oranları ters işlem fırsatıdır.

    - Funding > 0.05% = Perakende aşırı LONG = SHORT fırsatı
    - Funding > 0.10% = EKSTREM perakende LONG = Güçlü SHORT fırsatı
    - Funding < -0.03% = Perakende aşırı SHORT = LONG fırsatı
    """
    if not FUNDING_ENGINE_ENABLED:
        return {"enabled": False, "score": 0, "funding_signal": "KAPALI", "reason": "Funding motoru kapalı"}

    funding_data = await get_funding_rate(symbol)
    if not funding_data.get("enabled"):
        return {
            "enabled": False,
            "score": 0,
            "funding_signal": "VERI_YOK",
            "funding_rate": 0.0,
            "source": funding_data.get("source", "VERI_YOK"),
            "reason": funding_data.get("reason", "Funding verisi alınamadı"),
        }

    rate = safe_float(funding_data.get("rate", 0.0))
    source = str(funding_data.get("source", "-"))

    score = 0.0
    signal = "NÖTR"
    reasons: List[str] = []

    if direction == "SHORT":
        if rate >= FUNDING_EXTREME_THRESHOLD:
            score += FUNDING_EXTREME_SHORT_BONUS
            signal = "EKSTREM_SHORT_FIRSATI"
            reasons.append(f"🚨 Funding %{rate:.4f} - Perakende aşırı LONG sıkışmış")
            reasons.append("Balinalar short açıp funding toplar - YÜKSEK SHORT FıRSATI")
            stats["funding_short_bonus"] += 1
        elif rate >= FUNDING_SHORT_THRESHOLD:
            score += FUNDING_SHORT_BONUS
            signal = "SHORT_FIRSATI"
            reasons.append(f"⚠️ Funding %{rate:.4f} - Perakende long tarafında kalabalık")
            reasons.append("Funding pozitif = Short'lara ödeme yapılıyor - SHORT fırsatı")
            stats["funding_short_bonus"] += 1
        elif rate <= FUNDING_LONG_THRESHOLD:
            score -= FUNDING_LONG_BONUS
            signal = "LONG_AGIRLIKLI"
            reasons.append(f"🔻 Funding %{rate:.4f} - Negatif = Short'lar ödüyor")
    else:  # LONG
        if rate <= -FUNDING_EXTREME_THRESHOLD:
            score += FUNDING_EXTREME_LONG_BONUS
            signal = "EKSTREM_LONG_FIRSATI"
            reasons.append(f"🚨 Funding %{rate:.4f} - Perakende aşırı SHORT sıkışmış")
            stats["funding_long_bonus"] += 1
        elif rate <= FUNDING_LONG_THRESHOLD:
            score += FUNDING_LONG_BONUS
            signal = "LONG_FIRSATI"
            reasons.append(f"⚠️ Funding %{rate:.4f} - Short tarafında kalabalık")
            stats["funding_long_bonus"] += 1
        elif rate >= FUNDING_SHORT_THRESHOLD:
            score -= FUNDING_SHORT_BONUS
            signal = "SHORT_AGIRLIKLI"
            reasons.append(f"🔺 Funding %{rate:.4f} - Pozitif = Long'lar ödüyor")

    return {
        "enabled": True,
        "score": round(score, 2),
        "funding_rate": round(rate, 4),
        "funding_signal": signal,
        "source": source,
        "next_funding_time": funding_data.get("next_funding_time", 0),
        "reason": (" | ".join(reasons) if reasons else f"Funding nötr %{rate:.4f}") + f" | Kaynak: {source}",
    }


async def analyze_whale_eye_spoofing(
    symbol: str,
    price: float,
    direction: str = "SHORT"
) -> Dict[str, Any]:
    """
    ORDERBOOK SPOOFING DEDEKTÖRÜ
    Sahte büyük emirleri (spoofing) tespit eder.

    - Büyük alış duvarı konup aniden çekilmesi = Satıcı tuzağı
    - Büyük satış duvarı konup aniden çekilmesi = Alıcı tuzağı
    - Sürekli yenilenen duvar = Gerçek arz/talep
    """
    if not SPOOFING_ENGINE_ENABLED:
        return {"enabled": False, "score": 0, "spoofing_detected": False, "spoof_type": "KAPALI"}

    symbol_okx = normalize_symbol(symbol)
    cache_key = f"SPOOF:{symbol_okx}"
    cached = orderbook_cache.get(cache_key)
    now_ts = time.time()

    # Güncel orderbook al
    try:
        book = await get_okx_orderbook(symbol_okx, 100)
        if not book.get("ok"):
            return {"enabled": True, "score": 0, "spoofing_detected": False, "spoof_type": "VERI_YOK", "reason": "Orderbook alınamadı"}
    except Exception:
        return {"enabled": True, "score": 0, "spoofing_detected": False, "spoof_type": "VERI_YOK", "reason": "Orderbook hatası"}

    prev_spoof = spoofing_memory.get(symbol_okx, {})
    prev_bid_near = safe_float(prev_spoof.get("bid_near", 0))
    prev_ask_near = safe_float(prev_spoof.get("ask_near", 0))
    prev_ts = safe_float(prev_spoof.get("ts", 0))

    bid_near = safe_float(book.get("bid_near", 0))
    ask_near = safe_float(book.get("ask_near", 0))
    mid = safe_float(book.get("mid", price))

    time_diff = now_ts - prev_ts if prev_ts > 0 else 999

    score = 0.0
    spoof_detected = False
    spoof_type = "YOK"
    reasons: List[str] = []

    # Alış duvarı aniden kayboldu mu? (Spoofing - satıcı tuzağı)
    if prev_bid_near > 0 and bid_near < prev_bid_near * 0.4 and time_diff <= SPOOFING_WALL_VANISH_SEC:
        spoof_detected = True
        spoof_type = "ALIS_DUVARI_KAYBOLDU"
        if direction == "SHORT":
            score += SPOOFING_SHORT_SCORE_BONUS
        reasons.append(f"🪤 Büyük alış duvarı {time_diff:.1f}s içinde kayboldu - Sahte destek!")
        reasons.append("Satıcılar alıcıları tuzağa çekip short açıyor")
        stats["spoofing_detected"] += 1

    # Satış duvarı aniden kayboldu mu? (Alıcı tuzağı)
    if prev_ask_near > 0 and ask_near < prev_ask_near * 0.4 and time_diff <= SPOOFING_WALL_VANISH_SEC:
        spoof_detected = True
        spoof_type = "SATIS_DUVARI_KAYBOLDU"
        if direction == "LONG":
            score += SPOOFING_LONG_SCORE_BONUS
        reasons.append(f"🪤 Büyük satış duvarı {time_diff:.1f}s içinde kayboldu - Sahte direnç!")
        stats["spoofing_detected"] += 1

    # Ani satış duvarı yığılması
    if prev_ask_near > 0 and ask_near > prev_ask_near * SPOOFING_MIN_WALL_SIZE_MULT and time_diff <= 5.0:
        if direction == "SHORT":
            score += SPOOFING_SHORT_SCORE_BONUS * 0.7
        reasons.append(f"🧱 Satış duvarı aniden %{pct_change(prev_ask_near, ask_near):.0f} büyüdü")
        stats["spoofing_detected"] += 1

    # Hafızaya kaydet
    spoofing_memory[symbol_okx] = {
        "ts": now_ts,
        "bid_near": bid_near,
        "ask_near": ask_near,
        "mid": mid
    }

    return {
        "enabled": True,
        "score": round(score, 2),
        "spoofing_detected": spoof_detected,
        "spoof_type": spoof_type,
        "reason": " | ".join(reasons) if reasons else "Orderbook temiz, spoofing yok",
        "bid_near": bid_near,
        "ask_near": ask_near
    }


async def analyze_whale_eye_cvd(
    symbol: str,
    price: float,
    k1: List[List[Any]],
    direction: str = "SHORT"
) -> Dict[str, Any]:
    """
    CUMULATIVE VOLUME DELTA (CVD) ANALİZİ
    Alış/satış hacim agresyonunu ölçer.

    - Fiyat yükseliyor ama CVD düşüyor = Bearish divergence (SHORT fırsatı)
    - Fiyat düşüyor ama CVD yükseliyor = Bullish divergence (LONG fırsatı)
    """
    if not CVD_ENGINE_ENABLED or len(k1) < CVD_LOOKBACK_MIN:
        return {"enabled": False, "score": 0, "divergence": "KAPALI", "reason": "CVD kapalı veya veri yetersiz"}

    # Basitleştirilmiş CVD: Her mumun alış/satış yönünü body'den tahmin et
    cvd = 0.0
    cvd_history: List[float] = []
    price_history: List[float] = []

    lookback = min(CVD_LOOKBACK_MIN, len(k1) - 5)
    for i in range(len(k1) - lookback, len(k1)):
        k = k1[i]
        o = safe_float(k[1])
        c = safe_float(k[4])
        v = safe_float(k[5])
        body = c - o

        if body > 0:
            cvd += v  # Alış hacmi
        elif body < 0:
            cvd -= v  # Satış hacmi

        cvd_history.append(cvd)
        price_history.append(c)

    if len(cvd_history) < 10 or len(price_history) < 10:
        return {"enabled": True, "score": 0, "divergence": "VERI_YOK", "reason": "CVD verisi yetersiz"}

    # CVD trendi
    cvd_first = avg(cvd_history[:5])
    cvd_last = avg(cvd_history[-5:])
    price_first = avg(price_history[:5])
    price_last = avg(price_history[-5:])

    cvd_trend = pct_change(cvd_first, cvd_last)
    price_trend = pct_change(price_first, price_last)

    score = 0.0
    divergence = "NÖTR"
    reasons: List[str] = []

    # Bearish divergence: Fiyat yükseliyor, CVD düşüyor
    if price_trend > 0.3 and cvd_trend < -0.5:
        divergence = "BEARISH_DIVERGENCE"
        if direction == "SHORT":
            score += CVD_SHORT_DIVERGENCE_SCORE
        reasons.append(f"📉 Bearish: Fiyat %{price_trend:.2f}↑ ama CVD %{cvd_trend:.2f}↓ - Satış baskısı gizli")
        stats["cvd_diverge_short"] += 1

    # Bullish divergence: Fiyat düşüyor, CVD yükseliyor
    elif price_trend < -0.3 and cvd_trend > 0.5:
        divergence = "BULLISH_DIVERGENCE"
        if direction == "LONG":
            score += CVD_LONG_DIVERGENCE_SCORE
        reasons.append(f"📈 Bullish: Fiyat %{price_trend:.2f}↓ ama CVD %{cvd_trend:.2f}↑ - Alış baskısı gizli")
        stats["cvd_diverge_long"] += 1

    return {
        "enabled": True,
        "score": round(score, 2),
        "divergence": divergence,
        "cvd_trend_pct": round(cvd_trend, 2),
        "price_trend_pct": round(price_trend, 2),
        "reason": " | ".join(reasons) if reasons else "CVD fiyatla uyumlu"
    }


async def build_full_whale_eye_analysis(
    symbol: str,
    price: float,
    price_change_5m: float,
    k1: List[List[Any]],
    direction: str = "SHORT"
) -> Dict[str, Any]:
    """
    TÜM WHALE EYE MOTORLARINI BIRLEŞTIREN ANA FONKSIYON.
    OI + Funding + Spoofing + CVD = Gerçek balina izi.
    """
    oi = await analyze_whale_eye_open_interest(symbol, price, price_change_5m, direction)
    funding = await analyze_whale_eye_funding(symbol, price, direction)
    spoofing = await analyze_whale_eye_spoofing(symbol, price, direction)
    cvd = await analyze_whale_eye_cvd(symbol, price, k1, direction)

    total_score = (
        safe_float(oi.get("score", 0)) +
        safe_float(funding.get("score", 0)) +
        safe_float(spoofing.get("score", 0)) +
        safe_float(cvd.get("score", 0))
    )

    divergence_types = []
    if oi.get("divergence_type", "NÖTR") not in ("NÖTR", "BEKLIYOR", "KAPALI", "VERI_YOK"):
        divergence_types.append(oi.get("divergence_type"))
    if funding.get("funding_signal", "NÖTR") not in ("NÖTR", "KAPALI", "VERI_YOK"):
        divergence_types.append(funding.get("funding_signal"))
    if spoofing.get("spoofing_detected"):
        divergence_types.append(spoofing.get("spoof_type", "SPOOF"))
    if cvd.get("divergence", "NÖTR") not in ("NÖTR", "KAPALI", "VERI_YOK"):
        divergence_types.append(cvd.get("divergence"))

    whale_confidence = "DÜŞÜK"
    if len(divergence_types) >= 3:
        whale_confidence = "ÇOK_YÜKSEK"
    elif len(divergence_types) >= 2:
        whale_confidence = "YÜKSEK"
    elif len(divergence_types) >= 1:
        whale_confidence = "ORTA"

    all_reasons = []
    for r in [oi.get("reason", ""), funding.get("reason", ""), spoofing.get("reason", ""), cvd.get("reason", "")]:
        if r and r != "NÖTR":
            all_reasons.append(r)

    return {
        "enabled": True,
        "total_score": round(total_score, 2),
        "whale_confidence": whale_confidence,
        "divergence_count": len(divergence_types),
        "divergence_types": divergence_types,
        "oi": oi,
        "funding": funding,
        "spoofing": spoofing,
        "cvd": cvd,
        "reason": " | ".join(all_reasons) if all_reasons else "Balina izi tespit edilmedi"
    }
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
    session = _get_session()
    resp = session.post(url, data=payload, timeout=HTTP_TIMEOUT)
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
    session = _get_session()
    resp = session.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
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

    valid: List[str] = []
    invalid: List[str] = []
    seen = set()
    for sym in COINS:
        ns = normalize_symbol(sym)
        if is_blocked_coin_symbol(ns):
            invalid.append(ns)
            stats["blocked_coin_skip"] += 1
            continue
        if ns in seen:
            continue
        seen.add(ns)
        if ns in instruments:
            valid.append(ns)
        else:
            invalid.append(ns)

    if valid:
        COINS = valid

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


async def get_okx_orderbook(symbol: str, depth: int = 50) -> Dict[str, Any]:
    if not GORUNMEYEN_YUZ_ORDERBOOK_ENABLED:
        return {"enabled": False, "ok": False, "reason": "Orderbook motoru kapalı."}

    symbol = normalize_symbol(symbol)
    cache_key = f"BOOK:{symbol}:{depth}"
    cached = orderbook_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= GORUNMEYEN_YUZ_BOOK_CACHE_SEC:
        return cached[1]

    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/market/books",
            {"instId": symbol, "sz": min(max(depth, 5), 400)},
        )
        if not data:
            raise RuntimeError("empty book")
        book = data[0]
        bids = book.get("bids", []) or []
        asks = book.get("asks", []) or []
        if not bids or not asks:
            raise RuntimeError("empty bids/asks")

        best_bid = safe_float(bids[0][0])
        best_ask = safe_float(asks[0][0])
        mid = (best_bid + best_ask) / 2.0 if best_bid > 0 and best_ask > 0 else 0.0
        band = mid * 0.0018 if mid > 0 else 0.0

        bid_near = 0.0
        ask_near = 0.0
        bid_total = 0.0
        ask_total = 0.0

        for row in bids:
            px = safe_float(row[0])
            sz = safe_float(row[1])
            notional = px * sz
            bid_total += notional
            if mid > 0 and px >= mid - band:
                bid_near += notional

        for row in asks:
            px = safe_float(row[0])
            sz = safe_float(row[1])
            notional = px * sz
            ask_total += notional
            if mid > 0 and px <= mid + band:
                ask_near += notional

        total_near = bid_near + ask_near
        book_pressure = ((ask_near - bid_near) / total_near) if total_near > 0 else 0.0
        total_all = bid_total + ask_total
        full_book_pressure = ((ask_total - bid_total) / total_all) if total_all > 0 else 0.0

        prev = orderbook_memory.get(symbol, {})
        prev_bid_near = safe_float(prev.get("bid_near", 0))
        prev_ask_near = safe_float(prev.get("ask_near", 0))

        bid_wall_pulled = prev_bid_near > 0 and bid_near < prev_bid_near * 0.58
        ask_wall_stacked = prev_ask_near > 0 and ask_near > prev_ask_near * 1.35
        bid_wall_added = prev_bid_near > 0 and bid_near > prev_bid_near * 1.35
        ask_wall_pulled = prev_ask_near > 0 and ask_near < prev_ask_near * 0.58

        orderbook_memory[symbol] = {
            "ts": now_ts,
            "bid_near": bid_near,
            "ask_near": ask_near,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "book_pressure": book_pressure,
            "full_book_pressure": full_book_pressure,
        }

        result = {
            "enabled": True,
            "ok": True,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread_pct": abs(pct_change(best_bid, best_ask)) if best_bid > 0 and best_ask > 0 else 0.0,
            "bid_near": bid_near,
            "ask_near": ask_near,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "book_pressure": round(book_pressure, 4),
            "full_book_pressure": round(full_book_pressure, 4),
            "bid_wall_pulled": bid_wall_pulled,
            "ask_wall_stacked": ask_wall_stacked,
            "bid_wall_added": bid_wall_added,
            "ask_wall_pulled": ask_wall_pulled,
            "reason": "OKX orderbook okundu.",
        }
        orderbook_cache[cache_key] = (now_ts, result)
        stats["orderbook_ok"] += 1
        return result
    except Exception as e:
        stats["orderbook_fail"] += 1
        logger.warning("OKX orderbook alınamadı %s: %s", symbol, e)
        return {"enabled": True, "ok": False, "reason": f"Orderbook alınamadı: {e}"}


async def get_okx_recent_trades(symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    if not GORUNMEYEN_YUZ_TRADES_ENABLED:
        return []

    symbol = normalize_symbol(symbol)
    cache_key = f"TRADES:{symbol}:{limit}"
    cached = trades_cache.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached[0] <= GORUNMEYEN_YUZ_TRADE_CACHE_SEC:
        return cached[1]

    try:
        data = await asyncio.to_thread(
            _okx_get,
            "/api/v5/market/trades",
            {"instId": symbol, "limit": min(max(limit, 10), 500)},
        )
        rows: List[Dict[str, Any]] = []
        for row in data or []:
            rows.append({
                "px": safe_float(row.get("px", 0)),
                "sz": safe_float(row.get("sz", 0)),
                "side": str(row.get("side", "")).lower(),
                "ts": safe_float(row.get("ts", 0)),
            })
        trades_cache[cache_key] = (now_ts, rows)
        stats["trades_ok"] += 1
        return rows
    except Exception as e:
        stats["trades_fail"] += 1
        logger.warning("OKX trade akışı alınamadı %s: %s", symbol, e)
        return []


def analyze_trade_flow(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    buy_notional = 0.0
    sell_notional = 0.0
    buy_count = 0
    sell_count = 0

    for t in trades:
        px = safe_float(t.get("px", 0))
        sz = safe_float(t.get("sz", 0))
        side = str(t.get("side", "")).lower()
        notional = px * sz
        if side == "buy":
            buy_notional += notional
            buy_count += 1
        elif side == "sell":
            sell_notional += notional
            sell_count += 1

    total = buy_notional + sell_notional
    sell_ratio = sell_notional / total if total > 0 else 0.0
    buy_ratio = buy_notional / total if total > 0 else 0.0
    sell_to_buy = sell_notional / max(buy_notional, 1e-9)
    buy_to_sell = buy_notional / max(sell_notional, 1e-9)

    return {
        "buy_notional": buy_notional,
        "sell_notional": sell_notional,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "sell_ratio": round(sell_ratio, 4),
        "buy_ratio": round(buy_ratio, 4),
        "sell_to_buy": round(sell_to_buy, 4),
        "buy_to_sell": round(buy_to_sell, 4),
    }


def normalize_binance_symbol(symbol: str) -> str:
    s = normalize_symbol(symbol)
    parts = s.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    return s.replace("-", "")


def _binance_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{BINANCE_CONFIRM_BASE_URL}{path}"
    session = _get_session()
    resp = session.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
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
    """
    Güvenli EMA.
    Eski sürümde veri period'dan az olduğunda bütün seri avg(values) ile dolduruluyordu;
    bu da bot yeni başladığında/az veri olan coinde sahte EMA ve hatalı skor üretiyordu.
    Burada EMA ilk bardan başlar, her bar sadece o ana kadarki gerçek veriyle güncellenir.
    """
    if not values:
        return []
    if period <= 1:
        return [float(v) for v in values]
    alpha = 2.0 / (period + 1.0)
    out: List[float] = [float(values[0])]
    for v in values[1:]:
        out.append((float(v) * alpha) + (out[-1] * (1.0 - alpha)))
    return out


def rsi(values: List[float], period: int = 14) -> List[float]:
    if not values:
        return []
    if len(values) < period + 1:
        return [50.0 for _ in values]

    rsis = [50.0] * len(values)
    gains: List[float] = []
    losses: List[float] = []

    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))

    avg_gain = avg(gains[:period])
    avg_loss = avg(losses[:period])

    def calc_rsi(g: float, l: float) -> float:
        if l == 0 and g == 0:
            return 50.0
        if l == 0:
            return 100.0
        rs = g / l
        return 100.0 - (100.0 / (1.0 + rs))

    rsis[period] = calc_rsi(avg_gain, avg_loss)

    for i in range(period + 1, len(values)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        rsis[i] = calc_rsi(avg_gain, avg_loss)

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


def recent_red_count(klines: List[List[Any]], n: int = 5) -> int:
    if not klines:
        return 0
    part = klines[-n:]
    count = 0
    for k in part:
        if safe_float(k[4]) < safe_float(k[1]):
            count += 1
    return count


def consecutive_green_count(klines: List[List[Any]], n: int = 6) -> int:
    if not klines:
        return 0
    count = 0
    for k in reversed(klines[-n:]):
        if safe_float(k[4]) > safe_float(k[1]):
            count += 1
        else:
            break
    return count


def short_breakdown_confirmation(k1: List[List[Any]], k5: List[List[Any]]) -> Dict[str, Any]:
    if len(k1) < 30 or len(k5) < 30:
        return {"score": 0.0, "reason": "Kırılım verisi yetersiz"}

    c1 = closes(k1)
    h1 = highs(k1)
    l1 = lows(k1)
    c5 = closes(k5)
    v1 = volumes(k1)
    e9 = ema(c1, 9)
    e21 = ema(c1, 21)
    r1 = rsi(c1, 14)

    last_price = c1[-1]
    prev_k = k1[-2]
    last_k = k1[-1]
    recent_low_8 = min(l1[-9:-1])
    recent_high_12 = max(h1[-13:-1])
    prev_high_6 = max(h1[-8:-2])
    red_count = recent_red_count(k1, 5)

    score = 0.0
    reasons: List[str] = []

    if last_price < e9[-1]:
        score += 2.0
        reasons.append("EMA9 altı")
    if last_price < e21[-1]:
        score += 2.5
        reasons.append("EMA21 altı")
    if e9[-1] < e21[-1]:
        score += 2.0
        reasons.append("EMA9/21 aşağı")
    if last_price < recent_low_8:
        score += 3.0
        reasons.append("Son dip kırıldı")
    if lower_highs(h1, 3):
        score += 2.0
        reasons.append("Alçalan tepeler")
    if lower_lows(l1, 3):
        score += 2.0
        reasons.append("Alçalan dipler")
    if red_count >= MIN_RED_CANDLES_FOR_SHORT:
        score += 1.5
        reasons.append(f"Kırmızı mum {red_count}")
    if safe_float(last_k[4]) < safe_float(last_k[1]) and safe_float(prev_k[4]) < safe_float(prev_k[1]):
        score += 1.5
        reasons.append("Arka arkaya satış mumu")
    if r1[-1] < 50:
        score += 2.0
        reasons.append("RSI 50 altı")
    elif r1[-1] < r1[-2] and r1[-1] < 55:
        score += 1.0
        reasons.append("RSI düşüyor")
    if c5[-1] < c5[-2] and c5[-1] < c5[-3]:
        score += 2.0
        reasons.append("5dk kapanış zayıf")
    if safe_float(last_k[2]) >= recent_high_12 and last_price < prev_high_6:
        score += 2.5
        reasons.append("Tepe reddi")
    vol_ratio = safe_float(v1[-1]) / max(avg(v1[-20:-1]), 1e-9)
    if safe_float(last_k[4]) < safe_float(last_k[1]) and vol_ratio >= 1.25:
        score += 1.5
        reasons.append(f"Satış hacmi x{vol_ratio:.2f}")

    return {"score": round(score, 2), "reason": " | ".join(reasons[:8]) if reasons else "Net kırılım yok"}


def candle_wick_ratios(kline: List[Any]) -> Tuple[float, float, float, bool]:
    o = safe_float(kline[1])
    h = safe_float(kline[2])
    l = safe_float(kline[3])
    c = safe_float(kline[4])
    rng = max(h - l, 1e-9)
    upper = max(0.0, h - max(o, c)) / rng
    lower = max(0.0, min(o, c) - l) / rng
    body = abs(c - o) / rng
    red = c < o
    return upper, lower, body, red


def candle_position_in_range(kline: List[Any], price: float) -> float:
    """
    Mum içindeki fiyat konumu.
    0.00 = mumun dibi, 1.00 = mumun tepesi.
    """
    h = safe_float(kline[2])
    l = safe_float(kline[3])
    rng = max(h - l, 1e-12)
    return clamp((safe_float(price) - l) / rng, 0.0, 1.0)



def build_ma_cross_entry_guard(
    k1: List[List[Any]],
    k15: List[List[Any]],
    direction: str,
) -> Dict[str, Any]:
    """
    MA7/MA25 kesişim giriş kapısı.
    1m ana tetik, 15m sadece yön filtresi.
    """
    direction = (direction or "SHORT").upper()
    if not MA_CROSS_ENTRY_ENABLED:
        return {"enabled": False, "passed": True, "class": "KAPALI", "reason": "MA7/MA25 giriş motoru kapalı."}

    if len(k1) < max(MA_CROSS_SLOW_PERIOD + 3, 35) or len(k15) < max(MA_CROSS_SLOW_PERIOD + 3, 35):
        return {"enabled": True, "passed": False, "class": "VERI_YOK", "reason": "MA7/MA25 için veri yetersiz."}

    c1 = closes(k1)
    e_fast_1 = ema(c1, MA_CROSS_FAST_PERIOD)
    e_slow_1 = ema(c1, MA_CROSS_SLOW_PERIOD)
    if len(e_fast_1) < 2 or len(e_slow_1) < 2:
        return {"enabled": True, "passed": False, "class": "VERI_YOK", "reason": "1m MA hesaplanamadı."}

    fast_prev = safe_float(e_fast_1[-2])
    slow_prev = safe_float(e_slow_1[-2])
    fast_now = safe_float(e_fast_1[-1])
    slow_now = safe_float(e_slow_1[-1])
    last_price = safe_float(c1[-1])
    gap_pct = abs(pct_change(slow_now, fast_now)) if slow_now > 0 else 0.0

    cross_down = fast_prev >= slow_prev and fast_now < slow_now
    cross_up = fast_prev <= slow_prev and fast_now > slow_now
    near_cross = gap_pct <= MA_CROSS_MAX_GAP_PCT

    k15_src = closed_klines(k15, "15m") if MA_CROSS_USE_CLOSED_15M else k15
    if len(k15_src) < max(MA_CROSS_SLOW_PERIOD + 3, 35):
        k15_src = k15
    c15 = closes(k15_src)
    e_fast_15 = ema(c15, MA_CROSS_FAST_PERIOD)
    e_slow_15 = ema(c15, MA_CROSS_SLOW_PERIOD)
    fast15 = safe_float(e_fast_15[-1]) if e_fast_15 else 0.0
    slow15 = safe_float(e_slow_15[-1]) if e_slow_15 else 0.0
    fast15_prev = safe_float(e_fast_15[-2]) if len(e_fast_15) >= 2 else fast15

    if direction == "SHORT":
        cross_ok = cross_down and near_cross
        direction_ok = (fast15 < slow15) or (fast15 < fast15_prev and fast15 <= slow15 * 1.0015)
        klass = "MA7_MA25_SHORT_KESISIM" if cross_ok and direction_ok else "MA_SHORT_BEKLE"
        if not cross_ok:
            return {
                "enabled": True, "passed": False, "class": klass, "cross_ok": False, "direction_ok": direction_ok,
                "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
                "reason": f"1m SHORT için MA7 yukarıdan aşağı MA25 kesmedi. MA7={fmt_num(fast_now)} MA25={fmt_num(slow_now)} gap=%{gap_pct:.3f}."
            }
        if MA_CROSS_REQUIRE_15M_DIRECTION and not direction_ok:
            return {
                "enabled": True, "passed": False, "class": "MA_15M_YON_BLOK", "cross_ok": True, "direction_ok": False,
                "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
                "reason": f"1m SHORT kesişim var ama 15m yön doğru değil. 15m MA7={fmt_num(fast15)} MA25={fmt_num(slow15)}."
            }
        return {
            "enabled": True, "passed": True, "class": "MA7_MA25_SHORT_KESISIM", "cross_ok": True, "direction_ok": direction_ok,
            "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
            "reason": f"1m MA7/MA25 SHORT kesişimi: MA7 yukarıdan aşağı kesti. 15m yön SHORT uyumlu. MA7={fmt_num(fast_now)} MA25={fmt_num(slow_now)}."
        }

    cross_ok = cross_up and near_cross
    direction_ok = (fast15 > slow15) or (fast15 > fast15_prev and fast15 >= slow15 * 0.9985)
    klass = "MA7_MA25_LONG_KESISIM" if cross_ok and direction_ok else "MA_LONG_BEKLE"
    if not cross_ok:
        return {
            "enabled": True, "passed": False, "class": klass, "cross_ok": False, "direction_ok": direction_ok,
            "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
            "reason": f"1m LONG için MA7 aşağıdan yukarı MA25 kesmedi. MA7={fmt_num(fast_now)} MA25={fmt_num(slow_now)} gap=%{gap_pct:.3f}."
        }
    if MA_CROSS_REQUIRE_15M_DIRECTION and not direction_ok:
        return {
            "enabled": True, "passed": False, "class": "MA_15M_YON_BLOK", "cross_ok": True, "direction_ok": False,
            "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
            "reason": f"1m LONG kesişim var ama 15m yön doğru değil. 15m MA7={fmt_num(fast15)} MA25={fmt_num(slow15)}."
        }
    return {
        "enabled": True, "passed": True, "class": "MA7_MA25_LONG_KESISIM", "cross_ok": True, "direction_ok": direction_ok,
        "gap_pct": round(gap_pct, 4), "fast": fast_now, "slow": slow_now, "fast15": fast15, "slow15": slow15,
        "reason": f"1m MA7/MA25 LONG kesişimi: MA7 aşağıdan yukarı kesti. 15m yön LONG uyumlu. MA7={fmt_num(fast_now)} MA25={fmt_num(slow_now)}."
    }

def build_entry_location_guard(
    k1: List[List[Any]],
    k5: List[List[Any]],
    k15: List[List[Any]],
    direction: str,
    price: float,
) -> Dict[str, Any]:
    """
    ERKEN GİRİŞ BÖLGESİ MOTORU
    - SHORT: kırmızı/reddeden 15m mumun üst/başlangıç bölgesinde yakalar.
    - LONG: yeşil/dönen 15m mumun alt/başlangıç bölgesinde yakalar.
    - Amaç sinyal sayısını körlemesine kesmek değil; geç mum dibi/tepe kovalamayı engelleyip
      doğru bölgeye bonus vermektir.
    """
    direction = (direction or "SHORT").upper()
    if not ENTRY_LOCATION_GUARD_ENABLED:
        return {"enabled": False, "passed": True, "early": False, "late": False, "class": "KAPALI", "score": 0.0, "reason": "Giriş bölgesi motoru kapalı."}

    src = k15 if ENTRY_LOCATION_TF == "15m" else (k5 if ENTRY_LOCATION_TF == "5m" else k1)
    tf_label = ENTRY_LOCATION_TF
    if not src:
        return {"enabled": True, "passed": True, "early": False, "late": False, "class": "VERI_YOK", "score": 0.0, "reason": "Giriş bölgesi verisi yok."}

    k = src[-1]
    o = safe_float(k[1])
    h = safe_float(k[2])
    l = safe_float(k[3])
    c = safe_float(k[4])
    p = safe_float(price)
    rng = max(h - l, 1e-12)
    pos = candle_position_in_range(k, p)
    upper_wick, lower_wick, body_ratio, red = candle_wick_ratios(k)
    green = c > o

    # Mum zamanı debug için saklanır.
    start_ts = kline_start_ms(k) / 1000.0 if kline_start_ms(k) else 0.0
    start_txt = datetime.fromtimestamp(start_ts, TZ).strftime("%H.%M") if start_ts else "-"

    if direction == "SHORT":
        # Tepe/reddetme var mı? Sadece dipteki kırmızı kovalamayı istemiyoruz.
        rejection_context = red or upper_wick >= SHORT_ENTRY_MIN_REJECTION_WICK
        early = bool(rejection_context and pos >= SHORT_ENTRY_UPPER_START_MIN_POS)
        late = bool(rejection_context and pos <= SHORT_ENTRY_LATE_LOW_MAX_POS)
        if early:
            klass = "ERKEN_SHORT_BOLGESI"
            reason = (
                f"{tf_label} SHORT doğru giriş bölgesi: fiyat mumun üst/başlangıç tarafında "
                f"(konum %{pos*100:.0f}, üst fitil {upper_wick:.2f}, red={red}, mum={start_txt})."
            )
            return {"enabled": True, "passed": True, "early": True, "late": False, "class": klass, "score": 10.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}
        if late:
            klass = "GEC_SHORT_KOVALAMA"
            reason = (
                f"{tf_label} SHORT geç kaldı: fiyat kırmızı/reddeden mumun alt/dip tarafına inmiş "
                f"(konum %{pos*100:.0f}, üst fitil {upper_wick:.2f}, red={red}, mum={start_txt})."
            )
            return {"enabled": True, "passed": False, "early": False, "late": True, "class": klass, "score": -10.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}
        reason = (
            f"{tf_label} SHORT giriş bölgesi nötr: fiyat henüz net üst başlangıç bölgesinde değil "
            f"(konum %{pos*100:.0f}, üst fitil {upper_wick:.2f}, red={red}, mum={start_txt})."
        )
        return {"enabled": True, "passed": True, "early": False, "late": False, "class": "SHORT_NÖTR", "score": 0.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}

    # LONG
    reversal_context = green or lower_wick >= LONG_ENTRY_MIN_LOWER_WICK
    early = bool(reversal_context and pos <= LONG_ENTRY_LOWER_START_MAX_POS)
    late = bool(reversal_context and pos >= LONG_ENTRY_LATE_HIGH_MIN_POS)
    if early:
        klass = "ERKEN_LONG_BOLGESI"
        reason = (
            f"{tf_label} LONG doğru giriş bölgesi: fiyat yeşil/dönen mumun alt/başlangıç tarafında "
            f"(konum %{pos*100:.0f}, alt fitil {lower_wick:.2f}, green={green}, mum={start_txt})."
        )
        return {"enabled": True, "passed": True, "early": True, "late": False, "class": klass, "score": 10.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}
    if late:
        klass = "GEC_LONG_KOVALAMA"
        reason = (
            f"{tf_label} LONG geç kaldı: fiyat yeşil/dönen mumun üst/tepe tarafına çıkmış "
            f"(konum %{pos*100:.0f}, alt fitil {lower_wick:.2f}, green={green}, mum={start_txt})."
        )
        return {"enabled": True, "passed": False, "early": False, "late": True, "class": klass, "score": -10.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}

    reason = (
        f"{tf_label} LONG giriş bölgesi nötr: fiyat henüz net dip/başlangıç bölgesinde değil "
        f"(konum %{pos*100:.0f}, alt fitil {lower_wick:.2f}, green={green}, mum={start_txt})."
    )
    return {"enabled": True, "passed": True, "early": False, "late": False, "class": "LONG_NÖTR", "score": 0.0, "position": round(pos, 3), "position_pct": round(pos*100, 1), "reason": reason, "candle_time": start_txt}


def trend_continuation_guard(
    pump_10m: float,
    pump_20m: float,
    last_price: float,
    ema9: float,
    ema21: float,
    rsi1_val: float,
    rsi5_val: float,
    rej_score: float,
    weak_close: bool,
    structure_turn: bool,
    breakdown_score: float,
    red_count: int,
) -> Dict[str, Any]:
    if not TREND_GUARD_ENABLED:
        return {"blocked": False, "score": 0.0, "reason": "Trend koruması kapalı"}

    score = 0.0
    reasons: List[str] = []

    if pump_10m >= TREND_GUARD_MIN_PUMP_10M:
        score += 1.4
        reasons.append(f"10dk güçlü %{pump_10m:.2f}")
    if pump_20m >= TREND_GUARD_MIN_PUMP_20M:
        score += 1.8
        reasons.append(f"20dk güçlü %{pump_20m:.2f}")
    if last_price > ema9 > ema21:
        score += 2.0
        reasons.append("EMA9>EMA21 üstünde")
    elif last_price > ema9:
        score += 1.0
        reasons.append("EMA9 üstünde")
    if rsi1_val >= TREND_GUARD_MIN_RSI_1M:
        score += 1.0
        reasons.append(f"RSI1 güçlü {rsi1_val:.1f}")
    if rsi5_val >= TREND_GUARD_MIN_RSI_5M:
        score += 1.0
        reasons.append(f"RSI5 güçlü {rsi5_val:.1f}")
    if rej_score < 10:
        score += 0.7
        reasons.append("Tepe reddi zayıf")
    if not weak_close:
        score += 0.8
        reasons.append("Son mum zayıf kapanmadı")
    if not structure_turn:
        score += 0.8
        reasons.append("Yapı bozulmadı")
    if red_count < MIN_RED_CANDLES_FOR_SHORT:
        score += 0.7
        reasons.append("Satış mumu yetersiz")

    if breakdown_score >= TREND_BREAKDOWN_MIN_SCORE:
        score -= 3.5
        reasons.append(f"Kırılım var {breakdown_score:.1f}")

    blocked = score >= TREND_GUARD_SCORE_BLOCK and breakdown_score < TREND_BREAKDOWN_MIN_SCORE
    return {"blocked": blocked, "score": round(score, 2), "reason": " | ".join(reasons[:8])}


def calculate_short_levels(entry: float, h1: List[float], last_atr1: float, last_atr5: float) -> Tuple[float, float, float, float, float]:
    if entry <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    if FIXED_STOP_PCT_ENABLED:
        stop = entry * (1 + FIXED_STOP_PCT / 100.0)
        tp1 = entry * (1 - FIXED_TP1_PCT / 100.0)
        tp2 = entry * (1 - FIXED_TP2_PCT / 100.0)
        tp3 = entry * (1 - FIXED_TP3_PCT / 100.0)
        rr = (entry - tp1) / max(stop - entry, 1e-9)
        stats["fixed_stop_used"] = stats.get("fixed_stop_used", 0) + 1
        return stop, tp1, tp2, tp3, rr

    recent_swing_high = max(h1[-12:]) if len(h1) >= 12 else max(h1) if h1 else entry
    min_stop_dist = entry * (SHORT_MIN_STOP_PCT / 100.0)
    atr_stop_dist = max(last_atr1 * SHORT_STOP_ATR_MULT, min_stop_dist)
    structure_buffer = recent_swing_high * (SHORT_STRUCTURE_EXTRA_BUFFER_PCT / 100.0)
    wick_buffer = max(last_atr1 * SHORT_STOP_WICK_ATR_BUFFER, entry * 0.0012, structure_buffer)
    wick_stop = recent_swing_high + wick_buffer
    raw_stop = max(entry + atr_stop_dist, wick_stop)
    max_stop = entry * (1 + SHORT_MAX_STOP_PCT / 100.0)
    stop = min(raw_stop, max_stop)

    if stop <= entry + min_stop_dist:
        stop = entry + min_stop_dist

    tp1 = entry * (1 - FIXED_TP1_PCT / 100.0)
    tp2 = entry * (1 - FIXED_TP2_PCT / 100.0)
    tp3 = entry * (1 - FIXED_TP3_PCT / 100.0)
    rr = (entry - tp1) / max(stop - entry, 1e-9)
    return stop, tp1, tp2, tp3, rr


def calculate_long_levels(entry: float, l1: List[float], last_atr1: float, last_atr5: float) -> Tuple[float, float, float, float, float]:
    if entry <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    if FIXED_STOP_PCT_ENABLED:
        stop = entry * (1 - FIXED_STOP_PCT / 100.0)
        tp1 = entry * (1 + FIXED_TP1_PCT / 100.0)
        tp2 = entry * (1 + FIXED_TP2_PCT / 100.0)
        tp3 = entry * (1 + FIXED_TP3_PCT / 100.0)
        rr = (tp1 - entry) / max(entry - stop, 1e-9)
        stats["fixed_stop_used"] = stats.get("fixed_stop_used", 0) + 1
        return stop, tp1, tp2, tp3, rr

    recent_swing_low = min(l1[-12:]) if len(l1) >= 12 else min(l1) if l1 else entry
    min_stop_dist = entry * (LONG_MIN_STOP_PCT / 100.0)
    atr_stop_dist = max(last_atr1 * LONG_STOP_ATR_MULT, min_stop_dist)
    structure_buffer = recent_swing_low * (LONG_STRUCTURE_EXTRA_BUFFER_PCT / 100.0)
    wick_buffer = max(last_atr1 * LONG_STOP_WICK_ATR_BUFFER, entry * 0.0012, structure_buffer)
    wick_stop = recent_swing_low - wick_buffer
    raw_stop = min(entry - atr_stop_dist, wick_stop)
    max_stop = entry * (1 - LONG_MAX_STOP_PCT / 100.0)
    stop = max(raw_stop, max_stop)

    if stop >= entry - min_stop_dist:
        stop = entry - min_stop_dist

    tp1 = entry * (1 + FIXED_TP1_PCT / 100.0)
    tp2 = entry * (1 + FIXED_TP2_PCT / 100.0)
    tp3 = entry * (1 + FIXED_TP3_PCT / 100.0)
    rr = (tp1 - entry) / max(entry - stop, 1e-9)
    return stop, tp1, tp2, tp3, rr


# =========================================================
# ICT MOTORU
# =========================================================
def ict_find_pivots(hs: List[float], ls: List[float], left: int = 2, right: int = 2) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    piv_h: List[Tuple[int, float]] = []
    piv_l: List[Tuple[int, float]] = []
    n = len(hs)
    if n < left + right + 3:
        return piv_h, piv_l
    for i in range(left, n - right):
        hh = hs[i]
        ll = ls[i]
        if all(hh >= hs[j] for j in range(i - left, i + right + 1) if j != i):
            if hh > max(hs[i-left:i] + hs[i+1:i+right+1]):
                piv_h.append((i, hh))
        if all(ll <= ls[j] for j in range(i - left, i + right + 1) if j != i):
            if ll < min(ls[i-left:i] + ls[i+1:i+right+1]):
                piv_l.append((i, ll))
    return piv_h, piv_l


def ict_detect_market_structure(k5: List[List[Any]], price: float) -> Dict[str, Any]:
    h5 = highs(k5)
    l5 = lows(k5)
    c5 = closes(k5)
    ph, pl = ict_find_pivots(h5, l5, max(1, ICT_PIVOT_LEFT), max(1, ICT_PIVOT_RIGHT))
    recent_ph = ph[-5:]
    recent_pl = pl[-5:]
    last_high = recent_ph[-1][1] if recent_ph else (max(h5[-20:-1]) if len(h5) > 20 else max(h5))
    prev_high = recent_ph[-2][1] if len(recent_ph) >= 2 else last_high
    last_low = recent_pl[-1][1] if recent_pl else (min(l5[-20:-1]) if len(l5) > 20 else min(l5))
    prev_low = recent_pl[-2][1] if len(recent_pl) >= 2 else last_low
    close_now = c5[-1]
    close_prev = c5[-2] if len(c5) >= 2 else close_now

    hh = last_high > prev_high
    lh = last_high < prev_high
    hl = last_low > prev_low
    ll = last_low < prev_low
    bias = "RANGE"
    if hh and hl:
        bias = "BULLISH"
    elif lh and ll:
        bias = "BEARISH"

    bos_up = close_now > last_high and close_prev <= last_high
    bos_down = close_now < last_low and close_prev >= last_low
    choch_up = bos_up and bias == "BEARISH"
    choch_down = bos_down and bias == "BULLISH"
    mss_up = close_now > max(h5[-8:-1]) if len(h5) >= 9 else False
    mss_down = close_now < min(l5[-8:-1]) if len(l5) >= 9 else False
    return {
        "structure_bias": bias,
        "hh": hh, "hl": hl, "lh": lh, "ll": ll,
        "last_structure_high": last_high,
        "prev_structure_high": prev_high,
        "last_structure_low": last_low,
        "prev_structure_low": prev_low,
        "bos_up": bos_up, "bos_down": bos_down,
        "choch_up": choch_up, "choch_down": choch_down,
        "mss_up": mss_up, "mss_down": mss_down,
        "pivot_high_count": len(ph),
        "pivot_low_count": len(pl),
    }


def ict_detect_equal_liquidity(k1: List[List[Any]], price: float) -> Dict[str, Any]:
    h1 = highs(k1)
    l1 = lows(k1)
    look = min(max(12, ICT_LIQUIDITY_LOOKBACK_1M), len(k1) - 2)
    hs = h1[-look-1:-1]
    ls = l1[-look-1:-1]
    tol = price * (ICT_EQUAL_LEVEL_TOLERANCE_PCT / 100.0)
    eq_high = False
    eq_low = False
    high_level = max(hs) if hs else price
    low_level = min(ls) if ls else price
    if hs:
        near_highs = [x for x in hs if abs(x - high_level) <= tol]
        eq_high = len(near_highs) >= 2
    if ls:
        near_lows = [x for x in ls if abs(x - low_level) <= tol]
        eq_low = len(near_lows) >= 2
    buyside_distance = pct_change(price, high_level) if price > 0 else 0.0
    sellside_distance = pct_change(price, low_level) if price > 0 else 0.0
    return {
        "equal_high": eq_high,
        "equal_low": eq_low,
        "buy_side_liquidity": high_level,
        "sell_side_liquidity": low_level,
        "buyside_distance_pct": round(buyside_distance, 2),
        "sellside_distance_pct": round(sellside_distance, 2),
    }


def ict_detect_fvg_zones(k1: List[List[Any]], price: float) -> Dict[str, Any]:
    if len(k1) < 5:
        return {"bullish_fvgs": [], "bearish_fvgs": [], "bullish_fvg_active": False, "bearish_fvg_active": False}
    look_start = max(2, len(k1) - max(8, ICT_FVG_LOOKBACK))
    bullish: List[Dict[str, Any]] = []
    bearish: List[Dict[str, Any]] = []
    for i in range(look_start, len(k1)):
        h2 = safe_float(k1[i-2][2]); l2 = safe_float(k1[i-2][3])
        hi = safe_float(k1[i][2]); li = safe_float(k1[i][3])
        if li > h2:
            low = h2; high = li
            mid = (low + high) / 2.0
            active = price >= low and price <= high * (1 + ICT_ZONE_TOLERANCE_PCT / 100.0)
            bullish.append({"low": low, "high": high, "mid": mid, "age": len(k1)-1-i, "active": active, "filled_pct": round(clamp((high - max(price, low)) / max(high - low, 1e-9) * 100, 0, 100), 1)})
        if hi < l2:
            low = hi; high = l2
            mid = (low + high) / 2.0
            active = price <= high and price >= low * (1 - ICT_ZONE_TOLERANCE_PCT / 100.0)
            bearish.append({"low": low, "high": high, "mid": mid, "age": len(k1)-1-i, "active": active, "filled_pct": round(clamp((min(price, high) - low) / max(high - low, 1e-9) * 100, 0, 100), 1)})
    bullish = sorted(bullish, key=lambda z: z["age"])[:4]
    bearish = sorted(bearish, key=lambda z: z["age"])[:4]
    return {
        "bullish_fvgs": bullish,
        "bearish_fvgs": bearish,
        "bullish_fvg_active": any(z.get("active") for z in bullish),
        "bearish_fvg_active": any(z.get("active") for z in bearish),
        "nearest_bullish_fvg": bullish[0] if bullish else {},
        "nearest_bearish_fvg": bearish[0] if bearish else {},
    }


def ict_detect_order_blocks(k1: List[List[Any]], price: float) -> Dict[str, Any]:
    if len(k1) < 20:
        return {"bullish_ob": {}, "bearish_ob": {}, "bullish_ob_near": False, "bearish_ob_near": False}
    atr1_vals = atr(k1, 14)
    last_atr = max(atr1_vals[-1], price * 0.0015)
    start = max(3, len(k1) - max(12, ICT_ORDER_BLOCK_LOOKBACK))
    bullish_ob: Dict[str, Any] = {}
    bearish_ob: Dict[str, Any] = {}
    for i in range(start, len(k1)):
        o = safe_float(k1[i][1]); h = safe_float(k1[i][2]); l = safe_float(k1[i][3]); c = safe_float(k1[i][4])
        body = abs(c - o)
        displacement = body >= last_atr * ICT_MIN_DISPLACEMENT_ATR
        if not displacement:
            continue
        if c > o:
            for j in range(i-1, max(start-1, i-8), -1):
                oj = safe_float(k1[j][1]); hj = safe_float(k1[j][2]); lj = safe_float(k1[j][3]); cj = safe_float(k1[j][4])
                if cj < oj:
                    bullish_ob = {"low": lj, "high": max(oj, cj), "full_high": hj, "index": j, "age": len(k1)-1-j}
                    break
        if c < o:
            for j in range(i-1, max(start-1, i-8), -1):
                oj = safe_float(k1[j][1]); hj = safe_float(k1[j][2]); lj = safe_float(k1[j][3]); cj = safe_float(k1[j][4])
                if cj > oj:
                    bearish_ob = {"low": min(oj, cj), "high": hj, "full_low": lj, "index": j, "age": len(k1)-1-j}
                    break
    bull_near = False
    bear_near = False
    if bullish_ob:
        bull_mid = (safe_float(bullish_ob.get("low")) + safe_float(bullish_ob.get("high"))) / 2
        bull_near = abs(pct_change(price, bull_mid)) <= ICT_MAX_OB_DISTANCE_PCT or (safe_float(bullish_ob.get("low")) <= price <= safe_float(bullish_ob.get("high")))
    if bearish_ob:
        bear_mid = (safe_float(bearish_ob.get("low")) + safe_float(bearish_ob.get("high"))) / 2
        bear_near = abs(pct_change(price, bear_mid)) <= ICT_MAX_OB_DISTANCE_PCT or (safe_float(bearish_ob.get("low")) <= price <= safe_float(bearish_ob.get("high")))
    return {"bullish_ob": bullish_ob, "bearish_ob": bearish_ob, "bullish_ob_near": bull_near, "bearish_ob_near": bear_near}


def ict_killzone_context() -> Dict[str, Any]:
    if not ICT_KILLZONE_ENABLED:
        return {"active": False, "name": "Kapalı", "score": 0.0}
    h = tr_now().hour
    london = ICT_LONDON_KILLZONE_START <= h < ICT_LONDON_KILLZONE_END
    ny = ICT_NY_KILLZONE_START <= h < ICT_NY_KILLZONE_END
    if london and ny:
        return {"active": True, "name": "Londra+NY overlap", "score": 1.5}
    if london:
        return {"active": True, "name": "Londra kill zone", "score": 1.0}
    if ny:
        return {"active": True, "name": "NY kill zone", "score": 1.2}
    return {"active": False, "name": "Kill zone dışı", "score": 0.0}


def build_ict_zone_context(k1: List[List[Any]], k5: List[List[Any]], k15: List[List[Any]], price: float) -> Dict[str, Any]:
    if not ICT_ENGINE_ENABLED or len(k1) < 50 or len(k5) < 50:
        return {"enabled": False, "reason": "ICT kapalı veya veri yetersiz."}

    c1 = closes(k1); h1 = highs(k1); l1 = lows(k1)
    c5 = closes(k5); h5 = highs(k5); l5 = lows(k5)
    look = min(max(20, ICT_SWING_LOOKBACK_5M), len(k5) - 2)
    seg_h = h5[-look:-1]
    seg_l = l5[-look:-1]
    if not seg_h or not seg_l:
        return {"enabled": False, "reason": "ICT swing verisi yok."}

    swing_high = max(seg_h)
    swing_low = min(seg_l)
    swing_range = max(swing_high - swing_low, 1e-9)
    range_pct = abs(pct_change(swing_low, swing_high)) if swing_low > 0 else 0.0
    equilibrium = swing_low + swing_range * 0.5
    discount_high = swing_high - swing_range * ICT_DISCOUNT_FIB_LOW
    discount_low = swing_high - swing_range * ICT_DISCOUNT_FIB_HIGH
    premium_low = swing_low + swing_range * (1.0 - ICT_PREMIUM_FIB_HIGH)
    premium_high = swing_low + swing_range * (1.0 - ICT_PREMIUM_FIB_LOW)
    tol = price * (ICT_ZONE_TOLERANCE_PCT / 100.0)

    in_discount_zone = discount_low - tol <= price <= discount_high + tol
    in_premium_zone = premium_low - tol <= price <= premium_high + tol or price >= equilibrium
    below_equilibrium = price < equilibrium
    above_equilibrium = price > equilibrium

    liq_look = min(max(8, ICT_LIQUIDITY_LOOKBACK_1M), len(k1) - 2)
    prev_low = min(l1[-liq_look-1:-1])
    prev_high = max(h1[-liq_look-1:-1])
    last_k = k1[-1]
    last_high = safe_float(last_k[2]); last_low = safe_float(last_k[3]); last_close = safe_float(last_k[4])
    upper_wick, lower_wick, body_ratio, red = candle_wick_ratios(last_k)
    sweep_low = last_low < prev_low * (1 - ICT_MIN_SWEEP_PCT / 100.0) and last_close > prev_low
    sweep_high = last_high > prev_high * (1 + ICT_MIN_SWEEP_PCT / 100.0) and last_close < prev_high

    structure = ict_detect_market_structure(k5, price)
    liquidity = ict_detect_equal_liquidity(k1, price)
    fvg = ict_detect_fvg_zones(k1, price)
    ob = ict_detect_order_blocks(k1, price)
    kill = ict_killzone_context()

    atr5_vals = atr(k5, 14)
    last_atr5 = max(atr5_vals[-1], price * 0.0015)
    bullish_displacement = False
    bearish_displacement = False
    for i in range(max(2, len(k1) - 8), len(k1)):
        ko = safe_float(k1[i][1]); kc = safe_float(k1[i][4])
        body = abs(kc - ko)
        if kc > ko and body >= max(last_atr5 * ICT_MIN_FVG_BODY_ATR, price * 0.0015):
            bullish_displacement = True
        if kc < ko and body >= max(last_atr5 * ICT_MIN_FVG_BODY_ATR, price * 0.0015):
            bearish_displacement = True

    recent_high_8 = max(h1[-9:-1])
    recent_low_8 = min(l1[-9:-1])
    e9_1 = ema(c1, 9)
    e21_1 = ema(c1, 21)
    choch_up_score = 0.0
    choch_down_score = 0.0
    choch_up_reasons: List[str] = []
    choch_down_reasons: List[str] = []

    if last_close > recent_high_8:
        choch_up_score += 2.0; choch_up_reasons.append("son mikro tepe üstü")
    if structure.get("choch_up") or structure.get("bos_up"):
        choch_up_score += 2.4; choch_up_reasons.append("BOS/CHOCH yukarı")
    if last_close > e9_1[-1]:
        choch_up_score += 1.3; choch_up_reasons.append("EMA9 üstü")
    if e9_1[-1] > e21_1[-1]:
        choch_up_score += 1.5; choch_up_reasons.append("EMA9/21 yukarı")
    if not red and lower_wick >= 0.22:
        choch_up_score += 1.0; choch_up_reasons.append("alt fitil alıcı savunması")
    if bullish_displacement:
        choch_up_score += 1.4; choch_up_reasons.append("bullish displacement")
    if fvg.get("bullish_fvg_active"):
        choch_up_score += 1.0; choch_up_reasons.append("bullish FVG aktif")
    if ob.get("bullish_ob_near"):
        choch_up_score += 1.0; choch_up_reasons.append("bullish OB yakın")

    if last_close < recent_low_8:
        choch_down_score += 2.0; choch_down_reasons.append("son mikro dip altı")
    if structure.get("choch_down") or structure.get("bos_down"):
        choch_down_score += 2.4; choch_down_reasons.append("BOS/CHOCH aşağı")
    if last_close < e9_1[-1]:
        choch_down_score += 1.3; choch_down_reasons.append("EMA9 altı")
    if e9_1[-1] < e21_1[-1]:
        choch_down_score += 1.5; choch_down_reasons.append("EMA9/21 aşağı")
    if red and upper_wick >= 0.18:
        choch_down_score += 1.0; choch_down_reasons.append("üst fitil satıcı reddi")
    if bearish_displacement:
        choch_down_score += 1.4; choch_down_reasons.append("bearish displacement")
    if fvg.get("bearish_fvg_active"):
        choch_down_score += 1.0; choch_down_reasons.append("bearish FVG aktif")
    if ob.get("bearish_ob_near"):
        choch_down_score += 1.0; choch_down_reasons.append("bearish OB yakın")

    short_pro_score = 0.0
    short_notes: List[str] = []
    if in_premium_zone or above_equilibrium:
        short_pro_score += 2.0; short_notes.append("premium/EQ üstü")
    if sweep_high:
        short_pro_score += 2.4; short_notes.append("üst likidite sweep")
    if liquidity.get("equal_high"):
        short_pro_score += 0.9; short_notes.append("equal high likiditesi")
    if choch_down_score >= ICT_MIN_CHOCH_SCORE:
        short_pro_score += 2.2; short_notes.append("CHOCH/BOS aşağı")
    if fvg.get("bearish_fvg_active") or bearish_displacement:
        short_pro_score += 1.5; short_notes.append("bearish FVG/displacement")
    if ob.get("bearish_ob_near"):
        short_pro_score += 1.2; short_notes.append("bearish OB/supply")
    if structure.get("structure_bias") == "BEARISH" or structure.get("mss_down"):
        short_pro_score += 1.0; short_notes.append("bearish yapı")
    if kill.get("active"):
        short_pro_score += safe_float(kill.get("score", 0)); short_notes.append(str(kill.get("name")))
    if in_discount_zone and sweep_low and choch_up_score >= choch_down_score:
        short_pro_score -= 2.5; short_notes.append("discount + alt sweep, short tehlikeli")

    long_pro_score = 0.0
    long_notes: List[str] = []
    if in_discount_zone or below_equilibrium:
        long_pro_score += 2.0; long_notes.append("discount/EQ altı")
    if sweep_low:
        long_pro_score += 2.4; long_notes.append("alt likidite sweep")
    if liquidity.get("equal_low"):
        long_pro_score += 0.9; long_notes.append("equal low likiditesi")
    if choch_up_score >= ICT_MIN_CHOCH_SCORE:
        long_pro_score += 2.2; long_notes.append("CHOCH/BOS yukarı")
    if fvg.get("bullish_fvg_active") or bullish_displacement:
        long_pro_score += 1.5; long_notes.append("bullish FVG/displacement")
    if ob.get("bullish_ob_near"):
        long_pro_score += 1.2; long_notes.append("bullish OB/demand")
    if structure.get("structure_bias") == "BULLISH" or structure.get("mss_up"):
        long_pro_score += 1.0; long_notes.append("bullish yapı")
    if kill.get("active"):
        long_pro_score += safe_float(kill.get("score", 0)); long_notes.append(str(kill.get("name")))
    if in_premium_zone and sweep_high and choch_down_score >= choch_up_score:
        long_pro_score -= 2.5; long_notes.append("premium + üst sweep, long tehlikeli")

    return {
        "enabled": True,
        "pro_enabled": bool(ICT_PRO_MODE_ENABLED),
        "swing_high": swing_high,
        "swing_low": swing_low,
        "range_pct": round(range_pct, 2),
        "equilibrium": equilibrium,
        "discount_low": discount_low,
        "discount_high": discount_high,
        "premium_low": premium_low,
        "premium_high": premium_high,
        "in_discount_zone": in_discount_zone,
        "in_premium_zone": in_premium_zone,
        "below_equilibrium": below_equilibrium,
        "above_equilibrium": above_equilibrium,
        "sweep_low": sweep_low,
        "sweep_high": sweep_high,
        "prev_low": prev_low,
        "prev_high": prev_high,
        "sell_side_liquidity_swept": sweep_low,
        "buy_side_liquidity_swept": sweep_high,
        "equal_high": liquidity.get("equal_high"),
        "equal_low": liquidity.get("equal_low"),
        "buy_side_liquidity": liquidity.get("buy_side_liquidity"),
        "sell_side_liquidity": liquidity.get("sell_side_liquidity"),
        "bullish_fvg": bool(fvg.get("bullish_fvg_active")),
        "bearish_fvg": bool(fvg.get("bearish_fvg_active")),
        "bullish_fvg_active": bool(fvg.get("bullish_fvg_active")),
        "bearish_fvg_active": bool(fvg.get("bearish_fvg_active")),
        "nearest_bullish_fvg": fvg.get("nearest_bullish_fvg", {}),
        "nearest_bearish_fvg": fvg.get("nearest_bearish_fvg", {}),
        "bullish_displacement": bullish_displacement,
        "bearish_displacement": bearish_displacement,
        "bullish_ob": ob.get("bullish_ob", {}),
        "bearish_ob": ob.get("bearish_ob", {}),
        "bullish_ob_near": ob.get("bullish_ob_near", False),
        "bearish_ob_near": ob.get("bearish_ob_near", False),
        "structure_bias": structure.get("structure_bias", "RANGE"),
        "bos_up": structure.get("bos_up", False),
        "bos_down": structure.get("bos_down", False),
        "choch_up": structure.get("choch_up", False),
        "choch_down": structure.get("choch_down", False),
        "mss_up": structure.get("mss_up", False),
        "mss_down": structure.get("mss_down", False),
        "last_structure_high": structure.get("last_structure_high", 0),
        "last_structure_low": structure.get("last_structure_low", 0),
        "choch_up_score": round(choch_up_score, 2),
        "choch_down_score": round(choch_down_score, 2),
        "choch_up_reason": " | ".join(choch_up_reasons[:8]) if choch_up_reasons else "CHOCH yukarı yok",
        "choch_down_reason": " | ".join(choch_down_reasons[:8]) if choch_down_reasons else "CHOCH aşağı yok",
        "last_upper_wick": round(upper_wick, 3),
        "last_lower_wick": round(lower_wick, 3),
        "last_red": red,
        "killzone_active": kill.get("active", False),
        "killzone_name": kill.get("name", "-"),
        "short_pro_score": round(short_pro_score, 2),
        "long_pro_score": round(long_pro_score, 2),
        "short_pro_reason": " | ".join(short_notes[:8]) if short_notes else "SHORT ICT bağlamı zayıf",
        "long_pro_reason": " | ".join(long_notes[:8]) if long_notes else "LONG ICT bağlamı zayıf",
        "reason": (
            f"ICT PRO Swing {fmt_num(swing_low)}→{fmt_num(swing_high)} | EQ {fmt_num(equilibrium)} | "
            f"Discount {fmt_num(discount_low)}-{fmt_num(discount_high)} | "
            f"Premium {fmt_num(premium_low)}-{fmt_num(premium_high)} | "
            f"Yapı {structure.get('structure_bias')} | SHORT ICT {short_pro_score:.1f} | LONG ICT {long_pro_score:.1f}"
        )
    }

def long_structure_confirmation(k1: List[List[Any]], k5: List[List[Any]], ict: Dict[str, Any]) -> Dict[str, Any]:
    if len(k1) < 30 or len(k5) < 30:
        return {"score": 0.0, "reason": "Long yapı verisi yetersiz"}
    c1 = closes(k1); h1 = highs(k1); l1 = lows(k1); c5 = closes(k5); v1 = volumes(k1)
    e9 = ema(c1, 9); e21 = ema(c1, 21); r1 = rsi(c1, 14)
    last_price = c1[-1]
    last_k = k1[-1]
    prev_k = k1[-2]
    recent_high_8 = max(h1[-9:-1])
    recent_low_8 = min(l1[-9:-1])
    score = 0.0
    reasons: List[str] = []
    upper, lower, body, red = candle_wick_ratios(last_k)

    if bool(ict.get("sweep_low")):
        score += 2.4; reasons.append("alt likidite süpürüldü")
    if bool(ict.get("in_discount_zone")):
        score += 2.0; reasons.append("0.5-0.618 discount/talep bölgesi")
    if lower >= 0.28 and not red:
        score += 1.8; reasons.append("alt fitil alıcı savunması")
    elif lower >= 0.38:
        score += 1.0; reasons.append("alt fitil savunma")
    if last_price > e9[-1]:
        score += 1.5; reasons.append("EMA9 üstü")
    if last_price > e21[-1]:
        score += 1.2; reasons.append("EMA21 üstü")
    if e9[-1] > e21[-1]:
        score += 1.4; reasons.append("EMA9/21 yukarı")
    if last_price > recent_high_8:
        score += 2.2; reasons.append("mikro tepe kırıldı")
    if safe_float(last_k[4]) > safe_float(last_k[1]) and safe_float(prev_k[4]) > safe_float(prev_k[1]):
        score += 1.2; reasons.append("arka arkaya alıcı mumu")
    if r1[-1] > r1[-2] and r1[-1] >= 45:
        score += 1.1; reasons.append("RSI toparlanıyor")
    if c5[-1] > c5[-2]:
        score += 1.2; reasons.append("5dk kapanış yukarı")
    vol_ratio = safe_float(v1[-1]) / max(avg(v1[-20:-1]), 1e-9)
    if safe_float(last_k[4]) > safe_float(last_k[1]) and vol_ratio >= 1.10:
        score += 1.2; reasons.append(f"alım hacmi x{vol_ratio:.2f}")
    if last_price < recent_low_8 and not ict.get("sweep_low"):
        score -= 2.0; reasons.append("dip kırılıyor, sweep teyidi yok")

    return {"score": round(score, 2), "reason": " | ".join(reasons[:8]) if reasons else "Net long dönüş yok"}


def long_close_confirmation_gate(k5: List[List[Any]], k15: List[List[Any]]) -> Dict[str, Any]:
    k5c = closed_klines(k5, "5m")
    k15c = closed_klines(k15, "15m")
    if len(k5c) < 30 or len(k15c) < 30:
        return {"passed": False, "class": "WAIT", "reason": "5m/15m kapanış verisi yetersiz."}
    c5v = closes(k5c); c15v = closes(k15c)
    e9_5 = ema(c5v, 9); e21_5 = ema(c5v, 21); e9_15 = ema(c15v, 9)
    k5_last = k5c[-1]; k15_last = k15c[-1]
    o5, cl5 = safe_float(k5_last[1]), safe_float(k5_last[4])
    o15, cl15 = safe_float(k15_last[1]), safe_float(k15_last[4])
    upper5, lower5, body5, red5 = candle_wick_ratios(k5_last)
    upper15, lower15, body15, red15 = candle_wick_ratios(k15_last)
    score5 = 0.0; reasons5: List[str] = []
    score15 = 0.0; reasons15: List[str] = []
    if cl5 > o5:
        score5 += 1.7; reasons5.append("5m yeşil kapandı")
    if cl5 > c5v[-2]:
        score5 += 1.2; reasons5.append("5m önceki kapanış üstü")
    if cl5 > e9_5[-1]:
        score5 += 1.3; reasons5.append("5m EMA9 üstü")
    if cl5 > e21_5[-1]:
        score5 += 1.1; reasons5.append("5m EMA21 üstü")
    if lower5 >= 0.25 and cl5 >= o5:
        score5 += 1.2; reasons5.append("5m alt fitil talep")
    if c5v[-1] > c5v[-2] > c5v[-3]:
        score5 += 0.9; reasons5.append("5m iki kapanış güçlü")
    if upper5 >= 0.45 and cl5 <= o5:
        score5 -= 1.5; reasons5.append("5m üst fitil satıcı")
    if cl5 < e9_5[-1] and red5:
        score5 -= 1.2; reasons5.append("5m hâlâ zayıf")
    if cl15 > o15:
        score15 += 1.2; reasons15.append("15m yeşil kapandı")
    if cl15 > c15v[-2]:
        score15 += 0.9; reasons15.append("15m önceki kapanış üstü")
    if cl15 > e9_15[-1]:
        score15 += 1.0; reasons15.append("15m EMA9 üstü")
    if lower15 >= 0.22 and cl15 >= o15:
        score15 += 0.8; reasons15.append("15m alt fitil talep")
    if upper15 >= 0.45 and red15:
        score15 -= 1.2; reasons15.append("15m üst fitil satıcı")
    pass5 = (not LONG_REQUIRE_5M_CONFIRM) or score5 >= LONG_MIN_5M_CONFIRM_SCORE
    pass15 = (not LONG_REQUIRE_15M_CONFIRM) or score15 >= LONG_MIN_15M_CONFIRM_SCORE
    passed = pass5 and pass15
    klass = "CLEAN" if score5 >= LONG_MIN_5M_CONFIRM_SCORE + 2 and score15 >= LONG_MIN_15M_CONFIRM_SCORE + 1 else "RISKY"
    if not passed:
        klass = "WAIT"
    return {
        "passed": passed, "class": klass,
        "score5": round(score5, 2), "score15": round(score15, 2),
        "reason": f"5m long skoru {score5:.1f}/{LONG_MIN_5M_CONFIRM_SCORE:.1f}: {'; '.join(reasons5[:4]) if reasons5 else 'net alıcı yok'} | 15m long skoru {score15:.1f}/{LONG_MIN_15M_CONFIRM_SCORE:.1f}: {'; '.join(reasons15[:4]) if reasons15 else 'ana onay yok'}"
    }


def interval_to_milliseconds(interval: str) -> int:
    mp = {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1H": 3_600_000, "1h": 3_600_000, "4H": 14_400_000, "4h": 14_400_000}
    return mp.get(interval, 60_000)


def kline_start_ms(kline: List[Any]) -> int:
    ts = safe_float(kline[0], 0)
    if ts <= 0:
        return 0
    return int(ts if ts > 10_000_000_000 else ts * 1000)


def is_kline_closed(kline: List[Any], interval: str, now_ms: Optional[int] = None) -> bool:
    start_ms = kline_start_ms(kline)
    if start_ms <= 0:
        return True
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    return now_ms >= start_ms + interval_to_milliseconds(interval)


def closed_klines(klines: List[List[Any]], interval: str) -> List[List[Any]]:
    if not klines:
        return []
    now_ms = int(time.time() * 1000)
    if is_kline_closed(klines[-1], interval, now_ms):
        return klines
    return klines[:-1]


def short_close_confirmation_gate(k5: List[List[Any]], k15: List[List[Any]], res: Dict[str, Any]) -> Dict[str, Any]:
    if not CLOSE_CONFIRM_GATE_ENABLED:
        return {"passed": True, "class": "CLEAN", "reason": "Kapanış kapısı kapalı."}

    k5c = closed_klines(k5, "5m")
    k15c = closed_klines(k15, "15m")
    if len(k5c) < 30 or len(k15c) < 30:
        return {"passed": False, "class": "WAIT", "reason": "5m/15m kapanış verisi yetersiz; 1m radar takipte."}

    c5v = closes(k5c)
    c15v = closes(k15c)
    e9_5 = ema(c5v, 9)
    e21_5 = ema(c5v, 21)
    e9_15 = ema(c15v, 9)
    r5 = rsi(c5v, 14)
    r15 = rsi(c15v, 14)

    k5_last = k5c[-1]
    k15_last = k15c[-1]
    o5, h5, l5, cl5 = safe_float(k5_last[1]), safe_float(k5_last[2]), safe_float(k5_last[3]), safe_float(k5_last[4])
    o15, h15, l15, cl15 = safe_float(k15_last[1]), safe_float(k15_last[2]), safe_float(k15_last[3]), safe_float(k15_last[4])
    upper5, lower5, body5, red5 = candle_wick_ratios(k5_last)
    upper15, lower15, body15, red15 = candle_wick_ratios(k15_last)

    score5 = 0.0; reasons5: List[str] = []
    if red5:
        score5 += 1.8; reasons5.append("5m kırmızı kapandı")
    if cl5 < c5v[-2]:
        score5 += 1.1; reasons5.append("5m önceki kapanış altı")
    if cl5 < e9_5[-1]:
        score5 += 1.4; reasons5.append("5m EMA9 altı")
    if cl5 < e21_5[-1]:
        score5 += 1.3; reasons5.append("5m EMA21 altı")
    if upper5 >= 0.22 and cl5 <= o5:
        score5 += 1.0; reasons5.append("5m üst fitil/red")
    if c5v[-1] < c5v[-2] < c5v[-3]:
        score5 += 1.0; reasons5.append("5m iki kapanış zayıf")
    if lower5 >= 0.45 and cl5 >= o5:
        score5 -= 1.4; reasons5.append("5m alt fitil alıcı savunması")
    if cl5 > e9_5[-1] and not red5:
        score5 -= 1.2; reasons5.append("5m kapanış hâlâ diri")

    score15 = 0.0; reasons15: List[str] = []
    if red15:
        score15 += 1.4; reasons15.append("15m kırmızı kapandı")
    if cl15 < c15v[-2]:
        score15 += 1.0; reasons15.append("15m önceki kapanış altı")
    if cl15 < e9_15[-1]:
        score15 += 1.4; reasons15.append("15m EMA9 altı")
    if upper15 >= 0.20 and cl15 <= o15:
        score15 += 0.9; reasons15.append("15m üst fitil/red")
    if r15[-1] >= 62:
        score15 += 0.8; reasons15.append(f"15m şişkin RSI {r15[-1]:.1f}")
    if lower15 >= 0.45 and cl15 >= o15:
        score15 -= 1.2; reasons15.append("15m alt fitil alıcı savunması")
    if cl15 > e9_15[-1] and cl15 > c15v[-2] and not red15:
        score15 -= 1.6; reasons15.append("15m kapanış hâlâ yukarı")

    pass5 = (not CLOSE_CONFIRM_REQUIRE_5M) or score5 >= CLOSE_CONFIRM_MIN_5M_SCORE
    pass15 = (not CLOSE_CONFIRM_REQUIRE_15M) or score15 >= CLOSE_CONFIRM_MIN_15M_SCORE
    passed = pass5 and pass15
    clean = score5 >= CLOSE_CONFIRM_CLEAN_5M_SCORE and score15 >= CLOSE_CONFIRM_CLEAN_15M_SCORE
    decision_class = "CLEAN" if clean else "RISKY"
    if not passed:
        decision_class = "WAIT"
    reason = (
        f"5m kapanış skoru {score5:.1f}/{CLOSE_CONFIRM_MIN_5M_SCORE:.1f}: "
        f"{'; '.join(reasons5[:4]) if reasons5 else 'net zayıflama yok'} | "
        f"15m kapanış skoru {score15:.1f}/{CLOSE_CONFIRM_MIN_15M_SCORE:.1f}: "
        f"{'; '.join(reasons15[:4]) if reasons15 else 'net onay yok'}"
    )
    return {"passed": passed, "class": decision_class, "score5": round(score5, 2), "score15": round(score15, 2), "reason": reason}


def final_quality_gate(res: Dict[str, Any]) -> Tuple[bool, str, float]:
    score = 0.0
    hard_blocks: List[str] = []
    soft_notes: List[str] = []

    inv = res.get("invisible_face") if isinstance(res.get("invisible_face"), dict) else {}
    breakdown = safe_float(res.get("breakdown_score", 0))
    trend_guard_score = safe_float(res.get("trend_guard_score", 0))
    rr = safe_float(res.get("rr", 0))
    is_risky_scalp = str(res.get("signal_label", "")) == "RİSKLİ TP1 SCALP"
    is_tepe_early = bool(res.get("top_early_short")) or bool(inv.get("top_early_short")) or str(res.get("signal_label", "")) == "TEPE ERKEN SHORT"
    min_rr_required = RISKY_SCALP_MIN_RR_TP1 if is_risky_scalp or is_tepe_early else MIN_RR_TP1
    verify = safe_float(res.get("verify_score", 0))
    red_count = int(safe_float(res.get("red_count_5", 0)))
    green_streak = int(safe_float(res.get("green_streak", 0)))
    rsi1_val = safe_float(res.get("rsi1", 50))
    rsi5_val = safe_float(res.get("rsi5", 50))
    pump20 = safe_float(res.get("pump_20m", 0))
    drop_from_peak = safe_float(inv.get("drop_from_peak_pct", 0))
    bounce_from_low = safe_float(inv.get("bounce_from_low_pct", 0))
    top_exit_score = safe_float(inv.get("top_exit_score", 0))

    # V6: Whale Eye skorunu kalite kapısına ekle
    whale_eye = res.get("whale_eye", {})
    whale_score = safe_float(whale_eye.get("total_score", 0))
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))

    if drop_from_peak >= TEPE_ERKEN_TOO_LATE_DROP:
        hard_blocks.append(f"düşüş kaçmış/tepe uzak %{drop_from_peak:.2f}")
        stats["tepe_late_block"] += 1
    if drop_from_peak > 1.0 and bounce_from_low <= TEPE_ERKEN_BLOCK_LOCAL_LOW_BOUNCE:
        hard_blocks.append(f"yerel dibe yakın; düşüş sonu short riski, bounce %{bounce_from_low:.2f}")
        stats["tepe_late_block"] += 1

    if rr >= min_rr_required:
        score += 1.2
    else:
        hard_blocks.append(f"RR zayıf {rr:.2f}/{min_rr_required:.2f}")

    if breakdown >= TREND_BREAKDOWN_MIN_SCORE:
        score += 1.8
    elif is_tepe_early and top_exit_score >= TEPE_ERKEN_MIN_EXIT_SCORE:
        score += 1.4
        soft_notes.append(f"tam kırılım beklenmedi; tepe para çıkışı erken skor {top_exit_score:.1f}")
    elif trend_guard_score >= TREND_GUARD_SCORE_BLOCK or green_streak >= 3:
        hard_blocks.append(f"trend var ama kırılım zayıf {breakdown:.1f}/{TREND_BREAKDOWN_MIN_SCORE:.1f}")
    else:
        score += 0.5
        soft_notes.append(f"kırılım sınırda {breakdown:.1f}")

    # V6: Whale Eye bonus/malus
    if whale_confidence == "ÇOK_YÜKSEK":
        score += 2.5
        soft_notes.append(f"🐋 Whale Eye ÇOK YÜKSEK güven: {whale_score:.1f}")
    elif whale_confidence == "YÜKSEK":
        score += 1.5
        soft_notes.append(f"🐋 Whale Eye YÜKSEK güven: {whale_score:.1f}")
    elif whale_confidence == "ORTA":
        score += 0.5
        soft_notes.append(f"🐋 Whale Eye ORTA güven: {whale_score:.1f}")
    elif whale_score < -5:
        score -= 2.0
        hard_blocks.append(f"🐋 Whale Eye balina karşıtı sinyal: {whale_score:.1f}")

    if verify >= MIN_VERIFY_SCORE_FOR_SIGNAL:
        score += 1.4
    elif is_tepe_early and top_exit_score >= TEPE_ERKEN_MIN_EXIT_SCORE:
        score += 0.7
    else:
        soft_notes.append(f"doğrulama düşük {verify:.1f}")

    passed = score >= MIN_QUALITY_SCORE and not hard_blocks
    reason_parts = hard_blocks if hard_blocks else soft_notes
    return passed, " | ".join(reason_parts[:6]) if reason_parts else "Para koruma kapısı temiz", round(score, 2)


# =========================================================
# ANA ANALİZ FONKSİYONU (WHALE EYE ENTEGRASYONLU)
# =========================================================

async def analyze_symbol(symbol: str, tickers24: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    symbol = normalize_symbol(symbol)

    if is_blocked_coin_symbol(symbol):
        stats["blocked_coin_skip"] += 1
        return None

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

    c1 = closes(k1); c5 = closes(k5); c15 = closes(k15)
    h1 = highs(k1); l1 = lows(k1); v1 = volumes(k1); v5 = volumes(k5)

    ema9_1 = ema(c1, 9); ema21_1 = ema(c1, 21); ema50_5 = ema(c5, 50)
    rsi1 = rsi(c1, 14); rsi5 = rsi(c5, 14); rsi15 = rsi(c15, 14)
    atr1 = atr(k1, 14); atr5 = atr(k5, 14)

    last_price = c1[-1]; prev_price = c1[-2]
    last_rsi1 = rsi1[-1]; prev_rsi1 = rsi1[-2]
    last_rsi5 = rsi5[-1]; last_rsi15 = rsi15[-1]
    last_ema9_1 = ema9_1[-1]; last_ema21_1 = ema21_1[-1]; last_ema50_5 = ema50_5[-1]
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

    pump_10m = pct_change(min(c1[-11:-1]), last_price) if len(c1) >= 12 else pct_change(min(c1[:-1]), last_price)
    pump_20m = pct_change(min(c1[-21:-1]), last_price) if len(c1) >= 22 else pct_change(min(c1[:-1]), last_price)
    pump_1h = pct_change(min(c5[-13:-1]), last_price) if len(c5) >= 14 else pct_change(min(c5[:-1]), last_price)
    dist_from_ema21 = pct_change(last_ema21_1, last_price)
    vol_ratio_1m = safe_float(v1[-1]) / max(avg(v1[-20:-1]), 1e-9)
    vol_ratio_5m = safe_float(v5[-1]) / max(avg(v5[-12:-1]), 1e-9)

    recent_high_20 = max(h1[-21:-1])
    last_kline = k1[-1]; prev_kline = k1[-2]
    rej_score = candle_rejection_score(last_kline)

    failed_breakout = safe_float(last_kline[2]) > recent_high_20 and last_price < recent_high_20
    micro_bear = last_price < prev_price and last_price < last_ema9_1
    bear_cross = last_ema9_1 < last_ema21_1 and ema9_1[-2] >= ema21_1[-2]
    losing_momentum = last_rsi1 < prev_rsi1 and last_rsi1 < 60
    weak_close = last_price <= safe_float(prev_kline[3]) or last_price < safe_float(last_kline[1])
    structure_turn = lower_highs(h1, 3) and lower_lows(l1, 3)
    red_count_5 = recent_red_count(k1, 5)
    green_streak = consecutive_green_count(k1, 6)

    breakdown = short_breakdown_confirmation(k1, k5)
    breakdown_score = safe_float(breakdown.get("score", 0))
    ict_context = build_ict_zone_context(k1, k5, k15, last_price)
    market_regime = build_market_regime_context(k1, k5, k15, last_price)
    support_resistance = build_support_resistance_context(k1, k5, k15, last_price, "SHORT")
    macro_context = await build_macro_correlation_context(symbol, k5, "SHORT")

    # =========================================================
    # V6 WHALE EYE - BURADA ÇAĞIRILIYOR
    # =========================================================
    price_change_5m = pct_change(c5[-2], last_price) if len(c5) >= 2 else 0.0
    whale_eye = await build_full_whale_eye_analysis(symbol, last_price, price_change_5m, k1, "SHORT")
    # =========================================================

    trend_guard = trend_continuation_guard(
        pump_10m=pump_10m, pump_20m=pump_20m, last_price=last_price,
        ema9=last_ema9_1, ema21=last_ema21_1, rsi1_val=last_rsi1, rsi5_val=last_rsi5,
        rej_score=rej_score, weak_close=weak_close, structure_turn=structure_turn,
        breakdown_score=breakdown_score, red_count=red_count_5,
    )

    strong_breakout_continue = (
        pump_20m > 2.8 and last_price > last_ema9_1 > last_ema21_1 and
        last_rsi1 > 66 and last_rsi5 > 66 and rej_score < 10 and
        not weak_close and not structure_turn and breakdown_score < TREND_BREAKDOWN_MIN_SCORE
    )

    candidate_score = 0.0; ready_score = 0.0; verify_score = 0.0
    reasons: List[str] = []

    if pump_10m >= 0.8:
        candidate_score += 9; reasons.append(f"10dk pump %{pump_10m:.2f}")
    if pump_20m >= 1.35:
        candidate_score += 11; reasons.append(f"20dk pump %{pump_20m:.2f}")
    if pump_1h >= 2.5:
        candidate_score += 10; reasons.append(f"1s pump %{pump_1h:.2f}")
    if last_rsi5 >= 64:
        candidate_score += 9; reasons.append(f"5dk RSI {last_rsi5:.1f}")
    if dist_from_ema21 >= 0.55:
        candidate_score += 9; reasons.append(f"EMA21 üstü %{dist_from_ema21:.2f}")
    if vol_ratio_1m >= 1.45:
        candidate_score += 8; reasons.append(f"1dk hacim x{vol_ratio_1m:.2f}")
    if vol_ratio_5m >= 1.25:
        candidate_score += 6; reasons.append(f"5dk hacim x{vol_ratio_5m:.2f}")

    if rej_score >= 10:
        ready_score += clamp(rej_score, 0, 18); reasons.append(f"İğne/red {rej_score:.1f}")
    if failed_breakout:
        ready_score += 13; reasons.append("Sahte kırılım")
    if micro_bear:
        ready_score += 9; reasons.append("1dk zayıf kapanış")
    if bear_cross:
        ready_score += 9; reasons.append("EMA9/21 kısa zayıflama")
    if losing_momentum:
        ready_score += 7; reasons.append("RSI momentum düşüşü")
    if structure_turn:
        ready_score += 10; reasons.append("Alt yapı bozuluyor")

    if last_price < last_ema9_1:
        verify_score += 10; reasons.append("Fiyat EMA9 altı")
    if last_price < last_ema21_1:
        verify_score += 8; reasons.append("Fiyat EMA21 altı")
    if last_rsi1 < 50:
        verify_score += 8; reasons.append("1dk RSI 50 altı")
    elif last_rsi1 < 54:
        verify_score += 4; reasons.append("1dk RSI gevşiyor")
    if weak_close:
        verify_score += 8; reasons.append("Zayıf son mum")
    if c5[-1] < c5[-2] and c5[-1] < c5[-3]:
        verify_score += 8; reasons.append("5dk gevşeme")
    if last_rsi15 >= 56:
        verify_score += 5; reasons.append("15dk hâlâ şişkin")
    if last_price > last_ema50_5:
        verify_score += 4; reasons.append("5dk EMA50 üstünde, dönüş alanı var")
    if breakdown_score >= TREND_BREAKDOWN_MIN_SCORE:
        verify_score += 9; stats["trend_breakdown_pass"] += 1
        reasons.append(f"Short kırılım teyidi {breakdown_score:.1f}: {breakdown.get('reason', '')}")
    elif breakdown_score >= TREND_BREAKDOWN_MIN_SCORE * 0.65:
        verify_score += 3
        reasons.append(f"Kırılım yarım {breakdown_score:.1f}: {breakdown.get('reason', '')}")

    # V6: Whale Eye skorunu ekle
    whale_score = safe_float(whale_eye.get("total_score", 0))
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))
    if whale_score > 0:
        reasons.append(f"🐋 Whale Eye: +{whale_score:.1f} ({whale_confidence})")
        if whale_confidence == "ÇOK_YÜKSEK":
            candidate_score += whale_score * 0.7
            ready_score += whale_score * 0.5
            verify_score += whale_score * 0.5
        elif whale_confidence == "YÜKSEK":
            candidate_score += whale_score * 0.5
            ready_score += whale_score * 0.4
            verify_score += whale_score * 0.3
        else:
            candidate_score += whale_score * 0.3
            ready_score += whale_score * 0.2
    elif whale_score < 0:
        reasons.append(f"🐋 Whale Eye uyarı: {whale_score:.1f}")
        candidate_score += whale_score * 0.5
        verify_score += whale_score * 0.3

    if SHORT_ICT_CONTEXT_ENABLED and isinstance(ict_context, dict) and ict_context.get("enabled"):
        short_ict_score = safe_float(ict_context.get("short_pro_score", 0))
        if short_ict_score >= ICT_SHORT_MIN_PRO_SCORE:
            candidate_score += 6; ready_score += 5; verify_score += 4
            reasons.append(f"ICT PRO SHORT onayı {short_ict_score:.1f}")
        if ict_context.get("in_premium_zone") or ict_context.get("above_equilibrium"):
            candidate_score += 2
        if ict_context.get("sweep_high"):
            ready_score += 4; reasons.append("ICT üst likidite süpürme")
        if ict_context.get("choch_down") or ict_context.get("bos_down") or ict_context.get("mss_down"):
            verify_score += 4; reasons.append("ICT BOS/CHOCH/MSS aşağı")

    entry_location = build_entry_location_guard(k1, k5, k15, "SHORT", last_price)
    if ENTRY_LOCATION_BONUS_ENABLED and entry_location.get("early"):
        candidate_score += SHORT_ENTRY_CANDIDATE_BONUS
        ready_score += SHORT_ENTRY_READY_BONUS
        verify_score += SHORT_ENTRY_VERIFY_BONUS
        stats["entry_location_early"] = stats.get("entry_location_early", 0) + 1
        reasons.append("Erken SHORT giriş bölgesi: " + str(entry_location.get("reason", "")))
    elif entry_location.get("late"):
        reasons.append("Geç SHORT giriş bölgesi: " + str(entry_location.get("reason", "")))

    ma_cross = build_ma_cross_entry_guard(k1, k15, "SHORT")
    if ma_cross.get("passed"):
        candidate_score += MA_CROSS_SIGNAL_BONUS
        verify_score += MA_CROSS_VERIFY_BONUS
        stats["ma_cross_pass"] = stats.get("ma_cross_pass", 0) + 1
        reasons.append("MA7/MA25 SHORT kesişim: " + str(ma_cross.get("reason", "")))
    else:
        reasons.append("MA7/MA25 SHORT bekle: " + str(ma_cross.get("reason", "")))

    candidate_score = max(candidate_score, 0.0)
    ready_score = max(ready_score, 0.0)
    verify_score = max(verify_score, 0.0)
    total_score = candidate_score + ready_score + verify_score

    entry = last_price
    stop, tp1, tp2, tp3, rr = calculate_short_levels(entry, h1, last_atr1, last_atr5)

    # V6: Whale Eye güçlüyse sinyal eşiğini düşür
    effective_min_signal = MIN_SIGNAL_SCORE
    effective_min_ready = MIN_READY_SCORE
    if whale_confidence == "ÇOK_YÜKSEK":
        effective_min_signal = max(40, MIN_SIGNAL_SCORE - 15)
        effective_min_ready = max(30, MIN_READY_SCORE - 10)
    elif whale_confidence == "YÜKSEK":
        effective_min_signal = max(48, MIN_SIGNAL_SCORE - 10)
        effective_min_ready = max(35, MIN_READY_SCORE - 6)

    why_blocker = ""
    why_actual = None
    why_required = None
    why_note = ""

    if candidate_score < MIN_CANDIDATE_SCORE:
        stage = "IGNORE"
        stats["weak_candidate_reject"] += 1
        why_blocker = "MIN_CANDIDATE_SCORE"
        why_actual = round(candidate_score, 2)
        why_required = MIN_CANDIDATE_SCORE
        why_note = "Aday skoru eşik altında kaldı."
    elif (candidate_score + ready_score) < effective_min_ready:
        stage = "HOT"
        stats["hot_add"] += 1
        why_blocker = "MIN_READY_SCORE"
        why_actual = round(candidate_score + ready_score, 2)
        why_required = round(effective_min_ready, 2)
        why_note = "Aday + hazır skoru READY eşiğine yetmedi."
    elif total_score < effective_min_signal:
        stage = "READY"
        stats["weak_signal_reject"] += 1
        why_blocker = "MIN_SIGNAL_SCORE"
        why_actual = round(total_score, 2)
        why_required = round(effective_min_signal, 2)
        why_note = "Toplam skor sinyal eşiğine yetmedi."
    else:
        stage = "SIGNAL"

    if stage == "SIGNAL" and rr < MIN_RR_TP1:
        stage = "READY"
        total_score -= 6
        stats["rr_block"] += 1
        reasons.append(f"RR zayıf {rr:.2f}")
        why_blocker = "MIN_RR_TP1"
        why_actual = round(rr, 2)
        why_required = MIN_RR_TP1
        why_note = "Risk/ödül TP1 için yetersiz kaldı."

    final_payload = {
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
        "trend_guard_score": safe_float(trend_guard.get("score", 0)),
        "breakdown_score": breakdown_score,
        "green_streak": green_streak,
        "red_count_5": red_count_5,
        "quality_score": 0.0,
        "quality_reason": "-",
        "reason": " | ".join(reasons[:15]) if reasons else "Sebep yok",
        "ict": ict_context,
        "entry_location": entry_location,
        "ma_cross": ma_cross,
        "whale_eye": whale_eye,  # V6 YENI
        "market_regime": market_regime,
        "macro": macro_context,
        "support_resistance": support_resistance,
        "direction": "SHORT",
        "why_blocker": why_blocker,
        "why_actual": why_actual,
        "why_required": why_required,
        "why_note": why_note,
    }

    if final_payload["stage"] == "SIGNAL" and ENTRY_LOCATION_LATE_BLOCK_ENABLED and not (MA_CROSS_ENTRY_ENABLED and MA_CROSS_IGNORE_15M_CANDLE_LOCATION_BLOCK) and not entry_location.get("passed", True):
        final_payload["stage"] = "READY"
        final_payload["signal_label"] = "İÇ TAKİP"
        final_payload["score"] = round(safe_float(final_payload.get("score", 0)) - 5, 2)
        final_payload["reason"] = f"{final_payload.get('reason', '')} | Giriş bölgesi kapısı: {entry_location.get('reason', '-')}"[:1400]
        final_payload["why_blocker"] = "ENTRY_LOCATION_SHORT_LATE"
        final_payload["why_actual"] = f"konum %{safe_float(entry_location.get('position_pct', 0)):.1f}"
        final_payload["why_required"] = f"üst/başlangıç >= %{SHORT_ENTRY_UPPER_START_MIN_POS*100:.0f}"
        final_payload["why_note"] = entry_location.get("reason", "-")
        stats["entry_location_late_block"] = stats.get("entry_location_late_block", 0) + 1
        remember_why_blocked(final_payload, final_payload["why_blocker"], final_payload["why_actual"], final_payload["why_required"], final_payload["why_note"])
        return final_payload

    if final_payload["stage"] == "SIGNAL" and MA_CROSS_ENTRY_ENABLED and not ma_cross.get("passed", False):
        final_payload["stage"] = "READY"
        final_payload["signal_label"] = "İÇ TAKİP"
        final_payload["score"] = round(safe_float(final_payload.get("score", 0)) - 8, 2)
        final_payload["reason"] = f"{final_payload.get('reason', '')} | MA7/MA25 kapısı: {ma_cross.get('reason', '-')}"[:1400]
        final_payload["why_blocker"] = "MA7_MA25_SHORT_CROSS" if not ma_cross.get("cross_ok", False) else "MA_15M_SHORT_DIRECTION"
        final_payload["why_actual"] = ma_cross.get("class", "-")
        final_payload["why_required"] = "1m MA7<MA25 kesişim + 15m yön SHORT"
        final_payload["why_note"] = ma_cross.get("reason", "-")
        if ma_cross.get("cross_ok", False) and not ma_cross.get("direction_ok", True):
            stats["ma_cross_15m_block"] = stats.get("ma_cross_15m_block", 0) + 1
        else:
            stats["ma_cross_block"] = stats.get("ma_cross_block", 0) + 1
        remember_why_blocked(final_payload, final_payload["why_blocker"], final_payload["why_actual"], final_payload["why_required"], final_payload["why_note"])
        return final_payload

    if (strong_breakout_continue or trend_guard.get("blocked")) and whale_confidence not in ("ÇOK_YÜKSEK", "YÜKSEK"):
        stats["trend_strong_reject"] += 1
        stats["trend_guard_block_signal"] += 1
        final_payload["stage"] = "HOT"
        final_payload["score"] = round(max(total_score, MIN_CANDIDATE_SCORE), 2)
        final_payload["reason"] = f"TREND DEVAM KORUMASI: {trend_guard.get('reason', '')} | {final_payload['reason']}"[:900]
        final_payload["why_blocker"] = "TREND_GUARD_SCORE_BLOCK"
        final_payload["why_actual"] = safe_float(trend_guard.get("score", 0))
        final_payload["why_required"] = TREND_GUARD_SCORE_BLOCK
        final_payload["why_note"] = str(trend_guard.get("reason", ""))[:300]
        remember_why_blocked(final_payload, final_payload["why_blocker"], final_payload["why_actual"], final_payload["why_required"], final_payload["why_note"])
        return final_payload

    if final_payload["stage"] == "SIGNAL" and not (MA_CROSS_ENTRY_ENABLED and ma_cross.get("passed", False)):
        close_gate = short_close_confirmation_gate(k5, k15, final_payload)
        final_payload["close_confirm_gate"] = close_gate
        final_payload["reason"] = f"{final_payload.get('reason', '')} | 5m/15m: {close_gate.get('reason', '-')}"[:1400]
        if not close_gate.get("passed", False):
            final_payload["stage"] = "READY"
            final_payload["score"] = round(safe_float(final_payload.get("score", 0)) - 6, 2)
            stats["close_confirm_block"] += 1
            # Hangi kapanış kapısı taktıysa /neden için açık yaz.
            if CLOSE_CONFIRM_REQUIRE_5M and safe_float(close_gate.get("score5", 0)) < CLOSE_CONFIRM_MIN_5M_SCORE:
                final_payload["why_blocker"] = "CLOSE_CONFIRM_MIN_5M_SCORE"
                final_payload["why_actual"] = close_gate.get("score5", 0)
                final_payload["why_required"] = CLOSE_CONFIRM_MIN_5M_SCORE
            elif CLOSE_CONFIRM_REQUIRE_15M and safe_float(close_gate.get("score15", 0)) < CLOSE_CONFIRM_MIN_15M_SCORE:
                final_payload["why_blocker"] = "CLOSE_CONFIRM_MIN_15M_SCORE"
                final_payload["why_actual"] = close_gate.get("score15", 0)
                final_payload["why_required"] = CLOSE_CONFIRM_MIN_15M_SCORE
            else:
                final_payload["why_blocker"] = "CLOSE_CONFIRM_GATE"
                final_payload["why_actual"] = f"5m={close_gate.get('score5', 0)} 15m={close_gate.get('score15', 0)}"
                final_payload["why_required"] = "-"
            final_payload["why_note"] = close_gate.get("reason", "-")
            remember_why_blocked(final_payload, final_payload["why_blocker"], final_payload["why_actual"], final_payload["why_required"], final_payload["why_note"])
            return final_payload

    if final_payload["stage"] == "SIGNAL":
        passed, q_reason, q_score = final_quality_gate(final_payload)
        final_payload["quality_score"] = q_score
        final_payload["quality_reason"] = q_reason
        if not passed:
            final_payload["stage"] = "READY"
            final_payload["score"] = round(safe_float(final_payload["score"]) - 7, 2)
            stats["quality_gate_block"] += 1
            final_payload["reason"] = f"{final_payload['reason']} | Kalite kapısı: {q_reason}"
            final_payload["why_blocker"] = "MIN_QUALITY_SCORE"
            final_payload["why_actual"] = q_score
            final_payload["why_required"] = MIN_QUALITY_SCORE
            final_payload["why_note"] = q_reason
            remember_why_blocked(final_payload, "MIN_QUALITY_SCORE", q_score, MIN_QUALITY_SCORE, q_reason)

    final_payload["position_plan"] = build_position_plan({**final_payload, "direction": "SHORT"})
    final_payload = enforce_single_short_al_rules(final_payload)
    return final_payload



async def analyze_long_symbol(symbol: str, tickers24: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not LONG_ENGINE_ENABLED:
        return None

    symbol = normalize_symbol(symbol)
    if is_blocked_coin_symbol(symbol):
        return None
    if okx_live_symbols and symbol not in okx_live_symbols:
        return None
    if symbol_temporarily_blocked(symbol):
        return None
    if tickers24 and symbol not in tickers24:
        return None

    k1 = await get_klines(symbol, "1m", 120)
    k5 = await get_klines(symbol, "5m", 120)
    k15 = await get_klines(symbol, "15m", 120)
    if len(k1) < 60 or len(k5) < 60 or len(k15) < 50:
        return None

    c1 = closes(k1); h1 = highs(k1); l1 = lows(k1); v1 = volumes(k1)
    c5 = closes(k5); v5 = volumes(k5); c15 = closes(k15)
    ema9_1 = ema(c1, 9); ema21_1 = ema(c1, 21)
    ema50_5 = ema(c5, 50)
    rsi1 = rsi(c1, 14); rsi5 = rsi(c5, 14); rsi15 = rsi(c15, 14)
    atr1 = atr(k1, 14); atr5 = atr(k5, 14)

    last_price = c1[-1]
    last_rsi1 = rsi1[-1]; prev_rsi1 = rsi1[-2]
    last_rsi5 = rsi5[-1]; last_rsi15 = rsi15[-1]
    last_atr1 = max(atr1[-1], last_price * 0.0014)

    t24 = tickers24.get(symbol, {})
    last_px_24 = safe_float(t24.get("last", 0)) or last_price
    vol24h = safe_float(t24.get("vol24h", 0))
    vol_ccy_24h = safe_float(t24.get("volCcy24h", 0))
    quote_vol = max(vol_ccy_24h, vol24h * max(last_px_24, 1e-9))
    if quote_vol < MIN_24H_QUOTE_VOLUME:
        return None

    ict = build_ict_zone_context(k1, k5, k15, last_price)
    if not ict.get("enabled") or safe_float(ict.get("range_pct", 0)) < ICT_MIN_RANGE_PCT:
        return None
    market_regime = build_market_regime_context(k1, k5, k15, last_price)
    support_resistance = build_support_resistance_context(k1, k5, k15, last_price, "LONG")
    macro_context = await build_macro_correlation_context(symbol, k5, "LONG")

    drop_20m = max(0.0, abs(pct_change(max(c1[-21:-1]), last_price))) if len(c1) >= 22 and last_price < max(c1[-21:-1]) else 0.0
    drop_1h = max(0.0, abs(pct_change(max(c5[-13:-1]), last_price))) if len(c5) >= 14 and last_price < max(c5[-13:-1]) else 0.0
    drop_10m = max(0.0, abs(pct_change(max(c1[-11:-1]), last_price))) if len(c1) >= 12 and last_price < max(c1[-11:-1]) else 0.0
    bounce_from_low = pct_change(min(l1[-20:]), last_price) if len(l1) >= 20 and min(l1[-20:]) > 0 else 0.0
    vol_ratio_1m = safe_float(v1[-1]) / max(avg(v1[-20:-1]), 1e-9)
    vol_ratio_5m = safe_float(v5[-1]) / max(avg(v5[-12:-1]), 1e-9)
    upper_wick, lower_wick, body_ratio, red = candle_wick_ratios(k1[-1])
    green = not red

    whale_eye = await build_full_whale_eye_analysis(symbol, last_price, -drop_10m, k1, "LONG")

    book = await get_okx_orderbook(symbol)
    trades = await get_okx_recent_trades(symbol, 120)
    flow = analyze_trade_flow(trades)

    buy_to_sell = safe_float(flow.get("buy_to_sell", 0))
    sell_to_buy = safe_float(flow.get("sell_to_buy", 0))
    book_pressure = safe_float(book.get("book_pressure", 0))
    bid_wall_added = bool(book.get("bid_wall_added", False))
    ask_wall_pulled = bool(book.get("ask_wall_pulled", False))
    bid_defense = bool(book.get("ok")) and (bid_wall_added or ask_wall_pulled or book_pressure <= -0.12)
    buyer_defense = lower_wick >= 0.28 or buy_to_sell >= LONG_MIN_BUY_TO_SELL or bid_defense or (green and vol_ratio_1m >= 0.85)

    structure = long_structure_confirmation(k1, k5, ict)
    structure_score = safe_float(structure.get("score", 0))
    close_gate = long_close_confirmation_gate(k5, k15)
    entry_location = build_entry_location_guard(k1, k5, k15, "LONG", last_price)

    true_structure_up = bool(ict.get("bos_up") or ict.get("choch_up") or ict.get("mss_up"))
    ema9_15 = ema(c15, 9)
    ema21_15 = ema(c15, 21)
    price_below_15m_fast = bool(ema9_15 and ema21_15 and last_price < ema9_15[-1] and last_price < ema21_15[-1])
    bearish_context = str(ict.get("structure_bias", "")).upper() == "BEARISH" and not true_structure_up
    seller_flow_dominant = sell_to_buy >= LONG_SELL_TO_BUY_HARD_BLOCK and buy_to_sell < LONG_MIN_BUY_TO_SELL
    weak_live_volume = vol_ratio_1m <= LONG_WEAK_VOL_1M_BLOCK and vol_ratio_5m <= LONG_WEAK_VOL_5M_BLOCK
    mixed_bearish_zone = bool(ict.get("bearish_fvg_active") or ict.get("bearish_ob_near"))
    long_hard_blocks: List[str] = []
    if LONG_BEARISH_CONTEXT_HARD_BLOCK_ENABLED:
        if bearish_context and seller_flow_dominant and (weak_live_volume or price_below_15m_fast or mixed_bearish_zone):
            long_hard_blocks.append(
                f"LONG yasak: BEARISH yapı + gerçek BOS/CHOCH/MSS↑ yok + satıcı akışı x{sell_to_buy:.2f}; "
                f"hacim 1m/5m x{vol_ratio_1m:.2f}/x{vol_ratio_5m:.2f}"
            )
        if LONG_REQUIRE_TRUE_STRUCTURE_UP and bearish_context and not ict.get("sweep_low") and safe_float(ict.get("short_pro_score", 0)) >= safe_float(ict.get("long_pro_score", 0)) - 1.0:
            long_hard_blocks.append(
                f"LONG yasak: yapı BEARISH, sweep alt yok, SHORT ICT {safe_float(ict.get('short_pro_score', 0)):.1f} LONG ICT'ye yakın"
            )

    candidate_score = 0.0; ready_score = 0.0; verify_score = 0.0
    reasons: List[str] = []

    if drop_20m >= LONG_MIN_DROP_20M:
        candidate_score += 7; reasons.append(f"20dk düşüş %{drop_20m:.2f}")
    if drop_1h >= LONG_MIN_DROP_1H:
        candidate_score += 8; reasons.append(f"1s düşüş %{drop_1h:.2f}")
    if ict.get("in_discount_zone"):
        candidate_score += 12; reasons.append("ICT discount bölgesi")
    if ict.get("sweep_low"):
        ready_score += 14; reasons.append("Alt likidite süpürüldü")
    if lower_wick >= 0.28:
        ready_score += 9; reasons.append(f"Alt fitil {lower_wick:.2f}")
    if buyer_defense:
        ready_score += 8; reasons.append("Alıcı savunması")
    if buy_to_sell >= LONG_MIN_BUY_TO_SELL:
        ready_score += 8; reasons.append(f"Alış baskın x{buy_to_sell:.2f}")
    if bid_defense:
        ready_score += 7; reasons.append("Orderbook bid savunması")
    if safe_float(ict.get("long_pro_score", 0)) >= ICT_LONG_MIN_PRO_SCORE:
        candidate_score += 6; ready_score += 5; verify_score += 3
        reasons.append(f"ICT PRO LONG onayı {safe_float(ict.get('long_pro_score', 0)):.1f}")
    if structure_score >= ICT_MIN_CHOCH_SCORE:
        verify_score += 12; reasons.append(f"CHOCH yukarı {structure_score:.1f}")
    if last_price > ema9_1[-1]:
        verify_score += 6; reasons.append("EMA9 üstü")
    if last_price > ema21_1[-1]:
        verify_score += 5; reasons.append("EMA21 üstü")
    if last_rsi1 > prev_rsi1 and last_rsi1 >= 45:
        verify_score += 5; reasons.append("RSI toparlanıyor")

    if ENTRY_LOCATION_BONUS_ENABLED and entry_location.get("early"):
        candidate_score += LONG_ENTRY_CANDIDATE_BONUS
        ready_score += LONG_ENTRY_READY_BONUS
        verify_score += LONG_ENTRY_VERIFY_BONUS
        stats["entry_location_early"] = stats.get("entry_location_early", 0) + 1
        reasons.append("Erken LONG giriş bölgesi: " + str(entry_location.get("reason", "")))
    elif entry_location.get("late"):
        reasons.append("Geç LONG giriş bölgesi: " + str(entry_location.get("reason", "")))

    ma_cross = build_ma_cross_entry_guard(k1, k15, "LONG")
    if ma_cross.get("passed"):
        candidate_score += MA_CROSS_SIGNAL_BONUS
        verify_score += MA_CROSS_VERIFY_BONUS
        stats["ma_cross_pass"] = stats.get("ma_cross_pass", 0) + 1
        reasons.append("MA7/MA25 LONG kesişim: " + str(ma_cross.get("reason", "")))
    else:
        reasons.append("MA7/MA25 LONG bekle: " + str(ma_cross.get("reason", "")))

    whale_score = safe_float(whale_eye.get("total_score", 0))
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))
    if whale_score > 0:
        reasons.append(f"🐋 Whale Eye LONG: +{whale_score:.1f} ({whale_confidence})")
        candidate_score += whale_score * 0.3
        verify_score += whale_score * 0.3
    elif whale_score < 0:
        reasons.append(f"🐋 Whale Eye LONG uyarı: {whale_score:.1f}")

    candidate_score = max(candidate_score, 0.0)
    ready_score = max(ready_score, 0.0)
    verify_score = max(verify_score, 0.0)
    total_score = candidate_score + ready_score + verify_score
    entry = last_price
    stop, tp1, tp2, tp3, rr = calculate_long_levels(entry, l1, last_atr1, last_atr1)

    quality_score = 0.0
    if ict.get("in_discount_zone"):
        quality_score += 1.4
    if ict.get("sweep_low"):
        quality_score += 1.5
    if buyer_defense:
        quality_score += 1.2
    if structure_score >= ICT_MIN_CHOCH_SCORE:
        quality_score += 1.4
    if rr >= LONG_MIN_RR_TP1:
        quality_score += 0.7
    quality_score = round(clamp(quality_score, 0.0, 10.0), 2)

    if candidate_score < LONG_MIN_CANDIDATE_SCORE:
        stage = "IGNORE"; stats["long_reject"] += 1
    elif total_score >= LONG_MIN_SIGNAL_SCORE and verify_score >= LONG_MIN_VERIFY_SCORE:
        stage = "SIGNAL"; stats["long_ict_signal"] += 1
    else:
        stage = "READY"; stats["long_ready"] += 1

    if stage == "SIGNAL" and rr < LONG_MIN_RR_TP1:
        stage = "READY"; stats["rr_block"] += 1
    if stage == "SIGNAL" and not (MA_CROSS_ENTRY_ENABLED and ma_cross.get("passed", False)) and not close_gate.get("passed", False):
        stage = "READY"; stats["long_close_confirm_block"] += 1
    if stage == "SIGNAL" and quality_score < LONG_MIN_QUALITY_SCORE:
        stage = "READY"; stats["long_quality_block"] += 1

    if stage == "SIGNAL" and long_hard_blocks:
        stage = "READY"
        stats["long_conflict_block"] += 1
        reasons.extend(long_hard_blocks)

    payload = {
        "symbol": symbol, "direction": "LONG", "stage": stage,
        "signal_label": "LONG AL" if stage == "SIGNAL" else "İÇ TAKİP",
        "score": round(total_score, 2),
        "candidate_score": round(candidate_score, 2),
        "ready_score": round(ready_score, 2),
        "verify_score": round(verify_score, 2),
        "price": entry, "stop": stop, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "rr": round(rr, 2),
        "drop_10m": round(drop_10m, 2), "drop_20m": round(drop_20m, 2), "drop_1h": round(drop_1h, 2),
        "pump_10m": round(-drop_10m, 2), "pump_20m": round(-drop_20m, 2), "pump_1h": round(-drop_1h, 2),
        "rsi1": round(last_rsi1, 2), "rsi5": round(last_rsi5, 2), "rsi15": round(last_rsi15, 2),
        "vol_ratio_1m": round(vol_ratio_1m, 2), "vol_ratio_5m": round(vol_ratio_5m, 2),
        "quote_volume": quote_vol,
        "breakdown_score": structure_score, "long_structure_score": structure_score,
        "green_streak": consecutive_green_count(k1, 6), "red_count_5": recent_red_count(k1, 5),
        "quality_score": quality_score, "quality_reason": "-",
        "reason": " | ".join(reasons[:16]) if reasons else "Long sebep yok",
        "ict": ict, "long_close_gate": close_gate,
        "entry_location": entry_location,
        "ma_cross": ma_cross,
        "trade_flow": flow, "orderbook": book,
        "whale_eye": whale_eye,
        "market_regime": market_regime,
        "macro": macro_context,
        "support_resistance": support_resistance,
        "invisible_class": "ICT LONG", "invisible_score": round(quality_score * 12.0, 1),
        "invisible_decision": "LONG_AL_SERBEST" if stage == "SIGNAL" else "LONG_TAKIP",
    }
    if payload["stage"] == "SIGNAL" and ENTRY_LOCATION_LATE_BLOCK_ENABLED and not (MA_CROSS_ENTRY_ENABLED and MA_CROSS_IGNORE_15M_CANDLE_LOCATION_BLOCK) and not entry_location.get("passed", True):
        payload["stage"] = "READY"
        payload["signal_label"] = "İÇ TAKİP"
        payload["score"] = round(safe_float(payload.get("score", 0)) - 5, 2)
        payload["reason"] = f"{payload.get('reason', '')} | Giriş bölgesi kapısı: {entry_location.get('reason', '-')}"[:1400]
        payload["why_blocker"] = "ENTRY_LOCATION_LONG_LATE"
        payload["why_actual"] = f"konum %{safe_float(entry_location.get('position_pct', 0)):.1f}"
        payload["why_required"] = f"alt/başlangıç <= %{LONG_ENTRY_LOWER_START_MAX_POS*100:.0f}"
        payload["why_note"] = entry_location.get("reason", "-")
        stats["entry_location_late_block"] = stats.get("entry_location_late_block", 0) + 1
        remember_why_blocked(payload, payload["why_blocker"], payload["why_actual"], payload["why_required"], payload["why_note"])

    if payload["stage"] == "SIGNAL" and MA_CROSS_ENTRY_ENABLED and not ma_cross.get("passed", False):
        payload["stage"] = "READY"
        payload["signal_label"] = "İÇ TAKİP"
        payload["score"] = round(safe_float(payload.get("score", 0)) - 8, 2)
        payload["reason"] = f"{payload.get('reason', '')} | MA7/MA25 kapısı: {ma_cross.get('reason', '-')}"[:1400]
        payload["why_blocker"] = "MA7_MA25_LONG_CROSS" if not ma_cross.get("cross_ok", False) else "MA_15M_LONG_DIRECTION"
        payload["why_actual"] = ma_cross.get("class", "-")
        payload["why_required"] = "1m MA7>MA25 kesişim + 15m yön LONG"
        payload["why_note"] = ma_cross.get("reason", "-")
        if ma_cross.get("cross_ok", False) and not ma_cross.get("direction_ok", True):
            stats["ma_cross_15m_block"] = stats.get("ma_cross_15m_block", 0) + 1
        else:
            stats["ma_cross_block"] = stats.get("ma_cross_block", 0) + 1
        remember_why_blocked(payload, payload["why_blocker"], payload["why_actual"], payload["why_required"], payload["why_note"])

    payload["position_plan"] = build_position_plan(payload)
    return enforce_single_long_al_rules(payload)



def _bucket_float(v: float, cuts: List[float], names: List[str]) -> str:
    try:
        v = float(v)
    except Exception:
        return "NA"
    for i, cut in enumerate(cuts):
        if v < cut:
            return names[i]
    return names[-1]


def _tp_rank(level: str) -> int:
    return {"STOP": -1, "NÖTR": 0, "NO_HIT": 0, "YOK": 0, "TP1": 1, "TP2": 2, "TP3": 3}.get(str(level).upper(), 0)





# =========================================================
# PRO PLUS: DESTEK/DİRENÇ + REJİM + MAKRO + POZİSYON + BACKTEST
# =========================================================
def _pivot_levels(values_high: List[float], values_low: List[float], left: int = 2, right: int = 2) -> Tuple[List[float], List[float]]:
    resistances: List[float] = []
    supports: List[float] = []
    n = min(len(values_high), len(values_low))
    if n < left + right + 3:
        return supports, resistances
    for i in range(left, n - right):
        h = values_high[i]
        l = values_low[i]
        prev_h = values_high[i-left:i]
        next_h = values_high[i+1:i+right+1]
        prev_l = values_low[i-left:i]
        next_l = values_low[i+1:i+right+1]
        if prev_h and next_h and h >= max(prev_h) and h >= max(next_h):
            resistances.append(h)
        if prev_l and next_l and l <= min(prev_l) and l <= min(next_l):
            supports.append(l)
    return supports, resistances


def _cluster_levels(levels: List[float], price: float, cluster_pct: float = SR_CLUSTER_PCT) -> List[Dict[str, Any]]:
    clean = sorted([x for x in levels if x > 0])
    if not clean:
        return []
    clusters: List[List[float]] = []
    for lv in clean:
        if not clusters:
            clusters.append([lv])
            continue
        center = avg(clusters[-1])
        if abs(pct_change(center, lv)) <= cluster_pct:
            clusters[-1].append(lv)
        else:
            clusters.append([lv])
    out: List[Dict[str, Any]] = []
    for vals in clusters:
        center = avg(vals)
        out.append({"level": center, "touches": len(vals), "distance_pct": pct_change(price, center) if price > 0 else 0.0, "score": len(vals)})
    return sorted(out, key=lambda x: (abs(safe_float(x.get("distance_pct", 999))), -safe_float(x.get("score", 0))))


def build_support_resistance_context(k1: List[List[Any]], k5: List[List[Any]], k15: List[List[Any]], price: float, direction: str = "SHORT") -> Dict[str, Any]:
    if not SR_ENGINE_ENABLED:
        return {"enabled": False, "decision": "KAPALI", "passed": True, "reason": "SR motoru kapalı"}
    if len(k1) < 40 or len(k5) < 30:
        return {"enabled": True, "decision": "VERI_YOK", "passed": False, "reason": "SR verisi yetersiz"}
    direction = (direction or "SHORT").upper()
    h1, l1 = highs(k1[-SR_LOOKBACK_1M:]), lows(k1[-SR_LOOKBACK_1M:])
    h5, l5 = highs(k5[-SR_LOOKBACK_5M:]), lows(k5[-SR_LOOKBACK_5M:])
    h15, l15 = highs(k15[-48:]) if len(k15) >= 48 else highs(k15), lows(k15[-48:]) if len(k15) >= 48 else lows(k15)
    s1, r1 = _pivot_levels(h1, l1, SR_PIVOT_LEFT, SR_PIVOT_RIGHT)
    s5, r5 = _pivot_levels(h5, l5, SR_PIVOT_LEFT, SR_PIVOT_RIGHT)
    s15, r15 = _pivot_levels(h15, l15, SR_PIVOT_LEFT, SR_PIVOT_RIGHT)
    support_clusters = _cluster_levels(s1 + s5 + s15 + [min(l1[-20:])], price)
    resistance_clusters = _cluster_levels(r1 + r5 + r15 + [max(h1[-20:])], price)
    below = [x for x in support_clusters if safe_float(x.get("level")) < price]
    above = [x for x in resistance_clusters if safe_float(x.get("level")) > price]
    nearest_support = max(below, key=lambda x: safe_float(x.get("level")), default={})
    nearest_resistance = min(above, key=lambda x: safe_float(x.get("level")), default={})
    sup = safe_float(nearest_support.get("level", 0))
    res = safe_float(nearest_resistance.get("level", 0))
    support_dist = abs(pct_change(price, sup)) if sup > 0 else 999.0
    resistance_dist = abs(pct_change(price, res)) if res > 0 else 999.0
    if direction == "LONG":
        near_zone = support_dist <= SR_NEAR_LEVEL_PCT or price <= safe_float(nearest_support.get("level", 0)) * (1 + SR_NEAR_LEVEL_PCT/100.0) if sup > 0 else False
        wall_side = "direnç"
        decision = "LONG_SR_TEMIZ" if near_zone else "LONG_DESTEK_ZAYIF"
        passed = True
        reason = f"LONG: destek {fmt_num(sup)} mesafe %{support_dist:.2f}, direnç {fmt_num(res)} mesafe %{resistance_dist:.2f}"
    else:
        near_zone = resistance_dist <= SR_NEAR_LEVEL_PCT or price >= safe_float(nearest_resistance.get("level", 0)) * (1 - SR_NEAR_LEVEL_PCT/100.0) if res > 0 else False
        wall_side = "destek"
        decision = "SHORT_SR_TEMIZ" if near_zone else "SHORT_DIRENC_ZAYIF"
        passed = True
        reason = f"SHORT: direnç {fmt_num(res)} mesafe %{resistance_dist:.2f}, destek {fmt_num(sup)} mesafe %{support_dist:.2f}"
    return {
        "enabled": True,
        "passed": passed,
        "decision": decision,
        "direction": direction,
        "nearest_support": sup,
        "nearest_resistance": res,
        "support_distance_pct": round(support_dist, 2),
        "resistance_distance_pct": round(resistance_dist, 2),
        "support_score": safe_float(nearest_support.get("score", 0)),
        "resistance_score": safe_float(nearest_resistance.get("score", 0)),
        "near_trade_zone": bool(near_zone),
        "wall_side": wall_side,
        "reason": reason,
    }


def sr_final_gate(payload: Dict[str, Any]) -> Tuple[bool, str]:
    sr = payload.get("support_resistance") if isinstance(payload.get("support_resistance"), dict) else {}
    if not SR_ENGINE_ENABLED or not sr or not sr.get("enabled"):
        return True, "SR kapısı kapalı/yok"
    direction = str(payload.get("direction", "SHORT")).upper()
    price = safe_float(payload.get("price", 0))
    stop = safe_float(payload.get("stop", 0))
    tp1 = safe_float(payload.get("tp1", 0))
    sup = safe_float(sr.get("nearest_support", 0))
    res = safe_float(sr.get("nearest_resistance", 0))
    vol1 = safe_float(payload.get("vol_ratio_1m", 0))
    vol5 = safe_float(payload.get("vol_ratio_5m", 0))
    flow = payload.get("trade_flow") if isinstance(payload.get("trade_flow"), dict) else {}
    buy_to_sell = safe_float(flow.get("buy_to_sell", 0))
    sell_to_buy = safe_float(flow.get("sell_to_buy", 0))
    reasons: List[str] = []
    passed = True
    if direction == "LONG":
        if sup <= 0 or safe_float(sr.get("support_distance_pct", 999)) > SR_NEAR_LEVEL_PCT:
            passed = False; reasons.append(f"LONG destekten uzak %{safe_float(sr.get('support_distance_pct', 999)):.2f}")
        if SR_BLOCK_IF_TP1_WALL and res > 0 and res < tp1 * (1 + SR_TP1_ROOM_BUFFER_PCT/100.0):
            passed = False; reasons.append(f"TP1 önünde yakın direnç {fmt_num(res)}")
        if sup > 0 and stop > sup * (1 - SR_STOP_BEHIND_LEVEL_PCT/100.0):
            passed = False; reasons.append(f"stop desteğin arkasında değil: stop {fmt_num(stop)} destek {fmt_num(sup)}")
        if SR_BLOCK_WEAK_ZONE_LOW_FLOW and vol1 < LONG_WEAK_VOL_1M_BLOCK and vol5 < LONG_WEAK_VOL_5M_BLOCK and buy_to_sell < LONG_MIN_BUY_TO_SELL:
            passed = False; reasons.append(f"LONG hacim/flow zayıf: vol {vol1:.2f}/{vol5:.2f}, flow {buy_to_sell:.2f}")
    else:
        if res <= 0 or safe_float(sr.get("resistance_distance_pct", 999)) > SR_NEAR_LEVEL_PCT:
            passed = False; reasons.append(f"SHORT dirençten uzak %{safe_float(sr.get('resistance_distance_pct', 999)):.2f}")
        if SR_BLOCK_IF_TP1_WALL and sup > 0 and sup > tp1 * (1 - SR_TP1_ROOM_BUFFER_PCT/100.0):
            passed = False; reasons.append(f"TP1 önünde yakın destek {fmt_num(sup)}")
        if res > 0 and stop < res * (1 + SR_STOP_BEHIND_LEVEL_PCT/100.0):
            passed = False; reasons.append(f"stop direncin arkasında değil: stop {fmt_num(stop)} direnç {fmt_num(res)}")
        if SR_BLOCK_WEAK_ZONE_LOW_FLOW and vol1 < 0.55 and vol5 < 0.35 and sell_to_buy < 1.10:
            passed = False; reasons.append(f"SHORT hacim/flow zayıf: vol {vol1:.2f}/{vol5:.2f}, flow {sell_to_buy:.2f}")
    return passed, " | ".join(reasons) if reasons else sr.get("reason", "SR temiz")


def build_market_regime_context(k1: List[List[Any]], k5: List[List[Any]], k15: List[List[Any]], price: float) -> Dict[str, Any]:
    if not MARKET_REGIME_ENGINE_ENABLED:
        return {"enabled": False, "regime": "KAPALI", "bias": "NÖTR", "passed": True, "reason": "Rejim motoru kapalı"}
    if len(k5) < 55 or len(k15) < 30:
        return {"enabled": True, "regime": "VERI_YOK", "bias": "NÖTR", "passed": False, "reason": "Rejim verisi yetersiz"}
    c5 = closes(k5); h5 = highs(k5); l5 = lows(k5); v5 = volumes(k5)
    c15 = closes(k15)
    e9 = ema(c5, 9); e21 = ema(c5, 21); e50 = ema(c5, 50)
    r5 = rsi(c5, 14); atr5 = atr(k5, 14)
    width_pct = abs(pct_change(min(l5[-30:]), max(h5[-30:]))) if min(l5[-30:]) > 0 else 0.0
    ema_gap = pct_change(e50[-1], price) if e50[-1] > 0 else 0.0
    vol_ratio = safe_float(v5[-1]) / max(avg(v5[-20:-1]), 1e-9)
    last_range = max(h5[-1] - l5[-1], 1e-9)
    atr_now = max(atr5[-1], price * 0.001)
    breakout_up = c5[-1] > max(h5[-20:-1]) and last_range >= atr_now * REGIME_BREAKOUT_ATR_MULT
    breakout_down = c5[-1] < min(l5[-20:-1]) and last_range >= atr_now * REGIME_BREAKOUT_ATR_MULT
    uptrend = price > e9[-1] > e21[-1] > e50[-1] and ema_gap >= REGIME_TREND_EMA_GAP_PCT
    downtrend = price < e9[-1] < e21[-1] < e50[-1] and ema_gap <= -REGIME_TREND_EMA_GAP_PCT
    range_mode = width_pct <= REGIME_RANGE_MAX_WIDTH_PCT and not breakout_up and not breakout_down
    if breakout_up:
        regime, bias = "BREAKOUT_UP", "LONG"
    elif breakout_down:
        regime, bias = "BREAKDOWN_DOWN", "SHORT"
    elif uptrend and r5[-1] >= 55:
        regime, bias = "TREND_UP", "LONG"
    elif downtrend and r5[-1] <= 45:
        regime, bias = "TREND_DOWN", "SHORT"
    elif range_mode:
        regime, bias = "RANGE", "NÖTR"
    elif r5[-1] >= 68 and vol_ratio >= 1.15:
        regime, bias = "PUMP_DEVAM", "LONG"
    elif r5[-1] <= 34 and vol_ratio >= 1.15:
        regime, bias = "DUSUS_DEVAM", "SHORT"
    else:
        regime, bias = "KARISIK", "NÖTR"
    score = 0.0
    if bias == "LONG": score += 2.0
    if bias == "SHORT": score -= 2.0
    return {"enabled": True, "regime": regime, "bias": bias, "score": round(score, 2), "width_pct": round(width_pct, 2), "ema_gap_pct": round(ema_gap, 2), "vol_ratio": round(vol_ratio, 2), "reason": f"Rejim {regime} | bias {bias} | genişlik %{width_pct:.2f} | EMA50 fark %{ema_gap:.2f} | vol x{vol_ratio:.2f}"}


def regime_final_gate(payload: Dict[str, Any]) -> Tuple[bool, str]:
    reg = payload.get("market_regime") if isinstance(payload.get("market_regime"), dict) else {}
    if not MARKET_REGIME_ENGINE_ENABLED or not reg or not reg.get("enabled"):
        return True, "Rejim kapısı kapalı/yok"
    direction = str(payload.get("direction", "SHORT")).upper()
    regime = str(reg.get("regime", ""))
    bias = str(reg.get("bias", "NÖTR"))
    if not REGIME_BLOCK_COUNTER_TREND:
        return True, reg.get("reason", "Rejim pass")
    if direction == "LONG" and bias == "SHORT" and regime in ("TREND_DOWN", "BREAKDOWN_DOWN", "DUSUS_DEVAM"):
        return False, f"Rejim LONG'a ters: {regime}"
    if direction == "SHORT" and bias == "LONG" and regime in ("TREND_UP", "BREAKOUT_UP", "PUMP_DEVAM"):
        return False, f"Rejim SHORT'a ters: {regime}"
    return True, reg.get("reason", "Rejim temiz")


def _series_returns(values: List[float], lookback: int = 30) -> List[float]:
    vals = values[-lookback:]
    out = []
    for i in range(1, len(vals)):
        out.append(pct_change(vals[i-1], vals[i]))
    return out


def _corr(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n < 8:
        return 0.0
    a = a[-n:]; b = b[-n:]
    ma, mb = avg(a), avg(b)
    da = [x-ma for x in a]; db = [x-mb for x in b]
    va = sum(x*x for x in da); vb = sum(x*x for x in db)
    if va <= 0 or vb <= 0:
        return 0.0
    return sum(x*y for x,y in zip(da, db)) / ((va ** 0.5) * (vb ** 0.5))


async def build_macro_correlation_context(symbol: str, k5_symbol: List[List[Any]], direction: str = "SHORT") -> Dict[str, Any]:
    if not MACRO_CORRELATION_ENGINE_ENABLED:
        return {"enabled": False, "decision": "KAPALI", "passed": True, "reason": "Makro motor kapalı"}
    direction = (direction or "SHORT").upper()
    btc_symbol = normalize_symbol(MACRO_SYMBOLS[0] if MACRO_SYMBOLS else "BTC-USDT-SWAP")
    if normalize_symbol(symbol) == btc_symbol:
        return {"enabled": True, "decision": "ANA_COIN", "passed": True, "reason": "Ana makro coin kendisi"}
    btc1 = await get_klines(btc_symbol, "1m", 80)
    btc5 = await get_klines(btc_symbol, "5m", 80)
    if len(btc1) < 30 or len(btc5) < 30 or len(k5_symbol) < 30:
        return {"enabled": True, "decision": "VERI_YOK", "passed": True, "reason": "BTC/makro verisi yetersiz"}
    b1 = closes(btc1); b5 = closes(btc5); s5 = closes(k5_symbol)
    btc_5m = pct_change(b1[-6], b1[-1]) if len(b1) >= 6 else 0.0
    btc_20m = pct_change(b1[-21], b1[-1]) if len(b1) >= 21 else 0.0
    btc_1h = pct_change(b5[-13], b5[-1]) if len(b5) >= 13 else 0.0
    corr = _corr(_series_returns(s5, 35), _series_returns(b5, 35))
    passed = True
    decision = "MAKRO_TEMIZ"
    reasons = [f"BTC 5m/20m/1h %{btc_5m:.2f}/%{btc_20m:.2f}/%{btc_1h:.2f}", f"corr {corr:.2f}"]
    if direction == "LONG" and btc_20m <= -MACRO_BTC_DROP_BLOCK_LONG_PCT and (corr >= MACRO_HIGH_CORR_MIN or MACRO_BLOCK_IF_HIGH_CORR_COUNTER):
        passed = False; decision = "LONG_MAKRO_BLOK"; reasons.append("BTC düşerken altcoin LONG riskli")
    if direction == "SHORT" and btc_20m >= MACRO_BTC_PUMP_BLOCK_SHORT_PCT and (corr >= MACRO_HIGH_CORR_MIN or MACRO_BLOCK_IF_HIGH_CORR_COUNTER):
        passed = False; decision = "SHORT_MAKRO_BLOK"; reasons.append("BTC yükselirken altcoin SHORT riskli")
    if abs(btc_5m) >= MACRO_BTC_FAST_MOVE_5M_PCT:
        reasons.append("BTC hızlı hareket ediyor; slippage/ters iğne riski")
    return {"enabled": True, "passed": passed, "decision": decision, "btc_5m_pct": round(btc_5m, 2), "btc_20m_pct": round(btc_20m, 2), "btc_1h_pct": round(btc_1h, 2), "correlation": round(corr, 2), "reason": " | ".join(reasons)}


def macro_final_gate(payload: Dict[str, Any]) -> Tuple[bool, str]:
    macro = payload.get("macro") if isinstance(payload.get("macro"), dict) else {}
    if not MACRO_CORRELATION_ENGINE_ENABLED or not macro or not macro.get("enabled"):
        return True, "Makro kapısı kapalı/yok"
    return bool(macro.get("passed", True)), str(macro.get("reason", "Makro temiz"))


def format_pro_plus_blocks(res: Dict[str, Any]) -> str:
    parts: List[str] = []
    reg = res.get("market_regime") if isinstance(res.get("market_regime"), dict) else {}
    macro = res.get("macro") if isinstance(res.get("macro"), dict) else {}
    sr = res.get("support_resistance") if isinstance(res.get("support_resistance"), dict) else {}
    pm = res.get("position_plan") if isinstance(res.get("position_plan"), dict) else {}
    if reg:
        parts.append(f"\n🧭 Piyasa Rejimi: {reg.get('regime','-')} | Bias: {reg.get('bias','-')} | {reg.get('reason','-')}")
    if macro:
        parts.append(f"\n🌍 Makro/BTC: {macro.get('decision','-')} | {macro.get('reason','-')}")
    if sr:
        parts.append(
            f"\n🧱 Destek/Direnç: {sr.get('decision','-')} | Destek {fmt_num(sr.get('nearest_support',0))} (%{sr.get('support_distance_pct','-')}) | "
            f"Direnç {fmt_num(sr.get('nearest_resistance',0))} (%{sr.get('resistance_distance_pct','-')}) | {sr.get('reason','-')}"
        )
    if pm:
        parts.append(f"\n🎛️ Pozisyon Planı: {pm.get('summary','-')}")
    return "".join(parts)


def build_position_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    direction = str(payload.get("direction", "SHORT")).upper()
    entry = safe_float(payload.get("price", 0))
    stop = safe_float(payload.get("stop", 0))
    tp1 = safe_float(payload.get("tp1", 0))
    tp2 = safe_float(payload.get("tp2", 0))
    tp3 = safe_float(payload.get("tp3", 0))
    if entry <= 0:
        return {"enabled": False, "summary": "Entry yok"}
    be = entry
    if FOLLOWUP_CLOSE_ALL_AT_TP1:
        summary = (
            f"TP1'de %100 tam kapanış. Stop sabit %{FIXED_STOP_PCT:.2f}. "
            f"TP2/TP3 sadece sinyal kalitesi için takip. "
            f"Stop={fmt_num(stop)} | TP1={fmt_num(tp1)} | TP2={fmt_num(tp2)} | TP3={fmt_num(tp3)}"
        )
        return {"enabled": POSITION_MANAGER_ENABLED, "direction": direction, "break_even_stop": be, "tp1_partial_pct": 100.0, "tp2_partial_pct": 0.0, "trailing_enabled": False, "summary": summary}

    summary = (
        f"TP1 %{POSITION_TP1_PARTIAL_PCT:.0f} kısmi çıkış + stop BE; "
        f"TP2 %{POSITION_TP2_PARTIAL_PCT:.0f} ek çıkış; kalan TP3/trailing. "
        f"BE={fmt_num(be)} | Stop={fmt_num(stop)} | TP1={fmt_num(tp1)} | TP2={fmt_num(tp2)} | TP3={fmt_num(tp3)}"
    )
    return {"enabled": POSITION_MANAGER_ENABLED, "direction": direction, "break_even_stop": be, "tp1_partial_pct": POSITION_TP1_PARTIAL_PCT, "tp2_partial_pct": POSITION_TP2_PARTIAL_PCT, "trailing_enabled": POSITION_TRAILING_ENABLED, "summary": summary}


def position_manager_evaluate(k1: List[List[Any]], rec: Dict[str, Any]) -> Dict[str, Any]:
    direction = str(rec.get("direction", "SHORT")).upper()
    entry = safe_float(rec.get("entry", 0)); stop = safe_float(rec.get("stop", 0))
    tp1 = safe_float(rec.get("tp1", 0)); tp2 = safe_float(rec.get("tp2", 0)); tp3 = safe_float(rec.get("tp3", 0))
    if not k1 or entry <= 0:
        return {"action": "YOK", "reason": "veri yok"}
    last = safe_float(k1[-1][4])
    high = max(highs(k1[-30:])) if len(k1) >= 30 else max(highs(k1))
    low = min(lows(k1[-30:])) if len(k1) >= 30 else min(lows(k1))
    atr_now = max(atr(k1, 14)[-1], entry * 0.001)
    profit_pct = pct_change(entry, last) if direction == "LONG" else pct_change(entry, last) * -1
    pm_sent = rec.setdefault("pm_sent", {})
    if direction == "LONG":
        if last >= tp1 and not pm_sent.get("tp1"):
            return {"action": "TP1", "new_stop": entry if POSITION_MOVE_STOP_BE_AFTER_TP1 else stop, "reason": f"TP1 görüldü; %{POSITION_TP1_PARTIAL_PCT:.0f} kısmi çıkış + stop BE önerisi"}
        if last >= tp2 and not pm_sent.get("tp2"):
            trail = max(entry, last - atr_now * POSITION_TRAIL_ATR_MULT)
            return {"action": "TP2", "new_stop": trail, "reason": f"TP2 görüldü; ek kâr alma + trailing stop {fmt_num(trail)}"}
        if POSITION_TRAILING_ENABLED and profit_pct >= POSITION_TRAIL_AFTER_PROFIT_PCT:
            trail = max(entry, high - atr_now * POSITION_TRAIL_ATR_MULT)
            old_trail = safe_float(rec.get("trailing_stop", 0))
            if trail > old_trail * 1.001:
                return {"action": "TRAIL", "new_stop": trail, "reason": f"LONG kâr %{profit_pct:.2f}; trailing stop {fmt_num(trail)}"}
    else:
        if last <= tp1 and not pm_sent.get("tp1"):
            return {"action": "TP1", "new_stop": entry if POSITION_MOVE_STOP_BE_AFTER_TP1 else stop, "reason": f"TP1 görüldü; %{POSITION_TP1_PARTIAL_PCT:.0f} kısmi çıkış + stop BE önerisi"}
        if last <= tp2 and not pm_sent.get("tp2"):
            trail = min(entry, last + atr_now * POSITION_TRAIL_ATR_MULT)
            return {"action": "TP2", "new_stop": trail, "reason": f"TP2 görüldü; ek kâr alma + trailing stop {fmt_num(trail)}"}
        if POSITION_TRAILING_ENABLED and profit_pct >= POSITION_TRAIL_AFTER_PROFIT_PCT:
            trail = min(entry, low + atr_now * POSITION_TRAIL_ATR_MULT)
            old_trail = safe_float(rec.get("trailing_stop", 999999999))
            if old_trail == 999999999 or trail < old_trail * 0.999:
                return {"action": "TRAIL", "new_stop": trail, "reason": f"SHORT kâr %{profit_pct:.2f}; trailing stop {fmt_num(trail)}"}
    return {"action": "YOK", "reason": f"aktif kâr %{profit_pct:.2f}, yeni PM yok"}


async def position_management_loop() -> None:
    if not POSITION_MANAGER_ENABLED:
        return
    while True:
        try:
            now_ts = time.time()
            for key, rec in list(memory.get("follows", {}).items()):
                if rec.get("done"):
                    continue
                if now_ts - safe_float(rec.get("sent_ts", 0)) < POSITION_PM_MIN_AGE_SEC:
                    continue
                sym = normalize_symbol(str(rec.get("symbol", key)).replace("LONG:", "").replace("SHORT:", ""))
                k1 = await get_klines(sym, "1m", 90)
                action = position_manager_evaluate(k1, rec)
                act = str(action.get("action", "YOK"))
                if act == "YOK":
                    continue
                rec.setdefault("pm_sent", {})[act.lower()] = time.time()
                new_stop = safe_float(action.get("new_stop", 0))
                if new_stop > 0:
                    rec["trailing_stop"] = new_stop
                if POSITION_SEND_PM_ALERTS:
                    text = (
                        f"🎛️ POZİSYON YÖNETİMİ\n"
                        f"⏰ {tr_str()}\n"
                        f"🎯 {sym} | {rec.get('direction','-')}\n"
                        f"Eylem: {act}\n"
                        f"Yeni önerilen stop: {fmt_num(new_stop) if new_stop > 0 else '-'}\n"
                        f"Not: {action.get('reason','-')}\n"
                        f"Uyarı: Bu mod emir göndermez; yönetim uyarısı üretir."
                    )
                    if await safe_send_telegram(text):
                        stats["pm_alert_sent"] = stats.get("pm_alert_sent", 0) + 1
        except Exception as e:
            logger.exception("position_management_loop hata: %s", e)
        await asyncio.sleep(max(30, POSITION_MANAGER_CHECK_INTERVAL_SEC))


def _backtest_make_levels(direction: str, entry: float) -> Tuple[float, float, float, float]:
    if direction == "LONG":
        stop = entry * (1 - BACKTEST_RISK_STOP_PCT/100.0)
        return stop, entry * (1 + BACKTEST_TP1_PCT/100.0), entry * (1 + BACKTEST_TP2_PCT/100.0), entry * (1 + BACKTEST_TP3_PCT/100.0)
    stop = entry * (1 + BACKTEST_RISK_STOP_PCT/100.0)
    return stop, entry * (1 - BACKTEST_TP1_PCT/100.0), entry * (1 - BACKTEST_TP2_PCT/100.0), entry * (1 - BACKTEST_TP3_PCT/100.0)


def run_simple_backtest_on_klines(symbol: str, k1: List[List[Any]], direction: str, bars: int = BACKTEST_DEFAULT_BARS) -> Dict[str, Any]:
    direction = (direction or "SHORT").upper()
    data = k1[-max(80, min(len(k1), bars)):]
    if len(data) < 90:
        return {"ok": False, "reason": "Backtest için mum yetersiz"}
    closes_v = closes(data); highs_v = highs(data); lows_v = lows(data); vols_v = volumes(data)
    rs = rsi(closes_v, 14); e9 = ema(closes_v, 9); e21 = ema(closes_v, 21)
    signals = []
    last_i = -999
    for i in range(55, len(data) - BACKTEST_FORWARD_BARS):
        if i - last_i < BACKTEST_MIN_SIGNAL_GAP_BARS:
            continue
        window_high = max(highs_v[i-50:i]); window_low = min(lows_v[i-50:i]); price = closes_v[i]
        width = max(window_high - window_low, 1e-9)
        pos = (price - window_low) / width
        vol_ratio = vols_v[i] / max(avg(vols_v[i-20:i]), 1e-9)
        trigger = False
        if direction == "SHORT":
            trigger = pos >= 0.70 and price < e9[i] and rs[i] < rs[i-1] and vol_ratio >= 0.55
        else:
            trigger = pos <= 0.35 and price > e9[i] and rs[i] > rs[i-1] and vol_ratio >= 0.45
        if not trigger:
            continue
        entry = price
        stop, tp1, tp2, tp3 = _backtest_make_levels(direction, entry)
        result = evaluate_tp_stop_path(data[i+1:i+1+BACKTEST_FORWARD_BARS], direction, time.time()-999999, entry, stop, tp1, tp2, tp3)
        signals.append({"i": i, "entry": entry, "outcome": result.get("trade_outcome", result.get("outcome")), "potential": result.get("potential_outcome"), "checked": result.get("checked")})
        last_i = i
    total = len(signals); wins = sum(1 for x in signals if str(x.get("outcome", "")).startswith("TP")); stops = sum(1 for x in signals if x.get("outcome") == "STOP")
    tp3 = sum(1 for x in signals if x.get("potential") == "TP3")
    rate = wins / total * 100.0 if total else 0.0
    return {"ok": True, "symbol": symbol, "direction": direction, "signals": total, "wins": wins, "stops": stops, "tp3_potential": tp3, "win_rate": round(rate, 1), "last": signals[-8:]}


async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not BACKTEST_ENGINE_ENABLED:
        await update.message.reply_text("Backtest motoru kapalı.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /backtest LDOUSDT LONG 240")
        return
    sym = normalize_symbol(context.args[0])
    direction = str(context.args[1]).upper() if len(context.args) >= 2 else "SHORT"
    bars = int(safe_float(context.args[2], BACKTEST_DEFAULT_BARS)) if len(context.args) >= 3 else BACKTEST_DEFAULT_BARS
    k1 = await get_klines(sym, "1m", min(300, max(120, bars)))
    res = run_simple_backtest_on_klines(sym, k1, direction, bars)
    stats["backtest_run"] = stats.get("backtest_run", 0) + 1
    if not res.get("ok"):
        await update.message.reply_text(f"Backtest yapılamadı: {res.get('reason')}")
        return
    lines = [
        "🧪 BACKTEST / REPLAY RAPORU",
        f"Coin: {sym} | Yön: {direction} | Mum: {bars}",
        f"Sinyal: {res.get('signals')} | TP: {res.get('wins')} | STOP: {res.get('stops')} | Başarı: %{res.get('win_rate')}",
        f"TP3 potansiyel: {res.get('tp3_potential')}",
        "Not: Bu hızlı replay testidir; canlı emir garantisi değildir."
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_pozisyon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    follows = memory.get("follows", {})
    active = [(k, v) for k, v in follows.items() if isinstance(v, dict) and not v.get("done")]
    if not active:
        await update.message.reply_text("Aktif takip edilen pozisyon yok.")
        return
    lines = ["🎛️ AKTİF POZİSYON YÖNETİMİ"]
    for k, rec in active[:12]:
        lines.append(f"- {rec.get('symbol')} {rec.get('direction')} | entry {fmt_num(rec.get('entry',0))} | stop {fmt_num(rec.get('stop',0))} | trailing {fmt_num(rec.get('trailing_stop',0)) if rec.get('trailing_stop') else '-'}")
    await update.message.reply_text("\n".join(lines))

def enforce_single_short_al_rules(payload: Dict[str, Any]) -> Dict[str, Any]:
    p = copy.deepcopy(payload)
    if p.get("stage") != "SIGNAL":
        return p


    reason_text = str(p.get("reason", ""))
    for gate_name, gate_fn, stat_key in (
        ("Rejim", regime_final_gate, "regime_block"),
        ("Makro", macro_final_gate, "macro_block"),
        ("SR", sr_final_gate, "sr_block"),
    ):
        ok_gate, gate_reason = gate_fn(p)
        if not ok_gate:
            p["stage"] = "READY"
            p["signal_label"] = "İÇ TAKİP"
            p["reason"] = f"{reason_text} | {gate_name} kapısı blok: {gate_reason}"
            stats[stat_key] = stats.get(stat_key, 0) + 1
            return p
        else:
            pass_key = stat_key.replace("block", "pass")
            stats[pass_key] = stats.get(pass_key, 0) + 1
    pump_20m = safe_float(p.get("pump_20m", 0))
    pump_1h = safe_float(p.get("pump_1h", 0))

    whale_eye = p.get("whale_eye", {})
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))

    ma_cross = p.get("ma_cross") if isinstance(p.get("ma_cross"), dict) else {}
    if not (MA_CROSS_ENTRY_ENABLED and ma_cross.get("passed", False)):
        if pump_20m < 0.55 and pump_1h < 1.05 and whale_confidence not in ("ÇOK_YÜKSEK", "YÜKSEK"):
            p["stage"] = "READY"
            p["signal_label"] = "İÇ TAKİP"
            p["reason"] = f"{reason_text} | Pump zayıf, whale teyidi yok"
            stats["weak_signal_reject"] += 1
            return p

    p["signal_label"] = "SHORT AL"
    return p


def enforce_single_long_al_rules(payload: Dict[str, Any]) -> Dict[str, Any]:
    p = copy.deepcopy(payload)
    if p.get("stage") != "SIGNAL":
        return p


    ict = p.get("ict") if isinstance(p.get("ict"), dict) else {}
    reason = str(p.get("reason", ""))
    for gate_name, gate_fn, stat_key in (
        ("Rejim", regime_final_gate, "regime_block"),
        ("Makro", macro_final_gate, "macro_block"),
        ("SR", sr_final_gate, "sr_block"),
    ):
        ok_gate, gate_reason = gate_fn(p)
        if not ok_gate:
            p["stage"] = "READY"
            p["signal_label"] = "İÇ TAKİP"
            p["reason"] = f"{reason} | {gate_name} kapısı blok: {gate_reason}"
            stats[stat_key] = stats.get(stat_key, 0) + 1
            return p
        else:
            pass_key = stat_key.replace("block", "pass")
            stats[pass_key] = stats.get(pass_key, 0) + 1

    if ICT_REQUIRE_PRO_CONTEXT_FOR_SIGNAL and safe_float(ict.get("long_pro_score", 0)) < ICT_LONG_MIN_PRO_SCORE:
        p["stage"] = "READY"; p["signal_label"] = "İÇ TAKİP"
        p["reason"] = f"{reason} | LONG ICT PRO bağlam yetersiz"
        stats["long_quality_block"] += 1
        return p
    if not ict.get("in_discount_zone") and not ict.get("sweep_low"):
        p["stage"] = "READY"; p["signal_label"] = "İÇ TAKİP"
        p["reason"] = f"{reason} | Discount/sweep yok"
        stats["long_quality_block"] += 1
        return p

    flow = p.get("trade_flow") if isinstance(p.get("trade_flow"), dict) else {}
    sell_to_buy = safe_float(flow.get("sell_to_buy", 0))
    true_structure_up = bool(ict.get("bos_up") or ict.get("choch_up") or ict.get("mss_up"))
    if (
        LONG_BEARISH_CONTEXT_HARD_BLOCK_ENABLED
        and str(ict.get("structure_bias", "")).upper() == "BEARISH"
        and not true_structure_up
        and sell_to_buy >= LONG_SELL_TO_BUY_HARD_BLOCK
    ):
        p["stage"] = "READY"; p["signal_label"] = "İÇ TAKİP"
        p["reason"] = f"{reason} | LONG hard block: BEARISH yapı + BOS/CHOCH/MSS↑ yok + satıcı akışı x{sell_to_buy:.2f}"
        stats["long_conflict_block"] += 1
        return p

    p["signal_label"] = "LONG AL"
    return p


# =========================================================
# MESAJ FORMATLARI
# =========================================================

def format_whale_eye_block(res: Dict[str, Any]) -> str:
    whale = res.get("whale_eye") if isinstance(res.get("whale_eye"), dict) else {}
    if not whale or not whale.get("enabled"):
        return ""

    oi = whale.get("oi", {}) if isinstance(whale.get("oi"), dict) else {}
    funding = whale.get("funding", {}) if isinstance(whale.get("funding"), dict) else {}
    spoofing = whale.get("spoofing", {}) if isinstance(whale.get("spoofing"), dict) else {}
    cvd = whale.get("cvd", {}) if isinstance(whale.get("cvd"), dict) else {}

    lines = []

    # V6 WHALE EYE başlığı
    lines.append(f"\n🐋 V6 WHALE EYE - BALİNA İSTİHBARATI")
    lines.append(f"├─ Toplam Skor: {whale.get('total_score', 0)}/30")
    lines.append(f"├─ Güven Seviyesi: {whale.get('whale_confidence', '-')}")
    lines.append(f"├─ Uyumsuzluk Sayısı: {whale.get('divergence_count', 0)}")

    # Open Interest
    if oi.get("enabled"):
        lines.append(f"├─ OI Kaynak: {oi.get('source', '-')}")
    if oi.get("enabled") and oi.get("divergence_type", "NÖTR") != "NÖTR":
        lines.append(f"├─ OI Delta: {oi.get('divergence_type', '-')}")
        if oi.get("oi_change_pct"):
            lines.append(f"│  └─ OI Değişim: %{oi.get('oi_change_pct', 0):.2f} | Fiyat: %{oi.get('price_change_pct', 0):.2f}")
    elif not oi.get("enabled"):
        lines.append(f"├─ OI: VERİ YOK ({str(oi.get('reason', '-'))[:90]})")

    # Funding Rate
    if funding.get("enabled"):
        lines.append(f"├─ Funding Kaynak: {funding.get('source', '-')}")
    if funding.get("enabled") and funding.get("funding_signal", "NÖTR") != "NÖTR":
        lines.append(f"├─ Funding: {funding.get('funding_signal', '-')} (%{funding.get('funding_rate', 0):.4f})")
    elif not funding.get("enabled"):
        lines.append(f"├─ Funding: VERİ YOK ({str(funding.get('reason', '-'))[:90]})")

    # CVD
    if cvd.get("enabled") and cvd.get("divergence", "NÖTR") != "NÖTR":
        lines.append(f"├─ CVD: {cvd.get('divergence', '-')} (CVD: %{cvd.get('cvd_trend_pct', 0):.2f} | Fiyat: %{cvd.get('price_trend_pct', 0):.2f})")

    # Spoofing
    if spoofing.get("enabled") and spoofing.get("spoofing_detected"):
        lines.append(f"├─ Spoofing: {spoofing.get('spoof_type', '-')}")

    # Whale Eye yorumu
    if whale.get("reason", "") and whale.get("reason", "") != "Balina izi tespit edilmedi":
        lines.append(f"└─ Yorum: {whale.get('reason', '')[:200]}")

    return "\n".join(lines)


def format_ict_block(res: Dict[str, Any]) -> str:
    ict = res.get("ict") if isinstance(res.get("ict"), dict) else {}
    if not ict or not ict.get("enabled"):
        return ""
    return (
        f"\n🏛️ ICT PRO\n"
        f"├─ Yapı: {ict.get('structure_bias', '-')}\n"
        f"├─ BOS↑/↓: {ict.get('bos_up')}/{ict.get('bos_down')}\n"
        f"├─ CHOCH↑/↓: {ict.get('choch_up')}/{ict.get('choch_down')}\n"
        f"├─ MSS↑/↓: {ict.get('mss_up')}/{ict.get('mss_down')}\n"
        f"├─ Discount/Premium: {ict.get('in_discount_zone')}/{ict.get('in_premium_zone')}\n"
        f"├─ Sweep Alt/Üst: {ict.get('sweep_low')}/{ict.get('sweep_high')}\n"
        f"├─ SHORT PRO: {ict.get('short_pro_score', 0)}\n"
        f"└─ LONG PRO: {ict.get('long_pro_score', 0)}"
    )


def build_signal_message(res: Dict[str, Any]) -> str:
    if str(res.get("direction", "SHORT")).upper() == "LONG":
        return build_long_signal_message(res)
    signal_label = str(res.get("signal_label", "SHORT AL"))
    confirm_status = str(res.get("binance_confirm_status", "YOK"))
    binance_symbol = str(res.get("binance_symbol", "-"))
    binance_price = safe_float(res.get("binance_price", 0))
    binance_gap = safe_float(res.get("binance_price_gap_pct", 0))

    whale_eye = res.get("whale_eye", {})
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))
    whale_score = safe_float(whale_eye.get("total_score", 0))

    base = (
        f"🚨 {VERSION_NAME} - {signal_label}\n"
        f"⏰ {tr_str()}\n"
        f"🎯 Coin: {res['symbol']}\n"
        f"📊 Skor: {res['score']} | Kalite: {res.get('quality_score', '-')}\n"
        f"🐋 Whale Eye: {whale_confidence} ({whale_score}) | OI/Funding/CVD/Spoof\n"
        f"🟢 Aday: {res['candidate_score']} | 🟡 Hazır: {res['ready_score']} | 🔴 Doğrula: {res['verify_score']}\n"
        f"📈 Pump 10/20/1s: %{res['pump_10m']} / %{res['pump_20m']} / %{res['pump_1h']}\n"
        f"📉 RSI 1/5/15: {res['rsi1']} / {res['rsi5']} / {res['rsi15']}\n"
        f"🎯 Giriş bölgesi: {res.get('entry_location', {}).get('class', '-')} | {str(res.get('entry_location', {}).get('reason', '-'))[:110]}\n"
        f"📍 MA7/MA25: {res.get('ma_cross', {}).get('class', '-')} | {str(res.get('ma_cross', {}).get('reason', '-'))[:110]}\n"
        f"💰 Giriş: {fmt_num(res['price'])}\n"
        f"🛑 Stop: {fmt_num(res['stop'])}\n"
        f"🎯 TP1: {fmt_num(res['tp1'])} | TP2: {fmt_num(res['tp2'])} | TP3: {fmt_num(res['tp3'])}\n"
        f"📐 RR(TP1): {res['rr']}\n"
        f"🔧 Trend Kilit: {res.get('trend_guard_score', '-')} | Kırılım: {res.get('breakdown_score', '-')}\n"
        f"📝 Not: {res['reason'][:400]}\n"
        f"📡 Veri: OKX SWAP | Binance teyit: {confirm_status}"
    )
    return base + format_whale_eye_block(res) + format_ict_block(res) + format_pro_plus_blocks(res)


def build_long_signal_message(res: Dict[str, Any]) -> str:
    whale_eye = res.get("whale_eye", {})
    whale_confidence = str(whale_eye.get("whale_confidence", "DÜŞÜK"))
    whale_score = safe_float(whale_eye.get("total_score", 0))
    gate = res.get("long_close_gate", {}) if isinstance(res.get("long_close_gate"), dict) else {}

    base = (
        f"🚀 {VERSION_NAME} - LONG AL\n"
        f"⏰ {tr_str()}\n"
        f"🎯 Coin: {res['symbol']}\n"
        f"📊 Skor: {res['score']} | Kalite: {res.get('quality_score', '-')}\n"
        f"🐋 Whale Eye: {whale_confidence} ({whale_score}) | OI/Funding/CVD/Spoof\n"
        f"🟢 Aday: {res['candidate_score']} | 🟡 Hazır: {res['ready_score']} | 🔴 Doğrula: {res['verify_score']}\n"
        f"📉 Düşüş 10/20/1s: %{res.get('drop_10m', 0)} / %{res.get('drop_20m', 0)} / %{res.get('drop_1h', 0)}\n"
        f"📈 RSI 1/5/15: {res['rsi1']} / {res['rsi5']} / {res['rsi15']}\n"
        f"🎯 Giriş bölgesi: {res.get('entry_location', {}).get('class', '-')} | {str(res.get('entry_location', {}).get('reason', '-'))[:110]}\n"
        f"📍 MA7/MA25: {res.get('ma_cross', {}).get('class', '-')} | {str(res.get('ma_cross', {}).get('reason', '-'))[:110]}\n"
        f"💰 Giriş: {fmt_num(res['price'])}\n"
        f"🛑 Stop: {fmt_num(res['stop'])}\n"
        f"🎯 TP1: {fmt_num(res['tp1'])} | TP2: {fmt_num(res['tp2'])} | TP3: {fmt_num(res['tp3'])}\n"
        f"📐 RR(TP1): {res['rr']}\n"
        f"📝 Not: {res['reason'][:400]}\n"
        f"📡 Veri: OKX SWAP + ICT LONG"
    )
    return base + format_whale_eye_block(res) + format_ict_block(res) + format_pro_plus_blocks(res)


def build_heartbeat_message() -> str:
    hot_count = len(memory.get("hot", {}))
    trend_watch_count = len(memory.get("trend_watch", {}))
    last_sig = safe_float(memory.get("last_signal_ts", 0))
    last_sig_txt = tr_str(last_sig) if last_sig else "Yok"

    # Günlük sayaç sadece günlük limit içindir.
    today_short = get_today_trade_sent_count("SHORT")
    today_long = get_today_trade_sent_count("LONG")

    # Toplam sayaç kod aktif edildiğinden beri memory içinde kalıcı tutulur.
    ls = normalize_lifetime_stats()
    lifetime_total = int(safe_float(ls.get("total_signals", 0), 0))
    lifetime_short = int(safe_float(ls.get("short_signals", 0), 0))
    lifetime_long = int(safe_float(ls.get("long_signals", 0), 0))
    lifetime_tp = int(safe_float(ls.get("tp_total", 0), 0))
    lifetime_stop = int(safe_float(ls.get("stop_total", 0), 0))
    lifetime_neutral = int(safe_float(ls.get("neutral_total", 0), 0))
    lifetime_closed = lifetime_tp + lifetime_stop
    lifetime_pending = max(0, lifetime_total - lifetime_closed - lifetime_neutral)
    lifetime_winrate = (lifetime_tp / lifetime_closed * 100.0) if lifetime_closed > 0 else 0.0
    lifetime_age = format_duration_from_ts(safe_float(ls.get("activated_ts", 0), 0))

    # Eski anlık follow kayıtları yine bilgi amaçlı kalsın; ama ana başarı toplam memory'den gelir.
    follows = memory.get("follows", {})
    active_follow_tp = sum(1 for r in follows.values() if str(r.get("outcome", "")).startswith("TP"))
    active_follow_stop = sum(1 for r in follows.values() if r.get("outcome") == "STOP")

    return (
        f"💓 {VERSION_NAME} DURUM\n"
        f"⏰ {tr_str()}\n"
        f"📊 Coin: {len(COINS)} | Sıcak: {hot_count} | Trend: {trend_watch_count} | Bloklu: {get_blocked_symbol_count()}\n"
        f"📨 Bugün: SHORT {today_short}/{DAILY_SHORT_TOTAL_LIMIT} | LONG {today_long}/{LONG_DAILY_TOTAL_LIMIT}\n"
        f"📈 Toplam sinyal: {lifetime_total} | SHORT {lifetime_short} | LONG {lifetime_long} | Süre: {lifetime_age}\n"
        f"🎯 Toplam başarı: TP={lifetime_tp} Stop={lifetime_stop} Bekleyen={lifetime_pending} Nötr={lifetime_neutral} | %{lifetime_winrate:.1f}\n"
        f"⭐ TP dağılımı: TP1={ls.get('tp1',0)} | TP2={ls.get('tp2',0)} | TP3={ls.get('tp3',0)}\n"
        f"📌 Aktif takip hafızası: TP={active_follow_tp} | Stop={active_follow_stop}\n"
        f"🐋 Whale Eye: OI={stats['oi_short_diverge']} Fund={stats['funding_short_bonus']} Spoof={stats['spoofing_detected']} CVD={stats['cvd_diverge_short']}\n"
        f"🛡️ Kalite Blok: {stats['quality_gate_block']} | Kırılım Geçen: {stats['trend_breakdown_pass']} | Kapanış Blok: {stats['close_confirm_block']}\n"
        f"🎯 Giriş Bölgesi: erken={stats.get('entry_location_early',0)} | geç blok={stats.get('entry_location_late_block',0)}\n"
        f"📍 MA7/MA25: geçiş={stats.get('ma_cross_pass',0)} | blok={stats.get('ma_cross_block',0)} | 15m yön blok={stats.get('ma_cross_15m_block',0)} | sabit stop={stats.get('fixed_stop_used',0)}\n"
        f"🧠 Hata Hafızası: geçiş={stats.get('mistake_memory_pass',0)} | blok={stats.get('mistake_memory_block',0)} | öğrenme={stats.get('mistake_memory_learn',0)}\n"
        f"🔧 API Fail: {stats['api_fail']} | Telegram Fail: {stats['telegram_fail']} | Analiz: {stats['analyzed']}\n"
        f"📌 Son Sinyal: {last_sig_txt}"
    )


def build_hot_message(res: Dict[str, Any]) -> str:
    return (
        f"🔥 SICAK TAKİP\n"
        f"⏰ {tr_str()}\n"
        f"🎯 Coin: {res['symbol']}\n"
        f"📊 Skor: {res['score']} | Fiyat: {fmt_num(res['price'])}\n"
        f"🐋 Whale Eye: {res.get('whale_eye', {}).get('whale_confidence', '-')}\n"
        f"📝 {res['reason'][:300]}"
    )


def build_ready_message(res: Dict[str, Any]) -> str:
    return (
        f"🟠 İNCE TAKİP\n"
        f"⏰ {tr_str()}\n"
        f"🎯 Coin: {res['symbol']}\n"
        f"📊 Skor: {res['score']} | Fiyat: {fmt_num(res['price'])}\n"
        f"🐋 Whale Eye: {res.get('whale_eye', {}).get('whale_confidence', '-')}\n"
        f"📝 {res['reason'][:300]}"
    )



# =========================================================
# HATA HAFIZASI / KENDİ KENDİNE DÜZELTME
# =========================================================
def mistake_memory_store() -> Dict[str, Any]:
    ensure_memory_shape()
    mm = memory.setdefault("mistake_memory", {"patterns": {}, "coins": {}, "recent": []})
    if not isinstance(mm, dict):
        memory["mistake_memory"] = {"patterns": {}, "coins": {}, "recent": []}
        mm = memory["mistake_memory"]
    mm.setdefault("patterns", {})
    mm.setdefault("coins", {})
    mm.setdefault("recent", [])
    return mm


def _mm_bucket(v: float, cuts: List[float], names: List[str]) -> str:
    try:
        v = float(v)
    except Exception:
        return "NA"
    for i, cut in enumerate(cuts):
        if v < cut:
            return names[i]
    return names[-1]


def mistake_signal_features(payload: Dict[str, Any]) -> Dict[str, Any]:
    direction = str(payload.get("direction", "SHORT")).upper()
    symbol = normalize_symbol(str(payload.get("symbol", "")))
    base = coin_base_from_symbol(symbol)
    ict = payload.get("ict") if isinstance(payload.get("ict"), dict) else {}
    whale = payload.get("whale_eye") if isinstance(payload.get("whale_eye"), dict) else {}
    sr = payload.get("support_resistance") if isinstance(payload.get("support_resistance"), dict) else {}
    reg = payload.get("market_regime") if isinstance(payload.get("market_regime"), dict) else {}
    gate = payload.get("long_close_gate") if direction == "LONG" else payload.get("close_confirm_gate")
    gate = gate if isinstance(gate, dict) else {}
    short_ict = safe_float(ict.get("short_pro_score", 0))
    long_ict = safe_float(ict.get("long_pro_score", 0))
    edge = (long_ict - short_ict) if direction == "LONG" else (short_ict - long_ict)
    sr_dist = safe_float(sr.get("support_distance_pct" if direction == "LONG" else "resistance_distance_pct", 999))
    return {
        "symbol": symbol,
        "base": base,
        "direction": direction,
        "close_class": str(gate.get("class", "-")),
        "score15": round(safe_float(gate.get("score15", 0)), 2),
        "ict_edge_bucket": _mm_bucket(edge, [-2, 0, 1.5, 3.0, 999], ["TERS", "ZAYIF", "NORMAL", "IYI", "COK_IYI"]),
        "regime": str(reg.get("regime", "-")),
        "sr_decision": str(sr.get("decision", "-")),
        "sr_dist_bucket": _mm_bucket(sr_dist, [0.25, 0.55, 0.90, 999], ["COK_YAKIN", "YAKIN", "ORTA", "UZAK"]),
        "vol_bucket": _mm_bucket(max(safe_float(payload.get("vol_ratio_1m", 0)), safe_float(payload.get("vol_ratio_5m", 0))), [0.35, 0.75, 1.20, 2.50, 999], ["OLU", "ZAYIF", "NORMAL", "YUKSEK", "ASIRI"]),
        "whale_bucket": _mm_bucket(safe_float(whale.get("total_score", 0)), [1, 3, 6, 10, 999], ["YOK", "DUSUK", "ORTA", "YUKSEK", "COK_YUKSEK"]),
        "break_bucket": _mm_bucket(safe_float(payload.get("breakdown_score", 0)), [3, 6, 9, 13, 999], ["YOK", "ZAYIF", "ORTA", "GUCLU", "COK_GUCLU"]),
        "quality_bucket": _mm_bucket(safe_float(payload.get("quality_score", 0)), [5.5, 6.5, 7.5, 999], ["DUSUK", "ORTA", "IYI", "COK_IYI"]),
    }


def mistake_pattern_keys(features: Dict[str, Any]) -> List[str]:
    d = features.get("direction", "-")
    return [
        f"DIR={d}|COIN={features.get('base')}",
        f"DIR={d}|REG={features.get('regime')}|SR={features.get('sr_decision')}",
        f"DIR={d}|CLOSE={features.get('close_class')}|S15={features.get('score15')}|ICTEDGE={features.get('ict_edge_bucket')}",
        f"DIR={d}|VOL={features.get('vol_bucket')}|WHALE={features.get('whale_bucket')}|BREAK={features.get('break_bucket')}",
        f"DIR={d}|SRDIST={features.get('sr_dist_bucket')}|QUALITY={features.get('quality_bucket')}",
    ]


def _mistake_summary(rec: Dict[str, Any]) -> Tuple[int, float, float]:
    total = int(safe_float(rec.get("total", 0)))
    if total <= 0:
        return 0, 0.0, 0.0
    stops = safe_float(rec.get("STOP", 0))
    wins = safe_float(rec.get("TP1", 0)) + safe_float(rec.get("TP2", 0)) + safe_float(rec.get("TP3", 0))
    return total, stops / total, wins / total


def mistake_memory_gate(payload: Dict[str, Any]) -> Tuple[bool, str, float]:
    if not MISTAKE_MEMORY_ENABLED:
        return True, "Hata hafızası kapalı.", 0.0
    f = mistake_signal_features(payload)
    mm = mistake_memory_store()
    risk = 0.0
    notes: List[str] = []
    for key in mistake_pattern_keys(f):
        total, stop_rate, win_rate = _mistake_summary(mm.get("patterns", {}).get(key, {}))
        if total >= MISTAKE_MIN_PATTERN_SAMPLES and stop_rate >= MISTAKE_PATTERN_STOP_RATE_BLOCK and win_rate < 0.50:
            risk += 1.25
            notes.append(f"benzer pattern stop oranı %{stop_rate*100:.0f} ({key[:70]})")
    total, stop_rate, win_rate = _mistake_summary(mm.get("coins", {}).get(str(f.get("base", "")), {}))
    if total >= MISTAKE_MIN_COIN_SAMPLES and stop_rate >= MISTAKE_COIN_STOP_RATE_BLOCK:
        risk += 1.50
        notes.append(f"{f.get('base')} stop oranı yüksek %{stop_rate*100:.0f}")
    recent = list(mm.get("recent", []))[-MISTAKE_RECENT_WINDOW:]
    same_stops = [x for x in recent if isinstance(x, dict) and x.get("base") == f.get("base") and x.get("direction") == f.get("direction") and x.get("outcome") == "STOP"]
    if len(same_stops) >= MISTAKE_MAX_RECENT_STOPS:
        risk += 1.30
        notes.append(f"aynı coin/yön son dönemde {len(same_stops)} stop")
    if risk >= MISTAKE_MEMORY_BLOCK_SCORE:
        return False, "HATA HAFIZASI BLOK: " + " | ".join(notes[:5]), round(risk, 2)
    return True, "Hata hafızası temiz" + ((": " + " | ".join(notes[:3])) if notes else ""), round(risk, 2)


def mistake_store_signal_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    f = mistake_signal_features(payload)
    return {"created_ts": time.time(), "features": f, "keys": mistake_pattern_keys(f), "signal_reason": str(payload.get("reason", ""))[:900]}


def _mistake_update(bucket: Dict[str, Any], outcome: str, symbol: str) -> None:
    outcome = str(outcome or "NÖTR").upper()
    if outcome not in ("TP1", "TP2", "TP3", "STOP", "NÖTR"):
        outcome = "NÖTR"
    bucket["total"] = int(safe_float(bucket.get("total", 0))) + 1
    bucket[outcome] = int(safe_float(bucket.get(outcome, 0))) + 1
    bucket["last_symbol"] = symbol
    bucket["last_outcome"] = outcome
    bucket["last_ts"] = time.time()


def mistake_stop_reason(rec: Dict[str, Any]) -> str:
    snap = rec.get("mistake_snapshot", {}) if isinstance(rec.get("mistake_snapshot"), dict) else {}
    f = snap.get("features", {}) if isinstance(snap.get("features"), dict) else {}
    if safe_float(f.get("score15", 0)) < 0.5:
        return "15m onayı zayıf"
    if str(f.get("close_class", "")) != "CLEAN":
        return "kapanış CLEAN değil"
    if f.get("ict_edge_bucket") in ("TERS", "ZAYIF"):
        return "ICT yön üstünlüğü zayıf"
    if f.get("sr_dist_bucket") in ("ORTA", "UZAK"):
        return "destek/direnç bölgesinden uzak"
    if f.get("vol_bucket") in ("OLU", "ZAYIF"):
        return "hacim zayıf"
    if str(f.get("regime", "")).upper() in ("RANGE", "KARISIK"):
        return "range/karışık rejim"
    return "stop önce geldi"


def mistake_learn_from_followup(rec: Dict[str, Any], outcome: str) -> None:
    if not MISTAKE_MEMORY_ENABLED:
        return
    snap = rec.get("mistake_snapshot") if isinstance(rec.get("mistake_snapshot"), dict) else {}
    f = snap.get("features", {}) if isinstance(snap.get("features"), dict) else {}
    if not f:
        return
    outcome = str(outcome or "NÖTR").upper()
    if outcome not in ("TP1", "TP2", "TP3", "STOP", "NÖTR"):
        outcome = "NÖTR"
    mm = mistake_memory_store()
    for key in snap.get("keys", mistake_pattern_keys(f)):
        _mistake_update(mm.setdefault("patterns", {}).setdefault(str(key), {}), outcome, str(f.get("symbol", "")))
    _mistake_update(mm.setdefault("coins", {}).setdefault(str(f.get("base", "")), {}), outcome, str(f.get("symbol", "")))
    recent = mm.setdefault("recent", [])
    recent.append({"ts": time.time(), "symbol": f.get("symbol"), "base": f.get("base"), "direction": f.get("direction"), "outcome": outcome, "stop_reason": mistake_stop_reason(rec) if outcome == "STOP" else "-"})
    if len(recent) > max(50, MISTAKE_RECENT_WINDOW * 4):
        del recent[:-max(50, MISTAKE_RECENT_WINDOW * 4)]
    stats["mistake_memory_learn"] += 1


def build_mistake_memory_status_message() -> str:
    mm = mistake_memory_store()
    bad = []
    for key, rec in mm.get("patterns", {}).items():
        total, stop_rate, win_rate = _mistake_summary(rec)
        if total >= MISTAKE_MIN_PATTERN_SAMPLES and stop_rate >= MISTAKE_PATTERN_STOP_RATE_BLOCK:
            bad.append((stop_rate, total, key))
    bad.sort(reverse=True)
    lines = [
        "🧠 HATA HAFIZASI DURUM",
        f"Aktif: {'EVET' if MISTAKE_MEMORY_ENABLED else 'HAYIR'}",
        f"Pattern: {len(mm.get('patterns',{}))} | Coin: {len(mm.get('coins',{}))} | Son kayıt: {len(mm.get('recent',[]))}",
        f"Geçiş/blok/öğrenme: {stats.get('mistake_memory_pass',0)} / {stats.get('mistake_memory_block',0)} / {stats.get('mistake_memory_learn',0)}",
        "Kötüleşen patternler:",
    ]
    if bad:
        for stop_rate, total, key in bad[:8]:
            lines.append(f"- stop %{stop_rate*100:.0f} / {total} örnek | {key[:110]}")
    else:
        lines.append("- Henüz güvenilir kötü pattern yok.")
    recent = list(mm.get("recent", []))[-5:]
    if recent:
        lines.append("Son sonuçlar:")
        for r in recent:
            lines.append(f"- {r.get('symbol')} {r.get('direction')} -> {r.get('outcome')} | {r.get('stop_reason','-')}")
    return "\n".join(lines[:40])

# =========================================================
# SİNYAL İŞLEME
# =========================================================
def signal_key(symbol: str, stage: str) -> str:
    return f"{symbol}:{stage}"


def get_signal_record(symbol: str, stage: str) -> Dict[str, Any]:
    return memory.get("signals", {}).get(signal_key(symbol, stage), {})


def better_than_previous(symbol: str, stage: str, payload: Dict[str, Any]) -> bool:
    prev = get_signal_record(symbol, stage)
    prev_score = safe_float(prev.get("score", 0))
    cur_score = safe_float(payload.get("score", 0))
    return cur_score >= prev_score + SCORE_OVERRIDE_GAP


def daily_trade_already_sent(symbol: str, direction: str) -> bool:
    direction = (direction or "SHORT").upper()
    if direction == "LONG":
        return bool(memory.get("daily_long_sent", {}).get(tr_day_key(), {}).get(symbol, {}))
    return bool(memory.get("daily_short_sent", {}).get(tr_day_key(), {}).get(symbol, {}))


def set_daily_trade_sent(symbol: str, payload: Dict[str, Any]) -> None:
    direction = str(payload.get("direction", "SHORT")).upper()
    day_key = tr_day_key()
    if direction == "LONG":
        memory.setdefault("daily_long_sent", {}).setdefault(day_key, {})[symbol] = {"ts": time.time(), "price": payload.get("price")}
    else:
        memory.setdefault("daily_short_sent", {}).setdefault(day_key, {})[symbol] = {"ts": time.time(), "price": payload.get("price")}


def get_today_trade_sent_count(direction: str) -> int:
    direction = (direction or "SHORT").upper()
    if direction == "LONG":
        return len(memory.get("daily_long_sent", {}).get(tr_day_key(), {}))
    return len(memory.get("daily_short_sent", {}).get(tr_day_key(), {}))


def get_daily_trade_limit(direction: str) -> int:
    return LONG_DAILY_TOTAL_LIMIT if (direction or "SHORT").upper() == "LONG" else DAILY_SHORT_TOTAL_LIMIT


def update_hot_memory(res: Dict[str, Any]) -> None:
    res = copy.deepcopy(res)
    sym = res["symbol"]
    hot = memory.setdefault("hot", {})
    rec = hot.get(sym, {})
    hot[sym] = {
        "first_seen": rec.get("first_seen", time.time()),
        "last_seen": time.time(),
        "first_price": safe_float(rec.get("first_price", 0)) or safe_float(res.get("price", 0)),
        "last_price": res.get("price"),
        "score": max(safe_float(rec.get("score", 0)), safe_float(res.get("score", 0))),
        "whale_confidence": res.get("whale_eye", {}).get("whale_confidence", rec.get("whale_confidence", "-")),
        "reason": res.get("reason", ""),
        "updates": int(safe_float(rec.get("updates", 0))) + 1,
    }


async def confirm_signal_on_binance(res: Dict[str, Any]) -> Dict[str, Any]:
    if not BINANCE_CONFIRM_ENABLED:
        return {"status": "DISABLED", "score": 0.0, "price_gap_pct": 0.0, "binance_symbol": normalize_binance_symbol(res["symbol"]), "binance_price": 0.0, "reason": "Binance teyidi kapalı."}

    symbol = normalize_binance_symbol(res["symbol"])
    k1 = await get_binance_klines(symbol, "1m", 80)
    k5 = await get_binance_klines(symbol, "5m", 80)
    if len(k1) < 30 or len(k5) < 30:
        return {"status": "UNAVAILABLE", "score": 0.0, "price_gap_pct": 0.0, "binance_symbol": symbol, "binance_price": 0.0, "reason": "Binance teyit verisi yok."}

    c1 = closes(k1); c5 = closes(k5); h1 = highs(k1); l1 = lows(k1)
    ema9_1 = ema(c1, 9); ema21_1 = ema(c1, 21)
    rsi1 = rsi(c1, 14); rsi5 = rsi(c5, 14)

    last_price = c1[-1]; prev_price = c1[-2]
    okx_price = safe_float(res.get("price", 0))
    price_gap_pct = abs(pct_change(okx_price, last_price)) if okx_price > 0 and last_price > 0 else 0.0

    last_kline = k1[-1]
    weak_close = last_price <= safe_float(last_kline[3]) or last_price < safe_float(last_kline[1])
    bear_cross = ema9_1[-1] < ema21_1[-1] and ema9_1[-2] >= ema21_1[-2]
    micro_bear = last_price < prev_price and last_price < ema9_1[-1]
    last_rsi1 = rsi1[-1]; last_rsi5 = rsi5[-1]

    score = 0.0
    reasons: List[str] = []

    if price_gap_pct <= MAX_BINANCE_OKX_PRICE_GAP_PCT:
        score += 6.0; reasons.append(f"Fiyat farkı iyi %{price_gap_pct:.2f}")
    elif price_gap_pct <= HARD_BINANCE_OKX_PRICE_GAP_PCT:
        score -= 2.0; reasons.append(f"Fiyat farkı orta %{price_gap_pct:.2f}")
    else:
        score -= 16.0; reasons.append(f"Fiyat farkı yüksek %{price_gap_pct:.2f}")

    if micro_bear: score += 4.0; reasons.append("1dk zayıflıyor")
    if bear_cross: score += 5.0; reasons.append("EMA9/21 aşağı")
    if last_price < ema9_1[-1]: score += 4.0; reasons.append("EMA9 altı")
    if last_rsi1 < 50: score += 4.0; reasons.append("RSI1 gevşek")
    if weak_close: score += 4.0; reasons.append("Zayıf kapanış")
    if c5[-1] < c5[-2] and c5[-1] < c5[-3]: score += 4.0; reasons.append("5dk gevşeme")
    if last_rsi5 < 50: score += 2.0; reasons.append("RSI5 gevşek")

    if price_gap_pct > HARD_BINANCE_OKX_PRICE_GAP_PCT:
        status = "HARD_FAIL"
    elif score >= BINANCE_CONFIRM_SCORE_PASS:
        status = "PASS"
    elif score >= BINANCE_CONFIRM_SCORE_SOFT:
        status = "SOFT_PASS"
    else:
        status = "FAIL"

    return {"status": status, "score": round(score, 2), "price_gap_pct": round(price_gap_pct, 2), "binance_symbol": symbol, "binance_price": last_price, "reason": " | ".join(reasons[:8]) if reasons else "Binance teyit nedeni yok."}




# =========================================================
# RAILWAY RUNTIME FIX — EKSİK ARKA PLAN DÖNGÜLERİ
# =========================================================
# Bu blok V6.2 profesyonel runtime dosyasında post_init içinde çağrılan
# hot_scan_loop / deep_scan_loop / heartbeat_loop / followup_loop / save_loop
# fonksiyonlarının eksik kalması nedeniyle eklendi.
# Amaç: Railway'deki NameError çökmesini düzeltmek ve ana sinyal motorlarını çalıştırmak.


def has_active_trade() -> bool:
    if not ONE_ACTIVE_TRADE_MODE or ACTIVE_TRADE_BLOCK_SEC <= 0:
        return False
    now_ts = time.time()
    for rec in memory.get("follows", {}).values():
        if not isinstance(rec, dict) or rec.get("done"):
            continue
        sent_ts = safe_float(rec.get("sent_ts", rec.get("created_ts", 0)))
        if sent_ts and now_ts - sent_ts < ACTIVE_TRADE_BLOCK_SEC:
            return True
    return False


def global_signal_gap_active() -> bool:
    last_sig = safe_float(memory.get("last_signal_attempt_ts", 0)) or safe_float(memory.get("last_signal_ts", 0))
    if not last_sig:
        return False
    gap = INTERNAL_SIGNAL_SPACING_SEC if SIGNAL_SPACING_SEC <= 0 else max(float(SIGNAL_SPACING_SEC), INTERNAL_SIGNAL_SPACING_SEC)
    return time.time() - last_sig < gap


def should_block_signal(symbol: str, stage: str, payload: Dict[str, Any]) -> bool:
    direction = str(payload.get("direction", "SHORT")).upper()
    if stage == "SIGNAL" and daily_trade_already_sent(symbol, direction):
        return True

    mem_symbol = f"{direction}:{normalize_symbol(symbol)}"
    now_ts = time.time()

    sig_rec = get_signal_record(mem_symbol, stage)
    sig_ts = safe_float(sig_rec.get("ts", 0))
    if sig_ts and now_ts - sig_ts < ALERT_COOLDOWN_MIN * 60:
        if better_than_previous(mem_symbol, stage, payload):
            stats["cooldown_override"] += 1
            return False
        return True

    setup_rec = memory.get("signals", {}).get(f"setup:{mem_symbol}", {})
    setup_ts = safe_float(setup_rec.get("ts", 0))
    if setup_ts and now_ts - setup_ts < SETUP_COOLDOWN_MIN * 60:
        if better_than_previous(mem_symbol, stage, payload):
            stats["cooldown_override"] += 1
            return False
        return True

    return False


def set_signal_memory(symbol: str, stage: str, payload: Dict[str, Any]) -> None:
    direction = str(payload.get("direction", "SHORT")).upper()
    sym = normalize_symbol(symbol)
    mem_symbol = f"{direction}:{sym}"
    memory.setdefault("signals", {})[signal_key(mem_symbol, stage)] = {
        "ts": time.time(),
        "stage": stage,
        "direction": direction,
        "price": payload.get("price"),
        "score": payload.get("score"),
    }
    memory.setdefault("signals", {})[f"setup:{mem_symbol}"] = {
        "ts": time.time(),
        "stage": stage,
        "direction": direction,
        "price": payload.get("price"),
        "score": payload.get("score"),
    }
    if stage == "SIGNAL":
        set_daily_trade_sent(sym, payload)
        record_lifetime_signal_sent(sym, payload)
        memory["last_signal_ts"] = time.time()


def signal_rank_score(res: Dict[str, Any]) -> float:
    whale = res.get("whale_eye") if isinstance(res.get("whale_eye"), dict) else {}
    ict = res.get("ict") if isinstance(res.get("ict"), dict) else {}
    direction = str(res.get("direction", "SHORT")).upper()
    ict_edge = 0.0
    if ict.get("enabled"):
        if direction == "LONG":
            ict_edge = safe_float(ict.get("long_pro_score", 0)) - safe_float(ict.get("short_pro_score", 0))
        else:
            ict_edge = safe_float(ict.get("short_pro_score", 0)) - safe_float(ict.get("long_pro_score", 0))
    return (
        safe_float(res.get("score", 0))
        + safe_float(res.get("quality_score", 0)) * 2.0
        + safe_float(res.get("breakdown_score", 0)) * 1.4
        + safe_float(res.get("rr", 0)) * 2.0
        + safe_float(whale.get("total_score", 0)) * 1.3
        + ict_edge * 1.8
    )


def select_best_signals(signals: List[Dict[str, Any]], limit: int = MAX_SIGNAL_PER_SCAN) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not signals:
        return [], []
    ordered = sorted(signals, key=signal_rank_score, reverse=True)
    effective_limit = max(1, int(limit))
    if not ONE_ACTIVE_TRADE_MODE and SIGNAL_SPACING_SEC <= 0:
        effective_limit = 1
    return ordered[:effective_limit], ordered[effective_limit:]


async def maybe_send_signal(res: Dict[str, Any]) -> None:
    symbol = normalize_symbol(str(res.get("symbol", "")))
    if not symbol:
        return
    direction = str(res.get("direction", "SHORT")).upper()
    expected_label = "LONG AL" if direction == "LONG" else "SHORT AL"

    if res.get("stage") != "SIGNAL":
        if res.get("stage") in ("READY", "HOT"):
            remember_why_blocked(res, str(res.get("why_blocker") or res.get("stage")), res.get("why_actual"), res.get("why_required"), res.get("why_note") or res.get("reason", ""))
            update_hot_memory(res)
        return

    # Dışarı riskli/çelişkili etiket gitmesin.
    res = copy.deepcopy(res)
    res["symbol"] = symbol
    if direction == "LONG":
        res["signal_label"] = "LONG AL"
        res["data_engine"] = "OKX SWAP + ICT LONG"
        res["binance_confirm_status"] = "NOT_USED"
        res["binance_symbol"] = normalize_binance_symbol(symbol)
        res["binance_price"] = 0
        res["binance_price_gap_pct"] = 0
        res["binance_confirm_reason"] = "LONG motoru OKX/ICT/Whale Eye ile çalışır; short Binance teyidi kullanılmadı."
    else:
        res["signal_label"] = "SHORT AL"
        confirm = await confirm_signal_on_binance(res)
        res["data_engine"] = "OKX SWAP"
        res["binance_confirm_status"] = confirm.get("status", "YOK")
        res["binance_confirm_score"] = confirm.get("score", 0)
        res["binance_symbol"] = confirm.get("binance_symbol", normalize_binance_symbol(symbol))
        res["binance_price"] = confirm.get("binance_price", 0)
        res["binance_price_gap_pct"] = confirm.get("price_gap_pct", 0)
        res["binance_confirm_reason"] = confirm.get("reason", "-")

        status = str(confirm.get("status", "YOK"))
        if status == "PASS":
            stats["binance_confirm_pass"] += 1
        elif status == "SOFT_PASS":
            stats["binance_confirm_soft"] += 1
        elif status == "UNAVAILABLE":
            stats["binance_confirm_unavailable"] += 1
            if BINANCE_CONFIRM_REQUIRED:
                update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Binance teyidi yok, takipte."})
                return
        elif status in ("FAIL", "HARD_FAIL"):
            stats["binance_confirm_fail"] += 1
            if BINANCE_CONFIRM_REQUIRED or status == "HARD_FAIL":
                stats["signal_downgraded_by_binance"] += 1
                update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Binance teyidi zayıf: {confirm.get('reason', '-')}"})
                return

    mm_ok, mm_reason, mm_score = mistake_memory_gate(res)
    res["mistake_memory_reason"] = mm_reason
    res["mistake_memory_score"] = mm_score
    if not mm_ok:
        stats["mistake_memory_block"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | {mm_reason}"})
        logger.info("HATA HAFIZASI BLOK %s %s: %s", direction, symbol, mm_reason)
        return
    stats["mistake_memory_pass"] += 1

    if daily_trade_already_sent(symbol, direction):
        stats["daily_short_block"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Aynı coin bugün zaten {expected_label} aldı."})
        return

    if get_today_trade_sent_count(direction) >= get_daily_trade_limit(direction):
        stats["daily_total_block"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Günlük {direction} üst sınırı doldu."})
        return

    if has_active_trade():
        stats["active_trade_block"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Aktif işlem varken yeni AL basılmadı."})
        return

    if global_signal_gap_active():
        stats["global_gap_block"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Aynı anda çoklu sinyal engeli."})
        return

    if should_block_signal(symbol, "SIGNAL", res):
        stats["cooldown_reject"] += 1
        update_hot_memory({**res, "stage": "READY", "reason": f"{res.get('reason', '')} | Cooldown nedeniyle sessiz takip."})
        return

    memory["last_signal_attempt_ts"] = time.time()
    ok = await safe_send_telegram(build_signal_message(res))
    if ok:
        stats["signal_sent"] += 1
        if direction == "LONG":
            stats["long_signal_sent"] += 1
        set_signal_memory(symbol, "SIGNAL", res)
        memory.setdefault("follows", {})[f"{direction}:{symbol}"] = {
            "created_ts": time.time(),
            "sent_ts": time.time(),
            "symbol": symbol,
            "direction": direction,
            "entry": res.get("price"),
            "stop": res.get("stop"),
            "tp1": res.get("tp1"),
            "tp2": res.get("tp2"),
            "tp3": res.get("tp3"),
            "mistake_snapshot": mistake_store_signal_snapshot(res),
            "done": False,
        }
        memory.get("hot", {}).pop(symbol, None)
        memory.get("trend_watch", {}).pop(symbol, None)


def get_hot_symbols(limit: int = MAX_HOT_CANDIDATES) -> List[str]:
    merged: Dict[str, Dict[str, Any]] = {}
    for sym, rec in memory.get("hot", {}).items():
        merged[sym] = rec if isinstance(rec, dict) else {}
    for sym, rec in memory.get("trend_watch", {}).items():
        if not isinstance(rec, dict):
            continue
        old = merged.get(sym, {})
        if safe_float(rec.get("score", 0)) > safe_float(old.get("score", 0)):
            merged[sym] = rec
    items = sorted(merged.items(), key=lambda x: safe_float(x[1].get("score", 0)), reverse=True)
    return [normalize_symbol(k) for k, _ in items if not is_blocked_coin_symbol(k)][:limit]


def pick_general_symbols(batch_size: int = MAX_DEEP_ANALYSIS_PER_CYCLE) -> List[str]:
    global deep_pointer
    if not COINS:
        return []
    out: List[str] = []
    n = len(COINS)
    for _ in range(min(batch_size, n)):
        out.append(normalize_symbol(COINS[deep_pointer % n]))
        deep_pointer += 1
    return out


async def analyze_separate_engines(symbol: str, tickers24: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    short_res = await analyze_symbol(symbol, tickers24)
    long_res = await analyze_long_symbol(symbol, tickers24) if LONG_ENGINE_ENABLED else None
    for res in (short_res, long_res):
        if res:
            results.append(res)
    signal_dirs = {str(r.get("direction", "SHORT")).upper() for r in results if r.get("stage") == "SIGNAL"}
    if "SHORT" in signal_dirs and "LONG" in signal_dirs:
        stats["long_conflict_block"] += 1
        fixed: List[Dict[str, Any]] = []
        for r in results:
            rr = copy.deepcopy(r)
            rr["stage"] = "READY"
            rr["signal_label"] = "İÇ TAKİP"
            rr["reason"] = f"{rr.get('reason', '')} | LONG/SHORT motorları çakıştı; dış sinyal yok."
            fixed.append(rr)
        return fixed
    return results


async def hot_scan_loop() -> None:
    while True:
        try:
            cleanup_memory()
            tickers24 = await get_24h_tickers()
            hot_syms = get_hot_symbols(MAX_HOT_CANDIDATES)
            signal_candidates: List[Dict[str, Any]] = []
            for sym in hot_syms:
                engine_results = await analyze_separate_engines(sym, tickers24)
                if not engine_results:
                    continue
                stats["analyzed"] += 1
                for res in engine_results:
                    if res.get("stage") == "SIGNAL":
                        signal_candidates.append(res)
                    elif res.get("stage") in ("READY", "HOT"):
                        remember_why_blocked(res, str(res.get("why_blocker") or res.get("stage") or "READY/HOT"), res.get("why_actual"), res.get("why_required"), res.get("why_note") or res.get("reason", ""))
                        update_hot_memory(res)
                    else:
                        remember_why_blocked(res, str(res.get("why_blocker") or res.get("stage") or "IGNORE"), res.get("why_actual"), res.get("why_required"), res.get("why_note") or res.get("reason", ""))
                        stats["rejected"] += 1
            chosen, suppressed = select_best_signals(signal_candidates, MAX_SIGNAL_PER_SCAN)
            for res in suppressed:
                stats["scan_signal_suppressed"] += 1
                update_hot_memory({**copy.deepcopy(res), "stage": "READY", "reason": f"{res.get('reason', '')} | Aynı taramada daha güçlü aday seçildi."})
            for res in chosen:
                await maybe_send_signal(res)
        except Exception as e:
            logger.exception("hot_scan_loop hata: %s", e)
        await asyncio.sleep(max(0.5, HOT_SCAN_INTERVAL_SEC))


async def deep_scan_loop() -> None:
    while True:
        try:
            cleanup_memory()
            tickers24 = await get_24h_tickers()
            batch = pick_general_symbols(MAX_DEEP_ANALYSIS_PER_CYCLE)
            signal_candidates: List[Dict[str, Any]] = []
            for sym in batch:
                engine_results = await analyze_separate_engines(sym, tickers24)
                if not engine_results:
                    continue
                stats["analyzed"] += 1
                for res in engine_results:
                    if res.get("stage") == "SIGNAL":
                        signal_candidates.append(res)
                    elif res.get("stage") in ("READY", "HOT"):
                        remember_why_blocked(res, str(res.get("why_blocker") or res.get("stage") or "READY/HOT"), res.get("why_actual"), res.get("why_required"), res.get("why_note") or res.get("reason", ""))
                        update_hot_memory(res)
                    else:
                        remember_why_blocked(res, str(res.get("why_blocker") or res.get("stage") or "IGNORE"), res.get("why_actual"), res.get("why_required"), res.get("why_note") or res.get("reason", ""))
                        stats["rejected"] += 1
            chosen, suppressed = select_best_signals(signal_candidates, MAX_SIGNAL_PER_SCAN)
            for res in suppressed:
                stats["scan_signal_suppressed"] += 1
                update_hot_memory({**copy.deepcopy(res), "stage": "READY", "reason": f"{res.get('reason', '')} | Aynı taramada daha güçlü aday seçildi."})
            for res in chosen:
                await maybe_send_signal(res)
        except Exception as e:
            logger.exception("deep_scan_loop hata: %s", e)
        await asyncio.sleep(max(1.0, DEEP_SCAN_INTERVAL_SEC))


async def heartbeat_loop() -> None:
    if not AUTO_HEARTBEAT:
        return
    while True:
        try:
            await safe_send_telegram(build_heartbeat_message())
        except Exception as e:
            logger.exception("heartbeat_loop hata: %s", e)
        await asyncio.sleep(max(60, HEARTBEAT_INTERVAL_SEC))


def _followup_candle_hit(direction: str, kline: List[Any], stop: float, tp1: float, tp2: float, tp3: float) -> Dict[str, Any]:
    high = safe_float(kline[2])
    low = safe_float(kline[3])
    direction = (direction or "SHORT").upper()
    if direction == "LONG":
        stop_hit = low <= stop if stop > 0 else False
        if high >= tp3 > 0:
            return {"stop_hit": stop_hit, "tp_level": "TP3", "tp_price": tp3}
        if high >= tp2 > 0:
            return {"stop_hit": stop_hit, "tp_level": "TP2", "tp_price": tp2}
        if high >= tp1 > 0:
            return {"stop_hit": stop_hit, "tp_level": "TP1", "tp_price": tp1}
        return {"stop_hit": stop_hit, "tp_level": "", "tp_price": 0.0}
    stop_hit = high >= stop if stop > 0 else False
    if 0 < tp3 and low <= tp3:
        return {"stop_hit": stop_hit, "tp_level": "TP3", "tp_price": tp3}
    if 0 < tp2 and low <= tp2:
        return {"stop_hit": stop_hit, "tp_level": "TP2", "tp_price": tp2}
    if 0 < tp1 and low <= tp1:
        return {"stop_hit": stop_hit, "tp_level": "TP1", "tp_price": tp1}
    return {"stop_hit": stop_hit, "tp_level": "", "tp_price": 0.0}


async def check_followups() -> None:
    follows = memory.get("follows", {})
    if not follows:
        return
    now_ts = time.time()
    for key, rec in list(follows.items()):
        if not isinstance(rec, dict) or rec.get("done"):
            continue
        sent_ts = safe_float(rec.get("sent_ts", rec.get("created_ts", 0)))
        if now_ts - sent_ts < FOLLOWUP_DELAY_SEC:
            continue
        sym = normalize_symbol(str(rec.get("symbol", key.split(":")[-1])))
        direction = str(rec.get("direction", "SHORT")).upper()
        entry = safe_float(rec.get("entry", 0))
        stop = safe_float(rec.get("stop", 0))
        tp1 = safe_float(rec.get("tp1", 0))
        tp2 = safe_float(rec.get("tp2", 0))
        tp3 = safe_float(rec.get("tp3", 0))
        limit = int(clamp((FOLLOWUP_DELAY_SEC / 60.0) + 80, 120, 300))
        k1 = await get_klines(sym, "1m", limit)
        scan = [k for k in k1 if (kline_start_ms(k) / 1000.0) + 60 >= sent_ts] if k1 else []
        if not scan:
            scan = k1[-min(len(k1), 120):] if k1 else []
        last_price = safe_float(scan[-1][4]) if scan else entry
        outcome = "NÖTR"
        hit_time = "-"
        hit_price = 0.0
        detail = "Takip süresinde TP/stop görülmedi."
        for k in scan:
            hit = _followup_candle_hit(direction, k, stop, tp1, tp2, tp3)
            candle_time = tr_str(kline_start_ms(k) / 1000.0) if kline_start_ms(k) else "-"
            if hit["stop_hit"] and hit["tp_level"]:
                outcome = "STOP"
                hit_time = candle_time
                hit_price = stop
                detail = f"Aynı 1m mumda hem {hit['tp_level']} hem stop göründü; güvenli değerlendirme STOP."
                break
            if hit["stop_hit"]:
                outcome = "STOP"
                hit_time = candle_time
                hit_price = stop
                detail = "Stop, TP seviyelerinden önce geldi."
                break
            if hit["tp_level"]:
                outcome = hit["tp_level"]
                hit_time = candle_time
                hit_price = safe_float(hit["tp_price"])
                detail = f"{outcome}, stoptan önce geldi."
                # Kullanıcı TP1'de tamamını kapatmak istese bile raporda ulaşılan en üst TP'yi gösterebilmek için
                # aynı takip penceresinde daha derin TP var mı taramaya devam edilmez; ilk temas kuralı korunur.
                break
        pnl = pct_change(entry, last_price) if direction == "LONG" else pct_change(entry, last_price) * -1
        stars = {"TP1": "⭐", "TP2": "⭐⭐", "TP3": "⭐⭐⭐"}.get(outcome, "")
        text = (
            f"⏱ 2 SAAT TP/STOP TAKİP\n"
            f"⏰ Rapor: {tr_str()} | İlk temas: {hit_time}\n"
            f"🎯 {sym} | {direction}\n"
            f"💰 Giriş: {fmt_num(entry)} | Güncel: {fmt_num(last_price)}\n"
            f"📍 Sonuç fiyatı: {fmt_num(hit_price) if hit_price else '-'}\n"
            f"📊 Güncel PnL: %{pnl:.2f}\n"
            f"🛑 Stop: {fmt_num(stop)}\n"
            f"🎯 TP1: {fmt_num(tp1)} | TP2: {fmt_num(tp2)} | TP3: {fmt_num(tp3)}\n"
            f"🧭 Mum tarama: {len(scan)} adet 1m mum incelendi.\n"
            f"Sonuç: {outcome} {stars}\n"
            f"Not: {detail}"
        )
        ok = await safe_send_telegram(text)
        if ok:
            stats["followup_sent"] += 1
            rec["done"] = True
            rec["outcome"] = outcome
            rec["hit_time"] = hit_time
            rec["hit_price"] = hit_price
            record_lifetime_signal_outcome(rec, outcome)
            mistake_learn_from_followup(rec, outcome)


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
# PRO WS + PROFESYONEL GERÇEKÇİLİK KATMANI
# Bu bölüm yapay zeka değildir. Sinyali yorumlamaz; veri akışını,
# maliyet modelini, backtest gerçekçiliğini ve LONG güvenliğini artırır.
# =========================================================

_REST_get_okx_orderbook = get_okx_orderbook
_REST_get_okx_recent_trades = get_okx_recent_trades
_BASE_analyze_whale_eye_spoofing = analyze_whale_eye_spoofing
_BASE_enforce_single_long_al_rules = enforce_single_long_al_rules


def _safe_append_limited(mp: Dict[str, List[Dict[str, Any]]], key: str, item: Dict[str, Any], limit: int) -> None:
    arr = mp.setdefault(key, [])
    arr.append(item)
    if len(arr) > max(10, limit):
        del arr[:-max(10, limit)]


def _summarize_book_from_rows(symbol: str, bids: List[List[Any]], asks: List[List[Any]], ts: Optional[float] = None, source: str = "WS") -> Dict[str, Any]:
    if not bids or not asks:
        return {"enabled": True, "ok": False, "reason": f"{source} book boş"}
    best_bid = safe_float(bids[0][0])
    best_ask = safe_float(asks[0][0])
    mid = (best_bid + best_ask) / 2.0 if best_bid > 0 and best_ask > 0 else 0.0
    band = mid * 0.0018 if mid > 0 else 0.0
    bid_near = ask_near = bid_total = ask_total = 0.0
    bid_sizes: List[float] = []
    ask_sizes: List[float] = []
    for row in bids:
        px = safe_float(row[0]); sz = safe_float(row[1]); notional = px * sz
        bid_total += notional; bid_sizes.append(notional)
        if mid > 0 and px >= mid - band:
            bid_near += notional
    for row in asks:
        px = safe_float(row[0]); sz = safe_float(row[1]); notional = px * sz
        ask_total += notional; ask_sizes.append(notional)
        if mid > 0 and px <= mid + band:
            ask_near += notional
    total_near = bid_near + ask_near
    total_all = bid_total + ask_total
    book_pressure = ((ask_near - bid_near) / total_near) if total_near > 0 else 0.0
    full_book_pressure = ((ask_total - bid_total) / total_all) if total_all > 0 else 0.0
    prev = orderbook_memory.get(symbol, {})
    prev_bid_near = safe_float(prev.get("bid_near", 0))
    prev_ask_near = safe_float(prev.get("ask_near", 0))
    bid_wall_pulled = prev_bid_near > 0 and bid_near < prev_bid_near * 0.58
    ask_wall_stacked = prev_ask_near > 0 and ask_near > prev_ask_near * 1.35
    bid_wall_added = prev_bid_near > 0 and bid_near > prev_bid_near * 1.35
    ask_wall_pulled = prev_ask_near > 0 and ask_near < prev_ask_near * 0.58
    avg_bid = avg(bid_sizes) if bid_sizes else 0.0
    avg_ask = avg(ask_sizes) if ask_sizes else 0.0
    max_bid = max(bid_sizes) if bid_sizes else 0.0
    max_ask = max(ask_sizes) if ask_sizes else 0.0
    ts = ts or time.time()
    orderbook_memory[symbol] = {
        "ts": ts, "bid_near": bid_near, "ask_near": ask_near,
        "bid_total": bid_total, "ask_total": ask_total,
        "book_pressure": book_pressure, "full_book_pressure": full_book_pressure,
    }
    return {
        "enabled": True, "ok": True, "source": source, "ts": ts,
        "best_bid": best_bid, "best_ask": best_ask, "mid": mid,
        "spread_pct": abs(pct_change(best_bid, best_ask)) if best_bid > 0 and best_ask > 0 else 0.0,
        "bid_near": bid_near, "ask_near": ask_near, "bid_total": bid_total, "ask_total": ask_total,
        "book_pressure": round(book_pressure, 4), "full_book_pressure": round(full_book_pressure, 4),
        "bid_wall_pulled": bid_wall_pulled, "ask_wall_stacked": ask_wall_stacked,
        "bid_wall_added": bid_wall_added, "ask_wall_pulled": ask_wall_pulled,
        "max_bid_wall": max_bid, "max_ask_wall": max_ask,
        "avg_bid_wall": avg_bid, "avg_ask_wall": avg_ask,
        "reason": f"OKX {source} orderbook okundu.",
    }


def _pro_ws_symbols() -> List[str]:
    out: List[str] = []
    for sym in list(COINS) + [normalize_symbol(x) for x in MACRO_SYMBOLS]:
        ns = normalize_symbol(sym)
        if ns and ns not in out and not is_blocked_coin_symbol(ns):
            out.append(ns)
    return out[:max(1, PRO_WS_MAX_SYMBOLS)]


async def _okx_ws_consumer(symbols: List[str]) -> None:
    try:
        import importlib
        websockets = importlib.import_module("websockets")
    except Exception as e:
        ws_runtime_state.update({"enabled": False, "installed": False, "connected": False, "last_error": f"websockets paketi yok: {e}"})
        logger.warning("PRO WS kapalı: websockets paketi bulunamadı. requirements.txt içine websockets>=12.0 ekle.")
        return

    ws_runtime_state["installed"] = True
    while True:
        try:
            args = []
            for sym in symbols:
                args.append({"channel": PRO_WS_BOOK_CHANNEL, "instId": sym})
                args.append({"channel": PRO_WS_TRADE_CHANNEL, "instId": sym})
            async with websockets.connect(PRO_WS_OKX_URL, ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
                ws_runtime_state.update({"enabled": True, "connected": True, "last_error": "", "symbols": symbols})
                stats["ws_connect"] = stats.get("ws_connect", 0) + 1
                await ws.send(json.dumps({"op": "subscribe", "args": args}, ensure_ascii=False))
                async for raw in ws:
                    now_ts = time.time()
                    stats["ws_msg"] = stats.get("ws_msg", 0) + 1
                    ws_runtime_state["last_msg_ts"] = now_ts
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    arg = msg.get("arg", {}) if isinstance(msg, dict) else {}
                    channel = str(arg.get("channel", ""))
                    inst = normalize_symbol(str(arg.get("instId", "")))
                    data = msg.get("data", []) if isinstance(msg, dict) else []
                    if not inst or not data:
                        continue
                    if channel == PRO_WS_BOOK_CHANNEL:
                        item = data[0]
                        bids = item.get("bids", []) or []
                        asks = item.get("asks", []) or []
                        book = _summarize_book_from_rows(inst, bids, asks, now_ts, "WebSocket")
                        if book.get("ok"):
                            ws_orderbook_state[inst] = book
                            _safe_append_limited(ws_orderbook_history, inst, book, PRO_WS_HISTORY_LEN)
                            stats["ws_book_update"] = stats.get("ws_book_update", 0) + 1
                    elif channel == PRO_WS_TRADE_CHANNEL:
                        rows: List[Dict[str, Any]] = []
                        for row in data:
                            rows.append({
                                "px": safe_float(row.get("px", 0)),
                                "sz": safe_float(row.get("sz", 0)),
                                "side": str(row.get("side", "")).lower(),
                                "ts": safe_float(row.get("ts", now_ts * 1000)),
                            })
                        if rows:
                            cur = ws_trade_state.setdefault(inst, [])
                            cur.extend(rows)
                            if len(cur) > PRO_WS_TRADE_HISTORY_LEN:
                                del cur[:-PRO_WS_TRADE_HISTORY_LEN]
                            stats["ws_trade_update"] = stats.get("ws_trade_update", 0) + len(rows)
        except asyncio.CancelledError:
            ws_runtime_state.update({"connected": False, "last_error": "cancelled"})
            raise
        except Exception as e:
            ws_runtime_state.update({"connected": False, "last_error": str(e)[:180], "reconnects": int(ws_runtime_state.get("reconnects", 0)) + 1})
            stats["ws_reconnect"] = stats.get("ws_reconnect", 0) + 1
            logger.warning("PRO WS reconnect: %s", e)
            await asyncio.sleep(max(1.0, PRO_WS_RECONNECT_SEC))


async def pro_websocket_supervisor_loop() -> None:
    if not PRO_WS_ENABLED:
        ws_runtime_state.update({"enabled": False, "last_error": "PRO_WS_ENABLED=false"})
        return
    while True:
        symbols = _pro_ws_symbols()
        if not symbols:
            await asyncio.sleep(10)
            continue
        batches = [symbols[i:i + max(1, PRO_WS_BATCH_SIZE)] for i in range(0, len(symbols), max(1, PRO_WS_BATCH_SIZE))]
        tasks = [asyncio.create_task(_okx_ws_consumer(batch)) for batch in batches]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            raise
        except Exception as e:
            logger.warning("PRO WS supervisor hata: %s", e)
        await asyncio.sleep(max(5.0, PRO_WS_RECONNECT_SEC))


async def get_okx_orderbook(symbol: str, depth: int = 50) -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    if PRO_WS_ENABLED and PRO_WS_USE_FOR_ORDERBOOK:
        book = ws_orderbook_state.get(symbol)
        if book and book.get("ok") and time.time() - safe_float(book.get("ts", 0)) <= PRO_WS_STALE_SEC:
            stats["ws_orderbook_used"] = stats.get("ws_orderbook_used", 0) + 1
            return copy.deepcopy(book)
    return await _REST_get_okx_orderbook(symbol, depth)


async def get_okx_recent_trades(symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    symbol = normalize_symbol(symbol)
    if PRO_WS_ENABLED and PRO_WS_USE_FOR_TRADES:
        rows = ws_trade_state.get(symbol, [])
        if rows:
            stats["ws_trade_used"] = stats.get("ws_trade_used", 0) + 1
            return copy.deepcopy(rows[-min(max(limit, 10), len(rows)):])
    return await _REST_get_okx_recent_trades(symbol, limit)


def _pro_spoof_from_ws_history(symbol: str, direction: str = "SHORT") -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    hist = ws_orderbook_history.get(symbol, [])
    if len(hist) < PRO_SPOOF_MIN_HISTORY:
        return {"ok": False, "reason": "WebSocket spoofing için yeterli geçmiş yok"}
    now_ts = time.time()
    recent = [x for x in hist if now_ts - safe_float(x.get("ts", 0)) <= PRO_SPOOF_WINDOW_SEC]
    if len(recent) < PRO_SPOOF_MIN_HISTORY:
        recent = hist[-PRO_SPOOF_MIN_HISTORY:]
    cur = recent[-1]
    prev = recent[:-1]
    max_prev_bid = max(safe_float(x.get("bid_near", 0)) for x in prev) if prev else 0.0
    max_prev_ask = max(safe_float(x.get("ask_near", 0)) for x in prev) if prev else 0.0
    avg_prev_bid = avg([safe_float(x.get("bid_near", 0)) for x in prev]) if prev else 0.0
    avg_prev_ask = avg([safe_float(x.get("ask_near", 0)) for x in prev]) if prev else 0.0
    cur_bid = safe_float(cur.get("bid_near", 0))
    cur_ask = safe_float(cur.get("ask_near", 0))
    score = 0.0
    spoof_detected = False
    spoof_type = "YOK"
    reasons: List[str] = []
    if max_prev_bid > 0 and cur_bid < max_prev_bid * PRO_SPOOF_VANISH_RATIO and max_prev_bid > max(avg_prev_bid, 1e-9) * PRO_SPOOF_WALL_MULT:
        spoof_detected = True
        spoof_type = "WS_ALIS_DUVARI_KAYBOLDU"
        if direction == "SHORT":
            score += SPOOFING_SHORT_SCORE_BONUS + 3.0
        reasons.append(f"Canlı alış duvarı kayboldu: {fmt_num(max_prev_bid)} -> {fmt_num(cur_bid)}")
    if max_prev_ask > 0 and cur_ask < max_prev_ask * PRO_SPOOF_VANISH_RATIO and max_prev_ask > max(avg_prev_ask, 1e-9) * PRO_SPOOF_WALL_MULT:
        spoof_detected = True
        spoof_type = "WS_SATIS_DUVARI_KAYBOLDU"
        if direction == "LONG":
            score += SPOOFING_LONG_SCORE_BONUS + 3.0
        reasons.append(f"Canlı satış duvarı kayboldu: {fmt_num(max_prev_ask)} -> {fmt_num(cur_ask)}")
    if avg_prev_ask > 0 and cur_ask > avg_prev_ask * PRO_SPOOF_STACK_RATIO:
        if direction == "SHORT":
            score += SPOOFING_SHORT_SCORE_BONUS * 0.75
        reasons.append(f"Canlı satış duvarı yığıldı: avg {fmt_num(avg_prev_ask)} -> {fmt_num(cur_ask)}")
    if avg_prev_bid > 0 and cur_bid > avg_prev_bid * PRO_SPOOF_STACK_RATIO:
        if direction == "LONG":
            score += SPOOFING_LONG_SCORE_BONUS * 0.75
        reasons.append(f"Canlı alış duvarı yığıldı: avg {fmt_num(avg_prev_bid)} -> {fmt_num(cur_bid)}")
    return {
        "ok": True,
        "score": round(score, 2),
        "spoofing_detected": spoof_detected,
        "spoof_type": spoof_type,
        "reason": " | ".join(reasons) if reasons else "WebSocket spoofing temiz",
        "history_count": len(hist),
        "source": "WEBSOCKET",
    }


async def analyze_whale_eye_spoofing(symbol: str, price: float, direction: str = "SHORT") -> Dict[str, Any]:
    if not SPOOFING_ENGINE_ENABLED:
        return {"enabled": False, "score": 0, "spoofing_detected": False, "spoof_type": "KAPALI"}
    ws_res = _pro_spoof_from_ws_history(symbol, direction)
    if ws_res.get("ok"):
        if ws_res.get("spoofing_detected"):
            stats["ws_spoofing_detected"] = stats.get("ws_spoofing_detected", 0) + 1
            stats["spoofing_detected"] = stats.get("spoofing_detected", 0) + 1
        return {"enabled": True, **ws_res}
    rest_res = await _BASE_analyze_whale_eye_spoofing(symbol, price, direction)
    if PRO_SPOOFING_WS_REQUIRED_FOR_STRONG and rest_res.get("spoofing_detected"):
        rest_res["reason"] = f"REST spoofing izi var ama WS teyidi yok: {rest_res.get('reason', '-') }"
        rest_res["score"] = round(safe_float(rest_res.get("score", 0)) * 0.55, 2)
        rest_res["source"] = "REST_SOFT"
    return rest_res


def pro_estimated_cost_pct(entry: float, spread_pct: float = 0.0, funding_rate_pct_8h: Optional[float] = None) -> Dict[str, float]:
    funding = PRO_DEFAULT_FUNDING_PCT_8H if funding_rate_pct_8h is None else funding_rate_pct_8h
    # Entry + exit taker maliyeti, slippage ve tahmini funding taşıma maliyeti.
    fee_round = PRO_TAKER_FEE_PCT * 2.0
    slippage = PRO_SLIPPAGE_BASE_PCT * 2.0 + max(0.0, spread_pct) * PRO_SPREAD_SLIPPAGE_MULT
    funding_cost = abs(funding) * (max(0.0, PRO_FUNDING_HOLD_HOURS) / 8.0)
    total = fee_round + slippage + funding_cost
    return {"fee_round_pct": fee_round, "slippage_pct": slippage, "funding_cost_pct": funding_cost, "total_cost_pct": total}


def evaluate_tp_stop_path(
    klines: List[List[Any]],
    direction: str,
    sent_ts: float,
    entry: float,
    stop: float,
    tp1: float,
    tp2: float,
    tp3: float,
    spread_pct: float = 0.0,
    funding_rate_pct_8h: Optional[float] = None,
) -> Dict[str, Any]:
    direction = (direction or "SHORT").upper()
    if not klines:
        return {"trade_outcome": "VERI_YOK", "outcome": "VERI_YOK", "potential_outcome": "YOK", "checked": 0, "net_pnl_pct": 0.0}
    cost = pro_estimated_cost_pct(entry, spread_pct, funding_rate_pct_8h) if PRO_COST_MODEL_ENABLED else {"total_cost_pct": 0.0}
    first_outcome = "NÖTR"
    potential = "YOK"
    first_price = 0.0
    first_time = "-"
    same_candle = False
    for k in klines:
        high = safe_float(k[2]); low = safe_float(k[3])
        ts = tr_str(kline_start_ms(k) / 1000.0) if kline_start_ms(k) else "-"
        if direction == "LONG":
            stop_hit = low <= stop
            hits = []
            if high >= tp1: hits.append("TP1")
            if high >= tp2: hits.append("TP2")
            if high >= tp3: hits.append("TP3")
        else:
            stop_hit = high >= stop
            hits = []
            if low <= tp1: hits.append("TP1")
            if low <= tp2: hits.append("TP2")
            if low <= tp3: hits.append("TP3")
        if hits:
            potential = hits[-1]
        if first_outcome == "NÖTR":
            if stop_hit and hits:
                same_candle = True
                if PRO_BACKTEST_SAME_CANDLE_POLICY == "TP_FIRST":
                    first_outcome = hits[-1]
                    first_price = {"TP1": tp1, "TP2": tp2, "TP3": tp3}.get(first_outcome, tp1)
                else:
                    first_outcome = "STOP"
                    first_price = stop
                first_time = ts
                break
            if stop_hit:
                first_outcome = "STOP"; first_price = stop; first_time = ts; break
            if hits:
                first_outcome = hits[-1]; first_price = {"TP1": tp1, "TP2": tp2, "TP3": tp3}.get(first_outcome, tp1); first_time = ts; break
    if first_outcome == "NÖTR":
        last = safe_float(klines[-1][4])
        gross = pct_change(entry, last) if direction == "LONG" else pct_change(entry, last) * -1
    elif first_outcome == "STOP":
        gross = pct_change(entry, stop) if direction == "LONG" else pct_change(entry, stop) * -1
    else:
        px = {"TP1": tp1, "TP2": tp2, "TP3": tp3}.get(first_outcome, first_price)
        gross = pct_change(entry, px) if direction == "LONG" else pct_change(entry, px) * -1
    net = gross - safe_float(cost.get("total_cost_pct", 0.0))
    stats["pro_cost_applied"] = stats.get("pro_cost_applied", 0) + 1 if PRO_COST_MODEL_ENABLED else stats.get("pro_cost_applied", 0)
    return {
        "trade_outcome": first_outcome,
        "outcome": first_outcome,
        "potential_outcome": potential if potential != "YOK" else first_outcome,
        "hit_price": first_price,
        "hit_time": first_time,
        "same_candle": same_candle,
        "checked": len(klines),
        "gross_pnl_pct": round(gross, 3),
        "net_pnl_pct": round(net, 3),
        "cost_pct": round(safe_float(cost.get("total_cost_pct", 0.0)), 3),
        "cost_detail": cost,
    }


def _pro_calc_max_drawdown(equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        peak = max(peak, eq)
        if peak > 0:
            max_dd = min(max_dd, (eq - peak) / peak * 100.0)
    return round(abs(max_dd), 2)


def _pro_profit_factor(pnls: List[float]) -> float:
    wins = sum(x for x in pnls if x > 0)
    losses = abs(sum(x for x in pnls if x < 0))
    return round(wins / losses, 2) if losses > 0 else (999.0 if wins > 0 else 0.0)


def run_simple_backtest_on_klines(symbol: str, k1: List[List[Any]], direction: str, bars: int = BACKTEST_DEFAULT_BARS) -> Dict[str, Any]:
    direction = (direction or "SHORT").upper()
    data = k1[-max(120, min(len(k1), bars)):] if k1 else []
    if len(data) < 120:
        return {"ok": False, "reason": "Backtest için mum yetersiz"}
    closes_v = closes(data); highs_v = highs(data); lows_v = lows(data); vols_v = volumes(data)
    rs = rsi(closes_v, 14); e9 = ema(closes_v, 9); e21 = ema(closes_v, 21); atr_v = atr(data, 14)
    signals = []
    last_i = -999
    equity = PRO_BACKTEST_INITIAL_EQUITY
    equity_curve = [equity]
    pnl_list: List[float] = []
    for i in range(60, len(data) - BACKTEST_FORWARD_BARS):
        if i - last_i < BACKTEST_MIN_SIGNAL_GAP_BARS:
            continue
        price = closes_v[i]
        window_high = max(highs_v[i-55:i]); window_low = min(lows_v[i-55:i])
        width = max(window_high - window_low, 1e-9)
        pos = (price - window_low) / width
        vol_ratio = vols_v[i] / max(avg(vols_v[i-20:i]), 1e-9)
        spread_guess = clamp((safe_float(atr_v[i]) / max(price, 1e-9)) * 100.0 * 0.05, 0.01, 0.18)
        trigger = False
        if direction == "SHORT":
            trigger = pos >= 0.68 and price < e9[i] and e9[i] <= e21[i] * 1.003 and rs[i] < rs[i-1] and vol_ratio >= 0.50
        else:
            trigger = pos <= 0.38 and price > e9[i] and e9[i] >= e21[i] * 0.997 and rs[i] > rs[i-1] and vol_ratio >= 0.40
        if not trigger:
            continue
        entry = price
        stop, tp1, tp2, tp3 = _backtest_make_levels(direction, entry)
        result = evaluate_tp_stop_path(data[i+1:i+1+BACKTEST_FORWARD_BARS], direction, time.time()-999999, entry, stop, tp1, tp2, tp3, spread_pct=spread_guess)
        net_pct = safe_float(result.get("net_pnl_pct", 0.0))
        risk_cash = equity * (PRO_BACKTEST_RISK_PER_TRADE_PCT / 100.0)
        # Basit model: yüzde sonuç, risk yüzdesi kadar normalize edilir. Gerçek emir dolumu değildir.
        trade_cash = risk_cash * (net_pct / max(BACKTEST_RISK_STOP_PCT, 0.1))
        equity += trade_cash
        equity_curve.append(equity)
        pnl_list.append(trade_cash)
        signals.append({
            "i": i, "entry": entry, "outcome": result.get("trade_outcome"), "potential": result.get("potential_outcome"),
            "net_pct": result.get("net_pnl_pct"), "gross_pct": result.get("gross_pnl_pct"), "cost_pct": result.get("cost_pct"),
            "equity": round(equity, 2), "checked": result.get("checked")
        })
        last_i = i
    total = len(signals)
    wins = sum(1 for x in signals if str(x.get("outcome", "")).startswith("TP"))
    stops = sum(1 for x in signals if x.get("outcome") == "STOP")
    tp1 = sum(1 for x in signals if x.get("outcome") == "TP1")
    tp2 = sum(1 for x in signals if x.get("outcome") == "TP2")
    tp3 = sum(1 for x in signals if x.get("outcome") == "TP3")
    rate = wins / total * 100.0 if total else 0.0
    total_return = pct_change(PRO_BACKTEST_INITIAL_EQUITY, equity) if PRO_BACKTEST_INITIAL_EQUITY > 0 else 0.0
    return {
        "ok": True, "symbol": symbol, "direction": direction, "signals": total, "wins": wins, "stops": stops,
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "win_rate": round(rate, 1),
        "initial_equity": PRO_BACKTEST_INITIAL_EQUITY, "final_equity": round(equity, 2), "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": _pro_calc_max_drawdown(equity_curve), "profit_factor": _pro_profit_factor(pnl_list),
        "avg_trade_cash": round(avg(pnl_list), 3) if pnl_list else 0.0,
        "cost_model": f"fee round %{PRO_TAKER_FEE_PCT*2:.2f} + slippage + funding tahmini",
        "last": signals[-8:]
    }


async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not BACKTEST_ENGINE_ENABLED:
        await update.message.reply_text("Backtest motoru kapalı.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /backtest LDOUSDT LONG 240")
        return
    sym = normalize_symbol(context.args[0])
    direction = str(context.args[1]).upper() if len(context.args) >= 2 else "SHORT"
    bars = int(safe_float(context.args[2], BACKTEST_DEFAULT_BARS)) if len(context.args) >= 3 else BACKTEST_DEFAULT_BARS
    k1 = await get_klines(sym, "1m", min(300, max(140, bars)))
    res = run_simple_backtest_on_klines(sym, k1, direction, bars)
    stats["backtest_run"] = stats.get("backtest_run", 0) + 1
    stats["pro_backtest_run"] = stats.get("pro_backtest_run", 0) + 1
    if not res.get("ok"):
        await update.message.reply_text(f"Backtest yapılamadı: {res.get('reason')}")
        return
    lines = [
        "🧪 PROFESYONEL BACKTEST / REPLAY RAPORU",
        f"Coin: {sym} | Yön: {direction} | Mum: {bars}",
        f"Sinyal: {res.get('signals')} | TP: {res.get('wins')} | STOP: {res.get('stops')} | Başarı: %{res.get('win_rate')}",
        f"TP1/TP2/TP3: {res.get('tp1')}/{res.get('tp2')}/{res.get('tp3')}",
        f"Başlangıç: {res.get('initial_equity')} | Final: {res.get('final_equity')} | Getiri: %{res.get('total_return_pct')}",
        f"Max DD: %{res.get('max_drawdown_pct')} | Profit factor: {res.get('profit_factor')} | Ort. işlem: {res.get('avg_trade_cash')}",
        f"Maliyet modeli: {res.get('cost_model')}",
        "Not: WebSocket geçmişi olmadığı için bu replay mum bazlıdır; yine de komisyon/slippage/funding tahmini dahil edilir."
    ]
    await update.message.reply_text("\n".join(lines))


def enforce_single_long_al_rules(payload: Dict[str, Any]) -> Dict[str, Any]:
    p = _BASE_enforce_single_long_al_rules(payload)
    if p.get("stage") != "SIGNAL" or not PRO_LONG_STRICT_ENABLED:
        return p
    reason = str(p.get("reason", ""))
    ict = p.get("ict") if isinstance(p.get("ict"), dict) else {}
    regime = p.get("market_regime") if isinstance(p.get("market_regime"), dict) else {}
    sr = p.get("support_resistance") if isinstance(p.get("support_resistance"), dict) else {}
    flow = p.get("trade_flow") if isinstance(p.get("trade_flow"), dict) else {}
    book = p.get("orderbook") if isinstance(p.get("orderbook"), dict) else {}
    buy_to_sell = safe_float(flow.get("buy_to_sell", 0))
    sell_to_buy = safe_float(flow.get("sell_to_buy", 0))
    vol1 = safe_float(p.get("vol_ratio_1m", 0))
    vol5 = safe_float(p.get("vol_ratio_5m", 0))
    true_structure_up = bool(ict.get("bos_up") or ict.get("choch_up") or ict.get("mss_up"))
    hard: List[str] = []
    if PRO_LONG_BLOCK_STRONG_BEAR_REGIME and str(regime.get("regime", "")).upper() in ("BEAR_TREND", "STRONG_BEAR") and not true_structure_up:
        hard.append(f"rejim long karşıtı: {regime.get('regime')}")
    if sell_to_buy >= PRO_LONG_MAX_SELL_TO_BUY and buy_to_sell < PRO_LONG_MIN_BUY_TO_SELL:
        hard.append(f"satıcı akışı baskın x{sell_to_buy:.2f}")
    if vol1 < PRO_LONG_MIN_VOL1 and vol5 < PRO_LONG_MIN_VOL5 and buy_to_sell < PRO_LONG_MIN_BUY_TO_SELL:
        hard.append(f"hacim/flow zayıf: vol {vol1:.2f}/{vol5:.2f}, alış/satış {buy_to_sell:.2f}")
    if PRO_LONG_REQUIRE_SR_SUPPORT and sr.get("enabled") and not sr.get("near_trade_zone"):
        hard.append("destek bölgesi net değil")
    if PRO_LONG_REQUIRE_WS_NOT_BEARISH:
        ws_book = ws_orderbook_state.get(normalize_symbol(str(p.get("symbol", ""))), {})
        pressure = safe_float(ws_book.get("book_pressure", book.get("book_pressure", 0)))
        if pressure > 0.18:
            hard.append(f"canlı orderbook satış baskısı %{pressure*100:.1f}")
    if hard:
        p["stage"] = "READY"
        p["signal_label"] = "İÇ TAKİP"
        p["reason"] = f"{reason} | PRO LONG BLOK: {' | '.join(hard[:5])}"
        stats["pro_long_block"] = stats.get("pro_long_block", 0) + 1
        stats["long_quality_block"] = stats.get("long_quality_block", 0) + 1
        return p
    p["reason"] = f"{reason} | PRO LONG onayı: rejim/SR/flow/orderbook temiz"[:1400]
    p["signal_label"] = "LONG AL"
    return p


def build_heartbeat_message() -> str:
    hot_count = len(memory.get("hot", {}))
    trend_watch_count = len(memory.get("trend_watch", {}))
    last_sig = safe_float(memory.get("last_signal_ts", 0))
    last_sig_txt = tr_str(last_sig) if last_sig else "Yok"

    # Günlük sayaç sadece günlük limit içindir.
    today_short = get_today_trade_sent_count("SHORT")
    today_long = get_today_trade_sent_count("LONG")

    # Toplam sayaç kod aktif edildiğinden beri memory içinde kalıcı tutulur.
    ls = normalize_lifetime_stats()
    lifetime_total = int(safe_float(ls.get("total_signals", 0), 0))
    lifetime_short = int(safe_float(ls.get("short_signals", 0), 0))
    lifetime_long = int(safe_float(ls.get("long_signals", 0), 0))
    lifetime_tp = int(safe_float(ls.get("tp_total", 0), 0))
    lifetime_stop = int(safe_float(ls.get("stop_total", 0), 0))
    lifetime_neutral = int(safe_float(ls.get("neutral_total", 0), 0))
    lifetime_closed = lifetime_tp + lifetime_stop
    lifetime_pending = max(0, lifetime_total - lifetime_closed - lifetime_neutral)
    lifetime_winrate = (lifetime_tp / lifetime_closed * 100.0) if lifetime_closed > 0 else 0.0
    lifetime_age = format_duration_from_ts(safe_float(ls.get("activated_ts", 0), 0))

    follows = memory.get("follows", {})
    active_follow_tp = sum(1 for r in follows.values() if str(r.get("outcome", "")).startswith("TP"))
    active_follow_stop = sum(1 for r in follows.values() if r.get("outcome") == "STOP")

    ws_age = time.time() - safe_float(ws_runtime_state.get("last_msg_ts", 0)) if ws_runtime_state.get("last_msg_ts") else 9999
    ws_status = "AÇIK" if ws_runtime_state.get("connected") and ws_age <= PRO_WS_STALE_SEC * 3 else "KAPALI/BEKLİYOR"

    return (
        f"💓 {VERSION_NAME} DURUM\n"
        f"⏰ {tr_str()}\n"
        f"📊 Coin: {len(COINS)} | Sıcak: {hot_count} | Trend: {trend_watch_count} | Bloklu: {get_blocked_symbol_count()}\n"
        f"📨 Bugün: SHORT {today_short}/{DAILY_SHORT_TOTAL_LIMIT} | LONG {today_long}/{LONG_DAILY_TOTAL_LIMIT}\n"
        f"📈 Toplam sinyal: {lifetime_total} | SHORT {lifetime_short} | LONG {lifetime_long} | Süre: {lifetime_age}\n"
        f"🎯 Toplam başarı: TP={lifetime_tp} Stop={lifetime_stop} Bekleyen={lifetime_pending} Nötr={lifetime_neutral} | %{lifetime_winrate:.1f}\n"
        f"⭐ TP dağılımı: TP1={ls.get('tp1',0)} | TP2={ls.get('tp2',0)} | TP3={ls.get('tp3',0)}\n"
        f"📌 Aktif takip hafızası: TP={active_follow_tp} | Stop={active_follow_stop}\n"
        f"📡 WebSocket: {ws_status} | book={len(ws_orderbook_state)} | trades={sum(len(v) for v in ws_trade_state.values())} | age={ws_age:.1f}s | reconnect={ws_runtime_state.get('reconnects', 0)}\n"
        f"🐋 Whale Eye: OI={stats['oi_short_diverge']} Fund={stats['funding_short_bonus']} Spoof={stats['spoofing_detected']} CVD={stats['cvd_diverge_short']} | WS Spoof={stats.get('ws_spoofing_detected', 0)}\n"
        f"🛡️ Kalite Blok: {stats['quality_gate_block']} | Kırılım Geçen: {stats['trend_breakdown_pass']} | Kapanış Blok: {stats['close_confirm_block']}\n"
        f"🧪 Backtest: {stats.get('pro_backtest_run',0)} | Maliyet uygulandı={stats.get('pro_cost_applied',0)} | PRO LONG blok={stats.get('pro_long_block',0)}\n"
        f"🧠 Hata Hafızası: geçiş={stats.get('mistake_memory_pass',0)} | blok={stats.get('mistake_memory_block',0)} | öğrenme={stats.get('mistake_memory_learn',0)}\n"
        f"🔧 API Fail: {stats['api_fail']} | Telegram Fail: {stats['telegram_fail']} | Analiz: {stats['analyzed']}\n"
        f"📌 Son Sinyal: {last_sig_txt}\n"
        f"WS hata: {str(ws_runtime_state.get('last_error','-'))[:100] if ws_runtime_state.get('last_error') else '-'}"
    )


async def cmd_ws(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ws_age = time.time() - safe_float(ws_runtime_state.get("last_msg_ts", 0)) if ws_runtime_state.get("last_msg_ts") else 9999
    sample = list(ws_orderbook_state.keys())[:10]
    msg = (
        f"📡 WEBSOCKET DURUM\n"
        f"Aktif: {ws_runtime_state.get('connected', False)} | Paket: {ws_runtime_state.get('installed', False)}\n"
        f"URL: {PRO_WS_OKX_URL}\n"
        f"Kanal: {PRO_WS_BOOK_CHANNEL} + {PRO_WS_TRADE_CHANNEL}\n"
        f"Book sembol: {len(ws_orderbook_state)} | Trade sembol: {len(ws_trade_state)}\n"
        f"Son mesaj yaşı: {ws_age:.1f}s | Reconnect: {ws_runtime_state.get('reconnects', 0)}\n"
        f"Örnek semboller: {', '.join(sample) if sample else '-'}\n"
        f"Son hata: {ws_runtime_state.get('last_error', '-') or '-'}"
    )
    await update.message.reply_text(msg)


# =========================================================
# TELEGRAM KOMUTLARI
# =========================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🐋 {VERSION_NAME} AKTİF\n\n"
        "Komutlar:\n"
        "/status - Durum raporu\n"
        "/hot - Sıcak coinler\n"
        "/trend - Trend izleme listesi\n"
        "/coin BTCUSDT - Tek coin analiz\n"
        "/scan - Hızlı tarama\n"
        "/whale BTCUSDT - Whale Eye detay\n"
        "/av - Görünmeyen yüz av listesi\n"
        "/test - Test mesajı\n"
        "/id - Chat ID göster\n\n"
        "V6 YENİ MOTORLAR:\n"
        "🐋 Open Interest Delta\n"
        "💰 Funding Rate Dedektörü\n"
        "🪤 Orderbook Spoofing\n"
        "📊 CVD Diverjans"
    )


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ok = await safe_send_telegram(f"✅ Test başarılı. {tr_str()}")
    await update.message.reply_text("Test gönderildi." if ok else "Test başarısız.")


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await update.message.reply_text(f"CHAT ID: {chat.id}\nTYPE: {chat.type}\nTITLE: {chat.title or chat.first_name or '-'}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_heartbeat_message())


async def cmd_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    hot = memory.get("hot", {})
    if not hot:
        await update.message.reply_text("Şu an sıcak coin yok.")
        return
    items = sorted(hot.items(), key=lambda x: safe_float(x[1].get("score", 0)), reverse=True)[:10]
    lines = ["🔥 Sıcak Coinler:"]
    for sym, rec in items:
        lines.append(f"- {sym} | skor={safe_float(rec.get('score', 0)):.1f} | 🐋={rec.get('whale_confidence', '-')} | fiyat={fmt_num(safe_float(rec.get('last_price', 0)))}")
    await update.message.reply_text("\n".join(lines))


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tickers24 = await get_24h_tickers()
    syms = pick_general_symbols(8)
    out = ["🔎 Hızlı Tarama:"]
    for sym in syms:
        res = await analyze_symbol(sym, tickers24)
        if not res:
            continue
        whale_conf = res.get("whale_eye", {}).get("whale_confidence", "-")
        out.append(f"- {sym} | {res['stage']} | skor={res.get('score', 0)} | 🐋={whale_conf} | fiyat={fmt_num(safe_float(res.get('price', 0)))}")
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
        res["binance_symbol"] = confirm.get("binance_symbol", "")
        res["binance_price"] = confirm.get("binance_price", 0)
        res["binance_price_gap_pct"] = confirm.get("price_gap_pct", 0)
        res["binance_confirm_reason"] = confirm.get("reason", "-")
        await update.message.reply_text(build_signal_message(res))
    elif res["stage"] == "READY":
        await update.message.reply_text(build_ready_message(res))
    elif res["stage"] == "HOT":
        await update.message.reply_text(build_hot_message(res))
    else:
        await update.message.reply_text(f"{symbol} şu an short için zayıf.\nSkor: {res.get('score', 0)}\n🐋 Whale: {res.get('whale_eye', {}).get('whale_confidence', '-')}\n{res.get('reason', '')[:300]}")


async def cmd_whale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Whale Eye detaylı raporu"""
    if not context.args:
        await update.message.reply_text("Kullanım: /whale BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    k1 = await get_klines(symbol, "1m", 120)
    if len(k1) < 50:
        await update.message.reply_text(f"{symbol} için yeterli veri yok.")
        return
    price = safe_float(k1[-1][4])
    whale = await build_full_whale_eye_analysis(symbol, price, 0, k1, "SHORT")

    oi = whale.get("oi", {})
    funding = whale.get("funding", {})
    spoofing = whale.get("spoofing", {})
    cvd = whale.get("cvd", {})

    msg = (
        f"🐋 WHALE EYE RAPORU - {symbol}\n"
        f"⏰ {tr_str()}\n"
        f"💰 Fiyat: {fmt_num(price)}\n"
        f"📊 Toplam Skor: {whale.get('total_score', 0)}\n"
        f"🎯 Güven: {whale.get('whale_confidence', '-')}\n"
        f"🔢 Uyumsuzluk: {whale.get('divergence_count', 0)}\n\n"
        f"📈 OPEN INTEREST\n"
        f"├─ Durum: {oi.get('divergence_type', '-')}\n"
        f"├─ Kaynak: {oi.get('source', '-')}\n"
        f"├─ Güncel OI: {oi.get('current_oi', 0):,.0f}\n"
        f"├─ OI Değişim: %{oi.get('oi_change_pct', 0):.2f}\n"
        f"├─ Fiyat Değişim: %{oi.get('price_change_pct', 0):.2f}\n"
        f"└─ Yorum: {oi.get('reason', '-')}\n\n"
        f"💰 FUNDING RATE\n"
        f"├─ Oran: %{funding.get('funding_rate', 0):.4f}\n"
        f"├─ Kaynak: {funding.get('source', '-')}\n"
        f"├─ Sinyal: {funding.get('funding_signal', '-')}\n"
        f"└─ Yorum: {funding.get('reason', '-')}\n\n"
        f"🪤 ORDERBOOK SPOOFING\n"
        f"├─ Tespit: {spoofing.get('spoofing_detected', False)}\n"
        f"├─ Tip: {spoofing.get('spoof_type', '-')}\n"
        f"└─ Yorum: {spoofing.get('reason', '-')}\n\n"
        f"📊 CVD\n"
        f"├─ Diverjans: {cvd.get('divergence', '-')}\n"
        f"├─ CVD Trend: %{cvd.get('cvd_trend_pct', 0):.2f}\n"
        f"└─ Fiyat Trend: %{cvd.get('price_trend_pct', 0):.2f}"
    )
    await update.message.reply_text(msg)


async def cmd_trend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    trend_watch = memory.get("trend_watch", {})
    if not trend_watch:
        await update.message.reply_text("Şu an trend devam kilidine takılan coin yok.")
        return

    items = sorted(
        trend_watch.items(),
        key=lambda x: safe_float(x[1].get("score", 0)),
        reverse=True
    )[:12]

    lines = ["🧲 Trend izleme / short erken kilidi:"]
    for sym, rec in items:
        first_price = safe_float(rec.get("first_price", 0))
        last_price = safe_float(rec.get("last_price", 0))
        move = pct_change(first_price, last_price) if first_price > 0 and last_price > 0 else 0.0
        whale_conf = rec.get("whale_confidence", "-")
        lines.append(
            f"- {sym} | skor={safe_float(rec.get('score', 0)):.1f} | 🐋={whale_conf} | "
            f"ilk={fmt_num(first_price)} | son={fmt_num(last_price)} | "
            f"hareket=%{move:.2f} | kırılım={safe_float(rec.get('breakdown_score', 0)):.1f}"
        )

    await update.message.reply_text("\n".join(lines))


async def cmd_av(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    merged: Dict[str, Dict[str, Any]] = {}
    for sym, rec in memory.get("hot", {}).items():
        merged[sym] = {**copy.deepcopy(rec), "source": "HOT"}
    for sym, rec in memory.get("trend_watch", {}).items():
        old = merged.get(sym, {})
        if safe_float(rec.get("score", 0)) > safe_float(old.get("score", 0)):
            merged[sym] = {**copy.deepcopy(rec), "source": "TREND"}
    if not merged:
        await update.message.reply_text("🎯 Şu an av listesinde coin yok.")
        return
    items = sorted(merged.items(), key=lambda x: safe_float(x[1].get("score", 0)), reverse=True)[:15]
    lines = ["🎯 AV LİSTESİ:"]
    for sym, rec in items:
        lines.append(f"- {sym} | skor={safe_float(rec.get('score', 0)):.1f} | 🐋={rec.get('whale_confidence', '-')} | fiyat={fmt_num(safe_float(rec.get('last_price', 0)))}")
    await update.message.reply_text("\n".join(lines))



async def cmd_hafiza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_mistake_memory_status_message())


# =========================================================
# BAŞLATMA
# =========================================================
async def post_init(application) -> None:
    active_count, pruned_count = await refresh_coin_pool(force=True)
    if AUTO_START_MESSAGE:
        await safe_send_telegram(
            f"🐋 {VERSION_NAME} BAŞLADI\n"
            f"⏰ {tr_str()}\n"
            f"📊 Coin: {active_count} aktif\n"
            f"🗑️ Çıkarılan: {pruned_count}\n"
            f"📡 Veri: OKX {OKX_INST_TYPE}\n"
            f"🐋 Whale Eye: OI + Funding + Spoofing + CVD AKTİF\n"
            f"🧱 Mimari: Profesyonel paket yapı + log rotation + cache cleanup\n"
            f"🎯 Günlük SHORT limit: {DAILY_SHORT_TOTAL_LIMIT}\n"
            f"🎯 Günlük LONG limit: {LONG_DAILY_TOTAL_LIMIT}\n"
            f"🧠 Hata hafızası: aktif"
        )

    asyncio.create_task(hot_scan_loop())
    asyncio.create_task(deep_scan_loop())
    asyncio.create_task(symbol_refresh_loop())
    asyncio.create_task(pro_websocket_supervisor_loop())
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(followup_loop())
    asyncio.create_task(position_management_loop())
    asyncio.create_task(cache_cleanup_loop())
    asyncio.create_task(save_loop())
    logger.info("Tüm motorlar başlatıldı")


def validate_config() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError(f"Eksik env: {', '.join(missing)}")



# =========================================================
# DOĞAL DİL KOMUT MOTORU
# =========================================================
# Bu katman yapay zeka değildir. Sinyal motoruna karışmaz.
# Sadece kullanıcının normal cümlelerini mevcut komutlara çevirir.
def _nl_clean_text(text: str) -> str:
    import re
    s = (text or "").strip().lower()
    tr_map = str.maketrans({
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "â": "a", "î": "i", "û": "u"
    })
    s = s.translate(tr_map)
    s = re.sub(r"[^a-z0-9\s\-_/\.]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _nl_known_coin_bases() -> List[str]:
    bases = {"BTC", "ETH"}
    for sym in COINS:
        base = coin_base_from_symbol(sym)
        if base:
            bases.add(base.upper())
    return sorted(bases, key=len, reverse=True)


def _nl_extract_coin(text: str) -> Optional[str]:
    import re
    raw = (text or "").upper().replace("/", "-")
    cleaned = _nl_clean_text(text).upper()

    # BTCUSDT, BTC-USDT, BTC-USDT-SWAP gibi doğrudan sembol yakalama
    m = re.search(r"\b([A-Z0-9]{2,15})(?:-)?USDT(?:-SWAP)?\b", raw)
    if m:
        return normalize_symbol(m.group(1))

    skip_words = {
        "DURUM", "BOT", "WS", "WEB", "WEBSOCKET", "BALINA", "WHALE", "BAK", "ANALIZ", "ANALIZI",
        "SICAK", "HOT", "TREND", "HAFIZA", "HATA", "AV", "LISTE", "LISTESI", "POZISYON",
        "ISLEM", "TEST", "ID", "CHAT", "BACKTEST", "REPLAY", "SHORT", "LONG", "COIN", "COINLER"
    }
    tokens = re.findall(r"\b[A-Z0-9]{2,15}\b", cleaned)
    for token in tokens:
        if token in skip_words:
            continue
        if token in _nl_known_coin_bases():
            return normalize_symbol(token)
    return None


async def _nl_reply_coin(update: Update, symbol: str) -> None:
    symbol = normalize_symbol(symbol)
    tickers24 = await get_24h_tickers()
    res = await analyze_symbol(symbol, tickers24)
    long_res = await analyze_long_symbol(symbol, tickers24) if LONG_ENGINE_ENABLED else None

    lines: List[str] = [f"🔎 {symbol} DOĞAL DİL ANALİZ"]
    if res:
        lines.append(
            f"SHORT: {res.get('stage')} | skor={res.get('score', 0)} | fiyat={fmt_num(safe_float(res.get('price', 0)))} | "
            f"kırılım={res.get('breakdown_score', '-')} | whale={res.get('whale_eye', {}).get('whale_confidence', '-')}"
        )
        lines.append(f"SHORT not: {str(res.get('reason', '-'))[:450]}")
    else:
        lines.append("SHORT: analiz edilemedi veya veri yetersiz.")

    if long_res:
        lines.append(
            f"LONG: {long_res.get('stage')} | skor={long_res.get('score', 0)} | kalite={long_res.get('quality_score', '-')} | "
            f"fiyat={fmt_num(safe_float(long_res.get('price', 0)))}"
        )
        lines.append(f"LONG not: {str(long_res.get('reason', '-'))[:350]}")

    await update.message.reply_text("\n".join(lines[:8]))


async def _nl_reply_whale(update: Update, symbol: str) -> None:
    symbol = normalize_symbol(symbol)
    k1 = await get_klines(symbol, "1m", 120)
    if len(k1) < 50:
        await update.message.reply_text(f"{symbol} için Whale Eye verisi yetersiz.")
        return
    price = safe_float(k1[-1][4])
    whale = await build_full_whale_eye_analysis(symbol, price, 0, k1, "SHORT")
    oi = whale.get("oi", {})
    funding = whale.get("funding", {})
    spoofing = whale.get("spoofing", {})
    cvd = whale.get("cvd", {})
    msg = (
        f"🐋 WHALE EYE RAPORU - {symbol}\n"
        f"⏰ {tr_str()}\n"
        f"💰 Fiyat: {fmt_num(price)}\n"
        f"📊 Toplam Skor: {whale.get('total_score', 0)} | Güven: {whale.get('whale_confidence', '-')}\n\n"
        f"📈 OI: {oi.get('divergence_type', '-')} | Kaynak: {oi.get('source', '-')} | Değişim: %{safe_float(oi.get('oi_change_pct', 0)):.2f}\n"
        f"💰 Funding: %{safe_float(funding.get('funding_rate', 0)):.4f} | Kaynak: {funding.get('source', '-')} | {funding.get('funding_signal', '-')}\n"
        f"🪤 Spoofing: {spoofing.get('spoofing_detected', False)} | Tip: {spoofing.get('spoof_type', '-')}\n"
        f"📊 CVD: {cvd.get('divergence', '-')} | CVD trend: %{safe_float(cvd.get('cvd_trend_pct', 0)):.2f} | Fiyat trend: %{safe_float(cvd.get('price_trend_pct', 0)):.2f}\n"
        f"Not: {whale.get('reason', '-') if whale.get('reason') else 'Whale Eye özeti hazır.'}"
    )
    await update.message.reply_text(msg)


async def _nl_reply_backtest(update: Update, symbol: str, direction: str = "SHORT", bars: int = BACKTEST_DEFAULT_BARS) -> None:
    if not BACKTEST_ENGINE_ENABLED:
        await update.message.reply_text("Backtest motoru kapalı.")
        return
    sym = normalize_symbol(symbol)
    direction = (direction or "SHORT").upper()
    if direction not in ("SHORT", "LONG"):
        direction = "SHORT"
    bars = int(clamp(float(bars), 120, 300))
    k1 = await get_klines(sym, "1m", min(300, max(140, bars)))
    res = run_simple_backtest_on_klines(sym, k1, direction, bars)
    stats["backtest_run"] = stats.get("backtest_run", 0) + 1
    stats["pro_backtest_run"] = stats.get("pro_backtest_run", 0) + 1
    if not res.get("ok"):
        await update.message.reply_text(f"Backtest yapılamadı: {res.get('reason')}")
        return
    await update.message.reply_text(
        "🧪 PROFESYONEL BACKTEST / REPLAY RAPORU\n"
        f"Coin: {sym} | Yön: {direction} | Mum: {bars}\n"
        f"Sinyal: {res.get('signals')} | TP: {res.get('wins')} | STOP: {res.get('stops')} | Başarı: %{res.get('win_rate')}\n"
        f"TP1/TP2/TP3: {res.get('tp1')}/{res.get('tp2')}/{res.get('tp3')}\n"
        f"Final equity: {res.get('final_equity')} | Getiri: %{res.get('total_return_pct')} | Max DD: %{res.get('max_drawdown_pct')}\n"
        f"Maliyet modeli: {res.get('cost_model')}"
    )


def _nl_today_signal_summary() -> str:
    total_short = get_today_trade_sent_count("SHORT")
    total_long = get_today_trade_sent_count("LONG")
    last_sig = safe_float(memory.get("last_signal_ts", 0))
    last_sig_txt = tr_str(last_sig) if last_sig else "Yok"
    return (
        "📨 BUGÜN SİNYAL ÖZETİ\n"
        f"SHORT: {total_short}/{DAILY_SHORT_TOTAL_LIMIT}\n"
        f"LONG: {total_long}/{LONG_DAILY_TOTAL_LIMIT}\n"
        f"Toplam gönderilen: {stats.get('signal_sent', 0)}\n"
        f"Son sinyal: {last_sig_txt}"
    )


def _nl_direction_signal_summary(direction: str = "SHORT") -> str:
    """Doğal dilde 'short var mı / long var mı' sorusuna net cevap verir."""
    direction = (direction or "SHORT").upper()
    if direction not in ("SHORT", "LONG"):
        direction = "SHORT"

    total = get_today_trade_sent_count(direction)
    limit = LONG_DAILY_TOTAL_LIMIT if direction == "LONG" else DAILY_SHORT_TOTAL_LIMIT
    day_key = tr_day_key()
    daily_key = "daily_long_sent" if direction == "LONG" else "daily_short_sent"
    daily_map = memory.get(daily_key, {}).get(day_key, {}) or {}

    last_symbol = "-"
    last_time = "Yok"
    if daily_map:
        try:
            last_symbol, rec = max(daily_map.items(), key=lambda x: safe_float((x[1] or {}).get("ts", 0)))
            ts = safe_float((rec or {}).get("ts", 0))
            last_time = tr_str(ts) if ts else "Yok"
        except Exception:
            pass

    active = []
    for _, rec in (memory.get("follows", {}) or {}).items():
        if rec.get("done"):
            continue
        if str(rec.get("direction", "SHORT")).upper() == direction:
            active.append(str(rec.get("symbol", "-")))

    if direction == "SHORT":
        hot_items = sorted(
            (memory.get("hot", {}) or {}).items(),
            key=lambda x: safe_float((x[1] or {}).get("score", 0)),
            reverse=True
        )[:5]
        hot_txt = ", ".join(f"{s}({safe_float((r or {}).get('score', 0)):.0f})" for s, r in hot_items) if hot_items else "Yok"
    else:
        hot_txt = "LONG sıcak listesi ayrı tutulmuyor; coin bazlı analiz için 'SEI bak' yaz."

    if total > 0:
        status = f"✅ Bugün {total} adet {direction} sinyali var."
    else:
        status = f"Şu an bugün gönderilmiş {direction} sinyali yok."

    return (
        f"📨 {direction} SİNYAL DURUMU\n"
        f"{status}\n"
        f"Günlük sınır: {total}/{limit}\n"
        f"Aktif takip: {', '.join(active[:6]) if active else 'Yok'}\n"
        f"Son {direction}: {last_symbol} | {last_time}\n"
        f"Sıcak takip: {hot_txt}\n"
        f"Not: Yeni temiz {direction} oluşursa bot ayrıca Telegram'a AL mesajı atar."
    )


def _nl_coin_list_message() -> str:
    shown = COINS[:45]
    extra = max(0, len(COINS) - len(shown))
    return (
        f"📋 AKTİF COIN LİSTESİ ({len(COINS)})\n" +
        ", ".join(shown) +
        (f"\n... +{extra} coin daha" if extra else "")
    )


async def cmd_natural(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Slash kullanmadan yazılan cümleleri mevcut komutlara çevirir."""
    text_raw = update.message.text or ""
    text = _nl_clean_text(text_raw)
    if not text:
        await update.message.reply_text("Buradayım dostum. Durum, ws, btc balina bak, sei bak gibi yazabilirsin.")
        return

    # Yardım / örnekler
    if any(x in text for x in ("yardim", "ne yazabilirim", "komut", "neler yapabilirsin", "nasil kullan")):
        await update.message.reply_text(
            "🤝 Beni slash olmadan da kullanabilirsin:\n"
            "- nasılsın\n"
            "- durum ne\n"
            "- ws çalışıyor mu\n"
            "- btc balina bak\n"
            "- sei bak / tao analiz et\n"
            "- sıcak coinler\n"
            "- hata hafızası\n"
            "- pozisyonlar\n"
            "- coin listesi\n"
            "- btc short backtest 240"
        )
        return

    # Selam / sohbet
    greeting_words = ("selam", "merhaba", "naber", "nasilsin", "iyi misin", "gunaydin", "iyi aksam", "iyi geceler", "dostum")
    command_words = ("durum", "ws", "websocket", "balina", "whale", "analiz", "bak", "sicak", "trend", "hafiza", "pozisyon", "backtest", "coin")
    if any(g in text for g in greeting_words) and not any(c in text for c in command_words):
        ws_age = time.time() - safe_float(ws_runtime_state.get("last_msg_ts", 0)) if ws_runtime_state.get("last_msg_ts") else 9999
        ws_ok = ws_runtime_state.get("connected") and ws_age <= PRO_WS_STALE_SEC * 3
        await update.message.reply_text(
            f"İyiyim dostum, görevdeyim. WebSocket {'açık' if ws_ok else 'bekliyor/kapalı'}, "
            f"analiz sayacı {stats.get('analyzed', 0)}, son sinyal {tr_str(memory.get('last_signal_ts')) if memory.get('last_signal_ts') else 'yok'}."
        )
        return

    # Durum / health / bugün sinyal
    if any(x in text for x in ("durum", "calisiyor", "ayakta", "health", "bot ne durumda", "bot durum")):
        await cmd_status(update, context)
        return

    # "Short var mı?", "Long var mı?", "AL var mı?" gibi doğal sorular
    # Backtest sorularını burada yakalama; onlar aşağıdaki backtest bloğuna gitsin.
    has_signal_question = any(x in text for x in (
        "varmi", "var mi", "var m", "sinyal", "firsat", "al var", "alim var",
        "short var", "long var", "short al", "long al"
    ))
    if "backtest" not in text and has_signal_question:
        if "short" in text or "sort" in text:
            await update.message.reply_text(_nl_direction_signal_summary("SHORT"))
            return
        if "long" in text:
            await update.message.reply_text(_nl_direction_signal_summary("LONG"))
            return
        if any(x in text for x in ("bugun sinyal", "sinyal attin", "sinyal var", "kac sinyal", "al var", "alim var", "firsat var")):
            await update.message.reply_text(_nl_today_signal_summary())
            return

    # Coin listesi / izlenen coinler
    # ÖNEMLİ: Bu blok Whale/OI bloğundan önce olmalı.
    # Çünkü "coin" kelimesinin içinde "oi" harfleri geçer; eski sürüm "hangi coinleri izliyorsun"
    # cümlesini yanlışlıkla OI/Whale raporu sanıyordu.
    coin_list_phrases = (
        "coin listesi", "hangi coin", "coinler", "coinleri", "liste",
        "hangi coinleri izliyorsun", "hangi coinleri takip", "izledigin coin",
        "takip ettigin coin", "izlenen coin", "aktif coin"
    )
    if any(x in text for x in coin_list_phrases) and not _nl_extract_coin(text_raw):
        await update.message.reply_text(_nl_coin_list_message())
        return

    # WebSocket
    if any(x in text for x in ("websocket", "ws", "canli veri", "canli akış", "canli akis", "book", "orderbook")):
        await cmd_ws(update, context)
        return

    # Whale / balina raporu
    # "oi" sadece tek başına kelimeyse yakalanır; "coin" içindeki oi artık yanlış tetiklemez.
    tokens = set(text.split())
    whale_phrase_hit = any(x in text for x in ("balina", "whale", "funding", "cvd", "spoof", "open interest"))
    whale_token_hit = ("oi" in tokens)
    if whale_phrase_hit or whale_token_hit:
        sym = _nl_extract_coin(text_raw) or "BTC-USDT-SWAP"
        await _nl_reply_whale(update, sym)
        return

    # Hata hafızası
    if any(x in text for x in ("hafiza", "hata", "hatali", "ogrenme", "stop hafiza", "hata hafizasi")):
        await cmd_hafiza(update, context)
        return

    # Sıcak / trend / av / pozisyon
    if any(x in text for x in ("sicak", "hot", "isinan", "sicak coin")):
        await cmd_hot(update, context)
        return
    if "trend" in text:
        await cmd_trend(update, context)
        return
    if text in ("av", "av listesi") or "av listesi" in text or "gorunmeyen" in text:
        await cmd_av(update, context)
        return
    if any(x in text for x in ("pozisyon", "aktif islem", "islemler", "takip edilen")):
        await cmd_pozisyon(update, context)
        return

    # Backtest doğal dil: btc short backtest 240 / backtest sei long
    if "backtest" in text or "replay" in text or "geriye donuk" in text:
        sym = _nl_extract_coin(text_raw) or "BTC-USDT-SWAP"
        direction = "LONG" if "long" in text else "SHORT"
        import re
        nums = [int(x) for x in re.findall(r"\b\d{2,4}\b", text)]
        bars = nums[-1] if nums else BACKTEST_DEFAULT_BARS
        await _nl_reply_backtest(update, sym, direction, bars)
        return

    # Tara / scan
    if any(x in text for x in ("tara", "scan", "piyasayi tara", "hizli tarama")):
        await cmd_scan(update, context)
        return

    # Test / id
    if text in ("test", "test at", "test mesaj"):
        await cmd_test(update, context)
        return
    if text in ("id", "chat id", "chatid"):
        await cmd_id(update, context)
        return

    # Coin analizi: sei bak, tao ne durumda, btc analiz et...
    sym = _nl_extract_coin(text_raw)
    if sym:
        await _nl_reply_coin(update, sym)
        return

    if text_raw.strip().lower().startswith("neden"):
        await cmd_neden(update, context)
        return

    # Bilinmeyen mesajlara da cevap ver.
    await update.message.reply_text(
        "Duydum dostum. Bunu komuta çeviremedim ama buradayım.\n"
        "Örnek: durum ne, ws çalışıyor mu, btc balina bak, sei bak, sıcak coinler, hata hafızası."
    )

def build_app():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("test", cmd_test))
    application.add_handler(CommandHandler("id", cmd_id))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("health", cmd_status))
    application.add_handler(CommandHandler("ws", cmd_ws))
    application.add_handler(CommandHandler("scan", cmd_scan))
    application.add_handler(CommandHandler("coin", cmd_coin))
    application.add_handler(CommandHandler("hot", cmd_hot))
    application.add_handler(CommandHandler("whale", cmd_whale))
    application.add_handler(CommandHandler("trend", cmd_trend))
    application.add_handler(CommandHandler("av", cmd_av))
    application.add_handler(CommandHandler("backtest", cmd_backtest))
    application.add_handler(CommandHandler("pozisyon", cmd_pozisyon))
    application.add_handler(CommandHandler("hafiza", cmd_hafiza))
    application.add_handler(CommandHandler("neden", cmd_neden))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_natural))
    return application


async def shutdown_app(signal_type=None):
    logger.info("Shutdown başlatılıyor... (signal: %s)", signal_type)
    save_memory()
    logger.info("Memory kaydedildi.")
    if app:
        try:
            await app.stop()
            await app.shutdown()
        except Exception as e:
            logger.warning("Uygulama durdurma hatası: %s", e)
    logger.info("Bot durdu.")

def main() -> None:
    global app
    try:
        validate_config()
        load_memory()
        app = build_app()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except Exception:
            loop = asyncio.get_event_loop_policy().new_event_loop()
            asyncio.set_event_loop(loop)

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                if hasattr(loop, "add_signal_handler"):
                    loop.add_signal_handler(
                        sig,
                        lambda s=sig: asyncio.create_task(shutdown_app(s.name))
                    )
            except (NotImplementedError, RuntimeError, ValueError):
                logger.info(
                    "Bu platformda add_signal_handler desteklenmiyor: %s",
                    getattr(sig, "name", sig)
                )

        logger.info("%s başlıyor", VERSION_NAME)
        app.run_polling(close_loop=False, drop_pending_updates=True)

    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.exception("Kritik hata: %s", e)
        raise
    finally:
        logger.info("Memory kaydediliyor...")
        save_memory()
        logger.info("Bot durdu.")


if __name__ == "__main__":
    main()
