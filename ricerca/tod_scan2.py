"""Come tod_scan ma con orologi diversi: UTC (Asia) e Londra."""
import pandas as pd, numpy as np, sys
from feat import fwd
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
for sym in sys.argv[1].split(','):
    b=pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet'); F=fwd(b,(30,60,120)); Y=b.index.year
    b['cost_now']=(0.00006 if sym.startswith('NAS') else 0.0001)*b.c/b.atr
    rows=[]
    for clock in ('utm','ldm'):
        for ev,col,k in [('v3>=2','ret3',2.0),('v6>=3','ret6',3.0)]:
            d=np.where(b[col]>=k,1,np.where(b[col]<=-k,-1,0))
            for bk in range(0,1440,30):
                m=(d!=0)&(b[clock]>=bk)&(b[clock]<bk+30)&F[60].notna()
                if m.sum()<200: continue
                f=F[60][m]*d[m]; ym=f.groupby(Y[m]).mean()
                t=f.mean()/f.std()*np.sqrt(len(f))
                if abs(t)<2.5: continue
                rows.append({'sym':sym,'clock':clock,'ev':ev,'time':f'{bk//60:02d}:{bk%60:02d}','n':int(m.sum()),'f60':round(f.mean(),3),'t':round(t,1),
                             'yrs+':f'{(ym>0).sum()}/{len(ym)}','cost':round(b.cost_now[m].median(),3),'f30':round((F[30][m]*d[m]).mean(),3),'f120':round((F[120][m]*d[m]).mean(),3)})
    print(pd.DataFrame(rows).to_string(index=False))
