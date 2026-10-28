"""Gruppo B: strategie intraday "di qualita'" prese dalla letteratura / internet.
Tutte producono ordini con livelli assoluti per engine.simulate_limit.

C1 ORB 5 minuti (Zarattini & Aziz 2023, "Can Day Trading Really Be Profitable?")
C2 Noise Area intraday momentum (Zarattini, Aziz & Barbon 2024, "Beat the Market")
C3 Sweep di liquidita' + rientro (Turtle Soup di Connors/Raschke, versione ICT con killzone)
C4 Order block con displacement + volume + trend (definizione causale, senza lookahead)
"""
import numpy as np, pandas as pd
from engine import resample, atr, ema

MKT = 1e12
M = pd.Timedelta(minutes=1)


def ny(idx):
    return idx.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None)


def frame(m1, tf='5min'):
    b = resample(m1, tf)
    b['ny'] = ny(b.index)
    b['nyday'] = b.ny.dt.normalize()
    b['nym'] = b.ny.dt.hour * 60 + b.ny.dt.minute
    b['atr'] = atr(b, 14)
    return b


def _utc(ny_ts):
    return ny_ts.tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward').tz_convert('UTC').tz_localize(None)


def mkt(t, d, sl, tp, tmax):
    """ordine a mercato all'apertura del minuto t"""
    return dict(act=t, exp=t + M, d=d, px=MKT if d > 0 else -MKT, sl=sl, tp=tp, tmax=tmax)


# ---------------------------------------------------------------- C1
def orb5(b, tp_r=10.0, rvol_min=0.0, bars=1, eod_ny=16 * 60, max_risk_atr=99):
    """Prima candela (o prime `bars` candele M5) dopo le 9:30 NY: direzione della candela,
    stop al lato opposto, target tp_r volte il rischio oppure chiusura a fine sessione."""
    out = []
    first = b[(b.nym >= 570) & (b.nym < 570 + 5 * bars)]
    g = first.groupby('nyday')
    o = g.o.first(); c = g.c.last(); h = g.h.max(); l = g.l.min()
    v = g.v.sum() if 'v' in b else None
    rv = (v / v.shift(1).rolling(14).mean()) if v is not None else pd.Series(1.0, o.index)
    at = g.atr.last()
    for day in o.index:
        d = int(np.sign(c[day] - o[day]))
        if d == 0 or not (rv.get(day, 0) >= rvol_min):
            continue
        e = c[day]; sl = l[day] if d > 0 else h[day]; risk = abs(e - sl)
        if risk <= 0 or risk > max_risk_atr * at[day]:
            continue
        t = _utc(day + pd.Timedelta(minutes=570 + 5 * bars))
        tmax = _utc(day + pd.Timedelta(minutes=eod_ny))
        out.append(mkt(t, d, sl, e + d * tp_r * risk, tmax))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- C2
