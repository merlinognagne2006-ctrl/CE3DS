import numpy as np, pandas as pd, itertools, sys, warnings; warnings.filterwarnings('ignore')
import strat_lab as L
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
sym='NASH'; b=L.F(sym)
win=(b.nym>=575)&(b.nym<660)
rows=[]
for vk in (2.5,4.0):
    d=np.where(win&(b.ret6>=vk),1,np.where(win&(b.ret6<=-vk),-1,0))
    for sl,tp,hold in itertools.product((1.5,2.5,3.5),(0,2.0,4.0,6.0),(60,120)):
        o=L.orders_from(b,d,sl_atr=sl,tp_atr=tp,hold=hold,cooldown=6)
        tr=L.run(sym,o,'now'); r=L.report(tr,f'v6>={vk} sl{sl} tp{tp} h{hold}'); rows.append(r)
    for sl,tr_a,hold in itertools.product((1.5,2.5),(1.5,2.5),(120,)):
        o=L.orders_from(b,d,sl_atr=sl,tp_atr=0,hold=hold,cooldown=6,trail_atr=tr_a,trail_on_atr=1.0)
        tr=L.run(sym,o,'now'); rows.append(L.report(tr,f'v6>={vk} sl{sl} trail{tr_a} h{hold}'))
df=pd.DataFrame(rows); print(df[['name','n','per_day','win%','avgR','grossR','costR','PF','maxDD_R','med_min','t','yrs+','worstY','R_2023+']].to_string(index=False))
