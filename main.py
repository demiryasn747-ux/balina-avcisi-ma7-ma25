    Ard arda gelen iki ZIT pivot arasındaki mesafe min_fark'tan küçükse o pivot
    yapısal değildir, atılır. Aynı tip ard arda gelirse daha uç olanı kalır.
    APT yanlış SHORT vakasının kök nedeni buydu: 0.25 ATR'lik bir kıpırtı
    event_side'ı belirlerken, gerçek yapısal dip hiç değerlendirilmiyordu."""
    if min_fark <= 0 or len(sw) < 2:
        return sw
    out = []
    for s_ in sw:
        if not out:
            out.append(s_); continue
        onceki = out[-1]
        if s_.kind == onceki.kind:
            if (s_.kind == "H" and s_.price >= onceki.price) or \
               (s_.kind == "L" and s_.price <= onceki.price):
                out[-1] = s_
            continue
        if abs(s_.price - onceki.price) < min_fark:
            continue
        out.append(s_)
    return out


def v10_find_swings(k, left, right, min_fark=0.0):
    H = highs(k); L = lows(k); n = len(k); sw = []
    for i in range(left, n - right):
        wh = H[i-left:i+right+1]; wl = L[i-left:i+right+1]
        if H[i] == max(wh) and wh.count(H[i]) == 1:
            sw.append(V10Swing(i, H[i], "H"))
        elif L[i] == min(wl) and wl.count(L[i]) == 1:
            sw.append(V10Swing(i, L[i], "L"))
    ham = len(sw)
    sw = v107_pivot_ele(sw, min_fark)
    if ham != len(sw):
        stats["v107_pivot_elendi"] = int(stats.get("v107_pivot_elendi", 0)) + (ham - len(sw))
    return sw


def v10_market_structure(k):
    # V10.7: pivot belirginlik eşiği ATR cinsinden
    try:
        _a = atr(k, V10_ATR_PERIOD)[-1] if V107_PIVOT_ATR > 0 else 0.0
    except Exception:
        _a = 0.0
    min_fark = _a * V107_PIVOT_ATR if (_a and _a > 0) else 0.0
    sw = v10_find_swings(k, V10_SWING_LEFT, V10_SWING_RIGHT, min_fark)
    res = {"trend":"RANGE","hh":False,"hl":False,"lh":False,"ll":False,
           "last_sh":0.0,"last_sh_idx":-1,"last_sl":0.0,"last_sl_idx":-1,
           "prev_sh":0.0,"prev_sh_idx":-1,"prev_sl":0.0,"prev_sl_idx":-1,
           "event":None,"event_side":None,"event_level":0.0,"event_idx":-1,
           "range_break":False,"atr":_a}
    hs = [s for s in sw if s.kind == "H"]; ls = [s for s in sw if s.kind == "L"]
    if hs: res["last_sh"] = hs[-1].price; res["last_sh_idx"] = hs[-1].idx
    if ls: res["last_sl"] = ls[-1].price; res["last_sl_idx"] = ls[-1].idx
    # V10.8: bir önceki pivot — onarılmış sweep dedektörü bunu referans alır
    if len(hs) >= 2: res["prev_sh"] = hs[-2].price; res["prev_sh_idx"] = hs[-2].idx
    if len(ls) >= 2: res["prev_sl"] = ls[-2].price; res["prev_sl_idx"] = ls[-2].idx
    if len(hs) >= 2:
        res["hh"] = hs[-1].price > hs[-2].price; res["lh"] = hs[-1].price < hs[-2].price
    if len(ls) >= 2:
        res["hl"] = ls[-1].price > ls[-2].price; res["ll"] = ls[-1].price < ls[-2].price
    if res["hh"] and res["hl"]: res["trend"] = "UP"
    elif res["lh"] and res["ll"]: res["trend"] = "DOWN"
    lc = closes(k)[-1]
    # V10.7: RANGE bağlamı artık "BOS (devam)" diye etiketlenmiyor.
    # V10.6'da ternary'nin else dalı RANGE'i yakalıyor ve devam edecek trend
    # yokken "devam" yazıyordu — loglarda "Boğa BOS (devam) | 1H:RANGE" böyle çıktı.
    if res["last_sh"] > 0 and lc > res["last_sh"]:
        res["event"] = "CHoCH" if res["trend"] == "DOWN" else "BOS"
        res["event_side"] = "UP"; res["event_level"] = res["last_sh"]; res["event_idx"] = res["last_sh_idx"]
        res["range_break"] = (res["trend"] == "RANGE")
    elif res["last_sl"] > 0 and lc < res["last_sl"]:
        res["event"] = "CHoCH" if res["trend"] == "UP" else "BOS"
        res["event_side"] = "DOWN"; res["event_level"] = res["last_sl"]; res["event_idx"] = res["last_sl_idx"]
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
    mv = (c[-1] - c[-1-V10_FOMO_LOOKBACK]) / c[-1-V10_FOMO_LOOKBACK] * 100.0
    if side == "LONG" and mv > V10_FOMO_MAX_MOVE: return True, mv
    if side == "SHORT" and mv < -V10_FOMO_MAX_MOVE: return True, mv
    return False, mv


def v10_pullback(side, k, ms):
    lvl = safe_float(ms.get("event_level"))
    if lvl <= 0 or ms.get("event_side") not in ("UP", "DOWN"):
        return False, ""
    ev_idx = int(ms.get("event_idx", -1)); n = len(k)
    seg = k[max(ev_idx+1, n-V10_PULLBACK_WAIT):]
    if len(seg) < 2:
        return False, ""
    tol = V10_PULLBACK_TOL / 100.0
    last = k[-1]; lc=safe_float(last[4]); ll=safe_float(last[3]); lh=safe_float(last[2]); lo=safe_float(last[1])
    if side == "LONG":
        touched = any(safe_float(r[3]) <= lvl*(1+tol) for r in seg)
        if (touched and lc > lvl and lc > lo) or (lc > lvl and ll <= lvl*(1+tol)):
            return True, f"retest @ {lvl:.6g}"
    else:
        touched = any(safe_float(r[2]) >= lvl*(1-tol) for r in seg)
        if (touched and lc < lvl and lc < lo) or (lc < lvl and lh >= lvl*(1-tol)):
            return True, f"retest @ {lvl:.6g}"
    return False, ""


def v10_detect_order_block(side, k):
    n = len(k); seg = k[max(0, n-V10_OB_LOOKBACK):]
    zone = None
    for r in reversed(seg):
        o = safe_float(r[1]); c = safe_float(r[4])
        if side == "LONG" and c < o: zone = (safe_float(r[3]), safe_float(r[2])); break
        if side == "SHORT" and c > o: zone = (safe_float(r[3]), safe_float(r[2])); break
    if not zone: return 0.0
    lo, hi = zone; price = safe_float(k[-1][4])
    tol = (hi-lo)*0.5 if hi > lo else price*0.003
    if side == "LONG":
        return 1.0 if lo-tol <= price <= hi+tol else 0.3 if price > hi else 0.0
    return 1.0 if lo-tol <= price <= hi+tol else 0.3 if price < lo else 0.0


def v10_detect_fvg(side, k):
    n = len(k); best = None
    for i in range(max(1, n-V10_FVG_LOOKBACK), n-1):
        if i+1 >= n: break
        if side == "LONG":
            h0 = safe_float(k[i-1][2]); l2 = safe_float(k[i+1][3])
            if h0 < l2 and not any(safe_float(k[j][3]) <= h0 for j in range(i+2, n)): best = True
        else:
            l0 = safe_float(k[i-1][3]); h2 = safe_float(k[i+1][2])
            if l0 > h2 and not any(safe_float(k[j][2]) >= l0 for j in range(i+2, n)): best = True
    return 1.0 if best else 0.0


def v10_volume_profile(k):
    seg = k[-V10_VP_LOOKBACK:] if len(k) > V10_VP_LOOKBACK else k
    H = highs(seg); L = lows(seg); lo = min(L); hi = max(H)
    if hi <= lo: return None
    w = (hi-lo)/V10_VP_BINS; prof = [0.0]*V10_VP_BINS
    for r in seg:
        mid = (safe_float(r[2])+safe_float(r[3]))/2; v = safe_float(r[5])
        idx = min(V10_VP_BINS-1, max(0, int((mid-lo)/w))); prof[idx] += v
    poc_idx = max(range(V10_VP_BINS), key=lambda i: prof[i])
    poc = lo + (poc_idx+0.5)*w
    total = sum(prof); target = total*0.7
    order = sorted(range(V10_VP_BINS), key=lambda i: prof[i], reverse=True)
    acc = 0.0; sel = set()
    for i in order:
        acc += prof[i]; sel.add(i)
        if acc >= target: break
    return {"poc":poc,"vah":lo+(max(sel)+1)*w,"val":lo+min(sel)*w}


def v10_vp_score(side, price, vp):
    if not vp: return 0.5
    if side == "LONG":
        return 1.0 if price > vp["poc"] else 0.5 if price >= vp["val"] else 0.2
    return 1.0 if price < vp["poc"] else 0.5 if price <= vp["vah"] else 0.2


def v10_cvd_proxy(k):
    seg = k[-V10_CVD_WINDOW:]; cvd = 0.0; series = []
    for r in seg:
        o = safe_float(r[1]); c = safe_float(r[4]); v = safe_float(r[5])
        cvd += v if c >= o else -v; series.append(cvd)
    return (series[-1]-series[0]) if len(series) >= 2 else 0.0


