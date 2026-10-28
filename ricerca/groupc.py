"""Gruppo C: altre strategie intraday dalla letteratura. Ordini a mercato o limite per engine.simulate_limit.
Le uscite basate su regole (RSI, VWAP, fine giornata) diventano un tempo massimo calcolato in modo causale:
la prima candela DOPO l'ingresso in cui la regola scatta."""
import numpy as np, pandas as pd
from engine import resample, atr, ema, rsi
from groupb import frame, mkt, _utc, M

BAR = pd.Timedelta(minutes=5)


def h1_trend(m1, idx):
    h = resample(m1, '1h'); e = ema(h.c, 50); s = np.sign(h.c - e); s.index = s.index + pd.Timedelta(hours=1)
    return s.reindex(idx, method='ffill')


def rth(b):
    return b[(b.nym >= 570) & (b.nym < 960)]


def first_after(cond, start_pos, maxpos):
    """indice della prima posizione > start_pos in cui cond e' vera (entro maxpos)"""
    w = np.flatnonzero(cond[start_pos + 1:maxpos + 1])
    return start_pos + 1 + w[0] if len(w) else maxpos


# C1 ------------------------------------------------------------- intraday momentum (Gao et al. 2018)
def last_half_hour(b, sl_atr=3.0, use_12th=False):
    r = rth(b); out = []
    for day, g in r.groupby('nyday'):
        g = g.set_index('nym')
        if not all(k in g.index for k in (595, 1555 % 1440 if False else 925)):
            continue
        prev = b[(b.nyday < day) & (b.nym == 955)]
        if len(prev) == 0 or (day - prev.nyday.iloc[-1]).days > 4:
            continue
        pc = prev.c.iloc[-1]
        f = g.c[595] / pc - 1  # rendimento dalla chiusura di ieri alle 10:00
        s = f
        if use_12th and 895 in g.index and 925 in g.index:
            s = np.sign(f) + np.sign(g.c[925] / g.c[895] - 1)
        d = int(np.sign(s))
        if d == 0:
            continue
        e = g.c[925]; a = g.atr[925]
        t = _utc(day + pd.Timedelta(minutes=930)); x = _utc(day + pd.Timedelta(minutes=955))
        out.append(mkt(t, d, e - d * sl_atr * a, e + d * 100 * a, x))
    return pd.DataFrame(out)


# C2 ------------------------------------------------------------- VWAP trend (Zarattini & Aziz)
def vwap_trend(b, m1, sl_atr=1.5, start=600, last_entry=900, max_trades=2, trend=True):
    """Dopo le 10:00 NY: long alla prima chiusura sopra il VWAP di sessione (dopo una sotto), short al contrario.
    Uscita alla chiusura opposta rispetto al VWAP o alle 15:55. Al massimo `max_trades` al giorno, a favore del trend H1."""
    r = rth(b).copy()
    tp_ = (r.h + r.l + r.c) / 3; v = r.v if 'v' in r and r.v.sum() > 0 else pd.Series(1.0, r.index)
    r['vw'] = (tp_ * v).groupby(r.nyday).cumsum() / v.groupby(r.nyday).cumsum()
    r['tr'] = h1_trend(m1, r.index + BAR).values
    out = []
    for day, g in r.groupby('nyday'):
        above = (g.c > g.vw).values; n = 0; i = 1; idx = g.index; nym = g.nym.values
        while i < len(g) and n < max_trades:
            if nym[i] >= start and nym[i] <= last_entry and above[i] != above[i - 1]:
                d = 1 if above[i] else -1
                if not trend or g.tr.iloc[i] == d:
                    j = first_after(above != above[i], i, len(g) - 1)
                    e = g.c.iloc[i]; a = g.atr.iloc[i]
                    out.append(mkt(idx[i] + BAR, d, e - d * sl_atr * a, e + d * 100 * a, idx[j] + BAR))
                    n += 1; i = j; continue
            i += 1
    return pd.DataFrame(out)


