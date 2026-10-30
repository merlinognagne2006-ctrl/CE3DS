import pandas as pd, warnings; warnings.filterwarnings('ignore')
from engine import load, simulate_limit, stats
import groupb as G, groupc as C
m1=load('NAS100X'); b5=G.frame(m1); b15=G.frame(m1,'15min'); T={}
T['C1_NAS_LastHalfHour']=simulate_limit(m1,C.last_half_hour(b5),'NAS100X')
T['C2_NAS_GapFade']=simulate_limit(m1,C.gap_fade(b5),'NAS100X')
T['C3_NAS_Supertrend']=simulate_limit(m1,C.supertrend(b15,m1).reset_index(drop=True),'NAS100X')
T['C4_NAS_FVG']=simulate_limit(m1,C.fvg(b5,m1).reset_index(drop=True),'NAS100X')
for k,t in T.items(): print(stats(t,k))
pd.to_pickle(T,'../results/groupc_final.pkl')
