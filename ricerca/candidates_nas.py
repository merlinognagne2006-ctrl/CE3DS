"""Tutti i segnali candidati del Nasdaq nella sessione di NY, ognuno simulato in modo indipendente
con l'uscita standard, piu' le caratteristiche al momento del segnale. Serve a costruire il punteggio."""
import numpy as np, pandas as pd, sys, warnings
warnings.filterwarnings('ignore')
import strat_lab as L
from lab_trendday import noise_state, pullback_signals


def session_rules(o, close_ny=(16, 50), no_entry=(960, 1110), friday_last=930):
    """Regole di sessione dell'EA: niente ingressi tra 16:00 e 18:30 NY (chiusura/riapertura giornaliera),
    il venerdi' niente ingressi dopo le 15:30 NY, chiusura forzata alle 16:50 NY (mai posizioni nella pausa o nel weekend)."""
    if len(o) == 0: return o
    ny = o.act.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    m = ny.dt.hour * 60 + ny.dt.minute
    keep = ~((m >= no_entry[0]) & (m < no_entry[1])) & ~((ny.dt.dayofweek == 4) & (m >= friday_last)) & (ny.dt.dayofweek != 5)
    o = o[keep.values].copy(); ny = ny[keep.values]
    d0 = ny.dt.normalize()
    cut = d0 + pd.Timedelta(hours=close_ny[0], minutes=close_ny[1])
    cut = cut.where(ny < cut, cut + pd.Timedelta(days=1))
    cut_utc = cut.dt.tz_convert('UTC').dt.tz_localize(None)
    o['tmax'] = np.minimum(o.tmax.values.astype('datetime64[ns]'), cut_utc.values.astype('datetime64[ns]'))
    return o


def candidates(sym, start=575, end=930, sl=1.5, hold=120, tp=0, trail=0.0, trail_on=0.0, be=0.0):
    b = L.F(sym)
    dc = b.groupby('tday').c.last(); td = np.sign(dc - dc.rolling(20).mean()).shift(1)
    b['tr_d1'] = b.tday.map(td).values
    st = noise_state(b, mult=1.0).values; b['noise'] = st
    w = (b.nym >= start) & (b.nym < end)
    trig = {}
    trig['ret3'] = np.where(b.ret3 >= 1.5, 1, np.where(b.ret3 <= -1.5, -1, 0))
    trig['ret6'] = np.where(b.ret6 >= 2.5, 1, np.where(b.ret6 <= -2.5, -1, 0))
    trig['vwap'] = np.where((b.vwd >= 2) & (b.tr_h1 == 1), 1, np.where((b.vwd <= -2) & (b.tr_h1 == -1), -1, 0))
    trig['pull'] = pullback_signals(b, st, window=(start, end))
    trig['noise'] = np.where((st == 1) & (np.roll(st, 1) != 1), 1, np.where((st == -1) & (np.roll(st, 1) != -1), -1, 0))
    D = pd.DataFrame(trig, index=b.index).mul(w.values.astype(int), axis=0)
    # direzione: somma dei trigger concordi; scarta conflitti
    pos = (D > 0).sum(axis=1); neg = (D < 0).sum(axis=1)
    d = np.where((pos > 0) & (neg == 0), 1, np.where((neg > 0) & (pos == 0), -1, 0))
    o = L.orders_from(b, d, sl_atr=sl, tp_atr=tp, hold=hold, cooldown=1, trail_atr=trail, trail_on_atr=trail_on, be_atr=be)
    o = session_rules(o)
    tr = L.run(sym, o, 'now')
    f = b.iloc[tr.bi.values]
    dd = tr.d.values
    out = pd.DataFrame({'entry': tr.entry.values, 'exit': tr.exit.values, 'd': dd, 'R': tr.R.values, 'mins': tr.mins.values,
                        'cost_R': tr.cost_R.values, 'nym': f.nym.values,
                        'n_trig': (pos.values + neg.values)[tr.bi.values]})
    for k in trig: out['t_' + k] = (D[k].values[tr.bi.values] == dd).astype(int)
    out['mom3'] = f.ret3.values * dd; out['mom6'] = f.ret6.values * dd; out['vwd'] = f.vwd.values * dd
    out['tr_h1'] = f.tr_h1.values * dd; out['tr_m15'] = f.tr_m15.values * dd; out['tr_d1'] = f.tr_d1.values * dd
    out['noise'] = f.noise.values * dd; out['rr'] = f.rr.values; out['clv'] = np.where(dd > 0, f.clv.values, 1 - f.clv.values)
    out['atr_ratio'] = (f.atr / f.atr_slow).values
    out['dow'] = f.dow.values; out['year'] = pd.DatetimeIndex(out.entry).year
    return out


if __name__ == '__main__':
    sym = sys.argv[1] if len(sys.argv) > 1 else 'NASH'
    c = candidates(sym); c.to_parquet(f'../results/cand_{sym}.parquet')
    print(sym, len(c), 'candidati', round(len(c) / c.entry.dt.normalize().nunique(), 1), 'al giorno; R medio', round(c.R.mean(), 3))
