import pandas as pd, numpy as np, sys, warnings
warnings.filterwarnings('ignore')
from engine import load, resample, simulate_limit, stats
import groupb as G
pd.set_option('display.width',260); pd.set_option('display.max_rows',500)
def periods(tr, sym):
    if sym.startswith('NAS'):
        return pd.cut(tr.entry,[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-05-01'),pd.Timestamp('2026-07-15'),pd.Timestamp('2026-10-01')],labels=['P1','P2','P3']).astype(str)
    return tr.entry.dt.year.astype(str)
rows=[]; ALL={}
def run(name, sym, m1, orders):
    tr=simulate_limit(m1,orders,sym)
    if len(tr)==0: return
    ALL[(name,sym)]=tr
    st=stats(tr,name); r={'sym':sym,**{k:st[k] for k in ['name','trades','per_day','win%','avgR','grossR','PF','maxDD_R','med_min']}}
    for p,g in tr.groupby(periods(tr,sym)): r[p]=round(g.R.mean(),3)
    rows.append(r)
for sym in sys.argv[1].split(','):
    m1=load(sym); b=G.frame(m1); h1=resample(m1,'1h')
    for tp in [1,2,10]:
        for rv in [0,1.5]:
            run(f'C1 ORB5 tp{tp} rvol>={rv}',sym,m1,G.orb5(b,tp_r=tp,rvol_min=rv))
        run(f'C1 ORB15 tp{tp}',sym,m1,G.orb5(b,tp_r=tp,bars=3))
    for mult in [1.0,1.5]:
        for sk in [1.0,2.0]:
            run(f'C2 Noise m{mult} stop{sk}',sym,m1,G.noise_area(m1,mult=mult,stop_k=sk))
    for tp in [1,2,3]:
        for cf in [1,3]:
            run(f'C3 Sweep tp{tp} conf{cf}',sym,m1,G.liquidity_sweep(b,tp_r=tp,confirm=cf))
    for tp in [1,2,3]:
        for da in [1.0,1.5]:
            run(f'C4 OB tp{tp} disp{da}',sym,m1,G.order_block(b,h1,tp_r=tp,disp_atr=da))
d=pd.DataFrame(rows); print(d.to_string()); d.to_csv(f'../results/groupb_{sys.argv[1].replace(",","_")}.csv',index=False)
pd.to_pickle(ALL,f'../results/groupb_trades_{sys.argv[1].replace(",","_")}.pkl')
