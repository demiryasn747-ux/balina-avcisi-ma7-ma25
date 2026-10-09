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
import hashlib
import shutil
import platform
import math
import functools
import itertools
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

VERSION_NAME = "Balina Avcısı V12.1.0 KURUMSAL ÖLÇÜM PLATFORMU"
BOT_BUILD = "V12.1.0"  # Bu çalıştırılabilir dosyanın sürümü; eski Railway etiketiyle karışmaz.

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
ORTAK_MIN_N = int(float(os.getenv("ORTAK_MIN_N", "20")))
KOMBINASYON_MIN_KAPANIS = int(float(os.getenv("KOMBINASYON_MIN_KAPANIS", "100")))
GOLGE_IZLEME = os.getenv("GOLGE_IZLEME", "true").lower() == "true"
GOLGE_SAAT = float(os.getenv("GOLGE_SAAT", "48"))
GOLGE_ARALIK_SEC = int(float(os.getenv("GOLGE_ARALIK_SEC", "300")))
GOLGE_TF = os.getenv("GOLGE_TF", "15m").strip()

# === V12.1.0 KURUMSAL ALTYAPI ===
KURUMSAL_ENABLED = os.getenv("KURUMSAL_ENABLED", "true").lower() == "true"
DB_SCHEMA_VERSION = 14
DB_BACKUP_ENABLED = os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true"
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", "/data/backups").strip()
DB_BACKUP_INTERVAL_SEC = int(float(os.getenv("DB_BACKUP_INTERVAL_SEC", "21600")))
DB_BACKUP_KEEP = int(float(os.getenv("DB_BACKUP_KEEP", "28")))
DB_INTEGRITY_INTERVAL_SEC = int(float(os.getenv("DB_INTEGRITY_INTERVAL_SEC", "3600")))
AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", "true").lower() == "true"
HEALTH_ALERT_ENABLED = os.getenv("HEALTH_ALERT_ENABLED", "true").lower() == "true"
HEALTH_CHECK_INTERVAL_SEC = int(float(os.getenv("HEALTH_CHECK_INTERVAL_SEC", "60")))
HEALTH_ALERT_COOLDOWN_SEC = int(float(os.getenv("HEALTH_ALERT_COOLDOWN_SEC", "1800")))
SCAN_STALE_SEC = float(os.getenv("SCAN_STALE_SEC", "180"))
PAPER_STALE_SEC = float(os.getenv("PAPER_STALE_SEC", "180"))
DATA_MAX_AGE_SEC = float(os.getenv("DATA_MAX_AGE_SEC", "30"))
DATA_QUALITY_BLOCK_ENABLED = os.getenv("DATA_QUALITY_BLOCK_ENABLED", "false").lower() == "true"
SIM_FEE_RATE_PCT = float(os.getenv("SIM_FEE_RATE_PCT", "0.05"))
SIM_SLIPPAGE_PCT = float(os.getenv("SIM_SLIPPAGE_PCT", "0.03"))
SIM_FUNDING_COST_PCT = float(os.getenv("SIM_FUNDING_COST_PCT", "0.0"))
SIM_AMBIGUOUS_BAR_POLICY = os.getenv("SIM_AMBIGUOUS_BAR_POLICY", "STOP_FIRST").strip().upper()
RISK_ENGINE_ENABLED = os.getenv("RISK_ENGINE_ENABLED", "false").lower() == "true"
RISK_KILL_SWITCH = os.getenv("RISK_KILL_SWITCH", "false").lower() == "true"
RISK_MAX_DAILY_R = float(os.getenv("RISK_MAX_DAILY_R", "5.0"))
RISK_MAX_WEEKLY_R = float(os.getenv("RISK_MAX_WEEKLY_R", "12.0"))
RISK_MAX_CONSECUTIVE_STOPS = int(float(os.getenv("RISK_MAX_CONSECUTIVE_STOPS", "5")))
RISK_MAX_TOTAL_OPEN = int(float(os.getenv("RISK_MAX_TOTAL_OPEN", "20")))
RISK_MAX_SAME_SIDE = int(float(os.getenv("RISK_MAX_SAME_SIDE", "12")))
RISK_MAX_GROUP = int(float(os.getenv("RISK_MAX_GROUP", "4")))
VALIDATION_MIN_CLOSED = int(float(os.getenv("VALIDATION_MIN_CLOSED", "100")))

# === V12.1.0 ÖLÇÜM BÜTÜNLÜĞÜ ===
# Eski veri aynı dosyada korunur; yeni ölçümler build/config ile ayrılır.

# V12.1.0: tüm seçenekler yapılandırma kimliğine girer.
SCORE_MODE = os.getenv("SCORE_MODE", "EVIDENCE").upper()
SCORE_CVD_SOURCE = os.getenv("SCORE_CVD_SOURCE", "AUTO").upper()
SCORE_FIB_ENABLED = os.getenv("SCORE_FIB_ENABLED", "true").lower() == "true"
SPOOF_SOURCE = os.getenv("SPOOF_SOURCE", "AUTO").upper()
SPOOF_CACHE_SEC = float(os.getenv("SPOOF_CACHE_SEC", "20"))
WASH_GUARD_BLOCK = os.getenv("WASH_GUARD_BLOCK", "false").lower() == "true"
TIME_EXIT_MODE = os.getenv("TIME_EXIT_MODE", "HARD").upper()
TIME_EXIT_MAX_HOURS = float(os.getenv("TIME_EXIT_MAX_HOURS", "0"))
LIQ_EVENTS_ENABLED = os.getenv("LIQ_EVENTS_ENABLED", "false").lower() == "true"
MEXC_ENABLED = os.getenv("MEXC_ENABLED", "false").lower() == "true"
MEXC_BASE_URL = os.getenv("MEXC_BASE_URL", "https://contract.mexc.com").rstrip("/")
MEXC_REFRESH_SEC = float(os.getenv("MEXC_REFRESH_SEC", "15"))
MEXC_STALE_SEC = float(os.getenv("MEXC_STALE_SEC", "45"))
MEXC_HTTP_TIMEOUT = float(os.getenv("MEXC_HTTP_TIMEOUT", "8"))

RSI_METHOD = os.getenv("RSI_METHOD", "WILDER").strip().upper()
ENTRY_MAX_AGE_SEC = float(os.getenv("ENTRY_MAX_AGE_SEC", "5"))
BALINA_WS_BOOK_CHANNEL = os.getenv("BALINA_WS_BOOK_CHANNEL", "books").strip()
BALINA_THRESHOLD_REFRESH_SEC = float(os.getenv("BALINA_THRESHOLD_REFRESH_SEC", "1"))
BALINA_RETENTION_INTERVAL_SEC = float(os.getenv("BALINA_RETENTION_INTERVAL_SEC", "3600"))
BALINA_WS_FAIL_POLICY = os.getenv("BALINA_WS_FAIL_POLICY", "REST").strip().upper()
REPORT_REQUIRE_COMPLETE = os.getenv("REPORT_REQUIRE_COMPLETE", "true").lower() == "true"
CORRELATION_UNKNOWN_SHARED = os.getenv("CORRELATION_UNKNOWN_SHARED", "false").lower() == "true"
REPORT_CURRENT_COHORT_ONLY = os.getenv("REPORT_CURRENT_COHORT_ONLY", "true").lower() == "true"
VALIDATION_START_TS = float(os.getenv("VALIDATION_START_TS", "0"))
PAPER_HISTORY_MAX_PAGES = int(os.getenv("PAPER_HISTORY_MAX_PAGES", "24"))
PAPER_SECOND_BARS = os.getenv("PAPER_SECOND_BARS", "true").lower() == "true"
NOTIFICATION_INTERVAL_SEC = float(os.getenv("NOTIFICATION_INTERVAL_SEC", "1.1"))

# === CANLI BALINA AKIŞ MOTORU ===
BALINA_MOTOR_ENABLED = os.getenv("BALINA_MOTOR_ENABLED", "false").lower() == "true"
BALINA_MOTOR_BLOCK = os.getenv("BALINA_MOTOR_BLOCK", "false").lower() == "true"
BALINA_KARLI_KAPI_ENABLED = os.getenv("BALINA_KARLI_KAPI_ENABLED", "false").lower() == "true"
BALINA_KARLI_DURUMLAR = {
    x.strip().upper() for x in os.getenv(
        "BALINA_KARLI_DURUMLAR",
        "SATIS_EMILIMI,BALINA_ALIMI,BALINA_SATISI",
    ).split(",") if x.strip()
}
BALINA_WS_URL = os.getenv("BALINA_WS_URL", "wss://ws.okx.com:8443/ws/v5/public").strip()
BALINA_RECONNECT_MAX_SEC = float(os.getenv("BALINA_RECONNECT_MAX_SEC", "60"))
BALINA_STALE_SEC = float(os.getenv("BALINA_STALE_SEC", "20"))
BALINA_TRADE_WINDOW_SEC = int(float(os.getenv("BALINA_TRADE_WINDOW_SEC", "900")))
BALINA_BOOK_DEPTH = int(float(os.getenv("BALINA_BOOK_DEPTH", "20")))
BALINA_WHALE_PERCENTILE = float(os.getenv("BALINA_WHALE_PERCENTILE", "99"))
BALINA_WHALE_MIN_USDT = float(os.getenv("BALINA_WHALE_MIN_USDT", "25000"))
BALINA_CLUSTER_WINDOW_SEC = float(os.getenv("BALINA_CLUSTER_WINDOW_SEC", "15"))
BALINA_CLUSTER_MIN_COUNT = int(float(os.getenv("BALINA_CLUSTER_MIN_COUNT", "3")))
BALINA_WALL_MULT = float(os.getenv("BALINA_WALL_MULT", "3.0"))
BALINA_WALL_LIFETIME_SEC = float(os.getenv("BALINA_WALL_LIFETIME_SEC", "8"))
BALINA_SPOOF_CANCEL_RATIO = float(os.getenv("BALINA_SPOOF_CANCEL_RATIO", "0.80"))
BALINA_SPOOF_ENABLED = os.getenv("BALINA_SPOOF_ENABLED", "true").lower() == "true"
BALINA_WALL_MIN_USDT = float(os.getenv("BALINA_WALL_MIN_USDT", "25000"))
BALINA_SPOOF_CONFIRM_SEC = float(os.getenv("BALINA_SPOOF_CONFIRM_SEC", "2.0"))
BALINA_SPOOF_MIN_MISSING = int(float(os.getenv("BALINA_SPOOF_MIN_MISSING", "3")))
BALINA_SPOOF_MAX_DISTANCE_PCT = float(os.getenv("BALINA_SPOOF_MAX_DISTANCE_PCT", "0.5"))
BALINA_SNAPSHOT_SEC = float(os.getenv("BALINA_SNAPSHOT_SEC", "1"))
BALINA_DB = os.getenv("BALINA_DB", "balina_akis.db").strip()
BALINA_DB_FLUSH_SEC = float(os.getenv("BALINA_DB_FLUSH_SEC", "2"))
BALINA_EVENT_RETENTION_HOURS = float(os.getenv("BALINA_EVENT_RETENTION_HOURS", "168"))
BALINA_FLOW_MIN_TRADES_1M = int(float(os.getenv("BALINA_FLOW_MIN_TRADES_1M", "20")))
BALINA_FLOW_MIN_VOLUME_1M_USDT = float(os.getenv("BALINA_FLOW_MIN_VOLUME_1M_USDT", "10000"))
BALINA_FLOW_MIN_AGE_SEC = float(os.getenv("BALINA_FLOW_MIN_AGE_SEC", "120"))
BALINA_FLOW_MIN_15S_TRADES = int(float(os.getenv("BALINA_FLOW_MIN_15S_TRADES", "5")))
BALINA_NO_WHALE_MAX_CONFIDENCE = float(os.getenv("BALINA_NO_WHALE_MAX_CONFIDENCE", "55"))
BALINA_CLASSIFY_MIN_CONFIDENCE = float(os.getenv("BALINA_CLASSIFY_MIN_CONFIDENCE", "45"))

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

for _file_path in (LOG_FILE, MEMORY_FILE, OLCUM_DB, BALINA_DB):
    os.makedirs(os.path.dirname(os.path.abspath(_file_path)), exist_ok=True)

# V12.1: eski veri salt okunur arşiv, yeni defter ayrı dosyalardadır.
ESKI_OLCUM_DB = os.path.abspath(os.getenv("ESKI_OLCUM_DB", OLCUM_DB))
ESKI_MEMORY_FILE = os.path.abspath(os.getenv("ESKI_MEMORY_FILE", MEMORY_FILE))
ESKI_BALINA_DB = os.path.abspath(os.getenv("ESKI_BALINA_DB", BALINA_DB))
def _yeni_yol(path, suffix):
    base, ext = os.path.splitext(os.path.abspath(path))
    return base + suffix + ext
OLCUM_DB = os.path.abspath(os.getenv("YENI_OLCUM_DB", _yeni_yol(OLCUM_DB, "_v12_1")))
MEMORY_FILE = os.path.abspath(os.getenv("YENI_MEMORY_FILE", _yeni_yol(MEMORY_FILE, "_v12_1")))
BALINA_DB = os.path.abspath(os.getenv("YENI_BALINA_DB", _yeni_yol(BALINA_DB, "_v12_1")))
for _new in (OLCUM_DB, MEMORY_FILE, BALINA_DB):
    if os.path.realpath(_new) in {os.path.realpath(p) for p in (ESKI_OLCUM_DB, ESKI_MEMORY_FILE, ESKI_BALINA_DB)}:
        raise RuntimeError("Yeni ve eski dosya yolları aynı olamaz; arşiv korunmalıdır")
DB_BACKUP_DIR = os.path.join(DB_BACKUP_DIR, "v12_1")
GIZLI_ENABLED = os.getenv("GIZLI_ENABLED", "true").lower() == "true"
GIZLI_TELEGRAM_ENABLED = os.getenv("GIZLI_TELEGRAM_ENABLED", "false").lower() == "true"
GIZLI_MAX_OPEN = int(os.getenv("GIZLI_MAX_OPEN", "400"))
GIZLI_MIN_OI_PCT = float(os.getenv("GIZLI_MIN_OI_PCT", "1"))
GIZLI_GEREKLI_KAPILAR = tuple(x.strip() for x in os.getenv("GIZLI_GEREKLI_KAPILAR", "coin_1h_ema").split(",") if x.strip())
HISTORY_SETTLE_SEC = max(1, int(os.getenv("HISTORY_SETTLE_SEC", "5")))
TAKIP_SAAT = float(os.getenv("TAKIP_SAAT", "48"))
# Yeni defterde TP1 tam kapanış; eski kademeli ayarlar kullanılmaz.
TP1_WEIGHT, TP2_WEIGHT, TP3_WEIGHT, TP4_WEIGHT = 1.0, 0.0, 0.0, 0.0
PAPER_SECOND_BARS = True
SIM_AMBIGUOUS_BAR_POLICY = "STOP_FIRST"

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
                penalty = max(0.0, _OKX_CEZA["kadar"] - simdi)
                self._tokens = min(self.burst, self._tokens + (simdi - self._last) * self._etkin_rate())
                self._last = simdi
                if self._tokens >= 1.0 and penalty <= 0:
                    self._tokens -= 1.0
                    return
                eksik = max(penalty, (1.0 - self._tokens) / self._etkin_rate())
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
    remaining = max(1.0, OKX_CALL_BUDGET_SEC)
    for attempt in range(max(0, max_retries) + 1):
        # Kuyruk/bucket beklemesi network bütçesine dahil değildir.
        await _okx_kova(path).acquire()
        await _OKX_SLOTS.acquire()
        began = loop.time()
        future = loop.run_in_executor(OKX_EXECUTOR, _okx_get, path, params, 0)
        # wait_for thread'i durdurmaz: slot gerçek iş bitene kadar tutulur.
        def completed(f):
            _OKX_SLOTS.release()
            if not f.cancelled():
                f.exception()  # Timeout sonrasında gelen hata da tüketilir.
        future.add_done_callback(completed)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=remaining)
        except asyncio.TimeoutError:
            stats["okx_timeout"] = int(stats.get("okx_timeout", 0)) + 1
            raise
        except (OKXRequestError, requests.RequestException, ValueError) as exc:
            remaining -= loop.time() - began
            retryable = isinstance(exc, (requests.Timeout, requests.ConnectionError)) or getattr(exc, "retryable", False)
            if not retryable or attempt >= max_retries or remaining <= 0:
                raise
            await asyncio.sleep(max(0.5 * (attempt + 1), getattr(exc, "retry_after", 0)))


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
    "balina_ws_connect": 0, "balina_ws_disconnect": 0,
    "balina_ws_message": 0, "balina_trade": 0, "balina_whale": 0,
    "balina_spoof": 0, "balina_db_fail": 0, "balina_red_conflict": 0,
    "balina_red_karli_kapi": 0,
    "risk_reject": 0, "data_quality_reject": 0, "db_integrity_fail": 0,
    "backup_success": 0, "backup_fail": 0, "health_alert": 0,
}

app = None
memory_lock = asyncio.Lock()
v10_last_alert: Dict[str, float] = {}
v10_sent_candle: Dict[str, str] = {}
_v107_stop_kilit: Dict[str, float] = {}

_V106_BTC_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}

_BALINA_LOCK = threading.RLock()
_BALINA_STATE: Dict[str, Dict[str, Any]] = {}
_BALINA_DB_QUEUE: Optional[asyncio.Queue] = None
_RUNTIME_HEALTH: Dict[str, Any] = {
    "started_ts": time.time(), "scan_heartbeat": 0.0, "paper_heartbeat": 0.0,
    "shadow_heartbeat": 0.0, "save_heartbeat": 0.0, "last_backup_ts": 0.0,
    "last_integrity_ts": 0.0, "last_health_alert_ts": 0.0,
    "db_integrity": "BILINMIYOR", "emergency_stop": False,
}
_BALINA_WS_STATUS: Dict[str, Any] = {
    "connected": False, "last_message_ts": 0.0, "last_error": "",
    "connected_ts": 0.0, "subscriptions": 0,
}

OLCUM_KAPILARI = (
    "btc_hiza", "wash", "pump", "yapi", "range", "fomo",
    "coin_1h_ema", "pullback", "session", "vwap", "mtf", "vwm",
    "spoof", "rsi", "oi_yorum", "kayma", "korelasyon",
)
_OLCUM_DB_LOCK = threading.RLock()


def config_fingerprint() -> str:
    prefixes = ('V10_', 'V106_', 'V107_', 'V109_', 'TP', 'SABIT_', 'OLCUM_',
                'BALINA_', 'RISK_', 'SIM_', 'GOLGE_', 'ADX_', 'VWAP_', 'MTF_',
                'RSI_', 'ENTRY_', 'PAPER_', 'CORRELATION_', 'SESSION_', 'SPOOF_',
                'WASH_', 'PUMP_', 'INSIDER_', 'VWM_', 'TIME_EXIT_', 'COIN_',
                'HISTORY_', 'TAKIP_', 'MIN_24H_', 'MAX_24H_', 'EXCLUDE_', 'ADAPTIVE_', 'DATA_', 'SCORE_', 'MEXC_', 'LIQ_')
    values = {}
    for key,value in list(globals().items()):
        if not key.startswith(prefixes) or any(x in key for x in ('TOKEN','SECRET','KEY','URL','DB')):
            continue
        if isinstance(value,(str,int,float,bool)):
            values[key] = value
        elif isinstance(value,(tuple,list,set)) and all(isinstance(x,(str,int,float,bool)) for x in value):
            values[key] = sorted(value) if isinstance(value,set) else list(value)
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()[:16]


def audit_yaz(event_type: str, uid: str = "", symbol: str = "",
              payload: Optional[Dict[str, Any]] = None) -> None:
    if not AUDIT_ENABLED or not os.path.exists(OLCUM_DB):
        return
    try:
        with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
            conn.execute(
                "INSERT INTO audit_event(ts,event_type,uid,symbol,build,config_hash,payload_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (time.time(), str(event_type), str(uid), str(symbol), BOT_BUILD,
                 config_fingerprint(), json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)),
            )
    except Exception as e:
        logger.warning("Audit yazılamadı: %s", e)


