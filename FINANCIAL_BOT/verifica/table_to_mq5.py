"""Riscrive la tabella dei punti di FINANCIAL_BOT.mq5 da un file JSON (stesso formato di score_table_FINAL.json).
Uso: python3 table_to_mq5.py tabella.json FINANCIAL_BOT.mq5 uscita.mq5"""
import json, re, sys
tab = json.load(open(sys.argv[1]))['table']; s = open(sys.argv[2], encoding='utf-8').read()
keys = sorted(int(k) for k in tab['bucket'])
pts = [tab['bucket'][str(k)] for k in keys]
def arr(v): return ','.join(str(x) for x in v)
k1, k2 = keys[:25], keys[25:]; p1, p2 = pts[:25], pts[25:]
s = re.sub(r'static const int key\[\] = \{[^}]*\};', 'static const int key[] = {' + arr(k1) + ',\n                             ' + arr(k2) + '};', s)
s = re.sub(r'static const int pts\[\] = \{[^}]*\};', 'static const int pts[] = {' + arr(p1) + ',\n                             ' + arr(p2) + '};', s)
def binpts(f, n): return '{' + ', '.join(str(tab[f].get(str(i), 0)) for i in range(n)) + '}'
s = re.sub(r'int P_MOM6\[\] = \{[^}]*\};', 'int P_MOM6[] = ' + binpts('mom6', 6) + ';', s)
s = re.sub(r'int P_MOM3\[\] = \{[^}]*\};', 'int P_MOM3[] = ' + binpts('mom3', 6) + ';', s)
s = re.sub(r'int P_VWD\[\]  = \{[^}]*\};', 'int P_VWD[]  = ' + binpts('vwd', 5) + ';', s)
s = re.sub(r'int P_ATRR\[\] = \{[^}]*\};', 'int P_ATRR[] = ' + binpts('atr_ratio', 6) + ';', s)
n = tab['n_trig']; s = re.sub(r'int NtrigPts\(int n\) \{[^\n]*\}', 'int NtrigPts(int n) { if(n >= 4) return %d; if(n == 3) return %d; if(n == 2) return %d; if(n == 1) return %d; return 0; }' % (n['4'], n['3'], n['2'], n['1']), s)
def tri(f, name, var='v'):
    t = tab[f]; return 'int %s(int v)%s{ return v > 0 ? %d : (v < 0 ? %d : %d); }' % (name, ' ' * (2 if name == 'TrD1Pts' else (1 if name == 'TrM15Pts' or name == 'NoisePts' else 0)), t['1'], t['-1'], t['0'])
s = re.sub(r'int TrD1Pts\(int v\)\s*\{[^\n]*\}', tri('tr_d1', 'TrD1Pts'), s)
s = re.sub(r'int TrM15Pts\(int v\)\s*\{[^\n]*\}', tri('tr_m15', 'TrM15Pts'), s)
s = re.sub(r'int NoisePts\(int v\)\s*\{[^\n]*\}', tri('noise', 'NoisePts'), s)
d = tab['dow']; s = re.sub(r'int DowPts\(int dow\) \{[^\n]*\}', 'int DowPts(int dow) { if(dow == 0) return %d; if(dow == 1) return %d; if(dow == 2) return %d; if(dow == 3) return %d; if(dow == 4) return %d; return 0; }' % tuple(d[str(i)] for i in range(5)), s)
open(sys.argv[3], 'w', encoding='utf-8').write(s)
