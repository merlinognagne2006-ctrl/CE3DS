import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import DEFAULT, backtest
from mc_v3 import run, pool, oos
F=dict(DEFAULT,mode=3,kstop=3,risk=0.25,dloss=3.0,maxloss=9.0,lock_start=2.0,lock_give=0.5)
rows=[]
for name,p in [('Qualita thr30',dict(F,thr=30)),('Bilanciata thr20',dict(F,thr=20)),('Alta freq thr10',dict(F,thr=10)),('Massima thr0',dict(F,thr=0)),
               ('Bilanciata senza oro',dict(F,thr=20,use_xau=0)),('Bilanciata oro x0.5 solo shock>=2.3',dict(F,thr=20,xau_mult=0.5,xau_min_sc=30)),
               ('Alta freq oro x0.5 solo shock',dict(F,thr=10,xau_mult=0.5,xau_min_sc=30)),('Bilanciata rischio 0.35',dict(F,thr=20,risk=0.35)),
               ('Bilanciata inattivita 90m -10',dict(F,thr=20,idle=90,relax=10))]:
    d=backtest(pool,p,oos); r=run(p,n=1500)
    rows.append(dict(config=name,trades_day=round(d.n.mean(),2),win=round(100*d.wins.sum()/max(1,d.n.sum()),1),pnl_day=round(d.pnl.mean(),3),sd_day=round(d.pnl.std(),2),
                     best=round(d.pnl.max(),1),worst=round(d.pnl.min(),1),**r)); print(rows[-1],flush=True)
pd.DataFrame(rows).to_csv('../results/mc_v5.csv',index=False)
