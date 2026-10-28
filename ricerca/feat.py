"""Caratteristiche causali su barre M5 chiuse per la ricerca 'accelerazione + volume'."""
import numpy as np, pandas as pd
from engine import ema


def wilder_atr(h, l, c, n=14):
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def bars(m1, tf='5min'):
    agg = {'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}
    if 'v' in m1: agg['v'] = 'sum'
    if 'spr' in m1: agg['spr'] = 'mean'
    b = m1.resample(tf, label='left', closed='left').agg(agg).dropna(subset=['o'])
    return b


def build(m1, tf='5min', tod_days=20):
    b = bars(m1, tf)
    bar = pd.Timedelta(tf)
    ny = b.index.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None)
    b['ny'] = ny; b['nym'] = ny.hour * 60 + ny.minute
    ld = b.index.tz_localize('UTC').tz_convert('Europe/London').tz_localize(None)
    b['ldm'] = ld.hour * 60 + ld.minute                         # minuto del giorno a Londra (con ora legale UE)
    b['utm'] = b.index.hour * 60 + b.index.minute               # minuto UTC (Asia: Tokyo 00:00, HK/Shanghai 01:30)
    b['tday'] = (ny + pd.Timedelta(hours=6)).normalize()        # giorno di trading che parte alle 18:00 NY
    b['dow'] = b.tday.dt.dayofweek
    b['atr'] = wilder_atr(b.h, b.l, b.c, 14)
    b['atr_slow'] = wilder_atr(b.h, b.l, b.c, 288)
    a = b.atr
    b['body'] = (b.c - b.o) / a
    b['rng'] = (b.h - b.l) / a
    b['clv'] = ((b.c - b.l) / (b.h - b.l)).fillna(0.5)
    b['ret3'] = (b.c - b.c.shift(3)) / a
    b['ret6'] = (b.c - b.c.shift(6)) / a
    b['ret12'] = (b.c - b.c.shift(12)) / a
    # range relativo allo stesso orario dei 20 giorni precedenti (proxy dell'attivita'/volume)
    rng_abs = b.h - b.l
    med = rng_abs.groupby(b.nym).transform(lambda s: s.shift(1).rolling(tod_days, min_periods=10).median())
    b['rr'] = rng_abs / med
    if 'v' in b and b.v.sum() > 0:
        vm = b.v.groupby(b.nym).transform(lambda s: s.shift(1).rolling(tod_days, min_periods=10).mean())
        b['rv'] = b.v / vm
        b['rv20'] = b.v / b.v.shift(1).rolling(20).mean()
    # massimi/minimi recenti (rottura)
    b['hh12'] = b.h.shift(1).rolling(12).max(); b['ll12'] = b.l.shift(1).rolling(12).min()
    b['hh24'] = b.h.shift(1).rolling(24).max(); b['ll24'] = b.l.shift(1).rolling(24).min()
    # VWAP del giorno di trading (con volume se disponibile, altrimenti prezzo tipico medio)
    tp = (b.h + b.l + b.c) / 3
    vv = b.v.clip(lower=1e-9) if 'v' in b and b.v.sum() > 0 else pd.Series(1.0, b.index)
    b['vwap'] = (tp * vv).groupby(b.tday).cumsum() / vv.groupby(b.tday).cumsum()
    b['vwd'] = (b.c - b.vwap) / a
    # trend: EMA50 H1 (candela H1 chiusa), EMA20 M15 e pendenza
    h1 = m1.c.resample('1h', label='left', closed='left').last().dropna()
    e = ema(h1, 50); s = np.sign(h1 - e); s.index = s.index + pd.Timedelta(hours=1)
    b['tr_h1'] = s.reindex(b.index + bar, method='ffill').values
    m15 = m1.c.resample('15min', label='left', closed='left').last().dropna()
    e15 = ema(m15, 20); sl15 = np.sign(e15 - e15.shift(2)); sl15.index = sl15.index + pd.Timedelta(minutes=15)
    b['tr_m15'] = sl15.reindex(b.index + bar, method='ffill').values
    b['ema20'] = ema(b.c, 20); b['ema50'] = ema(b.c, 50)
    return b


def fwd(b, mins=(30, 60, 120)):
    """ritorno futuro in ATR (dall'apertura della barra successiva)"""
    bar_min = int(b.index.to_series().diff().mode()[0].total_seconds() // 60)
    out = {}
    nxt_o = b.o.shift(-1)
    for m in mins:
        k = m // bar_min
        out[m] = (b.c.shift(-k) - nxt_o) / b.atr
    return pd.DataFrame(out, index=b.index)
