"""Challenge storiche con l'EA vero: una partenza al mese, fase 1 (8%), fase 2 (5%), poi 6 mesi finanziati con payout.
Regole prop controllate dal simulatore minuto per minuto: perdita giornaliera 5%, perdita totale 10%."""
import subprocess, json, sys, os, datetime as dt, concurrent.futures as cf
import pandas as pd

H = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get('HARNESS', f'{H}/harness')
START0, START1 = os.environ.get('START0', '2011-02-01'), os.environ.get('START1', '2026-03-01')
OUT = sys.argv[1] if len(sys.argv) > 1 else f'{H}/runs/challenges'
EXTRA = sys.argv[2:]                       # es. --set InpRiskPct=0.2
os.makedirs(OUT, exist_ok=True)


def run(tag, start, extra, max_days):
    out = f'{OUT}/{tag}'
    args = [BIN, '--from', start, '--to', (dt.date.fromisoformat(start) + dt.timedelta(days=max_days + 10)).isoformat(),
            '--out', out, '--stop-on-halt', '--prop-daily', '5', '--prop-max', '10', '--max-days', str(max_days)] + extra + EXTRA
    subprocess.run(args, cwd=H, capture_output=True, check=True)
    s = json.load(open(f'{out}/summary.json'))
    t = pd.read_csv(f'{out}/trades.csv')
    s['trade_days'] = t.t_open.str[:10].nunique() if len(t) else 0
    return s


def next_start(end, phase_start, min_gap=7):
    e = dt.datetime.strptime(end[:10], '%Y.%m.%d').date() + dt.timedelta(days=3)          # nuova fase dopo ~3 giorni
    return max(e, dt.date.fromisoformat(phase_start) + dt.timedelta(days=min_gap)).isoformat()


def one(start):
    tag = start
    r = {'start': start}
    p1 = run(f'{tag}/p1', start, ['--set', 'InpTargetPct=8'], 365)
    r.update(p1_res=p1['halt'] or 'fine_dati', p1_end=p1['end'], p1_days=p1['trade_days'], p1_worst_daily=p1['worst_daily_pct'])
    if p1['halt'] != 'target': return r
    s2 = next_start(p1['end'], start)
    p2 = run(f'{tag}/p2', s2, ['--set', 'InpTargetPct=5'], 365)
    r.update(p2_start=s2, p2_res=p2['halt'] or 'fine_dati', p2_end=p2['end'], p2_days=p2['trade_days'], p2_worst_daily=p2['worst_daily_pct'])
    if p2['halt'] != 'target': return r
    s3 = next_start(p2['end'], s2)
    f = run(f'{tag}/funded', s3, ['--set', 'InpTargetPct=0', '--payout', '0.8'], 183)
    r.update(f_start=s3, f_res=f['halt'] or 'fine_dati', f_end=f['end'], payouts=f['payouts'], n_payouts=f['n_payouts'],
             f_final_profit=round((f['equity'] - f['deposit']) * 0.8, 2))
    return r


if __name__ == '__main__':
    starts = [d.date().isoformat() for d in pd.date_range(START0, START1, freq='MS')]
    if os.environ.get('ONLY'): starts = [x for x in open(os.environ['ONLY']).read().split() if x]
    rows = []
    with cf.ThreadPoolExecutor(4) as ex:
        for r in ex.map(one, starts):
            rows.append(r); print(r, flush=True)
    df = pd.DataFrame(rows); df.to_csv(f'{OUT}/challenges.csv', index=False)
