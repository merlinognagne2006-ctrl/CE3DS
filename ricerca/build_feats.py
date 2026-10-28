import pandas as pd, time, sys
from engine2 import load
from feat import build
for sym, start in [('NASH','2014-01-01'),('XAUD','2016-09-01'),('NAS100X','2026-01-01'),('XAUH','2014-01-01')]:
    t=time.time(); m1=load(sym); m1=m1[m1.index>=start]
    b=build(m1); b.to_parquet(f'/home/user/trading/data/F5_{sym}.parquet')
    print(sym, len(b), round(time.time()-t,1),'s', b.index[0], b.index[-1], 'rv' in b)
