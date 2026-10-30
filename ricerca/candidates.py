import pandas as pd
from engine import load, resample, simulate, stats
import strategies as S
pd.set_option('display.width',250)
M={s:load(s) for s in ['XAUUSD','XAU26','NAS100X']}
def bars(s):
    m1=M[s]; q=resample(m1,'15min'); return m1, resample(m1,'5min'), q, q, resample(m1,'1h')
C={
 'NAS_EMA12/21_T100': ('NAS100X', lambda b,h,b15,h1: S.ema_cross_momo(b,h,f=12,s=21,tn=100,sl_atr=1.5,tp_atr=2,sess=(7,20))),
 'NAS_EMA9/34_T50_24h': ('NAS100X', lambda b,h,b15,h1: S.ema_cross_momo(b,h,f=9,s=34,tn=50,sl_atr=1.5,tp_atr=3,sess=(0,24))),
 'NAS_EMA15m': ('NAS100X', lambda b,h,b15,h1: S.ema_cross_momo(b15,h1,f=12,s=21,tn=50,sl_atr=1.5,tp_atr=2,sess=(7,20))),
 'NAS_AsiaLdn_r.5/1': ('NAS100X', lambda b,h,b15,h1: S.range_break(b,rng=(0,7),win=(7,10),sl_k=.5,tp_k=1)),
 'NAS_NYORB15_r1/1': ('NAS100X', lambda b,h,b15,h1: S.range_break(b,rng=(13.5,13.75),win=(13.75,17),sl_k=1,tp_k=1)),
 'NAS_FadeLdnNY_r1/1': ('NAS100X', lambda b,h,b15,h1: S.range_break(b,rng=(7,12.5),win=(12.5,16),sl_k=1,tp_k=1).pipe(lambda s: s.assign(d=-s.d))),
 'XAU_NYORB15_r1/1': ('XAUUSD', lambda b,h,b15,h1: S.range_break(b,rng=(13.5,13.75),win=(13.75,17),sl_k=1,tp_k=1)),
 'XAU_NYORB15_r1/1_26': ('XAU26', lambda b,h,b15,h1: S.range_break(b,rng=(13.5,13.75),win=(13.75,17),sl_k=1,tp_k=1)),
 'XAU_LdnORB30_r1/1': ('XAUUSD', lambda b,h,b15,h1: S.range_break(b,rng=(7,7.5),win=(7.5,10),sl_k=1,tp_k=1)),
 'XAU_LdnNY_r1/1': ('XAUUSD', lambda b,h,b15,h1: S.range_break(b,rng=(7,12.5),win=(12.5,16),sl_k=1,tp_k=1)),
 'XAU_Donch15_vol': ('XAUUSD', lambda b,h,b15,h1: S.donchian_break(b15,n=12,sl_atr=1,tp_atr=2,atr_min_ratio=1.2)),
}
rows=[]; T={}
for n,(s,f) in C.items():
    m1,b,h,b15,h1=bars(s); tr=simulate(m1,f(b,h,b15,h1),s); T[n]=tr
    per = tr.entry.dt.to_period('Q' if 'NAS' in n or '26' in n else 'Y').astype(str) if True else None
    if 'NAS' in n: per=pd.cut(tr.entry,[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-05-01'),pd.Timestamp('2026-07-15'),pd.Timestamp('2026-10-01')],labels=['P1','P2','P3']).astype(str)
    else: per=tr.entry.dt.year.astype(str)
    r={'bot':n,**{k:stats(tr)[k] for k in ['trades','per_day','win%','avgR','PF','maxDD_R','med_min']}}
    for p,g in tr.groupby(per): r[p]=round(g.R.mean(),3)
    rows.append(r)
print(pd.DataFrame(rows).to_string())
pd.to_pickle(T,'../results/cand_trades.pkl')
