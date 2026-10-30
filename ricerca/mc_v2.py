"""Monte Carlo dei challenge con le regole dell'EA (simulate giorno per giorno sui giorni storici ricampionati)."""
import numpy as np, pandas as pd, sys, warnings
warnings.filterwarnings('ignore')
from portfolio_sim import load_candidates, Pool, DEFAULT

rng = np.random.default_rng(42)


def phase(pool, days, p, target, max_days=60, prop_daily=5.0, prop_max=10.0):
    eq = 0.0
    for _ in range(max_days):
        k = days[rng.integers(len(days))]
        pnl, n, w, st = pool.day(k, dict(p, target=target), start_eq=eq)
        if pnl <= -prop_daily: return 'fail', eq + pnl
        eq += pnl
        if eq <= -prop_max: return 'fail', eq
        if eq >= target: return 'pass', eq
    return 'timeout', eq


def challenge(pool, days, p, n=2000, p1=8.0, p2=5.0, size=100_000, fee=500, months=6):
    res = []
    for _ in range(n):
        s1, _ = phase(pool, days, p, p1)
        if s1 != 'pass': res.append((0, 0.0)); continue
        s2, _ = phase(pool, days, p, p2)
        if s2 != 'pass': res.append((1, 0.0)); continue
        paid = 0.0
        for m in range(months):
            s, e = phase(pool, days, p, 1e9, max_days=21)
            if s == 'fail': break
            if e > 0: paid += e / 100 * size * 0.8
        res.append((2, paid))
    r = np.array(res)
    return dict(P1=round(100 * (r[:, 0] >= 1).mean(), 1), P1P2=round(100 * (r[:, 0] == 2).mean(), 1), EV=round(r[:, 1].mean() - fee))


if __name__ == '__main__':
    c, _ = load_candidates('IS')
    pool = Pool(c)
    oos = np.array([k for k in range(len(pool.d0)) if pool.days[k] >= np.datetime64('2022-01-01')])
    allk = np.arange(len(pool.d0))
    cfgs = [('freq alta thr10 serie+score', dict(thr=10, mode=3, kstop=0)),
            ('bilanciata thr20 serie+score', dict(thr=20, mode=3, kstop=0)),
            ('qualita thr30 score', dict(thr=30, mode=1, kstop=0)),
            ('thr20 + stop 3 perdite', dict(thr=20, mode=3, kstop=3)),
            ('thr10 + stop 4 perdite', dict(thr=10, mode=3, kstop=4)),
            ('thr20 rischio fisso', dict(thr=20, mode=0, kstop=0))]
    rows = []
    for name, extra in cfgs:
        for risk in (0.25, 0.4, 0.6):
            p = dict(DEFAULT, risk=risk, dloss=4.0, maxloss=9.0, **extra)
            r = challenge(pool, oos, p, n=1500)
            rows.append(dict(config=name, risk=risk, **r)); print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv('../results/mc_v2.csv', index=False)
    print(pd.DataFrame(rows).to_string(index=False))
