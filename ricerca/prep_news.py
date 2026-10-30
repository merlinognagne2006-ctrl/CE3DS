"""Calendario notizie storico (UTC): ForexFactory high+medium 2010-2023 (spoluan, UTC+8) + high 2020-2026/01 (ehsanrs2, UTC)."""
import pandas as pd, glob
s=pd.concat([pd.read_csv(f) for f in sorted(glob.glob('/tmp/claude-0/data3/spoluan_forex-factory-scraper/datasets/*.csv'))])
s=s[s.Impact.isin(['High','Medium']) & s.Time.str.contains(r'\d', na=False)]
s['t']=pd.to_datetime(s['Combined DateTime'])-pd.Timedelta(hours=8)
a=s[['t','Currency','Impact','Event']].rename(columns={'Currency':'cur','Impact':'imp','Event':'ev'})
h=pd.read_csv('/tmp/claude-0/data3/ehsanrs2_forexfactory-scraper/high_impact_events_calendar.csv')
h['t']=pd.to_datetime(h.DateTime,utc=True).dt.tz_localize(None)
b=h[['t','Currency','Event']].rename(columns={'Currency':'cur','Event':'ev'}); b['imp']='High'
n=pd.concat([a,b]).drop_duplicates(['t','cur','ev']).sort_values('t').reset_index(drop=True)
n.to_parquet('/home/user/trading/data/news.parquet')
u=n[n.cur=='USD']
print(len(n), n.t.min(), n.t.max()); print(u.groupby([u.t.dt.year,'imp']).size().unstack().fillna(0).astype(int).to_string())
