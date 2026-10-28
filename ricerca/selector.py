"""Selettore dei trade: 'trend detector' + 'strategy detector' + regressione logistica.
Ogni trade candidato (di qualsiasi bot) riceve un punteggio = probabilita' stimata di chiudere in profitto.
Validazione walk-forward: il modello si allena solo sui trade chiusi PRIMA del mese che deve prevedere.
Le stesse caratteristiche si calcolano in MQL5 (PPF_Selector.mqh) con i coefficienti esportati."""
import numpy as np, pandas as pd, json, warnings
warnings.filterwarnings('ignore')
from engine import load, resample, atr, ema, adx

A = pd.read_pickle('../results/cand_trades.pkl'); B = pd.read_pickle('../results/groupb_final.pkl'); C = pd.read_pickle('../results/groupc_final.pkl')
BOTS = {'B1_NAS_EMA_M5': A['NAS_EMA12/21_T100'], 'B2_NAS_EMA_M15': A['NAS_EMA15m'], 'B3_NAS_LdnRangeFade': A['NAS_FadeLdnNY_r1/1'],
        'B4_NAS_AsiaBreak': A['NAS_AsiaLdn_r.5/1'], 'B5_XAU_NY_ORB': pd.concat([A['XAU_NYORB15_r1/1'], A['XAU_NYORB15_r1/1_26']]),
        **B, **C}
GROUP = {k: ('A' if k.startswith('B') else 'B' if k.startswith('H') else 'C') for k in BOTS}
FEATS = ['trend_al', 'trend_str', 'adx', 'vol_ratio', 'vwap_al', 'daymove_al', 'bot_recent', 'hour_sin', 'hour_cos']


def symbol_features(sym):
    m1 = load(sym); b = resample(m1, '5min'); h = resample(m1, '1h')
    e50 = ema(h.c, 50); ah = atr(h, 14)
    hf = pd.DataFrame({'trend_sign': np.sign(h.c - e50), 'trend_str': (h.c - e50) / ah, 'adx': adx(h, 14)})
    hf.index = hf.index + pd.Timedelta(hours=1)  # disponibile a candela H1 chiusa
    a5 = atr(b, 14); f = pd.DataFrame(index=b.index + pd.Timedelta(minutes=5))  # disponibile a candela M5 chiusa
    f['vol_ratio'] = (a5 / atr(b, 288)).values
    day = (b.index + pd.Timedelta(hours=6)).normalize()  # giorno di trading da 18:00 NY circa (UTC 22-23)
    tp = (b.h + b.l + b.c) / 3; v = b.v if 'v' in b and b.v.sum() > 0 else pd.Series(1.0, b.index)
    vw = (tp * v).groupby(day).cumsum() / v.groupby(day).cumsum()
    f['vwap_dev'] = ((b.c - vw) / a5).values
    dop = b.o.groupby(day).transform('first')
    f['day_move'] = ((b.c - dop) / (a5 * np.sqrt(288))).values
    f = f.join(hf.reindex(f.index, method='ffill'))
    return f


