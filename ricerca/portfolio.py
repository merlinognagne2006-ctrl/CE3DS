"""Portafoglio dei 5 bot con regola 'un solo trade aperto alla volta' + Monte Carlo dei challenge prop."""
import numpy as np, pandas as pd
from engine import stats
pd.set_option('display.width', 250)
rng = np.random.default_rng(7)

T = pd.read_pickle('../results/cand_trades.pkl')
BOTS = {'B1_NAS_EMA_M5': 'NAS_EMA12/21_T100', 'B2_NAS_EMA_M15': 'NAS_EMA15m', 'B3_NAS_LdnRangeFade': 'NAS_FadeLdnNY_r1/1',
        'B4_NAS_AsiaBreak': 'NAS_AsiaLdn_r.5/1', 'B5_XAU_NY_ORB': 'XAU_NYORB15_r1/1'}
xau = pd.concat([T['XAU_NYORB15_r1/1'], T['XAU_NYORB15_r1/1_26']])


def no_overlap(tr):
    """Regola del portafoglio: si apre un nuovo trade solo se non ce n'e' un altro aperto (qualsiasi bot)."""
    tr = tr.sort_values('entry'); keep = []; last = pd.Timestamp(0)
    for i, r in tr.iterrows():
        if r.entry >= last:
            keep.append(i); last = r.exit
    return tr.loc[keep]


nas = pd.concat([T[v].assign(bot=k) for k, v in BOTS.items() if k != 'B5_XAU_NY_ORB'], ignore_index=True)
xau = xau.assign(bot='B5_XAU_NY_ORB').reset_index(drop=True)
print('--- singoli bot ---')
print(pd.DataFrame([stats(g, b) for b, g in pd.concat([nas, xau]).groupby('bot')]).to_string())

# pool di giornate: Nasdaq (2026) e oro (2022-2026). Ogni giorno simulato = un giorno NAS + un giorno XAU
nas['day'] = nas.entry.dt.normalize(); xau['day'] = xau.entry.dt.normalize()
nas_days = [g for _, g in nas.groupby('day')]
xau_days = [g for _, g in xau.groupby('day')]
n_nas_trading_days = nas.day.nunique()


def sample_day(with_xau=True):
    a = nas_days[rng.integers(len(nas_days))].copy()
    parts = [a.assign(tod=a.entry - a.day, tox=a.exit - a.day)]
    if with_xau:
        b = xau_days[rng.integers(len(xau_days))].copy()
        parts.append(b.assign(tod=b.entry - b.day, tox=b.exit - b.day))
    d = pd.concat(parts).sort_values('tod')
    keep = []; last = pd.Timedelta(-1)
    for i, r in d.iterrows():
        if r.tod >= last:
            keep.append(r.R); last = r.tox
    return keep


# pre-campiona molte giornate per velocita'
POOL = [sample_day() for _ in range(20000)]
print('trade/giorno dopo la regola no-overlap:', round(np.mean([len(x) for x in POOL]), 2),
      ' R medio/trade:', round(np.mean([r for x in POOL for r in x]), 3))


def run_phase(day_iter, risk, target, daily_lim=5.0, max_lim=10.0, max_days=60, start=0.0):
    """Ritorna ('pass'|'fail_daily'|'fail_max'|'timeout', giorni, equity%)"""
    eq = start
    for d in range(max_days):
        day_start = eq
        for R in next(day_iter):
            eq += R * risk
            if eq <= day_start - daily_lim:
                return 'fail_daily', d + 1, eq
            if eq <= -max_lim:
                return 'fail_max', d + 1, eq
            if eq >= target:
                return 'pass', d + 1, eq
    return 'timeout', max_days, eq


def day_gen(pool):
    while True:
        yield pool[rng.integers(len(pool))]


def challenge(pool, risk, p1=8.0, p2=5.0, n=4000, funded_months=6, split=0.8, size=100_000):
    g = day_gen(pool); res = []
    for _ in range(n):
        s1, d1, _ = run_phase(g, risk, p1)
        if s1 != 'pass':
            res.append((0, 0, 0.0)); continue
        s2, d2, _ = run_phase(g, risk, p2)
        if s2 != 'pass':
            res.append((1, 0, 0.0)); continue
        # conto finanziato: ogni 21 giorni si preleva l'80% del profitto, si riparte da 0
        paid = 0.0; npay = 0; eq = 0.0; alive = True
        for m in range(funded_months):
            s, _, eq_end = run_phase(g, risk, 1e9, max_days=21, start=0.0)
            if s.startswith('fail'):
                break
            if eq_end > 0:
                paid += eq_end / 100 * size * split; npay += 1
        res.append((2, npay, paid))
    r = np.array(res)
    return {'risk%': risk, 'P1_pass%': round(100 * (r[:, 0] >= 1).mean(), 1), 'P1+P2_pass%': round(100 * (r[:, 0] == 2).mean(), 1),
            'payouts_medi_per_conto_passato': round(r[r[:, 0] == 2, 1].mean(), 2) if (r[:, 0] == 2).any() else 0,
            'incasso_medio_per_challenge_$': round(r[:, 2].mean())}


if __name__ == '__main__':
    out = []
    for risk in [0.25, 0.5, 0.75, 1.0, 1.5]:
        out.append({'strategia': '5 bot (backtest)', **challenge(POOL, risk)})
    # confronto: scalper ad alta frequenza senza vantaggio, 20 trade/giorno, TP=SL, costo 0.2R (tipico oro M1/M5 a 10-15 pips)
    for e, lab in [(-0.2, '20 trade/g, nessun vantaggio, costi 0.2R'), (0.0, '20 trade/g, nessun vantaggio, costi zero (teorico)')]:
        pool = [list(np.where(rng.random(20) < 0.5, 1.0, -1.0) + e) for _ in range(20000)]
        for risk in [0.25, 0.5, 1.0]:
            out.append({'strategia': lab, **challenge(pool, risk)})
    df = pd.DataFrame(out); df['EV_netto_per_challenge_$ (fee 500)'] = df['incasso_medio_per_challenge_$'] - 500
    print(df.to_string()); df.to_csv('../results/challenge_mc.csv', index=False)
