import pandas as pd, numpy as np, sys
from engine import load, resample, atr, ema, COST
pd.set_option('display.width',250)
sym=sys.argv[1]; cut=pd.Timestamp(sys.argv[2])
m1=load(sym); b=resample(m1,'5min'); a=atr(b,14); a1h=atr(resample(m1,'1h'),14)
day=b.index.normalize()
F=pd.DataFrame(index=b.index)
F['mom60']=(b.c-b.c.shift(12))/(a*np.sqrt(12))
F['mom15']=(b.c-b.c.shift(3))/(a*np.sqrt(3))
F['mom240']=(b.c-b.c.shift(48))/(a*np.sqrt(48))
dh=b.h.groupby(day).cummax(); dl=b.l.groupby(day).cummin()
F['dayrng_pos']=(b.c-dl)/(dh-dl)
F['ema200dist']=(b.c-ema(b.c,200))/a
F['body']=(b.c-b.o)/a
F['atr_ratio']=a/atr(b,200)
fwd={k:(b.c.shift(-k)-b.c)/a for k in (6,12,24)}
sess=pd.cut(b.index.hour,[-1,6,12,20,24],labels=['asia','london','ny','late'])
cost=COST[sym]/a
for f in F.columns:
    q=pd.qcut(F[f].rank(method='first'),5,labels=False)
    for per,mask in [('IS',b.index<cut),('OOS',b.index>=cut)]:
        t=pd.DataFrame({'q':q,'s':sess,'f':fwd[12]})[mask]
        p=t.pivot_table(index='s',columns='q',values='f',aggfunc='mean',observed=True).round(3)
        print(f, per, 'fwd60 (ATR units) by quintile'); print(p.to_string())
print('avg cost in ATR units', cost.groupby(b.index<cut).mean().round(3).to_dict())
