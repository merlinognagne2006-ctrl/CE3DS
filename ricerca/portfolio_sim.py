"""Simulatore di portafoglio con le regole esatte dell'EA finale + Monte Carlo dei challenge.
Candidati: Nasdaq (punteggio 24h) + oro (shock di volatilita' in sessione NY). Ogni candidato ha gia' il suo esito (R)
simulato minuto per minuto; qui si decide QUALI prendere con le regole di portafoglio, giorno per giorno."""
import numpy as np, pandas as pd, json, sys, warnings
from numba import njit
warnings.filterwarnings('ignore')
from score_build import prep, fit, score

NEWS = '/home/user/trading/data/news.parquet'


def news_minutes(entry, ev_times):
    t = np.sort(ev_times.astype('datetime64[ns]').astype('int64')); e = entry.astype('datetime64[ns]').astype('int64')
    i = np.searchsorted(t, e)
    BIG = 4 * 10 ** 18
    prev = np.where(i > 0, t[np.maximum(i - 1, 0)], -BIG); nxt = np.where(i < len(t), t[np.minimum(i, len(t) - 1)], BIG)
    return (e - prev) / 6e10, (nxt - e) / 6e10      # minuti dall'ultima notizia, minuti alla prossima


def load_candidates(fit_on='IS'):
    nas = prep(pd.read_parquet('../results/cand24x_NASH.parquet'))
    base = nas[nas.entry < '2022-01-01'] if fit_on == 'IS' else nas
    table, mu = fit(base); nas['score'] = score(nas, table); nas['sym'] = 0
    xau = pd.read_parquet('../results/cand24x_XAUD.parquet')
    xau = xau[(xau.nym >= 480) & (xau.nym < 930) & (xau.atr_ratio >= 2.0)].copy()
    xau['score'] = np.where(xau.atr_ratio >= 2.3, 30, 20); xau['sym'] = 1
    c = pd.concat([nas[['entry', 'exit', 'R', 'score', 'sym', 'nym']], xau[['entry', 'exit', 'R', 'score', 'sym', 'nym']]])
    c = c.sort_values('entry').reset_index(drop=True)
    news = pd.read_parquet(NEWS); u = news[news.cur == 'USD']
    for imp in ('High', 'Medium'):
        a, b = news_minutes(c.entry.values, u[u.imp == imp].t.values)
        c[f'after_{imp}'] = a; c[f'before_{imp}'] = b
    c['has_news_data'] = c.entry < '2026-01-30'
    c['day'] = (c.entry + pd.Timedelta(hours=6)).dt.normalize()       # giorno di trading ~ dalle 18:00 NY
    return c, table


@njit(cache=True)
def sim_day(ent, ext, R, sc, sy, bh, ah, bm, am, nd, i0, i1, thr, relax, idle, max_tot, max_nas, max_xau, kstop,
            dloss, risk0, mode, eq_pct, maxloss, target, nb_before, nb_after_h, nb_after_m, start_eq, lock_start, lock_give, use_xau, xau_mult, xau_min_sc):
    """Ritorna: pnl del giorno in %, trade presi, vincenti, fermato (0/1/2)."""
    open_ext = np.zeros(8); open_R = np.zeros(8); open_risk = np.zeros(8); open_sym = np.zeros(8, np.int64); n_open = 0
    pnl = 0.0; ntr = 0; nwin = 0; consec = 0; streak = 0; stopped = 0; last_entry = -1e18; peak = 0.0
    for i in range(i0, i1):
        t = ent[i]
        # chiude le posizioni terminate prima di questo istante
        j = 0
        while j < n_open:
            if open_ext[j] <= t:
                r = open_R[j] * open_risk[j]; pnl += r
                if open_R[j] > 0:
                    consec = 0; streak += 1; nwin += 1
                else:
                    consec += 1; streak = 0
                open_ext[j] = open_ext[n_open - 1]; open_R[j] = open_R[n_open - 1]; open_risk[j] = open_risk[n_open - 1]; open_sym[j] = open_sym[n_open - 1]
                n_open -= 1
            else:
                j += 1
        if pnl > peak: peak = pnl
        if stopped: continue
        if pnl <= -dloss: stopped = 1; continue
        if lock_start > 0 and peak >= lock_start and pnl <= peak - lock_give * peak: stopped = 3; continue
        if sy[i] == 1 and (use_xau == 0 or sc[i] < xau_min_sc): continue
        if kstop > 0 and consec >= kstop: stopped = 2; continue
        eq_now = start_eq + pnl
        if eq_now <= -maxloss or (target > 0 and eq_now >= target): continue
        # filtro notizie
        if nd[i]:
            if bh[i] <= nb_before or bm[i] <= nb_before or ah[i] <= nb_after_h or am[i] <= nb_after_m: continue
        th = thr
        if idle > 0 and (t - last_entry) >= idle * 6e10 and relax > 0: th = thr - relax
        if sc[i] < th: continue
        if n_open >= max_tot: continue
        cnt_n = 0; cnt_x = 0
        for j in range(n_open):
            if open_sym[j] == 0: cnt_n += 1
            else: cnt_x += 1
        if sy[i] == 0 and cnt_n >= max_nas: continue
        if sy[i] == 1 and cnt_x >= max_xau: continue
        # rischio
        r = risk0
        if mode == 1:      # per punteggio
            r = risk0 * (0.5 if sc[i] < 20 else (1.0 if sc[i] < 40 else 1.5))
        elif mode == 2:    # cavalca la serie: +25% per ogni vincente consecutivo, massimo x2
            r = risk0 * min(2.0, 1.0 + 0.25 * streak)
        elif mode == 3:    # punteggio + serie + riduzione in drawdown
            r = risk0 * (0.5 if sc[i] < 20 else (1.0 if sc[i] < 40 else 1.5)) * min(2.0, 1.0 + 0.25 * streak)
            if eq_now < 0: r *= max(0.4, 1.0 + eq_now / maxloss * 1.2)
        if sy[i] == 1: r *= xau_mult
        # una perdita piena di tutte le posizioni aperte + questa non deve superare lo stop giornaliero
        risk_open = 0.0
        for j in range(n_open): risk_open += open_risk[j]
        if pnl - risk_open - r < -dloss:
            r = pnl + dloss - risk_open
            if r < 0.25 * risk0: continue
        open_ext[n_open] = ext[i]; open_R[n_open] = R[i]; open_risk[n_open] = r; open_sym[n_open] = sy[i]; n_open += 1
        ntr += 1; last_entry = t
    for j in range(n_open):
        pnl += open_R[j] * open_risk[j]
        if open_R[j] > 0: nwin += 1
    return pnl, ntr, nwin, stopped