def v10_detect_sweep(side, k, ms):
    seg = k[-V10_SWEEP_LOOKBACK:]
    sl = safe_float(ms.get("last_sl")); sh = safe_float(ms.get("last_sh"))
    if side == "LONG" and sl > 0:
        for r in seg:
            o=safe_float(r[1]); c=safe_float(r[4]); l=safe_float(r[3])
            if l < sl and c > sl and (min(o,c)-l) > (abs(c-o)+1e-9)*V10_SWEEP_MIN_WICK:
                return 1.0
    if side == "SHORT" and sh > 0:
        for r in seg:
            o=safe_float(r[1]); c=safe_float(r[4]); h=safe_float(r[2])
            if h > sh and c < sh and (h-max(o,c)) > (abs(c-o)+1e-9)*V10_SWEEP_MIN_WICK:
                return 1.0
    return 0.0


# ============================================================================ #
#  V10.8 — SWEEP DEDEKTÖRÜ ONARIMI
#  Ölçüm (6000 senaryo): eski dedektör CHoCH kurulumlarının %0.17'sinde,
#  BOS'ların %0.84'ünde ateş ediyordu. Paylaşılan 9 canlı sinyalin 9'unda da
#  Sweep▫️ vardı. Yani 7 puanlık terim pratikte ÖLÜ, hep 0 dönüyordu.
#
#  Kök neden — iki ayrı hata:
#   (1) YANLIŞ SEVİYE: Ayı olayı "kapanış < last_sl" demek. Eski kod SHORT için
#       last_sh'ın delinmesini arıyor. Aynı 6 mumda hem tepeyi hem dibi kırmak
#       gerekiyordu; ölçümde last_sh, son 6 mumun tepesinin medyan %0.64
#       üstünde kalıyor, sadece %0.99 vakada gerçekten deliniyordu.
#   (2) YANLIŞ PENCERE: gerçek likidite avı, yapı kırılmadan ÖNCE — pivotun
#       oluştuğu mumda — olur. Son 6 muma bakmak o anı kaçırır.
#
#  Onarım: sweep artık iki yoldan tespit edilir.
#   A) YAPISAL  : son pivotun KENDİSİ bir avdı — o mumun fitili bir ÖNCEKİ
#                 pivotu deldi, ama kapanış geri döndü (klasik stop avı).
#   B) PENCERE  : son N mumda ilgili pivot delinip geri alındı (eski davranışın
#                 doğru seviyeye bağlanmış ve genişletilmiş hali).
#  Hiçbir filtre zorunlu hale getirilmedi; bu sadece skor terimini diriltir.
# ============================================================================ #
V108_SWEEP_ONARIM  = os.getenv("V108_SWEEP_ONARIM", "true").lower() == "true"
V108_SWEEP_PENCERE = int(float(os.getenv("V108_SWEEP_PENCERE", "20")))
V108_SWEEP_FITIL   = float(os.getenv("V108_SWEEP_FITIL", "0.5"))
# CHoCH kurulumlarında sweep teyidini ZORUNLU kılar.
# V10.9: canlı ölçüm sonrası AÇILDI. 15-17 Ağu defterinde Sweep✅ %50 oranında
# geliyordu (akış ölmüyor) ve kapı açık olsaydı CC + BAT kesilip +2.00R
# kurtarılacaktı; DOT kazananı BOS olduğu için etkilenmezdi.
V108_CHOCH_SWEEP_ZORUNLU = os.getenv("V108_CHOCH_SWEEP_ZORUNLU", "true").lower() == "true"

# ============================================================================ #
#  V10.9 — CHoCH'ta COIN'İN KENDİ 1H TREND UYUMU
#
#  ÖNEMLİ TESPİT: mesajdaki "1H:UP" etiketi (ms["trend"]) bu iş için KULLANILAMAZ.
#  Ayı CHoCH'un tanımı zaten "trend UP iken last_sl kırıldı" demek — 8000
#  senaryoda Ayı CHoCH'un 421/421'i 1H:UP, Boğa CHoCH'un 414/414'ü 1H:DOWN
#  çıktı. Yani "CHoCH'ta 1H uyumu ara" o etikete bakılarak yazılırsa TÜM CHoCH
#  kolunu siler; filtre değil, kapatma düğmesi olur.
#
#  Bu yüzden uyum, BTC'ye uygulanan testin AYNISIYLA ölçülür: coin'in kendi 1H
#  EMA20/EMA50 ilişkisi. Bu pivot yapısından bağımsızdır — bir coin'in pivotları
#  hâlâ HH/HL yaparken EMA'sı çoktan aşağı kesmiş olabilir; asıl aradığımız da
#  tam olarak bu ayrım.
#
#  SHORT CHoCH → coin 1H EMA20 < EMA50 şart | LONG CHoCH → EMA20 > EMA50 şart
#  Sadece CHoCH'a uygulanır; BOS kurulumları etkilenmez.
# ============================================================================ #
V109_COIN_1H_UYUM      = os.getenv("V109_COIN_1H_UYUM", "true").lower() == "true"
V109_COIN_EMA_FAST     = int(float(os.getenv("V109_COIN_EMA_FAST", "20")))
V109_COIN_EMA_SLOW     = int(float(os.getenv("V109_COIN_EMA_SLOW", "50")))
V109_COIN_1H_FLAT_GECER = os.getenv("V109_COIN_1H_FLAT_GECER", "false").lower() == "true"


def v109_coin_1h_yon(k1h):
    """Coin'in kendi 1H EMA20/EMA50 yönü. Kapanmış mumlarla, repaint yok.
    Döner: "UP" | "DOWN" | "FLAT" (veri yetersizse FLAT)."""
    try:
        c = closes(_s_closed(k1h))
        if len(c) < V109_COIN_EMA_SLOW + 2:
            return "FLAT"
        f = ema(c, V109_COIN_EMA_FAST)[-1]
        y = ema(c, V109_COIN_EMA_SLOW)[-1]
        if f > y: return "UP"
        if f < y: return "DOWN"
    except Exception as e:
        logger.warning("V10.9 coin 1H EMA yönü hesaplanamadı: %s", e)
    return "FLAT"


def _v108_pivotlar(ms, kind):
    """Son iki pivotu (fiyat, indeks) olarak döner: (son, onceki)."""
    if kind == "H":
        return (safe_float(ms.get("last_sh")), int(ms.get("last_sh_idx", -1)),
                safe_float(ms.get("prev_sh")), int(ms.get("prev_sh_idx", -1)))
    return (safe_float(ms.get("last_sl")), int(ms.get("last_sl_idx", -1)),
            safe_float(ms.get("prev_sl")), int(ms.get("prev_sl_idx", -1)))


def v108_sweep_tespit(side, k, ms):
    """Onarılmış sweep dedektörü. Döner: (skor 0..1, açıklama)."""
    if not V108_SWEEP_ONARIM:
        return v10_detect_sweep(side, k, ms), ""
    n = len(k)
    kind = "L" if side == "LONG" else "H"
    son, son_idx, onceki, onceki_idx = _v108_pivotlar(ms, kind)
    if son <= 0:
        return 0.0, ""

    def _fitil_ok(r, yon):
        o = safe_float(r[1]); c = safe_float(r[4])
        h = safe_float(r[2]); l = safe_float(r[3])
        govde = abs(c - o) + 1e-9
        return ((min(o, c) - l) if yon == "alt" else (h - max(o, c))) > govde * V108_SWEEP_FITIL

    # --- A) YAPISAL: son pivotun kendisi bir likidite avıydı ---
    if onceki > 0 and 0 <= son_idx < n:
        r = k[son_idx]
        c = safe_float(r[4]); h = safe_float(r[2]); l = safe_float(r[3])
        if side == "LONG" and l < onceki and c > onceki and _fitil_ok(r, "alt"):
            return 1.0, "yapısal"
        if side == "SHORT" and h > onceki and c < onceki and _fitil_ok(r, "ust"):
            return 1.0, "yapısal"

    # --- B) PENCERE: son N mumda ilgili pivot delinip geri alındı ---
    bas = max(0, n - V108_SWEEP_PENCERE)
    for i in range(bas, n):
        if i == son_idx:
            continue
        r = k[i]
        c = safe_float(r[4]); h = safe_float(r[2]); l = safe_float(r[3])
        if side == "LONG" and l < son and c > son and _fitil_ok(r, "alt"):
            return 1.0, "pencere"
        if side == "SHORT" and h > son and c < son and _fitil_ok(r, "ust"):
            return 1.0, "pencere"
    return 0.0, ""


