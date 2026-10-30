"""Monte Carlo dei challenge per Gruppo A, Gruppo B e A+B (ogni gruppo ha il suo blocco 'un trade alla volta')."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from engine import stats
rng=np.random.default_rng(11)
A=pd.read_pickle('../results/cand_trades.pkl'); B=pd.read_pickle('../results/groupb_final.pkl')
GA={'NAS':['NAS_EMA12/21_T100','NAS_EMA15m','NAS_FadeLdnNY_r1/1','NAS_AsiaLdn_r.5/1'],'XAU':['XAU_NYORB15_r1/1','XAU_NYORB15_r1/1_26']}
GB={'NAS':['H1_NAS_OrderBlock','H2_NAS_Sweep','H4_NAS_NoiseArea'],'XAU':['H3_XAU_ORB30']}
def days(src,names):
    t=pd.concat([src[n] for n in names],ignore_index=True); t['day']=t.entry.dt.normalize()
    t['tod']=t.entry-t.day; t['tox']=t.exit-t.day
    return t
def lock(d):
    d=d.sort_values('tod'); out=[]; last=pd.Timedelta(-1)
    for r in d.itertuples():
        if r.tod>=last: out.append(r.R); last=r.tox
    return out
def pool(groups, n=15000):
    # per ogni gruppo: un giorno NAS a caso + un giorno XAU a caso (stesso indice di giorno per tutti i gruppi NAS)
    nas_days=sorted(set().union(*[set(g['NAS'].day) for g in groups])); xau_days=sorted(set().union(*[set(g['XAU'].day) for g in groups]))
    idx={}
    for gi,g in enumerate(groups):
        for k in ('NAS','XAU'): idx[(gi,k)]={d:x for d,x in g[k].groupby('day')}
    P=[]
    for _ in range(n):
        dn=nas_days[rng.integers(len(nas_days))]; dx=xau_days[rng.integers(len(xau_days))]; tot=[]
        for gi,g in enumerate(groups):
            parts=[idx[(gi,'NAS')].get(dn),idx[(gi,'XAU')].get(dx)]; parts=[p for p in parts if p is not None]
            if parts: tot+=lock(pd.concat(parts))
        P.append(tot)
    return P
def run_phase(g,risk,target,daily=5.,mx=10.,maxd=60,start=0.):
    eq=start
    for d in range(maxd):
        ds=eq
        for R in next(g):
            eq+=R*risk
            if eq<=ds-daily: return 'fd',eq
            if eq<=-mx: return 'fm',eq
            if eq>=target: return 'p',eq
    return 't',eq
def gen(P):
    while True: yield P[rng.integers(len(P))]
def challenge(P,risk,n=3000,size=100000):
    g=gen(P); res=[]
    for _ in range(n):
        s1,_=run_phase(g,risk,8)
        if s1!='p': res.append((0,0,0)); continue
        s2,_=run_phase(g,risk,5)
        if s2!='p': res.append((1,0,0)); continue
        paid=0; k=0
        for m in range(6):
            s,e=run_phase(g,risk,1e9,maxd=21)
            if s.startswith('f'): break
            if e>0: paid+=e/100*size*0.8; k+=1
        res.append((2,k,paid))
    r=np.array(res,float)
    return {'risk%':risk,'P1%':round(100*(r[:,0]>=1).mean(),1),'P1+P2%':round(100*(r[:,0]==2).mean(),1),'EV_netto_$':round(r[:,2].mean()-500)}
gA={'NAS':days(A,GA['NAS']),'XAU':days(A,GA['XAU'])}; gB={'NAS':days(B,GB['NAS']),'XAU':days(B,GB['XAU'])}
out=[]
for lab,gs in [('Gruppo A',[gA]),('Gruppo B',[gB]),('A + B',[gA,gB])]:
    P=pool(gs); flat=[x for d in P for x in d]
    info={'gruppo':lab,'trade/giorno':round(np.mean([len(d) for d in P]),2),'R_medio':round(np.mean(flat),3)}
    for h in [0.0,0.05]:
        Ph=[[x-h for x in d] for d in P]
        for risk in [0.5,0.75,1.0]:
            out.append({**info,'sconto_R':h,**challenge(Ph,risk)})
d=pd.DataFrame(out); print(d.to_string()); d.to_csv('../results/challenge_groups.csv',index=False)
