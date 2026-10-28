"""Oro M1 2016-2026 con bid/ask e volume (Dypoi/XAUUSD_Dataset, formato Dukascopy, UTC)."""
import pandas as pd, glob, numpy as np
fs=sorted(glob.glob('/tmp/claude-0/data3/Dypoi_XAUUSD_Dataset/XAUUSD_M1_*.csv'))
x=pd.concat([pd.read_csv(f) for f in fs])
x['t']=pd.to_datetime(x.timestamp); x=x.set_index('t').sort_index(); x=x[~x.index.duplicated(keep='last')]
out=pd.DataFrame({'o':x.open_bid,'h':x.high_bid,'l':x.low_bid,'c':x.close_bid,
                  'spr':(x.close_ask-x.close_bid).astype('float32'),'v':(x.volume_bid+x.volume_ask).astype('float32')})
out=out[(out.h>=out.l)&(out.c>0)]
out.to_parquet('/home/user/trading/data/XAUD_M1.parquet')
print(out.index[0], out.index[-1], len(out))
print('spread by year (median, p90):'); print(out.spr.groupby(out.index.year).quantile([0.5,0.9]).unstack().round(3).T.to_string())
h=out.index.hour; print('median spread by UTC hour 2025:'); y=out['2025']; print(y.spr.groupby(y.index.hour).median().round(3).to_dict())
print('volume zero share', (out.v==0).mean().round(3))