def v107_oi_skor(side, oi_pct, fiyat_pct):
    """V10.7: OI skoru artık YÖN FARKINDA.
    V10.6'da 'oi > 0.5 -> tam puan' hem LONG hem SHORT için aynıydı; 9 puanlık
    terim hiçbir yönsel bilgi taşımıyordu.
    Standart yorum:
      fiyat YUKARI + OI YUKARI  -> yeni LONG'lar açılıyor      (boğa teyidi)
      fiyat AŞAĞI  + OI YUKARI  -> yeni SHORT'lar açılıyor     (ayı teyidi)
      fiyat YUKARI + OI AŞAĞI   -> short kapanışı (zayıf ralli)
      fiyat AŞAĞI  + OI AŞAĞI   -> long likidasyonu (zayıf düşüş)
    Döner: (0..1 çarpan, açıklama)"""
    if abs(oi_pct) < 0.05:
        return 0.2, "OI yatay"
    oi_up = oi_pct > 0
    fiyat_up = fiyat_pct >= 0
    if oi_up and fiyat_up:
        return (1.0, "yeni long girişi") if side == "LONG" else (0.3, "yeni long girişi — SHORT'a ters")
    if oi_up and not fiyat_up:
        return (1.0, "yeni short girişi") if side == "SHORT" else (0.3, "yeni short girişi — LONG'a ters")
    if (not oi_up) and fiyat_up:
        return (0.5, "short kapanışı — zayıf ralli") if side == "LONG" else (0.4, "short kapanışı")
    return (0.5, "long likidasyonu — zayıf düşüş") if side == "SHORT" else (0.4, "long likidasyonu")


def v10_quality_score(side, k, ms, ext):
    """Döner: (skor, parça sözlüğü, rsi, confluence bayrakları).
    V10.7: bayraklar ayrı döner — V10.6'da mesajdaki ✅ işaretleri 'puan > 0'
    testine bakıyordu, ama CVD/VP/OB bileşenlerinin TABAN puanı sıfırdan büyük
    olduğu için bu üçü HER sinyalde ✅ görünüyordu."""
    p = {}
    bayrak = {}
    ok, _ = v10_structure_allows(side, ms)
    s = 18.0 if ok else 0.0
    if ok and ms.get("event") == "CHoCH": s *= 0.85
    p["structure"] = s
    vols = [safe_float(r[5]) for r in k[-21:-1]]; av = sum(vols)/len(vols) if vols else 0.0
    lv = safe_float(k[-1][5]); p["volume"] = 2.0*min(1.0, max(0.0, (lv/av-0.8)/0.7)) if av > 0 else 0.0
    bayrak["volume"] = bool(av > 0 and lv > av)
    r = rsi(closes(k))[-1]
    if side == "LONG": p["rsi"] = 7.0*(1.0 if 45 <= r <= 65 else 0.5 if 35 <= r <= 75 else 0.1)
    else: p["rsi"] = 7.0*(1.0 if 35 <= r <= 55 else 0.5 if 25 <= r <= 65 else 0.1)
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
    if side == "LONG": p["funding"] = 7.0*(0.2 if fr > 0.0008 else 1.0 if fr < 0 else 0.7)
    else: p["funding"] = 7.0*(0.2 if fr < -0.0008 else 1.0 if fr > 0 else 0.7)
    btc4h = str(ext.get("btc_dir", "FLAT")).upper()
    btc1h = str(ext.get("btc_dir_1h", "FLAT")).upper()
    if side == "LONG":
        if btc4h == "UP" and btc1h == "UP": btc_mult = 1.0      # ikisi de yukarı → tam güç
        elif btc4h == "UP" or btc1h == "UP": btc_mult = 0.7     # sadece biri yukarı
        elif btc4h == "DOWN" and btc1h == "DOWN": btc_mult = 0.15  # ikisi de aşağı → LONG'a karşı
        else: btc_mult = 0.5                                    # FLAT / karışık
    else:
        if btc4h == "DOWN" and btc1h == "DOWN": btc_mult = 1.0
        elif btc4h == "DOWN" or btc1h == "DOWN": btc_mult = 0.7
        elif btc4h == "UP" and btc1h == "UP": btc_mult = 0.15
        else: btc_mult = 0.5
    p["btc"] = 14.0 * btc_mult
    ob = ext.get("orderbook") or {}; imb = safe_float(ob.get("imbalance"))
    if side == "LONG":
        obs = (0.6 if imb > 0.15 else 0.3 if imb > 0 else 0.0) + (0.4 if ob.get("bid_wall") else 0.0)
    else:
        obs = (0.6 if imb < -0.15 else 0.3 if imb < 0 else 0.0) + (0.4 if ob.get("ask_wall") else 0.0)
    p["orderbook"] = 7.0*min(1.0, obs)
    bayrak["orderbook"] = obs > 0.0
    _ob_ham = v10_detect_order_block(side, k)
    p["order_block"] = 11.0*_ob_ham
    bayrak["order_block"] = _ob_ham >= 1.0          # sadece fiyat OB bölgesinin İÇİNDEyse ✅
    _fvg_ham = v10_detect_fvg(side, k)
    p["fvg"] = 8.0*_fvg_ham
    bayrak["fvg"] = _fvg_ham > 0.0
    _vp_ham = v10_vp_score(side, safe_float(k[-1][4]), v10_volume_profile(k))
    p["volume_profile"] = 5.0*_vp_ham
    bayrak["volume_profile"] = _vp_ham >= 1.0       # POC'un doğru tarafındaysa ✅
    cv = v10_cvd_proxy(k)
    _cvd_uyum = (cv > 0 and side == "LONG") or (cv < 0 and side == "SHORT")
    p["cvd"] = 5.0*(1.0 if _cvd_uyum else 0.2)
    bayrak["cvd"] = bool(_cvd_uyum)
    _sw_ham, _sw_tip = v108_sweep_tespit(side, k, ms)
    p["sweep"] = 7.0*_sw_ham
    bayrak["sweep"] = _sw_ham > 0.0
    ext["sweep_tip"] = _sw_tip
    # V10.8: canlı isabet sayacı — kapıyı açma kararı bu orana bakılarak verilecek
    stats["v108_sweep_tot"] = int(stats.get("v108_sweep_tot", 0)) + 1
    if _sw_ham > 0:
        stats["v108_sweep_var"] = int(stats.get("v108_sweep_var", 0)) + 1
        anahtar = "v108_sweep_yapisal" if _sw_tip == "yapısal" else "v108_sweep_pencere"
        stats[anahtar] = int(stats.get(anahtar, 0)) + 1
    return (round(sum(p.values()), 1),
            {kk: round(vv, 1) for kk, vv in p.items()},
            round(r, 1), bayrak)


def v10_targets(side, entry, a, fib=None):
    dist = min(max(a*V10_ATR_MULT, entry*V10_STOP_MIN_PCT), entry*V10_STOP_MAX_PCT)
    # V10.7: stop kaç ATR'lik? MIN==MAX ise ATR terimi tamamen kırpılmış demektir
    # (V10.6'da öyleydi: her sinyalde stop tam %2, volatiliteden bağımsız).
    stop_atr = (dist / a) if (a and a > 0) else 0.0
    kirpildi = abs(V10_STOP_MAX_PCT - V10_STOP_MIN_PCT) < 1e-9
    stop = entry-dist if side == "LONG" else entry+dist
    risk = abs(entry-stop)
    if side == "LONG":
        tp1, tp2, tp3 = entry+risk*V10_TP1_RR, entry+risk*V10_TP2_RR, entry+risk*V10_TP3_RR
    else:
        tp1, tp2, tp3 = entry-risk*V10_TP1_RR, entry-risk*V10_TP2_RR, entry-risk*V10_TP3_RR
    tp_kaynak = "ATR"
    if fib:
        def _rr(px):
            return (px - entry) / risk if side == "LONG" else (entry - px) / risk
        f2, f3 = fib.get("ext_1272"), fib.get("ext_1618")
        if f2 and f3 and f2 > 0 and f3 > 0 and _rr(f2) >= 1.5 and _rr(f3) > _rr(f2):
            tp2, tp3 = f2, f3
            tp_kaynak = "FİB"
            # V10.7: isteğe bağlı üst sınır (varsayılan kapalı -> davranış V10.6 ile aynı)
            if V107_MAX_TP_RR > 0:
                sinir2 = entry + risk*V107_MAX_TP_RR if side == "LONG" else entry - risk*V107_MAX_TP_RR
                sinir3 = entry + risk*V107_MAX_TP_RR*1.25 if side == "LONG" else entry - risk*V107_MAX_TP_RR*1.25
                if _rr(tp2) > V107_MAX_TP_RR:
                    tp2 = sinir2; tp3 = sinir3; tp_kaynak = "FİB-kırpık"
    return {"stop":stop,"stop_pct":round(dist/entry*100,3),"risk":risk,
            "tp1":tp1,"tp2":tp2,"tp3":tp3,"tp_kaynak":tp_kaynak,
            "tp1_rr":round(abs(tp1-entry)/risk,2),
            "tp2_rr":round(abs(tp2-entry)/risk,1),"tp3_rr":round(abs(tp3-entry)/risk,1),
            "stop_atr":round(stop_atr,2),"stop_sabit":kirpildi}


