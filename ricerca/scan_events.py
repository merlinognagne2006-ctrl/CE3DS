"""Scansione sistematica di eventi di 'accelerazione' e risposta del prezzo a 30/60/120 minuti (ATR, lordo).
Per ogni cella (evento x sessione x trend [x volume]) calcola media, t-stat, coerenza tra anni.
Positivo = continuazione nella direzione dell'evento, negativo = inversione."""
import pandas as pd, numpy as np, sys, itertools
from feat import fwd
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 500)

SESS = [('asia', lambda m: (m >= 1110) | (m < 120)), ('london', lambda m: (m >= 120) & (m < 480)),
        ('ny_open', lambda m: (m >= 570) & (m < 660)), ('ny_pre', lambda m: (m >= 480) & (m < 570)),
        ('ny_mid', lambda m: (m >= 660) & (m < 840)), ('ny_pm', lambda m: (m >= 840) & (m < 960))]


def events(b):
    E = {}
    sgn = np.sign(b.body)
    for k in (0.8, 1.2, 1.6):
        E[f'bar{k}'] = np.where((b.body >= k) & (b.clv >= 0.7), 1, np.where((b.body <= -k) & (b.clv <= 0.3), -1, 0))
    for k in (1.5, 2.5, 3.5):
        E[f'v3_{k}'] = np.where(b.ret3 >= k, 1, np.where(b.ret3 <= -k, -1, 0))
    for k in (2.5, 4.0):
        E[f'v6_{k}'] = np.where(b.ret6 >= k, 1, np.where(b.ret6 <= -k, -1, 0))
    E['brk24'] = np.where((b.c > b.hh24) & (b.c.shift() <= b.hh24.shift()), 1, np.where((b.c < b.ll24) & (b.c.shift() >= b.ll24.shift()), -1, 0))
    for k in (2.0, 3.0):
        E[f'vwap{k}'] = np.where(b.vwd >= k, 1, np.where(b.vwd <= -k, -1, 0))
    for k in (2.5, 4.0):
        E[f'rr{k}'] = np.where(b.rr >= k, sgn, 0)
    return E


def scan(sym, years=None):
    b = pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet')
    F = fwd(b, (30, 60, 120)); Y = b.index.year.values; m = b.nym.values
    E = events(b); rows = []
    vol = 'rv' in b
    for (en, d), (sn, sf), tf in itertools.product(E.items(), SESS, ('any', 'with', 'against')):
        d = np.asarray(d); msk = (d != 0) & sf(m) & ~np.isnan(F[60].values)
        if tf == 'with': msk &= (b.tr_h1.values == d)
        if tf == 'against': msk &= (b.tr_h1.values == -d)
        for vf in (('all', 'rv15') if vol else ('all',)):
            mm = msk & (b.rv.values >= 1.5) if vf == 'rv15' else msk
            n = mm.sum()
            if n < 150: continue
            r = {'sym': sym, 'ev': en, 'sess': sn, 'trend': tf, 'vol': vf, 'n': int(n), 'per_day': round(n / b.tday.nunique(), 2)}
            for h in (30, 60, 120):
                f = F[h].values[mm] * d[mm]; f = f[~np.isnan(f)]
                r[f'f{h}'] = round(f.mean(), 3); r[f't{h}'] = round(f.mean() / f.std() * np.sqrt(len(f)), 1)
            f = F[60].values[mm] * d[mm]; yy = Y[mm]
            ym = pd.Series(f).groupby(yy).mean()
            r['yrs_same_sign'] = round((np.sign(ym) == np.sign(r['f60'])).mean(), 2); r['n_yrs'] = len(ym)
            r['worst_yr'] = round(ym.min() if r['f60'] > 0 else ym.max(), 3)
            rows.append(r)
    return pd.DataFrame(rows)


if __name__ == '__main__':
    out = pd.concat([scan(s) for s in sys.argv[1].split(',')])
    out.to_csv('../results/scan_events.csv', index=False)
    good = out[(out.t60.abs() >= 3) & (out.yrs_same_sign >= 0.75)].sort_values('t60', key=abs, ascending=False)
    print('celle robuste (|t60|>=3, stesso segno in >=75% degli anni):', len(good))
    print(good.head(80).to_string(index=False))
