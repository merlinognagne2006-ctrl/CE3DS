"""Combinazione consigliata: fasi 1 e 2 in modalita' Qualita', conto finanziato in modalita' Bilanciata.
Riusa le fasi di runs/challenges_q e rifa' solo i 6 mesi finanziati (stesse date di partenza) in Bilanciata."""
import os, json, glob, subprocess, datetime as dt, concurrent.futures as cf

H = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = f'{H}/runs/challenges_q', f'{H}/runs/challenges_combo'
BIN = os.environ.get('HARNESS', f'{H}/harness_final')


def one(d):
    start = os.path.basename(d); o = f'{OUT}/{start}'
    os.makedirs(o, exist_ok=True)
    for ph in ('p1', 'p2'):
        if os.path.isdir(f'{d}/{ph}') and not os.path.exists(f'{o}/{ph}'): os.symlink(f'{d}/{ph}', f'{o}/{ph}')
    f = f'{d}/funded/summary.json'
    if not os.path.exists(f): return start, None
    s = json.load(open(f)); fs = s['from']
    to = (dt.date.fromisoformat(fs) + dt.timedelta(days=193)).isoformat()
    args = [BIN, '--from', fs, '--to', to, '--out', f'{o}/funded', '--stop-on-halt', '--prop-daily', '5', '--prop-max', '10', '--max-days', '183',
            '--set', 'InpTargetPct=0', '--set', 'InpMode=1', '--payout', '0.8']
    subprocess.run(args, cwd=H, capture_output=True, check=True)
    return start, json.load(open(f'{o}/funded/summary.json'))['payouts']


if __name__ == '__main__':
    dirs = sorted(glob.glob(f'{SRC}/20??-??-??'))
    with cf.ThreadPoolExecutor(4) as ex:
        for st, p in ex.map(one, dirs): print(st, p, flush=True)
