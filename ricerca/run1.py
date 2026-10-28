import pandas as pd, itertools, time
from engine import load, resample, simulate, split_stats
import strategies as S
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
sym='XAUUSD'; m1=load(sym); m5=resample(m1,'5min'); m15=resample(m1,'15min')
cut=pd.Timestamp('2024-01-01'); rows=[]
tests = {
 'pullback': (lambda **k: S.trend_pullback(m5,m15,**k), dict(rsi_lvl=[20,30], sl_atr=[1.0,1.5], tp_atr=[1.0,2.0])),
 'bbfade':   (lambda **k: S.bb_fade(m5,**k), dict(k=[2.0,2.5], adx_max=[20,30], sl_atr=[1.0,2.0], tp_atr=[1.0])),
 'donch':    (lambda **k: S.donchian_break(m5,**k), dict(n=[12,24], sl_atr=[1.0,1.5], tp_atr=[1.0,2.0])),
 'emax':     (lambda **k: S.ema_cross_momo(m5,m15,**k), dict(sl_atr=[1.0,1.5], tp_atr=[1.0,2.0])),
 'vwap':     (lambda **k: S.vwap_revert(m5,**k), dict(k=[1.5,2.5], sl_atr=[1.0,2.0], tp_atr=[1.0])),
 'inside':   (lambda **k: S.inside_break(m5,m15,**k), dict(sl_atr=[1.0,1.5], tp_atr=[1.0,2.0])),
}
for name,(f,grid) in tests.items():
    keys=list(grid)
    for vals in itertools.product(*grid.values()):
        kw=dict(zip(keys,vals)); tr=simulate(m1,f(**kw),sym)
        a,b=split_stats(tr,cut,name); a['p']=b['p']=str(kw); rows+= [a,b]
df=pd.DataFrame(rows); df.to_csv('../results/run1_xau.csv',index=False)
print(df[['name','p','trades','per_day','win%','avgR','PF','totR','maxDD_R','med_min','avg_move']].to_string())
