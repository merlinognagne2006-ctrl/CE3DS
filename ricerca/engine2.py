"""Motore v2: ogni ordine e' simulato in modo indipendente (nessun vincolo 'occupato'),
cosi' il livello di portafoglio (max posizioni, stop giornalieri, ecc.) puo' scegliere dopo.

Ordini: act (tempo da cui l'ordine e' valido), exp (scadenza per l'esecuzione), d (+1/-1),
px (prezzo limite; +-1e12 = a mercato), sl, tp (assoluti; tp=0 nessun target), tmax (uscita a tempo),
trail (distanza del trailing, 0 = no), trail_on (profitto che attiva il trailing), be (profitto che porta lo SL
a pareggio + costi, 0 = no), cost (costo andata+ritorno in prezzo).
Esecuzione a mercato: apertura del primo minuto >= act. Ipotesi prudenti: nello stesso minuto SL prima del TP;
il trailing e il break-even si aggiornano con il massimo/minimo del minuto e valgono dal minuto successivo.
"""
import numpy as np, pandas as pd
from numba import njit

DATA = '/home/user/trading/data/'


def load(sym):
    return pd.read_parquet(DATA + f'{sym}_M1.parquet')


def cost_of(sym, price):
    """costo realistico andata+ritorno per broker prop (spread medio + commissione), in prezzo"""
    price = np.asarray(price, dtype=float)
    if sym.startswith('NAS'):
        return np.maximum(1.0, 0.00006 * price)       # ~1.5 punti a 25.000
    return np.maximum(0.30, 0.0001 * price)            # oro: ~0.40 $ a 4.000 (spread 0.33 + comm. 0.07)


@njit(cache=True)
def _sim(t1, o1, h1, l1, c1, act, exp, d, px, sl0, tp, tmax, trail, trail_on, be, cost):
    n = len(act)
    out = np.full((n, 6), np.nan)  # entry_i, exit_i, entry_px, pnl, risk, mfe
    j0 = 0
    for i in range(n):
        while j0 < len(t1) and t1[j0] < act[i]:
            j0 += 1
        # esecuzione
        e = -1; m = j0
        while m < len(t1) and t1[m] < exp[i]:
            if abs(px[i]) > 1e11:
                e = m; break
            if (d[i] > 0 and l1[m] <= px[i]) or (d[i] < 0 and h1[m] >= px[i]):
                e = m; break
            m += 1
        if e < 0:
            continue
        if abs(px[i]) > 1e11:
            ep = o1[e]
        else:
            ep = px[i]
            if (d[i] > 0 and o1[e] < px[i]) or (d[i] < 0 and o1[e] > px[i]):
                ep = o1[e]
        risk = abs(px[i] - sl0[i]) if abs(px[i]) < 1e11 else abs(ep - sl0[i])
        if risk <= 0:
            continue
        sl = sl0[i]; best = ep; trailing = False; bedone = False
        x = -1; xp = 0.0; mfe = 0.0
        if (d[i] > 0 and ep <= sl) or (d[i] < 0 and ep >= sl):
            x = e; xp = ep
        m = e
        while x < 0 and m < len(t1):
            if m > e and (t1[m] >= tmax[i] or t1[m] - t1[m - 1] > 3 * 3600 * 1000000000):
                x = m; xp = o1[m]; break
            if d[i] > 0:
                if l1[m] <= sl:
                    x = m; xp = sl if o1[m] >= sl or m == e else o1[m]; break
                if tp[i] > 0 and m > e and h1[m] >= tp[i]:
                    x = m; xp = tp[i] if o1[m] <= tp[i] else o1[m]; break
                if h1[m] > best: best = h1[m]
            else:
                if h1[m] >= sl:
                    x = m; xp = sl if o1[m] <= sl or m == e else o1[m]; break
                if tp[i] > 0 and m > e and l1[m] <= tp[i]:
                    x = m; xp = tp[i] if o1[m] >= tp[i] else o1[m]; break
                if l1[m] < best: best = l1[m]
            fav = (best - ep) * d[i]
            if fav > mfe: mfe = fav
            # aggiornamenti validi dal minuto successivo
            if be[i] > 0 and not bedone and fav >= be[i]:
                nsl = ep + d[i] * cost[i]
                if (d[i] > 0 and nsl > sl) or (d[i] < 0 and nsl < sl): sl = nsl
                bedone = True
            if trail[i] > 0 and fav >= trail_on[i]:
                nsl = best - d[i] * trail[i]
                if (d[i] > 0 and nsl > sl) or (d[i] < 0 and nsl < sl): sl = nsl
            m += 1
        if x < 0:
            continue
        out[i, 0] = e; out[i, 1] = x; out[i, 2] = ep
        out[i, 3] = d[i] * (xp - ep) - cost[i]; out[i, 4] = risk; out[i, 5] = mfe / risk
    return out


