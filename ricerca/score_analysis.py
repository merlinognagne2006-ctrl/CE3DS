import pandas as pd, numpy as np, sys
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
c=pd.read_parquet(f'../results/cand_{sys.argv[1]}.parquet'); c['IS']=c.entry<'2022-01-01'
def tab(col,bins=None,labels=None):
    x=c.copy()
    if bins is not None: x['k']=pd.cut(x[col],bins)
    else: x['k']=x[col]
    g=x.groupby(['k','IS'],observed=True).R.agg(['mean','count']).unstack()
    g.columns=[f'{a}_{"IS" if b else "OOS"}' for a,b in g.columns]
    print(f'--- {col}'); print(g.round(3).to_string())
c['bucket']=(c.nym//30*30).map(lambda m:f'{m//60:02d}:{m%60:02d}')
tab('bucket')
for t in ['t_ret3','t_ret6','t_vwap','t_pull','t_noise','n_trig','tr_h1','tr_m15','tr_d1','noise','dow']: tab(t)
tab('mom6',[-99,0,1,2,2.5,3,4,6,99]); tab('mom3',[-99,0,1,1.5,2,2.5,3,4,99]); tab('vwd',[-99,-1,0,1,2,3,4,99])
tab('rr',[0,0.7,1,1.5,2,3,99]); tab('clv',[0,0.3,0.6,0.8,1.01]); tab('atr_ratio',[0,0.7,1,1.3,1.7,2.5,99])