async def v10_fetch_orderbook(symbol):
    blank = {"imbalance":0.0,"bid_wall":False,"ask_wall":False,"mid":0.0,"bid":0.0,"ask":0.0}
    if not V10_USE_ORDERBOOK:
        return blank
    try:
        data = await _okx_get_async("/api/v5/market/books",
                                       {"instId": symbol, "sz": V10_OB_DEPTH})
        if not data:
            return blank
        book = data[0]
        bsz = [safe_float(x[1]) for x in book.get("bids", [])[:V10_OB_DEPTH]]
        asz = [safe_float(x[1]) for x in book.get("asks", [])[:V10_OB_DEPTH]]
        bids = sum(bsz); asks = sum(asz); tot = bids+asks
        imb = (bids-asks)/tot if tot > 0 else 0.0
        bmean = bids/len(bsz) if bsz else 0; amean = asks/len(asz) if asz else 0
        # V10.7: canlı giriş fiyatı için en iyi alış/satış
        try:
            bid = safe_float(book.get("bids", [[0]])[0][0])
            ask = safe_float(book.get("asks", [[0]])[0][0])
        except Exception:
            bid = ask = 0.0
        mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else 0.0
        return {"imbalance": imb,
                "bid_wall": (max(bsz) > bmean*V10_OB_WALL_MULT) if bsz and bmean > 0 else False,
                "ask_wall": (max(asz) > amean*V10_OB_WALL_MULT) if asz and amean > 0 else False,
                "mid": mid, "bid": bid, "ask": ask}
    except Exception as e:
        logger.debug("V10 ob fail %s: %s", symbol, e)
        return blank


def v10_structure_gate(symbol, k1h, k4h, allowed_side=None):
    k = _s_closed(k1h)
    if len(k) < 40:
        return None
    ms = v10_market_structure(k)
    trend4 = "FLAT"
    if V10_USE_4H_FILTER and k4h and len(k4h) >= 52:
        c4 = closes(_s_closed(k4h)); e = ema(c4, min(50, len(c4)-1))
        trend4 = "UP" if c4[-1] > e[-1] else "DOWN"
    if V107_RANGE_ENGELLE and ms.get("range_break"):
        stats["v107_red_range"] = int(stats.get("v107_red_range", 0)) + 1
        return None
    for side in ("LONG", "SHORT"):
        ok, why = v10_structure_allows(side, ms)
        if not ok: continue
        # --- V10.6: zorunlu BTC trend filtresi (BTC'ye ters yön hiç değerlendirilmez) ---
        if allowed_side and side != allowed_side:
            stats["v10_red_btc_ters"] = int(stats.get("v10_red_btc_ters", 0)) + 1
            logger.info("V10.6 %s %s → %s", symbol, side, V106_TREND_BLOCK_LINE)
            continue
        if V10_USE_4H_FILTER and trend4 != "FLAT":
            if side == "LONG" and trend4 != "UP": continue
            if side == "SHORT" and trend4 != "DOWN": continue
        blk, mv = v10_fomo_block(side, k)
        if blk: continue
        # --- V10.8: CHoCH → sweep teyidi (VARSAYILAN KAPALI) -------------------
        # Onarılmış dedektörle bile CHoCH'ların ~%17'si geçiyor; açmak akışın
        # büyük kısmını keser. Canlı Sweep✅ oranı görülene kadar kapalı.
        # Açmak için: V108_CHOCH_SWEEP_ZORUNLU=true
        if V108_CHOCH_SWEEP_ZORUNLU and ms.get("event") == "CHoCH":
            _sk, _ = v108_sweep_tespit(side, k, ms)
            if _sk <= 0:
                stats["v108_red_choch_sweep"] = int(stats.get("v108_red_choch_sweep", 0)) + 1
                logger.info("V10.8 %s %s → CHoCH sweep teyidi yok, kesildi", symbol, side)
                continue
        # --- V10.9: CHoCH'ta coin'in KENDİ 1H EMA yönü sinyalle uyuşmalı ---
        # (ms["trend"] burada işe yaramaz — CHoCH tanımı gereği hep ters, bkz. üstteki not)
        if V109_COIN_1H_UYUM and ms.get("event") == "CHoCH":
            _cy = v109_coin_1h_yon(k1h)
            _ters = (side == "LONG" and _cy == "DOWN") or (side == "SHORT" and _cy == "UP")
            _bilinmiyor = (_cy == "FLAT" and not V109_COIN_1H_FLAT_GECER)
            if _ters or _bilinmiyor:
                stats["v109_red_coin_1h"] = int(stats.get("v109_red_coin_1h", 0)) + 1
                logger.info("V10.9 %s %s → coin 1H EMA yönü %s, CHoCH kesildi", symbol, side, _cy)
                continue
        pb, note = v10_pullback(side, k, ms)
        if not pb: continue
        return {"side":side,"ms":ms,"why":why,"trend4":trend4,"fomo":round(mv,2),
                "pullback":note,"k":k,"coin_1h_ema":v109_coin_1h_yon(k1h)}
    return None


def v107_canli_giris(k1h, ob, referans):
    """V10.7 — EN KRİTİK DÜZELTME.
    V10.6: entry = closes(_s_closed(k1h))[-1]  -> son KAPANMIŞ 1H mumun kapanışı.
    Yani giriş fiyatı 59 dakikaya kadar bayat olabiliyordu; buna karşılık
    v10_paper_loop stopu CANLI fiyatla kontrol ediyordu. Sinyal gittiği anda
    fiyat zaten %2 aşağıdaysa pozisyon saniyeler içinde stop oluyordu.
    Bu asimetri deftere sistematik negatif kayma enjekte ediyordu.

    Öncelik: orderbook orta fiyatı -> oluşmakta olan mumun son fiyatı -> referans.
    Döner: (giris, kaynak)"""
    if not V107_CANLI_GIRIS:
        return referans, "kapanis"
    ref = safe_float(referans)
    mid = safe_float((ob or {}).get("mid"))
    # sağlık kontrolü: orderbook fiyatı referanstan %10'dan fazla sapıyorsa veri bozuk
    if mid > 0 and ref > 0 and abs(mid - ref) / ref <= 0.10:
        return mid, "orderbook"
    try:
        forming = safe_float(k1h[-1][4])
    except Exception:
        forming = 0.0
    if forming > 0 and ref > 0 and abs(forming - ref) / ref <= 0.30:
        return forming, "canli mum"
    return ref, "kapanis"


