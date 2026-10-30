import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import load_candidates, Pool, DEFAULT
import mc_v2 as M
c,_=load_candidates('IS'); pool=Pool(c)
oos=np.array([k for k in range(len(pool.d0)) if pool.days[k]>=np.datetime64('2022-01-01')])
def run(p, n=1200, p1=8.0, p2=5.0, max_days=250, size=100000, fee=500):
    res=[]; dd=[]
    for _ in range(n):
        s1,_=M.phase(pool,oos,p,p1,max_days=max_days)
        if s1!='pass': res.append((0,0.0,0)); continue
        s2,_=M.phase(pool,oos,p,p2,max_days=max_days)
        if s2!='pass': res.append((1,0.0,0)); continue
        paid=0.0
        for m in range(6):
            s,e=M.phase(pool,oos,p,1e9,max_days=21)
            if s=='fail': break
            if e>0: paid+=e/100*size*0.8
        res.append((2,paid,1))
    r=np.array(res); return dict(P1=round(100*(r[:,0]>=1).mean(),1),P1P2=round(100*(r[:,0]==2).mean(),1),EV=round(r[:,1].mean()-fee))
if __name__ == "__main__":
    rows=[]
    for name,extra in [('thr20 fisso',dict(thr=20,mode=0)),('thr20 serie+score',dict(thr=20,mode=3)),('thr10 serie+score',dict(thr=10,mode=3)),
                       ('thr30 score',dict(thr=30,mode=1)),('thr20 serie + stop3',dict(thr=20,mode=3,kstop=3))]:
        for risk in (0.3,0.5,0.75,1.0):
            r=run(dict(DEFAULT,risk=risk,dloss=4.0,maxloss=9.0,**extra)); rows.append(dict(config=name,risk=risk,**r)); print(rows[-1],flush=True)
    pd.DataFrame(rows).to_csv('../results/mc_v3.csv',index=False)
