"""Momentum dopo accelerazione per fascia oraria di 30 minuti (ora di New York)."""
import pandas as pd, numpy as np, sys
from feat import fwd
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
for sym in sys.argv[1].split(','):
    b=pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet'); F=fwd(b,(30,60,120)); Y=b.index.year
    b['cost_now']=(0.00006 if sym.startswith('NAS') else 0.0001)*b.c/b.atr
    rows=[]
    for ev,col,k in [('v3>=2','ret3',2.0),('v6>=3','ret6',3.0)]:
        d=np.where(b[col]>=k,1,np.where(b[col]<=-k,-1,0))
        for bk in range(0,1440,30):
            m=(d!=0)&(b.nym>=bk)&(b.nym<bk+30)&F[60].notna()
            if m.sum()<200: continue
            f=F[60][m]*d[m]; ym=f.groupby(Y[m]).mean()
            rows.append({'sym':sym,'ev':ev,'ny':f'{bk//60:02d}:{bk%60:02d}','n':int(m.sum()),'per_yr':round(m.sum()/len(ym),0),'f60':round(f.mean(),3),
                         't':round(f.mean()/f.std()*np.sqrt(len(f)),1),'yrs+':f'{(ym>0).sum()}/{len(ym)}','cost':round(b.cost_now[m].median(),3),
                         'f30':round((F[30][m]*d[m]).mean(),3),'f120':round((F[120][m]*d[m]).mean(),3)})
    df=pd.DataFrame(rows); print(df[df.ev=='v3>=2'].to_string(index=False)); print(df[(df.ev=='v6>=3')&(df.t.abs()>=2)].to_string(index=False))
