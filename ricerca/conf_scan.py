import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings('ignore')
from engine import load, resample, simulate_limit, stats, ema
import groupb as G
pd.set_option('display.width',260)
def per(t,sym): return t.entry.dt.year if not sym.startswith('NAS') else pd.cut(t.entry,[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-05-01'),pd.Timestamp('2026-07-15'),pd.Timestamp('2026-10-01')],labels=['P1','P2','P3'])
def trend_at(h1, ts):
    e=ema(h1.c,50); e.index=e.index+pd.Timedelta(hours=1); c=h1.c.copy(); c.index=c.index+pd.Timedelta(hours=1)
    s=np.sign(c-e); return s.reindex(ts,method='ffill').values
rows=[]
for sym in sys.argv[1].split(','):
    m1=load(sym); b=G.frame(m1); h1=resample(m1,'1h')
    tests={}
    for tp in [1,2]:
        o=G.orb5(b,tp_r=tp,bars=3); tests[f'ORB15 tp{tp}']=o
        o2=o.copy(); o2=o2[trend_at(h1,pd.DatetimeIndex(o2.act))==o2.d.values]; tests[f'ORB15 tp{tp} +trendH1']=o2
        o=G.orb5(b,tp_r=tp,bars=6); tests[f'ORB30 tp{tp}']=o
        o2=o[trend_at(h1,pd.DatetimeIndex(o.act))==o.d.values]; tests[f'ORB30 tp{tp} +trendH1']=o2
    for tp in [1.5,2]:
        o=G.liquidity_sweep(b,tp_r=tp,confirm=3); tests[f'Sweep tp{tp}']=o
        tests[f'Sweep tp{tp} +trendH1']=o[trend_at(h1,pd.DatetimeIndex(o.act))==o.d.values]
        o=G.liquidity_sweep(b,tp_r=tp,confirm=3,kill=((510,660),)); tests[f'Sweep NY tp{tp} +trendH1']=o[trend_at(h1,pd.DatetimeIndex(o.act))==o.d.values]
    for k,o in tests.items():
        t=simulate_limit(m1,o.reset_index(drop=True),sym)
        if len(t)==0: continue
        st=stats(t); r={'sym':sym,'name':k,**{x:st[x] for x in ['trades','per_day','win%','avgR','grossR','PF','maxDD_R','med_min']}}
        r.update(t.groupby(per(t,sym),observed=True).R.mean().round(3).to_dict()); rows.append(r)
print(pd.DataFrame(rows).to_string())
