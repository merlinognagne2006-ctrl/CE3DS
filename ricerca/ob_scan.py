import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings('ignore')
from engine import load, resample, simulate_limit, stats, COST
import groupb as G
pd.set_option('display.width',260)
rows=[]
for sym in sys.argv[1].split(','):
    m1=load(sym); h1=resample(m1,'1h')
    for tf in ['5min','15min']:
        b=G.frame(m1,tf)
        for buf in [0.3,0.6,1.0]:
            for tp in [1.0,1.5,2.0]:
                for tr_ in [True]:
                    o=G.order_block(b,h1,tp_r=tp,disp_atr=1.0,buf_atr=buf,trend=tr_,valid_bars=48 if tf=='5min' else 16)
                    t=simulate_limit(m1,o,sym)
                    if len(t)==0: continue
                    st=stats(t); per=t.entry.dt.year if not sym.startswith('NAS') else pd.cut(t.entry,[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-05-01'),pd.Timestamp('2026-07-15'),pd.Timestamp('2026-10-01')],labels=['P1','P2','P3'])
                    r={'sym':sym,'tf':tf,'buf':buf,'tp':tp,**{k:st[k] for k in ['trades','per_day','win%','avgR','grossR','cost_R','PF','maxDD_R','med_min']}}
                    r.update(t.groupby(per,observed=True).R.mean().round(3).to_dict()); rows.append(r)
print(pd.DataFrame(rows).to_string())
