"""Risultati delle challenge storiche letti dai file summary.json di ogni fase (esito effettivo).
Una fase 'non conclusa' con il saldo bloccato vicino al -9% e' contata come persa (l'EA non puo' piu' operare)."""
import sys, os, json, glob, numpy as np, pandas as pd
FEE = 500


def phase(d, ph):
    f = f'{d}/{ph}/summary.json'
    if not os.path.exists(f): return None
    s = json.load(open(f))
    tr = f'{d}/{ph}/trades.csv'
    days = pd.read_csv(tr).t_open.str[:10].nunique() if os.path.exists(tr) and os.path.getsize(tr) > 100 else 0
    h = s['halt'] or 'fine_dati'
    eff = 'superata' if h == 'target' else ('persa' if h in ('maxloss', 'prop_max', 'prop_daily') or s['equity'] < 91500 else 'aperta')
    return dict(res=eff, halt=h, days=days, equity=s['equity'], payouts=s.get('payouts', 0), worst_daily=s.get('worst_daily_pct', 0), end=s['end'])


def load(root):
    rows = []
    for d in sorted(glob.glob(f'{root}/20??-??-??')):
        p1, p2, fu = phase(d, 'p1'), phase(d, 'p2'), phase(d, 'funded')
        if p1 is None: continue
        r = dict(start=pd.Timestamp(os.path.basename(d)), p1=p1['res'], p1_days=p1['days'], worst_daily=p1['worst_daily'])
        if p1['res'] == 'superata' and p2 is not None:
            r.update(p2=p2['res'], p2_days=p2['days'], worst_daily=max(r['worst_daily'], p2['worst_daily']))
            if p2['res'] == 'superata' and fu is not None:
                r.update(f=fu['res'], payouts=fu['payouts'], f_equity=fu['equity'])
        rows.append(r)
    df = pd.DataFrame(rows)
    for c in ('p2', 'f'):
        if c not in df: df[c] = np.nan
    df['payouts'] = df.get('payouts', pd.Series(0.0, index=df.index)).fillna(0)
    df['both'] = df.p2 == 'superata'
    return df


def col(x):
    f = x[x.both]
    pct = lambda m: f'{100 * m:.0f}%'
    return {'Partenze (una al mese)': f'{len(x)}',
            'Fase 1 superata': pct((x.p1 == 'superata').mean()),
            'Fase 1 persa': pct((x.p1 == 'persa').mean()),
            'Fase 1 non conclusa (12 mesi o fine dati)': pct((x.p1 == 'aperta').mean()),
            'Fase 2 superata (dopo la fase 1)': pct((x[x.p1 == 'superata'].p2 == 'superata').mean()) if (x.p1 == 'superata').any() else '-',
            '**Entrambe le fasi superate**': f'**{pct(x.both.mean())}**',
            'Giorni di trading per la fase 1 (mediana)': f'{x[x.p1 == "superata"].p1_days.median():.0f}' if (x.p1 == 'superata').any() else '-',
            'Giorni di trading per la fase 2 (mediana)': f'{x[x.both].p2_days.median():.0f}' if x.both.any() else '-',
            'Payout nei primi 6 mesi da finanziato (media)': (f'{f.payouts.mean():,.0f} $'.replace(',', '.')) if len(f) else '-',
            'Finanziati con almeno un payout in 6 mesi': pct((f.payouts > 0).mean()) if len(f) else '-',
            'Finanziati persi entro 6 mesi': pct((f.f == 'persa').mean()) if len(f) else '-',
            '**Guadagno medio per challenge (payout - 500 $)**': f'**{(x.payouts - FEE).mean():,.0f} $**'.replace(',', '.')}


def table(cols):
    keys = list(next(iter(cols.values())).keys())
    out = ['| | ' + ' | '.join(cols) + ' |', '|---|' + '---|' * len(cols)]
    for k in keys: out.append(f'| {k} | ' + ' | '.join(c[k] for c in cols.values()) + ' |')
    return '\n'.join(out)


def windows(df, k=10):
    n2 = df.both.astype(int).values; ev = (df.payouts - FEE).values
    return pd.DataFrame([(df.start.iloc[i], n2[i:i + k].sum(), ev[i:i + k].sum()) for i in range(len(df) - k + 1)], columns=['inizio', 'passate', 'netto'])


if __name__ == '__main__':
    R = '/home/user/trading/tools/harness/runs'
    m = load(f'{R}/challenges'); m.to_csv(f'{R}/challenges/esiti_effettivi.csv', index=False)
    print(table({'Tutto 2011-2026': col(m), '2011-2013 (mai visti)': col(m[m.start < '2014-01-01']),
                 '2014-2021': col(m[(m.start >= '2014-01-01') & (m.start < '2022-01-01')]), '2022-2026': col(m[m.start >= '2022-01-01'])}))
    print('perdita giornaliera peggiore vista nelle fasi:', round(m.worst_daily.max(), 2), '% (limite prop 5%)')
    w = windows(m)
    print(f'\n10 challenge comprate una al mese: entrambe le fasi superate mediana {w.passate.median():.0f}, minimo {w.passate.min()}, massimo {w.passate.max()}')
    print('distribuzione:', w.passate.value_counts().sort_index().to_dict())
    print(f'netto (payout 6 mesi - 5.000 $): mediana {w.netto.median():,.0f} $, peggiore {w.netto.min():,.0f} $ (da {w.loc[w.netto.idxmin(), "inizio"]:%Y-%m}), finestre in perdita {100 * (w.netto < 0).mean():.0f}%')
    extra = {}
    if os.path.isdir(f'{R}/challenges_is2021'):
        wf = load(f'{R}/challenges_is2021')
        if len(wf):
            print('\nWALK-FORWARD 2022-2026:'); print(table({'Punteggio stimato solo fino al 2021': col(wf), 'Punteggio finale (tutti i dati)': col(m[m.start >= '2022-01-01'])}))
    modes = {}
    for lab, d in (("Qualita'", 'challenges_q'), ('Bilanciata', 'challenges'), ('Alta frequenza', 'challenges_h')):
        if os.path.isdir(f'{R}/{d}'):
            x = load(f'{R}/{d}')
            if len(x) == len(m): modes[lab] = col(x)
    if len(modes) > 1: print("\nMODALITA' (2011-2026):"); print(table(modes))
