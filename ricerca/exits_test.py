"""Stessi ingressi (punteggio 24h), uscite diverse."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from candidates_nas import candidates
from score_build import prep, score, sequential, evaluate, fit
pd.set_option('display.width',250)
base=pd.read_parquet('../results/cand24_scored_NASH.parquet')
IS=base[base.entry<'2022-01-01']; table,mu=fit(IS)
total_days=pd.read_parquet('/home/user/trading/data/F5_NASH.parquet',columns=['tday']).tday.nunique()
variants={'SL1.5 noTP 120m':dict(sl=1.5),'SL1.5 TP3 120m':dict(sl=1.5,tp=3.0),'SL1.5 TP2 120m':dict(sl=1.5,tp=2.0),
          'SL2 TP2 (1:1) 120m':dict(sl=2.0,tp=2.0),'SL1.5 TP1.5 (1:1)':dict(sl=1.5,tp=1.5),'SL1.5 BE1 trail2':dict(sl=1.5,be=1.0,trail=2.0,trail_on=1.5),
          'SL2 BE1.2 TP3':dict(sl=2.0,tp=3.0,be=1.2),'SL1.5 noTP 60m':dict(sl=1.5,hold=60),'SL2.5 TP2.5':dict(sl=2.5,tp=2.5)}
rows=[]
for name,kw in variants.items():
    c=prep(candidates('NASH',start=0,end=1440,**kw)); c['score']=score(c,table)
    for thr in (10,20,30):
        s=sequential(c,thr,max_open=3); r=evaluate(s,f'{name} thr{thr}'); r['per_day']=round(len(s)/total_days,2); r['R/day_OOS']=round(r['R_OOS']*r['per_day'],3); rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))
