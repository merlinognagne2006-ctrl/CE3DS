"""Oro: accelerazioni solo nella direzione del trend giornaliero (chiusura sopra/sotto SMA20 dei giorni precedenti)."""
import numpy as np, pandas as pd, itertools, warnings; warnings.filterwarnings('ignore')
import strat_lab as L
from mine import WINDOWS, EVENTS, EXITS, event_dir, stats
pd.set_option('display.width',260)
rows=[]
for sym in ('XAUD','NASH'):
    b=L.F(sym); days=b.tday.nunique()
    dc=b.groupby('tday').c.last(); sma=dc.rolling(20).mean(); td=np.sign(dc-sma).shift(1)   # trend fino a ieri
    b['tr_d1']=b.tday.map(td).values
    for (wn,(clk,a,z)),(col,k) in itertools.product(WINDOWS.items(),EVENTS):
        w=(b[clk]>=a)&(b[clk]<z); d=event_dir(b,col,k)*w.values; d=d*(b.tr_d1.values==d)
        if (d!=0).sum()<100: continue
        for sl,tp,h in EXITS['cont']:
            tr=L.run(sym,L.orders_from(b,d,sl_atr=sl,tp_atr=tp,hold=h,cooldown=6),'now'); s=stats(tr)
            if s: rows.append(dict(sym=sym,win_=wn,ev=f'{col}{k}',sl=sl,tp=tp,h=h,per_day=round(len(tr)/days,2),**s))
df=pd.DataFrame(rows); df.to_csv('../results/mine_daily_trend.csv',index=False)
for sym,g in df.groupby('sym'):
    sel=g[(g.t_IS>=2.5)&(g.R_IS>=0.04)]
    print(sym,'tot',len(g),'selez',len(sel),'OOS medio selez',round(sel.R_OOS.mean(),3),'quota OOS>0',round((sel.R_OOS>0).mean(),2),'| OOS medio tutte',round(g.R_OOS.mean(),3))
    print(sel.sort_values('t_IS',ascending=False).head(25).to_string(index=False))
