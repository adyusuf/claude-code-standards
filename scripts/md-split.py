#!/usr/bin/env python3
"""CLAUDE.md karar günlüğünü iki katmana ayırır — TAŞIYARAK, yeniden yazmadan.

Kullanım:
  python3 scripts/md-split.py <claude.md> <bölüm-başlığı> <detay-dosyası> <göreli-link>

⚠️ Kanonik kopya ~/.claude/scripts/ altındadır; her proje KOPYA alır ve
   commit'ler. Üçü ikizdir — birini değiştiren hepsini değiştirir.

Yöntem:
  · DETAY dosyası her maddeyi **birebir ve eksiksiz** alır (tek satırı bile
    değişmez) — yani bu adımdan sonra kayıp tanım gereği imkânsızdır.
  · AKTİF dosyada maddenin KURAL taşıyan satırları aynen kalır; kural işareti
    taşımayan saf anlatı satırları düşer ve yerine detay linki konur.
  · Hiçbir cümle parafraz edilmez. Parafraz, kaybın en sık yoludur.

Ölçüldü (Proje A backend/CLAUDE.md): bölümün %87'si kural taşıyan satır,
%12'si saf anlatı. Yani bu işlemin BOYUT kazancı ~%10'dur — asıl kazancı
detayın bir evinin olması ve aktif dosyanın bir kural indeksine dönüşmesidir.
Bundan daha fazlasını istemek kural feda etmek demektir; md-kapi.py bunu
reddeder.
"""
import pathlib
import re
import sys

# md-kapi.py ile AYNI desen olmak zorunda: kapının koruduğu şeyi burada
# düşürürsek kapı haklı olarak kırılır. Tek kaynak olsun diye buradan
# değiştirilirse md-kapi.py da güncellenir.
KURAL = re.compile(
    r"KALICI|ZORUNLU|YASAK"
    r"|\byok\b|\basla\b|\byalnız\b|\byalniz\b|\bsadece\b|\bşart\b|\bdaima\b"
    r"|\bher zaman\b|\bhiçbir\b|\bhicbir\b|\bgerekir\b|\bgerekmez\b"
    r"|\w+m[ae]z\b|\w+m[ae]li\b|\bdeğil\b|\bdegil\b|❌|⚠",
    re.IGNORECASE,
)
# Ters tırnaklı tanımlayıcı taşıyan satır da korunur: kapı tanımlayıcı kaybını
# da reddediyor ve haklı — `MemberTierInfo.ContentHiddenTiers` gibi cümleler
# kural işareti taşımaz ama kuralın KENDİSİDİR.
TANIM = re.compile(r"`[^`\n]*[./][^`\n]*`|`[a-z][A-Za-z0-9]*[A-Z][^`\n]*`")
BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def slug(s: str) -> str:
    d = {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
         "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"}
    s = "".join(d.get(c, c) for c in s)
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s).strip().lower()
    return re.sub(r"\s+", "-", s)[:60].strip("-") or "karar"


def baslik(madde: str) -> str:
    m = BOLD.search(madde)
    if not m:
        return madde.lstrip("- ").split("\n")[0][:110]
    return " ".join(m.group(1).split()).rstrip(":").strip()


def maddeler(govde: str):
    out, cari = [], None
    for s in govde.split("\n"):
        if re.match(r"^- ", s):
            if cari:
                out.append("\n".join(cari).rstrip())
            cari = [s]
        elif cari is not None:
            cari.append(s)
    if cari:
        out.append("\n".join(cari).rstrip())
    return [m for m in out if m.strip()]


def korunur(satir: str) -> bool:
    """Bu satır aktif dosyada KALMALI mı?"""
    if not satir.strip():
        return False
    return bool(KURAL.search(satir) or TANIM.search(satir))


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    yol, hedef, detay_yolu, goreli = sys.argv[1:5]
    p = pathlib.Path(yol)
    ham = p.read_text(encoding="utf-8")
    sat = ham.split("\n")

    bas = son = None
    for i, s in enumerate(sat):
        if s.strip() == hedef.strip():
            bas = i
        elif bas is not None and s.startswith("## "):
            son = i
            break
    if bas is None:
        print(f"HATA: '{hedef}' bulunamadı.")
        return 1
    son = son if son is not None else len(sat)

    mlist = maddeler("\n".join(sat[bas + 1:son]))
    if not mlist:
        print("HATA: madde yok.")
        return 1

    kullanilan, detay_parca, yeni = set(), [], [sat[bas], ""]
    yeni += [
        "> Aşağıdaki her satır **bağlayıcı bir kuraldır**. Her maddenin gerekçesi,",
        f"> nasıl keşfedildiği ve tarihçesi [{pathlib.Path(detay_yolu).name}]({goreli})",
        "> dosyasında **birebir** durur — o dosya otomatik yüklenmez; bir karara",
        "> dokunmadan önce ilgili maddesini oradan oku. Kuralın NEDEN var olduğunu",
        "> bilmeden gevşetme.",
        "",
    ]

    dusen = 0
    for m in mlist:
        b = baslik(m)
        s = slug(b)
        oz, n = s, 2
        while s in kullanilan:
            s, n = f"{oz}-{n}", n + 1
        kullanilan.add(s)

        # Detaya BİREBİR ve EKSİKSİZ
        detay_parca.append(f"### {b}\n\n{m}\n")

        # Aktife yalnız kural taşıyan satırlar
        tut = [ln for ln in m.split("\n") if korunur(ln)]
        dusen += len(m.split("\n")) - len(tut)
        if not tut:
            tut = [m.split("\n")[0]]
        yeni += tut
        yeni.append(f"  · [gerekçe & tarihçe]({goreli}#{s})")

    yeni.append("")

    d = pathlib.Path(detay_yolu)
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(
        "# Kalıcı yapısal kararlar — tam metin\n\n"
        f"> `{p.name}`'in karar günlüğü. **Otomatik yüklenmez.**\n"
        "> Aktif dosyada her kararın kural satırları durur; gerekçe, tuzak\n"
        "> hikâyesi, test kilidi ve tarihçe burada — aktif dosyadan **birebir**\n"
        "> taşındı, parafraz yok.\n\n" + "\n".join(detay_parca),
        encoding="utf-8")

    p.write_text("\n".join(sat[:bas] + yeni + sat[son:]), encoding="utf-8")

    print(f"madde         : {len(mlist)}")
    print(f"düşen satır   : {dusen} (saf anlatı — tamamı detayda duruyor)")
    print(f"detay dosyası : {d} ({len(d.read_text(encoding='utf-8'))/1024:.0f} KB)")
    print(f"aktif dosya   : {len(ham)/1024:.0f} KB -> {len(p.read_text(encoding='utf-8'))/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
