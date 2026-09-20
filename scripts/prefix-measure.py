#!/usr/bin/env python3
"""Oturumların SABIT ONEGINI olcer (sistem prompt + arac/skill listeleri + CLAUDE.md).

Kullanim:  python3 ~/.claude/scripts/prefix-measure.py [YYYY-MM-DD HH:MM]
           ikinci argüman verilirse o andan SONRA baslayan oturumlar isaretlenir.

NEDEN VAR: sabit onek her istekte yeniden okunur; 20/09/2026 olcumunde toplam
harcamanin %18'iydi. Eklenti kapatmak / CLAUDE.md kucultmek bu sayiyi dusurur
ama etkisi YALNIZ YENI OTURUMDA gorunur — acik oturum yapilandirma anlik
goruntusunu baslangicta alir (olculerek dogrulandi: ayni oturumda degisiklik
oncesi ve sonrasi ajan onegi birebir ayni cikti).

⚠️ Siralama dosya damgasina degil OTURUM BASLANGICINA gore yapilir: en son
YAZILAN transcript cogu zaman eski bir oturumdur ve "sonrasi" sanilir.
"""
import glob, json, os, sys, datetime

kes = None
if len(sys.argv) > 1:
    kes = datetime.datetime.fromisoformat(' '.join(sys.argv[1:])).timestamp()

rows = []
for f in glob.glob(os.path.expanduser('~/.claude/projects/**/*.jsonl'), recursive=True):
    if os.path.basename(f).startswith('agent-'):
        continue
    ilk = bas = None
    for line in open(f, errors='ignore'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if bas is None and d.get('timestamp'):
            bas = d['timestamp']
        u = (d.get('message') or {}).get('usage')
        if u:
            ilk = sum(u.get(k, 0) or 0 for k in
                      ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
            break
    if ilk and bas:
        ts = datetime.datetime.fromisoformat(bas.replace('Z', '+00:00')).timestamp()
        rows.append((ts, os.path.basename(f)[:8], ilk))

rows.sort(reverse=True)
print("oturum başlangıcına göre son 10 oturum:\n")
for ts, ad, ilk in rows[:10]:
    im = ' ← kesim sonrası' if kes and ts > kes else ''
    print(f"  {datetime.datetime.fromtimestamp(ts):%d/%m %H:%M}  {ad}  {ilk:>8,} token{im}")
if kes:
    s = [r[2] for r in rows if r[0] > kes]
    print(f"\nkesimden sonra başlayan oturum: {len(s)}" +
          (f" · medyan önek {sorted(s)[len(s)//2]:,} token" if s else " → yeni oturum açılmalı"))
