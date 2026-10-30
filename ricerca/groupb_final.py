"""Trade finali del Gruppo B con i parametri scelti (gli stessi degli EA)."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from engine import load, resample, simulate_limit, stats, ema
import groupb as G
def trend_at(h1, ts):
    e=ema(h1.c,50); e.index=e.index+pd.Timedelta(hours=1); c=h1.c.copy(); c.index=c.index+pd.Timedelta(hours=1)
    return np.sign(c-e).reindex(ts,method='ffill').values
def filt(o,h1): return o[trend_at(h1,pd.DatetimeIndex(o.act))==o.d.values].reset_index(drop=True)
T={}
m1=load('NAS100X'); b5=G.frame(m1); b15=G.frame(m1,'15min'); h1=resample(m1,'1h')
T['H1_NAS_OrderBlock']=simulate_limit(m1,G.order_block(b15,h1,tp_r=2,disp_atr=1.0,buf_atr=1.0,valid_bars=16),'NAS100X')
T['H2_NAS_Sweep']=simulate_limit(m1,filt(G.liquidity_sweep(b5,tp_r=2,confirm=3,kill=((510,660),)),h1),'NAS100X')
T['H4_NAS_NoiseArea']=simulate_limit(m1,G.noise_area(m1,mult=1.5,stop_k=2.0),'NAS100X')
x=[]
for s in ['XAUUSD','XAU26']:
    m=load(s); bb=G.frame(m); hh=resample(m,'1h'); x.append(simulate_limit(m,filt(G.orb5(bb,tp_r=2,bars=6),hh),s))
T['H3_XAU_ORB30']=pd.concat(x,ignore_index=True)
for k,t in T.items(): print(stats(t,k))
pd.to_pickle(T,'../results/groupb_final.pkl')
