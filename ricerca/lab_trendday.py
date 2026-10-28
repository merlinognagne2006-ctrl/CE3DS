"""Giornata di trend + pullback: quando il prezzo e' fuori dalla 'noise area' di Zarattini (o lontano dal VWAP),
ogni ritracciamento verso EMA20/VWAP seguito da ripartenza e' un ingresso nella direzione del trend.
Valutazione IS (<=2021) / OOS (>=2022)."""
import numpy as np, pandas as pd, itertools, sys, warnings
warnings.filterwarnings('ignore')
import strat_lab as L
pd.set_option('display.width', 270); pd.set_option('display.max_rows', 500)


def noise_state(b, lookback=14, mult=1.0, session=(570, 960)):
    """+1 sopra la banda alta, -1 sotto la bassa, 0 dentro. Bande calcolate sullo stesso minuto dei giorni precedenti,
    rispetto all'apertura della sessione (09:30 NY) e alla chiusura precedente."""
    s0, s1 = session
    r = b[(b.nym >= s0) & (b.nym < s1)].copy()
    r['day'] = r.ny.dt.normalize()
    op = r.groupby('day').o.transform('first')
    r['mv'] = (r.c / op - 1).abs()
    piv = r.pivot_table(index='day', columns='nym', values='mv')
    sig = piv.shift(1).rolling(lookback, min_periods=lookback).mean() * mult
    sig_long = sig.stack().rename('sig').reset_index()
    r = r.reset_index().merge(sig_long, on=['day', 'nym'], how='left').set_index('t' if 't' in r.reset_index().columns else 'index')
    prevc = r.groupby('day').c.last().shift(1)
    r['pc'] = r.day.map(prevc); r['op'] = op.values
    up = np.maximum(r.op, r.pc) * (1 + r.sig); dn = np.minimum(r.op, r.pc) * (1 - r.sig)
    st = np.where(r.c > up, 1, np.where(r.c < dn, -1, 0))
    out = pd.Series(0, index=b.index, dtype=float)
    out.loc[r.index] = st
    return out


def pullback_signals(b, state, ema_col='ema20', touch_atr=0.3, window=(600, 930)):
    """long: stato +1, la barra precedente ha toccato EMA20 (low <= ema + 0.3ATR), la barra chiude sopra il massimo precedente."""
    w = (b.nym >= window[0]) & (b.nym < window[1])
    e = b[ema_col]; a = b.atr
    touch_l = (b.l.shift(1) <= e.shift(1) + touch_atr * a.shift(1)); touch_s = (b.h.shift(1) >= e.shift(1) - touch_atr * a.shift(1))
    up = w & (state == 1) & touch_l & (b.c > b.h.shift(1)) & (b.c > e)
    dn = w & (state == -1) & touch_s & (b.c < b.l.shift(1)) & (b.c < e)
    return np.where(up, 1, np.where(dn, -1, 0))


def evaluate(sym, label, d, grid, cooldown=3):
    b = L.F(sym); rows = []
    for sl, tp, h in grid:
        o = L.orders_from(b, d, sl_atr=sl, tp_atr=tp, hold=h, cooldown=cooldown)
        tr = L.run(sym, o, 'now')
        if len(tr) == 0: continue
        IS = tr[tr.entry < '2022-01-01']; OS = tr[tr.entry >= '2022-01-01']; y = tr.groupby(tr.entry.dt.year).R.mean()
        rows.append({'name': label, 'sl': sl, 'tp': tp, 'h': h, 'n': len(tr), 'per_day': round(len(tr) / b.tday.nunique(), 2),
                     'win%': round(100 * (tr.R > 0).mean(), 1), 'R_IS': round(IS.R.mean(), 3), 't_IS': round(IS.R.mean() / IS.R.std() * np.sqrt(len(IS)), 1),
                     'R_OOS': round(OS.R.mean(), 3), 't_OOS': round(OS.R.mean() / OS.R.std() * np.sqrt(len(OS)), 1), 'yrs+': f'{(y > 0).sum()}/{len(y)}',
                     'costR': round(tr.cost_R.mean(), 3), 'med_min': round(tr.mins.median())})
    return rows


if __name__ == '__main__':
    grid = [(sl, tp, h) for sl in (1.0, 1.5, 2.5) for tp in (0, 2.0, 3.0) for h in (60, 120)]
    rows = []
    for sym in sys.argv[1].split(','):
        b = L.F(sym)
        for mult in (1.0, 1.5):
            st = noise_state(b, mult=mult)
            for ema_col in ('ema20', 'vwap'):
                d = pullback_signals(b, st, ema_col=ema_col)
                rows += [dict(r, sym=sym) for r in evaluate(sym, f'TD_pull m{mult} {ema_col}', d, grid)]
    df = pd.DataFrame(rows); df.to_csv('../results/lab_trendday.csv', index=False)
    for (s, n), g in df.groupby(['sym', 'name'], sort=False):
        print(g.sort_values('t_IS', ascending=False).head(4).to_string(index=False)); print()
