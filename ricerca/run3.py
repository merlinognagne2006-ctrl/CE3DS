import pandas as pd, sys
from engine import load, resample, simulate, split_stats
import strategies as S
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
sym=sys.argv[1]; cut=pd.Timestamp(sys.argv[2]); m1=load(sym); b=resample(m1,'5min'); rows=[]
cfg = {
 'asia->london': dict(rng=(0,7), win=(7,10)),
 'london->ny':   dict(rng=(7,12.5), win=(12.5,16)),
 'nyORB15':      dict(rng=(13.5,13.75), win=(13.75,17)),
 'nyORB30':      dict(rng=(13.5,14), win=(14,17)),
 'londonORB30':  dict(rng=(7,7.5), win=(7.5,10)),
}
for n,c in cfg.items():
    for mode,sl,tp in [('range',0.5,0.5),('range',0.5,1.0),('range',1.0,1.0),('atr',1.0,2.0),('atr',1.5,3.0),('atr',2,2)]:
        for fade in [False, True]:
            s=S.range_break(b,sl_mode=mode,sl_k=sl,tp_k=tp,**c)
            if fade: s=s.assign(d=-s.d)
            tr=simulate(m1,s,sym); a,o=split_stats(tr,cut,('FADE ' if fade else '')+n); a['p']=o['p']=f'{mode} {sl}/{tp}'; rows+=[a,o]
for sl,tp in [(1,1),(1,2),(1.5,1.5)]:
    for fade in [False,True]:
        s=S.pdhl_sweep(b,sl_atr=sl,tp_atr=tp)
        if fade: s=s.assign(d=-s.d)
        tr=simulate(m1,s,sym); a,o=split_stats(tr,cut,('FADE ' if fade else '')+'pdhl'); a['p']=o['p']=f'{sl}/{tp}'; rows+=[a,o]
df=pd.DataFrame(rows); df.to_csv(f'../results/run3_{sym}.csv',index=False)
print(df[['name','p','trades','per_day','win%','avgR','grossR','cost_R','PF','maxDD_R','med_min']].to_string())
