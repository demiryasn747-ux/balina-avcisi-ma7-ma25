#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_balina.py — Balina Avcısı V9 saf fonksiyon testleri (bağımlılık YOK).

Çalıştırma:  python test_balina.py
Telegram/requests KURULU OLMASA BİLE çalışır: balina_hibrit.py'yi import etmez,
saf (I/O'suz) fonksiyonları AST ile çıkarıp izole bir ortamda test eder.
Böylece canlı API'ye dokunmadan strateji + backtest matematiği doğrulanır.

Kapsam: strateji motoru, likidasyon koruması, BTC rejim geçidi, volatilite guard,
backtester metrikleri (Sharpe/Sortino/PF/expectancy/equity), resample, TP/stop sim, pnl.
"""
import ast
import os
import sys
import typing

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(HERE, "balina_hibrit.py")


def _load(names):
    """balina_hibrit.py'den verilen fonksiyonları izole namespace'e çıkar (exec)."""
    src = open(SRC_PATH, encoding="utf-8").read()
    tree = ast.parse(src)
    ns = {
        "safe_float": (lambda v, d=0.0: float(v) if (v is not None and str(v).strip() not in ("", "None")) else d),
        "List": typing.List, "Dict": typing.Dict, "Any": typing.Any,
        "Optional": typing.Optional, "Tuple": typing.Tuple,
        # --- test config (canlı default'lardan bağımsız sabit değerler) ---
        "HYBRID_TREND_EMA": 100, "HYBRID_RISK_PCT": 1.5,
        "HYBRID_LIQ_GUARD_ENABLED": True, "HYBRID_MAINT_MARGIN_PCT": 0.005, "HYBRID_LIQ_SAFETY": 0.6,
        "BTC_BIAS_ENABLED": True, "SHORT_REQUIRE_INSTITUTIONAL": True, "SHORT_BLOCK_WHEN_BTC_UP": True,
        "SHORT_EXTREME_OVERRIDE": True, "LONG_BLOCK_WHEN_BTC_DOWN": True, "LONG_EXTREME_OVERRIDE": True,
        "VOL_GUARD_ENABLED": True, "BTC_ATR_HIGH_PCT": 2.5, "VOL_GUARD_RISK_MULT": 0.5,
        "BT_FEE_PCT": 0.00045, "BT_SLIPPAGE_PCT": 0.0018,
        "SWEEP_MIN_WICK_PCT": 0.20, "SWEEP_STOP_BUFFER_PCT": 0.15, "SWEEP_USE_TREND_FILTER": False,
        "SWEEP_MA_CONFIRM": False,
        "WHALE_PRICE_BARS": 3, "WHALE_MIN_PRICE_PCT": 0.5, "WHALE_MIN_OI_RISE": 1.0, "WHALE_FUNDING_EXTREME": 0.0005,
        "FUNDING_POS_THRESH": 0.0005, "FUNDING_NEG_THRESH": 0.0005, "FUNDING_REQUIRE_CONFIRM": True,
        "FUNDING_CONFIRM_PCT": 0.3, "FUNDING_PRICE_BARS": 3,
        "HYBRID_FIXED_TARGETS": False, "HYBRID_FIXED_STOP_PCT": 1.4,
        "HYBRID_FIXED_TP1_PCT": 4.0, "HYBRID_FIXED_TP2_PCT": 6.0, "HYBRID_FIXED_TP3_PCT": 8.0,
        "fmt_num": (lambda v: "%.4f" % float(v)),
    }
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            exec(ast.get_source_segment(src, node), ns)
    missing = [n for n in names if n not in ns]
    if missing:
        raise SystemExit(f"Fonksiyon bulunamadı: {missing}")
    return ns


FN = _load([
    "s_ema", "s_atr", "_s_closed", "_s_closes",
    "ma_cross_trigger", "trend_4h", "momentum_ok", "mtf_decision",
    "atr_stop", "rr_targets", "position_size", "build_hybrid_signal",
    "btc_regime_gate", "dynamic_risk_pct",
    "_bt_dyn_slippage", "_bt_mean", "_bt_std", "_bt_sharpe", "_bt_sortino",
    "_bt_longest_loss_streak", "_bt_metrics", "_bt_equity_dd",
    "_bt_regime_breakdown", "_bt_trades_to_csv",
    "_bt_resample", "bt_simulate_tp_stop", "bt_calc_pnl", "_bt_btc_trend_at",
    "_okx_to_kline", "_bt_assemble_klines", "_bt_funding_cost",
    "detect_liquidity_sweep", "_targets_for", "build_sweep_signal", "_btc_dir_series", "ma_side",
    "detect_whale_position", "build_whale_signal", "_paper_r",
    "detect_funding_extreme", "build_funding_signal", "_bt_funding_at",
])

PASS = 0
FAIL = 0


def ck(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ✗ FAIL: {name}")


def kl(cs, vol=1000.0):
    rows, p = [], cs[0]
    for i, c in enumerate(cs):
        rows.append([1_700_000_000 + i * 3600, p, max(p, c) * 1.003, min(p, c) * 0.997, c, vol])
        p = c
    return rows


rising = lambda n, s=100.0, st=0.5: [s + i * st for i in range(n)]
falling = lambda n, s=150.0, st=0.5: [s - i * st for i in range(n)]
flat = lambda n, v=100.0: [v] * n

# ---- strateji motoru ----
ck("flat→jump-up = LONG", FN["ma_cross_trigger"](kl(flat(55) + [115.0, 116.0])) == "LONG")
ck("flat→jump-down = SHORT", FN["ma_cross_trigger"](kl(flat(55) + [85.0, 84.0])) == "SHORT")
ck("düz piyasa = None", FN["ma_cross_trigger"](kl(flat(60))) is None)
ck("trend UP", FN["trend_4h"](kl(rising(60)), 100)[0] == "UP")
ck("trend DOWN", FN["trend_4h"](kl(falling(60)), 100)[0] == "DOWN")
ck("momentum LONG=True", FN["momentum_ok"](kl(rising(40)), "LONG") is True)
ck("momentum SHORT(yükselişte)=False", FN["momentum_ok"](kl(rising(40)), "SHORT") is False)
ck("mtf LONG+UP+mom = LONG", FN["mtf_decision"]("LONG", kl(rising(120)), kl(rising(40)), kl(rising(40)))[0] == "LONG")
ck("mtf LONG ama 4H DOWN = None", FN["mtf_decision"]("LONG", kl(falling(120)), kl(rising(40)), kl(rising(40)))[0] is None)

# ---- ATR stop / RR / sizing ----
s, p = FN["atr_stop"](100.0, "LONG", 2.0, 1.5)
ck("ATR stop=97", abs(s - 97.0) < 1e-9)
ck("ATR stop %3.0", abs(p - 3.0) < 1e-9)
ck("ATR min clamp %0.4", abs(FN["atr_stop"](100.0, "LONG", 0.01, 1.5)[1] - 0.4) < 1e-9)
ck("ATR max clamp SHORT=105", abs(FN["atr_stop"](100.0, "SHORT", 100.0, 1.5)[0] - 105.0) < 1e-9)
t = FN["rr_targets"](100.0, 97.0, "LONG")
ck("tp2 = 2.5R = 107.5", abs(t["tp2"] - 107.5) < 1e-9)
ck("SHORT tp2 = 92.5", abs(FN["rr_targets"](100.0, 103.0, "SHORT")["tp2"] - 92.5) < 1e-9)
ps = FN["position_size"](100.0, 97.0, 1000.0, 1.5, 1.0)
ck("qty=5", abs(ps["qty"] - 5.0) < 1e-9)
ck("risk_usdt=15", abs(ps["risk_usdt"] - 15.0) < 1e-9)
ck("5x marj=100", abs(FN["position_size"](100.0, 97.0, 1000.0, 1.5, 5.0)["margin"] - 100.0) < 1e-9)

# ---- build_hybrid_signal + likidasyon koruması ----
sig = FN["build_hybrid_signal"]("X", kl(flat(55) + [115.0, 116.0]), kl(rising(120)), kl(rising(40)), kl(rising(40)),
                                leverage=5, atr_mult=1.6, allow_weak_trend=True)
ck("sinyal üretildi (LONG)", bool(sig) and sig["direction"] == "LONG")
ck("stop<entry (LONG)", bool(sig) and sig["stop"] < sig["entry"])
ck("likidasyon fiyatı dolu", bool(sig) and sig.get("liquidation_price", 0) > 0)
hi = FN["build_hybrid_signal"]("Y", kl(flat(55) + [140.0, 141.0]), kl(rising(120)), kl(rising(40)), kl(rising(40)),
                               leverage=20, atr_mult=1.6, allow_weak_trend=True)
lo = FN["build_hybrid_signal"]("Y", kl(flat(55) + [140.0, 141.0]), kl(rising(120)), kl(rising(40)), kl(rising(40)),
                               leverage=1, atr_mult=1.6, allow_weak_trend=True)
ck("yüksek vol 20x → REDDEDİLDİ", hi is None)
ck("aynı coin 1x → kabul", lo is not None)

# ---- BTC rejim geçidi ----
def _res(d, w=0, f=0): return {"direction": d, "institutional_oi_bonus": w, "institutional_funding_bonus": f}
def _b(t, atr=1.0): return {"trend": t, "strong": True, "gap_pct": 2.0 if t == "UP" else -2.0, "atr_pct": atr, "ok": True}
G = FN["btc_regime_gate"]
ck("BTC UP + SHORT teyitsiz → blok", G(_res("SHORT"), _b("UP"))[0] is False)
ck("BTC UP + SHORT + whale+funding → geç", G(_res("SHORT", 20, 20), _b("UP"))[0] is True)
ck("BTC UP + LONG → geç", G(_res("LONG"), _b("UP"))[0] is True)
ck("BTC DOWN + LONG teyitsiz → blok", G(_res("LONG"), _b("DOWN"))[0] is False)
ck("BTC DOWN + LONG + funding → geç", G(_res("LONG", 0, 20), _b("DOWN"))[0] is True)
ck("BTC DOWN + SHORT teyitsiz → blok (kurumsal şart)", G(_res("SHORT"), _b("DOWN"))[0] is False)
ck("yüksek ATR → risk yarı (0.75)", abs(FN["dynamic_risk_pct"](_b("UP", 3.0)) - 0.75) < 1e-9)
ck("normal ATR → tam risk (1.5)", abs(FN["dynamic_risk_pct"](_b("UP", 1.0)) - 1.5) < 1e-9)

# ---- backtester metrikleri ----
ck("slippage 100M→0.05%", abs(FN["_bt_dyn_slippage"](100e6) - 0.0005) < 1e-12)
ck("slippage 5M→0.20%", abs(FN["_bt_dyn_slippage"](5e6) - 0.0020) < 1e-12)
ck("slippage 500k→0.40%", abs(FN["_bt_dyn_slippage"](5e5) - 0.0040) < 1e-12)
ck("sharpe sabit seri=0", FN["_bt_sharpe"]([1, 1, 1]) == 0.0)
ck("sharpe pozitif>0", FN["_bt_sharpe"]([2.5, -1, 2.5, -1, 2.5]) > 0)
ck("sortino [2.5,2.5,-1,-1]>0", FN["_bt_sortino"]([2.5, 2.5, -1, -1]) > 0)
ck("kayıp serisi=3", FN["_bt_longest_loss_streak"]([1, -1, -1, -1, 1, -1]) == 3)
M = FN["_bt_metrics"]([2.5, -1, 2.5, -1, -1])
ck("winrate %40", M["winrate"] == 40.0)
ck("profit_factor≈1.67", abs(M["profit_factor"] - 1.67) < 0.01)
ck("expectancy 0.4R", abs(M["expectancy_r"] - 0.4) < 1e-9)
ck("tüm kayıp→PF 0", FN["_bt_metrics"]([-1, -1])["profit_factor"] == 0.0)
ck("tüm kazanç→PF inf", FN["_bt_metrics"]([1, 2])["profit_factor"] == float("inf"))
eq = FN["_bt_equity_dd"]([-1, -1, -1], 1.5, 1000.0)
ck("hep kayıp→getiri negatif", eq["ret_pct"] < 0)
ck("hep kayıp→calmar negatif", eq["calmar"] < 0)
reg = FN["_bt_regime_breakdown"]([{"r": 2.5, "btc_trend": "UP"}, {"r": -1, "btc_trend": "DOWN"}])
ck("rejim raporu UP+DOWN", "UP" in reg and "DOWN" in reg)

# ---- resample / sim / pnl / btc-at ----
rs = FN["_bt_resample"]([[i, 100 + i, 105 + i, 95 + i, 101 + i, 10] for i in range(8)], 4)
ck("resample 8→2", len(rs) == 2)
ck("4H#1 close=104", rs[0][4] == 104)
ck("4H#1 vol=40", rs[0][5] == 40)
futL = [[0, 100.5, 102.7, 99.9, 102.0, 1]]
ck("LONG→TP2", FN["bt_simulate_tp_stop"](100, 98, 101, 102.5, 104, futL, "LONG")["result"] == "TP2")
ck("LONG→STOP", FN["bt_simulate_tp_stop"](100, 98, 101, 102.5, 104, [[0, 99, 99.2, 97.5, 98, 1]], "LONG")["result"] == "STOP")
ck("sim bars alanı var", "bars" in FN["bt_simulate_tp_stop"](100, 98, 101, 102.5, 104, futL, "LONG"))
ck("LONG pnl kâr pozitif", FN["bt_calc_pnl"](100, 102.5, "LONG", 15) > 0)
ck("LONG stop pnl negatif", FN["bt_calc_pnl"](100, 98, "LONG", 15) < 0)
ser = [(100, "DOWN"), (200, "UP"), (300, "UP")]
ck("btc_at ts=150→DOWN", FN["_bt_btc_trend_at"](150, ser) == "DOWN")
ck("btc_at ts=50→FLAT", FN["_bt_btc_trend_at"](50, ser) == "FLAT")
_bris = [[1700 + i, 0, 0, 0, 100 + i, 0] for i in range(60)]
_bfal = [[1700 + i, 0, 0, 0, 200 - i, 0] for i in range(60)]
ck("BTC 1H serisi yükselen→UP", FN["_btc_dir_series"](_bris, 50)[-1][1] == "UP")
ck("BTC 1H serisi düşen→DOWN", FN["_btc_dir_series"](_bfal, 50)[-1][1] == "DOWN")

# ---- paginasyon birleştirme + gerçek funding maliyeti ----
_raw = [[3, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1], [2, 1, 1, 1, 1, 1], [2, 9, 9, 9, 9, 9]]
_asm = FN["_bt_assemble_klines"](_raw, 2)
ck("assemble ascending+dedup+son2 (ts [2,3])", [r[0] for r in _asm] == [2, 3])
ck("assemble dup'ta son kayıt (ts2 open=9)", _asm[0][1] == 9)
ck("assemble tümü dedup=3", len(FN["_bt_assemble_klines"](_raw, 10)) == 3)
_fh = [(1000, 0.01), (1500, 0.02), (2000, -0.005), (3000, 0.01)]
ck("LONG funding (1000,2500]=0.015", abs(FN["_bt_funding_cost"](_fh, 1000, 2500, "LONG") - 0.015) < 1e-9)
ck("SHORT funding aynı=-0.015 (gelir)", abs(FN["_bt_funding_cost"](_fh, 1000, 2500, "SHORT") + 0.015) < 1e-9)
ck("funding entry_ts hariç (ft=1000 sayılmaz)", abs(FN["_bt_funding_cost"](_fh, 1000, 1500, "LONG") - 0.02) < 1e-9)
ck("funding pencere dışı=0", FN["_bt_funding_cost"](_fh, 5000, 6000, "LONG") == 0)

# ---- likidite sweep motoru + ortak hedef ----
def _K(o, h, l, c): return [0, o, h, l, c, 1000.0]
_form = _K(99, 100, 98, 99)  # _s_closed bunu (oluşan mum) atar
_swL = [_K(100, 101, 95, 100) for _ in range(22)] + [_K(98, 99.5, 90, 99)] + [_form]
ck("boğa sweep → LONG", FN["detect_liquidity_sweep"](_swL, 20, 0.2)[0] == "LONG")
ck("süpürülen seviye ~95", abs(FN["detect_liquidity_sweep"](_swL, 20, 0.2)[1] - 95) < 1e-6)
_swH = [_K(100, 105, 99, 100) for _ in range(22)] + [_K(102, 110, 101, 101)] + [_K(101, 102, 100, 101)]
ck("ayı sweep → SHORT", FN["detect_liquidity_sweep"](_swH, 20, 0.2)[0] == "SHORT")
_no = [_K(100, 101, 95, 100) for _ in range(22)] + [_K(100, 101, 96, 100)] + [_form]
ck("sweep yok → None", FN["detect_liquidity_sweep"](_no, 20, 0.2)[0] is None)
_ss = FN["build_sweep_signal"]("X", _swL, [], balance_usdt=1000, risk_pct=1.5, leverage=5, lookback=20)
ck("sweep sinyali LONG", bool(_ss) and _ss["direction"] == "LONG")
ck("sweep stop < 90 (sweep low altı)", bool(_ss) and _ss["stop"] < 90)
ck("strategy=SWEEP", bool(_ss) and _ss["strategy"] == "SWEEP")
ck("sweep liq fiyatı dolu", bool(_ss) and _ss["liquidation_price"] > 0)
# MA7/MA25 yön (confluence) + onay filtresi
_upS = [_K(90 + i * 0.6, 91 + i * 0.6, 89 + i * 0.6, 90 + i * 0.6) for i in range(40)]
_dnS = [_K(150 - i * 0.6, 151 - i * 0.6, 149 - i * 0.6, 150 - i * 0.6) for i in range(40)]
ck("ma_side yükselen=LONG", FN["ma_side"](_upS) == "LONG")
ck("ma_side düşen=SHORT", FN["ma_side"](_dnS) == "SHORT")
_dnSweep = _dnS + [_K(127, 127.5, 120, 126.5)] + [_form]  # düşüşte boğa sweep
ck("düşüş+boğa sweep tespiti=LONG", FN["detect_liquidity_sweep"](_dnSweep, 20, 0.2)[0] == "LONG")
FN["SWEEP_MA_CONFIRM"] = True
ck("MA onay açık: boğa sweep + MA SHORT → None",
   FN["build_sweep_signal"]("X", _dnSweep, [], leverage=5, lookback=20) is None)
FN["SWEEP_MA_CONFIRM"] = False

# ---- balina pozisyon motoru (OI+fiyat+funding) ----
_D = FN["detect_whale_position"]
ck("fiyat↑+OI↑+funding normal→LONG", _D(1.5, 3.0, 0.0001, 0.5, 1.0, 0.0005) == "LONG")
ck("fiyat↓+OI↑→SHORT", _D(-1.5, 3.0, 0.0001, 0.5, 1.0, 0.0005) == "SHORT")
ck("OI artmıyor→None", _D(1.5, 0.2, 0.0001, 0.5, 1.0, 0.0005) is None)
ck("funding aşırı pozitif→None (geç)", _D(1.5, 3.0, 0.001, 0.5, 1.0, 0.0005) is None)
ck("fiyat yatay→None", _D(0.1, 3.0, 0.0001, 0.5, 1.0, 0.0005) is None)
_wup = [[0, 100 + i * 0.6, (100 + i * 0.6) * 1.004, (100 + i * 0.6) * 0.996, 100 + i * 0.6, 1000.0] for i in range(40)]
_wsig = FN["build_whale_signal"]("X", _wup, 4.0, 0.0001, balance_usdt=1000, risk_pct=1.5, leverage=5)
ck("balina sinyali LONG", bool(_wsig) and _wsig["direction"] == "LONG")
ck("strategy=WHALE", bool(_wsig) and _wsig["strategy"] == "WHALE")
ck("OI düşük→sinyal yok", FN["build_whale_signal"]("X", _wup, 0.1, 0.0001, leverage=5) is None)

# ---- paper ledger R hesabı (backtest maliyet modeliyle tutarlı) ----
ck("paper LONG kazanç ~+2R eksi maliyet", 1.8 < FN["_paper_r"](100, 98, 104, "LONG") < 2.0)
ck("paper LONG stop ~-1R", FN["_paper_r"](100, 98, 98, "LONG") < -0.9)
ck("paper SHORT kazanç ~+2R", 1.8 < FN["_paper_r"](100, 102, 96, "SHORT") < 2.0)
ck("paper risk_unit=0 → 0R", FN["_paper_r"](100, 100, 104, "LONG") == 0.0)

# ---- funding-ekstrem motoru (kalabalığın tersine) ----
_FD = FN["detect_funding_extreme"]
ck("funding++ & fiyat döndü→SHORT", _FD(0.001, -0.5, 0.0005, 0.0005, True, 0.3) == "SHORT")
ck("funding++ fiyat yukarı→None", _FD(0.001, 0.5, 0.0005, 0.0005, True, 0.3) is None)
ck("funding-- & fiyat döndü→LONG", _FD(-0.001, 0.5, 0.0005, 0.0005, True, 0.3) == "LONG")
ck("funding normal→None", _FD(0.0001, 0.0, 0.0005, 0.0005, True, 0.3) is None)
ck("teyit kapalı funding++→SHORT", _FD(0.001, 5.0, 0.0005, 0.0005, False, 0.3) == "SHORT")
_fhA = [(1000, 0.0001), (2000, 0.0008), (3000, -0.0003)]
ck("funding_at ts=2500→0.0008", FN["_bt_funding_at"](_fhA, 2500) == 0.0008)
ck("funding_at ts=999→0", FN["_bt_funding_at"](_fhA, 999) == 0.0)
_fdown = [[0, 150 - i * 0.5, (150 - i * 0.5) * 1.004, (150 - i * 0.5) * 0.996, 150 - i * 0.5, 1000.0] for i in range(40)]
_fsig = FN["build_funding_signal"]("X", _fdown, 0.001, balance_usdt=1000, risk_pct=1.5, leverage=5)
ck("funding sinyali SHORT", bool(_fsig) and _fsig["direction"] == "SHORT")
ck("strategy=FUNDING", bool(_fsig) and _fsig["strategy"] == "FUNDING")
ck("normal funding→sinyal yok", FN["build_funding_signal"]("X", _fdown, 0.0001, leverage=5) is None)
ck("MA onay kapalı: aynı sweep → sinyal var",
   bool(FN["build_sweep_signal"]("X", _dnSweep, [], leverage=5, lookback=20)))
ck("RR modu tp2=2.5R=107.5", abs(FN["_targets_for"](100, 97, "LONG")["tp2"] - 107.5) < 1e-9)
FN["HYBRID_FIXED_TARGETS"] = True
_fx = FN["_targets_for"](100, 98.6, "LONG")
ck("sabit modu tp1=+4%=104", abs(_fx["tp1"] - 104) < 1e-9)
ck("sabit modu tp1_rr=4/1.4≈2.86", abs(_fx["tp1_rr"] - 2.86) < 0.01)
FN["HYBRID_FIXED_TARGETS"] = False

print(f"\n=== {PASS} geçti, {FAIL} kaldı ===")
sys.exit(1 if FAIL else 0)
