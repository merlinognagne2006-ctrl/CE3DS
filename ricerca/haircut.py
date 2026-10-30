import numpy as np, pandas as pd
import portfolio as P
out=[]
for h in [0.0,0.05,0.10,0.15]:
    pool=[[r-h for r in d] for d in P.POOL]
    for risk in [0.5,0.75,1.0]:
        out.append({'sconto_R':h,'R_medio':round(0.116-h,3),**P.challenge(pool,risk,n=3000)})
d=pd.DataFrame(out); d['EV_netto_$']=d['incasso_medio_per_challenge_$']-500; print(d.to_string()); d.to_csv('../results/challenge_haircut.csv',index=False)