async def analyze_v10_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    symbol = normalize_symbol(symbol)

    # === V10.6 KURAL 1: ZORUNLU BTC TREND FİLTRESİ (her şeyden önce) ===
    allowed_side = None
    btc_1h = "FLAT"; btc_4h = "FLAT"
    if V106_BTC_TREND_FILTER:
        bt = await v106_btc_trend()
        btc_1h = bt.get("dir_1h", "FLAT"); btc_4h = bt.get("dir_4h", "FLAT")
        if not bt.get("ok"):
            stats["v10_red_btc_veri"] = int(stats.get("v10_red_btc_veri", 0)) + 1
            return None
        allowed_side = bt.get("allow")
        if not allowed_side:          # 1H ile 4H uyuşmuyor → hiç sinyal basma
            stats["v10_red_btc_karisik"] = int(stats.get("v10_red_btc_karisik", 0)) + 1
            return None
    else:
        bt = await v106_btc_trend()
        btc_1h = bt.get("dir_1h", "FLAT"); btc_4h = bt.get("dir_4h", "FLAT")

    k1h = await get_klines(symbol, MA_KLINE_INTERVAL, V10_KLINE_LIMIT)
    if len(k1h) < 40:
        stats["v10_red_veri"] = int(stats.get("v10_red_veri", 0)) + 1
        return None
    k4h = await get_klines(symbol, HYBRID_TREND_TF, 120, ttl=V107_4H_CACHE_SEC) if V10_USE_4H_FILTER else None
    gate = v10_structure_gate(symbol, k1h, k4h, allowed_side)
    if not gate:
        stats["v10_red_yapi"] = int(stats.get("v10_red_yapi", 0)) + 1
        return None
    side = gate["side"]; k = gate["k"]
    oi = await fetch_okx_oi_change(symbol, V10_OI_LOOKBACK_PER)
    funding = await fetch_okx_funding_rate(symbol)
    ob = await v10_fetch_orderbook(symbol)
    ext = {"oi_change_pct": oi if oi is not None else 0.0,
           "funding": funding, "btc_dir": btc_4h, "btc_dir_1h": btc_1h, "orderbook": ob}
    score, parts, r, bayrak = v10_quality_score(side, k, gate["ms"], ext)

    # --- Fibonacci: bonus + V10.6 KURAL 2 zorunlu derinlik kapısı ---
    fib = fib_leg_and_depth(side, lows(k), highs(k), closes(k))
    if fib and V10_FIB_ENABLED:
        score = round(score + fib["bonus"], 1)
        parts["fib"] = fib["bonus"]
    min_depth = V106_FIB_MIN_DEPTH_LONG if side == "LONG" else V106_FIB_MIN_DEPTH_SHORT
    min_depth = max(min_depth, V10_FIB_MIN_DEPTH)
    if min_depth > 0 and (not fib or safe_float(fib.get("depth")) < min_depth):
        stats["v10_red_fib"] = int(stats.get("v10_red_fib", 0)) + 1
        logger.info("V10.6 %s %s → fib derinlik %s < %s (SIĞ) red",
                    symbol, side, (fib or {}).get("depth"), min_depth)
        return None

    # --- V10.6 KURAL 5a: FOMO %4 üzerinde → skor cezası + uyarı ---
    fomo_mv = safe_float(gate.get("fomo"))
    fomo_uyari = abs(fomo_mv) > V106_FOMO_WARN_PCT
    if fomo_uyari:
        score = round(score - V106_FOMO_PENALTY, 1)
        parts["fomo_cezasi"] = -V106_FOMO_PENALTY

    # --- V10.6 KURAL 5c: OI değişimi çok düşükse skor cezası ---
    oi_val = safe_float(ext["oi_change_pct"])
    oi_dusuk = abs(oi_val) < V106_OI_MIN_CHANGE_PCT
    if oi_dusuk:
        score = round(score - V106_OI_LOW_PENALTY, 1)
        parts["oi_dusuk_cezasi"] = -V106_OI_LOW_PENALTY

    if score > safe_float(stats.get("v10_best_score", 0)):
        stats["v10_best_score"] = round(score, 1)

    # --- V10.6 KURAL 5b: SHORT'ta orderbook imbalance en az -0.15 ---
    imb = safe_float(ob.get("imbalance"))
    if side == "SHORT" and imb > V106_SHORT_MIN_OB_IMB:
        stats["v10_red_ob_imb"] = int(stats.get("v10_red_ob_imb", 0)) + 1
        logger.info("V10.6 %s SHORT → OB imbalance %.3f > %.3f red", symbol, imb, V106_SHORT_MIN_OB_IMB)
        return None

    if (side == "LONG" and r > V10_RSI_LONG_MAX) or (side == "SHORT" and r < V10_RSI_SHORT_MIN):
        stats["v10_red_rsi"] = int(stats.get("v10_red_rsi", 0)) + 1
        return None
    # --- V10.6 KURAL 3: minimum skor eşiği yok (V10_MIN_QUALITY=0 → kapalı) ---
    if V10_MIN_QUALITY > 0 and score < V10_MIN_QUALITY:
        stats["v10_red_kalite"] = int(stats.get("v10_red_kalite", 0)) + 1
        return None
    # --- V10.7: GİRİŞ FİYATI CANLI + BAYATLIK KAPISI ---
    entry_ref = closes(k)[-1]                       # yapı mumunun kapanışı (referans)
    entry, giris_kaynak = v107_canli_giris(k1h, ob, entry_ref)
    kayma = (abs(entry - entry_ref) / entry_ref * 100.0) if entry_ref > 0 else 0.0
    if V107_MAX_GIRIS_KAYMA > 0 and kayma > V107_MAX_GIRIS_KAYMA:
        stats["v107_red_kayma"] = int(stats.get("v107_red_kayma", 0)) + 1
        logger.info("V10.7 %s %s → kurulum bayat: mum kapanışı %.8f, canlı %.8f (%%%.2f kayma) red",
                    symbol, side, entry_ref, entry, kayma)
        return None
    a = atr(k, V10_ATR_PERIOD)[-1]; tgt = v10_targets(side, entry, a, fib)
    if V107_TP_RR_UYARI > 0 and safe_float(tgt.get("tp2_rr")) > V107_TP_RR_UYARI:
        stats["v107_ulasilamaz_tp"] = int(stats.get("v107_ulasilamaz_tp", 0)) + 1
    return {"symbol":symbol,"direction":side,"entry":entry,"strategy":"V10_SMC",
            "entry_ref":entry_ref,"entry_kaynak":giris_kaynak,"entry_kayma_pct":round(kayma,3),
            "event":gate["ms"]["event"],"structure":gate["why"],
            "range_break":bool(gate["ms"].get("range_break")),
            "trend_1h":gate["ms"]["trend"],"trend_4h":gate["trend4"],
            "fomo_move_pct":gate["fomo"],"pullback":gate["pullback"],
            "score":score,"score_parts":parts,"bayrak":bayrak,"rsi":r,"atr":round(a,8),
            "candle_ts":str(k[-1][0]),"oi_change_pct":ext["oi_change_pct"],
            "oi_yorum":ext.get("oi_yorum",""),"sweep_tip":ext.get("sweep_tip",""),
            "coin_1h_ema":gate.get("coin_1h_ema","-"),
            "funding":funding,"ob_imbalance":ob.get("imbalance",0),
            "btc_4h":btc_4h,"btc_1h":btc_1h,
            "trend_uyum":True,"fomo_uyari":fomo_uyari,"oi_dusuk":oi_dusuk,
            "min_quality":V10_MIN_QUALITY,
            "fib_depth":(fib or {}).get("depth"),"fib_zone":(fib or {}).get("zone"),
            "fib_bonus":(fib or {}).get("bonus",0),**tgt}


def _v10_fmt(x):
    x = safe_float(x)
    if x == 0: return "0"
    if x >= 100: return f"{x:.2f}"
    if x >= 1: return f"{x:.4f}"
    return f"{x:.6f}"


def build_v10_message(sig):
    # V10.7: ✅ artık gerçek tespite bakıyor. V10.6'da 'puan > 0' testi kullanılıyordu
    # ama CVD/VP/OB'nin taban puanı sıfırdan büyük olduğu için bu üçü her sinyalde
    # ✅ görünüyordu — yani 6 göstergenin 4'ü sabitti.
    b = sig.get("bayrak") or {}
    p = sig["score_parts"]
    tag = lambda key, lbl: f"{lbl}{'✅' if b.get(key, p.get(key,0) > 0) else '▫️'}"
    # V10.8: sweep ✅ ise hangi yoldan tespit edildiğini de göster (yapısal / pencere)
    _swt = str(sig.get("sweep_tip") or "")
    _sw_lbl = f"Sweep({_swt})" if (b.get("sweep") and _swt) else "Sweep"
    conf = " ".join([tag("order_block","OB"), tag("fvg","FVG"), tag("volume_profile","VP"),
                     tag("cvd","CVD"), tag("sweep", _sw_lbl), tag("orderbook","OBflow")])
    fund = safe_float(sig.get("funding"))
    fib_line = ""
    if sig.get("fib_zone"):
        fib_line = (f"Fib: derinlik %{round(safe_float(sig.get('fib_depth'))*100)} → "
                f"{sig['fib_zone']} ({safe_float(sig.get('fib_bonus')):+.0f} puan)\n")
    # V10.6: en üst satır — trend uyumu
    trend_line = (V106_TREND_OK_LINE if sig.get("trend_uyum", True) else V106_TREND_BLOCK_LINE) + "\n"
    fomo_mark = " ⚠️ FOMO" if sig.get("fomo_uyari") else ""
    oi_mark = " ⚠️ düşük OI" if sig.get("oi_dusuk") else ""
    # V10.7: stop gürültü bandının içindeyse görünür uyarı (1 ATR altı = mum gürültüsü)
    _satr = safe_float(sig.get("stop_atr"))
    stop_uyari = " ⚠️ GÜRÜLTÜ İÇİNDE" if (0 < _satr < 1.0) else ""
    _tp2rr = safe_float(sig.get("tp2_rr"))
    tp_uyari = " ⚠️ TP2/TP3 pratikte ulaşılamaz" if (V107_TP_RR_UYARI > 0 and _tp2rr > V107_TP_RR_UYARI) else ""
    _kay = safe_float(sig.get("entry_kayma_pct"))
    kayma_mark = f" (mum kapanışından %{_kay:+.2f})" if abs(_kay) >= 0.05 else ""
    return (f"{trend_line}"
            f"🎯 {VERSION_NAME}\n🆕 V10.9 SMC | {sig['direction']} | {sig['symbol']}\n"
            f"Yapı: {sig['structure']} | 1H:{sig['trend_1h']} 4H:{sig['trend_4h']}\n"
            f"BTC: 1H:{sig.get('btc_1h','-')} 4H:{sig.get('btc_4h','-')}"
            + (f" | Coin 1H EMA: {sig.get('coin_1h_ema','-')}" if sig.get('coin_1h_ema') else "") + "\n"
            f"Skor: {sig['score']}/100  RSI:{sig['rsi']}\nConfluence: {conf}\n{fib_line}"
            f"Giriş: {_v10_fmt(sig['entry'])} [{sig.get('entry_kaynak','-')}]{kayma_mark}\n"
            f"Stop: {_v10_fmt(sig['stop'])} (%{sig['stop_pct']} = {sig.get('stop_atr','?')}×ATR){stop_uyari}\n"
            f"TP1 {_v10_fmt(sig['tp1'])} ({sig.get('tp1_rr', V10_TP1_RR)}R %50) | TP2 {_v10_fmt(sig['tp2'])} ({sig.get('tp2_rr', V10_TP2_RR)}R %30) | TP3 {_v10_fmt(sig['tp3'])} ({sig.get('tp3_rr', V10_TP3_RR)}R %20) [{sig.get('tp_kaynak','ATR')}]{tp_uyari}\n"
            f"Pullback: {sig['pullback']} | FOMO:%{sig['fomo_move_pct']}{fomo_mark}\n"
            f"OI%{round(safe_float(sig.get('oi_change_pct')),2)}{oi_mark} ({sig.get('oi_yorum','-')}) Fund:{round(fund*100,4)}% OBimb:{round(safe_float(sig.get('ob_imbalance')),2)}\n"
            f"⚠️ PAPER — risk %{V10_RISK_PCT}/işlem")


def build_v10_close_message(pos, R, outcome, exit_price):
    if outcome == "STOP":
        head = "❌ STOP GELDİ"
    elif outcome == "TP3":
        head = "✅ TP3 GELDİ — tam hedef"
    elif outcome == "BE":
        head = "⚖️ BREAKEVEN — TP1 sonrası girişe döndü"
    else:
        head = f"🏁 {outcome}"
    return (
        f"🆕 V10.7 SMC — POZİSYON KAPANDI\n"
        f"{head}\n"
        f"Coin: {pos['symbol']}\n"
        f"Yön: {pos['side']}\n"
        f"Giriş: {_v10_fmt(pos['entry'])}\n"
        f"Çıkış: {_v10_fmt(exit_price)}\n"
        f"Sonuç: {R:+.2f}R (skor {pos['score']})\n"
        f"Saat: {tr_str()}"
    )

