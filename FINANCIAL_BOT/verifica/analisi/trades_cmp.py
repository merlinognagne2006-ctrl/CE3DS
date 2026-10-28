"""Trade dell'EA (simulatore) contro la ricerca: R per trade negli stessi ingressi, statistiche per anno."""
import sys, glob, numpy as np, pandas as pd
RUN = sys.argv[1] if len(sys.argv) > 1 else '/home/user/trading/tools/harness/runs/full'
tr = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f'{RUN}/*/trades.csv'))], ignore_index=True)
def srv_to_utc(s):
    s = pd.to_datetime(s, format='%Y.%m.%d %H:%M:%S')
    u = (s - pd.Timedelta(hours=3)).dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    dst = u.apply(lambda x: x.dst() != pd.Timedelta(0)).values
    return s - pd.to_timedelta(np.where(dst, 3, 2), unit='h')
tr['t'] = srv_to_utc(tr.t_open); tr['tc'] = srv_to_utc(tr.t_close); tr['d'] = np.where(tr.type == 0, 1, -1)
tr['mins'] = (tr.tc - tr.t).dt.total_seconds() / 60; tr['year'] = tr.t.dt.year
tr['gold'] = tr.sym == 'XAUUSD'
tr.to_parquet(f'{RUN}/ea_trades.parquet')
g = tr.groupby(['year']).agg(n=('R', 'size'), win=('R', lambda x: round(100 * (x > 0).mean(), 1)), R=('R', 'mean'), pnl=('profit', 'sum'))
g['R'] = g.R.round(3); g['pnl%'] = (g.pnl / 1000).round(1); print(g.drop(columns='pnl').to_string())
print('oro:', tr.gold.sum(), 'trade, R medio', round(tr[tr.gold].R.mean(), 3), '| Nasdaq R medio', round(tr[~tr.gold].R.mean(), 3))
print('durata (min): mediana', tr.mins.median(), '| quartili', tr.mins.quantile([.25, .75]).tolist(), '| >= 30 min:', round(100 * (tr.mins >= 30).mean(), 1), '%')
c = pd.read_parquet('/home/user/trading/results/cand24x_NASH.parquet', columns=['entry', 'd', 'R', 'mins'])
c['t'] = pd.to_datetime(c.entry)
n = tr[~tr.gold].merge(c, on=['t', 'd'], suffixes=('_ea', '_r'))
n = n[n.t >= '2014-02-01']
print(f'\ntrade Nasdaq EA dal 2014-02: {(~tr.gold & (tr.t >= "2014-02-01")).sum()} | trovati tra i candidati della ricerca: {len(n)}')
print(f'R medio EA {n.R_ea.mean():.4f} vs ricerca {n.R_r.mean():.4f} | correlazione {np.corrcoef(n.R_ea, n.R_r)[0, 1]:.4f} | |diff|<0.05: {100 * ((n.R_ea - n.R_r).abs() < 0.05).mean():.1f}%')
print('stesso segno:', round(100 * (np.sign(n.R_ea) == np.sign(n.R_r)).mean(), 2), '%')
