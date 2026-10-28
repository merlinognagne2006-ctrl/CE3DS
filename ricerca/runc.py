import pandas as pd, numpy as np, sys, warnings, time; warnings.filterwarnings('ignore')
from engine import load, simulate_limit, stats
import groupb as G, groupc as C
pd.set_option('display.width',260); pd.set_option('display.max_rows',500)
def per(t,sym): return t.entry.dt.year.astype(str) if not sym.startswith('NAS') else pd.cut(t.entry,[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-05-01'),pd.Timestamp('2026-07-15'),pd.Timestamp('2026-10-01')],labels=['P1','P2','P3']).astype(str)
rows=[]; ALL={}
for sym in sys.argv[1].split(','):
    m1=load(sym); b5=G.frame(m1); b15=G.frame(m1,'15min')
    T={
     'C1 LastHalfHour':lambda: C.last_half_hour(b5),
     'C1 LastHalfHour+12th':lambda: C.last_half_hour(b5,use_12th=True),
     'C2 VWAP trend':lambda: C.vwap_trend(b5,m1),
     'C2 VWAP notrend':lambda: C.vwap_trend(b5,m1,trend=False),
     'C3 GapFade':lambda: C.gap_fade(b5),
     'C3 GapFade big':lambda: C.gap_fade(b5,min_gap_atr=1.0),
     'C4 Squeeze M15':lambda: C.ttm_squeeze(b15,m1),
     'C4 Squeeze M5':lambda: C.ttm_squeeze(b5,m1,hold=120),
     'C5 NR7 ORB':lambda: C.nr7_orb(b5),
     'C5 NR4 ORB':lambda: C.nr7_orb(b5,nr=4),
     'C6 FVG M5':lambda: C.fvg(b5,m1),
     'C6 FVG M15':lambda: C.fvg(b15,m1,valid=8,hold=240),
     'C7 RSI2 M15':lambda: C.rsi2_pullback(b15,m1),
     'C7 RSI2 M5':lambda: C.rsi2_pullback(b5,m1,hold_bars=24),
     'C8 PDHL break':lambda: C.pdhl_break(b5,m1),
     'C9 Supertrend M15':lambda: C.supertrend(b15,m1),
     'C9 Supertrend M5':lambda: C.supertrend(b5,m1,hold=120),
    }
    for k,f in T.items():
        try: o=f()
        except Exception as e: print(k,sym,'ERR',e); continue
        if len(o)==0: continue
        t=simulate_limit(m1,o.reset_index(drop=True),sym)
        if len(t)==0: continue
        ALL[(k,sym)]=t; st=stats(t)
        r={'sym':sym,'name':k,**{x:st[x] for x in ['trades','per_day','win%','avgR','grossR','PF','maxDD_R','med_min']}}
        r.update(t.groupby(per(t,sym)).R.mean().round(3).to_dict()); rows.append(r)
d=pd.DataFrame(rows); print(d.to_string()); d.to_csv('../results/groupc_scan.csv',index=False); pd.to_pickle(ALL,'../results/groupc_scan.pkl')
