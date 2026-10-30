"""Event study: dopo una 'accelerazione' (candela M5 forte, chiusura sugli estremi, range sopra la norma)
il prezzo continua (momentum) o torna indietro? Ritorni futuri in ATR, firmati nella direzione dell'evento."""
import pandas as pd, numpy as np, sys
from feat import fwd
from engine2 import cost_of
pd.set_option('display.width',250); pd.set_option('display.max_rows',400)
def sess(nym):
    return np.select([(nym>=1080)|(nym<120),(nym>=120)&(nym<480),(nym>=480)&(nym<690),(nym>=690)&(nym<840),(nym>=840)&(nym<960)],
                     ['asia','london','ny_am','ny_mid','ny_pm'],'late')
for sym in sys.argv[1].split(','):
    b=pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet'); F=fwd(b,(30,60,120))
    b['cost_atr']=cost_of(sym,b.c)/b.atr
    b['cost_now']=(0.00006 if sym.startswith('NAS') else 0.0001)*b.c/b.atr  # costo in bps di oggi
    up=(b.body>=1.0)&(b.clv>=0.75); dn=(b.body<=-1.0)&(b.clv<=0.25)
    d=np.where(up,1,np.where(dn,-1,0)); b['d']=d
    ev={'E1 body>=1':pd.Series(d!=0,b.index),
        'E2 +rr>=2':(d!=0)&(b.rr>=2),
        'E3 +break12':(d!=0)&(b.rr>=2)&(((d>0)&(b.c>b.hh12))|((d<0)&(b.c<b.ll12))),
        'E4 +trendH1':(d!=0)&(b.rr>=2)&(((d>0)&(b.c>b.hh12))|((d<0)&(b.c<b.ll12)))&(b.tr_h1==d),
        'E4c +counterH1':(d!=0)&(b.rr>=2)&(((d>0)&(b.c>b.hh12))|((d<0)&(b.c<b.ll12)))&(b.tr_h1==-d)}
    if 'rv' in b: ev['E5 E4+rv>=1.5']=ev['E4 +trendH1']&(b.rv>=1.5)
    b['S']=sess(b.nym.values); b['Y']=b.index.year
    days=b.tday.nunique(); rows=[]
    for k,m in ev.items():
        m=np.asarray(m); x=b[m]; f=F[m].mul(x.d,axis=0)
        r={'sym':sym,'event':k,'per_day':round(len(x)/days,2),'cost_atr':round(x.cost_atr.mean(),3),'cost_now':round(x.cost_now.median(),3)}
        for h in (30,60,120): r[f'f{h}']=round(f[h].mean(),3); r[f't{h}']=round(f[h].mean()/f[h].std()*np.sqrt(f[h].count()),1)
        rows.append(r)
        if k in ('E3 +break12','E4 +trendH1'):
            g=f[60].groupby(x.S).agg(['mean','count']); print(sym,k,'f60 by session:',{s:(round(v['mean'],3),int(v['count'])) for s,v in g.iterrows()})
            gy=f[60].groupby(x.Y).mean().round(3).to_dict(); print(sym,k,'f60 by year:',gy)
    print(pd.DataFrame(rows).to_string())