def olcum_db_init() -> None:
    db_dizin = os.path.dirname(os.path.abspath(OLCUM_DB))
    os.makedirs(db_dizin, exist_ok=True)
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
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
            "sonuc_tipi": "TEXT",
            "position_json": "TEXT", "shadow_json": "TEXT", "cohort": "TEXT",
            "golge_durum": "TEXT",
            "golge_tp": "INTEGER",
            "golge_mfe_pct": "REAL",
            "golge_mae_pct": "REAL",
            "golge_tp1_dk": "REAL",
            "golge_tp2_dk": "REAL",
            "golge_tp3_dk": "REAL",
            "golge_tp4_dk": "REAL",
            "golge_bitis_ts": "REAL",
            "stop_neden_json": "TEXT",
            "net_r_value": "REAL",
            "cost_r": "REAL",
            "build": "TEXT",
            "config_hash": "TEXT",
        }
        for kolon, tur in yeni_kolonlar.items():
            if kolon not in mevcut_kolonlar:
                conn.execute(f"ALTER TABLE olcum_pozisyon ADD COLUMN {kolon} {tur}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_olcum_durum ON olcum_pozisyon(durum)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_olcum_sonuc_tipi ON olcum_pozisyon(sonuc_tipi)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_olcum_open_ts ON olcum_pozisyon(open_ts)")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)",
                     (str(DB_SCHEMA_VERSION),))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
                event_type TEXT NOT NULL, uid TEXT, symbol TEXT,
                build TEXT, config_hash TEXT, payload_json TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_event(ts)")
        conn.execute("""CREATE TABLE IF NOT EXISTS notification_outbox (
            event_id TEXT PRIMARY KEY, uid TEXT NOT NULL, kind TEXT NOT NULL,
            payload TEXT NOT NULL, created_ts REAL NOT NULL, sent_ts REAL,
            attempts INTEGER NOT NULL DEFAULT 0, next_ts REAL NOT NULL DEFAULT 0,
            last_error TEXT, part_index INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_pending ON notification_outbox(sent_ts,next_ts,created_ts)")
        conn.execute("INSERT OR IGNORE INTO schema_meta VALUES('v12_0_1_started',?)", (str(time.time()),))
        eski_sonuclar = conn.execute(
            "SELECT uid,durum,kapi_json FROM olcum_pozisyon WHERE sonuc_tipi IS NULL AND durum!='ACIK'"
        ).fetchall()
        for uid, durum, raw_json in eski_sonuclar:
            try:
                payload = json.loads(raw_json or "{}")
            except Exception:
                payload = {}
            sonuc_tipi = sonuc_tipi_belirle(durum, payload)
            conn.execute("UPDATE olcum_pozisyon SET sonuc_tipi=? WHERE uid=?", (sonuc_tipi, uid))


def pozisyon_ozellikleri(pos: Dict[str, Any]) -> Dict[str, Any]:
    giris = str(pos.get("entry_kaynak", "") or "").lower()
    if "orderbook" in giris:
        giris = "orderbook"
    elif "mum" in giris:
        giris = "mum"
    elif "kapan" in giris:
        giris = "kapanis"
    yapi = "RANGE kırılımı" if pos.get("range_break") else pos.get("event")
    return {
        "yapi_tipi": yapi,
        "1h_trend": pos.get("trend_1h"), "4h_trend": pos.get("trend_4h"),
        "btc_1h": pos.get("btc_1h"), "btc_4h": pos.get("btc_4h"),
        "coin_1h_ema": pos.get("coin_1h_ema"), "session_name": pos.get("session_name"),
        "piyasa_modu": pos.get("piyasa_modu"),
        "giris_tipi": giris or None, "yon": pos.get("side"),
        "kontrol": int(bool(pos.get("kontrol"))),
        "skor": pos.get("score"), "rsi": pos.get("rsi"), "adx": pos.get("adx"),
        "vwm": pos.get("vwm"), "oi_pct": pos.get("oi_change_pct"),
        "fomo_pct": pos.get("fomo_move_pct"), "obimb": pos.get("ob_imbalance"),
        "funding": None if pos.get("funding") is None else safe_float(pos.get("funding"))*100,
        "balina_durum": pos.get("balina_durum"),
        "balina_guven": pos.get("balina_guven"),
        "balina_veri_kaynagi": pos.get("balina_veri_kaynagi"),
        "balina_cvd_1m": (pos.get("balina_akis") or {}).get("cvd_norm_1m"),
        "balina_whale_1m": (pos.get("balina_akis") or {}).get("whale_count_1m"),
        "balina_spoof_1m": (pos.get("balina_akis") or {}).get("spoof_1m"),
        "signal_no": pos.get("signal_no"),
        "build": BOT_BUILD, "config_hash": config_fingerprint(),
    }


def olcum_db_pozisyon_ac(pos: Dict[str, Any]) -> None:
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        _db_insert_position(conn, pos)


def simulasyon_maliyet_r(pos: Dict[str, Any]) -> float:
    if "cost_r_frozen" in pos:
        return max(0.0, safe_float(pos["cost_r_frozen"]))
    risk_pct = abs(safe_float(pos.get("entry")) - safe_float(pos.get("orig_stop")))
    entry = safe_float(pos.get("entry"))
    if entry <= 0 or risk_pct <= 0:
        return 0.0
    risk_pct = risk_pct / entry * 100.0
    toplam_maliyet_pct = max(0.0, SIM_FEE_RATE_PCT) * 2.0 + max(0.0, SIM_SLIPPAGE_PCT) + max(0.0, SIM_FUNDING_COST_PCT)
    return round(toplam_maliyet_pct / risk_pct, 6)


def olcum_db_pozisyon_guncelle(pos: Dict[str, Any], durum: str = "ACIK",
                               r_value: Optional[float] = None) -> None:
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        _db_update_position(conn, pos, durum, r_value)


def sonuc_tipi_belirle(outcome: str, kaynak: Dict[str, Any]) -> str:
    if outcome == "TP1":
        return "TP1_TAM"
    if outcome == "TP4":
        return "TP4_TAM"
    if outcome == "TIME_EXIT":
        return "TIME_EXIT"
    if outcome == "STOP":
        en_yuksek = max((idx for idx in range(1, 5)
                         if bool(kaynak.get(f"_hit{idx}", kaynak.get(f"hit{idx}", False)))), default=0)
        return f"TP{min(en_yuksek, 3)}_STOP" if en_yuksek else "TEMIZ_STOP"
    return str(outcome or "")


def olcum_db_sonuc_tipi_yaz(pos: Dict[str, Any], outcome: str) -> None:
    if not os.path.exists(OLCUM_DB):
        return
    payload = {f"hit{idx}": bool(pos.get(f"hit{idx}")) for idx in range(1, 5)}
    sonuc_tipi = sonuc_tipi_belirle(outcome, payload)
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("UPDATE olcum_pozisyon SET sonuc_tipi=? WHERE uid=?",
                     (sonuc_tipi, v107_pos_uid(pos)))


def olcum_db_ortak_satirlari() -> List[Dict[str, Any]]:
    if not os.path.exists(OLCUM_DB):
        return []
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        rows = conn.execute("""
            SELECT uid,side,kontrol,durum,r_value,mfe_pct,mae_pct,sonuc_tipi,kapi_json,cohort,net_r_value,open_ts,close_ts
            FROM olcum_pozisyon
        """).fetchall()
    sonuc = []
    for uid, side, kontrol, durum, r_value, mfe_pct, mae_pct, sonuc_tipi, raw_json, cohort, net_r, open_ts, close_ts in rows:
        try:
            payload = json.loads(raw_json or "{}")
        except Exception:
            payload = {}
        ozellikler = payload.get("_ozellikler") if isinstance(payload.get("_ozellikler"), dict) else {}
        ozellikler.setdefault("yon", side)
        ozellikler.setdefault("kontrol", int(kontrol or 0))
        kapilar = {ad: payload.get(ad) for ad in OLCUM_KAPILARI if payload.get(ad) in ("gecti", "kesti")}
        sonuc.append({"uid": uid, "side": side, "kontrol": int(kontrol or 0),
                      "durum": durum, "r_value": safe_float(r_value), "mfe_pct": safe_float(mfe_pct),
                      "mae_pct": safe_float(mae_pct),
                      "sonuc_tipi": sonuc_tipi,
                      "hit1": bool(payload.get("_hit1")), "hit2": bool(payload.get("_hit2")),
                      "hit3": bool(payload.get("_hit3")), "hit4": bool(payload.get("_hit4")),
                      "ozellikler": ozellikler,
                      "kapilar": kapilar, "cohort": cohort or "LEGACY", "net_r_value": net_r,
                      "open_ts": open_ts, "close_ts": close_ts, "coverage": payload.get("_coverage","LEGACY_UNVERIFIED")})
    return sonuc


def olcum_db_golge_baslat(pos: Dict[str, Any]) -> None:
    if not GOLGE_IZLEME or not os.path.exists(OLCUM_DB):
        return
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        stop_neden = {
            "symbol": pos.get("symbol"), "side": pos.get("side"),
            "entry": pos.get("entry"), "stop": pos.get("orig_stop"),
            "score": pos.get("score"), "event": pos.get("event"),
            "trend_1h": pos.get("trend_1h"), "trend_4h": pos.get("trend_4h"),
            "btc_1h": pos.get("btc_1h"), "btc_4h": pos.get("btc_4h"),
            "coin_1h_ema": pos.get("coin_1h_ema"), "rsi": pos.get("rsi"),
            "adx": pos.get("adx"), "vwm": pos.get("vwm"),
            "oi_pct": pos.get("oi_change_pct"), "fomo_pct": pos.get("fomo_move_pct"),
            "obimb": pos.get("ob_imbalance"), "funding": pos.get("funding"),
            "session": pos.get("session_name"), "piyasa_modu": pos.get("piyasa_modu"),
            "balina_durum": pos.get("balina_durum"), "balina_guven": pos.get("balina_guven"),
            "kapilar": pos.get("kapi_sonuclari", {}),
            "mfe_stop_oncesi": pos.get("mfe_pct"), "mae_stop_oncesi": pos.get("mae_pct"),
        }
        conn.execute("""
            UPDATE olcum_pozisyon
            SET golge_durum='IZLENIYOR', golge_tp=0, golge_mfe_pct=0,
                golge_mae_pct=0, golge_tp1_dk=NULL, golge_tp2_dk=NULL,
                golge_tp3_dk=NULL, golge_tp4_dk=NULL, golge_bitis_ts=NULL,
                stop_neden_json=?
            WHERE uid=?
        """, (json.dumps(stop_neden, ensure_ascii=False, sort_keys=True), v107_pos_uid(pos)))
    audit_yaz("SHADOW_START", v107_pos_uid(pos), pos.get("symbol", ""), stop_neden)


def olcum_db_golge_guncelle(golge: Dict[str, Any], bitti: bool=False) -> None:
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute("""UPDATE olcum_pozisyon SET golge_durum=?,
            golge_tp=MAX(COALESCE(golge_tp,0),?),golge_mfe_pct=MAX(COALESCE(golge_mfe_pct,0),?),
            golge_mae_pct=MAX(COALESCE(golge_mae_pct,0),?),
            golge_tp1_dk=COALESCE(golge_tp1_dk,?),golge_tp2_dk=COALESCE(golge_tp2_dk,?),
            golge_tp3_dk=COALESCE(golge_tp3_dk,?),golge_tp4_dk=COALESCE(golge_tp4_dk,?),
            golge_bitis_ts=?,shadow_json=? WHERE uid=? AND COALESCE(golge_durum,'')!='BITTI'""",
            ('BITTI' if bitti else 'IZLENIYOR',int(golge.get('golge_tp',0)),
             safe_float(golge.get('golge_mfe_pct')),safe_float(golge.get('golge_mae_pct')),
             *(golge.get(f'golge_tp{i}_dk') for i in range(1,5)),
             golge.get('end_ts') if bitti else None,_json(golge),golge['uid']))


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
        result = float(v)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError, OverflowError):
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
    memory.setdefault("signal_seq", 0)
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
    target = os.path.abspath(MEMORY_FILE)
    os.makedirs(os.path.dirname(target),exist_ok=True)
    temp = target+'.'+uuid.uuid4().hex+'.tmp'
    try:
        with open(temp,'w',encoding='utf-8') as stream:
            json.dump(snapshot,stream,ensure_ascii=False,indent=2,allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

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
    """JSON ve SQLite birlikte kurtarma sağlar; ölçüm alanları asla atılmaz."""
    return copy.deepcopy(memory)

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
        raise TelegramDeliveryError(401)
    response = _http_session().post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}, timeout=HTTP_TIMEOUT)
    data = response.json()
    if response.status_code != 200 or data.get("ok") is not True:
        raise TelegramDeliveryError(int(data.get("error_code", response.status_code)),
                                    (data.get("parameters") or {}).get("retry_after", 0))
    return True

async def safe_send_telegram(text: str, retry: int = 3, delay_sec: float = 1.5) -> bool:
    for part in telegram_parcala(text):
        for attempt in range(retry):
            try:
                await asyncio.to_thread(_telegram_api_send, part)
                break
            except Exception as exc:
                if getattr(exc, "permanent", False) or attempt+1 == retry:
                    stats["telegram_fail"] += 1
                    return False
                await asyncio.sleep(max(delay_sec*(attempt+1), getattr(exc, "retry_after", 0)))
    return True

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

        if SIGNAL_CHART_FIB:
            fib = fibonacci_context(_s_closed(rows), d)
            for ratio, level in fib.get("levels", {}).items():
                ax.axhline(level, color="#eab308", linestyle=":", linewidth=0.7, alpha=0.5)
                ax.text(0, level, "Fib " + ratio, fontsize=6, color="#eab308")
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


def _okx_get(path: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 0) -> Any:
    """Tek network denemesi. Rate limit, retry ve bekleme event loop'tadır."""
    response = _http_session().get(f"{OKX_BASE_URL}{path}", params=params or {},
                                   timeout=(min(HTTP_TIMEOUT, 5), HTTP_TIMEOUT))
    if response.status_code == 429:
        _okx_429_kaydet()
        raise OKXRequestError("HTTP 429", retryable=True,
                              retry_after=safe_float(response.headers.get("Retry-After"), OKX_429_CEZA_SEC))
    if response.status_code >= 500:
        raise OKXRequestError(f"HTTP {response.status_code}", retryable=True)
    response.raise_for_status()
    data = response.json()
    code = str(data.get("code", "1"))
    if code != "0":
        if code in ("50011", "50040"):
            _okx_429_kaydet()
        raise OKXRequestError(f"OKX code={code}", code=code,
                              retryable=code in ("50011", "50040", "50013", "50004"),
                              retry_after=OKX_429_CEZA_SEC if code in ("50011", "50040") else 0)
    return data.get("data", [])


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
            stats["empty_kline"] = int(stats.get("empty_kline", 0)) + 1
            return []
        note_symbol_success(symbol)
        kline_cache[cache_key] = (now_ts, rows)
        _kline_cache_buda()
        return rows
    except Exception as e:
        stats["api_fail"] += 1
        # Geçici timeout/429 bütün coin'i, özellikle BTC'yi, bloke etmez.
        if isinstance(e, OKXRequestError) and e.code in ("51001", "51008"):
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
    if RSI_METHOD == "WILDER":
        return _rsi_wilder(values, period)
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
#  CANLI BALINA AKIŞ MOTORU — yalnız BALINA_MOTOR_ENABLED=true iken çalışır
# ============================================================================

def _balina_yuzdelik(values: List[float], q: float) -> float:
    return yuzdelik(values,q)


def _balina_symbol_state(symbol: str) -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    with _BALINA_LOCK:
        state = _BALINA_STATE.get(symbol)
        if state is None:
            state = {
                "trades": deque(maxlen=12000),
                "whales": deque(maxlen=2000),
                "books": {"bids": {}, "asks": {}}, "book_full": {"bids": {}, "asks": {}}, "book_seq": None,
                "walls": {}, "spoofs": deque(maxlen=200),
                "trade_ids": deque(), "trade_id_set": set(),
                "last_price": 0.0, "last_ts": 0.0,
                "first_ts": 0.0, "last_book_ts": 0.0, "snapshot": {},
            }
            _BALINA_STATE[symbol] = state
        return state


def balina_db_init() -> None:
    if not BALINA_MOTOR_ENABLED:
        return
    os.makedirs(os.path.dirname(os.path.abspath(BALINA_DB)), exist_ok=True)
    with sqlite3.connect(BALINA_DB, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS balina_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                symbol TEXT NOT NULL,
                event_type TEXT NOT NULL,
                side TEXT,
                price REAL,
                value_usdt REAL,
                payload_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS balina_snapshot (
                symbol TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                durum TEXT NOT NULL,
                guven REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_balina_event_ts ON balina_event(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_balina_event_symbol_ts ON balina_event(symbol,ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_balina_event_type_ts ON balina_event(event_type,ts)")


def _balina_queue_event(event: Dict[str, Any]) -> None:
    q = _BALINA_DB_QUEUE
    if not BALINA_MOTOR_ENABLED or q is None:
        return
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        stats["balina_db_fail"] = int(stats.get("balina_db_fail", 0)) + 1


def _balina_contract_value(symbol: str, price: float, size: float) -> float:
    inst = okx_live_symbols.get(symbol,{})
    ct = safe_float(inst.get('ctVal'))*safe_float(inst.get('ctMult'),1.0)
    currency = str(inst.get('ctValCcy','')).upper()
    if ct<=0 or size<=0 or price<=0:
        return 0.0
    if currency==_base_of(symbol):
        return price*size*ct
    if currency in ('USD','USDT','USDC'):
        return size*ct
    return 0.0


def _balina_prune(state: Dict[str, Any], now_ts: float) -> None:
    cutoff = now_ts - max(60, BALINA_TRADE_WINDOW_SEC)
    for key in ("trades", "whales"):
        dq = state[key]
        while dq and safe_float(dq[0].get("ts")) < cutoff:
            dq.popleft()


def _balina_whale_threshold(state: Dict[str, Any]) -> float:
    now = time.monotonic()
    if now-safe_float(state.get('threshold_ts'),-1e20)<BALINA_THRESHOLD_REFRESH_SEC:
        return state['threshold']
    values = [safe_float(x.get('value')) for x in itertools.islice(reversed(state['trades']),2000)]
    threshold = max(BALINA_WHALE_MIN_USDT,_balina_yuzdelik(values,BALINA_WHALE_PERCENTILE/100)) if len(values)>=30 else BALINA_WHALE_MIN_USDT
    state.update(threshold_ts=now,threshold=threshold)
    return threshold


def _balina_process_trade(row: Dict[str, Any]) -> None:
    symbol = normalize_symbol(str(row.get("instId", "")))
    price = safe_float(row.get("px"))
    size = safe_float(row.get("sz"))
    ts = safe_float(row.get("ts")) / 1000.0
    side = str(row.get("side", "")).lower()
    if not symbol or price <= 0 or size <= 0 or side not in ("buy", "sell"):
        return
    now_ts = ts if ts > 0 else time.time()
    value = _balina_contract_value(symbol, price, size)
    if value<=0:
        stats['balina_missing_contract'] = int(stats.get('balina_missing_contract',0))+1
        return
    state = _balina_symbol_state(symbol)
    with _BALINA_LOCK:
        if now_ts<safe_float(state.get('last_ts')):
            stats['balina_out_of_order_trade'] = int(stats.get('balina_out_of_order_trade',0))+1
            return
        if len(state['trades'])==state['trades'].maxlen and state['trades'][0]['ts']>now_ts-300:
            state['truncated_until'] = now_ts+300
        trade_id = str(row.get("tradeId") or f"{row.get('ts')}:{side}:{price:.12g}:{size:.12g}")
        if trade_id in state["trade_id_set"]:
            stats["balina_duplicate_trade"] = int(stats.get("balina_duplicate_trade", 0)) + 1
            return
        if len(state["trade_ids"]) >= 5000:
            eski_id = state["trade_ids"].popleft()
            state["trade_id_set"].discard(eski_id)
        state["trade_ids"].append(trade_id)
        state["trade_id_set"].add(trade_id)
        trade = {"ts": now_ts, "side": side, "price": price, "size": size, "value": value}
        state["trades"].append(trade)
        state["last_price"] = price
        state["last_ts"] = max(safe_float(state.get("last_ts")), now_ts)
        if safe_float(state.get("first_ts")) <= 0:
            state["first_ts"] = now_ts
        else:
            state["first_ts"] = min(safe_float(state.get("first_ts")), now_ts)
        _balina_prune(state, now_ts)
        threshold = _balina_whale_threshold(state)
        if value >= threshold:
            trade["threshold"] = threshold
            state["whales"].append(dict(trade))
            stats["balina_whale"] = int(stats.get("balina_whale", 0)) + 1
            _balina_queue_event({"ts": now_ts, "symbol": symbol, "event_type": "WHALE_TRADE",
                                 "side": side, "price": price, "value_usdt": value,
                                 "threshold": threshold})
    stats["balina_trade"] = int(stats.get("balina_trade", 0)) + 1


def _balina_trade_near(state: Dict[str, Any], side: str, price: float,
                       since_ts: float, tolerance_pct: float = 0.05) -> float:
    if price <= 0:
        return 0.0
    tol = tolerance_pct / 100.0
    return sum(safe_float(t.get("value")) for t in state["trades"]
               if t.get("side") == side and safe_float(t.get("ts")) >= since_ts
               and abs(safe_float(t.get("price")) - price) / price <= tol)


def _balina_process_book(row: Dict[str, Any], action: str='snapshot') -> None:
    symbol = normalize_symbol(str(row.get('instId','')))
    ts = safe_float(row.get('ts'))/1000
    if not symbol or ts<=0:
        return
    state = _balina_symbol_state(symbol)
    with _BALINA_LOCK:
        if ts<safe_float(state.get('last_book_ts')):
            stats['balina_out_of_order_book'] = int(stats.get('balina_out_of_order_book',0))+1
            return
        seq,prev = row.get('seqId'),row.get('prevSeqId')
        if action=='update' and (state.get('book_seq') is None or prev!=state.get('book_seq')):
            stats['balina_book_gap'] = int(stats.get('balina_book_gap',0))+1
            raise ValueError('Orderbook sequence gap: yeni snapshot gerekli')
        if action=='snapshot':
            state['book_full'] = {'bids':{},'asks':{}}
            if BALINA_WS_BOOK_CHANNEL=='books':
                state['walls'].clear()
        state['book_seq'] = seq
        for side in ('bids','asks'):
            full = state['book_full'][side]
            for level in row.get(side,[]):
                p,q = safe_float(level[0]),safe_float(level[1])
                if p<=0 or q<0:
                    continue
                if q==0:
                    full.pop(p,None)
                else:
                    full[p] = q
            ordered = sorted(full.items(),reverse=side=='bids')[:400]
            state['book_full'][side] = dict(ordered)
            depth = min(BALINA_BOOK_DEPTH,5) if BALINA_WS_BOOK_CHANNEL=='books5' else BALINA_BOOK_DEPTH
            state['books'][side] = dict(ordered[:max(1,depth)])
        state['last_book_ts'] = ts
        tol = max(0,SPOOF_FIYAT_TOLERANS_PCT)/100
        for key,wall in list(state['walls'].items()):
            side,p = wall['side'],wall['price']
            levels = state['books'][side]
            # Görünür aralık DIŞINDA kalan duvar için iptal kanıtı yoktur.
            if not levels or not min(levels)<=p<=max(levels):
                state['walls'].pop(key,None)
                continue
            qty = sum(q for px,q in levels.items() if abs(px-p)/p<=tol)
            peak = max(safe_float(wall.get('max_qty')),qty)
            wall.update(last_qty=qty,max_qty=peak,last_ts=ts)
            drop = 1-qty/peak if peak else 0
            if drop<BALINA_SPOOF_CANCEL_RATIO:
                wall.pop('missing_since',None)
                wall.pop('missing_count',None)
                continue
            wall.setdefault('missing_since',ts)
            wall['missing_count'] = int(wall.get('missing_count',0))+1
            if ts-wall['missing_since']<BALINA_SPOOF_CONFIRM_SEC or wall['missing_count']<max(2,BALINA_SPOOF_MIN_MISSING):
                continue
            state['walls'].pop(key,None)
            value = _balina_contract_value(symbol,p,peak)
            executed = _balina_trade_near(state,'sell' if side=='bids' else 'buy',p,wall['first_ts'])
            unexplained = clamp(drop-executed/value,0,1) if value>0 else 0
            bid = max(state['books']['bids'] or {0:0})
            ask = min(state['books']['asks'] or {0:0})
            mid = (bid+ask)/2 if bid>0 and ask>0 else 0
            distance = abs(p-mid)/mid*100 if mid else 999
            life = wall['missing_since']-wall['first_ts']
            if (BALINA_SPOOF_ENABLED and life>=BALINA_WALL_LIFETIME_SEC and value>=BALINA_WALL_MIN_USDT
                    and distance<=BALINA_SPOOF_MAX_DISTANCE_PCT and unexplained>=BALINA_SPOOF_CANCEL_RATIO):
                event = {'ts':ts,'symbol':symbol,'event_type':'SPOOF_WALL','side':side,'price':p,
                         'value_usdt':value,'lifetime':life,'cancel_ratio':unexplained,
                         'interpretation':'unexplained_depth_reduction_not_proof'}
                state['spoofs'].append(event)
                stats['balina_spoof'] = int(stats.get('balina_spoof',0))+1
                _balina_queue_event(event)
        # Ortalama eşiği SADECE yeni duvar tespitinde; mevcut duvarı silmez.
        for side,levels in state['books'].items():
            mean = avg(list(levels.values()))
            for p,q in levels.items():
                if mean<=0 or q<mean*BALINA_WALL_MULT:
                    continue
                if any(w['side']==side and abs(w['price']-p)/p<=tol for w in state['walls'].values()):
                    continue
                band_qty = sum(qty for px,qty in levels.items() if abs(px-p)/p<=tol)
                state['walls'][f'{side}:{p:.12g}'] = dict(side=side,price=p,first_ts=ts,last_ts=ts,max_qty=band_qty,last_qty=band_qty)


def _balina_window_metrics(state: Dict[str, Any], seconds: float, now_ts: float) -> Dict[str, float]:
    windows = tuple(sorted(set((5,15,60,300,seconds))))
    cached = state.get('_window_cache')
    if not cached or cached[0]!=now_ts or seconds not in cached[1]:
        data = {s:dict(buy=0.0,sell=0.0,count=0,first=None,last=None) for s in windows}
        for trade in reversed(state['trades']):
            age = now_ts-safe_float(trade.get('ts'))
            if age>max(windows):
                break
            if age<0:
                continue
            for s,m in data.items():
                if age<=s:
                    m[trade['side']]+=trade['value']; m['count']+=1
                    m['first']=trade['price']
                    if m['last'] is None:
                        m['last']=trade['price']
        for m in data.values():
            total=m['buy']+m['sell']; cvd=m['buy']-m['sell']
            m.update(total=total,cvd=cvd,cvd_norm=cvd/total if total else 0,
                     price_move_pct=pct_change(m['first'],m['last']) if m['first'] else 0)
        state['_window_cache']=(now_ts,data)
    return state['_window_cache'][1][seconds]


def balina_snapshot(symbol: str) -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    if not BALINA_MOTOR_ENABLED:
        return {"enabled": False, "source": "REST", "status": "KAPALI",
                "durum": "OLCUMSUZ", "guven": 0.0}
    now_ts = time.time()
    state = _balina_symbol_state(symbol)
    with _BALINA_LOCK:
        stale = (not _BALINA_WS_STATUS.get('connected') or
                 now_ts-safe_float(state.get('last_ts'))>BALINA_STALE_SEC or
                 now_ts-safe_float(state.get('last_book_ts'))>BALINA_STALE_SEC or
                 safe_float(state.get('truncated_until'))>now_ts)
        cached = state.get('snapshot') or {}
        if cached and now_ts-safe_float(cached.get('ts'))<BALINA_SNAPSHOT_SEC and not stale:
            return copy.deepcopy(cached)
        m5 = _balina_window_metrics(state, 5, now_ts)
        m15 = _balina_window_metrics(state, 15, now_ts)
        m60 = _balina_window_metrics(state, 60, now_ts)
        m300 = _balina_window_metrics(state, 300, now_ts)
        whales = [w for w in state["whales"] if safe_float(w.get("ts")) >= now_ts - 60]
        whale_buy = sum(safe_float(w.get("value")) for w in whales if w.get("side") == "buy")
        whale_sell = sum(safe_float(w.get("value")) for w in whales if w.get("side") == "sell")
        whale_total = whale_buy + whale_sell
        whale_cvd_norm = (whale_buy - whale_sell) / whale_total if whale_total > 0 else 0.0
        clustered_buy = sum(1 for w in whales if w.get("side") == "buy" and
                            safe_float(w.get("ts")) >= now_ts - BALINA_CLUSTER_WINDOW_SEC)
        clustered_sell = sum(1 for w in whales if w.get("side") == "sell" and
                             safe_float(w.get("ts")) >= now_ts - BALINA_CLUSTER_WINDOW_SEC)
        bids = state["books"].get("bids", {})
        asks = state["books"].get("asks", {})
        bid_qty, ask_qty = sum(bids.values()), sum(asks.values())
        book_imb = (bid_qty - ask_qty) / (bid_qty + ask_qty) if bid_qty + ask_qty > 0 else 0.0
        recent_spoof = [x for x in state["spoofs"] if safe_float(x.get("ts")) >= now_ts - 60]

        durum = "BELIRSIZ"
        guven = 0.0
        akis_yasi = max(0.0, now_ts - safe_float(state.get("first_ts"), now_ts))
        count_factor = clamp(m60["count"] / max(1, BALINA_FLOW_MIN_TRADES_1M), 0.0, 1.0)
        volume_factor = clamp(m60["total"] / max(1.0, BALINA_FLOW_MIN_VOLUME_1M_USDT), 0.0, 1.0)
        age_factor = clamp(akis_yasi / max(1.0, BALINA_FLOW_MIN_AGE_SEC), 0.0, 1.0)
        short_factor = clamp(m15["count"] / max(1, BALINA_FLOW_MIN_15S_TRADES), 0.0, 1.0)
        veri_kalitesi = 100.0 * (0.35 * count_factor + 0.35 * volume_factor +
                                0.20 * age_factor + 0.10 * short_factor)
        flow_ready = (m60["count"] >= BALINA_FLOW_MIN_TRADES_1M and
                      m60["total"] >= BALINA_FLOW_MIN_VOLUME_1M_USDT and
                      akis_yasi >= BALINA_FLOW_MIN_AGE_SEC and
                      m15["count"] >= BALINA_FLOW_MIN_15S_TRADES)
        same_flow_sign = (m15["cvd_norm"] * m60["cvd_norm"] > 0 and
                          abs(m15["cvd_norm"]) >= 0.15)
        if stale:
            durum = "VERI_YETERSIZ"
        else:
            absorption_sell = (flow_ready and same_flow_sign and m60["cvd_norm"] < -0.25 and
                               m60["price_move_pct"] > -0.15)
            absorption_buy = (flow_ready and same_flow_sign and m60["cvd_norm"] > 0.25 and
                              m60["price_move_pct"] < 0.15)
            accumulation = (flow_ready and same_flow_sign and abs(m300["price_move_pct"]) < 0.8 and
                            m300["cvd_norm"] > 0.18)
            distribution = (flow_ready and same_flow_sign and abs(m300["price_move_pct"]) < 0.8 and
                            m300["cvd_norm"] < -0.18)
            if clustered_buy >= BALINA_CLUSTER_MIN_COUNT and whale_cvd_norm > 0.35:
                durum = "PARCALI_BALINA_ALIMI"
                guven = min(95.0, 60.0 + clustered_buy * 5.0 + whale_cvd_norm * 15.0)
            elif clustered_sell >= BALINA_CLUSTER_MIN_COUNT and whale_cvd_norm < -0.35:
                durum = "PARCALI_BALINA_SATISI"
                guven = min(95.0, 60.0 + clustered_sell * 5.0 + abs(whale_cvd_norm) * 15.0)
            elif absorption_sell:
                durum = "SATIS_EMILIMI"
                guven = min(90.0, (45.0 + abs(m60["cvd_norm"]) * 45.0) * veri_kalitesi / 100.0)
            elif absorption_buy:
                durum = "ALIS_EMILIMI"
                guven = min(90.0, (45.0 + abs(m60["cvd_norm"]) * 45.0) * veri_kalitesi / 100.0)
            elif accumulation:
                durum = "BIRIKIM"
                guven = min(88.0, (45.0 + m300["cvd_norm"] * 60.0) * veri_kalitesi / 100.0)
            elif distribution:
                durum = "DAGITIM"
                guven = min(88.0, (45.0 + abs(m300["cvd_norm"]) * 60.0) * veri_kalitesi / 100.0)
            elif whale_cvd_norm > 0.35 and whale_total > 0:
                durum = "BALINA_ALIMI"
                guven = min(85.0, 45.0 + whale_cvd_norm * 50.0)
            elif whale_cvd_norm < -0.35 and whale_total > 0:
                durum = "BALINA_SATISI"
                guven = min(85.0, 45.0 + abs(whale_cvd_norm) * 50.0)
            elif not flow_ready:
                durum = "AKIS_YETERSIZ"
                guven = min(40.0, veri_kalitesi * 0.4)
            if whale_total <= 0 and durum not in ("VERI_YETERSIZ", "AKIS_YETERSIZ", "BELIRSIZ"):
                guven = min(guven, BALINA_NO_WHALE_MAX_CONFIDENCE)
            if durum not in ("VERI_YETERSIZ", "AKIS_YETERSIZ", "BELIRSIZ") and guven < BALINA_CLASSIFY_MIN_CONFIDENCE:
                durum = "AKIS_ZAYIF"
        out = {
            "enabled": True, "source": "WEBSOCKET" if _BALINA_WS_STATUS.get("connected") else "WS_YOK",
            "status": "BAYAT" if stale else "CANLI", "symbol": symbol,
            "ts": now_ts, "durum": durum, "guven": round(guven, 1),
            "cvd_5s": round(m5["cvd"], 2), "cvd_15s": round(m15["cvd"], 2),
            "cvd_1m": round(m60["cvd"], 2), "cvd_5m": round(m300["cvd"], 2),
            "cvd_norm_1m": round(m60["cvd_norm"], 4),
            "price_move_1m_pct": round(m60["price_move_pct"], 4),
            "trade_count_15s": int(m15["count"]), "trade_count_1m": int(m60["count"]),
            "trade_volume_1m_usdt": round(m60["total"], 2),
            "flow_age_sec": round(akis_yasi, 1), "data_quality": 0.0 if stale else round(veri_kalitesi, 1),
            "flow_ready": flow_ready,
            "whale_buy_1m": round(whale_buy, 2), "whale_sell_1m": round(whale_sell, 2),
            "whale_count_1m": len(whales), "whale_cvd_norm": round(whale_cvd_norm, 4),
            "book_imbalance": round(book_imb, 4), "active_walls": len(state["walls"]),
            "spoof_1m": len(recent_spoof), "last_data_age_sec": round(max(0.0,now_ts - safe_float(state.get("last_ts"))), 2),
        }
        state["snapshot"] = out
        return copy.deepcopy(out)


def _balina_db_flush_sync(events: List[Dict[str, Any]], snapshots: List[Dict[str, Any]]) -> None:
    global _BALINA_LAST_RETENTION
    if not events and not snapshots:
        return
    with sqlite3.connect(BALINA_DB, timeout=10) as conn:
        if events:
            conn.executemany("""
                INSERT INTO balina_event(ts,symbol,event_type,side,price,value_usdt,payload_json)
                VALUES(?,?,?,?,?,?,?)
            """, [(safe_float(e.get("ts")), str(e.get("symbol", "")), str(e.get("event_type", "")),
                    str(e.get("side", "")), safe_float(e.get("price")), safe_float(e.get("value_usdt")),
                    json.dumps(e, ensure_ascii=False, separators=(",", ":"))) for e in events])
        for snap in snapshots:
            conn.execute("""
                INSERT INTO balina_snapshot(symbol,ts,durum,guven,payload_json)
                VALUES(?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET
                ts=excluded.ts,durum=excluded.durum,guven=excluded.guven,payload_json=excluded.payload_json
            """, (str(snap.get("symbol", "")), safe_float(snap.get("ts")), str(snap.get("durum", "")),
                  safe_float(snap.get("guven")), json.dumps(snap, ensure_ascii=False, separators=(",", ":"))))
        now = time.time()
        retention = now-_BALINA_LAST_RETENTION>=BALINA_RETENTION_INTERVAL_SEC
        if retention:
            cutoff = now-max(1.0,BALINA_EVENT_RETENTION_HOURS)*3600
            conn.execute('DELETE FROM balina_event WHERE ts < ?',(cutoff,))
    if retention:
        _BALINA_LAST_RETENTION = now


async def balina_db_loop() -> None:
    global _BALINA_DB_QUEUE
    if _BALINA_DB_QUEUE is None:
        _BALINA_DB_QUEUE = asyncio.Queue(maxsize=20000)
    pending = []
    try:
        while True:
            await asyncio.sleep(max(0.5,BALINA_DB_FLUSH_SEC))
            try:
                while len(pending)<2000:
                    pending.append(_BALINA_DB_QUEUE.get_nowait())
            except asyncio.QueueEmpty:
                pass
            snapshots = []
            for symbol in list(_BALINA_STATE):
                snapshots.append(balina_snapshot(symbol))
                await asyncio.sleep(0)
            try:
                await asyncio.to_thread(_balina_db_flush_sync,pending,snapshots)
                pending.clear()
            except Exception:
                stats['balina_db_fail'] = int(stats.get('balina_db_fail',0))+1
                logger.exception('Balina DB yazılamadı; batch yeniden denenecek')
    finally:
        for event in pending:
            _balina_queue_event(event)


async def _balina_ws_subscribe(ws, symbols: List[str]) -> None:
    args = [{"channel": "liquidation-orders", "instType": "SWAP"}] if LIQ_EVENTS_ENABLED else []
    for symbol in symbols:
        args.append({"channel": "trades", "instId": symbol})
        args.append({"channel": BALINA_WS_BOOK_CHANNEL, "instId": symbol})
    for i in range(0, len(args), 40):
        await ws.send(json.dumps({"op": "subscribe", "args": args[i:i + 40]}, separators=(",", ":")))
        await asyncio.sleep(0.2)
    _BALINA_WS_STATUS["subscriptions"] = len(args)


async def _balina_ws_change_symbols(ws, old_symbols: set, new_symbols: set) -> None:
    for op, symbols in (("unsubscribe", sorted(old_symbols - new_symbols)),
                        ("subscribe", sorted(new_symbols - old_symbols))):
        args = []
        for symbol in symbols:
            args.extend(({"channel": "trades", "instId": symbol},
                         {"channel": BALINA_WS_BOOK_CHANNEL, "instId": symbol}))
        for i in range(0, len(args), 40):
            await ws.send(json.dumps({"op": op, "args": args[i:i + 40]}, separators=(",", ":")))
            await asyncio.sleep(0.2)
    for symbol in old_symbols-new_symbols:
        _BALINA_STATE.pop(symbol,None)
    _BALINA_WS_STATUS["subscriptions"] = len(new_symbols) * 2 + int(LIQ_EVENTS_ENABLED)


async def balina_ws_loop() -> None:
    if not BALINA_MOTOR_ENABLED:
        return
    try:
        import websockets
    except Exception:
        _BALINA_WS_STATUS["last_error"] = "websockets paketi kurulu değil"
        logger.error("Balina motoru için 'websockets' paketi gerekli")
        raise
    backoff = 1.0
    while True:
        try:
            symbols = [normalize_symbol(s) for s in list(COINS)[:MA_COIN_LIMIT]]
            async with websockets.connect(BALINA_WS_URL, ping_interval=15, ping_timeout=10,
                                          close_timeout=5, max_queue=20000) as ws:
                _BALINA_STATE.clear()  # Kopuk aralık için yeni ısınma/snapshot gerekir.
                _BALINA_WS_STATUS.update({"connected": True, "connected_ts": time.time(),
                                          "last_error": "", "last_message_ts": time.time()})
                stats["balina_ws_connect"] = int(stats.get("balina_ws_connect", 0)) + 1
                await _balina_ws_subscribe(ws, symbols)
                subscribed = set(symbols)
                last_symbol_check = time.time()
                backoff = 1.0
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(),timeout=20)
                    except asyncio.TimeoutError:
                        await ws.send('ping')
                        raw = await asyncio.wait_for(ws.recv(),timeout=10)
                    _BALINA_WS_STATUS["last_message_ts"] = time.time()
                    stats["balina_ws_message"] = int(stats.get("balina_ws_message", 0)) + 1
                    if raw == "pong":
                        continue
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    if msg.get('event')=='error':
                        raise RuntimeError('OKX WS error '+str(msg.get('code')))
                    channel = str((msg.get("arg") or {}).get("channel", ""))
                    inst_id = str((msg.get("arg") or {}).get("instId", ""))
                    for row in msg.get("data", []):
                        if inst_id and "instId" not in row:
                            row["instId"] = inst_id
                        if channel == "liquidation-orders":
                            _process_liquidation_report(row)
                        elif channel == "trades":
                            _balina_process_trade(row)
                        elif channel == BALINA_WS_BOOK_CHANNEL:
                            _balina_process_book(row,msg.get("action","snapshot"))
                    if time.time() - last_symbol_check >= 30.0:
                        current = {normalize_symbol(s) for s in list(COINS)[:MA_COIN_LIMIT]}
                        if current != subscribed:
                            await _balina_ws_change_symbols(ws, subscribed, current)
                            subscribed = current
                        last_symbol_check = time.time()
        except asyncio.CancelledError:
            _BALINA_WS_STATUS["connected"] = False
            raise
        except Exception as exc:
            stats["balina_ws_disconnect"] = int(stats.get("balina_ws_disconnect", 0)) + 1
            _BALINA_WS_STATUS.update({"connected": False, "last_error": str(exc)[:220]})
            logger.warning("Balina WebSocket koptu; REST devam ediyor: %s", exc)
            await asyncio.sleep(min(max(1.0, backoff), BALINA_RECONNECT_MAX_SEC))
            backoff = min(max(2.0, backoff * 2.0), BALINA_RECONNECT_MAX_SEC)


def balina_signal_ekle(sig: Dict[str, Any]) -> Dict[str, Any]:
    if not BALINA_MOTOR_ENABLED:
        return sig
    snap = balina_snapshot(str(sig.get("symbol", "")))
    sig["balina_akis"] = snap
    sig["balina_durum"] = snap.get("durum", "VERI_YETERSIZ")
    sig["balina_guven"] = snap.get("guven", 0.0)
    sig["balina_veri_kaynagi"] = snap.get("source", "WS_YOK")
    return sig


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


def likidasyon_haritasi(symbol, klines, oi_value):
    out = {"clusters": [], "top_bid_cluster": 0.0, "top_ask_cluster": 0.0,
           "estimated": True, "can_block": False, "model": "DISTANCE_BANDS",
           "note": "Giriş fiyatı ve kaldıraç dağılımı bilinmiyor; küme büyüklüğü hesaplanamaz."}
    if not LIQ_HEATMAP_ENABLED or not klines:
        return out
    price = safe_float(klines[-1][4])
    if price <= 0:
        return out
    for lev in LIQ_HEATMAP_LEVERAGES:
        if lev <= 0:
            continue
        distance = 100/lev-.5
        if not 0 < distance <= LIQ_HEATMAP_DIST_PCT:
            continue
        for side, sign in (("LONG_LIQ", -1), ("SHORT_LIQ", 1)):
            out["clusters"].append({"side": side, "price": price*(1+sign*distance/100),
                                    "value": None, "lev": lev, "assumed_maintenance_pct": .5})
    return out


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
        key = "v113_would_mtf" if OLCUM_MODU else "v113_red_mtf"
        stats[key] = int(stats.get(key,0))+1
        return False, "MTF veri yok", 0
    if onay < MTF_MIN_AGREE:
        key = "v113_would_mtf" if OLCUM_MODU else "v113_red_mtf"
        stats[key] = int(stats.get(key,0))+1
        return False, f"MTF onay yok ({onay}/{olculen})", onay
    return True, " ".join(detay), onay


def korelasyon_grubu(symbol: str) -> str:
    """Basit korelasyon grubu tahmini."""
    base = _base_of(symbol)
    if base in _correlation_group_cache:
        return _correlation_group_cache[base]
    grup = "diğer" if CORRELATION_UNKNOWN_SHARED else f"sınıflanmamış:{base}"
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
        key = "v113_would_correlation" if OLCUM_MODU else "v113_red_correlation"
        stats[key] = int(stats.get(key,0))+1
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
                         if i > res["last_sh_idx"] + V10_SWING_RIGHT and cls[i - 1] <= res["last_sh"] < cls[i]), -1) if res["last_sh"] > 0 else -1
    down_break_idx = next((i for i in range(len(cls) - 1, recent_start - 1, -1)
                           if i > res["last_sl_idx"] + V10_SWING_RIGHT and cls[i - 1] >= res["last_sl"] > cls[i]), -1) if res["last_sl"] > 0 else -1
    if up_break_idx >= 0 and up_break_idx > down_break_idx:
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


def _legacy_quality_score(side, k, ms, ext):
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


async def _legacy_spoof_tespit(symbol: str, force: bool = False) -> Tuple[bool, str]:
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
            return True, f"hacim/fiyat anomalisi (hacim {son_vol/ort_vol:.1f}x, fiyat %{fiyat_degisim:.2f})"
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
    """Analiz fiyatı; kesin paper giriş ayrıca taze bid/ask ile alınır."""
    mid = safe_float((ob or {}).get("mid"))
    if mid > 0:
        return mid, "orderbook"
    if k1h and safe_float(k1h[-1][4]) > 0:
        return safe_float(k1h[-1][4]), "canli mum"
    return 0.0, "veri yok"


def v10_structure_gate(symbol, k1h, k4h, allowed_side=None):
    k = _s_closed(k1h)
    if len(k) < 40:
        return None
    ms = v10_market_structure(k)
    if not ms.get('event_side'):
        stats['v10_red_yapi'] = int(stats.get('v10_red_yapi',0))+1
        return None
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
                stats["v10_red_4h"] = int(stats.get("v10_red_4h",0))+1
                continue
            if side == "SHORT" and trend4 != "DOWN":
                stats["v10_red_4h"] = int(stats.get("v10_red_4h",0))+1
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
            stats["v10_red_pullback"] = int(stats.get("v10_red_pullback",0))+1
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
    yapisal_yon = "LONG" if ms.get("event_side") == "UP" else "SHORT" if ms.get("event_side") == "DOWN" else None

    # Kontrol seçimi symbol+mum için sabittir. Aynı mum tekrar tarandığında
    # kontrol/normal veya LONG/SHORT arasında yeniden kura çekilmez.
    kontrol_anahtari = f"{symbol}|{k[-1][0]}".encode("utf-8")
    kontrol_ozeti = hashlib.sha256(kontrol_anahtari).digest()
    kontrol_degeri = int.from_bytes(kontrol_ozeti[:8], "big") / float(1 << 64)
    kontrol = kontrol_degeri < clamp(OLCUM_RASTGELE_ORAN, 0.0, 1.0)
    if not kontrol and not yapisal_yon:
        stats["v10_red_yapi"] = int(stats.get("v10_red_yapi", 0)) + 1
        return None
    side = ("LONG" if kontrol_ozeti[8] % 2 == 0 else "SHORT") if kontrol else yapisal_yon
    entry_ref = closes(k)[-1]

    bt = await v106_btc_trend()
    btc_1h, btc_4h = bt.get("dir_1h", "FLAT"), bt.get("dir_4h", "FLAT")
    allowed_side = bt.get("allow")
    wash_hit, wash_note = v112_wash_tespit(symbol, k, force=True)
    tickers24 = await get_24h_tickers()
    pump_hit, pump_note = v112_pump_dump_tespit(symbol, k, tickers24, force=True)
    k4h = await get_klines(symbol, "4H", 120, ttl=180)
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
    if entry <= 0:
        stats["v10_red_veri"] += 1
        return None
    kayma = abs(entry - entry_ref) / entry_ref * 100.0 if entry_ref > 0 else 0.0
    kor_block, _ = korelasyon_kilidi(symbol, side, force=True)
    ext = {"oi_change_pct": oi, "funding": funding,
           "btc_dir": btc_4h, "btc_dir_1h": btc_1h, "orderbook": ob}
    ext.update(await score_market_context(symbol, k, side))
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
                "spoof_ok": None if spoof_hit is None or spoof_note in ("hata", "veri yok", "yetersiz", "kapalı") else not spoof_hit,
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
            "event": ms.get("event"), "structure": "Rastgele kontrol grubu" if kontrol else v10_structure_allows(side, ms)[1],
            "range_break": bool(ms.get("range_break")), "trend_1h": ms.get("trend", "RANGE"),
            "trend_4h": trend4, "fomo_move_pct": round(fomo_mv, 2), "pullback": pb_note or "yok",
            "score": score, "score_parts": parts, "bayrak": bayrak, "market_context": ext.get("market_context", {}), "rsi": r_value,
            "candle_ts": str(k[-1][0]), "oi_change_pct": oi, "oi_yorum": oi_yorum,
            "coin_1h_ema": coin_yon, "funding": funding, "ob_imbalance": ob.get("imbalance", 0),
            "btc_4h": btc_4h, "btc_1h": btc_1h, "trend_uyum": allowed_side == side,
            "spoof_guard": spoof_note, "wash_guard": wash_note, "pump_guard": pump_note,
            "insider_uyari": insider_note if insider_hit else "", "stop_hunt": stop_hunt_note if stop_hunt_hit else "",
            "adx": round(adx_hesapla(k, ADX_PERIOD), 2), "piyasa_modu": _adx_regime(adx_hesapla(k, ADX_PERIOD)),
            "session_name": session_name, "session_weight": session_weight,
            "vwap": round(vwap_v, 8) if vwap_v else 0.0, "mtf_note": mtf_note,
            "mtf_count": mtf_count, "vwm": round(vwm_val, 3), "liq_map": liq_map,
            "liq_note": "tahmini — bilgi amaçlı", "kapi_sonuclari": kapilar,
            "kontrol": kontrol, **size, **tgt}


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
    wash_hit, wash_note = v112_wash_tespit(symbol, _s_closed(k1h))
    if wash_hit and WASH_GUARD_BLOCK:
        stats["v112_red_wash"] = int(stats.get("v112_red_wash", 0)) + 1
        return None

    tickers24 = await get_24h_tickers()
    pump_hit, pump_note = v112_pump_dump_tespit(symbol, _s_closed(k1h), tickers24)
    if pump_hit:
        stats["v112_red_pump_dump"] = int(stats.get("v112_red_pump_dump", 0)) + 1
        return None

    k4h = await get_klines(symbol, "4H", 120, ttl=180) if V10_USE_4H_FILTER else None
    gate = v10_structure_gate(symbol, k1h, k4h, allowed_side)
    if not gate:
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

    ext = {"oi_change_pct": oi,
           "funding": funding, "btc_dir": btc_4h, "btc_dir_1h": btc_1h,
           "orderbook": ob}

    ext.update(await score_market_context(symbol, k, side))
    score, parts, r, bayrak = v10_quality_score(side, k, gate["ms"], ext)
    if SCORE_MODE == "LEGACY" and ((side == "LONG" and gate.get("trend4") == "UP") or
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
            "score": score, "score_parts": parts, "bayrak": bayrak, "market_context": ext.get("market_context", {}), "rsi": r,
            "candle_ts": str(k[-1][0]), "oi_change_pct": ext["oi_change_pct"],
            "oi_yorum": ext.get("oi_yorum", ""),
            "coin_1h_ema": gate.get("coin_1h_ema", "-"),
            "funding": funding, "ob_imbalance": ob.get("imbalance", 0),
            "btc_4h": btc_4h, "btc_1h": btc_1h,
            "trend_uyum": ((side == "LONG" and btc_1h == btc_4h == "UP") or (side == "SHORT" and btc_1h == btc_4h == "DOWN")),
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
                     tag("cvd", "CVD:" + sig.get("market_context", {}).get("score_cvd_source", "CANDLE_PROXY")), tag("sweep", "Sweep"), tag("orderbook", "OBflow")])
    fund = safe_float(sig.get("funding"))
    trend_line = ("🎲 KONTROL GRUBU — yön rastgele\n" if sig.get("kontrol") else
                  ("Trend Uyumu: BTC ile AYNI YÖN ✅\n" if sig.get("trend_uyum") else
                   "Trend Uyumu: normalde geçmezdi\n"))
    _kay = safe_float(sig.get("entry_kayma_pct"))
    kayma_mark = f" (mum kapanışından %{_kay:+.2f})" if abs(_kay) >= 0.05 else ""

    # V11.5 ek bilgiler
    savunma_lines = ["🛡 " + " | ".join(
        f"{label}: {sig.get(key, 'ölçümsüz')}" for label, key in
        (("Duvar anomalisi", "spoof_guard"), ("Hacim/fiyat", "wash_guard"), ("Ani hareket", "pump_guard")))]
    if sig.get("insider_uyari"):
        savunma_lines.append(f"⚠️ Hacim anomalisi: {sig['insider_uyari']}")
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
    balina_line = ""
    if BALINA_MOTOR_ENABLED:
        akis = sig.get("balina_akis") or {}
        balina_line = (f"🐋 Balina: {akis.get('durum', 'VERI_YETERSIZ')} | "
                       f"Güven {safe_float(akis.get('guven')):.0f}/100 | "
                       f"Kalite {safe_float(akis.get('data_quality')):.0f}/100 | "
                       f"CVD1m {safe_float(akis.get('cvd_norm_1m')):+.2f} | "
                       f"W:{int(safe_float(akis.get('whale_count_1m')))} | "
                       f"{akis.get('source', 'REST_YEDEK')}\n")

    signal_no_line = f"🆔 Sinyal #{int(safe_float(sig.get('signal_no')))}\n" if sig.get("signal_no") else ""
    return (f"{signal_no_line}{trend_line}"
            f"🎯 {VERSION_NAME}\n🆕 V12.1.0 | {sig['direction']} | {sig['symbol']}\n"
            f"Yapı: {sig['structure']} | 1H:{sig['trend_1h']} 4H:{sig['trend_4h']}\n"
            f"BTC: 1H:{sig.get('btc_1h','-')} 4H:{sig.get('btc_4h','-')}"
            + (f" | Coin 1H EMA: {sig.get('coin_1h_ema','-')}" if sig.get('coin_1h_ema') else "") + "\n"
            f"Skor: {sig['score']}/100  RSI:{sig['rsi']}\nConfluence: {conf}\n"
            + "\n".join([savunma_lines[0], vwap_line, adx_line, session_line, mtf_line, vwm_line, liq_line] +
                        savunma_lines[1:]) + "\n"
            f"{olcum_line}"
            f"{balina_line}"
            f"Paper kayıt saati: {tr_str(sig.get('accepted_ts'))}\n"
            f"Giriş: {_v10_fmt(sig['entry'])} [{sig.get('entry_kaynak','-')}]{kayma_mark}\n"
            f"Stop: {_v10_fmt(sig['stop'])} (%{sig['stop_pct']} sabit)\n"
            f"TP1 {_v10_fmt(sig['tp1'])} ({sig.get('tp1_rr', TP1_RR)}R) | TP2 {_v10_fmt(sig['tp2'])} ({sig.get('tp2_rr', TP2_RR)}R) | "
            f"TP3 {_v10_fmt(sig['tp3'])} ({sig.get('tp3_rr', TP3_RR)}R) | TP4 {_v10_fmt(sig['tp4'])} ({sig.get('tp4_rr', TP4_RR)}R)\n"
            f"Pullback: {sig['pullback']} | FOMO:%{sig['fomo_move_pct']}\n"
            f"OI%{round(safe_float(sig.get('oi_change_pct')),2)} ({sig.get('oi_yorum','-')}) Fund:{round(fund*100,4)}% OBimb:{round(safe_float(sig.get('ob_imbalance')),2)}\n"
            f"Pozisyon: {sig.get('position_multiplier',1)}x ayar | Marjin ≈{sig.get('margin_usdt',0)} USDT | Risk ≈{sig.get('estimated_risk_usdt',0)} USDT\n"
            f"TP1: %100 kapanış. Sonraki TP/stop yalnız izlemedir.\n⚠️ PAPER — risk %{V10_RISK_PCT}/işlem")


