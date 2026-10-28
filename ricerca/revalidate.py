"""Rivalidazione delle strategie dei gruppi A/B/C sullo storico lungo (Nasdaq 2014-2026, oro 2016-2026)
con il motore v2 e costi relativi di oggi."""
import numpy as np, pandas as pd, sys, warnings
warnings.filterwarnings('ignore')
import engine2 as E, strat_lab as L
from engine import resample
import strategies as S, groupb as G, groupc as C
pd.set_option('display.width', 250)


def from_rel(sigs):
    """segnali del gruppo A (d, sl/tp come distanze, hold in minuti) -> ordini assoluti a mercato"""
    if len(sigs) == 0: return pd.DataFrame()
    s = sigs[sigs.d != 0].dropna()
    return pd.DataFrame({'act': s.index, 'd': s.d.values.astype(float), 'ref': np.nan, 'sl_d': s.sl.values,
                         'tp_d': s.tp.values, 'tmax': s.index + pd.to_timedelta(s.hold.values, unit='m')})


def finalize_rel(o, m1):
    """riferimento = apertura del minuto di ingresso"""
    i = m1.index.searchsorted(o.act.values)
    i = np.clip(i, 0, len(m1) - 1); ref = m1.o.values[i]
    o['sl'] = ref - o.d * o.sl_d; o['tp'] = np.where(o.tp_d > 0, ref + o.d * o.tp_d, 0.0)
    return o.drop(columns=['ref', 'sl_d', 'tp_d'])


def trend_filter(o, m1):
    h1 = resample(m1, '1h'); e = h1.c.ewm(span=50, adjust=False).mean(); s = np.sign(h1.c - e); s.index = s.index + pd.Timedelta(hours=1)
    t = s.reindex(pd.DatetimeIndex(o.act), method='ffill').values
    return o[t == o.d.values].reset_index(drop=True)


def run_all(sym):
    m1 = L.m1(sym); m5 = resample(m1, '5min'); m15 = resample(m1, '15min'); h1 = resample(m1, '1h')
    b5 = G.frame(m1); b15 = G.frame(m1, '15min')
    out = {}
    if sym.startswith('NAS'):
        out['B1_EMA_M5'] = finalize_rel(from_rel(S.ema_cross_momo(m5, m15, f=12, s=21, tn=100, sl_atr=1.5, tp_atr=2, sess=(7, 20))), m1)
        out['B2_EMA_M15'] = finalize_rel(from_rel(S.ema_cross_momo(m15, h1, f=12, s=21, tn=50, sl_atr=1.5, tp_atr=2, sess=(7, 20))), m1)
        out['H1_OrderBlock'] = G.order_block(b15, h1, tp_r=2, disp_atr=1.0, buf_atr=1.0, valid_bars=16)
        out['H2_Sweep'] = trend_filter(G.liquidity_sweep(b5, tp_r=2, confirm=3, kill=((510, 660),)), m1)
        out['H4_NoiseArea'] = G.noise_area(m1, mult=1.5, stop_k=2.0)
        out['C1_LastHalfHour'] = C.last_half_hour(b5)
        out['C2_GapFade'] = C.gap_fade(b5)
        out['C3_Supertrend'] = C.supertrend(b15, m1)
        out['C4_FVG_M5'] = C.fvg(b5, m1)
    else:
        out['B5_NY_ORB15'] = finalize_rel(from_rel(S.range_break(m5, rng=(13.5, 13.75), win=(13.75, 17), sl_k=1, tp_k=1)), m1)
        out['H3_ORB30_trend'] = trend_filter(G.orb5(b5, tp_r=2, bars=6), m1)
        out['C1_LastHalfHour'] = C.last_half_hour(b5)
        out['C3_Supertrend'] = C.supertrend(b15, m1)
        out['C4_FVG_M5'] = C.fvg(b5, m1)
        out['C4_FVG_M15'] = C.fvg(b15, m1, valid=8, hold=240)
    rows = []; trades = {}
    for k, o in out.items():
        if o is None or len(o) == 0: continue
        o = o.reset_index(drop=True)
        if 'px' in o: o['px'] = np.where(np.abs(o.px) >= 1e11, np.where(o.d > 0, 1e12, -1e12), o.px)
        tr = L.run(sym, o, 'now'); trades[k] = tr
        rows.append({'sym': sym, **L.report(tr, k)})
    return pd.DataFrame(rows), trades


if __name__ == '__main__':
    res = []; allt = {}
    for sym in sys.argv[1].split(','):
        r, t = run_all(sym); res.append(r); allt.update({(sym, k): v for k, v in t.items()})
    df = pd.concat(res); df.to_csv('../results/revalidate.csv', index=False); pd.to_pickle(allt, '../results/revalidate_trades.pkl')
    print(df[['sym', 'name', 'n', 'per_day', 'win%', 'avgR', 'costR', 'PF', 'maxDD_R', 'med_min', 't', 'yrs+', 'worstY', 'R_2023+']].to_string(index=False))
