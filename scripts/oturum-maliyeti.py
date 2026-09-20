#!/usr/bin/env python3
"""Bir oturumun o ana kadarki harcamasini transcript'ten OLCER (tahmin etmez).

Kullanim:  python3 ~/.claude/scripts/oturum-maliyeti.py <oturum-id>
           python3 ~/.claude/scripts/oturum-maliyeti.py <oturum-id> --json

Oturum id'si scratchpad yolunun son parcasidir; Claude kendi oturumununkini
sistem prompt'undaki "Scratchpad Directory" satirindan okur.

NEDEN VAR: modes/otonom-kosum.md "her turda o ana kadarki harcama yazilir" ve
"~$50 asinca durur" diyor. Olculmeyen bir tavan tavan degildir — sonraki
oturum "asagi yukari" der ve gecer. Bu betik ~/.claude/projects/**/*.jsonl
icindeki her asistan mesajinin `usage` alanini toplar ve liste fiyatiyla
carpar. Ayni yontem 05/09/2026'da 33 oturumu olcmek icin kullanildi.

⚠️ Fiyatlar API LISTE fiyatidir ve abonelik faturasi DEGILDIR; tuketim
vekilidir. Fable 5.1'de cache okumasi %2,5 (digerlerinde %10) — canli
dokumandan dogrulandi (05/09/2026). Yeni model cikinca tabloyu guncelle.
"""
import glob, json, os, sys, collections

# model: (girdi $/M, cikti $/M, cache-okuma orani). cache-yazma = girdi x 1.25
FIYAT = {
    'claude-fable-5-1': (10, 50, .025),
    'claude-fable-5':   (10, 50, .10),
    'claude-opus-5':    (5,  25, .10),
    'claude-opus-4-8':  (5,  25, .10),
    'claude-sonnet-5':  (2,  10, .10),
    'claude-haiku-4-5': (1,   5, .10),
}
VARSAYILAN = (5, 25, .10)   # bilinmeyen model: Opus fiyati, ustune not dus

def olc(sid):
    ana = alt = 0.0; model = collections.Counter(); bilinmeyen = set(); mesaj = 0
    kok = os.path.expanduser('~/.claude/projects')
    for f in glob.glob(os.path.join(kok, '**', '*.jsonl'), recursive=True):
        with open(f, errors='ignore') as fh:
            for line in fh:
                try: d = json.loads(line)
                except Exception: continue
                if d.get('sessionId') != sid: continue
                m = d.get('message') or {}; u = m.get('usage')
                if not u: continue
                mo = m.get('model', '?')
                if mo not in FIYAT: bilinmeyen.add(mo)
                i, o, cr = FIYAT.get(mo, VARSAYILAN)
                c = (u.get('input_tokens', 0) * i
                     + u.get('cache_creation_input_tokens', 0) * i * 1.25
                     + u.get('cache_read_input_tokens', 0) * i * cr
                     + u.get('output_tokens', 0) * o) / 1e6
                model[mo] += c
                if d.get('isSidechain'): alt += c
                else: ana += c; mesaj += 1
    return dict(oturum=sid, ana=round(ana, 2), subagent=round(alt, 2),
                toplam=round(ana + alt, 2), asistan_mesaji=mesaj,
                model={k: round(v, 2) for k, v in model.most_common()},
                bilinmeyen_model=sorted(bilinmeyen))

def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        print(__doc__); return 2
    r = olc(sys.argv[1])
    if r['asistan_mesaji'] == 0:
        print(f"✗ oturum bulunamadi: {r['oturum']}"); return 1
    if '--json' in sys.argv:
        print(json.dumps(r, ensure_ascii=False)); return 0
    print(f"oturum {r['oturum'][:8]}…  ana ${r['ana']:.2f} + subagent ${r['subagent']:.2f} = TOPLAM ${r['toplam']:.2f}  ({r['asistan_mesaji']} mesaj)")
    print("  model:", ', '.join(f"{k[:16]} ${v:.2f}" for k, v in r['model'].items()))
    if r['bilinmeyen_model']:
        print(f"  ⚠️ fiyati bilinmeyen model (Opus varsayildi): {r['bilinmeyen_model']} — FIYAT tablosunu guncelle")
    return 0

if __name__ == '__main__':
    sys.exit(main())
