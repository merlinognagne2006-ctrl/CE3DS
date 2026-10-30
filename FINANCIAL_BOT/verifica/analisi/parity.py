"""Parita' tra l'EA (log del simulatore) e la ricerca (candidati cand24x + punteggio FINAL)."""
import sys, glob, re, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trading/research')
from score_build import prep, BINS
RUN = sys.argv[1] if len(sys.argv) > 1 else '/home/user/trading/tools/harness/runs/full'

def us_dst_utc(t):
    ny = t.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    return ny.apply(lambda x: x.dst() != pd.Timedelta(0)).values

def srv_to_utc(s):
    s = pd.to_datetime(s, format='%Y.%m.%d %H:%M:%S')
    u = s - pd.Timedelta(hours=2)                     # prima ipotesi: inverno
    dst = us_dst_utc(u - pd.Timedelta(hours=1))
    return s - pd.to_timedelta(np.where(dst, 3, 2), unit='h')

rows = []
for f in sorted(glob.glob(f'{RUN}/*/files/FINANCIAL_BOT_log.csv')):
    for line in open(f, encoding='latin-1'):
        p = line.rstrip('\r\n').split(';')
        if len(p) < 4 or p[1] not in ('SEGNALE_SCARTATO', 'SEGNALE_BLOCCATO', 'INGRESSO'): continue
        m = re.search(r'punteggio (-?\d+)', line)
        rows.append((p[0], p[1], p[2], p[3], int(m.group(1)) if m else None, p[-1] if p[1] != 'SEGNALE_BLOCCATO' else ''))
ea = pd.DataFrame(rows, columns=['srv', 'kind', 'sym', 'side', 'score', 'info'])
ea['t'] = srv_to_utc(ea.srv); ea['d'] = np.where(ea.side == 'BUY', 1, -1)
nas = ea[ea.sym == 'US100.cash'].drop_duplicates(['t', 'd'])
print('segnali EA Nasdaq registrati:', len(nas), '| tipi:', nas.kind.value_counts().to_dict())

tab = json.load(open('/home/user/trading/results/score_table_FINAL.json'))['table']
c = prep(pd.read_parquet('/home/user/trading/results/cand24x_NASH.parquet'))
def keyof(c, f):
    if BINS[f] is None: return c[f].astype(str)
    return pd.cut(c[f], BINS[f], labels=False).astype('Int64').astype(str)
c['score'] = 0
for f, t in tab.items(): c['score'] += keyof(c, f).map(t).fillna(0).astype(int).values
c['t'] = pd.to_datetime(c.entry)
lo, hi = nas.t.min(), nas.t.max()
cr = c[(c.t >= lo) & (c.t <= hi)]
m = cr.merge(nas, on=['t', 'd'], how='outer', suffixes=('_r', '_ea'), indicator=True)
print('periodo', lo, '->', hi)
print('candidati ricerca:', len(cr), '| in comune:', (m._merge == 'both').sum(), '| solo ricerca:', (m._merge == 'left_only').sum(), '| solo EA:', (m._merge == 'right_only').sum())
b = m[m._merge == 'both']
diff = (b.score_ea - b.score_r)
print(f'punteggio identico: {100 * (diff == 0).mean():.2f}% | |diff|<=2: {100 * (diff.abs() <= 2).mean():.2f}% | diff media {diff.mean():.3f}')
print('distribuzione differenze:', diff.value_counts().head(12).to_dict())
for thr in (10, 20, 30):
    print(f'soglia {thr}: sopra soglia ricerca {(b.score_r >= thr).sum()} vs EA {(b.score_ea >= thr).sum()}, concordanza {100 * ((b.score_r >= thr) == (b.score_ea >= thr)).mean():.2f}%')
m.to_parquet(f'{RUN}/parity_merge.parquet')
only_r = m[m._merge == 'left_only']; only_e = m[m._merge == 'right_only']
print('solo ricerca, per anno:', only_r.t.dt.year.value_counts().sort_index().to_dict())
print('solo EA, per anno:', only_e.t.dt.year.value_counts().sort_index().to_dict())