def v10_score_band(s):
    return "90-100" if s >= 90 else "80-90" if s >= 80 else "70-80" if s >= 70 else "60-70"


def _v10_mem():
    return memory.setdefault("v10_paper", {"open": [], "closed": [], "buckets": {}})


def v107_kova_adi(sig_veya_pos):
    """V10.7: RANGE kırılımları kendi kovasında ölçülsün.
    V10.6'da RANGE kırılımı ile gerçek trend devamı aynı 'BOS' kovasına
    düşüyordu; ikisinin EV'si ayrıştırılamıyordu."""
    ev = sig_veya_pos.get("event")
    rb = "-RANGE" if sig_veya_pos.get("range_break") else ""
    return f'{ev}{rb}|{v10_score_band(sig_veya_pos.get("score", 0))}'


def v107_pos_uid(pos):
    """Pozisyona kalıcı kimlik. Liste indeksine güvenmek yerine kimlikle silme
    yapılır — böylece await sırasında eklenen yeni pozisyonlar kaybolmaz."""
    uid = pos.get("uid")
    if not uid:
        uid = f"{pos.get('symbol','?')}|{pos.get('side','?')}|{safe_float(pos.get('open_ts',0)):.3f}|{uuid.uuid4().hex[:6]}"
        pos["uid"] = uid
    return uid


def v10_open_paper(sig):
    mp = _v10_mem()
    poz = {
        "uid": f"{sig['symbol']}|{sig['direction']}|{time.time():.3f}|{uuid.uuid4().hex[:6]}",
        "symbol":sig["symbol"],"side":sig["direction"],"entry":sig["entry"],
        "orig_stop":sig["stop"],"stop":sig["stop"],
        "tp1":sig["tp1"],"tp2":sig["tp2"],"tp3":sig["tp3"],
        "tp1_rr":safe_float(sig.get("tp1_rr", V10_TP1_RR)),
        "tp2_rr":safe_float(sig.get("tp2_rr", V10_TP2_RR)),
        "tp3_rr":safe_float(sig.get("tp3_rr", V10_TP3_RR)),
        "hit1":False,"hit2":False,"hit3":False,"realized":0.0,
        "score":sig["score"],"event":sig["event"],
        "range_break":bool(sig.get("range_break")),
        "entry_kaynak":sig.get("entry_kaynak","-"),
        "entry_kayma_pct":sig.get("entry_kayma_pct",0),
        "stop_atr":sig.get("stop_atr",0),
        "min_quality":safe_float(sig.get("min_quality", V10_MIN_QUALITY)),
        "bucket":v107_kova_adi(sig),
        "open_ts":time.time(),"scan_ts":0.0,"candle_ts":sig["candle_ts"]}
    mp["open"].append(poz)
    return poz


async def v107_takip_barlari(pos):
    """V10.7: takip artık 1m mumlarla ve WICK'lerle yapılır.
    V10.6: sadece son kapanış fiyatına bakıyordu, üstelik >=60 sn'de bir —
    iki poll arasındaki hareket tamamen görünmezdi ve defter tekrar üretilemezdi.
    Ayrıca sadece GİRİŞTEN SONRAKİ barlar işlenir; girişten önceki fitil
    pozisyonu yanlışlıkla stop ettiremez."""
    sym = pos["symbol"]
    open_ms = safe_float(pos.get("open_ts", 0)) * 1000.0
    scan_ms = safe_float(pos.get("scan_ts", 0))
    baslangic = max(open_ms, scan_ms)
    k = await get_klines(sym, V107_TAKIP_TF, V107_TAKIP_LIMIT, ttl=V107_TAKIP_CACHE_SEC)
    if not k:
        return [], "veri yok"
    ilk_ms = safe_float(k[0][0])
    if baslangic > 0 and ilk_ms > baslangic + 120000:
        eksik = int((ilk_ms - baslangic) / 60000)
        stats["v107_takip_bosluk"] = int(stats.get("v107_takip_bosluk", 0)) + 1
        logger.warning("V10.7 takip boşluğu %s: ~%d bar penceresi dışında kaldı", sym, eksik)
    barlar = [r for r in k if safe_float(r[0]) >= baslangic]
    if barlar:
        pos["scan_ts"] = safe_float(barlar[-1][0])
        return barlar, V107_TAKIP_TF
    son = safe_float(k[-1][4])
    return [[safe_float(k[-1][0]), son, son, son, son, 0]], "son fiyat"


def v107_check_paper_bar(pos, hi, lo):
    """Tek bir mumun yüksek/düşük değerleriyle pozisyonu ilerletir.
    Aynı mumda hem stop hem TP1 varsa sıra bilinemez -> TEMKİNLİ: stop sayılır."""
    side = pos["side"]; e = safe_float(pos["entry"]); w = {"tp1":0.5,"tp2":0.3,"tp3":0.2}
    tp1r = safe_float(pos.get("tp1_rr", V10_TP1_RR))
    tp2r = safe_float(pos.get("tp2_rr", V10_TP2_RR))
    tp3r = safe_float(pos.get("tp3_rr", V10_TP3_RR))
    if side == "LONG":
        stop_lv = safe_float(pos["orig_stop"]) if not pos["hit1"] else e
        stop_vuruldu = lo <= stop_lv
        tp1_vuruldu = (not pos["hit1"]) and hi >= safe_float(pos["tp1"])
        if stop_vuruldu and tp1_vuruldu:
            stats["v107_belirsiz_bar"] = int(stats.get("v107_belirsiz_bar", 0)) + 1
            return -1.0, "STOP"
        if stop_vuruldu:
            return (-1.0, "STOP") if not pos["hit1"] else (pos["realized"], "BE")
        if tp1_vuruldu:
            pos["hit1"] = True; pos["realized"] += w["tp1"]*tp1r; pos["stop"] = e
            if lo <= e:
                return pos["realized"], "BE"
        if pos["hit1"] and not pos["hit2"] and hi >= safe_float(pos["tp2"]):
            pos["hit2"] = True; pos["realized"] += w["tp2"]*tp2r
        if pos["hit2"] and not pos["hit3"] and hi >= safe_float(pos["tp3"]):
            pos["hit3"] = True; pos["realized"] += w["tp3"]*tp3r
            return pos["realized"], "TP3"
    else:
        stop_lv = safe_float(pos["orig_stop"]) if not pos["hit1"] else e
        stop_vuruldu = hi >= stop_lv
        tp1_vuruldu = (not pos["hit1"]) and lo <= safe_float(pos["tp1"])
        if stop_vuruldu and tp1_vuruldu:
            stats["v107_belirsiz_bar"] = int(stats.get("v107_belirsiz_bar", 0)) + 1
            return -1.0, "STOP"
        if stop_vuruldu:
            return (-1.0, "STOP") if not pos["hit1"] else (pos["realized"], "BE")
        if tp1_vuruldu:
            pos["hit1"] = True; pos["realized"] += w["tp1"]*tp1r; pos["stop"] = e
            if hi >= e:
                return pos["realized"], "BE"
        if pos["hit1"] and not pos["hit2"] and lo <= safe_float(pos["tp2"]):
            pos["hit2"] = True; pos["realized"] += w["tp2"]*tp2r
        if pos["hit2"] and not pos["hit3"] and lo <= safe_float(pos["tp3"]):
            pos["hit3"] = True; pos["realized"] += w["tp3"]*tp3r
            return pos["realized"], "TP3"
    return None, None


def v107_check_paper_barlar(pos, barlar):
    for r in barlar:
        R, oc = v107_check_paper_bar(pos, safe_float(r[2]), safe_float(r[3]))
        if oc:
            return R, oc
    return None, None


def v10_check_paper(pos, price):
    """[V10.6 ARTIĞI] Tek fiyatla kontrol — artık kullanılmıyor.
    Yerine v107_check_paper_barlar (1m + wick) kullanılır. Geriye dönük
    uyumluluk için bırakıldı."""
    side = pos["side"]; e = pos["entry"]; w = {"tp1":0.5,"tp2":0.3,"tp3":0.2}
    if side == "LONG":
        if not pos["hit1"] and price <= pos["orig_stop"]: return -1.0, "STOP"
        if pos["hit1"] and price <= e: return pos["realized"], "BE"
        if not pos["hit1"] and price >= pos["tp1"]:
            pos["hit1"]=True; pos["realized"]+=w["tp1"]*pos["tp1_rr"]; pos["stop"]=e
        if pos["hit1"] and not pos["hit2"] and price >= pos["tp2"]:
            pos["hit2"]=True; pos["realized"]+=w["tp2"]*pos["tp2_rr"]
        if pos["hit2"] and not pos["hit3"] and price >= pos["tp3"]:
            pos["hit3"]=True; pos["realized"]+=w["tp3"]*pos["tp3_rr"]; return pos["realized"], "TP3"
    else:
        if not pos["hit1"] and price >= pos["orig_stop"]: return -1.0, "STOP"
        if pos["hit1"] and price >= e: return pos["realized"], "BE"
        if not pos["hit1"] and price <= pos["tp1"]:
            pos["hit1"]=True; pos["realized"]+=w["tp1"]*pos["tp1_rr"]; pos["stop"]=e
        if pos["hit1"] and not pos["hit2"] and price <= pos["tp2"]:
            pos["hit2"]=True; pos["realized"]+=w["tp2"]*pos["tp2_rr"]
        if pos["hit2"] and not pos["hit3"] and price <= pos["tp3"]:
            pos["hit3"]=True; pos["realized"]+=w["tp3"]*pos["tp3_rr"]; return pos["realized"], "TP3"
    return None, None


