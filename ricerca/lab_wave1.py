"""Ondata 1: tutte le celle robuste della scansione trasformate in strategie con griglia di uscite."""
import numpy as np, pandas as pd, itertools, sys, warnings
warnings.filterwarnings('ignore')
import strat_lab as L
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 1000)


def W(b, a, z):
    return (b.nym >= a) & (b.nym < z)


def sig(cond_up, cond_dn):
    return np.where(cond_up, 1, np.where(cond_dn, -1, 0))


def specs(sym, b):
    S = {}
    tr = b.tr_h1
    if sym.startswith('NAS'):
        S['N1_OpenDrive_v6_3'] = (sig(W(b, 575, 660) & (b.ret6 >= 3), W(b, 575, 660) & (b.ret6 <= -3)), 'cont')
        S['N1b_OpenDrive_v3_2.5'] = (sig(W(b, 575, 660) & (b.ret3 >= 2.5), W(b, 575, 660) & (b.ret3 <= -2.5)), 'cont')
        S['N2_PreMktSpike_fade'] = (sig(W(b, 480, 565) & (b.rr >= 2.5) & (b.body > 0), W(b, 480, 565) & (b.rr >= 2.5) & (b.body < 0)), 'fade')
        S['N3_Mid_momo_v6'] = (sig(W(b, 660, 840) & (b.ret6 >= 2.5), W(b, 660, 840) & (b.ret6 <= -2.5)), 'cont')
        S['N4_Asia_momo_v6'] = (sig(((b.nym >= 1110) | (b.nym < 120)) & (b.ret6 >= 2.5), ((b.nym >= 1110) | (b.nym < 120)) & (b.ret6 <= -2.5)), 'cont')
        S['N5_Ldn_momo_trend'] = (sig(W(b, 120, 480) & (b.ret3 >= 1.5) & (tr == 1), W(b, 120, 480) & (b.ret3 <= -1.5) & (tr == -1)), 'cont')
    else:
        rv = b.rv if 'rv' in b else pd.Series(9.0, b.index)
        S['G1_OpenDrive_vwap2_rv'] = (sig(W(b, 570, 660) & (b.vwd >= 2) & (tr == 1) & (rv >= 1.5), W(b, 570, 660) & (b.vwd <= -2) & (tr == -1) & (rv >= 1.5)), 'cont')
        S['G1b_OpenDrive_v6_3'] = (sig(W(b, 575, 660) & (b.ret6 >= 3), W(b, 575, 660) & (b.ret6 <= -3)), 'cont')
        S['G2_Ldn_fade_bar_against'] = (sig(W(b, 120, 480) & (b.body >= 0.8) & (b.clv >= 0.7) & (tr == -1), W(b, 120, 480) & (b.body <= -0.8) & (b.clv <= 0.3) & (tr == 1)), 'fade')
        S['G2b_Ldn_fade_bar_any'] = (sig(W(b, 120, 480) & (b.body >= 0.8) & (b.clv >= 0.7), W(b, 120, 480) & (b.body <= -0.8) & (b.clv <= 0.3)), 'fade')
        S['G3_PM_fade_v3_against'] = (sig(W(b, 840, 960) & (b.ret3 >= 1.5) & (tr == -1), W(b, 840, 960) & (b.ret3 <= -1.5) & (tr == 1)), 'fade')
        S['G3b_PM_fade_brk24'] = (sig(W(b, 840, 960) & (b.c > b.hh24), W(b, 840, 960) & (b.c < b.ll24)), 'fade')
        S['G4_Mid_fade_bar_with'] = (sig(W(b, 660, 840) & (b.body >= 0.8) & (b.clv >= 0.7) & (tr == 1), W(b, 660, 840) & (b.body <= -0.8) & (b.clv <= 0.3) & (tr == -1)), 'fade')
        S['G4b_Mid_fade_bar_any'] = (sig(W(b, 660, 840) & (b.body >= 0.8) & (b.clv >= 0.7), W(b, 660, 840) & (b.body <= -0.8) & (b.clv <= 0.3)), 'fade')
        S['G5_Asia_fade_vwap_rv'] = (sig(((b.nym >= 1110) | (b.nym < 120)) & (b.vwd >= 2) & (tr == -1) & (rv >= 1.5), ((b.nym >= 1110) | (b.nym < 120)) & (b.vwd <= -2) & (tr == 1) & (rv >= 1.5)), 'fade')
    return S


GRID_CONT = [(sl, tp, h) for sl in (1.5, 2.5) for tp in (0, 3.0, 5.0) for h in (60, 120)]
GRID_FADE = [(sl, tp, h) for sl in (1.0, 1.5, 2.5) for tp in (0.75, 1.0, 1.5) for h in (60, 120)]

if __name__ == '__main__':
    rows = []
    for sym in sys.argv[1].split(','):
        b = L.F(sym)
        for name, (d, mode) in specs(sym, b).items():
            dd = d if mode == 'cont' else -d
            for sl, tp, h in (GRID_CONT if mode == 'cont' else GRID_FADE):
                o = L.orders_from(b, dd, sl_atr=sl, tp_atr=tp, hold=h, cooldown=6)
                tr = L.run(sym, o, 'now')
                r = L.report(tr, name); r.update({'sym': sym, 'sl': sl, 'tp': tp, 'h': h}); rows.append(r)
    df = pd.DataFrame(rows); df.to_csv('../results/lab_wave1.csv', index=False)
    cols = ['sym', 'name', 'sl', 'tp', 'h', 'n', 'per_day', 'win%', 'avgR', 'costR', 'PF', 'maxDD_R', 'med_min', 't', 'yrs+', 'worstY', 'R_2023+']
    for name, g in df.groupby('name', sort=False):
        print(g.sort_values('t', ascending=False)[cols].head(4).to_string(index=False)); print()
