import pandas as pd, itertools, sys
from engine import load, resample, simulate, stats
import strategies as S
sym=sys.argv[1]; m1=load(sym); b=resample(m1,'5min'); h=resample(m1,'15min')
cuts=[pd.Timestamp(x) for x in sys.argv[2].split(',')]
rows=[]
for f,s,tn,sl,tp,sess in itertools.product([5,9,12],[21,34],[34,50,100],[1.0,1.5],[1.5,2.0,3.0],[(7,20),(0,24),(13,20)]):
    if f>=s: continue
    sg=S.ema_cross_momo(b,h,f=f,s=s,tn=tn,sl_atr=sl,tp_atr=tp,sess=sess,hold=120)
    tr=simulate(m1,sg,sym); r={'f':f,'s':s,'tn':tn,'sl':sl,'tp':tp,'sess':str(sess)}
    edges=[tr.entry.min()]+cuts+[tr.entry.max()+pd.Timedelta(1,'s')]
    for i in range(len(edges)-1):
        x=tr[(tr.entry>=edges[i])&(tr.entry<edges[i+1])]; r[f'R{i}']=round(x.R.mean(),3); r[f'n{i}']=len(x)
    st=stats(tr); r.update({k:st[k] for k in ['trades','per_day','win%','avgR','PF','maxDD_R','totR']})
    rows.append(r)
d=pd.DataFrame(rows); d.to_csv(f'../results/sweep_emax_{sym}.csv',index=False)
R=[c for c in d if c.startswith('R') and c[1:].isdigit()]
d['minR']=d[R].min(axis=1)
pd.set_option('display.width',250)
print('share of configs with avgR>0:', round((d.avgR>0).mean(),2), ' all periods >0:', round((d.minR>0).mean(),2))
print(d.groupby('sess')[['avgR','minR']].median()); print(d.groupby('tp')[['avgR','minR']].median()); print(d.groupby('sl')[['avgR','minR']].median()); print(d.groupby(['f','s'])[['avgR','minR']].median()); print(d.groupby('tn')[['avgR','minR']].median())
print(d.sort_values('minR',ascending=False).head(15).to_string())
