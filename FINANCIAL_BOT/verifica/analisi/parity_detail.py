import sys, json, re, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trading/research')
from score_build import BINS
RUN = sys.argv[1] if len(sys.argv) > 1 else '/home/user/trading/tools/harness/runs/full'
m = pd.read_parquet(f'{RUN}/parity_merge.parquet')
b = m[(m._merge == 'both') & (m.score_ea != m.score_r) & (m['info'].fillna('') != '')].copy()
tab = json.load(open('/home/user/trading/results/score_table_FINAL.json'))['table']
names = {'ora': 'bucket', 'segnali': 'n_trig', 'imp30': 'mom6', 'imp15': 'mom3', 'trendG': 'tr_d1', 'M15': 'tr_m15', 'noise': 'noise', 'VWAP': 'vwd', 'volat': 'atr_ratio', 'giorno': 'dow'}
def ea_parts(s):
    out = {}
    for k, v in re.findall(r'(ora|segnali \d+:|imp30|imp15|trendG|M15|noise|VWAP|volat|giorno) ?([+-]?\d+)', s):
        out[names[k.split()[0] if not k.startswith('segnali') else 'segnali']] = int(v)
    return out
def keyof(c, f):
    if BINS[f] is None: return c[f].astype(str)
    return pd.cut(c[f], BINS[f], labels=False).astype('Int64').astype(str)
for f in tab:
    b['r_' + f] = keyof(b, f).map(tab[f]).fillna(0).astype(int).values
parts = b['info'].apply(ea_parts)
cnt = {}
for i, (idx, r) in enumerate(b.iterrows()):
    p = parts.iloc[i]
    for f in tab:
        if f in p and p[f] != r['r_' + f]: cnt[f] = cnt.get(f, 0) + 1
print('differenze con dettaglio:', len(b), '| componenti diverse:', cnt)
for f in sorted(cnt, key=cnt.get, reverse=True)[:3]:
    sel = [i for i in range(len(b)) if f in parts.iloc[i] and parts.iloc[i][f] != b['r_' + f].iloc[i]]
    x = b.iloc[sel]
    print(f'\n== {f}: {len(sel)} casi; anni', x.t.dt.year.value_counts().sort_index().to_dict())
    cols = ['t', 'd', 'nym', f if f not in ('bucket',) else 'nym', 'score_r', 'score_ea']
    print(x[[c for c in dict.fromkeys(cols) if c in x.columns]].head(8).to_string())
    print('  EA:', [parts.iloc[i][f] for i in sel[:8]], ' ricerca:', list(x['r_' + f].head(8)))