# C3 ------------------------------------------------------------- gap fade all'apertura di NY
def gap_fade(b, min_gap_atr=0.5, max_gap_atr=3.0, stop_k=1.0, exit_ny=720):
    """Gap = apertura 9:30 - chiusura 16:00 di ieri. Se il gap e' tra min e max volte l'ATR giornaliero,
    si opera per la chiusura del gap: target = chiusura di ieri, stop = stop_k x gap oltre l'apertura."""
    r = rth(b); out = []
    day_rng = r.groupby('nyday').apply(lambda g: g.h.max() - g.l.min())
    datr = day_rng.ewm(alpha=1 / 14, adjust=False).mean().shift()
    prev_close = r.groupby('nyday').c.last().shift()
    for day, g in r.groupby('nyday'):
        if 570 not in set(g.nym) or pd.isna(prev_close.get(day)) or pd.isna(datr.get(day)):
            continue
        o = g[g.nym == 570].o.iloc[0]; pc = prev_close[day]; gap = o - pc
        if not (min_gap_atr * datr[day] <= abs(gap) <= max_gap_atr * datr[day]):
            continue
        d = -int(np.sign(gap))
        t = _utc(day + pd.Timedelta(minutes=570)); x = _utc(day + pd.Timedelta(minutes=exit_ny))
        out.append(dict(act=t, exp=t + M, d=d, px=1e12 * d, sl=o - d * stop_k * abs(gap), tp=pc, tmax=x))
    return pd.DataFrame(out)


# C4 ------------------------------------------------------------- TTM squeeze (John Carter)
def ttm_squeeze(b, m1, n=20, kc=1.5, min_sq=6, sl_atr=1.5, tp_atr=3.0, hold=240, sess=(180, 900), trend=True):
    mid = b.c.rolling(n).mean(); sd = b.c.rolling(n).std(); a = atr(b, n)
    sq = (mid + 2 * sd < mid + kc * a) & (mid - 2 * sd > mid - kc * a)
    run = sq.groupby((~sq).cumsum()).cumsum()
    rel = (~sq) & (run.shift() >= min_sq)
    mom = b.c - (b.h.rolling(n).max() + b.l.rolling(n).min()) / 4 - mid / 2
    tr = h1_trend(m1, b.index + (b.index[1] - b.index[0]))
    ok = (b.nym >= sess[0]) & (b.nym < sess[1])
    d = np.where(rel & ok & (mom > 0), 1, np.where(rel & ok & (mom < 0), -1, 0))
    if trend:
        d = np.where(d == tr.values, d, 0)
    bar = b.index[1] - b.index[0]; out = []
    for i in np.flatnonzero(d):
        e = b.c.iloc[i]; aa = b.atr.iloc[i]; t = b.index[i] + bar
        out.append(mkt(t, int(d[i]), e - d[i] * sl_atr * aa, e + d[i] * tp_atr * aa, t + pd.Timedelta(minutes=hold)))
    return pd.DataFrame(out)


# C5 ------------------------------------------------------------- NR7 + ORB (Toby Crabel)
def nr7_orb(b, bars=6, tp_r=2.0, nr=7, exit_ny=955):
    """Se ieri e' stato il giorno con il range piu' stretto degli ultimi 7 (sessione 9:30-16:00), oggi si opera
    la rottura del range dei primi 30 minuti con ordine stop sul massimo/minimo (il primo che viene toccato)."""
    r = rth(b); rngd = r.groupby('nyday').apply(lambda g: g.h.max() - g.l.min())
    isnr = rngd == rngd.rolling(nr).min()
    days = list(rngd.index); out = []
    for k in range(1, len(days)):
        if not isnr.iloc[k - 1]:
            continue
        day = days[k]; g = r[r.nyday == day]
        orw = g[(g.nym >= 570) & (g.nym < 570 + 5 * bars)]
        if len(orw) < bars:
            continue
        hi, lo = orw.h.max(), orw.l.min()
        rest = g[(g.nym >= 570 + 5 * bars) & (g.nym < exit_ny)]
        up = rest.index[rest.h > hi]; dn = rest.index[rest.l < lo]
        if len(up) == 0 and len(dn) == 0:
            continue
        d = 1 if (len(dn) == 0 or (len(up) and up[0] <= dn[0])) else -1
        tb = up[0] if d > 0 else dn[0]
        px = hi if d > 0 else lo; sl = lo if d > 0 else hi
        out.append(dict(act=tb + BAR, exp=tb + 2 * BAR, d=d, px=-px if False else (1e12 if d > 0 else -1e12), sl=sl,
                        tp=px + d * tp_r * abs(px - sl), tmax=_utc(day + pd.Timedelta(minutes=exit_ny))))
    return pd.DataFrame(out)