def simulate(m1, orders, sym):
    """Ritorna un DataFrame di trade (uno per ordine eseguito), stesso indice degli ordini."""
    if len(orders) == 0:
        return pd.DataFrame()
    o = orders.sort_values('act').reset_index(drop=True)
    for c, v in (('trail', 0.0), ('trail_on', 0.0), ('be', 0.0)):
        if c not in o: o[c] = v
    if 'exp' not in o: o['exp'] = o['act'] + pd.Timedelta(minutes=1)
    if 'px' not in o: o['px'] = np.where(o.d > 0, 1e12, -1e12)
    if 'tp' not in o: o['tp'] = 0.0
    ref = np.where(np.abs(o.px) < 1e11, o.px, o.sl)
    o['cost'] = cost_of(sym, ref)
    I = lambda s: s.values.astype('datetime64[ns]').astype('int64')
    t1 = m1.index.values.astype('datetime64[ns]').astype('int64')
    r = _sim(t1, m1.o.values, m1.h.values, m1.l.values, m1.c.values, I(o.act), I(o.exp), o.d.values.astype(np.float64),
             o.px.values.astype(np.float64), o.sl.values.astype(np.float64), o.tp.values.astype(np.float64), I(o.tmax),
             o.trail.values.astype(np.float64), o.trail_on.values.astype(np.float64), o.be.values.astype(np.float64),
             o.cost.values.astype(np.float64))
    ok = ~np.isnan(r[:, 0])
    tr = o[ok].copy()
    tr['entry'] = m1.index[r[ok, 0].astype(int)]; tr['exit'] = m1.index[r[ok, 1].astype(int)]
    tr['ep'] = r[ok, 2]; tr['pnl'] = r[ok, 3]; tr['risk'] = r[ok, 4]; tr['mfe'] = r[ok, 5]
    tr['R'] = tr.pnl / tr.risk; tr['cost_R'] = tr.cost / tr.risk
    tr['mins'] = (tr.exit - tr.entry).dt.total_seconds() / 60; tr['sym'] = sym
    return tr.reset_index(drop=True)


def summary(tr, label='', by=None):
    if tr is None or len(tr) == 0:
        return {'name': label, 'n': 0}
    days = max(1, tr.entry.dt.normalize().nunique())
    w = tr.R[tr.R > 0].sum(); l = -tr.R[tr.R < 0].sum()
    eq = tr.sort_values('exit').R.cumsum()
    r = {'name': label, 'n': len(tr), 'per_day': round(len(tr) / days, 2), 'win%': round(100 * (tr.R > 0).mean(), 1),
         'avgR': round(tr.R.mean(), 3), 'grossR': round((tr.R + tr.cost_R).mean(), 3), 'costR': round(tr.cost_R.mean(), 3),
         'PF': round(w / l, 2) if l > 0 else np.inf, 'maxDD_R': round((eq.cummax() - eq).max(), 1),
         'med_min': round(tr.mins.median()), 't': round(tr.R.mean() / (tr.R.std() + 1e-12) * np.sqrt(len(tr)), 2)}
    if by is not None:
        for k, g in tr.groupby(by):
            r[str(k)] = round(g.R.mean(), 3)
    return r
