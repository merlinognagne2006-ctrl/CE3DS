"""Laboratorio: da maschere di eventi a strategie con SL/TP/tempo, simulate con engine2 e costi realistici.
Due costi: 'hist' (spread minimo storico, penalizza gli anni vecchi) e 'now' (stesso costo relativo di oggi in bps)."""
import numpy as np, pandas as pd
import engine2 as E

M1 = {}


def m1(sym):
    if sym not in M1:
        M1[sym] = E.load(sym)
    return M1[sym]


def F(sym):
    return pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet')


def orders_from(b, d, sl_atr=1.5, tp_atr=2.0, hold=60, cooldown=6, trail_atr=0.0, trail_on_atr=0.0, be_atr=0.0,
                sl_mode='atr', max_per_day=0, atr_col='atr'):
    """d: array +1/-1/0 sulla barra M5 chiusa. Ingresso all'apertura della barra successiva.
    cooldown: barre minime tra due segnali della stessa strategia. sl_mode 'atr' o 'swing6' (min/max ultime 6 barre)."""
    d = np.asarray(d); idx = np.flatnonzero(d)
    bar = b.index.to_series().diff().mode()[0]
    keep = []; last = -10 ** 9; cnt = {}
    for i in idx:
        if i - last < cooldown: continue
        if max_per_day:
            k = (b.tday.iloc[i], int(d[i]))
            if cnt.get(k, 0) >= max_per_day: continue
            cnt[k] = cnt.get(k, 0) + 1
        keep.append(i); last = i
    keep = np.array(keep, dtype=int)
    if len(keep) == 0: return pd.DataFrame()
    a = b[atr_col].values[keep]; c = b.c.values[keep]; dd = d[keep].astype(float)
    if sl_mode == 'swing6':
        lo = b.l.rolling(6).min().values[keep]; hi = b.h.rolling(6).max().values[keep]
        sl = np.where(dd > 0, np.minimum(lo, c - 0.5 * a), np.maximum(hi, c + 0.5 * a)) - dd * 0.1 * a
        risk = np.abs(c - sl)
        tp = np.where(tp_atr > 0, c + dd * tp_atr * risk, 0.0)      # qui tp_atr = multiplo del rischio
    else:
        sl = c - dd * sl_atr * a
        tp = np.where(tp_atr > 0, c + dd * tp_atr * a, 0.0)
    act = b.index[keep] + bar
    o = pd.DataFrame({'act': act, 'd': dd, 'sl': sl, 'tp': tp, 'tmax': act + pd.Timedelta(minutes=hold),
                      'trail': trail_atr * a, 'trail_on': trail_on_atr * a, 'be': be_atr * a, 'bi': keep})
    return o


def run(sym, o, cost='now'):
    if len(o) == 0: return pd.DataFrame()
    if cost == 'now':
        save = E.cost_of
        E.cost_of = lambda s, p: (0.00006 if s.startswith('NAS') else 0.0001) * np.asarray(p, float)
        try:
            tr = E.simulate(m1(sym), o, sym)
        finally:
            E.cost_of = save
    else:
        tr = E.simulate(m1(sym), o, sym)
    return tr


def report(tr, label):
    if len(tr) == 0: return {'name': label, 'n': 0}
    r = E.summary(tr, label)
    y = tr.groupby(tr.entry.dt.year).R.mean()
    r['yrs+'] = f"{(y > 0).sum()}/{len(y)}"; r['worstY'] = round(y.min(), 3)
    r['R_2023+'] = round(tr[tr.entry >= '2023-01-01'].R.mean(), 3)
    return r