# C6 ------------------------------------------------------------- Fair value gap (ICT) con trend
def fvg(b, m1, disp_atr=1.0, buf_atr=0.5, tp_r=2.0, valid=12, hold=120, sess=(180, 720), trend=True):
    h, l, o, c, a = b.h.values, b.l.values, b.o.values, b.c.values, b.atr.values
    bar = b.index.to_series().diff().mode()[0]
    tr = h1_trend(m1, b.index + bar).values; out = []
    for i in range(2, len(b)):
        if not (sess[0] <= b.nym.iloc[i] < sess[1]) or abs(c[i - 1] - o[i - 1]) < disp_atr * a[i - 1]:
            continue
        if l[i] > h[i - 2] and c[i - 1] > o[i - 1]:
            d, px, sl = 1, l[i], h[i - 2] - buf_atr * a[i]
        elif h[i] < l[i - 2] and c[i - 1] < o[i - 1]:
            d, px, sl = -1, h[i], l[i - 2] + buf_atr * a[i]
        else:
            continue
        if trend and tr[i] != d:
            continue
        act = b.index[i] + bar  # solo a candela chiusa
        out.append(dict(act=act, exp=act + bar * valid, d=d, px=px, sl=sl, tp=px + d * tp_r * abs(px - sl),
                        tmax=act + bar * valid + pd.Timedelta(minutes=hold)))
    return pd.DataFrame(out)


# C7 ------------------------------------------------------------- RSI(2) pullback nel trend (Connors)
def rsi2_pullback(b, m1, lvl=10, exit_lvl=70, sl_atr=2.0, hold_bars=16, sess=(180, 900)):
    r2 = rsi(b.c, 2); tr = h1_trend(m1, b.index + (b.index[1] - b.index[0])).values
    ok = ((b.nym >= sess[0]) & (b.nym < sess[1])).values
    buy = (r2 < lvl).values & (tr == 1) & ok; sell = (r2 > 100 - lvl).values & (tr == -1) & ok
    bar = b.index[1] - b.index[0]; out = []; last = -1
    for i in np.flatnonzero(buy | sell):
        if i <= last:
            continue
        d = 1 if buy[i] else -1
        cond = (r2.values > exit_lvl) if d > 0 else (r2.values < 100 - exit_lvl)
        j = first_after(cond, i, min(i + hold_bars, len(b) - 1))
        e = c = b.c.iloc[i]; a = b.atr.iloc[i]
        out.append(mkt(b.index[i] + bar, d, e - d * sl_atr * a, e + d * 100 * a, b.index[j] + bar)); last = j
    return pd.DataFrame(out)


# C8 ------------------------------------------------------------- rottura del massimo/minimo di ieri (sessione NY)
def pdhl_break(b, m1, sl_atr=1.5, tp_r=2.0, win=(570, 720), hold=180):
    r = rth(b); dly = r.groupby('nyday').agg(h=('h', 'max'), l=('l', 'min'))
    pdh = dly.h.shift(); pdl = dly.l.shift(); tr = h1_trend(m1, b.index + BAR); out = []
    for day, g in b[(b.nym >= win[0]) & (b.nym < win[1])].groupby('nyday'):
        if day not in pdh.index or pd.isna(pdh[day]):
            continue
        for d, cond in ((1, (g.c > pdh[day]) & (g.c.shift() <= pdh[day])), (-1, (g.c < pdl[day]) & (g.c.shift() >= pdl[day]))):
            w = np.flatnonzero(cond.values)
            if len(w) == 0:
                continue
            i = g.index[w[0]]
            if tr.get(i) != d:
                continue
            e = g.c[i]; a = g.atr[i]; sl = e - d * sl_atr * a
            out.append(mkt(i + BAR, d, sl, e + d * tp_r * sl_atr * a, i + BAR + pd.Timedelta(minutes=hold)))
    return pd.DataFrame(out).sort_values('act') if out else pd.DataFrame()


# C9 ------------------------------------------------------------- Supertrend M15 a favore del trend H1
def supertrend(b, m1, n=10, k=3.0, tp_r=2.0, hold=240, sess=(180, 900)):
    a = atr(b, n).values; hl2 = ((b.h + b.l) / 2).values; c = b.c.values
    up = hl2 - k * a; dn = hl2 + k * a; fu = up.copy(); fd = dn.copy(); dirn = np.ones(len(b))
    for i in range(1, len(b)):
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        dirn[i] = 1 if c[i] > fd[i - 1] else (-1 if c[i] < fu[i - 1] else dirn[i - 1])
    flip = np.flatnonzero(np.diff(dirn) != 0) + 1
    tr = h1_trend(m1, b.index + (b.index[1] - b.index[0])).values; bar = b.index[1] - b.index[0]; out = []
    for i in flip:
        d = int(dirn[i])
        if tr[i] != d or not (sess[0] <= b.nym.iloc[i] < sess[1]):
            continue
        sl = fu[i] if d > 0 else fd[i]; e = c[i]
        if abs(e - sl) <= 0:
            continue
        out.append(mkt(b.index[i] + bar, d, sl, e + d * tp_r * abs(e - sl), b.index[i] + bar + pd.Timedelta(minutes=hold)))
    return pd.DataFrame(out)
