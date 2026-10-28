"""Monte Carlo finale: gruppi A/B/C, selettore per gruppo, rischio fisso o dinamico."""
import numpy as np, pandas as pd, itertools, warnings; warnings.filterwarnings('ignore')
rng=np.random.default_rng(5)
T=pd.read_pickle('../results/all_trades_selected.pkl'); T=T[T.scored].copy()
T['nas']=T.sym.str.startswith('NAS'); T['day']=T.entry.dt.normalize(); T['tod']=T.entry-T.day; T['tox']=T.exit-T.day
NAS={d:g for d,g in T[T.nas].groupby('day')}; XAU={d:g for d,g in T[~T.nas].groupby('day')}
nd=list(NAS); xd=list(XAU)
def day_trades(groups, sel):
    a=NAS[nd[rng.integers(len(nd))]]; b=XAU[xd[rng.integers(len(xd))]]; d=pd.concat([a,b])
    d=d[d.group.isin(groups)]
    if len(d)==0: return []
    m=d.group.map(lambda g: bool(sel.get(g,False))).astype(bool); d=d[(~m) | d.keep.astype(bool)]
    out=[]
    for g,x in d.sort_values('tod').groupby('group'):
        last=pd.Timedelta(-1)
        for r in x.itertuples():
            if r.tod>=last: out.append((r.tod,r.R)); last=r.tox
    return [R for _,R in sorted(out)]
def pool(groups,sel,n=6000): return [day_trades(groups,sel) for _ in range(n)]
def risk_of(mode,r0,eq,ds,daily,mx,target):
    if mode=='fixed': return r0
    m=1.0
    if eq<0: m=max(0.4,1-eq/-mx*1.2)        # in drawdown: riduce fino al 40%
    elif target<1e8: m=1+0.5*min(1,eq/target) # in profitto: fino a +50% ("soldi della casa")
    r=r0*m
    rem=eq-(ds-daily)                         # margine rimasto oggi
    return max(0.0,min(r,rem/2))
def phase(P,mode,r0,target,daily=5.,mx=10.,maxd=60,start=0.):
    eq=start
    for _ in range(maxd):
        ds=eq
        for R in P[rng.integers(len(P))]:
            r=risk_of(mode,r0,eq,ds,daily,mx,target)
            if r<=0: break
            eq+=R*r
            if eq<=ds-daily: return 'f',eq
            if eq<=-mx: return 'f',eq
            if eq>=target: return 'p',eq
    return 't',eq
def challenge(P,mode,r0,n=2500,size=100000):
    res=[]
    for _ in range(n):
        if phase(P,mode,r0,8)[0]!='p': res.append((0,0)); continue
        if phase(P,mode,r0,5)[0]!='p': res.append((1,0)); continue
        paid=0
        for m in range(6):
            s,e=phase(P,mode,r0,1e9,maxd=21)
            if s=='f': break
            if e>0: paid+=e/100*size*0.8
        res.append((2,paid))
    r=np.array(res); return round(100*(r[:,0]==2).mean(),1), round(r[:,1].mean()-500)
rows=[]
cfgs=[('A',{}),('B',{}),('C',{}),('B',{'B':1}),('C',{'C':1}),('A+B',{}),('A+B+C',{}),('A+B+C',{'B':1,'C':1}),('B+C',{'B':1,'C':1})]
for gs,sel in cfgs:
    groups=gs.split('+'); P=pool(groups,sel); flat=[x for d in P for x in d]
    for hair in [0.0,0.05]:
        Ph=[[x-hair for x in d] for d in P]
        for mode in ['fixed','dynamic']:
            for r0 in [0.5,0.75,1.0]:
                p,ev=challenge(Ph,mode,r0)
                rows.append(dict(gruppi=gs,selettore='+'.join(sel) or '-',trade_g=round(np.mean([len(d) for d in P]),1),R=round(np.mean(flat),3),sconto=hair,rischio=mode,r0=r0,pass_pct=p,EV=ev))
    print(rows[-1])
d=pd.DataFrame(rows); d.to_csv('../results/challenge_final.csv',index=False)
pd.set_option('display.width',220); pd.set_option('display.max_rows',300)
print(d.pivot_table(index=['gruppi','selettore','trade_g','R','rischio'],columns=['sconto','r0'],values='pass_pct').to_string())
