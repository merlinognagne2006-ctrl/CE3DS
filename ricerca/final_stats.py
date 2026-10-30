import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from portfolio_sim import DEFAULT, backtest, load_candidates, Pool
from mc_final2 import FINAL
c,_=load_candidates('ALL'); pool=Pool(c)
modes={'Qualita (30)':dict(FINAL,thr=30),'Bilanciata (20)':FINAL,'Alta frequenza (10)':dict(FINAL,thr=10)}
rows=[]
for name,p in modes.items():
    d=backtest(pool,p); d['day']=pd.to_datetime(d.day); d=d[d.n>=0]
    eq=d.pnl.cumsum(); dd=(eq.cummax()-eq).max()
    m=d.groupby(d.day.dt.to_period('M')).pnl.sum()
    rows.append(dict(mode=name,trade_g=round(d.n.mean(),2),trade_g_med=d.n.median(),giorni_con_trade=round((d.n>0).mean(),2),win_trade=round(100*d.wins.sum()/d.n.sum(),1),
                     pnl_g=round(d.pnl.mean(),3),giorni_pos=round((d.pnl>0).mean(),2),giorno_migliore=round(d.pnl.max(),1),giorno_peggiore=round(d.pnl.min(),1),
                     maxDD=round(dd,1),mesi_pos=f'{(m>0).sum()}/{len(m)}',mese_peggiore=round(m.min(),1),stop3_giorni=round((d.stopped==2).mean(),2),lock_giorni=round((d.stopped==3).mean(),2)))
print(pd.DataFrame(rows).T.to_string())
