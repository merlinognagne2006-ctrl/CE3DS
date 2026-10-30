import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import load_candidates, Pool, DEFAULT, backtest
import mc_v2 as M
c,_=load_candidates('IS'); pool=Pool(c)
oos=np.array([k for k in range(len(pool.d0)) if pool.days[k]>=np.datetime64('2022-01-01')])
def outcomes(p, n=1500, p1=8.0, max_days=60):
    out=[]
    for _ in range(n):
        eq=0.0; res='timeout'; d=0
        for d in range(max_days):
            k=oos[M.rng.integers(len(oos))]; pnl,_,_,_=pool.day(k,dict(p,target=p1),start_eq=eq)
            if pnl<=-5: res='fail_daily'; break
            eq+=pnl
            if eq<=-10: res='fail_max'; break
            if eq>=p1: res='pass'; break
        out.append((res,d+1))
    o=pd.DataFrame(out,columns=['res','days']); return o.res.value_counts(normalize=True).round(3).to_dict(), round(o[o.res=='pass'].days.median(),1)
for name,extra in [('thr20 fisso 0.4',dict(thr=20,mode=0,risk=0.4)),('thr20 serie 0.4',dict(thr=20,mode=3,risk=0.4)),('thr10 serie 0.4',dict(thr=10,mode=3,risk=0.4))]:
    for dl in (2.5,3.0,4.0):
        p=dict(DEFAULT,dloss=dl,maxloss=9.0,**extra)
        d=backtest(pool,p,oos)
        print(name,'stop giorno',dl,'| media/g',round(d.pnl.mean(),3),'sd',round(d.pnl.std(),2),'giorni<-4%',round((d.pnl<-4).mean(),3),'giorni<-5%',round((d.pnl<=-5).mean(),4),
              '| esiti fase1 (60g):',outcomes(p))
