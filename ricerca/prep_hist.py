"""Storico lungo HistData (gia' convertito in UTC reale da antonyaca/Aca5983): Nasdaq 100 e oro M1."""
import pandas as pd, glob
A='/tmp/claude-0/data3/antonyaca_Aca5983/data/'; D='/home/user/trading/data/'
for name,out in [('NASDAQ100','NASH'),('XAUUSD','XAUH')]:
    fs=sorted(glob.glob(A+f'{name}/{name}_M1_*.csv.gz'))
    x=pd.concat([pd.read_csv(f) for f in fs])
    x['t']=pd.to_datetime(x.time,utc=True).dt.tz_localize(None)
    x=x.rename(columns={'open':'o','high':'h','low':'l','close':'c'}).set_index('t')[['o','h','l','c']]
    x=x[~x.index.duplicated(keep='last')].sort_index()
    x.to_parquet(D+f'{out}_M1.parquet'); print(out, x.index[0], x.index[-1], len(x))
