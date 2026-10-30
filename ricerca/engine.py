"""Backtester minimale: segnali calcolati su barre M5 chiuse, esecuzione e uscite simulate su M1.

Ipotesi prudenti:
- ingresso all'apertura della barra M1 successiva alla chiusura della M5 di segnale
- se nella stessa barra M1 vengono toccati sia SL che TP, si conta lo SL
- costo fisso per trade (spread + commissione) sottratto a ogni operazione, in unita' di prezzo
"""
import numpy as np, pandas as pd
from numba import njit

DATA = '/home/user/trading/data/'
COST = {'XAUUSD': 0.35, 'XAU26': 0.35, 'NAS100': 1.5, 'NAS100X': 1.5}   # $/oncia round-trip per l'oro, punti indice per il Nasdaq


def load(sym):
    m1 = pd.read_parquet(DATA + f'{sym}_M1.parquet')
    return m1


def resample(m1, tf):
    agg = {'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}
    if 'v' in m1:
        agg['v'] = 'sum'
    r = m1.resample(tf, label='left', closed='left').agg(agg)
    return r.dropna(subset=['o'])


# ---------------- indicatori ----------------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    pc = df.c.shift()
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def adx(df, n=14):
    up = df.h.diff(); dn = -df.l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(pdm, df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    ndi = 100 * pd.Series(ndm, df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def htf(series_htf, idx):
    """Porta un valore di timeframe superiore (gia' chiuso) sull'indice M5 senza lookahead."""
    s = series_htf.copy()
    s.index = s.index + (series_htf.index[1] - series_htf.index[0])  # disponibile solo a barra chiusa
    return s.reindex(idx, method='ffill')


# ---------------- simulazione ----------------
@njit(cache=True)
def _sim(t1, o1, h1, l1, c1, sig_t, sig_d, sig_sl, sig_tp, sig_hold, be_r, cost):
    n = len(sig_t)
    out = np.full((n, 5), np.nan)  # entry_idx, exit_idx, dir, pnl_price, sl_dist
    j = 0
    busy_until = -1
    k = 0
    for i in range(n):
        # indice M1 della prima barra con tempo >= tempo di ingresso
        while j < len(t1) and t1[j] < sig_t[i]:
            j += 1
        if j >= len(t1):
            break
        if j <= busy_until:
            continue  # il bot ha gia' una posizione aperta
        d = sig_d[i]; e = o1[j]
        sl = e - d * sig_sl[i]; tp = e + d * sig_tp[i]
        tmax = sig_t[i] + sig_hold[i]
        be_done = False
        x = -1; px = 0.0
        m = j
        while m < len(t1):
            if t1[m] >= tmax or (m > j and t1[m] - t1[m - 1] > 3 * 3600 * 1000000000):
                x = m; px = o1[m]; break
            hit_sl = (l1[m] <= sl) if d > 0 else (h1[m] >= sl)
            hit_tp = (h1[m] >= tp) if d > 0 else (l1[m] <= tp)
            if hit_sl:
                x = m; px = sl
                # gap oltre lo stop: esci all'apertura
                if (d > 0 and o1[m] < sl) or (d < 0 and o1[m] > sl):
                    px = o1[m]
                break
            if hit_tp:
                x = m; px = tp; break
            if be_r > 0 and not be_done:
                fav = (h1[m] - e) if d > 0 else (e - l1[m])
                if fav >= be_r * sig_sl[i]:
                    sl = e + d * cost  # break-even coprendo i costi
                    be_done = True
            m += 1
        if x < 0:
            break
        out[k, 0] = j; out[k, 1] = x; out[k, 2] = d
        out[k, 3] = d * (px - e) - cost; out[k, 4] = sig_sl[i]
        k += 1
        busy_until = x
    return out[:k]


def simulate(m1, sigs, sym, be_r=0.0):
    """sigs: DataFrame indicizzato sul tempo di chiusura della barra segnale con colonne d, sl, tp, hold (minuti)."""
    sigs = sigs[sigs.d != 0].dropna()
    if len(sigs) == 0:
        return pd.DataFrame()
    t1 = m1.index.values.astype('datetime64[ns]').astype('int64')
    st = sigs.index.values.astype('datetime64[ns]').astype('int64')
    hold = (sigs.hold.values * 60e9).astype('int64')
    r = _sim(t1, m1.o.values, m1.h.values, m1.l.values, m1.c.values, st, sigs.d.values.astype(np.float64),
             sigs.sl.values.astype(np.float64), sigs.tp.values.astype(np.float64), hold, be_r, COST[sym])
    tr = pd.DataFrame({'entry': m1.index[r[:, 0].astype(int)], 'exit': m1.index[r[:, 1].astype(int)],
                       'd': r[:, 2], 'pnl': r[:, 3], 'sl': r[:, 4]})
    tr['R'] = tr.pnl / tr.sl
    tr['mins'] = (tr.exit - tr.entry).dt.total_seconds() / 60
    tr['sym'] = sym
    return tr


def stats(tr, label=''):
    if len(tr) == 0:
        return {'name': label, 'trades': 0}
    days = max(1, tr.entry.dt.normalize().nunique())
    eq = tr.R.cumsum()
    dd = (eq.cummax() - eq).max()
    w = tr.R[tr.R > 0].sum(); l = -tr.R[tr.R < 0].sum()
    return {'name': label, 'trades': len(tr), 'per_day': round(len(tr) / days, 1),
            'win%': round(100 * (tr.R > 0).mean(), 1), 'avgR': round(tr.R.mean(), 3),
            'PF': round(w / l, 2) if l > 0 else np.inf, 'totR': round(tr.R.sum(), 1),
            'maxDD_R': round(dd, 1), 'med_min': round(tr.mins.median()),
            'avg_move': round(tr.pnl.abs().mean(), 2),
            'grossR': round(((tr.pnl + COST[tr.sym.iloc[0]]) / tr.sl).mean(), 3),
            'cost_R': round((COST[tr.sym.iloc[0]] / tr.sl).mean(), 3)}


def split_stats(tr, cut, label):
    a = stats(tr[tr.entry < cut], label + ' IS')
    b = stats(tr[tr.entry >= cut], label + ' OOS')
    return [a, b]


@njit(cache=True)
def _sim_limit(t1, o1, h1, l1, act, exp, d, px, sl, tp, tmax, cost):
    """Ordini limite: si attiva al primo minuto in [act, exp) che tocca px; poi SL/TP/tempo.
    Nel minuto di ingresso conta solo lo SL (ipotesi prudente)."""
    n = len(act); out = np.full((n, 5), np.nan); k = 0; j = 0; busy = -1
    for i in range(n):
        while j < len(t1) and t1[j] < act[i]:
            j += 1
        m = max(j, busy + 1); e = -1
        while m < len(t1) and t1[m] < exp[i]:
            if (d[i] > 0 and l1[m] <= px[i]) or (d[i] < 0 and h1[m] >= px[i]):
                e = m; break
            m += 1
        if e < 0:
            continue
        ep = px[i]
        if (d[i] > 0 and o1[e] < px[i]) or (d[i] < 0 and o1[e] > px[i]):
            ep = o1[e]
        x = -1; xp = 0.0; m = e
        if (d[i] > 0 and ep <= sl[i]) or (d[i] < 0 and ep >= sl[i]):
            x = e; xp = ep; m = len(t1)  # aperto gia' oltre lo stop: uscita immediata
        while m < len(t1):
            if m > e and t1[m] >= tmax[i]:
                x = m; xp = o1[m]; break
            hs = (l1[m] <= sl[i]) if d[i] > 0 else (h1[m] >= sl[i])
            if hs:
                x = m; xp = sl[i]
                if (d[i] > 0 and o1[m] < sl[i] and m > e) or (d[i] < 0 and o1[m] > sl[i] and m > e):
                    xp = o1[m]
                break
            if m > e:
                ht = (h1[m] >= tp[i]) if d[i] > 0 else (l1[m] <= tp[i])
                if ht:
                    x = m; xp = tp[i]; break
            m += 1
        if x < 0:
            break
        out[k, 0] = e; out[k, 1] = x; out[k, 2] = d[i]; out[k, 3] = d[i] * (xp - ep) - cost
        out[k, 4] = abs(px[i] - sl[i]) if abs(px[i]) < 1e11 else abs(ep - sl[i])  # rischio pianificato
        k += 1; busy = x
    return out[:k]


def simulate_limit(m1, orders, sym):
    """orders: DataFrame con act, exp, tmax (Timestamp), d, px, sl, tp (prezzi assoluti)."""
    if len(orders) == 0:
        return pd.DataFrame()
    o = orders.sort_values('act')
    I = lambda c: o[c].values.astype('datetime64[ns]').astype('int64')
    r = _sim_limit(m1.index.values.astype('datetime64[ns]').astype('int64'), m1.o.values, m1.h.values, m1.l.values, I('act'), I('exp'),
                   o.d.values.astype(np.float64), o.px.values.astype(np.float64), o.sl.values.astype(np.float64),
                   o.tp.values.astype(np.float64), I('tmax'), COST[sym])
    tr = pd.DataFrame({'entry': m1.index[r[:, 0].astype(int)], 'exit': m1.index[r[:, 1].astype(int)],
                       'd': r[:, 2], 'pnl': r[:, 3], 'sl': r[:, 4]})
    tr['R'] = tr.pnl / tr.sl; tr['mins'] = (tr.exit - tr.entry).dt.total_seconds() / 60; tr['sym'] = sym
    return tr
