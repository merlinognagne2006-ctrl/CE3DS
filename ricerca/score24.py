import pandas as pd, numpy as np, sys
from score_build import prep, fit, score, sequential, evaluate
pd.set_option('display.width',250)
sym=sys.argv[1]
c=prep(pd.read_parquet(f'../results/cand24_{sym}.parquet')); IS=c[c.entry<'2022-01-01']
table,mu=fit(IS); c['score']=score(c,table)
c['sess']=pd.cut(c.nym,[-1,119,479,569,929,1109,1440],labels=['asia1','london','ny_pre','ny','ny_close','asia0'])
c['IS']=c.entry<'2022-01-01'
total_days=pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet',columns=['tday']).tday.nunique()
print('punti fascia oraria (NY):',{int(k):v for k,v in table['bucket'].items() if v!=0})
for thr in (0,10,20,30):
    s=sequential(c,thr,max_open=3); r=evaluate(s,f'thr{thr}'); r['per_day']=round(len(s)/total_days,2); print(r)
    g=s.groupby(['sess','IS'],observed=True).R.agg(['mean','count']).unstack(); g.columns=[f'{a}_{"IS" if b else "OOS"}' for a,b in g.columns]
    print((g.assign(per_day=(g.count_IS+g.count_OOS)/total_days)).round(3).to_string())
c.to_parquet(f'../results/cand24_scored_{sym}.parquet')
