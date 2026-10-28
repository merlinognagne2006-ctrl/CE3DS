"""Esporta le serie M1 (UTC) in un formato binario semplice per il simulatore C++:
int64 n, poi n record {int64 t_utc_sec, double o, h, l, c, v}."""
import sys, numpy as np, pandas as pd
src, dst, vscale = sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
d = pd.read_parquet(src)
t = d.index.values.astype('datetime64[s]').astype(np.int64)
v = (d['v'].values * vscale) if ('v' in d.columns and vscale > 0) else np.ones(len(d))
rec = np.zeros(len(d), dtype=[('t', '<i8'), ('o', '<f8'), ('h', '<f8'), ('l', '<f8'), ('c', '<f8'), ('v', '<f8')])
rec['t'] = t; rec['o'] = d.o.values; rec['h'] = d.h.values; rec['l'] = d.l.values; rec['c'] = d.c.values; rec['v'] = v
assert (np.diff(t) > 0).all(), 'tempi non crescenti'
with open(dst, 'wb') as f:
    np.array([len(d)], dtype='<i8').tofile(f); rec.tofile(f)
print(dst, len(d), pd.Timestamp(t[0], unit='s'), pd.Timestamp(t[-1], unit='s'))
