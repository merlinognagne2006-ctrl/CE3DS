"""Ricerca ampia con hold-out: le regole si scelgono SOLO sul periodo in-sample (<=2021),
poi si guarda il risultato out-of-sample (>=2022) dei sopravvissuti.
Famiglie: impulso (ret3/ret6), rottura di massimi/minimi, distanza dal VWAP; per finestra oraria;
continuazione o inversione; con o senza filtro di trend H1."""
import numpy as np, pandas as pd, itertools, sys, warnings, time
warnings.filterwarnings('ignore')
import strat_lab as L
pd.set_option('display.width', 280); pd.set_option('display.max_rows', 3000)

WINDOWS = {  # nome: (orologio, inizio, fine)
    'asia_tokyo': ('utm', 0, 90), 'asia_hk': ('utm', 90, 210), 'asia_pm': ('utm', 300, 420),
    'ldn_open': ('ldm', 480, 600), 'ldn_mid': ('ldm', 600, 720), 'ldn_pm': ('ldm', 720, 810),
    'ny_pre': ('nym', 480, 570), 'ny_open': ('nym', 570, 660), 'ny_am': ('nym', 660, 750),
    'ny_lunch': ('nym', 750, 840), 'ny_pm': ('nym', 840, 930), 'ny_close': ('nym', 930, 990),
    'eve': ('nym', 1110, 1260),
}
EVENTS = [('ret3', 1.5), ('ret3', 2.5), ('ret6', 2.5), ('ret6', 4.0), ('brk24', 0), ('vwd', 2.0), ('vwd', 3.0)]
EXITS = {'cont': [(1.5, 0, 60), (1.5, 0, 120), (2.5, 3.0, 120)], 'fade': [(2.5, 1.5, 60), (2.5, 1.0, 120), (1.5, 1.5, 60)]}


def event_dir(b, col, k):
    if col == 'brk24':
        return np.where((b.c > b.hh24) & (b.c.shift() <= b.hh24.shift()), 1, np.where((b.c < b.ll24) & (b.c.shift() >= b.ll24.shift()), -1, 0))
    x = b[col]
    return np.where(x >= k, 1, np.where(x <= -k, -1, 0))


def stats(tr):
    if len(tr) < 30: return None
    IS = tr[tr.entry < '2022-01-01']; OS = tr[tr.entry >= '2022-01-01']
    if len(IS) < 30 or len(OS) < 20: return None
    f = lambda x: (round(x.R.mean(), 3), round(x.R.mean() / (x.R.std() + 1e-9) * np.sqrt(len(x)), 1))
    (ri, ti), (ro, to) = f(IS), f(OS)
    y = IS.groupby(IS.entry.dt.year).R.mean()
    return dict(n_IS=len(IS), R_IS=ri, t_IS=ti, yrsIS=f'{(y > 0).sum()}/{len(y)}', n_OOS=len(OS), R_OOS=ro, t_OOS=to,
                win=round(100 * (tr.R > 0).mean(), 1), costR=round(tr.cost_R.mean(), 3), med_min=round(tr.mins.median()))


def mine(sym):
    b = L.F(sym); days = b.tday.nunique(); rows = []; t0 = time.time()
    for (wn, (clk, a, z)), (col, k), trf, mode in itertools.product(WINDOWS.items(), EVENTS, ('any', 'with'), ('cont', 'fade')):
        w = (b[clk] >= a) & (b[clk] < z)
        d = event_dir(b, col, k) * w.values
        if trf == 'with': d = d * (b.tr_h1.values == d)
        if mode == 'fade': d = -d
        if (d != 0).sum() < 100: continue
        for sl, tp, h in EXITS[mode]:
            o = L.orders_from(b, d, sl_atr=sl, tp_atr=tp, hold=h, cooldown=6)
            tr = L.run(sym, o, 'now'); s = stats(tr)
            if s is None: continue
            rows.append(dict(sym=sym, win_=wn, ev=f'{col}{k}', trend=trf, mode=mode, sl=sl, tp=tp, h=h, per_day=round(len(tr) / days, 2), **s))
    print(sym, 'combinazioni', len(rows), 'tempo', round(time.time() - t0), 's')
    return pd.DataFrame(rows)


if __name__ == '__main__':
    df = pd.concat([mine(s) for s in sys.argv[1].split(',')])
    df.to_csv('../results/mine.csv', index=False)
    for sym, g in df.groupby('sym'):
        sel = g[(g.t_IS >= 2.5) & (g.R_IS >= 0.04)]
        print(f'\n{sym}: combinazioni {len(g)}, selezionate in-sample {len(sel)}; R medio OOS dei selezionati {sel.R_OOS.mean():.3f}, '
              f'quota con OOS>0 {(sel.R_OOS > 0).mean():.2f}; (tutte le combinazioni: OOS medio {g.R_OOS.mean():.3f})')
        print(sel.sort_values('t_IS', ascending=False).head(60).to_string(index=False))
