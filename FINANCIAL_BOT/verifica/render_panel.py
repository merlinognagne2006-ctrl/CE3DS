"""Disegna il pannello dell'EA dagli oggetti registrati dal simulatore (posizioni, colori e testi reali)."""
import sys, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src, out = sys.argv[1], sys.argv[2]
objs = [l.rstrip('\n').split('\t') for l in open(src, encoding='latin-1') if l.strip()]
def rgb(c):
    c = int(c); return ((c & 255) / 255, ((c >> 8) & 255) / 255, ((c >> 16) & 255) / 255)
W, H = 580, 410
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
fig.patch.set_facecolor('#0b0e14')
order = sorted(objs, key=lambda o: 0 if o[0].endswith('bg') else (1 if o[0][7:9] in ('ce', 'sa', 'mo', 'dy', 'na', 'xa', 'nw', 'pa', 'cl', 'rs') else 2))
for name, x, y, w, h, col, bg, fs, txt in order:
    x, y, w, h, fs = int(x), int(y), int(w), int(h), int(fs) or 9
    k = name[7:]
    if k == 'bg':
        ax.add_patch(Rectangle((x, y), w, h, color=rgb(bg)))
    elif k.startswith('ce'):
        ax.add_patch(Rectangle((x, y), w, h, facecolor='black', edgecolor='#666', lw=0.8)); ax.text(x + 4, y + h / 2, txt, color='white', fontsize=8.5, va='center', ha='left')
    elif k in ('save', 'mode', 'dyn', 'nas', 'xau', 'nws', 'pau', 'cls', 'rst'):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=rgb(bg), edgecolor='#999', lw=0.8)); ax.text(x + w / 2, y + h / 2, txt, color='white', fontsize=7.6, va='center', ha='center')
    else:
        ax.text(x, y, txt, color=rgb(col), fontsize=fs * 0.86, va='top', ha='left', family='DejaVu Sans')
plt.savefig(out, dpi=100, facecolor=fig.get_facecolor())