def v10_record_closed(pos, R, outcome):
    mp = _v10_mem()
    mp["closed"].append({"symbol":pos["symbol"],"side":pos["side"],"R":round(R,3),
        "outcome":outcome,
        "hit1":bool(pos.get("hit1")),"hit2":bool(pos.get("hit2")),"hit3":bool(pos.get("hit3")),
        "score":pos["score"],"event":pos["event"],
        "range_break":bool(pos.get("range_break")),
        "entry_kaynak":pos.get("entry_kaynak","-"),
        "stop_atr":pos.get("stop_atr",0),
        "min_quality":pos.get("min_quality",0),
        "tutma_dk":round((time.time()-safe_float(pos.get("open_ts",0)))/60.0,1),
        "bucket":pos.get("bucket") or v107_kova_adi(pos),"close_ts":time.time()})
    b = mp["buckets"].setdefault(pos["bucket"], {"n":0,"R":0.0,"win":0})
    b["n"] += 1; b["R"] = round(b["R"]+R, 3)
    if R > 0: b["win"] += 1


def v10_learn_report():
    mp = _v10_mem(); out = []
    for bk, b in sorted(mp["buckets"].items(), key=lambda x: x[1]["R"], reverse=True):
        n = b["n"]; out.append((bk, n, round(b["win"]/n*100,1) if n else 0, round(b["R"]/n,3) if n else 0))
    return out


def v10_learn_adjust():
    global V10_MIN_QUALITY
    mp = _v10_mem()
    if not V10_LEARN_AUTO_ADJUST or len(mp["closed"]) < V10_LEARN_MIN_TRADES:
        return None
    worst = None
    for bk, b in mp["buckets"].items():
        if b["n"] >= 10:
            ev = b["R"]/b["n"]
            if ev < -0.1 and (worst is None or ev < worst[1]): worst = (bk, ev)
    if worst and V10_MIN_QUALITY < 85:
        V10_MIN_QUALITY += 2
        # V10.7: eşik değişimi kalıcı olsun — yoksa restart'ta env varsayılanına
        # dönerken defter devam ediyor, tek örneklem iki farklı politikaya ait oluyordu.
        memory["v10_min_quality"] = V10_MIN_QUALITY
        logger.info("V10 ADAPTİF: %s EV=%.2f → min skor %d", worst[0], worst[1], int(V10_MIN_QUALITY))
        return f"{worst[0]} kötü (EV {worst[1]:.2f}) → min skor {int(V10_MIN_QUALITY)}"
    return None


def v10_cooldown_ok(symbol):
    return time.time() - v10_last_alert.get(symbol, 0) >= V10_ALERT_COOLDOWN_MIN*60


async def maybe_send_v10_signal(sig):
    if not sig:
        return
    symbol = sig["symbol"]; side = sig["direction"]
    ckey = f"{symbol}:{side}"
    if v10_sent_candle.get(ckey) == sig["candle_ts"]:
        return
    if not v10_cooldown_ok(symbol):
        return

    mp = _v10_mem()

    # --- V10.7 (1) HAYALET SİNYAL: defter doluyken V10.6 sinyali Telegram'a
    # gönderiyor ama TAKİP ETMİYORDU. Artık dolu defterde sinyal hiç basılmaz.
    if len(mp["open"]) >= V10_MAX_OPEN:
        stats["v107_red_defter_dolu"] = int(stats.get("v107_red_defter_dolu", 0)) + 1
        logger.info("V10.7 %s %s → defter dolu (%d/%d), sinyal basılmadı",
                    symbol, side, len(mp["open"]), V10_MAX_OPEN)
        return

    # --- V10.7 (2) ÖRNEKLEM BAĞIMSIZLIĞI: aynı coin'de açık pozisyon varken
    # tekrar girilmez. V10.6'da TRUTH x3 / CC x3 aynı fikri 3 kez deftere yazıyordu.
    if V107_ACIKKEN_ENGELLE and any(p.get("symbol") == symbol for p in mp["open"]):
        stats["v107_red_acik_poz"] = int(stats.get("v107_red_acik_poz", 0)) + 1
        logger.info("V10.7 %s %s → bu coin'de zaten açık pozisyon var", symbol, side)
        return

    # --- V10.7 (3) STOP sonrası bekleme (varsayılan kapalı) ---
    if V107_STOP_BEKLEME_SAAT > 0 and time.time() < _v107_stop_kilit.get(symbol, 0.0):
        stats["v107_red_stop_bekleme"] = int(stats.get("v107_red_stop_bekleme", 0)) + 1
        return

    ok = await send_rich_signal(
        build_v10_message(sig), symbol, side,
        entry=safe_float(sig.get("entry")), stop=safe_float(sig.get("stop")),
        tps={"TP1": sig.get("tp1"), "TP2": sig.get("tp2"), "TP3": sig.get("tp3")},
        meta={"score": sig.get("score"), "rsi": sig.get("rsi"),
              "funding": sig.get("funding"), "oi": sig.get("oi_change_pct")},
    )
    if ok:
        v10_last_alert[symbol] = time.time()
        v10_sent_candle[ckey] = sig["candle_ts"]
        # KOŞULSUZ: gönderilen her sinyal deftere işlenir. Kapasite kontrolü
        # gönderimden ÖNCE yapıldı; await sırasında defter dolduysa taşmayı
        # kabul edip logluyoruz — takipsiz sinyal bırakmak çok daha kötü.
        mp = _v10_mem()
        if len(mp["open"]) >= V10_MAX_OPEN:
            logger.warning("V10.7 defter kapasitesi aşıldı (%d/%d) — sinyal yine de takibe alındı",
                           len(mp["open"]) + 1, V10_MAX_OPEN)
        v10_open_paper(sig)
        stats["v10_signals"] = int(stats.get("v10_signals", 0)) + 1
        stats["last_signal"] = f"V10 {side} {symbol} skor {sig['score']}"
        logger.info("V10 SİNYAL GÖNDERİLDİ %s %s skor=%s", side, symbol, sig["score"])
    else:
        logger.warning("V10 TELEGRAM GÖNDERİLEMEDİ %s %s", side, symbol)


