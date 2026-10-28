import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import load_candidates, Pool, DEFAULT, backtest
import mc_v2 as M
from mc_v3 import run, pool, oos
B=dict(DEFAULT,thr=20,mode=3,kstop=3,risk=0.3,dloss=4.0,maxloss=9.0)
rows=[]
for name,p in [('B base (NAS+oro)',B),('B senza oro',dict(B,use_xau=0)),('B pausa 15 min dopo news rosse',dict(B,nb_after_h=15)),
               ('B pausa 30 min dopo news rosse',dict(B,nb_after_h=30)),('B protezione profitto (da +2%, max -50%)',dict(B,lock_start=2.0,lock_give=0.5)),
               ('B rischio 0.2',dict(B,risk=0.2)),('B rischio 0.25',dict(B,risk=0.25)),('B stop giorno 3%',dict(B,dloss=3.0)),('B stop 2 perdite',dict(B,kstop=2)),
               ('B senza filtro news',dict(B,nb_before=-1,nb_after_h=-1,nb_after_m=-1))]:
    d=backtest(pool,p,oos); r=run(p,n=1200)
    rows.append(dict(config=name,trades_day=round(d.n.mean(),2),pnl_day=round(d.pnl.mean(),3),sd_day=round(d.pnl.std(),2),**r)); print(rows[-1],flush=True)
pd.DataFrame(rows).to_csv('../results/mc_v4.csv',index=False)
