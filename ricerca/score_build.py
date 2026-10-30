"""Punteggio deterministico (somma di punti per caratteristica) stimato SOLO sul periodo in-sample.
1 punto = +0.01R rispetto alla media in-sample. Poi selezione sequenziale: un trade alla volta per strumento."""
import numpy as np, pandas as pd, json, sys
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)

BINS = {
    'bucket': None,
    'n_trig': None,
    'mom6': [-99, 1, 2.5, 3, 4, 6, 99],
    'mom3': [-99, 1, 1.5, 2.5, 3, 4, 99],
    'tr_d1': None, 'tr_m15': None, 'noise': None,
    'vwd': [-99, 0, 2, 3, 4, 99],
    'atr_ratio': [0, 0.7, 1.0, 1.3, 1.7, 2.5, 99],
    'dow': None,
}


def prep(c):
    c = c.copy()
    c['bucket'] = (c.nym // 30 * 30).astype(int)
    c['n_trig'] = c.n_trig.clip(upper=4)
    for k in ('tr_d1', 'tr_m15', 'noise'):
        c[k] = c[k].fillna(0).astype(int)
    return c


def keyof(c, f):
    if BINS[f] is None: return c[f].astype(str)
    return pd.cut(c[f], BINS[f], labels=False).astype('Int64').astype(str)


def fit(c, clip=(-20, 30), min_n=200):
    mu = c.R.mean(); table = {}
    for f in BINS:
        k = keyof(c, f); g = c.groupby(k).R.agg(['mean', 'count'])
        pts = ((g['mean'] - mu) * 100).round().clip(*clip)
        pts[g['count'] < min_n] = 0
        table[f] = pts.astype(int).to_dict()
    return table, mu


def score(c, table):
    s = np.zeros(len(c), dtype=int)
    for f, t in table.items():
        s += keyof(c, f).map(t).fillna(0).astype(int).values
    return s


def sequential(c, thr, max_open=1, min_gap_min=0):
    """accetta in ordine temporale i candidati con punteggio >= soglia se ci sono meno di max_open posizioni aperte"""
    c = c[c.score >= thr].sort_values('entry')
    open_exits = []; keep = []; last = pd.Timestamp(0)
    for i, r in zip(c.index, c.itertuples()):
        open_exits = [x for x in open_exits if x > r.entry]
        if len(open_exits) < max_open and (r.entry - last).total_seconds() >= 60 * min_gap_min:
            keep.append(i); open_exits.append(r.exit); last = r.entry
    return c.loc[keep]


def evaluate(c, label):
    days = c.entry.dt.normalize().nunique()
    IS = c[c.entry < '2022-01-01']; OS = c[c.entry >= '2022-01-01']
    t = lambda x: round(x.R.mean() / (x.R.std() + 1e-9) * np.sqrt(len(x)), 1) if len(x) > 2 else np.nan
    y = c.groupby(c.entry.dt.year).R.mean()
    return dict(name=label, n=len(c), win=round(100 * (c.R > 0).mean(), 1), R_IS=round(IS.R.mean(), 3), t_IS=t(IS),
                R_OOS=round(OS.R.mean(), 3), t_OOS=t(OS), yrs=f'{(y > 0).sum()}/{len(y)}', med_min=round(c.mins.median()))


if __name__ == '__main__':
    sym = sys.argv[1] if len(sys.argv) > 1 else 'NASH'
    c = prep(pd.read_parquet(f'../results/cand_{sym}.parquet'))
    IS = c[c.entry < '2022-01-01']
    table, mu = fit(IS)
    c['score'] = score(c, table)
    json.dump({'mu': mu, 'table': {f: {str(k): int(v) for k, v in t.items()} for f, t in table.items()}, 'bins': BINS},
              open(f'../results/score_table_{sym}.json', 'w'), indent=1)
    c['IS'] = c.entry < '2022-01-01'
    c['sbin'] = pd.cut(c.score, [-999, -20, 0, 10, 20, 30, 40, 60, 999])
    g = c.groupby(['sbin', 'IS'], observed=True).R.agg(['mean', 'count']).unstack(); print(g.round(3).to_string())
    total_days = pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet', columns=['tday']).tday.nunique()
    rows = []
    for thr in (0, 10, 20, 30, 40, 50):
        for mo in (1, 2, 3):
            s = sequential(c, thr, max_open=mo)
            r = evaluate(s, f'thr{thr} max_open{mo}'); r['per_day'] = round(len(s) / total_days, 2); rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False))
    c.drop(columns=['sbin']).to_parquet(f'../results/cand_scored_{sym}.parquet')