def build_v10_close_message(pos, R, outcome, exit_price):
    head = "✅ TP1 — %100 KAPANIŞ" if outcome=='TP1' else "❌ TP GÖRMEDEN STOP" if outcome=='STOP' else "⏱ SÜRE ÇIKIŞI"
    prefix = "GİZLİ " if pos.get('engine')=='GIZLI' else ""
    return (f"{prefix}{BOT_BUILD} | #{pos.get('signal_no',0)} | {pos['symbol']} {pos['side']}\n"
            f"{head}\nGiriş: {_v10_fmt(pos['entry'])} | Çıkış: {_v10_fmt(exit_price)}\n"
            f"Brüt sonuç: {R:+.3f}R | Net: {R-simulasyon_maliyet_r(pos):+.3f}R\n"
            "Sonraki fiyat takibi bu kapanış sonucunu değiştirmez.")


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


def v10_open_paper(sig, persist=True):
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
        "trend_1h": sig.get("trend_1h"), "trend_4h": sig.get("trend_4h"),
        "btc_1h": sig.get("btc_1h"), "btc_4h": sig.get("btc_4h"),
        "coin_1h_ema": sig.get("coin_1h_ema"),
        "rsi": sig.get("rsi"), "adx": sig.get("adx"), "vwm": sig.get("vwm"),
        "oi_change_pct": sig.get("oi_change_pct"), "fomo_move_pct": sig.get("fomo_move_pct"),
        "ob_imbalance": sig.get("ob_imbalance"), "funding": sig.get("funding"),
        "entry_kaynak": sig.get("entry_kaynak", "-"),
        "open_ts": safe_float(sig.get("accepted_ts"), time.time()), "scan_ts": 0.0, "candle_ts": sig["candle_ts"],
        "session_name": sig.get("session_name", "-"),
        "piyasa_modu": sig.get("piyasa_modu", "-"),
        "balina_durum": sig.get("balina_durum", "OLCUMSUZ"),
        "balina_guven": safe_float(sig.get("balina_guven")),
        "balina_veri_kaynagi": sig.get("balina_veri_kaynagi", "REST"),
        "balina_akis": copy.deepcopy(sig.get("balina_akis", {})),
        "signal_no": int(safe_float(sig.get("signal_no"))),
        "kapi_sonuclari": copy.deepcopy(sig.get("kapi_sonuclari", {})),
        "kontrol": bool(sig.get("kontrol")),
        "mfe_pct": 0.0, "mae_pct": 0.0, "current_r": 0.0,
    }
    poz["market_context"] = copy.deepcopy(sig.get("market_context", {}))
    poz["time_exit_policy"] = {"enabled": TIME_EXIT_ENABLED, "mode": TIME_EXIT_MODE,
        "hours": TIME_EXIT_HOURS, "min_r": TIME_EXIT_MIN_PROFIT_R, "max_hours": TIME_EXIT_MAX_HOURS}
    poz["tp_weights"] = _tp_weights()
    poz["tp_rrs"] = [safe_float(sig.get(f"tp{i}_rr"), rr) for i, rr in enumerate((TP1_RR, TP2_RR, TP3_RR, TP4_RR), 1)]
    poz["cost_r_frozen"] = simulasyon_maliyet_r(poz)
    poz["config_hash"] = config_fingerprint()
    poz["build"] = BOT_BUILD
    poz["cohort"] = _cohort()
    poz["coverage"] = "COMPLETE"
    poz["entry_ref"] = sig.get("entry_ref")
    if TIME_EXIT_ENABLED and TIME_EXIT_MODE=='HARD':
        poz['tracking_deadline']=float(math.ceil(poz['open_ts']+TIME_EXIT_HOURS*3600))
    if persist:
        olcum_db_pozisyon_ac(poz)
        mp["open"].append(poz)
    return poz