def build():
    rows = []
    feats = {}
    for bot, tr in BOTS.items():
        tr = tr.copy(); tr['bot'] = bot; tr['group'] = GROUP[bot]; rows.append(tr)
    T = pd.concat(rows, ignore_index=True).sort_values('entry').reset_index(drop=True)
    T['symkey'] = np.where(T.sym.str.startswith('NAS'), 'NAS100X', 'XAU')
    out = []
    for sk, g in T.groupby('symkey'):
        if sk == 'XAU':
            f = pd.concat([symbol_features('XAUUSD'), symbol_features('XAU26')]).sort_index()
            f = f[~f.index.duplicated(keep='last')]
        else:
            f = symbol_features('NAS100X')
        x = pd.merge_asof(g.sort_values('entry'), f, left_on='entry', right_index=True, direction='backward')
        out.append(x)
    T = pd.concat(out).sort_values('entry').reset_index(drop=True)
    T['trend_al'] = T.d * T.trend_sign; T['trend_str'] = T.d * T.trend_str
    T['vwap_al'] = T.d * T.vwap_dev; T['daymove_al'] = T.d * T.day_move
    ny = T.entry.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    hr = ny.dt.hour + ny.dt.minute / 60
    T['hour_sin'] = np.sin(2 * np.pi * hr / 24); T['hour_cos'] = np.cos(2 * np.pi * hr / 24)
    # strategy detector: R medio degli ultimi 10 trade GIA' CHIUSI dello stesso bot
    T['bot_recent'] = 0.0
    for bot, g in T.groupby('bot'):
        ex = g.sort_values('exit'); rec = []
        for i, r in g.iterrows():
            closed = ex[ex.exit <= r.entry].R.tail(10)
            rec.append(closed.mean() if len(closed) >= 3 else 0.0)
        T.loc[g.index, 'bot_recent'] = rec
    T['adx'] = T.adx / 10.0  # ADX 0-100 -> 0-10, stessa scala delle altre caratteristiche
    T['y'] = (T.R > 0).astype(int)
    T[FEATS] = T[FEATS].fillna(0).clip(-5, 5)
    return T


def fit_logit(X, y, l2=1.0, it=300, lr=0.1):
    mu = X.mean(0); sd = X.std(0) + 1e-9; Z = (X - mu) / sd
    w = np.zeros(Z.shape[1]); b = np.log((y.mean() + 1e-6) / (1 - y.mean() + 1e-6))
    for _ in range(it):
        p = 1 / (1 + np.exp(-(Z @ w + b)))
        gw = Z.T @ (p - y) / len(y) + l2 * w / len(y); gb = (p - y).mean()
        w -= lr * gw * 10; b -= lr * gb * 10
    return dict(mu=mu, sd=sd, w=w, b=b)


def predict(m, X):
    return 1 / (1 + np.exp(-(((X - m['mu']) / m['sd']) @ m['w'] + m['b'])))


def walk_forward(T, min_train=300):
    T = T.copy(); T['score'] = np.nan
    months = T.entry.dt.to_period('M').unique()
    for mth in months:
        test = T.entry.dt.to_period('M') == mth
        train = T.exit < T.entry[test].min() if test.any() else None
        if train is None or train.sum() < min_train:
            continue
        m = fit_logit(T.loc[train, FEATS].values, T.loc[train, 'y'].values)
        T.loc[test, 'score'] = predict(m, T.loc[test, FEATS].values)
    return T


if __name__ == '__main__':
    pd.set_option('display.width', 250)
    T = build(); T.to_pickle('../results/all_trades_features.pkl')
    print('trade totali', len(T), T.groupby('group').size().to_dict())
    W = walk_forward(T)
    s = W.dropna(subset=['score'])
    print('trade con punteggio fuori campione:', len(s), 'dal', s.entry.min().date())
    s['q'] = pd.qcut(s.score, 5, labels=False)
    print(s.groupby('q').agg(n=('R', 'size'), winrate=('y', 'mean'), avgR=('R', 'mean'), score=('score', 'mean')).round(3))
    for th in [0.0, 0.40, 0.45, 0.50, 0.55]:
        x = s[s.score >= th]; print(f'soglia {th:.2f}: trade {len(x)} ({len(x)/len(s):.0%}), win {x.y.mean():.1%}, R medio {x.R.mean():.3f}')
    for g in 'ABC':
        x = s[s.group == g]
        print(g, 'tutti', round(x.R.mean(), 3), ' score>=mediana', round(x[x.score >= s.score.median()].R.mean(), 3))
    # modello finale su tutti i dati, esportato per MQL5
    m = fit_logit(T[FEATS].values, T.y.values)
    json.dump({'features': FEATS, 'mu': m['mu'].tolist(), 'sd': m['sd'].tolist(), 'w': m['w'].tolist(), 'b': float(m['b'])},
              open('../results/selector_model.json', 'w'), indent=1)
    print('coefficienti:', dict(zip(FEATS, np.round(m['w'], 3))), 'b', round(m['b'], 3))
    W.to_pickle('../results/all_trades_scored.pkl')
