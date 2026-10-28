"""Traduce un EA MQL5 (un solo file, senza classi) in C++ compilabile con mql5shim.hpp.

Il programma viene racchiuso in `struct MQLProgram { ... };`: come in MQL5 le funzioni possono
usarsi prima della loro definizione. Trasformazioni (dopo aver tolto i commenti):
  - #property / input group / #include <Trade/Trade.mqh>  -> rimossi
  - input T X = V;   -> const T X = V;  (modalita' 'check')   oppure  T X = V;  (modalita' 'run', modificabili)
  - "letterale"      -> string("letterale")   (in MQL5 "a" + "b" e' valido)
  - C'r,g,b'         -> colore numerico
  - parametri  const T &a[]  -> const MqlArr<T> &a ;  dichiarazioni  T a[], b[];  -> MqlArr<T> a, b;
  - array globali inizializzati  T a[] = {...};  -> static inline T a[] = {...};
Uso: python3 mq5tocpp.py file.mq5 out.hpp [check|run]
"""
import re, sys

BASE_TYPES = ['double', 'int', 'long', 'uint', 'ulong', 'char', 'uchar', 'short', 'ushort', 'bool', 'string', 'datetime',
              'color', 'float', 'MqlRates', 'MqlCalendarValue', 'MqlCalendarEvent', 'MqlDateTime', 'MqlTick']


def strip_comments(s):
    out = []; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if s.startswith('//', i):
            j = s.find('\n', i); i = n if j < 0 else j
        elif s.startswith('/*', i):
            j = s.find('*/', i + 2); j = n if j < 0 else j + 2
            out.append('\n' * s.count('\n', i, j)); i = j
        elif c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == '\\' else 1
            out.append(s[i:j + 1]); i = j + 1
        elif c == "'":
            j = i + 1
            while j < n and s[j] != "'":
                j += 2 if s[j] == '\\' else 1
            out.append(s[i:j + 1]); i = j + 1
        else:
            out.append(c); i += 1
    return ''.join(out)


def protect_strings(s):
    """sostituisce i letterali con segnaposto (le regex successive non li toccano)"""
    lits = []
    def rep(m):
        lits.append(m.group(0)); return f'__LIT{len(lits) - 1}__'
    s = re.sub(r'"(?:[^"\\\n]|\\.)*"', rep, s)
    return s, lits


def brace_depth_map(s):
    d = 0; depth = [0] * (len(s) + 1)
    for i, c in enumerate(s):
        depth[i] = d
        if c == '{': d += 1
        elif c == '}': d -= 1
    depth[len(s)] = d
    return depth


def transform(src, mode):
    s = strip_comments(src)
    lines = []
    inputs = []
    for ln in s.split('\n'):
        st = ln.strip()
        if st.startswith('#property') or re.match(r'#include\s*<Trade/Trade\.mqh>', st) or re.match(r's?input\s+group\b', st):
            lines.append(''); continue
        m = re.match(r'^(\s*)s?input\s+(\w+)\s+(\w+)\s*=\s*(.+?);\s*$', ln)
        if m:
            ind, t, name, val = m.groups(); inputs.append((t, name))
            lines.append(f'{ind}{"const " if mode == "check" else ""}{t} {name} = {val};'); continue
        lines.append(ln)
    s = '\n'.join(lines)
    s = re.sub(r"\bC'\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*'", lambda m: f'((color)({m.group(1)}|({m.group(2)}<<8)|({m.group(3)}<<16)))', s)
    s, lits = protect_strings(s)
    structs = re.findall(r'\bstruct\s+(\w+)', s)
    T = '|'.join(BASE_TYPES + structs)
    # parametri array
    s = re.sub(rf'(\bconst\s+)?\b({T})\s*&\s*(\w+)\s*\[\s*\]', lambda m: f'{m.group(1) or ""}MqlArr<{m.group(2)}> &{m.group(3)}', s)
    # dichiarazioni di array dinamici senza inizializzazione
    def decl(m):
        names = re.findall(r'(\w+)\s*\[\s*\]', m.group(2))
        return f'MqlArr<{m.group(1)}> {", ".join(names)};'
    s = re.sub(rf'\b({T})\s+((?:\w+\s*\[\s*\]\s*,\s*)*\w+\s*\[\s*\])\s*;', decl, s)
    # array inizializzati a livello globale -> membri statici
    depth = brace_depth_map(s)
    out = []; last = 0
    for m in re.finditer(rf'(?<![\w.])(static\s+)?(const\s+)?\b({T})\s+(\w+)\s*\[\s*\]\s*=\s*\{{', s):
        if depth[m.start()] == 0 and not m.group(1):
            out.append(s[last:m.start()]); out.append('static inline ' + m.group(0)); last = m.end()
    out.append(s[last:]); s = ''.join(out)
    # letterali stringa
    s = re.sub(r'__LIT(\d+)__', lambda m: f'string({lits[int(m.group(1))]})', s)
    setter = ''
    if mode == 'run':
        cases = []
        for t, name in inputs:
            if t == 'string': conv = 'string(v)'
            elif t == 'bool': conv = '(v == "true" || v == "1")'
            elif t in ('double', 'float'): conv = 'std::strtod(v.c_str(), nullptr)'
            else: conv = f'({t})std::strtoll(v.c_str(), nullptr, 10)'
            cases.append(f'      if(k == "{name}") {{ {name} = {conv}; return true; }}')
        setter = '   bool __set_input(const std::string& k, const std::string& v)\n   {\n' + '\n'.join(cases) + '\n      return false;\n   }\n'
    return '#include "mql5shim.hpp"\nstruct MQLProgram\n{\n' + s + '\n' + setter + '};\n'


if __name__ == '__main__':
    src = open(sys.argv[1], encoding='utf-8').read()
    mode = sys.argv[3] if len(sys.argv) > 3 else 'check'
    open(sys.argv[2], 'w', encoding='utf-8').write(transform(src, mode))
