import pandas as pd, itertools, sys
from engine import load, resample, simulate, split_stats
import strategies as S
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
sym=sys.argv[1]; cut=pd.Timestamp(sys.argv[2]); m1=load(sym)
rows=[]
for tf,htf_ in [('5min','15min'),('15min','1h')]:
    b=resample(m1,tf); h=resample(m1,htf_)
    tests = {
     'pullback': lambda **k: S.trend_pullback(b,h,**k),
     'bbfade':   lambda **k: S.bb_fade(b,adx_max=30,**k),
     'donch':    lambda **k: S.donchian_break(b,n=12,**k),
     'emax':     lambda **k: S.ema_cross_momo(b,h,**k),
     'vwap':     lambda **k: S.vwap_revert(b,k=2.5,**k),
     'inside':   lambda **k: S.inside_break(b,h,**k),
    }
    for name,f in tests.items():
        for sl,tp in [(1.0,1.0),(1.5,1.5),(1.0,2.0)]:
            tr=simulate(m1,f(sl_atr=sl,tp_atr=tp,hold=120),sym)
            a,c=split_stats(tr,cut,f'{tf} {name}'); a['p']=c['p']=f'{sl}/{tp}'; rows+=[a,c]
df=pd.DataFrame(rows); df.to_csv(f'../results/run2_{sym}.csv',index=False)
print(df[['name','p','trades','per_day','win%','avgR','grossR','cost_R','PF','maxDD_R','med_min','avg_move']].to_string())
