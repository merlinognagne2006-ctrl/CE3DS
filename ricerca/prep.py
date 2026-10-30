# Converte i dati M1 grezzi in parquet UTC
import pandas as pd, glob, sys
src = sys.argv[1]
out = '/home/user/trading/data/'
fs = sorted(glob.glob(src + '/xau/DAT_ASCII_XAUUSD_M1_*.csv'))
x = pd.concat([pd.read_csv(f, sep=';', header=None, names=['t','o','h','l','c','v']) for f in fs])
x['t'] = pd.to_datetime(x['t'], format='%Y%m%d %H%M%S') + pd.Timedelta(hours=5)  # HistData = EST fisso (UTC-5)
x = x.drop(columns='v').drop_duplicates('t').set_index('t').sort_index()
x.to_parquet(out + 'XAUUSD_M1.parquet'); print('XAU', x.index[0], x.index[-1], len(x))
n = pd.read_csv(src + '/getdata-finance_nas100-1m-ohlcv-index-historical-data/NAS100_1m.csv')
n['t'] = pd.to_datetime(n['datetime'], utc=True).dt.tz_localize(None)
n = n.rename(columns={'open':'o','high':'h','low':'l','close':'c'})[['t','o','h','l','c']].drop_duplicates('t').set_index('t').sort_index()
n.to_parquet(out + 'NAS100_M1.parquet'); print('NAS', n.index[0], n.index[-1], len(n))