def noise_area(m1, lookback=14, mult=1.0, start_ny=600, end_ny=15 * 60 + 30, step=30, stop_k=1.0):
    """Banda di rumore = apertura del giorno +/- media (14 gg) dello spostamento assoluto dall'apertura
    allo stesso minuto. Controllo ogni 30 minuti: long sopra la banda alta, short sotto la bassa.
    Uscita: al controllo successivo se il prezzo torna sotto max(banda, VWAP) (trailing del paper)
    o a fine giornata. Stop di protezione = stop_k x (banda alta - apertura)."""
    b = resample(m1, '5min'); b['ny'] = ny(b.index)
    b = b[(b.ny.dt.hour * 60 + b.ny.dt.minute >= 570) & (b.ny.dt.hour * 60 + b.ny.dt.minute < 960)]
    b['day'] = b.ny.dt.normalize(); b['m'] = b.ny.dt.hour * 60 + b.ny.dt.minute
    op = b.groupby('day').o.transform('first')
    b['mv'] = (b.c / op - 1).abs()
    piv = b.pivot_table(index='day', columns='m', values='mv')
    sig = piv.shift(1).rolling(lookback, min_periods=lookback).mean() * mult
    days = piv.index
    closes = b.groupby('day').c.last(); prevc = closes.shift(1)
    tp_ = (b.h + b.l + b.c) / 3; vv = b.v if 'v' in b and b.v.sum() > 0 else pd.Series(1.0, b.index)
    b['vwap'] = (tp_ * vv).groupby(b.day).cumsum() / vv.groupby(b.day).cumsum()
    trades = []
    for day, g in b.groupby('day'):
        if day not in sig.index or sig.loc[day].isna().all() or pd.isna(prevc.get(day)):
            continue
        o0 = g.o.iloc[0]; up_base = max(o0, prevc[day]); dn_base = min(o0, prevc[day])
        s = sig.loc[day]; g = g.set_index('m')
        pos = 0; entry = None
        for m in range(start_ny, end_ny + 1, step):
            mm = m - 5  # barra che chiude al minuto m
            if mm not in g.index or pd.isna(s.get(mm)):
                continue
            cl = g.c[mm]; ub = up_base * (1 + s[mm]); lb = dn_base * (1 - s[mm]); vw = g.vwap[mm]
            if pos == 1 and cl < max(ub, vw):
                trades[-1]['exit_ny'] = m; pos = 0
            elif pos == -1 and cl > min(lb, vw):
                trades[-1]['exit_ny'] = m; pos = 0
            if pos == 0 and m < end_ny:
                if cl > ub:
                    pos = 1; trades.append(dict(day=day, d=1, e=cl, sl=cl - stop_k * (ub - o0 if ub > o0 else ub * s[mm]), entry_ny=m, exit_ny=960 - 5))
                elif cl < lb:
                    pos = -1; trades.append(dict(day=day, d=-1, e=cl, sl=cl + stop_k * (o0 - lb if lb < o0 else lb * s[mm]), entry_ny=m, exit_ny=960 - 5))
    out = []
    for t in trades:
        a = _utc(t['day'] + pd.Timedelta(minutes=t['entry_ny'])); x = _utc(t['day'] + pd.Timedelta(minutes=t['exit_ny']))
        out.append(mkt(a, t['d'], t['sl'], t['e'] + t['d'] * 100 * abs(t['e'] - t['sl']), x))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- C3
def liquidity_sweep(b, tp_r=2.0, confirm=3, hold_min=120, kill=((120, 300), (510, 660)), buf_atr=0.1, levels=('asia', 'london', 'pd')):
    """Livelli di liquidita': massimo/minimo di Asia (20:00-24:00 NY), Londra (02:00-05:00 NY) e giorno precedente.
    Sweep: la candela supera il livello e chiude di nuovo dentro. Conferma: entro `confirm` candele una chiusura
    oltre l'estremo opposto della candela di sweep (cambio di struttura). Ingresso a mercato, stop oltre
    l'estremo dello sweep, target tp_r volte il rischio. Solo nelle killzone (Londra 2-5, NY 8:30-11 ora NY)."""
    b = b.copy()
    # "giorno di trading" che parte alle 18:00 NY
    tday = (b.ny + pd.Timedelta(hours=6)).dt.normalize()
    b['tday'] = tday
    m = b.nym
    def rng(mask):
        hh = b.h.where(mask).groupby(tday).transform('max'); ll = b.l.where(mask).groupby(tday).transform('min'); return hh, ll
    asia_m = (m >= 20 * 60); lon_m = (m >= 120) & (m < 300)
    ah, al = rng(asia_m); lh, ll_ = rng(lon_m)
    dly = b.groupby(tday).agg(h=('h', 'max'), l=('l', 'min'))
    pdh = pd.Series(dly.h.shift().reindex(tday).values, b.index); pdl = pd.Series(dly.l.shift().reindex(tday).values, b.index)
    out = []; used = set()
    H, L, C, A = b.h.values, b.l.values, b.c.values, b.atr.values
    for k, (s, e) in enumerate(kill):
        cand = []
        if 'asia' in levels: cand.append(('asia', ah, al))
        if 'london' in levels and s >= 480: cand.append(('london', lh, ll_))
        if 'pd' in levels: cand.append(('pd', pdh, pdl))
        inkz = ((m >= s) & (m < e)).values
        for name, hi, lo in cand:
            hv, lv = hi.values, lo.values
            for i in np.where(inkz)[0]:
                key = (tday.iloc[i], name, k)
                if key in used or np.isnan(hv[i]):
                    continue
                for d, lvl, swept in ((-1, hv[i], H[i] > hv[i] and C[i] < hv[i]), (1, lv[i], L[i] < lv[i] and C[i] > lv[i])):
                    if not swept:
                        continue
                    ext = H[i] if d < 0 else L[i]; trig = L[i] if d < 0 else H[i]
                    for j in range(i + 1, min(i + 1 + confirm, len(C))):
                        if (d < 0 and H[j] > ext) or (d > 0 and L[j] < ext):
                            break  # nuovo estremo: setup invalidato
                        if (d < 0 and C[j] < trig) or (d > 0 and C[j] > trig):
                            sl = ext - d * buf_atr * A[i]; ent = C[j]; risk = abs(ent - sl)
                            t = b.index[j] + (b.index[1] - b.index[0] if False else pd.Timedelta(minutes=5))
                            out.append(mkt(t, d, sl, ent + d * tp_r * risk, t + pd.Timedelta(minutes=hold_min)))
                            used.add(key); break
                    if key in used:
                        break
    return pd.DataFrame(out).sort_values('act') if out else pd.DataFrame()


