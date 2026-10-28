"""Strategie 'a finestra oraria': momentum nelle aperture, inversione nei momenti di esaurimento.
Valutazione separata: in-sample <= 2021, out-of-sample >= 2022."""
import numpy as np, pandas as pd, itertools, sys, warnings
warnings.filterwarnings('ignore')
import strat_lab as L
pd.set_option('display.width', 270); pd.set_option('display.max_rows', 2000)

# nome, simbolo, orologio, inizio, fine (minuti), evento, soglia, modo
SPECS = [
    ('NAS_NYopen_v6', 'NASH', 'nym', 575, 660, 'ret6', 3.0, 'cont'),
    ('NAS_NYopen_v3', 'NASH', 'nym', 575, 660, 'ret3', 2.0, 'cont'),
    ('NAS_NYlate_am_v6', 'NASH', 'nym', 660, 720, 'ret6', 3.0, 'cont'),
    ('NAS_NYlunch_v6', 'NASH', 'nym', 750, 810, 'ret6', 3.0, 'cont'),
    ('NAS_AsiaOpen_v6', 'NASH', 'utm', 90, 150, 'ret6', 3.0, 'cont'),
    ('NAS_AsiaOpen_v3', 'NASH', 'utm', 90, 150, 'ret3', 2.0, 'cont'),
    ('NAS_AsiaPM_v6', 'NASH', 'utm', 330, 360, 'ret6', 3.0, 'cont'),
    ('NAS_PreNY_v3', 'NASH', 'utm', 660, 690, 'ret3', 2.0, 'cont'),
    ('NAS_LdnMid_fade_v6', 'NASH', 'ldm', 630, 660, 'ret6', 3.0, 'fade'),
    ('XAU_NYopen_v6', 'XAUD', 'nym', 600, 690, 'ret6', 3.0, 'cont'),
    ('XAU_NYopen_v3', 'XAUD', 'nym', 600, 660, 'ret3', 2.0, 'cont'),
    ('XAU_PM_fade_v6', 'XAUD', 'nym', 900, 960, 'ret6', 3.0, 'fade'),
    ('XAU_PM_fade_v3', 'XAUD', 'nym', 900, 960, 'ret3', 2.0, 'fade'),
    ('XAU_Noon_fade_v3', 'XAUD', 'nym', 720, 750, 'ret3', 2.0, 'fade'),
    ('XAU_LdnMid_fade_v3', 'XAUD', 'utm', 630, 660, 'ret3', 2.0, 'fade'),
    ('XAU_7am_fade_v3', 'XAUD', 'nym', 420, 450, 'ret3', 2.0, 'fade'),
]
GRID = {'cont': [(sl, tp, h) for sl in (1.5, 2.5) for tp in (0, 3.0) for h in (60, 120)],
        'fade': [(sl, tp, h) for sl in (1.5, 2.5) for tp in (1.0, 1.5, 2.5) for h in (60, 120)]}


def evaluate(spec, cooldown=6):
    name, sym, clock, a, z, col, k, mode = spec
    b = L.F(sym)
    w = (b[clock] >= a) & (b[clock] < z)
    d = np.where(w & (b[col] >= k), 1, np.where(w & (b[col] <= -k), -1, 0))
    if mode == 'fade': d = -d
    rows = []
    for sl, tp, h in GRID[mode]:
        o = L.orders_from(b, d, sl_atr=sl, tp_atr=tp, hold=h, cooldown=cooldown)
        tr = L.run(sym, o, 'now')
        if len(tr) == 0: continue
        IS = tr[tr.entry < '2022-01-01']; OS = tr[tr.entry >= '2022-01-01']
        y = tr.groupby(tr.entry.dt.year).R.mean()
        rows.append({'name': name, 'sl': sl, 'tp': tp, 'h': h, 'n': len(tr),
                     'per_day': round(len(tr) / tr.entry.dt.normalize().nunique() * (tr.entry.dt.normalize().nunique() / max(1, b.tday.nunique())), 2),
                     'win%': round(100 * (tr.R > 0).mean(), 1), 'R_IS': round(IS.R.mean(), 3), 't_IS': round(IS.R.mean() / IS.R.std() * np.sqrt(len(IS)), 1),
                     'R_OOS': round(OS.R.mean(), 3), 't_OOS': round(OS.R.mean() / OS.R.std() * np.sqrt(len(OS)), 1),
                     'n_OOS': len(OS), 'yrs+': f'{(y > 0).sum()}/{len(y)}', 'costR': round(tr.cost_R.mean(), 3), 'med_min': round(tr.mins.median())})
    return rows


if __name__ == '__main__':
    sel = sys.argv[1].split(',') if len(sys.argv) > 1 else None
    rows = []
    for s in SPECS:
        if sel and not any(x in s[0] for x in sel): continue
        rows += evaluate(s)
    df = pd.DataFrame(rows); df.to_csv('../results/lab_windows.csv', index=False)
    for name, g in df.groupby('name', sort=False):
        print(g.sort_values('t_IS', ascending=False).head(3).to_string(index=False)); print()
