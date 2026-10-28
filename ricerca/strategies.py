"""Strategie candidate. Ognuna restituisce un DataFrame di segnali (d, sl, tp, hold) indicizzato
sul momento in cui il segnale e' eseguibile (chiusura della barra M5)."""
import numpy as np, pandas as pd
from engine import ema, atr, rsi, adx, htf, resample


def _out(df, d, sl, tp, hold):
    s = pd.DataFrame({'d': d, 'sl': sl, 'tp': tp, 'hold': hold}, index=df.index + df.index.to_series().diff().mode()[0])
    return s[s.d != 0]


def hours(idx, a, b):
    h = idx.hour
    return (h >= a) & (h < b) if a < b else (h >= a) | (h < b)


def trend_pullback(m5, m15, rsi_n=3, rsi_lvl=25, sl_atr=1.5, tp_atr=1.5, hold=120, sess=(7, 20)):
    """Trend M15 (EMA20>EMA50 e pendenza positiva) + ritracciamento su M5 (RSI veloce ipervenduto)
    con ripresa: compra quando l'RSI rientra sopra la soglia."""
    e20 = htf(ema(m15.c, 20), m5.index); e50 = htf(ema(m15.c, 50), m5.index)
    up = (e20 > e50) & (e20 > e20.shift(3)); dn = (e20 < e50) & (e20 < e20.shift(3))
    r = rsi(m5.c, rsi_n); a = atr(m5)
    buy = up & (r.shift() < rsi_lvl) & (r >= rsi_lvl)
    sell = dn & (r.shift() > 100 - rsi_lvl) & (r <= 100 - rsi_lvl)
    ok = hours(m5.index, *sess)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def bb_fade(m5, n=20, k=2.5, rsi_lvl=25, adx_max=25, sl_atr=1.5, tp_atr=1.0, hold=90, sess=(0, 24)):
    """Mean reversion: chiusura fuori dalla banda di Bollinger con RSI estremo e mercato senza trend (ADX basso)."""
    mid = m5.c.rolling(n).mean(); sd = m5.c.rolling(n).std()
    r = rsi(m5.c, 14); a = atr(m5); x = adx(m5)
    calm = x < adx_max
    buy = calm & (m5.c < mid - k * sd) & (r < rsi_lvl)
    sell = calm & (m5.c > mid + k * sd) & (r > 100 - rsi_lvl)
    ok = hours(m5.index, *sess) if sess != (0, 24) else np.ones(len(m5), bool)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def donchian_break(m5, n=12, sl_atr=1.0, tp_atr=1.5, hold=120, sess=(7, 17), atr_min_ratio=1.0):
    """Breakout del massimo/minimo delle ultime n barre M5, solo in sessione e con volatilita' in espansione."""
    hi = m5.h.rolling(n).max().shift(); lo = m5.l.rolling(n).min().shift()
    a = atr(m5); a_slow = atr(m5, 100)
    exp_ = a > atr_min_ratio * a_slow
    buy = (m5.c > hi) & exp_; sell = (m5.c < lo) & exp_
    ok = hours(m5.index, *sess)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def ema_cross_momo(m5, m15, f=9, s=21, sl_atr=1.2, tp_atr=1.5, hold=120, sess=(7, 20), tn=50):
    """Incrocio EMA veloci su M5 nella direzione del trend M15 (EMA50)."""
    ef = ema(m5.c, f); es = ema(m5.c, s)
    t = htf(ema(m15.c, tn), m5.index)
    cu = (ef > es) & (ef.shift() <= es.shift()); cd = (ef < es) & (ef.shift() >= es.shift())
    a = atr(m5)
    ok = hours(m5.index, *sess)
    d = np.where(ok & cu & (m5.c > t), 1, np.where(ok & cd & (m5.c < t), -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def vwap_revert(m5, k=2.0, sl_atr=1.5, tp_atr=1.0, hold=90, sess=(0, 24)):
    """Distanza dal VWAP di sessione (proxy senza volume: prezzo medio tipico cumulato dal giorno UTC)."""
    tp_ = (m5.h + m5.l + m5.c) / 3
    day = m5.index.normalize()
    vw = tp_.groupby(day).cumsum() / tp_.groupby(day).cumcount().add(1)
    dev = (m5.c - vw)
    sd = dev.groupby(day).transform(lambda x: x.expanding().std())
    a = atr(m5)
    buy = (dev < -k * sd) & (m5.c > m5.o)  # candela di rifiuto
    sell = (dev > k * sd) & (m5.c < m5.o)
    ok = hours(m5.index, *sess) if sess != (0, 24) else np.ones(len(m5), bool)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def inside_break(m5, m15, sl_atr=1.0, tp_atr=1.5, hold=90, sess=(7, 20)):
    """Rottura di una inside bar M5 nella direzione del trend M15."""
    ins = (m5.h.shift() < m5.h.shift(2)) & (m5.l.shift() > m5.l.shift(2))
    t = htf(ema(m15.c, 50), m5.index)
    a = atr(m5)
    buy = ins & (m5.c > m5.h.shift()) & (m5.c > t)
    sell = ins & (m5.c < m5.l.shift()) & (m5.c < t)
    ok = hours(m5.index, *sess)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)


def range_break(m5, rng=(0, 7), win=(7, 10), sl_mode='range', sl_k=0.5, tp_k=1.0, hold=120, one_per_day=True, a_n=14):
    """Breakout del range di una sessione (es. Asia 00-07 UTC) durante la finestra successiva.
    sl/tp in multipli dell'ampiezza del range (sl_mode='range') o dell'ATR M5."""
    idx = m5.index; day = idx.normalize(); hr = idx.hour + idx.minute / 60
    inr = (hr >= rng[0]) & (hr < rng[1])
    rh = m5.h.where(inr).groupby(day).transform('max'); rl = m5.l.where(inr).groupby(day).transform('min')
    # il range e' noto solo dopo la sua chiusura
    inwin = (hr >= win[0]) & (hr < win[1])
    width = rh - rl
    a = atr(m5, a_n)
    base = width if sl_mode == 'range' else a
    up = inwin & (m5.c > rh) & (m5.c.shift() <= rh)
    dn = inwin & (m5.c < rl) & (m5.c.shift() >= rl)
    d = pd.Series(np.where(up, 1, np.where(dn, -1, 0)), idx)
    if one_per_day:
        first = d.ne(0).groupby(day).cumsum()
        d = d.where(first == 1, 0) * (d.ne(0))
    return _out(m5, d.values, sl_k * base, tp_k * base, hold)


def pdhl_sweep(m5, sl_atr=1.0, tp_atr=2.0, hold=120, sess=(7, 20)):
    """Sweep del massimo/minimo del giorno precedente e rientro: segnale di inversione."""
    idx = m5.index; day = idx.normalize()
    dly = m5.groupby(day).agg(h=('h', 'max'), l=('l', 'min'))
    pdh = pd.Series(dly.h.shift().reindex(day).values, idx); pdl = pd.Series(dly.l.shift().reindex(day).values, idx)
    a = atr(m5)
    sell = (m5.h > pdh) & (m5.c < pdh)
    buy = (m5.l < pdl) & (m5.c > pdl)
    ok = hours(idx, *sess)
    d = np.where(ok & buy, 1, np.where(ok & sell, -1, 0))
    return _out(m5, d, sl_atr * a, tp_atr * a, hold)
