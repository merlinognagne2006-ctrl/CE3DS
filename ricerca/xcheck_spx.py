"""Le regole trovate sul Nasdaq, IDENTICHE, applicate a S&P 500 (e apertura europea sul CAC 40)."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
import strat_lab as L
from lab_trendday import noise_state, pullback_signals
pd.set_option('display.width',260)
def rep(sym,name,d,sl,tp,h,cd=6):
    b=L.F(sym); tr=L.run(sym,L.orders_from(b,d,sl_atr=sl,tp_atr=tp,hold=h,cooldown=cd),'now')
    IS=tr[tr.entry<'2022-01-01']; OS=tr[tr.entry>='2022-01-01']; y=tr.groupby(tr.entry.dt.year).R.mean()
    t=lambda x: round(x.R.mean()/x.R.std()*np.sqrt(len(x)),1)
    return dict(sym=sym,name=name,n=len(tr),per_day=round(len(tr)/b.tday.nunique(),2),win=round(100*(tr.R>0).mean(),1),R=round(tr.R.mean(),3),
                R_IS=round(IS.R.mean(),3),t_IS=t(IS),R_OOS=round(OS.R.mean(),3),t_OOS=t(OS),yrs=f'{(y>0).sum()}/{len(y)}',costR=round(tr.cost_R.mean(),3))
rows=[]
for sym in ('SPXH','NASH'):
    b=L.F(sym); W=lambda a,z:(b.nym>=a)&(b.nym<z); tr=b.tr_h1
    sig=lambda u,dn: np.where(u,1,np.where(dn,-1,0))
    rows.append(rep(sym,'open ret6>=4',sig(W(575,660)&(b.ret6>=4),W(575,660)&(b.ret6<=-4)),1.5,0,120))
    rows.append(rep(sym,'open ret6>=3',sig(W(575,660)&(b.ret6>=3),W(575,660)&(b.ret6<=-3)),1.5,0,120))
    rows.append(rep(sym,'open ret3>=2.5',sig(W(575,660)&(b.ret3>=2.5),W(575,660)&(b.ret3<=-2.5)),1.5,0,60))
    rows.append(rep(sym,'am vwd3 trend',sig(W(660,750)&(b.vwd>=3)&(tr==1),W(660,750)&(b.vwd<=-3)&(tr==-1)),1.5,0,120))
    rows.append(rep(sym,'lunch ret6>=3',sig(W(750,810)&(b.ret6>=3),W(750,810)&(b.ret6<=-3)),2.5,0,120))
    rows.append(rep(sym,'trendday pull m1',pullback_signals(b,noise_state(b,mult=1.0)),1.5,3.0,120,3))
b=L.F('CACH'); W=lambda a,z:(b.ldm>=a)&(b.ldm<z)
rows.append(rep('CACH','eu open ret6>=3 (8:05-9:30 Londra)',np.where(W(485,570)&(b.ret6>=3),1,np.where(W(485,570)&(b.ret6<=-3),-1,0)),1.5,0,120))
rows.append(rep('CACH','us open ret6>=3',np.where((b.nym>=575)&(b.nym<660)&(b.ret6>=3),1,np.where((b.nym>=575)&(b.nym<660)&(b.ret6<=-3),-1,0)),1.5,0,120))
print(pd.DataFrame(rows).to_string(index=False))
