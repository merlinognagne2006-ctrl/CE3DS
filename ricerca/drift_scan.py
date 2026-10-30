"""Drift medio per ora (NY) normalizzato per ATR orario, anno per anno."""
import pandas as pd, numpy as np, sys
pd.set_option('display.width',250)
for sym in sys.argv[1].split(','):
    b=pd.read_parquet(f'/home/user/trading/data/F5_{sym}.parquet')
    h=b.resample('1h').agg({'o':'first','c':'last','atr':'mean','nym':'first'}).dropna()
    h['r']=(h.c-h.o)/(h.atr*np.sqrt(12)); h['hr']=(h.nym//60).astype(int); h['Y']=h.index.year
    g=h.groupby(['hr','Y']).r.mean().unstack()
    t=h.groupby('hr').r.apply(lambda x: x.mean()/x.std()*np.sqrt(len(x)))
    out=pd.DataFrame({'mean':h.groupby('hr').r.mean().round(3),'t':t.round(1),'yrs+':(g>0).sum(axis=1).astype(str)+'/'+g.notna().sum(axis=1).astype(str),
                      'IS':h[h.Y<=2021].groupby('hr').r.mean().round(3),'OOS':h[h.Y>=2022].groupby('hr').r.mean().round(3)})
    print(sym); print(out.to_string())