async def v10_scan_loop() -> None:
    if not V10_ENGINE_ENABLED:
        return
    await asyncio.sleep(4)
    while True:
        try:
            if not COINS:
                await refresh_coin_pool(force=True)
            batch_size = 8
            coins = list(COINS)[:MA_COIN_LIMIT]
            cfail = 0; ctot = 0
            for i in range(0, len(coins), batch_size):
                batch = coins[i:i+batch_size]
                tasks = [analyze_v10_symbol(sym) for sym in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    ctot += 1
                    if isinstance(res, Exception):
                        cfail += 1
                        logger.warning("V10 batch hata: %s", res)
                        continue
                    stats["v10_analyzed"] = int(stats.get("v10_analyzed", 0)) + 1
                    if res:
                        stats["v10_candidates"] = int(stats.get("v10_candidates", 0)) + 1
                        await maybe_send_v10_signal(res)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.exception("v10_scan_loop hata: %s", e)
        await asyncio.sleep(max(5.0, MA_SCAN_INTERVAL_SEC))


async def v10_paper_loop() -> None:
    if not V10_ENGINE_ENABLED:
        return
    await asyncio.sleep(12)
    while True:
        try:
            mp = _v10_mem()
            kapananlar = set()
            # V10.7 HAYALET POZİSYON DÜZELTMESİ:
            # V10.6 `for pos in mp["open"]` ile await'ler arasında dönüyor, sonra
            # `mp["open"] = still` ile listeyi KOMPLE yeniden yazıyordu. Tarama
            # döngüsü o await'ler sırasında yeni pozisyon eklerse sessizce siliniyordu.
            # Artık kopya üzerinde dönülüp, silme kimliğe göre yapılıyor.
            for pos in list(mp["open"]):
                uid = v107_pos_uid(pos)
                barlar, kaynak = await v107_takip_barlari(pos)
                if not barlar:
                    continue
                was1, was2 = pos["hit1"], pos["hit2"]
                R, oc = v107_check_paper_barlar(pos, barlar)
                if not oc:
                    if pos["hit1"] and not was1:
                        await safe_send_telegram(
                            f"✅ V10.7 TP1 GELDİ — {pos['side']} {pos['symbol']}\n"
                            f"Fiyat: {_v10_fmt(pos['tp1'])} | %50 realize\n"
                            f"Stop girişe çekildi (artık zararsız) | +{round(pos['realized'],2)}R kilitli | skor {pos['score']}")
                    if pos["hit2"] and not was2:
                        await safe_send_telegram(
                            f"✅ V10.7 TP2 GELDİ — {pos['side']} {pos['symbol']}\n"
                            f"Fiyat: {_v10_fmt(pos['tp2'])} | %30 realize | +{round(pos['realized'],2)}R kilitli | skor {pos['score']}")
                    continue
                v10_record_closed(pos, R, oc)
                if oc == "STOP" and V107_STOP_BEKLEME_SAAT > 0:
                    _v107_stop_kilit[pos["symbol"]] = time.time() + V107_STOP_BEKLEME_SAAT * 3600.0
                exit_price = pos["orig_stop"] if oc == "STOP" else (pos["tp3"] if oc == "TP3" else pos["entry"])
                await safe_send_telegram(build_v10_close_message(pos, R, oc, exit_price))
                logger.info("V10.7 KAPANDI %s %s %s R=%.2f (takip: %s)",
                            pos["side"], pos["symbol"], oc, R, kaynak)
                kapananlar.add(uid)
            if kapananlar:
                mp["open"] = [p for p in mp["open"] if v107_pos_uid(p) not in kapananlar]
            adj = v10_learn_adjust()
            if adj:
                await safe_send_telegram(f"🧠 V10.7 öğrenen: {adj}")
        except Exception as e:
            logger.exception("v10_paper_loop hata: %s", e)
        await asyncio.sleep(max(V107_TAKIP_ARALIK_SEC, 20))


async def cmd_v10(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mp = _v10_mem()
    cl = mp["closed"]; n = len(cl)
    ev = (sum(x["R"] for x in cl)/n) if n else 0
    wins = sum(1 for x in cl if x["R"] > 0)
    bt = await v106_btc_trend()
    if bt.get("allow") == "LONG":
        btc_line = "SADECE LONG ✅"
    elif bt.get("allow") == "SHORT":
        btc_line = "SADECE SHORT ✅"
    else:
        btc_line = "SİNYAL YOK ❌ (1H-4H uyuşmuyor)"
    lines = [
        f"🆕 V10.7 SMC durumu",
        f"Motor: {'AÇIK' if V10_ENGINE_ENABLED else 'KAPALI'} | Min skor: {'eşik yok' if V10_MIN_QUALITY <= 0 else int(V10_MIN_QUALITY)}",
        f"BTC trend (EMA{V106_BTC_EMA_FAST}/{V106_BTC_EMA_SLOW}): 1H:{bt.get('dir_1h','-')} 4H:{bt.get('dir_4h','-')} → {btc_line}",
        f"Fib kapısı: LONG ≥{V106_FIB_MIN_DEPTH_LONG} | SHORT ≥{V106_FIB_MIN_DEPTH_SHORT}",
        f"Ek filtre: FOMO>%{V106_FOMO_WARN_PCT:g} → {-V106_FOMO_PENALTY:g} puan | SHORT OBimb ≤{V106_SHORT_MIN_OB_IMB:g} | OI<%{V106_OI_MIN_CHANGE_PCT:g} → {-V106_OI_LOW_PENALTY:g} puan",
        f"Analiz: {stats.get('v10_analyzed',0)} | Aday: {stats.get('v10_candidates',0)} | Sinyal: {stats.get('v10_signals',0)}",
        f"Açık: {len(mp['open'])} | Kapalı: {n} | Win%{round(wins/n*100,1) if n else 0} | EV {round(ev,3)}R",
        "— V10.7 sayaçları —",
        f"Bayat kurulum red: {stats.get('v107_red_kayma',0)} | Açık poz. red: {stats.get('v107_red_acik_poz',0)} | Defter dolu red: {stats.get('v107_red_defter_dolu',0)}",
        f"Elenen mikro pivot: {stats.get('v107_pivot_elendi',0)} | RANGE red: {stats.get('v107_red_range',0)} | Alakasız haber: {stats.get('v107_haber_alakasiz',0)}",
        (f"Sweep dedektörü: {'ONARILMIŞ' if V108_SWEEP_ONARIM else 'eski (V10.7)'}"
         f" | pencere {V108_SWEEP_PENCERE} mum | CHoCH kapısı: "
         f"{'AÇIK' if V108_CHOCH_SWEEP_ZORUNLU else 'kapalı'}"
         + (f" (kesilen {stats.get('v108_red_choch_sweep',0)})" if V108_CHOCH_SWEEP_ZORUNLU else "")),
        (f"CHoCH coin 1H EMA{V109_COIN_EMA_FAST}/{V109_COIN_EMA_SLOW} uyumu: "
         f"{'AÇIK' if V109_COIN_1H_UYUM else 'kapalı'}"
         + (f" (kesilen {stats.get('v109_red_coin_1h',0)})" if V109_COIN_1H_UYUM else "")
         + " — BOS kurulumları etkilenmez"),
        (f"Canlı sweep isabeti: {int(stats.get('v108_sweep_var',0))}/{int(stats.get('v108_sweep_tot',0))}"
         f" (%{(stats.get('v108_sweep_var',0)/max(1,stats.get('v108_sweep_tot',0))*100):.1f})"
         f" — yapısal {int(stats.get('v108_sweep_yapisal',0))}, pencere {int(stats.get('v108_sweep_pencere',0))}"),
        f"Belirsiz bar (stop/TP aynı mumda): {stats.get('v107_belirsiz_bar',0)} | Takip boşluğu: {stats.get('v107_takip_bosluk',0)}",
        f"OKX 429: {stats.get('okx_429',0)} | Ölen task: {stats.get('task_oldu',0)} | API hata: {stats.get('api_fail',0)}",
        f"4H filtre: {V10_USE_4H_FILTER} | Orderbook: {V10_USE_ORDERBOOK} | Öğrenen: {V10_LEARN_AUTO_ADJUST}",
        f"RSI filtre: LONG max {int(V10_RSI_LONG_MAX)} | SHORT min {int(V10_RSI_SHORT_MIN)}",
    ]
    rep = v10_learn_report()
    if rep:
        lines.append("— Setup EV —")
        for bk, nn, wr, e in rep[:8]:
            lines.append(f"{bk}: n={nn} WR%{wr} EV={e}R")
    if mp["open"]:
        lines.append("— Açık —")
        for p in mp["open"][:10]:
            tps = "".join("✅" if p[f"hit{i}"] else "▫️" for i in (1, 2, 3))
            yas = round((time.time() - safe_float(p.get("open_ts", 0))) / 60.0)
            lines.append(f"{p['side']} {p['symbol']} {tps} R:{round(p['realized'],2)} skor {p['score']} ({yas}dk)")
    await update.message.reply_text("\n".join(lines))


# ============================================================================ #
#  V10 SMC MOTORU graft sonu
# ============================================================================ #


def build_app():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("test", cmd_test))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("scan", cmd_scan))
    application.add_handler(CommandHandler("coin", cmd_coin))
    application.add_handler(CommandHandler("hot", cmd_hot))
    application.add_handler(CommandHandler("ma", cmd_ma))
    application.add_handler(CommandHandler("hibrit", cmd_hibrit))
    application.add_handler(CommandHandler("risk", cmd_risk))
    application.add_handler(CommandHandler("backtest", cmd_backtest))
    application.add_handler(CommandHandler("ma_status", cmd_ma_status))
    application.add_handler(CommandHandler("whale", cmd_whale))
    application.add_handler(CommandHandler("whaletest", cmd_whaletest))
    application.add_handler(CommandHandler("paper", cmd_paper))
    application.add_handler(CommandHandler("version", cmd_version))
    application.add_handler(CommandHandler("funding", cmd_funding))
    application.add_handler(CommandHandler("v10", cmd_v10))
    return application

def main() -> None:
    validate_config()
    load_memory()
    # V10.7: öğrenen motorun eşiğini restart sonrası geri yükle
    global V10_MIN_QUALITY
    _kayitli = safe_float(memory.get("v10_min_quality", 0))
    if V10_LEARN_AUTO_ADJUST and _kayitli > V10_MIN_QUALITY:
        V10_MIN_QUALITY = _kayitli
        logger.info("V10.7: kayıtlı min skor eşiği geri yüklendi -> %s", V10_MIN_QUALITY)
    if PAPER_RESET_ON_DEPLOY:
        memory["paper_trades"] = []
        logger.info("PAPER_RESET_ON_DEPLOY=true → paper defteri sıfırlandı")
    # V10.7: ölçüm rejimi değişti (giriş fiyatı canlı, takip wick'li, kovalar
    # yeniden adlandırıldı). V10.6 kapanışlarıyla V10.7 kapanışlarını aynı
    # defterde toplamak EV'yi yorumlanamaz hale getirir. Bu bayrak eski defteri
    # SİLMEZ — arşivler ve temiz sayfa açar.
    if V107_DEFTER_SIFIRLA:
        eski = memory.get("v10_paper")
        if eski and (eski.get("open") or eski.get("closed")):
            memory.setdefault("v10_paper_arsiv", []).append(
                {"surum": "V10.6", "arsiv_ts": time.time(), "defter": eski})
            logger.info("V10.7: V10.6 defteri arşivlendi (%d açık, %d kapalı) → temiz defter",
                        len(eski.get("open", [])), len(eski.get("closed", [])))
        memory["v10_paper"] = {"open": [], "closed": [], "buckets": {}}
    # RiskGuard durumunu memory'ye bağla → deploy/restart arası kalıcı
    RISK_GUARD.state = memory.setdefault("risk_guard", RISK_GUARD.state)
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