# ---------------------------------------------------------------- C4
def order_block(b, h1, tp_r=2.0, disp_atr=1.2, vol_k=1.5, swing=20, valid_bars=48, sess=((180, 660),), hold_min=180, buf_atr=0.1, trend=True):
    """Order block causale: ultima candela opposta prima di una candela di displacement (corpo > disp_atr x ATR,
    volume > vol_k x media 20, rompe il massimo/minimo delle ultime `swing` candele). Zona = high/low di quella candela.
    Ordine limite al bordo della zona per `valid_bars` candele, nella direzione del trend H1 (EMA50)."""
    o, h, l, c, a = b.o.values, b.h.values, b.l.values, b.c.values, b.atr.values
    v = b.v.values if 'v' in b and b.v.sum() > 0 else None
    vavg = b.v.rolling(20).mean().shift().values if v is not None else None
    hh = b.h.rolling(swing).max().shift().values; lw = b.l.rolling(swing).min().shift().values
    tr = (b.c > b.c.index.map(lambda x: np.nan) if False else None)
    e50 = ema(h1.c, 50); e50.index = e50.index + pd.Timedelta(hours=1); e50 = e50.reindex(b.index, method='ffill').values
    m = b.nym.values
    insess = np.zeros(len(b), bool)
    for s, e in sess: insess |= (m >= s) & (m < e)
    bar = b.index.to_series().diff().mode()[0]
    out = []
    for i in range(swing + 2, len(b) - 1):
        body = abs(c[i] - o[i])
        if not insess[i] or body < disp_atr * a[i]:
            continue
        if v is not None and not (v[i] > vol_k * vavg[i]):
            continue
        d = 1 if (c[i] > o[i] and c[i] > hh[i]) else (-1 if (c[i] < o[i] and c[i] < lw[i]) else 0)
        if d == 0 or (trend and (np.isnan(e50[i]) or (d > 0 and c[i] < e50[i]) or (d < 0 and c[i] > e50[i]))):
            continue
        # ultima candela opposta nelle 3 precedenti
        k = None
        for j in range(i - 1, i - 4, -1):
            if (d > 0 and c[j] < o[j]) or (d < 0 and c[j] > o[j]):
                k = j; break
        if k is None:
            continue
        top, bot = h[k], l[k]
        px = top if d > 0 else bot
        sl = (bot - buf_atr * a[i]) if d > 0 else (top + buf_atr * a[i])
        risk = abs(px - sl)
        if risk <= 0:
            continue
        act = b.index[i] + bar  # solo dopo la chiusura della candela di displacement
        out.append(dict(act=act, exp=act + bar * valid_bars, d=d, px=px, sl=sl,
                        tp=px + d * tp_r * risk, tmax=act + bar * valid_bars + pd.Timedelta(minutes=hold_min)))
    return pd.DataFrame(out)