async def v107_takip_barlari(pos):
    tracking_tf = GOLGE_TF if pos.get('phase')=='AFTER_STOP' else V107_TAKIP_TF
    step = interval_minutes(tracking_tf)*60000
    now = int((time.time()-HISTORY_SETTLE_SEC)*1000)
    start = max(int(pos['open_ts']*1000), int(safe_float(pos.get('scan_ts'))))
    # Entry subsecond cannot be reconstructed by candles. Omit at most 999 ms explicitly.
    cursor = ((start+999)//1000)*1000
    if start%1000 and pos.get('coverage')=='COMPLETE':
        pos['coverage']='SUBSECOND_ENTRY_OMITTED'
    if pos.get('fetch_cutoff_ts') is not None:
        now=min(now,int(pos['fetch_cutoff_ts']*1000))
    limit = pos.get('tracking_deadline')
    if limit is not None:
        now = min(now, int(limit*1000))
    result=[]
    # Start/end partial minute uses closed seconds. Full minutes are refined at barriers.
    first_full=((cursor+step-1)//step)*step
    spans=[]
    if cursor<first_full:
        spans.append(('1s',cursor,min(first_full,now//1000*1000),1000))
    full_end=now//step*step
    if first_full<full_end:
        spans.append((tracking_tf,first_full,min(full_end,first_full+300*step),step))
    for tf,a,b,width in spans:
        if b<=a: continue
        raw, _ = await _history_range(pos['symbol'],tf,a,b,width)
        by_ts={int(r[0]):r for r in raw}
        t=a
        while t<b:
            if t not in by_ts:
                _history_gap(pos,t,b)
                return result,'eksik mum bekleniyor'
            row=by_ts[t]
            if width>1000:
                hi,lo=safe_float(row[2]),safe_float(row[3])
                barrier=pos.get('phase')!='AFTER_STOP' and (lo<=pos['orig_stop'] if pos['side']=='LONG' else hi>=pos['orig_stop'])
                observed=pos.get('shadow_hits',[]) if pos.get('phase')=='AFTER_STOP' else pos.get('follow_hits',[])
                barrier=barrier or any((hi>=pos[f'tp{i}'] if pos['side']=='LONG' else lo<=pos[f'tp{i}']) and i not in observed and (pos.get('phase')=='AFTER_STOP' or not pos.get(f'hit{i}')) for i in range(1,5))
                if barrier:
                    seconds,ok=await _history_range(pos['symbol'],'1s',t,t+width,1000)
                    sec={int(r[0]):r for r in seconds}
                    for s in range(t,t+width,1000):
                        if s not in sec:
                            _history_gap(pos,s,t+width)
                            return result,'çıkış saniyesi eksik'
                        result.append(sec[s])
                    pos.pop('history_gap',None)
                    return result,'eşik mumu saniyelerle doğrulandı'
            result.append(row)
            t+=width
    # At fixed tracking deadline include the last partial minute as seconds.
    last = int(result[-1][0])+int(result[-1][9]) if result else cursor
    if limit is not None and now>=int(limit*1000) and last<now and now-last<step:
        rows,_=await _history_range(pos['symbol'],'1s',last,now//1000*1000,1000)
        by_ts={int(r[0]):r for r in rows}
        for t in range(last,now//1000*1000,1000):
            if t not in by_ts:
                _history_gap(pos,t,now);return result,'son aralık eksik'
            result.append(by_ts[t])
    if result:
        pos.pop('history_gap',None)
    return result,V107_TAKIP_TF


def _tp_weights() -> List[float]:
    raw = [max(0.0, TP1_WEIGHT), max(0.0, TP2_WEIGHT),
           max(0.0, TP3_WEIGHT), max(0.0, TP4_WEIGHT)]
    total = sum(raw)
    return [x / total for x in raw] if total > 0 else [0.5, 0.3, 0.15, 0.05]


def _paper_realized_r(pos, stop_remaining):
    return float(pos['tp_rrs'][0]) if pos.get('hit1') else (-1.0 if stop_remaining else 0.0)


def _paper_time_exit_r(pos, current_r):
    return float(pos['tp_rrs'][0]) if pos.get('hit1') else current_r


def v107_check_paper_bar(pos, hi, lo):
    stop = lo <= pos['orig_stop'] if pos['side']=='LONG' else hi >= pos['orig_stop']
    hit = hi >= pos['tp1'] if pos['side']=='LONG' else lo <= pos['tp1']
    if stop:
        if hit:
            pos['ambiguous_exit'] = True
            stats['paper_ambiguous_bar'] = int(stats.get('paper_ambiguous_bar',0))+1
        return -1.0, 'STOP'
    if hit:
        pos['hit1'] = True
        pos['pending_hits'] = [1]
        return float(pos['tp_rrs'][0]), 'TP1'
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
    pos["current_r"] = round(_paper_time_exit_r(pos, move / risk), 6) if risk > 0 else 0.0


def v10_record_closed(pos, R, outcome):
    closed = _v10_mem()['closed']
    if not any(p.get('uid')==pos['uid'] for p in closed):
        closed.append(_closed_record(pos,R,outcome))


def v10_cooldown_ok(symbol):
    if OLCUM_MODU:
        return True
    return time.time() - v10_last_alert.get(symbol, 0) >= V10_ALERT_COOLDOWN_MIN * 60


def risk_durumu() -> Dict[str, Any]:
    mp = _v10_mem()
    simdi = time.time()
    gun_r = hafta_r = 0.0
    ardisik_stop = 0
    kapanan = []
    if os.path.exists(OLCUM_DB):
        try:
            with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
                kapanan = conn.execute(
                    "SELECT close_ts,COALESCE(net_r_value,r_value),sonuc_tipi "
                    "FROM olcum_pozisyon WHERE durum!='ACIK' ORDER BY close_ts DESC"
                ).fetchall()
        except Exception:
            kapanan = []
    gun_r = sum(safe_float(r[1]) for r in kapanan if simdi - safe_float(r[0]) <= 86400)
    hafta_r = sum(safe_float(r[1]) for r in kapanan if simdi - safe_float(r[0]) <= 7 * 86400)
    for _ts, _r, sonuc in kapanan:
        if sonuc == "TEMIZ_STOP":
            ardisik_stop += 1
        else:
            break
    side_counts = {side: sum(1 for p in mp.get("open", []) if p.get("side") == side)
                   for side in ("LONG", "SHORT")}
    return {"daily_r": gun_r, "weekly_r": hafta_r, "consecutive_stops": ardisik_stop,
            "open": len(mp.get("open", [])), "side_counts": side_counts,
            "kill_switch": bool(RISK_KILL_SWITCH or _RUNTIME_HEALTH.get("emergency_stop"))}


def risk_sinyal_uygun(symbol: str, side: str) -> Tuple[bool, str]:
    durum = risk_durumu()
    if durum["kill_switch"]:
        return False, "acil durdurma aktif"
    if not RISK_ENGINE_ENABLED:
        return True, "kapalı"
    if durum["daily_r"] <= -abs(RISK_MAX_DAILY_R):
        return False, f"günlük zarar limiti ({durum['daily_r']:+.2f}R)"
    if durum["weekly_r"] <= -abs(RISK_MAX_WEEKLY_R):
        return False, f"haftalık zarar limiti ({durum['weekly_r']:+.2f}R)"
    if durum["consecutive_stops"] >= RISK_MAX_CONSECUTIVE_STOPS:
        return False, f"ardışık temiz stop ({durum['consecutive_stops']})"
    if durum["open"] >= RISK_MAX_TOTAL_OPEN:
        return False, f"toplam açık sınırı ({durum['open']})"
    if durum["side_counts"].get(side, 0) >= RISK_MAX_SAME_SIDE:
        return False, f"{side} açık sınırı"
    grup = korelasyon_grubu(symbol)
    grup_sayi = sum(1 for p in _v10_mem().get("open", [])
                     if korelasyon_grubu(p.get("symbol", "")) == grup)
    if grup_sayi >= RISK_MAX_GROUP:
        return False, f"{grup} grup riski ({grup_sayi})"
    return True, "uygun"


def veri_kalitesi_uygun(sig: Dict[str, Any]) -> Tuple[bool, str]:
    if not DATA_QUALITY_BLOCK_ENABLED:
        return True, "ölçüm"
    if BALINA_MOTOR_ENABLED:
        akis = sig.get("balina_akis") or {}
        if akis.get("status") != "CANLI":
            return False, "balina verisi canlı değil"
        if safe_float(akis.get("last_data_age_sec"), 9999.0) > DATA_MAX_AGE_SEC:
            return False, "balina verisi eski"
    return True, "uygun"


async def maybe_send_v10_signal(sig):
    if not sig:
        return
    async with _SIGNAL_LOCK:
        symbol, side = sig["symbol"], sig["direction"]
        if any(v10_sent_candle.get(key) == sig["candle_ts"] for key in (symbol, f"{symbol}:{side}")):
            stats["duplicate_signal_skip"] = int(stats.get("duplicate_signal_skip", 0)) + 1
            return
        if not v10_cooldown_ok(symbol):
            stats["cooldown_skip"] = int(stats.get("cooldown_skip", 0)) + 1
            return
        mp = _v10_mem()
        if any(p.get('symbol')==symbol for p in mp.get('recovery_pending',[])):
            stats['recovery_symbol_block'] = int(stats.get('recovery_symbol_block',0))+1
            return
        if len(mp["open"]) >= (OLCUM_MAX_OPEN if OLCUM_MODU else V10_MAX_OPEN):
            stats["v107_red_defter_dolu"] += 1
            return
        if V107_ACIKKEN_ENGELLE and any(p.get("symbol") == symbol for p in mp["open"]):
            stats["v107_red_acik_poz"] += 1
            return
        risk_ok, risk_note = await _db_call(risk_sinyal_uygun, symbol, side)
        if not risk_ok:
            stats["risk_reject"] += 1
            await _db_call(audit_yaz, "RISK_REJECT", "", symbol, {"reason": risk_note})
            return
        # Filtrelerden önce taze snapshot; veri kalitesi boş sözlüğe bakmaz.
        balina_signal_ekle(sig)
        data_ok, data_note = veri_kalitesi_uygun(sig)
        if not data_ok:
            stats["data_quality_reject"] += 1
            return
        whale_ok, whale_note = _balina_gate(sig)
        sig["balina_gate"] = whale_note
        if not whale_ok and not OLCUM_MODU:
            stats["balina_red_karli_kapi"] += 1
            return
        if not whale_ok:
            stats["balina_would_reject"] = int(stats.get("balina_would_reject", 0)) + 1
        try:
            quote = await _live_entry_quote(symbol, side)
        except Exception:
            stats["entry_quote_fail"] = int(stats.get("entry_quote_fail", 0)) + 1
            logger.warning("Güncel giriş verisi yok: %s", symbol)
            return
        ref = safe_float(sig.get("entry_ref"))
        slip = abs(quote["price"]-ref)/ref*100 if ref > 0 else 0
        if not OLCUM_MODU and V107_MAX_GIRIS_KAYMA > 0 and slip > V107_MAX_GIRIS_KAYMA:
            stats["v107_red_kayma"] += 1
            return
        sig = copy.deepcopy(sig)
        sig.update(entry=quote["price"], entry_kaynak=quote["source"], accepted_ts=time.time(),
                   entry_quote_ts=quote["ts"], entry_kayma_pct=round(slip, 4))
        sig.update(v10_targets(side, sig["entry"]))
        sig.setdefault("kapi_sonuclari", {})["kayma"] = _kapi_durum(V107_MAX_GIRIS_KAYMA <= 0 or slip <= V107_MAX_GIRIS_KAYMA)
        pos = v10_open_paper(sig, persist=False)
        # Commit + outbox tek transaction: Telegram sonucu defteri belirlemez.
        try:
            pos = await _db_call(_persist_open, pos, sig)
        except Exception:
            stats["ledger_write_fail"] = int(stats.get("ledger_write_fail", 0)) + 1
            logger.exception("Sinyal kaydedilemedi: %s", symbol)
            return
        mp["open"].append(pos)
        memory["signal_seq"] = pos["signal_no"]
        v10_last_alert[symbol] = pos["open_ts"]
        v10_sent_candle[symbol] = sig["candle_ts"]
        stats["v10_signals"] += 1
        stats["last_signal"] = f"{BOT_BUILD} #{pos['signal_no']} {side} {symbol}"
        logger.info("Paper sinyal kaydedildi #%s %s %s", pos["signal_no"], side, symbol)


async def v10_scan_loop() -> None:
    await asyncio.sleep(4)
    while True:
        _RUNTIME_HEALTH["scan_heartbeat"] = time.time()
        try:
            if not COINS:
                await refresh_coin_pool(force=True)
            batch_size = 8
            coins = list(COINS)[:MA_COIN_LIMIT]
            for i in range(0, len(coins), batch_size):
                batch = coins[i:i + batch_size]
                tasks = [analyze_v10_symbol(sym) for sym in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for symbol, res in zip(batch, results):
                    _RUNTIME_HEALTH["scan_heartbeat"] = time.time()
                    if isinstance(res, Exception):
                        stats["analysis_error"] = int(stats.get("analysis_error", 0)) + 1
                        logger.error("Analiz hatası %s: %s", symbol, type(res).__name__, exc_info=(type(res), res, res.__traceback__))
                        continue
                    stats["v10_analyzed"] = int(stats.get("v10_analyzed", 0)) + 1
                    if res:
                        stats["v10_candidates"] = int(stats.get("v10_candidates", 0)) + 1
                        await gizli_aday(res)
                        await maybe_send_v10_signal(res)
                await asyncio.sleep(max(0.1, min(HOT_SCAN_INTERVAL_SEC, 2.0)))
        except Exception as e:
            logger.exception("v10_scan_loop hata: %s", e)
        await asyncio.sleep(max(5.0, DEEP_SCAN_INTERVAL_SEC))


async def v10_paper_loop() -> None:
    while True:
        await paper_tur()
        _RUNTIME_HEALTH['paper_heartbeat'] = time.time()
        await asyncio.sleep(max(1,V107_TAKIP_ARALIK_SEC))


def golge_kaydi_guncelle(golge: Dict[str, Any], barlar: List[List[Any]]) -> None:
    entry = safe_float(golge.get('entry'))
    stop = safe_float(golge.get('stop_ts'))*1000
    end = safe_float(golge.get('end_ts'),golge['stop_ts']+GOLGE_SAAT*3600)*1000
    scan = safe_float(golge.get('scan_ts'))
    if entry<=0:
        return
    for r in sorted(barlar,key=lambda r:safe_float(r[0])):
        ts = safe_float(r[0])
        duration = safe_float(r[9]) if len(r)>9 else interval_minutes(GOLGE_TF)*60000
        if ts<stop or ts<scan or ts+duration>end:
            continue
        hi,lo = safe_float(r[2]),safe_float(r[3])
        long = golge['side']=='LONG'
        favorable = max(0,(hi-entry)/entry*100 if long else (entry-lo)/entry*100)
        adverse = max(0,(entry-lo)/entry*100 if long else (hi-entry)/entry*100)
        golge['golge_mfe_pct'] = max(safe_float(golge.get('golge_mfe_pct')),favorable)
        golge['golge_mae_pct'] = max(safe_float(golge.get('golge_mae_pct')),adverse)
        for i in range(1,5):
            level = safe_float(golge.get(f'tp{i}'))
            if level>0 and (hi>=level if long else lo<=level):
                golge['golge_tp'] = max(int(golge.get('golge_tp',0)),i)
                if golge.get(f'golge_tp{i}_dk') is None:
                    golge[f'golge_tp{i}_dk'] = max(0,(ts+duration-stop)/60000)
        # Forming bar aynı timestamp ile yeniden okunur, sadece confirm=1 ilerletir.
        golge['scan_ts'] = ts+duration if len(r)>8 and str(r[8])=='1' else ts


async def golge_loop() -> None:
    while True:
        _RUNTIME_HEALTH['shadow_heartbeat']=time.time()
        await golge_tur()
        await asyncio.sleep(max(1,GOLGE_ARALIK_SEC))


async def save_loop() -> None:
    while True:
        try:
            await save_memory_async()
            _RUNTIME_HEALTH["save_heartbeat"] = time.time()
        except Exception:
            stats["memory_save_fail"] = int(stats.get("memory_save_fail",0))+1
            logger.exception("JSON snapshot yazılamadı")
        await asyncio.sleep(max(20, MEMORY_SAVE_INTERVAL_SEC))


def db_integrity_kontrol() -> Tuple[bool, str]:
    sonuclar = []
    for yol in (OLCUM_DB, BALINA_DB if BALINA_MOTOR_ENABLED else ""):
        if not yol or not os.path.exists(yol):
            continue
        try:
            with sqlite3.connect(yol, timeout=10) as conn:
                sonuc = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
            sonuclar.append(f"{os.path.basename(yol)}:{sonuc}")
            if sonuc.lower() != "ok":
                return False, " | ".join(sonuclar)
        except Exception as e:
            return False, f"{os.path.basename(yol)}:{e}"
    return True, " | ".join(sonuclar) if sonuclar else "veritabanı yok"


def db_yedekle() -> List[str]:
    if not DB_BACKUP_ENABLED:
        return []
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)
    damga = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uretilen = []
    for kaynak in (OLCUM_DB, BALINA_DB if BALINA_MOTOR_ENABLED else ""):
        if not kaynak or not os.path.exists(kaynak):
            continue
        hedef = os.path.join(DB_BACKUP_DIR, f"{os.path.basename(kaynak)}.{damga}.bak")
        with sqlite3.connect(kaynak, timeout=20) as src, sqlite3.connect(hedef, timeout=20) as dst:
            src.execute("PRAGMA wal_checkpoint(PASSIVE)")
            src.backup(dst)
        uretilen.append(hedef)
    if os.path.exists(MEMORY_FILE):
        hedef = os.path.join(DB_BACKUP_DIR, f"{os.path.basename(MEMORY_FILE)}.{damga}.bak")
        shutil.copy2(MEMORY_FILE, hedef)
        uretilen.append(hedef)
    dosyalar = sorted(
        (os.path.join(DB_BACKUP_DIR, x) for x in os.listdir(DB_BACKUP_DIR) if x.endswith(".bak")),
        key=lambda x: os.path.getmtime(x), reverse=True,
    )
    # KEEP dosya değil, aynı zaman damgalı tam yedek seti sayısıdır.
    stamps = sorted({p.rsplit('.',2)[-2] for p in dosyalar},reverse=True)
    keep = set(stamps[:max(1,DB_BACKUP_KEEP)])
    for eski in [p for p in dosyalar if p.rsplit('.',2)[-2] not in keep]:
        try:
            os.remove(eski)
        except OSError:
            pass
    return uretilen


def health_raporu_uret() -> str:
    now = time.time()
    risk = risk_durumu()
    disk_yol = os.path.abspath(os.path.dirname(OLCUM_DB) or ".")
    try:
        disk = shutil.disk_usage(disk_yol)
        disk_free = disk.free / (1024 ** 3)
    except Exception:
        disk_free = 0.0
    ws_age = max(0.0, now - safe_float(_BALINA_WS_STATUS.get("last_message_ts"), now))
    return (
        "🏥 V12.1.0 SİSTEM SAĞLIĞI\n"
        f"Çalışma süresi: {(now-safe_float(_RUNTIME_HEALTH.get('started_ts')))/3600:.1f} saat\n"
        f"Tarama yaşı: {now-safe_float(_RUNTIME_HEALTH.get('scan_heartbeat')):.1f} sn\n"
        f"Paper takip yaşı: {now-safe_float(_RUNTIME_HEALTH.get('paper_heartbeat')):.1f} sn\n"
        f"Gölge takip yaşı: {now-safe_float(_RUNTIME_HEALTH.get('shadow_heartbeat')):.1f} sn\n"
        f"WS: {'BAĞLI' if _BALINA_WS_STATUS.get('connected') else 'KOPUK'} | veri yaşı {ws_age:.1f} sn\n"
        f"DB integrity: {_RUNTIME_HEALTH.get('db_integrity')}\n"
        f"Gözetilen döngü: {len(_BACKGROUND_TASKS)} | Yeniden başlatma: {stats.get('task_restart',0)}\n"
        f"Kurtarma bekleyen: {stats.get('recovery_missing_position',0)} | Paper hata: {stats.get('paper_position_error',0)}\n"
        f"Son yedek yaşı: {(now-safe_float(_RUNTIME_HEALTH.get('last_backup_ts')))/3600:.1f} saat\n"
        f"Boş disk: {disk_free:.2f} GB\n"
        f"Risk: günlük {risk['daily_r']:+.2f}R | haftalık {risk['weekly_r']:+.2f}R | "
        f"ardışık stop {risk['consecutive_stops']} | açık {risk['open']}\n"
        f"Acil durdurma: {'AKTİF' if risk['kill_switch'] else 'kapalı'} | "
        f"Risk motoru: {'AKTİF' if RISK_ENGINE_ENABLED else 'ölçüm/kapalı'}"
    )


async def kurumsal_bakim_loop() -> None:
    await asyncio.sleep(20)
    while True:
        now = time.time()
        try:
            if now - safe_float(_RUNTIME_HEALTH.get("last_integrity_ts")) >= DB_INTEGRITY_INTERVAL_SEC:
                ok, detay = await asyncio.to_thread(db_integrity_kontrol)
                _RUNTIME_HEALTH["last_integrity_ts"] = now
                _RUNTIME_HEALTH["db_integrity"] = "OK" if ok else detay
                if not ok:
                    stats["db_integrity_fail"] = int(stats.get("db_integrity_fail", 0)) + 1
            if DB_BACKUP_ENABLED and now - safe_float(_RUNTIME_HEALTH.get("last_backup_ts")) >= DB_BACKUP_INTERVAL_SEC:
                try:
                    await asyncio.to_thread(db_yedekle)
                    _RUNTIME_HEALTH["last_backup_ts"] = now
                    stats["backup_success"] = int(stats.get("backup_success", 0)) + 1
                except Exception as e:
                    stats["backup_fail"] = int(stats.get("backup_fail", 0)) + 1
                    logger.exception("DB yedekleme hatası: %s", e)
            sorunlar = []
            if stats.get('recovery_missing_position',0):
                sorunlar.append('açık kayıtlar için eski JSON yedeğinden kurtarma gerekiyor')
            if now - safe_float(_RUNTIME_HEALTH.get("scan_heartbeat")) > SCAN_STALE_SEC:
                sorunlar.append("tarama döngüsü gecikti")
            if now - safe_float(_RUNTIME_HEALTH.get("paper_heartbeat")) > PAPER_STALE_SEC:
                sorunlar.append("paper takip döngüsü gecikti")
            if BALINA_MOTOR_ENABLED and (not _BALINA_WS_STATUS.get("connected") or
                    now - safe_float(_BALINA_WS_STATUS.get("last_message_ts")) > DATA_MAX_AGE_SEC):
                sorunlar.append("WebSocket bağlı değil veya verisi eski")
            if _RUNTIME_HEALTH.get("db_integrity") != "OK":
                sorunlar.append("DB integrity başarısız")
            if sorunlar and HEALTH_ALERT_ENABLED and now - safe_float(_RUNTIME_HEALTH.get("last_health_alert_ts")) >= HEALTH_ALERT_COOLDOWN_SEC:
                _RUNTIME_HEALTH["last_health_alert_ts"] = now
                stats["health_alert"] = int(stats.get("health_alert", 0)) + 1
                await safe_send_telegram("🚨 V12.1.0 SAĞLIK ALARMI\n" + "\n".join(f"• {x}" for x in sorunlar))
        except Exception as e:
            logger.exception("kurumsal_bakim_loop hata: %s", e)
        await asyncio.sleep(max(15, HEALTH_CHECK_INTERVAL_SEC))


def kapi_raporu_uret() -> str:
    rows = _report_rows()
    lines = [f'🧪 KAPI LABORATUVARI | Toplam örnek: {len(rows)} | Min hücre: {OLCUM_MIN_HUCRE}',_report_scope(),
             'R: kapanmış; MFE: açık+kapalı. Eksik kapılar ölçümsüzdür.']
    for gate in OLCUM_KAPILARI:
        lines.append('\n• '+gate)
        for control,name in ((0,'Normal'),(1,'Kontrol')):
            group = [r for r in rows if r['kontrol']==control]
            cells = {v:[r for r in group if r.get('kapilar',{}).get(gate)==v] for v in ('gecti','kesti')}
            metrics = []
            lines.append(f"{name} | ölçümsüz {len(group)-sum(map(len,cells.values()))}")
            for value,label in (('gecti','Geçen'),('kesti','Kesen')):
                m = _kombinasyon_metrik(cells[value]); metrics.append(m)
                rr = _metric(m['r']) if m['kapanan']>=OLCUM_MIN_HUCRE else f"ölçülemez (n={m['kapanan']})"
                mfe = _metric(m['mfe']) if m['toplam']>=OLCUM_MIN_HUCRE else f"ölçülemez (n={m['toplam']})"
                lines.append(f"  {label}: toplam {m['toplam']} | kapanan {m['kapanan']} | Ort.R {rr} | Ort.MFE %{mfe}")
            a,b = metrics
            if min(a['kapanan'],b['kapanan'])>=OLCUM_MIN_HUCRE:
                lines.append('  ΔR '+_metric(a['r']-b['r']))
            if min(a['toplam'],b['toplam'])>=OLCUM_MIN_HUCRE:
                lines.append('  ΔMFE %'+_metric(a['mfe']-b['mfe']))
    return '\n'.join(lines)


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


def tp_raporu_uret():
    return _engine_report('MAIN') + '\n' + _target_report('MAIN')


def sayisal_bantlar(ozellikler: Dict[str, Any]) -> Dict[str, str]:
    sonuc: Dict[str, str] = {}

    def ekle(ad: str, bantlar: List[Tuple[float, Optional[float], str]]) -> None:
        deger = ozellikler.get(ad)
        if deger is None:
            return
        try:
            sayi = float(deger)
        except Exception:
            return
        for alt, ust, etiket in bantlar:
            if sayi >= alt and (ust is None or sayi < ust):
                sonuc[ad] = etiket
                return

    ekle("skor", [(-float("inf"), 60, "<60"), (60, 70, "60-69"),
                   (70, 80, "70-79"), (80, None, "80+")])
    ekle("rsi", [(-float("inf"), 30, "<30"), (30, 45, "30-45"),
                  (45, 55, "45-55"), (55, 70, "55-70"), (70, None, "70+")])
    ekle("adx", [(-float("inf"), 20, "<20"), (20, 25, "20-25"),
                  (25, 30, "25-30"), (30, None, "30+")])
    ekle("vwm", [(-float("inf"), -0.2, "<-0.2"), (-0.2, 0, "-0.2..0"),
                  (0, 0.2, "0..0.2"), (0.2, None, "0.2+")])
    ekle("oi_pct", [(-float("inf"), -1, "<-1"), (-1, 0, "-1..0"),
                     (0, 1, "0..1"), (1, None, "1+")])
    ekle("fomo_pct", [(-float("inf"), 0, "<0"), (0, 1, "0-1"),
                       (1, 2, "1-2"), (2, None, "2+")])
    ekle("obimb", [(-float("inf"), -0.2, "<-0.2"), (-0.2, 0, "-0.2..0"),
                    (0, 0.2, "0..0.2"), (0.2, None, "0.2+")])
    ekle("funding", [(-float("inf"), 0, "negatif"), (0, 0.005, "0-0.005"),
                      (0.005, None, "0.005+")])
    return sonuc


def ortak_ozellik_analiz(grup_a: List[Dict[str, Any]],
                         grup_b: List[Dict[str, Any]]) -> List[str]:
    kategorik = ("yapi_tipi", "1h_trend", "4h_trend", "btc_1h", "btc_4h",
                 "coin_1h_ema", "session_name", "giris_tipi", "yon", "kontrol")

    def say(rec: Dict[str, Any]) -> set:
        oz = rec.get("ozellikler") or {}
        degerler = set()
        for ad in kategorik:
            if oz.get(ad) is not None:
                degerler.add((ad, str(oz[ad])))
        for ad, deger in sayisal_bantlar(oz).items():
            degerler.add((ad, deger))
        for ad, deger in (rec.get("kapilar") or {}).items():
            if deger in ("gecti", "kesti"):
                degerler.add((f"kapi:{ad}", deger))
        return degerler

    a_setleri = [say(r) for r in grup_a]
    b_setleri = [say(r) for r in grup_b]
    tum = set().union(*a_setleri, *b_setleri) if (a_setleri or b_setleri) else set()
    adaylar = []
    toplam_a, toplam_b = len(grup_a), len(grup_b)
    for ad, deger in tum:
        n_a = sum(1 for s in a_setleri if (ad, deger) in s)
        n_b = sum(1 for s in b_setleri if (ad, deger) in s)
        oran_a = n_a / toplam_a * 100.0 if toplam_a else 0.0
        oran_b = n_b / toplam_b * 100.0 if toplam_b else 0.0
        fark = oran_a - oran_b
        if abs(fark) < 10.0:
            continue
        adaylar.append((abs(fark), ad, deger, n_a, n_b, oran_a, oran_b, fark))
    adaylar.sort(key=lambda x: (-x[0], x[1], x[2]))
    satirlar = []
    for _mutlak, ad, deger, n_a, n_b, oran_a, oran_b, fark in adaylar[:15]:
        if n_a < ORTAK_MIN_N or n_b < ORTAK_MIN_N:
            satirlar.append(f"{ad} = {deger} | yetersiz (nA={n_a}, nB={n_b})")
        else:
            satirlar.append(
                f"{ad} = {deger} | A: {n_a}/{toplam_a} (%{oran_a:.1f}) | "
                f"B: {n_b}/{toplam_b} (%{oran_b:.1f}) | fark {fark:+.1f} puan"
            )
    return satirlar


def ortak_rapor_uret(ters: bool = False) -> str:
    tum = _report_rows()
    baslik = "🧪 STOP ORTAK ÖZELLİK" if ters else "🧪 TP ORTAK ÖZELLİK"
    lines = [baslik + " | TP1 tam kapanış / temiz stop karşılaştırması", _report_scope()]
    lines.append("⚠️ ~40 özellik test edildi. Bu kadar özellikte şans eseri fark çıkması beklenir. Buradaki bulgular hipotezdir, karar değildir — yeni bir örnekte doğrulanmadan kapı değiştirme.")
    tp_sonuclari = {"TP1_TAM", "TP1_STOP", "TP2_STOP", "TP3_STOP", "TP4_TAM"}
    for kontrol_degeri, grup_adi in ((0, "NORMAL"), (1, "KONTROL")):
        kaynak = [r for r in tum if int(r.get("kontrol", 0)) == kontrol_degeri]
        tp_grubu = [r for r in kaynak if r.get("sonuc_tipi") in tp_sonuclari or
                    r.get("hit1")]
        temiz_stop = [r for r in kaynak if r.get("sonuc_tipi") == "TEMIZ_STOP"]
        grup_a, grup_b = (temiz_stop, tp_grubu) if ters else (tp_grubu, temiz_stop)
        lines.append(f"\n{grup_adi} | A n={len(grup_a)} | B n={len(grup_b)}")
        lines.extend(ortak_ozellik_analiz(grup_a, grup_b))
    return "\n".join(lines)


def _kombinasyon_kosullari(rec: Dict[str, Any]) -> Dict[str, Optional[bool]]:
    oz, gates = rec.get('ozellikler') or {}, rec.get('kapilar') or {}
    def gate(name):
        return True if gates.get(name)=='gecti' else False if gates.get(name)=='kesti' else None
    oi = safe_float(oz.get('oi_pct'),None)
    source = str(oz.get('giris_tipi') or '').lower()
    return {'oi': oi>1 if oi is not None else None,
            'coin_ema':gate('coin_1h_ema'),'range':gate('range'),'spoof':gate('spoof'),
            'kapanis': source=='kapanis' if source in ('kapanis','orderbook','mum') else None}


def _kombinasyon_metrik(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    closed = [r for r in rows if r.get('durum') not in ('ACIK',None)]
    n,nc = len(rows),len(closed)
    return {'toplam':n,'kapanan':nc,
            'temiz_pct':sum(r.get('sonuc_tipi')=='TEMIZ_STOP' for r in closed)/nc*100 if nc else None,
            **{f'tp{i}_pct':sum(bool(r.get(f'hit{i}')) for r in rows)/n*100 if n else None for i in range(1,5)},
            'r':_mean_present(closed,'r_value'),'net_r':_mean_present(closed,'net_r_value'),
            'mfe':_mean_present(rows,'mfe_pct'),'mae':_mean_present(rows,'mae_pct')}


def _kombinasyon_metrik_satiri(ad: str, m: Dict[str, Any]) -> str:
    return (f"{ad}: toplam {m['toplam']} | kapanan {m['kapanan']} | temiz stop %"+_metric(m['temiz_pct'],1)+
            ' | '+' / '.join(f"TP{i} %"+_metric(m[f'tp{i}_pct'],1) for i in range(1,5))+
            ' | Brüt Ort.R '+_metric(m['r'])+' | Net Ort.R '+_metric(m['net_r'])+
            ' | MFE/MAE %'+_metric(m['mfe'])+'/%'+_metric(m['mae']))


def kombinasyon_raporu_uret() -> str:
    rows = _report_rows()
    combos = (('OI > %1',('oi',)),('Coin EMA uyumlu',('coin_ema',)),('RANGE geçti',('range',)),
              ('Giriş kapanış',('kapanis',)),('Spoof geçti',('spoof',)),('OI + Coin EMA',('oi','coin_ema')),
              ('OI + kapanış',('oi','kapanis')),('OI + Coin EMA + RANGE',('oi','coin_ema','range')),
              ('Beş şart',('oi','coin_ema','range','kapanis','spoof')))
    for r in rows:
        r['_conditions'] = _kombinasyon_kosullari(r)
    lines = [f'🧪 KOMBİNASYON LABORATUVARI | Min kapanan hücre: {KOMBINASYON_MIN_KAPANIS}',_report_scope(),
             'TP ve MFE/MAE açık+kapalı; R ve temiz stop yalnız kapananlardan. Açık sonuçlar tamamlanmamıştır.',
             'Ölçümsüz kayıtlar karşılaştırmadan çıkarılır. Hiçbir kombinasyon sinyal kesmez.']
    for control,name in ((0,'NORMAL'),(1,'KONTROL')):
        group = [r for r in rows if r['kontrol']==control]
        for side in ('TÜM','LONG','SHORT'):
            base = group if side=='TÜM' else [r for r in group if r['side']==side]
            lines.append(f'\n{name} / {side} | n={len(base)}')
            for label,keys in combos:
                a,b,u = _combo_partition(base,keys)
                lines.append('\n• '+label)
                lines.extend(_comparison_lines(a,b,len(u)))
        lines.append(f'\n{name} / BALİNA DURUMU + YÖN')
        for side in ('LONG','SHORT'):
            base = [r for r in group if r['side']==side]
            states = defaultdict(list)
            for r in base:
                states[(r.get('ozellikler') or {}).get('balina_durum') or 'OLCUMSUZ'].append(r)
            for state,a in sorted(states.items()):
                b = [r for s,items in states.items() if s!=state for r in items]
                lines.append(f'\n• {state} / {side}')
                lines.extend(_comparison_lines(a,b))
    return '\n'.join(lines)


def dogrulama_raporu_uret() -> str:
    rows = _report_rows()
    lines = ['📐 V12.1.0 İLERİ DOĞRULAMA',_report_scope(),f'Minimum kapanış: {VALIDATION_MIN_CLOSED}',
             'Maliyet girişte dondurulur; net R komisyon/kayma/funding varsayımı sonrasıdır.']
    if VALIDATION_START_TS<=0:
        lines.append('Sabit ileri doğrulama başlangıcı tanımlanmadı; sonuçlar betimseldir, karar yok.')
    else:
        lines.append('Sabit doğrulama başlangıcı: '+tr_str(VALIDATION_START_TS))
    for control,name in ((0,'NORMAL'),(1,'KONTROL')):
        group = [r for r in rows if r['kontrol']==control]
        closed = [r for r in group if r['durum']!='ACIK']
        lines.append(f"\n{name} | kapanan={len(closed)} | açık={len(group)-len(closed)}")
        splits = [('Tüm kapananlar',closed)] if VALIDATION_START_TS<=0 else [
            ('Başlangıç öncesi',[r for r in closed if r['open_ts']<VALIDATION_START_TS]),
            ('İleri doğrulama',[r for r in closed if r['open_ts']>=VALIDATION_START_TS])]
        for label,part in splits:
            lines.append(f'{label}: n={len(part)} | Brüt EV '+_metric(_mean_present(part,'r_value'))+
                         'R | Net EV '+_metric(_mean_present(part,'net_r_value'))+'R | '+
                         ('karar yok' if len(part)<VALIDATION_MIN_CLOSED or VALIDATION_START_TS<=0 else 'örnek eşiği tamam; tek başına karar değildir'))
        for side in ('LONG','SHORT'):
            part = [r for r in closed if r['side']==side]
            lines.append(f'{side}: n={len(part)} | Net EV '+_metric(_mean_present(part,'net_r_value'))+
                         'R | MFE/MAE %'+_metric(_mean_present(part,'mfe_pct'))+'/%'+_metric(_mean_present(part,'mae_pct')))
        regimes = sorted({str(r.get('ozellikler',{}).get('piyasa_modu') or 'OLCUMSUZ') for r in closed})
        for regime in regimes:
            part = [r for r in closed if str(r.get('ozellikler',{}).get('piyasa_modu') or 'OLCUMSUZ')==regime]
            lines.append(f'Rejim {regime}: n={len(part)} | Net EV '+_metric(_mean_present(part,'net_r_value'))+'R')
    lines.append('⚠️ Açık işlemler ve izleme süresi tamamlanmadan yalnız kapanan EV toplam performansı temsil etmez.')
    return '\n'.join(lines)


def golge_neden_raporu_uret():
    return _shadow_report('MAIN')


def selftest_raporu_uret() -> str:
    testler = []
    def test(ad: str, kosul: bool) -> None:
        testler.append((ad, bool(kosul)))
    test("safe_float", safe_float("1.25") == 1.25 and safe_float("x") == 0.0)
    test("yüzdelik", yuzdelik([1, 2, 3, 4], 0.5) == 2.5)
    test("TP1 tam kapanış", _tp_weights() == [1.0,0.0,0.0,0.0])
    ornek = {"entry": 100, "orig_stop": 98}
    test("maliyet R", simulasyon_maliyet_r(ornek) >= 0)
    test("sembol", normalize_symbol("BTCUSDT") == "BTC-USDT-SWAP")
    test("DB mevcut", os.path.exists(OLCUM_DB))
    ok, detay = db_integrity_kontrol()
    test("DB integrity", ok)
    lines = ["🧪 V12.1.0 ÖZ TEST"]
    lines.extend(f"{'✅' if sonuc else '❌'} {ad}" for ad, sonuc in testler)
    lines.append(f"Sonuç: {sum(1 for _, x in testler if x)}/{len(testler)} geçti")
    lines.append(f"DB: {detay}")
    return "\n".join(lines)


async def post_init(application) -> None:
    logger.info('Veri kaynakları: OKX REST/WS; MEXC ikincil REST=%s', MEXC_ENABLED)
    await _db_call(olcum_db_init)
    await _db_call(yeni_motor_db_init)
    await _db_call(_restore_ledger)
    now = time.time()
    _RUNTIME_HEALTH.update(started_ts=now,scan_heartbeat=now,paper_heartbeat=now,
        shadow_heartbeat=now,save_heartbeat=now,emergency_stop=bool(memory.get('emergency_stop',False)))
    await _db_call(audit_yaz,'BOT_START','','',{'python':platform.python_version(),'schema':DB_SCHEMA_VERSION})
    if BALINA_MOTOR_ENABLED:
        await asyncio.to_thread(balina_db_init)
    active,_ = await refresh_coin_pool(force=True)
    count = len(await _db_call(olcum_db_satirlari))
    mp = _v10_mem()
    follow_count=len(await _db_call(_follow_rows,True))
    hidden_open=len(await _db_call(_gizli_rows,True))
    text = (f'🚀 {VERSION_NAME} başladı\nSaat: {tr_str()}\nCoin sayısı: {active}\n'
        f'PAPER | Stop %{SABIT_STOP_PCT} | TP {TP1_RR}/{TP2_RR}/{TP3_RR}/{TP4_RR}R\n'
        f'TP1 tam kapanış; TP2/3/4 yalnız izleme. Gizli bildirim: {GIZLI_TELEGRAM_ENABLED}\n'
        f'Ölçüm modu: {OLCUM_MODU} | Kontrol oranı: %{OLCUM_RASTGELE_ORAN*100:.1f}\n'
        f'Ölçüm kaydı: {count} pozisyon | Açık {len(mp["open"])} | İzleme {follow_count} | Gizli açık {hidden_open}\n'
        f'RSI: {RSI_METHOD} | Skor: {SCORE_MODE} | CVD: {SCORE_CVD_SOURCE}\n'
        f'MEXC ikincil veri: {MEXC_ENABLED} | Süre çıkışı: {TIME_EXIT_MODE}\n'
        f'Balina motoru: {BALINA_MOTOR_ENABLED} | WS defter kanalı: {BALINA_WS_BOOK_CHANNEL}\n'
        f'Balina durum kapısı: {BALINA_KARLI_KAPI_ENABLED} | Ölçümde sinyal kesmez\n'
        f'Likidite: tahmini mesafe bantları; {"hesaplanıyor" if LIQ_HEATMAP_ENABLED and LIQ_HEATMAP_FETCH_OI else "hesaplanmıyor"}; bilgi amaçlı\n'
        f'Risk motoru: {RISK_ENGINE_ENABLED} | DB şema {DB_SCHEMA_VERSION}\n'+_report_scope()+
        '\n'+'\n'.join(_persistence_warnings()))
    # Startup bildirimi tarama/paper başlamasını bekletmez.
    await _db_call(_enqueue_system_notification,text)
    for factory in (symbol_refresh_loop,v10_scan_loop,v10_paper_loop,golge_loop,save_loop,notification_loop,yeni_motor_loop):
        _start_loop(factory)
    if MEXC_ENABLED:
        _start_loop(mexc_market_loop)
    if KURUMSAL_ENABLED:
        _start_loop(kurumsal_bakim_loop)
    if BALINA_MOTOR_ENABLED:
        _start_loop(balina_db_loop)
        _start_loop(balina_ws_loop)


async def cmd_start(update, context):
    if not telegram_yetkili(update):
        return
    await update.message.reply_text(
        f"{VERSION_NAME} aktif.\n"
        "/eskisürüm - eski defter (salt okunur)\n/gizli - sessiz motor raporu\n/hedefler - alternatif kapanışlar\n/mexc COIN - ikincil borsa verisi\n/status - durum\n/test - test\n/v10 - motor durumu\n/coin SYMBOL - tek coin\n"
        "/kapi - kapı ölçüm raporu\n/tp - TP ve stop sonrası ölçüm raporu\n"
        "/kombinasyon - koşul ve kombinasyon laboratuvarı\n"
        "/dogrulama - ileri doğrulama ve net maliyet raporu\n"
        "/golge - stop sonrası TP ve neden analizi\n"
        "/health - sistem ve veri sağlığı\n/risk - portföy risk durumu\n"
        "/durdur - yeni sinyalleri acil durdur\n/devam - sinyalleri yeniden aç\n"
        "/selftest - dahili doğrulama testleri\n/backup - manuel DB yedeği\n/yedekindir - DB ve JSON dosyalarını indir\n"
        "/tportak - TP ortak özellikleri\n/stoportak - temiz stop ortak özellikleri\n"
        "/balina [COIN] - balina akış durumu\n/akis COIN - büyük işlemler\n"
        "/birikim - birikim adayları\n/dagitim - dağıtım adayları\n"
        "/ws - canlı bağlantı durumu\n/balinarapor - motor olay özeti\n"
    )

async def cmd_test(update, context):
    if not telegram_yetkili(update):
        return
    ok = await safe_send_telegram(f"✅ Test başarılı. Saat: {tr_str()}")
    await update.message.reply_text("Gönderildi." if ok else "Başarısız.")

async def cmd_status(update, context):
    if not telegram_yetkili(update):
        return
    text = await _db_call(status_raporu_uret)
    for part in telegram_parcala(text):
        await update.message.reply_text(part)

async def cmd_coin(update, context):
    if not telegram_yetkili(update):
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /coin BTCUSDT")
        return
    symbol = normalize_symbol(context.args[0])
    res = await analyze_v10_symbol(symbol)
    if not res:
        await update.message.reply_text(f"{symbol} için V12.1.0 sinyali yok.")
        return
    for part in telegram_parcala('ÖN ANALİZ — deftere sinyal açılmadı; giriş tekrar fiyatlanır.\n'+build_v10_message(res)):
        await update.message.reply_text(part)

async def cmd_v10(update, context):
    if not telegram_yetkili(update):
        return
    mp = _v10_mem()
    lines = [
        f"🆕 V12.1.0 ULTRA motor durumu",
        f"Açık: {len(mp['open'])} | Sinyal: {stats.get('v10_signals', 0)}",
        f"Session: {session_belirle()[0]}",
        f"VWAP: {'AKTİF' if VWAP_ENABLED else 'kapalı'} | ADX: {'AKTİF' if ADX_ENABLED else 'kapalı'}",
        f"Tahmini mesafe bantları: {'hesaplanıyor' if LIQ_HEATMAP_ENABLED and LIQ_HEATMAP_FETCH_OI else 'hesaplanmıyor'} | MTF: {'AKTİF' if MTF_CONFLUENCE_ENABLED else 'kapalı'}",
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


async def cmd_tportak(update, context):
    if not telegram_yetkili(update):
        return
    try:
        rapor = await asyncio.to_thread(ortak_rapor_uret, False)
        for parca in telegram_parcala(rapor, 4000):
            await update.message.reply_text(parca)
    except Exception as e:
        logger.exception("/tportak rapor hatası: %s", e)
        await update.message.reply_text("TP ortak özellik raporu hazırlanamadı.")


async def cmd_stoportak(update, context):
    if not telegram_yetkili(update):
        return
    try:
        rapor = await asyncio.to_thread(ortak_rapor_uret, True)
        for parca in telegram_parcala(rapor, 4000):
            await update.message.reply_text(parca)
    except Exception as e:
        logger.exception("/stoportak rapor hatası: %s", e)
        await update.message.reply_text("STOP ortak özellik raporu hazırlanamadı.")


async def cmd_kombinasyon(update, context):
    if not telegram_yetkili(update):
        return
    try:
        rapor = await asyncio.to_thread(kombinasyon_raporu_uret)
        for parca in telegram_parcala(rapor, 4000):
            await update.message.reply_text(parca)
    except Exception as e:
        logger.exception("/kombinasyon rapor hatası: %s", e)
        await update.message.reply_text("Kombinasyon raporu hazırlanamadı.")


async def cmd_health(update, context):
    if not telegram_yetkili(update):
        return
    await update.message.reply_text(await asyncio.to_thread(health_raporu_uret))


async def cmd_risk(update, context):
    if not telegram_yetkili(update):
        return
    d = await asyncio.to_thread(risk_durumu)
    await update.message.reply_text(
        "🛡 V12.1.0 RİSK MOTORU\n"
        f"Motor: {'AKTİF' if RISK_ENGINE_ENABLED else 'ölçüm/kapalı'}\n"
        f"Acil durdurma: {'AKTİF' if d['kill_switch'] else 'kapalı'}\n"
        f"Günlük: {d['daily_r']:+.2f}R / -{abs(RISK_MAX_DAILY_R):.2f}R\n"
        f"Haftalık: {d['weekly_r']:+.2f}R / -{abs(RISK_MAX_WEEKLY_R):.2f}R\n"
        f"Ardışık temiz stop: {d['consecutive_stops']}/{RISK_MAX_CONSECUTIVE_STOPS}\n"
        f"Açık: {d['open']}/{RISK_MAX_TOTAL_OPEN} | LONG {d['side_counts']['LONG']} | SHORT {d['side_counts']['SHORT']}"
    )


async def cmd_durdur(update, context):
    if not telegram_yetkili(update):
        return
    _RUNTIME_HEALTH["emergency_stop"] = True
    memory["emergency_stop"] = True
    await _db_call(audit_yaz,"EMERGENCY_STOP","","",{"chat_id":str(update.effective_chat.id)})
    await save_memory_async()
    await update.message.reply_text("🛑 Yeni sinyal üretimi acil olarak durduruldu. Açık paper pozisyonlar izlenmeye devam ediyor.")


async def cmd_devam(update, context):
    if not telegram_yetkili(update):
        return
    if RISK_KILL_SWITCH:
        await update.message.reply_text("RISK_KILL_SWITCH env aktif; Railway ayarından false yapılmadan devam edemez.")
        return
    _RUNTIME_HEALTH["emergency_stop"] = False
    memory["emergency_stop"] = False
    await _db_call(audit_yaz,"EMERGENCY_RESUME","","",{"chat_id":str(update.effective_chat.id)})
    await save_memory_async()
    await update.message.reply_text("▶️ Yeni sinyal üretimi yeniden açıldı.")


async def cmd_dogrulama(update, context):
    if not telegram_yetkili(update):
        return
    rapor = await asyncio.to_thread(dogrulama_raporu_uret)
    for parca in telegram_parcala(rapor, 4000):
        await update.message.reply_text(parca)


async def cmd_golge(update, context):
    if not telegram_yetkili(update):
        return
    rapor = await asyncio.to_thread(golge_neden_raporu_uret)
    for parca in telegram_parcala(rapor, 4000):
        await update.message.reply_text(parca)


async def cmd_selftest(update, context):
    if not telegram_yetkili(update):
        return
    await update.message.reply_text(await asyncio.to_thread(selftest_raporu_uret))


async def cmd_backup(update, context):
    if not telegram_yetkili(update):
        return
    try:
        dosyalar = await asyncio.to_thread(db_yedekle)
        _RUNTIME_HEALTH["last_backup_ts"] = time.time()
        await update.message.reply_text(f"💾 Yedek tamamlandı: {len(dosyalar)} veritabanı")
    except Exception as e:
        logger.exception("Manuel yedek hatası: %s", e)
        await update.message.reply_text("Yedekleme başarısız.")


def _balina_snapshot_satiri(s: Dict[str, Any]) -> str:
    return (f"{_base_of(str(s.get('symbol', '')))} | {s.get('durum', 'VERI_YETERSIZ')} "
            f"{safe_float(s.get('guven')):.0f}/100 | Kalite {safe_float(s.get('data_quality')):.0f} | "
            f"CVD1m {safe_float(s.get('cvd_norm_1m')):+.2f} | "
            f"Balina A/S {safe_float(s.get('whale_buy_1m'))/1000:.0f}K/"
            f"{safe_float(s.get('whale_sell_1m'))/1000:.0f}K | OB {safe_float(s.get('book_imbalance')):+.2f}")


async def cmd_balina(update, context):
    if not telegram_yetkili(update):
        return
    if not BALINA_MOTOR_ENABLED:
        await update.message.reply_text("Balina motoru kapalı. BALINA_MOTOR_ENABLED=true ile açılır.")
        return
    if context.args:
        snap = balina_snapshot(normalize_symbol(context.args[0]))
        lines = ["🐋 BALİNA AKIŞ DURUMU", _balina_snapshot_satiri(snap),
                 f"Kaynak: {snap.get('source')} | Durum: {snap.get('status')}",
                 f"CVD 5s/15s/1m/5m: {safe_float(snap.get('cvd_5s')):+.0f} / "
                 f"{safe_float(snap.get('cvd_15s')):+.0f} / {safe_float(snap.get('cvd_1m')):+.0f} / "
                 f"{safe_float(snap.get('cvd_5m')):+.0f}",
                 f"Balina işlem: {int(safe_float(snap.get('whale_count_1m')))} | "
                 f"Aktif duvar: {int(safe_float(snap.get('active_walls')))} | "
                 f"Spoof 1m: {int(safe_float(snap.get('spoof_1m')))}",
                 f"Akış: {int(safe_float(snap.get('trade_count_1m')))} işlem | "
                 f"{safe_float(snap.get('trade_volume_1m_usdt')):,.0f} USDT | "
                 f"Kalite {safe_float(snap.get('data_quality')):.0f}/100",
                 f"Veri yaşı: {safe_float(snap.get('last_data_age_sec')):.1f} sn"]
    else:
        snaps = [balina_snapshot(sym) for sym in list(_BALINA_STATE)]
        snaps = [s for s in snaps if s.get("status") == "CANLI"]
        snaps.sort(key=lambda s: safe_float(s.get("guven")), reverse=True)
        lines = [f"🐋 BALİNA MOTORU | İzlenen {len(_BALINA_STATE)} coin"]
        lines.extend(_balina_snapshot_satiri(s) for s in snaps[:15])
        if len(lines) == 1:
            lines.append("Henüz canlı veri birikmedi.")
    for part in telegram_parcala("\n".join(lines), 4000):
        await update.message.reply_text(part)


async def cmd_akis(update, context):
    if not telegram_yetkili(update):
        return
    if not BALINA_MOTOR_ENABLED:
        await update.message.reply_text("Balina motoru kapalı.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /akis BTC")
        return
    symbol = normalize_symbol(context.args[0])
    state = _balina_symbol_state(symbol)
    with _BALINA_LOCK:
        rows = list(state["whales"])[-20:]
    lines = [f"🐋 BÜYÜK İŞLEMLER | {symbol}"]
    for row in reversed(rows):
        lines.append(f"{tr_str(safe_float(row.get('ts')))} | {str(row.get('side')).upper()} | "
                     f"{_v10_fmt(row.get('price'))} | {safe_float(row.get('value')):,.0f} USDT")
    if not rows:
        lines.append("Kayıt yok.")
    for part in telegram_parcala("\n".join(lines), 4000):
        await update.message.reply_text(part)


async def _cmd_balina_liste(update, durumlar: Tuple[str, ...], baslik: str) -> None:
    if not BALINA_MOTOR_ENABLED:
        await update.message.reply_text("Balina motoru kapalı.")
        return
    snaps = [balina_snapshot(sym) for sym in list(_BALINA_STATE)]
    snaps = [s for s in snaps if s.get("durum") in durumlar and s.get("status") == "CANLI"]
    snaps.sort(key=lambda s: safe_float(s.get("guven")), reverse=True)
    lines = [baslik] + [_balina_snapshot_satiri(s) for s in snaps[:25]]
    if len(lines) == 1:
        lines.append("Aktif aday yok.")
    for part in telegram_parcala("\n".join(lines), 4000):
        await update.message.reply_text(part)


async def cmd_birikim(update, context):
    if not telegram_yetkili(update):
        return
    await _cmd_balina_liste(update, ("BIRIKIM", "SATIS_EMILIMI", "BALINA_ALIMI", "PARCALI_BALINA_ALIMI"),
                            "🐋 BİRİKİM / ALIM ADAYLARI")


async def cmd_dagitim(update, context):
    if not telegram_yetkili(update):
        return
    await _cmd_balina_liste(update, ("DAGITIM", "ALIS_EMILIMI", "BALINA_SATISI", "PARCALI_BALINA_SATISI"),
                            "🐋 DAĞITIM / SATIM ADAYLARI")


async def cmd_ws(update, context):
    if not telegram_yetkili(update):
        return
    age = max(0.0,time.time()-safe_float(_BALINA_WS_STATUS.get("last_message_ts")))
    await update.message.reply_text(
        "🌐 BALİNA WEBSOCKET\n"
        f"Motor: {'AKTİF' if BALINA_MOTOR_ENABLED else 'kapalı'}\n"
        f"Bağlantı: {'BAĞLI' if _BALINA_WS_STATUS.get('connected') else 'KOPUK; REST sinyal analizi sürer'}\n"
        f"Abonelik: {_BALINA_WS_STATUS.get('subscriptions', 0)}\n"
        f"Son veri yaşı: {age:.1f} sn\n"
        f"Mesaj: {stats.get('balina_ws_message', 0)} | İşlem: {stats.get('balina_trade', 0)} | "
        f"Balina: {stats.get('balina_whale', 0)} | Spoof: {stats.get('balina_spoof', 0)}\n"
        f"Bağlanma/Kopma: {stats.get('balina_ws_connect', 0)}/{stats.get('balina_ws_disconnect', 0)}\n"
        f"Son hata: {_BALINA_WS_STATUS.get('last_error') or '-'}"
    )


def balina_raporu_uret() -> str:
    if not os.path.exists(BALINA_DB):
        return "🐋 BALİNA RAPORU\nKayıt yok."
    cutoff = time.time() - 24 * 3600
    with sqlite3.connect(BALINA_DB, timeout=10) as conn:
        rows = conn.execute("""
            SELECT event_type,side,COUNT(*),COALESCE(SUM(value_usdt),0)
            FROM balina_event WHERE ts>=? GROUP BY event_type,side ORDER BY COUNT(*) DESC
        """, (cutoff,)).fetchall()
        snaps = conn.execute("""
            SELECT durum,COUNT(*),AVG(guven) FROM balina_snapshot WHERE ts>=? GROUP BY durum ORDER BY COUNT(*) DESC
        """, (time.time()-max(10.0,BALINA_STALE_SEC*2),)).fetchall()
    lines = ["🐋 BALİNA RAPORU | Son 24 saat", "OLAYLAR"]
    lines.extend(f"{t} {s or '-'}: {n} | {safe_float(v):,.0f} USDT" for t, s, n, v in rows)
    lines.append("ANLIK DURUMLAR")
    lines.extend(f"{d}: {n} | Ort.güven {safe_float(g):.1f}" for d, n, g in snaps)
    lines.append("SİNYAL SONUÇLARI | Ort.R yalnız kapananlar; açık sonuçlar tamamlanmamıştır")
    lines.append(_report_scope())
    olcum_rows = _report_rows()
    for kontrol_degeri, grup_adi in ((0, "NORMAL"), (1, "KONTROL")):
        grup = [r for r in olcum_rows if int(r.get("kontrol", 0)) == kontrol_degeri]
        durumlar = defaultdict(list)
        for rec in grup:
            balina_durum = str((rec.get("ozellikler") or {}).get("balina_durum") or "")
            if balina_durum and balina_durum != "OLCUMSUZ":
                durumlar[balina_durum].append(rec)
        lines.append(grup_adi)
        if not durumlar:
            lines.append("Balina etiketi taşıyan pozisyon yok.")
            continue
        for durum, kayitlar in sorted(durumlar.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            kapanan = [r for r in kayitlar if r.get("durum") != "ACIK"]
            temiz = sum(1 for r in kapanan if r.get("sonuc_tipi") == "TEMIZ_STOP")
            tp_goren = sum(1 for r in kayitlar if r.get("hit1"))
            ort_r = _mean_present(kapanan,"r_value")
            ort_mfe = avg([safe_float(r.get("mfe_pct")) for r in kayitlar])
            lines.append(
                f"{durum}: n={len(kayitlar)} | kapanan={len(kapanan)} | "
                f"temiz stop={temiz} | TP1+={tp_goren} | Ort.R {_metric(ort_r)} | Ort.MFE %{ort_mfe:.3f}"
            )
    return "\n".join(lines)


async def cmd_balinarapor(update, context):
    if not telegram_yetkili(update):
        return
    rapor = await asyncio.to_thread(balina_raporu_uret)
    for part in telegram_parcala(rapor, 4000):
        await update.message.reply_text(part)


def telegram_yetkili(update: Update) -> bool:
    chat = getattr(update, "effective_chat", None)
    return bool(chat and str(chat.id) == str(TELEGRAM_CHAT_ID))


def build_app():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).post_stop(post_stop).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler("mexc", cmd_mexc))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Regex(r"^/eskisürüm(?:@\w+)?(?:\s|$)"), cmd_eskisurum))
    app.add_handler(CommandHandler("eskisurum", cmd_eskisurum))
    app.add_handler(CommandHandler("gizli", cmd_gizli))
    app.add_handler(CommandHandler("hedefler", cmd_hedefler))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("coin", cmd_coin))
    app.add_handler(CommandHandler("v10", cmd_v10))
    app.add_handler(CommandHandler("kapi", cmd_kapi))
    app.add_handler(CommandHandler("tp", cmd_tp))
    app.add_handler(CommandHandler("tportak", cmd_tportak))
    app.add_handler(CommandHandler("stoportak", cmd_stoportak))
    app.add_handler(CommandHandler("kombinasyon", cmd_kombinasyon))
    app.add_handler(CommandHandler("dogrulama", cmd_dogrulama))
    app.add_handler(CommandHandler("golge", cmd_golge))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("risk", cmd_risk))
    app.add_handler(CommandHandler("durdur", cmd_durdur))
    app.add_handler(CommandHandler("devam", cmd_devam))
    app.add_handler(CommandHandler("selftest", cmd_selftest))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("yedekindir", cmd_yedekindir, block=False))
    app.add_handler(CommandHandler("balina", cmd_balina))
    app.add_handler(CommandHandler("akis", cmd_akis))
    app.add_handler(CommandHandler("birikim", cmd_birikim))
    app.add_handler(CommandHandler("dagitim", cmd_dagitim))
    app.add_handler(CommandHandler("ws", cmd_ws))
    app.add_handler(CommandHandler("balinarapor", cmd_balinarapor))
    return app


def validate_config() -> None:
    for name,value,allowed in (("SCORE_MODE",SCORE_MODE,{"LEGACY","EVIDENCE"}),
        ("SCORE_CVD_SOURCE",SCORE_CVD_SOURCE,{"AUTO","WS","PROXY"}),
        ("SPOOF_SOURCE",SPOOF_SOURCE,{"AUTO","REST","LEGACY"}),
        ("TIME_EXIT_MODE",TIME_EXIT_MODE,{"HARD","MIN_PROFIT"})):
        if value not in allowed:
            raise ValueError(name+" geçersiz: "+str(value))
    if min(MEXC_REFRESH_SEC,MEXC_STALE_SEC,MEXC_HTTP_TIMEOUT) <= 0 or SPOOF_CACHE_SEC < 0:
        raise ValueError("Veri kaynaklarının süreleri geçersiz")
    if TIME_EXIT_MAX_HOURS < 0 or (TIME_EXIT_MAX_HOURS and TIME_EXIT_MAX_HOURS < TIME_EXIT_HOURS):
        raise ValueError("TIME_EXIT_MAX_HOURS sıfır veya ilk çıkış saatinden büyük olmalı")
    if RSI_METHOD not in ('LEGACY','WILDER'):
        raise ValueError('RSI_METHOD LEGACY/WILDER olmalı')
    if BALINA_WS_BOOK_CHANNEL not in ('books','books5') or BALINA_WS_FAIL_POLICY not in ('REST','BLOCK'):
        raise ValueError('WS kanal/fail policy geçersiz')
    if not 0<SABIT_STOP_PCT<100 or SABIT_STOP_PCT*TP4_RR>=100:
        raise ValueError('Stop/SHORT TP fiyatı geçersiz')
    if not 0<TP1_RR<TP2_RR<TP3_RR<TP4_RR:
        raise ValueError('TP R seviyeleri pozitif ve artan olmalı')
    if min(HTTP_TIMEOUT,OKX_EXECUTOR_WORKERS,ENTRY_MAX_AGE_SEC,PAPER_HISTORY_MAX_PAGES)<=0:
        raise ValueError('Süre/worker/sayfa sınırı pozitif olmalı')
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError(f"Eksik env: {', '.join(missing)}")
    if not OKX_BASE_URL.startswith("https://"):
        raise RuntimeError("OKX_BASE_URL HTTPS olmalı")
    if SIM_AMBIGUOUS_BAR_POLICY not in ("STOP_FIRST", "TP_FIRST"):
        raise RuntimeError("SIM_AMBIGUOUS_BAR_POLICY STOP_FIRST veya TP_FIRST olmalı")
    if not (0.0 <= OLCUM_RASTGELE_ORAN <= 1.0):
        raise RuntimeError("OLCUM_RASTGELE_ORAN 0 ile 1 arasında olmalı")
    if min(SABIT_STOP_PCT, TP1_RR, TP2_RR, TP3_RR, TP4_RR) <= 0:
        raise RuntimeError("Stop ve TP R değerleri pozitif olmalı")
    db_dizin = os.path.dirname(os.path.abspath(OLCUM_DB))
    try:
        os.makedirs(db_dizin, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"OLCUM_DB dizini oluşturulamadı: {db_dizin}: {e}") from e


    if GIZLI_MAX_OPEN<1 or not math.isfinite(GIZLI_MIN_OI_PCT) or not all(math.isfinite(x) and x>0 for x in (TAKIP_SAAT,GOLGE_SAAT)):
        raise RuntimeError('Gizli limit ve izleme süreleri geçersiz')
    if any(k not in OLCUM_KAPILARI for k in GIZLI_GEREKLI_KAPILAR):
        raise RuntimeError('GIZLI_GEREKLI_KAPILAR içinde bilinmeyen kapı var')

def main() -> None:
    validate_config()
    _new_storage_preflight()
    load_memory()
    global app
    app = build_app()
    logger.info("%s başlıyor", VERSION_NAME)
    try:
        app.run_polling(close_loop=True, drop_pending_updates=True)
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



# === V12.1.0 kalıcı defter / bildirim kuyruğu ===
_DB_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ledger")
_OKX_SLOTS = asyncio.Semaphore(OKX_EXECUTOR_WORKERS)
_SIGNAL_LOCK = asyncio.Lock()
_BACKGROUND_TASKS = set()
_HTTP_LOCAL = threading.local()
_HTTP_SESSIONS = []
_SHUTTING_DOWN = False
_BALINA_LAST_RETENTION = 0.0


class OKXRequestError(RuntimeError):
    def __init__(self, message, code="", retryable=False, retry_after=0.0):
        super().__init__(message)
        self.code, self.retryable, self.retry_after = code, retryable, retry_after


class TelegramDeliveryError(RuntimeError):
    def __init__(self, code, retry_after=0):
        super().__init__(f"Telegram HTTP/API {code}")
        self.retry_after = max(0.0, safe_float(retry_after))
        self.permanent = code in (400, 401, 403, 404)


def _http_session():
    session = getattr(_HTTP_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": f"BalinaAvcisi/{BOT_BUILD}"})
        _HTTP_LOCAL.session = session
        _HTTP_SESSIONS.append(session)
    return session


async def _db_call(fn, *args):
    # Kopan/cancel edilen coroutine, devam eden DB transaction'ını kesmez.
    future = asyncio.get_running_loop().run_in_executor(_DB_EXECUTOR, functools.partial(fn, *args))
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        # Kapanışta transaction tamamlandıktan sonra JSON snapshot alınır.
        await asyncio.shield(future)
        raise


def _cohort():
    return f"V12.1.0-TP1FULL:{config_fingerprint()}"


def _adx_regime(value):
    return "TREND" if value >= ADX_TREND_THRESHOLD else "RANGE" if value < ADX_RANGE_THRESHOLD else "GECIS"


def _rsi_wilder(values, period=14):
    out = [50.0] * len(values)
    if len(values) <= period:
        return out
    diffs = [values[i] - values[i-1] for i in range(1, len(values))]
    gain = sum(max(x, 0) for x in diffs[:period]) / period
    loss = sum(max(-x, 0) for x in diffs[:period]) / period
    def value(g, l):
        return 50.0 if g == l == 0 else 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    out[period] = value(gain, loss)
    for i in range(period+1, len(values)):
        gain = (gain * (period-1) + max(diffs[i-1], 0)) / period
        loss = (loss * (period-1) + max(-diffs[i-1], 0)) / period
        out[i] = value(gain, loss)
    return out


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _db_payload(pos, previous=None):
    payload = dict(previous or pos.get("kapi_sonuclari") or {})
    payload.setdefault("_ozellikler", pozisyon_ozellikleri(pos))
    for i in range(1, 5):
        payload[f"_hit{i}"] = bool(payload.get(f"_hit{i}") or pos.get(f"hit{i}"))
    payload["_coverage"] = pos.get("coverage", "LEGACY_UNVERIFIED")
    payload["_cohort"] = pos.get("cohort", "LEGACY")
    return payload


def _db_insert_position(conn, pos):
    conn.execute("""INSERT OR IGNORE INTO olcum_pozisyon
        (uid,symbol,side,kontrol,open_ts,durum,r_value,mfe_pct,mae_pct,kapi_json,
         position_json,build,config_hash,cohort)
        VALUES(?,?,?,?,?,'ACIK',?,?,?,?,?,?,?,?)""",
        (v107_pos_uid(pos), pos["symbol"], pos["side"], int(bool(pos.get("kontrol"))),
         pos["open_ts"], safe_float(pos.get("current_r")), safe_float(pos.get("mfe_pct")),
         safe_float(pos.get("mae_pct")), _json(_db_payload(pos)), _json(pos),
         pos.get("build", BOT_BUILD), pos.get("config_hash", config_fingerprint()), pos.get("cohort", "LEGACY")))


def _db_update_position(conn, pos, durum="ACIK", r_value=None):
    _db_insert_position(conn, pos)
    old = conn.execute("SELECT durum,kapi_json,mfe_pct,mae_pct FROM olcum_pozisyon WHERE uid=?",
                       (pos["uid"],)).fetchone()
    if old[0] != "ACIK":
        return False  # Kapanmış UID tekrar açılamaz/kapatılamaz.
    payload = _db_payload(pos, json.loads(old[1] or "{}"))
    for i in range(1, 5):
        pos[f"hit{i}"] = payload[f"_hit{i}"]
    pos["mfe_pct"] = max(safe_float(old[2]), safe_float(pos.get("mfe_pct")))
    pos["mae_pct"] = max(safe_float(old[3]), safe_float(pos.get("mae_pct")))
    closed = durum != "ACIK"
    rv = safe_float(pos.get("current_r")) if r_value is None else safe_float(r_value)
    cost = simulasyon_maliyet_r(pos) if closed else 0.0
    close_ts = safe_float(pos.get("close_ts"), time.time()) if closed else None
    conn.execute("""UPDATE olcum_pozisyon SET durum=?,close_ts=?,r_value=?,net_r_value=?,cost_r=?,
        mfe_pct=?,mae_pct=?,kapi_json=?,position_json=?,sonuc_tipi=? WHERE uid=? AND durum='ACIK'""",
        (durum, close_ts, rv, rv-cost, cost, pos["mfe_pct"], pos["mae_pct"], _json(payload), _json(pos),
         sonuc_tipi_belirle(durum, pos) if closed else None, pos["uid"]))
    return True


def _outbox_insert(conn, event_id, pos, kind, text, sig=None):
    conn.execute("""INSERT OR IGNORE INTO notification_outbox
        (event_id,uid,kind,payload,created_ts) VALUES(?,?,?,?,?)""",
        (event_id, pos["uid"], kind, _json({"text": text, "signal": sig}), time.time()))


def _persist_open(pos, sig):
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute('SELECT position_json FROM olcum_pozisyon WHERE uid=?',(pos['uid'],)).fetchone()
        if existing:
            return json.loads(existing[0])
        old = conn.execute("SELECT value FROM schema_meta WHERE key='signal_seq'").fetchone()
        number = max(int(old[0]) if old else 0, int(memory.get("signal_seq", 0)), int(stats.get("v10_signals", 0))) + 1
        pos["signal_no"] = sig["signal_no"] = number
        _db_insert_position(conn, pos)
        _audit_tx(conn,"PAPER_OPEN",pos)
        _outbox_insert(conn, pos["uid"] + ":OPEN", pos, "OPEN", build_v10_message(sig), sig)
        conn.execute("INSERT OR REPLACE INTO schema_meta VALUES('signal_seq',?)", (str(number),))
    return pos


def _closed_record(pos, r_value, outcome):
    record = copy.deepcopy(pos)
    record.update(R=round(r_value, 3), outcome=outcome,
                  sonuc_tipi=sonuc_tipi_belirle(outcome, pos),
                  close_ts=safe_float(pos.get("close_ts"), time.time()))
    record["tutma_dk"] = round((record["close_ts"] - pos["open_ts"]) / 60, 1)
    return record


def _shadow_from_position(pos):
    stop_ts = safe_float(pos.get("shadow_start_ts"), pos["close_ts"])
    return {"uid": pos["uid"], "symbol": pos["symbol"], "side": pos["side"],
            "entry": pos["entry"], **{f"tp{i}": pos[f"tp{i}"] for i in range(1, 5)},
            "stop_ts": stop_ts, "scan_ts": 0.0, "kontrol": bool(pos.get("kontrol")),
            "golge_tp": 0, "golge_mfe_pct": 0.0, "golge_mae_pct": 0.0,
            "end_ts": stop_ts + max(0.0, GOLGE_SAAT) * 3600,
            "coverage": "COMPLETE", **{f"golge_tp{i}_dk": None for i in range(1, 5)}}


def _persist_paper_step(pos, r_value=None, outcome=None):
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not _db_update_position(conn,pos,outcome or 'ACIK',r_value): return None
        if outcome:
            _audit_tx(conn,'PAPER_CLOSE',dict(pos,R=r_value,outcome=outcome))
            _outbox_insert(conn,pos['uid']+':CLOSE',pos,'CLOSE',build_v10_close_message(pos,r_value,outcome,pos['exit_price']))
            _follow_insert(conn,pos,outcome,'MAIN')
    return None


def _restore_ledger():
    """SQLite commit edilmiş kayıtlar JSON'dan üstün; eski JSON tek başına da korunur."""
    mp = _v10_mem()
    old_open = {v107_pos_uid(p): p for p in mp["open"]}
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        for p in old_open.values():
            _db_insert_position(conn, p)
        rows = conn.execute("SELECT * FROM olcum_pozisyon ORDER BY open_ts").fetchall()
    opens, closed, shadows, unresolved = [], [], {}, []
    for row in rows:
        r = dict(row)
        payload = json.loads(r["kapi_json"] or "{}")
        p = json.loads(r.get("position_json") or "{}") or copy.deepcopy(old_open.get(r["uid"], {}))
        p.update(uid=r["uid"], symbol=r["symbol"], side=r["side"], kontrol=bool(r["kontrol"]),
                 open_ts=r["open_ts"], current_r=r["r_value"],
                 mfe_pct=max(safe_float(p.get("mfe_pct")), r["mfe_pct"]),
                 mae_pct=max(safe_float(p.get("mae_pct")), r["mae_pct"]))
        p.setdefault("kapi_sonuclari", {k: payload.get(k, "olcumsuz") for k in OLCUM_KAPILARI})
        for i in range(1, 5):
            p[f"hit{i}"] = bool(p.get(f"hit{i}") or payload.get(f"_hit{i}"))
        p.setdefault("cohort", r.get("cohort") or "LEGACY")
        if r["durum"] == "ACIK":
            if safe_float(p.get("entry")) > 0 and safe_float(p.get("orig_stop")) > 0 and all(safe_float(p.get(f"tp{i}")) > 0 for i in range(1, 5)):
                # Kaybolan eski MFE'yi tahmin ederek üretme; eldeki maxima korunur.
                p.setdefault("coverage", "LEGACY_UNVERIFIED")
                opens.append(p)
            else:
                unresolved.append(p)
                logger.error("Kurtarılamayan açık UID %s: JSON'da giriş/TP gerekiyor", r["uid"])
                stats["recovery_missing_position"] = int(stats.get("recovery_missing_position", 0)) + 1
        else:
            p["close_ts"] = r["close_ts"]
            closed.append(_closed_record(p, r["r_value"], r["durum"]))
        if r["golge_durum"] == "IZLENIYOR":
            g = json.loads(r.get("shadow_json") or "{}")
            if g:
                shadows[r["uid"]] = g
        if p.get("candle_ts"):
            symbol = p["symbol"]
            if safe_float(p["candle_ts"]) >= safe_float(v10_sent_candle.get(symbol)):
                v10_sent_candle[symbol] = p["candle_ts"]
            v10_last_alert[symbol] = max(safe_float(v10_last_alert.get(symbol)), p["open_ts"])
        memory["signal_seq"] = max(int(memory.get("signal_seq", 0)), int(p.get("signal_no", 0)))
    # JSON-only tarihçe, ilk SQLite sürümünden önce bulunabilir.
    for legacy in mp["closed"]:
        if any((legacy.get("uid") and legacy.get("uid") == c.get("uid")) or
               (legacy.get("symbol") == c.get("symbol") and legacy.get("side") == c.get("side") and
                abs(safe_float(legacy.get("close_ts"))-safe_float(c.get("close_ts"))) < 2)
               for c in closed):
            continue
        closed.append(legacy)
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        done = {r[0] for r in conn.execute("SELECT uid FROM olcum_pozisyon WHERE golge_durum='BITTI'")}
    for g in mp.get("golge", []):
        if g.get("uid") not in done:
            shadows.setdefault(g["uid"], g)
    mp.update(open=opens, closed=closed, golge=list(shadows.values()), recovery_pending=unresolved)
    stats['v10_signals'] = max(int(stats.get('v10_signals',0)),len(rows))
    stats['recovery_missing_position'] = len(unresolved)


def _outbox_next():
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        if not GIZLI_TELEGRAM_ENABLED:
            conn.execute("UPDATE notification_outbox SET sent_ts=?,last_error='GIZLI_DISABLED_SUPPRESSED' WHERE kind='GIZLI' AND sent_ts IS NULL",(time.time(),))
        row = conn.execute("""SELECT a.* FROM notification_outbox a WHERE a.sent_ts IS NULL AND a.next_ts<=?
            AND NOT EXISTS(SELECT 1 FROM notification_outbox b WHERE b.uid=a.uid
            AND b.sent_ts IS NULL AND b.rowid<a.rowid) ORDER BY a.rowid LIMIT 1""", (time.time(),)).fetchone()
        return dict(row) if row else None


def _outbox_update(event_id, part=None, sent=False, error=None, delay=0):
    with _OLCUM_DB_LOCK, sqlite3.connect(OLCUM_DB, timeout=10) as conn:
        if error is not None:
            conn.execute("UPDATE notification_outbox SET attempts=attempts+1,next_ts=?,last_error=? WHERE event_id=?",
                         (time.time()+delay, str(error)[:240], event_id))
        elif sent:
            conn.execute("UPDATE notification_outbox SET sent_ts=?,last_error=NULL WHERE event_id=?", (time.time(), event_id))
        else:
            conn.execute("UPDATE notification_outbox SET part_index=? WHERE event_id=?", (part, event_id))


async def notification_loop():
    while True:
        item = await _db_call(_outbox_next)
        if item is None:
            await asyncio.sleep(0.5)
            continue
        payload = json.loads(item["payload"])
        try:
            parts = telegram_parcala(payload["text"])
            for i in range(item["part_index"], len(parts)):
                await asyncio.to_thread(_telegram_api_send, parts[i])
                await _db_call(_outbox_update, item["event_id"], i+1)
                await asyncio.sleep(max(0.05, NOTIFICATION_INTERVAL_SEC))
            await _db_call(_outbox_update, item["event_id"], None, True)
            stats["notification_sent"] = int(stats.get("notification_sent", 0)) + 1
            # Grafik/haber başarısızlığı ana bildirimi tekrar göndermez.
            sig = payload.get("signal")
            if sig and SIGNAL_CHART_ENABLED and _MPL_OK:
                try:
                    png = await render_signal_chart(sig["symbol"], sig["direction"], sig["entry"], sig["stop"],
                                                    {f"TP{i}": sig[f"tp{i}"] for i in range(1, 5)}, sig)
                    if png:
                        await safe_send_telegram_photo(f"Paper sinyal #{sig['signal_no']} | {sig['symbol']}", png)
                except Exception:
                    logger.exception("Sinyal grafiği gönderilemedi")
            if sig and SIGNAL_NEWS_ENABLED:
                news = await fetch_coin_news(sig["symbol"])
                if news:
                    await safe_send_telegram(f"📰 #{sig['signal_no']} {sig['symbol']}\n{news}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            delay = max(getattr(exc, "retry_after", 0), min(300, 2 ** min(8, item["attempts"])))
            if getattr(exc, "permanent", False):
                delay = 3600
            await _db_call(_outbox_update, item["event_id"], None, False, type(exc).__name__, delay)
            stats["telegram_fail"] += 1
            logger.warning("Bildirim kuyrukta kaldı: %s (%s)", item["event_id"], type(exc).__name__)


async def _supervised(factory):
    while not _SHUTTING_DOWN:
        try:
            await factory()
            if not _SHUTTING_DOWN:
                raise RuntimeError(f"{factory.__name__} beklenmeden sonlandı")
        except asyncio.CancelledError:
            raise
        except Exception:
            stats["task_restart"] = int(stats.get("task_restart", 0)) + 1
            logger.exception("Döngü yeniden başlatılacak: %s", factory.__name__)
            await asyncio.sleep(5)


def _start_loop(factory):
    task = asyncio.create_task(_supervised(factory), name=factory.__name__)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def post_stop(application):
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = True
    tasks = list(_BACKGROUND_TASKS)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await _db_call(_restore_ledger)
    await save_memory_async()


async def post_shutdown(application):
    if not _SHUTTING_DOWN:
        await post_stop(application)
    await asyncio.to_thread(OKX_EXECUTOR.shutdown, wait=True, cancel_futures=True)
    await asyncio.to_thread(_DB_EXECUTOR.shutdown, wait=True, cancel_futures=True)
    for session in _HTTP_SESSIONS:
        session.close()
    SESSION.close()



async def _live_entry_quote(symbol, side):
    rows = await _okx_get_async("/api/v5/market/books", {"instId": symbol, "sz": 5})
    if not rows:
        raise ValueError("boş orderbook")
    book = rows[0]
    ts = safe_float(book.get("ts"))/1000
    bid = safe_float((book.get("bids") or [[0]])[0][0])
    ask = safe_float((book.get("asks") or [[0]])[0][0])
    age = time.time()-ts
    if not (0 < bid <= ask) or ts <= 0 or age > ENTRY_MAX_AGE_SEC or age < -2:
        raise ValueError("eski veya geçersiz orderbook")
    return {"price": ask if side == "LONG" else bid, "ts": ts,
            "source": "orderbook ask" if side == "LONG" else "orderbook bid"}


def _balina_gate(sig):
    if not BALINA_MOTOR_ENABLED or not (BALINA_KARLI_KAPI_ENABLED or BALINA_MOTOR_BLOCK):
        return True, "kapalı"
    snap = sig.get("balina_akis") or {}
    if snap.get("status") != "CANLI":
        return BALINA_WS_FAIL_POLICY == "REST", "WS ölçümsüz; REST sinyal motoru"
    state = str(snap.get("durum", ""))
    long_states = {"SATIS_EMILIMI", "BALINA_ALIMI", "BIRIKIM", "PARCALI_BALINA_ALIMI"}
    short_states = {"ALIS_EMILIMI", "BALINA_SATISI", "DAGITIM", "PARCALI_BALINA_SATISI"}
    aligned = long_states if sig["direction"] == "LONG" else short_states
    opposite = short_states if sig["direction"] == "LONG" else long_states
    if BALINA_KARLI_KAPI_ENABLED and (state not in BALINA_KARLI_DURUMLAR or state not in aligned):
        return False, "durum/yön allowlist dışında"
    if BALINA_MOTOR_BLOCK and state in opposite and safe_float(snap.get("guven")) >= 70:
        return False, "ters yön akışı"
    return True, "uygun"



async def _history_raw(symbol, interval, start_ms, end_ms, step_ms):
    """[start,end) kapalı mumlar; sayfa/interval boşluğu ayrıca bildirilir."""
    start_ms, end_ms = int(start_ms), int(end_ms)
    if start_ms >= end_ms:
        return [], True
    rows, after = {}, str(end_ms)
    for _ in range(max(1,PAPER_HISTORY_MAX_PAGES)):
        data = await _okx_get_async('/api/v5/market/history-candles',
            {'instId':symbol,'bar':interval,'limit':300,'after':after})
        if not data:
            break
        oldest = min(int(safe_float(r[0])) for r in data)
        for raw in data:
            if len(raw)<9 or str(raw[8])!='1':
                continue
            ts = int(safe_float(raw[0]))
            if start_ms <= ts and ts+step_ms <= end_ms:
                rows[ts] = _okx_to_kline(raw)+[step_ms]
        if oldest <= start_ms or oldest >= int(after):
            break
        after = str(oldest)
    result = [rows[t] for t in sorted(rows)]
    complete = (len(result)==max(0,(end_ms-start_ms)//step_ms) and
                all(int(r[0])==start_ms+i*step_ms for i,r in enumerate(result)))
    return result, complete


def _paper_process_rows(pos, rows):
    """Mumları sırayla işler; çıkış sonrası fiyatları aynı işlemde saymaz."""
    for raw in rows:
        row = list(raw)
        ts = safe_float(row[0])/1000
        duration = safe_float(row[9])/1000 if len(row)>9 else interval_minutes(V107_TAKIP_TF)*60
        if ts < pos['open_ts'] or ts*1000 < safe_float(pos.get('scan_ts')):
            continue
        expected = max(int(pos['open_ts']*1000),int(safe_float(pos.get('scan_ts'))))
        expected = ((expected+999)//1000)*1000
        if int(row[0]) != expected:
            _history_gap(pos,expected,int(row[0])); break
        R, outcome = v107_check_paper_bar(pos,safe_float(row[2]),safe_float(row[3]))
        close_at = ts+duration
        if outcome:
            pos['exit_observation']={'hi':safe_float(row[2]),'lo':safe_float(row[3]),'close':safe_float(row[4]),'start_ts':ts,'duration':duration}
            if outcome=='STOP':
                exit_price = pos['orig_stop']
                if pos['side']=='LONG':
                    row[2],row[3] = max(pos['entry'],safe_float(row[1])), min(exit_price,safe_float(row[1]))
                else:
                    row[2],row[3] = max(exit_price,safe_float(row[1])), min(pos['entry'],safe_float(row[1]))
            else:
                exit_price = pos['tp1']
                if pos['side']=='LONG':
                    row[2],row[3] = exit_price,min(pos['entry'],safe_float(row[1]))
                else:
                    row[2],row[3] = max(pos['entry'],safe_float(row[1])),exit_price
            row[4] = exit_price
            pos.update(excursion_exit_bound=True,event_resolution_sec=duration,
                       close_ts=close_at,shadow_start_ts=close_at,exit_price=exit_price)
        v10_update_excursions(pos,[row])
        pos.update(last_price=safe_float(row[4]),last_price_ts=close_at,scan_ts=close_at*1000)
        if outcome:
            pos.pop('history_gap',None)
            return R,outcome
        if _time_exit_due(pos, close_at):
            risk = abs(pos['entry']-pos['orig_stop'])
            move = (pos['last_price']-pos['entry'])*(1 if pos['side']=='LONG' else -1)
            R = _paper_time_exit_r(pos,move/risk) if risk else 0.0
            pos.update(close_ts=close_at,exit_price=pos['last_price'])
            return round(R,3),'TIME_EXIT'
    return None,None


async def paper_tur():
    mp = _v10_mem()
    for original in list(mp['open']):
        _RUNTIME_HEALTH['paper_heartbeat'] = time.time()
        pos = copy.deepcopy(original)
        try:
            rows,_ = await v107_takip_barlari(pos)
            if not rows:
                await _db_call(_persist_paper_step,pos,None,None)
                original.clear(); original.update(pos)
                continue
            R,outcome = _paper_process_rows(pos,rows)
            shadow = await _db_call(_persist_paper_step,pos,R,outcome)
            if outcome:
                v10_record_closed(pos,R,outcome)
                mp['open'] = [p for p in mp['open'] if p.get('uid')!=pos['uid']]
                if shadow and not any(g.get('uid')==shadow['uid'] for g in mp['golge']):
                    mp['golge'].append(shadow)
            else:
                pos.pop('pending_hits',None)
                original.clear()
                original.update(pos)
        except asyncio.CancelledError:
            raise
        except Exception:
            stats['paper_position_error'] = int(stats.get('paper_position_error',0))+1
            logger.exception('Paper UID %s hatası; diğer pozisyonlar sürüyor',pos.get('uid'))



async def golge_tur():
    await _continuation_tur()



def _report_rows():
    rows = olcum_db_ortak_satirlari()
    if REPORT_CURRENT_COHORT_ONLY:
        rows = [r for r in rows if r.get('cohort')==_cohort()]
    if REPORT_REQUIRE_COMPLETE:
        rows = [r for r in rows if r.get('coverage') in ('COMPLETE','SUBSECOND_ENTRY_OMITTED')]
    return rows


def _report_scope():
    rows=olcum_db_ortak_satirlari()
    included=[r for r in rows if (not REPORT_CURRENT_COHORT_ONLY or r.get('cohort')==_cohort()) and (not REPORT_REQUIRE_COMPLETE or r.get('coverage') in ('COMPLETE','SUBSECOND_ENTRY_OMITTED'))]
    excluded=len(rows)-len(included)
    with sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        waiting=sum(bool(json.loads(p or '{}').get('history_gap')) for p, in conn.execute('SELECT position_json FROM olcum_pozisyon'))
    return (f'Yeni seri: {_cohort()} | Toplam {len(rows)} | Dahil {len(included)} | Kapsam/veri nedeniyle dışlanan {excluded} | Mum bekleyen {waiting}\n'
            'Eski sürüm ve gizli motor hariç. Girişin <1 saniyesi atlanır; aynı saniyede STOP önce kabul edilir.')


def _metric(value, digits=3):
    return '— (ölçümsüz)' if value is None else f'{value:+.{digits}f}'


def _mean_present(rows,key):
    values = [safe_float(r[key]) for r in rows if r.get(key) is not None]
    return avg(values) if values else None


def _combo_partition(rows,keys):
    passed,failed,unknown = [],[],[]
    for row in rows:
        conditions = row.get('_conditions') or _kombinasyon_kosullari(row)
        values = [conditions[k] for k in keys]
        (unknown if any(v is None for v in values) else failed if False in values else passed).append(row)
    return passed,failed,unknown


def _comparison_lines(first,second,unknown=0):
    a,b = _kombinasyon_metrik(first),_kombinasyon_metrik(second)
    lines = [_kombinasyon_metrik_satiri('Geçen',a),_kombinasyon_metrik_satiri('Geçmeyen',b),
             f'Ölçümsüz: {unknown}']
    delta = lambda k: None if a[k] is None or b[k] is None else a[k]-b[k]
    lines.append('Fark: Δtemiz stop '+_metric(delta('temiz_pct'),1)+' puan | '+
                 ' | '.join(f'ΔTP{i} '+_metric(delta(f'tp{i}_pct'),1)+' puan' for i in range(1,5))+
                 ' | ΔR '+_metric(delta('r'))+' | ΔMFE %'+_metric(delta('mfe'))+' | ΔMAE %'+_metric(delta('mae')))
    ready = min(a['kapanan'],b['kapanan'])>=KOMBINASYON_MIN_KAPANIS
    lines.append(('ÖRNEK EŞİĞİ TAMAM; ileri doğrulama gerekir' if ready else 'KARAR YOK')+
                 f": kapanan geçen={a['kapanan']}, geçmeyen={b['kapanan']}")
    return lines



def status_raporu_uret():
    text=_engine_report('MAIN')
    return text + (f"\nCoin havuzu: {len(COINS)} | Analiz {stats.get('v10_analyzed',0)} | Aday {stats.get('v10_candidates',0)}"
        f"\nAnaliz hatası {stats.get('analysis_error',0)} | Paper hata {stats.get('paper_position_error',0)}"
        f"\nOKX timeout {stats.get('okx_timeout',0)} | DB yazım hatası {stats.get('ledger_write_fail',0)}")



def _persistence_warnings():
    root = os.path.realpath(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data"))
    mounts = set()
    try:
        with open("/proc/self/mountinfo", encoding="utf-8") as stream:
            for line in stream:
                fields = line.split()
                if len(fields) > 4:
                    mounts.add(os.path.realpath(fields[4].replace("\\040", " ")))
    except OSError:
        pass
    warnings = []
    for name,path in (("OLCUM_DB",OLCUM_DB),("MEMORY_FILE",MEMORY_FILE),("BALINA_DB",BALINA_DB)):
        directory = os.path.realpath(os.path.dirname(os.path.abspath(path)))
        if root not in mounts or os.path.commonpath([root,directory]) != root or not os.access(directory,os.W_OK):
            warnings.append(f"⚠️ {name}: yazılabilir ayrı kalıcı bağlama doğrulanamadı; deploy'da veri kaybı olabilir")
    return warnings



def _enqueue_system_notification(text):
    uid = 'SYSTEM:'+uuid.uuid4().hex
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        _outbox_insert(conn,uid,{'uid':uid},'SYSTEM',text)


def _audit_tx(conn,event,pos):
    if AUDIT_ENABLED:
        conn.execute('INSERT INTO audit_event(ts,event_type,uid,symbol,build,config_hash,payload_json) VALUES(?,?,?,?,?,?,?)',
            (time.time(),event,pos['uid'],pos['symbol'],pos.get('build',BOT_BUILD),
             pos.get('config_hash',config_fingerprint()),_json(pos)))


# === V12.1.0 VERİ KAYNAKLARI VE ÖLÇÜLEBİLİR SKOR ===
_MEXC_CACHE = {"instruments": {}, "tickers": {}, "ts": 0.0, "meta_ts": 0.0, "error": ""}
_SPOOF_CACHE = {}
_SPOOF_LOCKS = {}
_CVD_REST_CACHE = {}


def fibonacci_context(k, side):
    """Yalnız sağında yeterli kapanmış mum bulunan pivotlardan son yönlü çift."""
    if side not in ("LONG", "SHORT"):
        return {}
    k = _s_closed(k)
    left, right = max(1, V10_SWING_LEFT), max(1, V10_SWING_RIGHT)
    pivots = []
    for i in range(left, len(k)-right):
        segment = k[i-left:i+right+1]
        h, l = safe_float(k[i][2]), safe_float(k[i][3])
        hs, ls = highs(segment), lows(segment)
        if h == max(hs) and hs.count(h) == 1:
            pivots.append((i, "H", h))
        if l == min(ls) and ls.count(l) == 1:
            pivots.append((i, "L", l))
    start_kind, end_kind = ("L", "H") if side == "LONG" else ("H", "L")
    for end in reversed(pivots):
        if end[1] != end_kind:
            continue
        starts = [p for p in pivots if p[0] < end[0] and p[1] == start_kind]
        if not starts:
            continue
        start = starts[-1]
        direction = 1 if side == "LONG" else -1
        span = (end[2]-start[2])*direction
        if span <= 0:
            continue
        depth = (end[2]-safe_float(k[-1][4]))*direction/span
        return {"start_ts": k[start[0]][0], "end_ts": k[end[0]][0],
                "start": start[2], "end": end[2], "depth": depth,
                "levels": {str(r): end[2]-direction*span*r for r in (.382,.5,.618,.786)},
                "quality": 1.0 if .382 <= depth <= .618 else .5 if .618 < depth <= .786 else 0.0}
    return {}


def _time_exit_due(pos, now):
    # Eski kayıtlar kendi tarihsel HARD çıkışını sürdürür.
    policy = pos.get("time_exit_policy") or {"enabled": TIME_EXIT_ENABLED,
                "mode": "HARD", "hours": TIME_EXIT_HOURS}
    if not policy.get("enabled", True):
        return False
    age = (now-safe_float(pos.get("open_ts")))/3600
    if age < safe_float(policy.get("hours"), 48):
        return False
    if policy.get("mode") == "HARD":
        return True
    maximum = safe_float(policy.get("max_hours"))
    if maximum > 0 and age >= maximum:
        return True
    risk = abs(pos["entry"]-pos["orig_stop"])
    if risk <= 0:
        return False
    move = (pos["last_price"]-pos["entry"])*(1 if pos["side"] == "LONG" else -1)/risk
    # Gerçekleşmiş parçalar + kalan pozisyon; eski R formülü değişmez.
    return _paper_time_exit_r(pos, move) >= safe_float(policy.get("min_r"), .5)


def _mexc_http(path):
    response = _http_session().get(MEXC_BASE_URL+path, timeout=MEXC_HTTP_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is not True or str(payload.get("code")) != "0":
        raise RuntimeError("MEXC market API başarısız")
    return payload.get("data")


def _mexc_instruments(rows):
    result = {}
    for row in rows if isinstance(rows, list) else []:
        base = str(row.get("baseCoin", "")).upper()
        if not base or row.get("quoteCoin") != "USDT" or row.get("settleCoin") != "USDT":
            continue
        if str(row.get("state", "0")) != "0" or str(row.get("futureType", "1")) != "1":
            continue
        if safe_float(row.get("contractSize")) <= 0 or row.get("symbol") != base+"_USDT":
            continue
        result[base+"-USDT-SWAP"] = dict(row)
    return result


async def mexc_market_loop():
    # Tek sıralı worker çağrısı: timeout'ta yeni thread yığılmaz.
    while True:
        try:
            if time.time()-_MEXC_CACHE["meta_ts"] > 1800:
                data = await asyncio.to_thread(_mexc_http, "/api/v1/contract/detail")
                _MEXC_CACHE["instruments"] = _mexc_instruments(data)
                _MEXC_CACHE["meta_ts"] = time.time()
            data = await asyncio.to_thread(_mexc_http, "/api/v1/contract/ticker")
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            _MEXC_CACHE.update(tickers={r["symbol"]: r for r in rows if r.get("symbol")},
                               ts=time.time(), error="")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _MEXC_CACHE["error"] = type(exc).__name__
            stats["mexc_api_fail"] = int(stats.get("mexc_api_fail", 0))+1
            logger.warning("MEXC ikincil veri alınamadı: %s", type(exc).__name__)
        await asyncio.sleep(max(5, MEXC_REFRESH_SEC))


def mexc_snapshot(symbol):
    out = {"source": "MEXC_REST", "status": "KAPALI" if not MEXC_ENABLED else "VERI_YOK"}
    if not MEXC_ENABLED:
        return out
    instrument = _MEXC_CACHE["instruments"].get(normalize_symbol(symbol))
    if not instrument:
        return out
    row = _MEXC_CACHE["tickers"].get(instrument["symbol"])
    if not row:
        return out
    ts = safe_float(row.get("timestamp"))/1000
    age = time.time()-ts
    if ts <= 0 or age < -5 or age > MEXC_STALE_SEC or time.time()-_MEXC_CACHE["ts"] > MEXC_STALE_SEC:
        out["status"] = "BAYAT"
        return out
    price = safe_float(row.get("lastPrice"))
    out.update(status="CANLI", ts=ts, symbol=instrument["symbol"], price=price,
        funding=safe_float(row.get("fundingRate")), turnover_24h_usdt=safe_float(row.get("amount24")),
        oi_notional_estimate_usdt=safe_float(row.get("holdVol"))*safe_float(instrument["contractSize"])*price)
    return out


async def cmd_mexc(update, context):
    if not telegram_yetkili(update):
        return
    symbol = normalize_symbol(context.args[0]) if context.args else "BTC-USDT-SWAP"
    data = mexc_snapshot(symbol)
    await update.message.reply_text("MEXC İKİNCİL VERİ | "+symbol+"\n"+json.dumps(data, ensure_ascii=False)+
                                   "\nOKX giriş/çıkış fiyatını değiştirmez.")


def _taker_cvd(rows, symbol, now, window=60):
    # 500 kayıt sınırına takılan pencere tam CVD olarak sunulmaz.
    cutoff = (now-window)*1000
    timestamps = [safe_float(r.get("ts")) for r in rows]
    if not timestamps or (len(rows) >= 500 and min(timestamps) > cutoff):
        return None
    selected = [r for r in rows if cutoff <= safe_float(r.get("ts")) <= now*1000]
    buy = sell = 0.0
    seen = set()
    for row in selected:
        key = row.get("tradeId")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        price, qty = safe_float(row.get("px")), safe_float(row.get("sz"))
        value = _balina_contract_value(symbol, price, qty)
        if value <= 0 or row.get("side") not in ("buy", "sell"):
            return None
        if row["side"] == "buy":
            buy += value
        else:
            sell += value
    total = buy+sell
    return {"cvd_value_usdt": buy-sell, "cvd_norm": (buy-sell)/total if total else 0.0,
            "cvd_source": "OKX_REST", "cvd_window_sec": window, "cvd_ts": now} if total else None


async def score_market_context(symbol, k, side):
    context = {"cvd_source": "CANDLE_PROXY", "cvd_value_usdt": None,
               "cvd_norm": None, "cvd_window_sec": None, "cvd_ts": time.time(),
               "fib": fibonacci_context(k, side), "mexc": mexc_snapshot(symbol), "score_mode": SCORE_MODE}
    if SCORE_CVD_SOURCE != "PROXY":
        snapshot = balina_snapshot(symbol) if BALINA_MOTOR_ENABLED else {}
        if snapshot.get("status") == "CANLI" and snapshot.get("flow_ready"):
            context.update(cvd_source="OKX_WS", cvd_value_usdt=snapshot.get("cvd_1m"),
                           cvd_norm=snapshot.get("cvd_norm_1m"), cvd_window_sec=60)
        elif SCORE_CVD_SOURCE == "AUTO":
            cached = _CVD_REST_CACHE.get(symbol)
            if not cached or time.time()-cached[0] > 5:
                try:
                    rows = await _okx_get_async("/api/v5/market/trades", {"instId": symbol, "limit": 500})
                    data = _taker_cvd(rows, symbol, time.time())
                except Exception:
                    data = None
                _CVD_REST_CACHE[symbol] = (time.time(), data)
                if len(_CVD_REST_CACHE) > 500:
                    _CVD_REST_CACHE.pop(next(iter(_CVD_REST_CACHE)))
            data = _CVD_REST_CACHE[symbol][1]
            if data:
                context.update(data)
    return {"market_context": context}


def v10_quality_score(side, k, ms, ext):
    score, parts, r, flags = _legacy_quality_score(side, k, ms, ext)
    if SCORE_MODE == "LEGACY":
        ext.setdefault("market_context", {})["score_cvd_source"] = "CANDLE_PROXY"
        return score, parts, r, flags
    # Ön şart olan yapı/BTC/4H uyumu tekrar sabit puan kazandırmaz.
    weights = {"volume": 2, "rsi": 7, "oi": 9, "funding": 7, "orderbook": 7,
               "order_block": 11, "fvg": 8, "volume_profile": 5, "cvd": 5, "sweep": 7}
    p = {name: max(0.0, parts.get(name, 0.0)) for name in weights}
    if ext.get("oi_change_pct") is None:
        p["oi"] = 0.0
    if ext.get("funding") is None:
        p["funding"] = 0.0
    if not ext.get("orderbook") or not ext["orderbook"].get("mid"):
        p["orderbook"] = 0.0
    # Eski zayıf/ters yöndeki pozitif tabanları kaldır.
    if p["order_block"] < 11:
        p["order_block"] = 0.0
    if p["volume_profile"] < 5:
        p["volume_profile"] = 0.0
    context = ext.get("market_context", {})
    norm = context.get("cvd_norm")
    if norm is not None and context.get("cvd_source") in ("OKX_WS", "OKX_REST"):
        p["cvd"] = 5*max(0.0, min(1.0, safe_float(norm)*(1 if side == "LONG" else -1)))
    else:
        cv = v10_cvd_proxy(k)
        p["cvd"] = 5.0 if cv*(1 if side == "LONG" else -1) > 0 else 0.0
    if SCORE_FIB_ENABLED:
        weights["fib"] = 5
        p["fib"] = 5*safe_float(context.get("fib", {}).get("quality"))
    flags.update(cvd=p["cvd"]>0, fib=p.get("fib",0)>0)
    score = 100*sum(p.values())/sum(weights.values())
    context["score_cvd_source"] = context.get("cvd_source", "CANDLE_PROXY")
    context["score_max_points"] = sum(weights.values())
    return round(score,1), {name:round(value,3) for name,value in p.items()}, r, flags


def _rest_wall_result(first, last, trades):
    start, end = safe_float(first.get("ts")), safe_float(last.get("ts"))
    if not start or end <= start:
        return None, "veri yok"
    if len(trades) >= 500 and min(safe_float(t.get("ts")) for t in trades) > start:
        return None, "veri yok"
    total = lost = unknown = 0
    for side_name, taker_side in (("bids", "sell"), ("asks", "buy")):
        initial = [(safe_float(r[0]),safe_float(r[1])) for r in first.get(side_name, [])[:10]]
        final = [(safe_float(r[0]),safe_float(r[1])) for r in last.get(side_name, [])]
        mean = avg([q for _,q in initial])
        if not final:
            return None, "veri yok"
        lo, hi = min(p for p,q in final), max(p for p,q in final)
        for price, qty in initial:
            if qty <= 0 or mean <= 0 or qty < mean*V10_OB_WALL_MULT:
                continue
            tolerance = price*SPOOF_FIYAT_TOLERANS_PCT/100
            if price-tolerance < lo or price+tolerance > hi:
                unknown += 1
                continue
            total += 1
            remaining = sum(q for p,q in final if abs(p-price) <= tolerance)
            seen, filled = set(), 0.0
            for trade in trades:
                key = trade.get("tradeId")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                if start < safe_float(trade.get("ts")) <= end and trade.get("side") == taker_side and abs(safe_float(trade.get("px"))-price) <= tolerance:
                    filled += safe_float(trade.get("sz"))
            if max(0.0, qty-remaining-filled)/qty >= SPOOF_CHANGE_THRESHOLD:
                lost += 1
    # Görünür defter dışına kayan duvar iptal diye sayılmaz.
    if lost and total and lost/(total+unknown) >= SPOOF_MIN_ORAN:
        return True, f"REST duvar iptal anomalisi ({lost}/{total+unknown}); manipülasyon kanıtı değil"
    return (None, "veri yok") if unknown else (False, "stabil")


async def v112_spoof_tespit(symbol, force=False):
    if (not SPOOF_GUARD_ENABLED and not force) or not V10_USE_ORDERBOOK:
        return False, "kapalı"
    if SPOOF_SOURCE == "LEGACY":
        return await _legacy_spoof_tespit(symbol, force)
    snapshot = balina_snapshot(symbol) if BALINA_MOTOR_ENABLED else {}
    if SPOOF_SOURCE == "AUTO" and snapshot.get("status") == "CANLI" and snapshot.get("flow_ready"):
        count = int(safe_float(snapshot.get("spoof_1m")))
        return bool(count), (f"WS duvar iptal anomalisi: {count}" if count else "stabil")
    lock = _SPOOF_LOCKS.setdefault(symbol, asyncio.Lock())
    async with lock:
        cached = _SPOOF_CACHE.get(symbol)
        if cached and time.time()-cached[0] < SPOOF_CACHE_SEC:
            return cached[1]
        try:
            first = await _okx_get_async("/api/v5/market/books", {"instId":symbol,"sz":20})
            await asyncio.sleep(max(0.1, SPOOF_CHECK_INTERVAL))
            last = await _okx_get_async("/api/v5/market/books", {"instId":symbol,"sz":20})
            trades = await _okx_get_async("/api/v5/market/trades", {"instId":symbol,"limit":500})
            result = _rest_wall_result(first[0],last[0],trades) if first and last else (None,"veri yok")
        except asyncio.CancelledError:
            raise
        except Exception:
            result = None,"hata"
        _SPOOF_CACHE[symbol] = time.time(),result
        if len(_SPOOF_CACHE) > 500:
            for old in list(_SPOOF_CACHE):
                if old != symbol and not _SPOOF_LOCKS.get(old, lock).locked():
                    _SPOOF_CACHE.pop(old, None)
                    _SPOOF_LOCKS.pop(old, None)
                    break
        return result



_LIQ_REPORTS_SEEN = {}


def _process_liquidation_report(row):
    symbol = str(row.get("instId", ""))
    for detail in row.get("details", []):
        ts = safe_float(detail.get("ts"))/1000
        price, qty = safe_float(detail.get("bkPx")), safe_float(detail.get("sz"))
        if not symbol or ts <= 0 or price <= 0 or qty <= 0:
            continue
        key = hashlib.sha256(json.dumps([symbol,detail],sort_keys=True).encode()).hexdigest()
        if key in _LIQ_REPORTS_SEEN:
            continue
        _LIQ_REPORTS_SEEN[key] = time.time()
        if len(_LIQ_REPORTS_SEEN) > 10000:
            _LIQ_REPORTS_SEEN.pop(next(iter(_LIQ_REPORTS_SEEN)))
        value = _balina_contract_value(symbol,price,qty)
        _balina_queue_event({"ts":ts,"symbol":symbol,"event_type":"LIQUIDATION_REPORTED",
            "side":detail.get("posSide"),"price":price,"value_usdt":value,
            "detail":detail,"coverage":"OKX_REPORTED_SUBSET", "source":"OKX_WS",
            "note":"Geçmiş gerçekleşen bildirim; toplam likidasyon veya gelecek haritası değil"})



# Yalnız yedek indirme eki: sürüm/cohort ve işlem mantığı değişmez.
_YEDEK_INDIR_LOCK = asyncio.Lock()


def _yedek_indir_hazirla(directory, snapshot):
    import zipfile
    from pathlib import Path
    root = Path(directory)
    started = time.time()
    manifest = {"build": BOT_BUILD, "started_ts": started, "files": [], "missing": [],
                "note": "DB'ler ayrı SQLite online snapshot; JSON ayrı anlık görüntüdür."}
    for name, source in (("balina_olcum.db", OLCUM_DB), ("balina_akis.db", BALINA_DB)):
        srcpath = Path(source).resolve()
        if not srcpath.is_file():
            manifest["missing"].append(name)
            continue
        target = root/name
        deadline = time.monotonic()+120
        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("Yedek süre sınırı")
        # mode=ro olmayan kaynak için boş DB oluşturulmasını önler; WAL dahil.
        with sqlite3.connect(srcpath.as_uri()+"?mode=ro", uri=True, timeout=10) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst, pages=256, progress=progress, sleep=.05)
                if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Yedek bütünlük kontrolü başarısız")
        manifest["files"].append(name)
    (root/"paper_memory.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    manifest["files"].append("paper_memory.json")
    manifest["completed_ts"] = time.time()
    (root/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = root/("balina_yedek_"+stamp+".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name in manifest["files"]+["manifest.json"]:
            z.write(root/name, name)
    # Büyük arşivleri eksiksiz, sıralı ikili parçalara böl.
    limit = 40*1024*1024
    if archive.stat().st_size <= limit:
        return [str(archive)], manifest
    pieces = []
    with archive.open("rb") as stream:
        while True:
            chunk = stream.read(limit)
            if not chunk:
                break
            part = root/(archive.name+f".part{len(pieces)+1:03d}")
            part.write_bytes(chunk)
            pieces.append(str(part))
    return pieces, manifest


async def cmd_yedekindir(update, context):
    if not telegram_yetkili(update):
        return
    if _YEDEK_INDIR_LOCK.locked():
        await update.message.reply_text("Bir yedek indirme işlemi zaten sürüyor.")
        return
    import tempfile
    from telegram import InputFile
    async with _YEDEK_INDIR_LOCK:
        await update.message.reply_text("Yedek hazırlanıyor; veritabanları silinmez veya sıfırlanmaz.")
        try:
            async with memory_lock:
                snapshot = copy.deepcopy(json_memory_snapshot())
            with tempfile.TemporaryDirectory(prefix="balina_export_") as directory:
                # Cancel durumunda worker bitmeden geçici dizin silinmez.
                worker = asyncio.create_task(asyncio.to_thread(_yedek_indir_hazirla, directory, snapshot))
                try:
                    paths, manifest = await asyncio.shield(worker)
                except asyncio.CancelledError:
                    await worker
                    raise
                total = len(paths)
                for i, path in enumerate(paths, 1):
                    caption = f"Balina veri yedeği ({i}/{total}). Dosyayı indirip inceleme için paylaşabilirsin."
                    if total > 1:
                        caption += " Büyük ZIP parçalandı; bütün .part dosyalarını birlikte gönder."
                    with open(path, "rb") as stream:
                        await update.message.reply_document(
                            document=InputFile(stream, filename=os.path.basename(path), read_file_handle=False),
                            caption=caption, read_timeout=120, write_timeout=180, connect_timeout=20)
                missing = ", ".join(manifest["missing"])
                await update.message.reply_text("Yedek dosyaları gönderildi."+
                    (" Bulunamayan dosyalar: "+missing if missing else ""))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Yedek indirme başarısız")
            await update.message.reply_text("Yedek hazırlanamadı veya gönderilemedi. /yedekindir ile tekrar deneyebilirsin; asıl kayıtlar korunur.")


# === V12.1 bağımsız motor / TP1 sonrası gözlem ===
_GIZLI_LOCK = asyncio.Lock()
_FOLLOW_PRELOAD = {}
_HISTORY_RAW = _history_raw


async def _history_range(symbol, interval, start_ms, end_ms, step_ms):
    # Gölge turu başına aynı coin'in tam dakikaları tek havuzdan paylaşılır.
    key=(symbol,interval,step_ms)
    pool=_FOLLOW_PRELOAD.get(key)
    if interval=='1s' and _FOLLOW_PRELOAD.get('_active'):
        pools=_FOLLOW_PRELOAD.get(('seconds',symbol),[])
        pool=next((item for item in pools if item[0]<=start_ms and end_ms<=item[1]),pool)
    if pool and pool[0]<=start_ms and end_ms<=pool[1]:
        result=[r for r in pool[2] if start_ms<=int(r[0]) and int(r[0])+step_ms<=end_ms]
        complete=len(result)==max(0,(end_ms-start_ms)//step_ms) and all(int(r[0])==start_ms+i*step_ms for i,r in enumerate(result))
        return result,complete
    result,complete=await _HISTORY_RAW(symbol,interval,start_ms,end_ms,step_ms)
    if _FOLLOW_PRELOAD.get('_active') and interval=='1s':
        _FOLLOW_PRELOAD.setdefault(('seconds',symbol),[]).append((start_ms,end_ms,result))
    return result,complete


def _history_gap(pos,start,end):
    old=pos.get('history_gap') or {}
    pos['history_gap']={'start_ms':int(start),'end_ms':int(end),
        'first_seen':old.get('first_seen',time.time()),'last_attempt':time.time(),
        'attempts':int(old.get('attempts',0))+1}


def yeni_motor_db_init():
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS motor_identity (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
        identity=conn.execute('SELECT value FROM motor_identity WHERE id=1').fetchone()
        if identity is None:
            # Yanlışlıkla eski DB'ye yönlendirme, geri yükleme veya yol hatasında karışma yerine dur.
            if conn.execute('SELECT COUNT(*) FROM olcum_pozisyon').fetchone()[0]:
                raise RuntimeError('Yeni DB boş değil ve V12.1 kimliği yok. YENI_OLCUM_DB ayrı olmalı.')
            conn.execute("INSERT INTO motor_identity VALUES(1,'V12.1-TP1FULL')")
        elif identity[0]!='V12.1-TP1FULL':
            raise RuntimeError('Defter motor kimliği uyumsuz')
        conn.execute('CREATE TABLE IF NOT EXISTS gizli_position (uid TEXT PRIMARY KEY,symbol TEXT NOT NULL,candle TEXT NOT NULL,side TEXT NOT NULL,status TEXT NOT NULL,position_json TEXT NOT NULL,UNIQUE(symbol,candle))')
        conn.execute('CREATE INDEX IF NOT EXISTS gizli_status ON gizli_position(status,symbol)')
        conn.execute('CREATE TABLE IF NOT EXISTS continuation (uid TEXT PRIMARY KEY,engine TEXT NOT NULL,symbol TEXT NOT NULL,phase TEXT NOT NULL,payload TEXT NOT NULL)')
        conn.execute('CREATE INDEX IF NOT EXISTS continuation_phase ON continuation(phase,symbol)')
        conn.execute("INSERT OR IGNORE INTO schema_meta VALUES('v12_1_started',?)",(str(time.time()),))
        conn.execute("INSERT OR IGNORE INTO schema_meta VALUES('archive_paths',?)",(_json({'olcum':ESKI_OLCUM_DB,'memory':ESKI_MEMORY_FILE,'akis':ESKI_BALINA_DB}),))
    if memory.get('v12_1_identity') not in (None,'V12.1-TP1FULL'):
        raise RuntimeError('Yeni JSON motor kimliği uyumsuz')
    if memory.get('v12_1_identity') is None and any(_v10_mem().get(k) for k in ('open','closed','golge')):
        raise RuntimeError('Eski JSON yeni deftere yüklenemez. YENI_MEMORY_FILE ayrı olmalı.')
    memory['v12_1_identity']='V12.1-TP1FULL'


def _gizli_accept(sig):
    # Aday filtreler; kârlılık iddiası değil. Ölçümsüz bir değer geçer sayılmaz.
    if sig.get('kontrol'): return False
    oi=sig.get('oi_change_pct')
    if oi is None or safe_float(oi)<=GIZLI_MIN_OI_PCT: return False
    gates=sig.get('kapi_sonuclari') or {}
    return all(gates.get(k)=='gecti' for k in GIZLI_GEREKLI_KAPILAR)


def _gizli_can_open(symbol,candle):
    with sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        if conn.execute("SELECT COUNT(*) FROM gizli_position WHERE status='ACIK'").fetchone()[0]>=GIZLI_MAX_OPEN:return False
        return conn.execute("SELECT 1 FROM gizli_position WHERE symbol=? AND (status='ACIK' OR candle=?)",(symbol,candle)).fetchone() is None


def _gizli_insert(pos):
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT 1 FROM gizli_position WHERE symbol=? AND (status='ACIK' OR candle=?)",(pos['symbol'],pos['candle_ts'])).fetchone():return None
        if conn.execute("SELECT COUNT(*) FROM gizli_position WHERE status='ACIK'").fetchone()[0]>=GIZLI_MAX_OPEN:return None
        old=conn.execute("SELECT value FROM schema_meta WHERE key='gizli_seq'").fetchone()
        pos['signal_no']=int(old[0])+1 if old else 1
        conn.execute('INSERT INTO gizli_position VALUES(?,?,?,?,?,?)',(pos['uid'],pos['symbol'],pos['candle_ts'],pos['side'],'ACIK',_json(pos)))
        conn.execute("INSERT OR REPLACE INTO schema_meta VALUES('gizli_seq',?)",(str(pos['signal_no']),))
        if GIZLI_TELEGRAM_ENABLED:
            text=f"🔒 GİZLİ PAPER #{pos['signal_no']} | {pos['symbol']} {pos['side']}\nGiriş {pos['entry']} | Stop %3 | TP %5/%9/%13/%20\nTP1 tam kapanış; aday filtreler, kârlılık doğrulanmadı."
            _outbox_insert(conn,pos['uid']+':OPEN',pos,'GIZLI',text)
    return pos


async def gizli_aday(sig):
    if not GIZLI_ENABLED or not _gizli_accept(sig):return
    if RISK_KILL_SWITCH or _RUNTIME_HEALTH.get('emergency_stop'):return
    async with _GIZLI_LOCK:
        try:
            if not await _db_call(_gizli_can_open,sig['symbol'],str(sig['candle_ts'])):return
            quote=await _live_entry_quote(sig['symbol'],sig['direction'])
            s=copy.deepcopy(sig);entry=quote['price'];sign=1 if s['direction']=='LONG' else -1
            s.update(entry=entry,stop=entry*(1-sign*.03),stop_pct=3.0,risk=entry*.03,accepted_ts=time.time(),entry_kaynak=quote['source'])
            for i,pct in enumerate((5,9,13,20),1):
                s[f'tp{i}']=entry*(1+sign*pct/100);s[f'tp{i}_rr']=pct/3
            p=v10_open_paper(s,persist=False)
            p.update(uid='GIZLI|'+p['uid'],engine='GIZLI',tp_weights=[1,0,0,0],
                filter_snapshot={'oi_min':GIZLI_MIN_OI_PCT,'gates':list(GIZLI_GEREKLI_KAPILAR)},cohort=_cohort()+':GIZLI')
            p.pop('cost_r_frozen',None)
            p['cost_r_frozen']=simulasyon_maliyet_r(p)
            await _db_call(_gizli_insert,p)
        except asyncio.CancelledError:raise
        except Exception:
            stats['gizli_error']=int(stats.get('gizli_error',0))+1
            logger.exception('Gizli aday hatası; ana motor devam ediyor')


def _follow_insert(conn,pos,outcome,engine):
    if outcome not in ('TP1','STOP'):return
    p=copy.deepcopy(pos)
    p.pop('pending_hits',None);p.pop('history_gap',None)
    phase='AFTER_TP' if outcome=='TP1' else 'AFTER_STOP'
    end=(pos['open_ts']+TAKIP_SAAT*3600) if phase=='AFTER_TP' else pos['close_ts']+GOLGE_SAAT*3600
    risk=abs(pos['entry']-pos['orig_stop'])
    rrs=[abs(pos[f'tp{i}']-pos['entry'])/risk for i in range(1,5)]
    p.update(engine=engine,phase=phase,actual_outcome=outcome,actual_r=rrs[0] if outcome=='TP1' else -1,
        tracking_deadline=float(math.ceil(max(pos['close_ts'],end))),targets={str(i):({'state':'TP','r':rrs[i-1]} if i==1 and outcome=='TP1' else {'state':'STOP','r':-1.0} if outcome=='STOP' else {'state':'PENDING','r':None}) for i in range(1,5)},
        follow_hits=[1] if outcome=='TP1' else [],follow_mfe_pct=0.0,follow_mae_pct=0.0,
        shadow_hits=[],shadow_mfe_pct=0.0,shadow_mae_pct=0.0,shadow_times={},shadow_complete=False,
        post_tp_stop_highest=None,stop_ts=pos['close_ts'] if outcome=='STOP' else None,
        first_tp_ts=pos['close_ts'] if outcome=='TP1' else None,shadow_enabled=GOLGE_IZLEME,shadow_hours=GOLGE_SAAT)
    observation=pos.get('exit_observation') or {}
    if outcome=='TP1' and observation:
        for i in range(2,5):
            reached=observation['hi']>=p[f'tp{i}'] if p['side']=='LONG' else observation['lo']<=p[f'tp{i}']
            if reached:
                p['follow_hits'].append(i);p['targets'][str(i)]={'state':'TP','r':rrs[i-1]}
                if engine=='MAIN' or GIZLI_TELEGRAM_ENABLED:
                    _outbox_insert(conn,p['uid']+f':POST_TP{i}',p,'FOLLOW' if engine=='MAIN' else 'GIZLI',
                        f"{'GİZLİ ' if engine=='GIZLI' else ''}#{p.get('signal_no',0)} | {p['symbol']} | TP{i} {rrs[i-1]:.3f}R teması\nTP1 ile aynı kapanış saniyesi; gerçekleşen TP1 sonucu değişmez.")
        if len(p['follow_hits'])==4:p['phase']='DONE'
        elif p['tracking_deadline']<=p['close_ts']:
            current=(observation['close']-p['entry'])*(1 if p['side']=='LONG' else -1)/risk
            for target in p['targets'].values():
                if target['state']=='PENDING':target.update(state='TIME_EXIT',r=current)
            p['phase']='DONE'
    if outcome=='STOP' and not GOLGE_IZLEME:p['phase']='DONE'
    conn.execute('INSERT OR IGNORE INTO continuation VALUES(?,?,?,?,?)',(p['uid'],engine,p['symbol'],p['phase'],_json(p)))


def _follow_process(p,rows):
    events=[]
    for row in rows:
        ts=int(row[0]);end=ts+int(row[9]);cursor=int(p.get('scan_ts',p['close_ts']*1000))
        if ts<cursor:continue
        if ts!=((cursor+999)//1000)*1000:
            _history_gap(p,cursor,ts);break
        if end>int(p['tracking_deadline']*1000):break
        hi,lo,c=map(safe_float,(row[2],row[3],row[4]));long=p['side']=='LONG';entry=p['entry']
        favorable=max(0,(hi-entry if long else entry-lo)/entry*100)
        adverse=max(0,(entry-lo if long else hi-entry)/entry*100)
        stop=lo<=p['orig_stop'] if long else hi>=p['orig_stop']
        touched=lambda i:hi>=p[f'tp{i}'] if long else lo<=p[f'tp{i}']
        if p['phase']=='AFTER_TP':
            p['follow_mfe_pct']=max(p['follow_mfe_pct'],favorable)
            p['follow_mae_pct']=max(p['follow_mae_pct'],adverse)
            if stop:
                highest=max(p['follow_hits'],default=1)
                p['post_tp_stop_highest']=highest;p['stop_ts']=end/1000
                for target in p['targets'].values():
                    if target['state']=='PENDING':target.update(state='STOP',r=-1.0)
                events.append(('POST_STOP',f"TP{highest} sonrası STOP | TP1 kapanışı sonrası izleme. Gerçekleşen brüt {p['actual_r']:+.3f}R değişmedi."))
                p['phase']='AFTER_STOP' if p.get('shadow_enabled',True) else 'DONE'
                p['tracking_deadline']=end/1000+p.get('shadow_hours',GOLGE_SAAT)*3600
                # Stop saniyesinin tamamı gölgeye dahil edilmez; sıralama belirsizdir.
            else:
                for i in range(2,5):
                    if i not in p['follow_hits'] and touched(i):
                        p['follow_hits'].append(i)
                        rr=p['tp_rrs'][i-1];p['targets'][str(i)]={'state':'TP','r':rr}
                        events.append((f'POST_TP{i}',f"TP{i} GELDİ | {rr:.3f}R | TP1 kapanışı sonrası izleme; gerçekleşen sonuç değişmedi."))
                if len(p['follow_hits'])==4:p['phase']='DONE'
                elif end>=int(p['tracking_deadline']*1000):
                    current=(c-entry)*(1 if long else -1)/abs(entry-p['orig_stop'])
                    for target in p['targets'].values():
                        if target['state']=='PENDING':target.update(state='TIME_EXIT',r=current)
                    p['phase']='DONE'
        elif p['phase']=='AFTER_STOP':
            p['shadow_mfe_pct']=max(p['shadow_mfe_pct'],favorable)
            p['shadow_mae_pct']=max(p['shadow_mae_pct'],adverse)
            for i in range(1,5):
                if i not in p['shadow_hits'] and touched(i):
                    p['shadow_hits'].append(i);p['shadow_times'][str(i)]=(end/1000-p['stop_ts'])/60
                    events.append((f'SHADOW_TP{i}',f"STOP SONRASI TP{i} | {p['tp_rrs'][i-1]:.3f}R mesafesi | Yalnız gölge izleme; kapanış sonucu değişmedi."))
            if end>=int(p['tracking_deadline']*1000):
                p['phase']='DONE';p['shadow_complete']=True
        p['scan_ts']=end;p['last_price']=c
        if p['phase']=='DONE':
            p.pop('history_gap',None)
            break
    return events


def _follow_save(p,events):
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('UPDATE continuation SET phase=?,payload=? WHERE uid=?',(p['phase'],_json(p),p['uid']))
        if p['engine']=='MAIN' or GIZLI_TELEGRAM_ENABLED:
            for key,text in events:
                label='GİZLİ ' if p['engine']=='GIZLI' else ''
                _outbox_insert(conn,p['uid']+':'+key,p,'GIZLI' if p['engine']=='GIZLI' else 'FOLLOW',
                    f"{label}#{p.get('signal_no',0)} | {p['symbol']} {p['side']}\n{text}\nMum sonu: {tr_str(p['scan_ts']/1000)}")


def _follow_rows(active_only=False,engine=None):
    with sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        query='SELECT payload FROM continuation';conditions=[];args=[]
        if active_only:conditions.append("phase!='DONE'")
        if engine:conditions.append('engine=?');args.append(engine)
        if conditions:query+=' WHERE '+' AND '.join(conditions)
        return [json.loads(r[0]) for r in conn.execute(query,args)]


async def _continuation_tur():
    records=await _db_call(_follow_rows,True)
    groups=defaultdict(list)
    for p in records:
        tf=GOLGE_TF if p['phase']=='AFTER_STOP' else V107_TAKIP_TF
        groups[(p['symbol'],tf)].append(p)
    for (symbol,tf),group in groups.items():
        _RUNTIME_HEALTH['shadow_heartbeat']=time.time()
        try:
            step=interval_minutes(tf)*60000
            start=min(int(p.get('scan_ts',p['close_ts']*1000)) for p in group)//step*step
            end=min(int((time.time()-HISTORY_SETTLE_SEC)*1000)//step*step,start+300*step)
            full,_=await _HISTORY_RAW(symbol,tf,start,end,step) if end>start else ([],True)
            _FOLLOW_PRELOAD.clear();_FOLLOW_PRELOAD['_active']=True
            _FOLLOW_PRELOAD[(symbol,tf,step)]=(start,end,full)
            for p in group:
                try:
                    # Aynı coinin tüm kayıtları ortak zaman penceresini paylaşır.
                    p['fetch_cutoff_ts']=end/1000
                    rows,_=await v107_takip_barlari(p)
                    p.pop('fetch_cutoff_ts',None)
                    events=_follow_process(p,rows)
                    await _db_call(_follow_save,p,events)
                except asyncio.CancelledError:raise
                except Exception:
                    stats['shadow_error']=int(stats.get('shadow_error',0))+1
                    logger.exception('Gölge UID hatası %s',p['uid'])
        except asyncio.CancelledError:raise
        except Exception:
            stats['shadow_error']=int(stats.get('shadow_error',0))+1
            logger.exception('Gölge coin hatası %s',symbol)
        finally:_FOLLOW_PRELOAD.clear()


def _gizli_rows(active_only=False):
    with sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        return [json.loads(p) for p, in conn.execute('SELECT position_json FROM gizli_position'+(" WHERE status='ACIK'" if active_only else ''))]


def _gizli_step(p,r=None,outcome=None):
    with _OLCUM_DB_LOCK,sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=conn.execute('SELECT status FROM gizli_position WHERE uid=?',(p['uid'],)).fetchone()
        if not current or current[0]!='ACIK':return
        p['status']=outcome or 'ACIK'
        if outcome:
            p['r_value']=r;p['net_r_value']=r-simulasyon_maliyet_r(p)
            p['sonuc_tipi']=sonuc_tipi_belirle(outcome,p)
            _follow_insert(conn,p,outcome,'GIZLI')
            if GIZLI_TELEGRAM_ENABLED:
                _outbox_insert(conn,p['uid']+':CLOSE',p,'GIZLI',build_v10_close_message(p,r,outcome,p['exit_price']))
        conn.execute('UPDATE gizli_position SET status=?,position_json=? WHERE uid=?',(p['status'],_json(p),p['uid']))


async def yeni_motor_loop():
    while True:
        if True:  # Açılmış kayıtlar GIZLI_ENABLED kapatılsa da takip edilir.
            for p in await _db_call(_gizli_rows,True):
                if p.get('status','ACIK')!='ACIK':continue
                try:
                    rows,_=await v107_takip_barlari(p)
                    r,outcome=_paper_process_rows(p,rows)
                    await _db_call(_gizli_step,p,r,outcome)
                except asyncio.CancelledError:raise
                except Exception:
                    stats['gizli_error']=int(stats.get('gizli_error',0))+1
                    logger.exception('Gizli takip hatası %s',p['uid'])
        await asyncio.sleep(max(1,V107_TAKIP_ARALIK_SEC))


def _engine_positions(engine):
    if engine=='GIZLI':return _gizli_rows()
    with sqlite3.connect(OLCUM_DB,timeout=10) as conn:
        result=[]
        for raw,status,r,net in conn.execute('SELECT position_json,durum,r_value,net_r_value FROM olcum_pozisyon'):
            p=json.loads(raw);p.update(status=status,r_value=r,net_r_value=net);result.append(p)
        return result


def _ratio(n,total):
    return f'{n}/{total} (%{n/total*100:.1f})' if total else '0/0 (ölçümsüz)'


def _engine_report(engine):
    rows=_engine_positions(engine);follows=_follow_rows(False,engine)
    lines=[f"📊 {BOT_BUILD} | {'ANA MOTOR' if engine=='MAIN' else 'GİZLİ MOTOR'} | TP1 %100 kapanış",
        'Eski sürüm ve diğer motor hariç; TP sonrası temaslar gerçekleşmiş kâr değildir.']
    lines.append(f'Toplam {len(rows)} | Açık {sum(p.get("status","ACIK")=="ACIK" for p in rows)} | Kapalı {sum(p.get("status","ACIK")!="ACIK" for p in rows)}')
    if engine=='GIZLI':lines.append(f'Bildirim: {GIZLI_TELEGRAM_ENABLED} | Aday filtreler: OI > %{GIZLI_MIN_OI_PCT:g}, '+','.join(GIZLI_GEREKLI_KAPILAR))
    for control,name in ((False,'NORMAL'),(True,'KONTROL')):
        group=[p for p in rows if bool(p.get('kontrol'))==control]
        if engine=='GIZLI' and control:continue
        closed=[p for p in group if p.get('status','ACIK')!='ACIK']
        tp=sum(p.get('status')=='TP1' for p in closed);stop=sum(p.get('status')=='STOP' for p in closed)
        lines.extend([f'\n{name}: toplam {len(group)} | açık {len(group)-len(closed)} | kapanan {len(closed)}',
            f'TP1 tam kapanış: {_ratio(tp,len(closed))} | TP görmeden stop: {_ratio(stop,len(closed))}',
            f"Süre çıkışı: {sum(p.get('status')=='TIME_EXIT' for p in closed)} | Brüt EV {_metric(_mean_present(closed,'r_value'))}R | Net EV {_metric(_mean_present(closed,'net_r_value'))}R",
            f"MFE/MAE (gerçek pozisyon): %{_metric(_mean_present(group,'mfe_pct'))}/%{_metric(_mean_present(group,'mae_pct'))}"])
        mfe=[p['mfe_pct'] for p in group if p.get('mfe_pct') is not None]
        mae=[p['mae_pct'] for p in group if p.get('mae_pct') is not None]
        lines.append('MFE dağılımı: '+ ' | '.join(f'{label} %{_metric(yuzdelik(mfe,q) if mfe else None)}' for label,q in (('medyan',.5),('p75',.75),('p90',.9))))
        lines.append(f'MAE medyan %{_metric(yuzdelik(mae,.5) if mae else None)} | Stop mesafesine ulaşan {sum(p.get("mae_pct",0)>=abs(p["entry"]-p["orig_stop"])/p["entry"]*100-1e-6 for p in group)}')
        fs=[p for p in follows if bool(p.get('kontrol'))==control]
        lines.append('TP1 sonrası temaslar: '+' | '.join(f'TP{i}: {sum(i in p["follow_hits"] for p in fs)}' for i in range(2,5)))
        lines.append('TP sonrası stop: '+' | '.join(f'TP{i} sonrası {sum(p.get("post_tp_stop_highest")==i for p in fs)}' for i in range(1,4)))
        lines.append(f"Mum bekleyen: {sum(bool(p.get('history_gap')) for p in group)} | Gözlemde mum bekleyen: {sum(bool(p.get('history_gap')) for p in fs)}")
    return '\n'.join(lines)


def _target_report(engine):
    rows=_engine_positions(engine);fs={p['uid']:p for p in _follow_rows(False,engine)}
    lines=['📐 ALTERNATİF TAM KAPANIŞ | ana sonuca yazılmaz',f'İzleme ufku {TAKIP_SAAT:g} saat. Aynı saniyede stop önce; eksik veri karar dışı.']
    for control,name in ((False,'NORMAL'),(True,'KONTROL')):
        if engine=='GIZLI' and control:continue
        group=[p for p in rows if bool(p.get('kontrol'))==control]
        lines.append(name)
        for target in range(1,5):
            values=[];net=[];pending=missing=0
            for p in group:
                follow=fs.get(p['uid']);result=None
                if target==1 and p.get('status','ACIK')!='ACIK':result=p.get('r_value')
                elif follow:
                    result=follow['targets'][str(target)]['r']
                elif p.get('status')=='TIME_EXIT':result=p.get('r_value')
                if result is None:
                    pending+=1;missing+=bool((follow or p).get('history_gap'));continue
                values.append(result);net.append(result-simulasyon_maliyet_r(p))
            lines.append(f'TP{target}: sonuçlanan {len(values)} | bekleyen {pending} (veri bekleyen {missing}) | Brüt EV {_metric(avg(values) if values else None)}R | Net EV {_metric(avg(net) if net else None)}R'+(' | KARAR YOK (<100)' if len(values)<100 else ' | ileri doğrulama gerekir'))
    return '\n'.join(lines)


def _shadow_report(engine):
    fs=[p for p in _follow_rows(False,engine) if p.get('stop_ts') is not None]
    lines=[f'👻 STOP SONRASI | {engine} | Eski sürüm hariç',f'İzleme {GOLGE_SAAT:g} saat; eksik aralık kapanmadan tamamlanmaz.']
    for control,name in ((False,'NORMAL'),(True,'KONTROL')):
        if engine=='GIZLI' and control:continue
        group=[p for p in fs if bool(p.get('kontrol'))==control];done=[p for p in group if p.get('shadow_complete')]
        lines.append(f'{name}: stop {len(group)} | biten {len(done)} | izlenen {sum(p["phase"]=="AFTER_STOP" for p in group)} | kapalı izleme {sum(not p.get("shadow_enabled",True) for p in group)}')
        for i in range(1,5):
            hit=[p for p in group if i in p['shadow_hits']];times=[p['shadow_times'][str(i)] for p in hit]
            finished=sum(i in p['shadow_hits'] for p in done)
            lines.append(f'TP{i}: {_ratio(len(hit),len(group))} | bitenlerde {_ratio(finished,len(done))} | medyan dk {_metric(yuzdelik(times,.5) if times else None,1)}')
        lines.append(f"Gölge MFE/MAE: %{_metric(_mean_present(group,'shadow_mfe_pct'))}/%{_metric(_mean_present(group,'shadow_mae_pct'))}")
        yes=[{'ozellikler':pozisyon_ozellikleri(p),'kapilar':p.get('kapi_sonuclari',{})} for p in done if 1 in p['shadow_hits']]
        no=[{'ozellikler':pozisyon_ozellikleri(p),'kapilar':p.get('kapi_sonuclari',{})} for p in done if 1 not in p['shadow_hits']]
        lines.append(f'Tamamlanmış gölgelerde TP1 gören {len(yes)} / görmeyen {len(no)}')
        lines.extend(ortak_ozellik_analiz(yes,no))
    lines.append('Çoklu özellik farkları hipotezdir; stop nedenini nedensel olarak kanıtlamaz.')
    return '\n'.join(lines)


def _archive_report():
    from pathlib import Path
    path=Path(ESKI_OLCUM_DB)
    if not path.is_file():return f'Eski defter bulunamadı: {path.name}. ESKI_OLCUM_DB eski dosyayı göstermeli.'
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=10) as conn:
        rows=conn.execute('SELECT kontrol,durum,r_value,sonuc_tipi FROM olcum_pozisyon').fetchall()
    lines=['📚 ESKİ SÜRÜM | DONDURULMUŞ ARŞİV','Takip ve bildirim kapalı. Yeni sürümün hiçbir hesabına girmez.']
    for control,name in ((0,'NORMAL'),(1,'KONTROL')):
        group=[r for r in rows if r[0]==control];closed=[r for r in group if r[1]!='ACIK']
        lines.append(f'{name}: toplam {len(group)} | arşivlenmiş açık {len(group)-len(closed)} | kapanan {len(closed)} | Brüt EV {_metric(avg([r[2] for r in closed]) if closed else None)}R')
        counts=defaultdict(int)
        for r in closed:counts[r[3] or r[1]]+=1
        lines.append(' | '.join(f'{k}: {v}' for k,v in sorted(counts.items())))
    return '\n'.join(lines)


async def cmd_eskisurum(update,context):
    if not telegram_yetkili(update):return
    for part in telegram_parcala(await _db_call(_archive_report)):await update.message.reply_text(part)


async def cmd_gizli(update,context):
    if not telegram_yetkili(update):return
    for fn in (_engine_report,_target_report,_shadow_report):
        for part in telegram_parcala(await _db_call(fn,'GIZLI')):await update.message.reply_text(part)


async def cmd_hedefler(update,context):
    if not telegram_yetkili(update):return
    for part in telegram_parcala(await _db_call(_target_report,'MAIN')):await update.message.reply_text(part)


def _new_storage_preflight():
    from pathlib import Path
    for new in (OLCUM_DB,MEMORY_FILE,BALINA_DB):
        for old in (ESKI_OLCUM_DB,ESKI_MEMORY_FILE,ESKI_BALINA_DB):
            if os.path.realpath(new)==os.path.realpath(old) or (os.path.exists(new) and os.path.exists(old) and os.path.samefile(new,old)):
                raise RuntimeError("Yeni dosya eski arşivle aynı; başlatma durduruldu")
    if os.path.exists(OLCUM_DB):
        with sqlite3.connect(Path(OLCUM_DB).resolve().as_uri()+'?mode=ro',uri=True) as conn:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'olcum_pozisyon' in tables and conn.execute('SELECT COUNT(*) FROM olcum_pozisyon').fetchone()[0] and 'motor_identity' not in tables:
                raise RuntimeError('Yeni defter yolunda eski kayıtlar var; ayrı dosya seçin')
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE,encoding='utf-8') as f: m=json.load(f)
        if m.get('v12_1_identity')!='V12.1-TP1FULL' and any(m.get('v10_paper',{}).get(k) for k in ('open','closed','golge')):
            raise RuntimeError('Yeni JSON yolunda eski kayıtlar var; ayrı dosya seçin')


if __name__ == "__main__":
    main()