class Pool:
    def __init__(self, c):
        c = c.sort_values(['day', 'entry']).reset_index(drop=True)
        self.c = c
        self.ent = c.entry.values.astype('datetime64[ns]').astype('int64').astype(np.float64)
        self.ext = c.exit.values.astype('datetime64[ns]').astype('int64').astype(np.float64)
        self.R = np.maximum(c.R.values.astype(np.float64), -2.5);   # protezione da picchi anomali nei dati (lo stop del server limita la perdita)
        self.sc = c.score.values.astype(np.float64); self.sy = c.sym.values.astype(np.int64)
        f = lambda k: c[k].values.astype(np.float64)
        self.bh, self.ah, self.bm, self.am = f('before_High'), f('after_High'), f('before_Medium'), f('after_Medium')
        self.nd = c.has_news_data.values.astype(np.bool_)
        days = c.day.values; brk = np.flatnonzero(np.r_[True, days[1:] != days[:-1], True])
        self.d0 = brk[:-1]; self.d1 = brk[1:]; self.days = days[self.d0]

    def day(self, k, p, start_eq=0.0):
        return sim_day(self.ent, self.ext, self.R, self.sc, self.sy, self.bh, self.ah, self.bm, self.am, self.nd,
                       self.d0[k], self.d1[k], p['thr'], p['relax'], p['idle'], p['max_tot'], p['max_nas'], p['max_xau'],
                       p['kstop'], p['dloss'], p['risk'], p['mode'], 0.0, p['maxloss'], p.get('target', 0.0),
                       p['nb_before'], p['nb_after_h'], p['nb_after_m'], start_eq, p.get('lock_start', 0.0), p.get('lock_give', 0.5), p.get('use_xau', 1), p.get('xau_mult', 1.0), p.get('xau_min_sc', 0.0))


DEFAULT = dict(thr=20, relax=0, idle=0, max_tot=3, max_nas=3, max_xau=1, kstop=3, dloss=4.0, risk=0.5, mode=0, maxloss=10.0,
               nb_before=5, nb_after_h=5, nb_after_m=5)


def backtest(pool, p, sel=None):
    """sequenza storica giorno per giorno (equity che si azzera ogni giorno, rischio in % del capitale)"""
    out = []
    ks = range(len(pool.d0)) if sel is None else sel
    for k in ks:
        pnl, n, w, st = pool.day(k, p); out.append((pool.days[k], pnl, n, w, st))
    return pd.DataFrame(out, columns=['day', 'pnl', 'n', 'wins', 'stopped'])


if __name__ == '__main__':
    c, table = load_candidates('IS')
    pool = Pool(c)
    oos = [k for k in range(len(pool.d0)) if pool.days[k] >= np.datetime64('2022-01-01')]
    ins = [k for k in range(len(pool.d0)) if pool.days[k] < np.datetime64('2022-01-01')]
    pd.set_option('display.width', 250)
    rows = []
    for thr in (10, 20, 30):
        for mode in (0, 1, 2, 3):
            for kstop in (0, 3):
                p = dict(DEFAULT, thr=thr, mode=mode, kstop=kstop)
                for lab, sel in (('IS', ins), ('OOS', oos)):
                    d = backtest(pool, p, sel)
                    rows.append(dict(set=lab, thr=thr, mode=mode, kstop=kstop, trades_day=round(d.n.mean(), 2), win=round(100 * d.wins.sum() / max(1, d.n.sum()), 1),
                                     pnl_day=round(d.pnl.mean(), 3), sd_day=round(d.pnl.std(), 3), sharpe_d=round(d.pnl.mean() / d.pnl.std(), 3),
                                     worst_day=round(d.pnl.min(), 2), p5=round(d.pnl.quantile(0.05), 2), best_day=round(d.pnl.max(), 2),
                                     stop_days=round((d.stopped > 0).mean(), 3)))
    print(pd.DataFrame(rows).to_string(index=False))
