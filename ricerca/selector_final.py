"""Selettore finale 'regime + bot attivi': flag walk-forward (per il Monte Carlo) + tabella finale per MQL5."""
import numpy as np, pandas as pd, json, warnings; warnings.filterwarnings('ignore')
T=pd.read_pickle('../results/all_trades_features.pkl').sort_values('entry').reset_index(drop=True)
T['mth']=T.entry.dt.to_period('M')
def table(tr,minn=15):
    qs=np.quantile(tr.adx,[1/3,2/3]); tr=tr.assign(b=np.digitize(tr.adx,qs),al=(tr.trend_al>0).astype(int))
    st=tr.groupby(['bot','b','al']).R.agg(['mean','size']).reset_index()
    bad={(r.bot,r.b,r.al) for r in st.itertuples() if r.size>=minn and r.mean<=0}
    return qs,bad
def regime_ok(te,qs,bad):
    b=np.digitize(te.adx,qs); al=(te.trend_al>0).astype(int).values
    return np.array([(x,y,z) not in bad for x,y,z in zip(te.bot,b,al)])
def bot_active(tr,te,n=60):
    m=tr.sort_values('exit').groupby('bot').R.apply(lambda x: x.tail(n).mean() if len(x)>=20 else 1.0)
    return te.bot.map(m).fillna(1.0).gt(0).values
T['scored']=False; T['keep']=True
for m in T.mth.unique():
    te=T.mth==m; tr=T.exit<T.entry[te].min()
    if tr.sum()<300: continue
    qs,bad=table(T[tr]); T.loc[te,'keep']=regime_ok(T[te],qs,bad)&bot_active(T[tr],T[te]); T.loc[te,'scored']=True
T.to_pickle('../results/all_trades_selected.pkl')
s=T[T.scored]
print(s.groupby('group').apply(lambda g: pd.Series({'n':len(g),'R_all':g.R.mean(),'n_sel':g.keep.sum(),'R_sel':g[g.keep].R.mean()})).round(3))
qs,bad=table(T)
json.dump({'adx_q':[q*10 for q in qs],'bad':sorted([list(map(lambda v: v if isinstance(v,str) else int(v),x)) for x in bad])},open('../results/selector_table.json','w'),indent=1)
print('soglie ADX H1:',[round(q*10,1) for q in qs]); print('combinazioni escluse:',sorted(bad))
