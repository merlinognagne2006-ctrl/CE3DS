import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from selector import FEATS
T=pd.read_pickle('../results/all_trades_features.pkl').sort_values('entry').reset_index(drop=True)
T['mth']=T.entry.dt.to_period('M')
months=T.mth.unique(); res={}
def wf(fn, name, min_train=300):
    keep=pd.Series(False,T.index); scored=pd.Series(False,T.index)
    for m in months:
        te=T.mth==m; tr=T.exit<T.entry[te].min()
        if tr.sum()<min_train: continue
        keep[te]=fn(T[tr],T[te]); scored[te]=True
    base=T[scored]; sel=T[scored&keep]
    res[name]=dict(n_all=len(base),n_sel=len(sel),R_all=round(base.R.mean(),3),R_sel=round(sel.R.mean(),3),totR_all=round(base.R.sum(),1),totR_sel=round(sel.R.sum(),1),
                   R_rejected=round(T[scored&~keep].R.mean(),3))
# 1) ridge sull'R
def ridge(tr,te,l=50.0,q=0.5):
    X=tr[FEATS].values; mu=X.mean(0); sd=X.std(0)+1e-9; Z=(X-mu)/sd; y=tr.R.values
    w=np.linalg.solve(Z.T@Z+l*np.eye(Z.shape[1]),Z.T@(y-y.mean())); p=((te[FEATS].values-mu)/sd)@w+y.mean()
    ptr=Z@w+y.mean(); return p>=np.quantile(ptr,q)
wf(ridge,'ridge su R, top 50%')
wf(lambda a,b: ridge(a,b,q=0.3),'ridge su R, top 70%')
# 2) regime per bot: bucket ADX(terzili globali) x allineamento trend
def regime(tr,te,minn=15):
    qs=np.quantile(tr.adx,[1/3,2/3])
    def key(x): return x.bot+'_'+pd.cut(x.adx,[-1e9,qs[0],qs[1],1e9],labels=['lo','mid','hi']).astype(str)+'_'+(x.trend_al>0).astype(str)
    st=tr.assign(k=key(tr)).groupby('k').R.agg(['mean','size'])
    good=set(st[(st['size']<minn)|(st['mean']>0)].index)
    return key(te).isin(good).values
wf(regime,'regime per bot (ADX x trend)')
# 3) curva di rendimento del bot
wf(lambda tr,te: (te.bot_recent>=0).values,'bot_recent >= 0 (ultimi 10 trade)')
wf(lambda tr,te: (te.bot_recent>-0.2).values,'bot_recent > -0.2')
# 4) solo bot con R medio positivo negli ultimi 60 trade (selezione dinamica delle strategie)
def botsel(tr,te,n=60):
    m=tr.sort_values('exit').groupby('bot').R.apply(lambda x: x.tail(n).mean() if len(x)>=20 else 1.0)
    return te.bot.map(m).fillna(1.0).gt(0).values
wf(botsel,'bot con media >0 sugli ultimi 60 trade')
# 5) combinato regime + botsel
wf(lambda a,b: regime(a,b)&botsel(a,b),'regime + bot attivi')
pd.set_option('display.width',200); print(pd.DataFrame(res).T.to_string())
