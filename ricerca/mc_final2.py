import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import DEFAULT, backtest, load_candidates, Pool
import mc_v2 as M
FINAL=dict(DEFAULT,thr=20,mode=3,kstop=3,risk=0.25,dloss=3.0,maxloss=9.0,lock_start=2.0,lock_give=0.5,xau_mult=0.5,xau_min_sc=30,idle=90,relax=10)
def run(pool,days,p,n=1500,p1=8.0,p2=5.0,max_days=250,size=100000,fee=500):
    res=[]; d1=[]
    for _ in range(n):
        s1,_=M.phase(pool,days,p,p1,max_days=max_days)
        if s1!='pass': res.append((0,0.0)); continue
        s2,_=M.phase(pool,days,p,p2,max_days=max_days)
        if s2!='pass': res.append((1,0.0)); continue
        paid=0.0
        for m in range(6):
            s,e=M.phase(pool,days,p,1e9,max_days=21)
            if s=='fail': break
            if e>0: paid+=e/100*size*0.8
        res.append((2,paid))
    r=np.array(res); return dict(P1=round(100*(r[:,0]>=1).mean(),1),P1P2=round(100*(r[:,0]==2).mean(),1),EV=round(r[:,1].mean()-fee))
for fit_on in ('IS','ALL'):
    c,_=load_candidates(fit_on); pool=Pool(c)
    sets={'2014-2021':[k for k in range(len(pool.d0)) if pool.days[k]<np.datetime64('2022-01-01')],
          '2022-2026':[k for k in range(len(pool.d0)) if pool.days[k]>=np.datetime64('2022-01-01')],
          'tutto':list(range(len(pool.d0)))}
    for lab,ks in sets.items():
        ks=np.array(ks); d=backtest(pool,FINAL,ks)
        y=d.groupby(pd.DatetimeIndex(d.day).year).pnl.sum().round(1).to_dict()
        print(f'punteggio stimato su {fit_on} | giorni {lab}: trade/g {d.n.mean():.2f} pnl/g {d.pnl.mean():.3f}% sd {d.pnl.std():.2f} | MC',run(pool,ks,FINAL))
        if lab=='tutto': print('   rendimento per anno (% somma giornaliera, rischio 0.25%):',y)
