#!/usr/bin/env python3
"""CLAUDE.md sadeleştirme kapısı — kural kaybını yakalar.

Kullanım:  python3 scripts/md-rule-gate.py <eski-dosya> <yeni-dosya>

⚠️ Taşıma birden çok dosyaya yayıldıysa "yeni" tarafı BİRLEŞTİRİLEREK verilir:
     cat CLAUDE.md docs/kurallar/*.md > /tmp/yeni.md
     python3 scripts/md-rule-gate.py <(git show origin/dev:CLAUDE.md) /tmp/yeni.md
⚠️ Kanonik kopya ~/.claude/scripts/ altındadır; her proje KOPYA alır ve
   commit'ler. Üçü ikizdir — birini değiştiren hepsini değiştirir.

Sadeleştirmenin tek kabul edilebilir biçimi "taşımak"tır, silmek değil. Bu
betik, aktif dosyadan bir KURALIN düşüp düşmediğini denetler. Tarihçe/göç
anlatısının arşive taşınması beklenen davranıştır ve rapor edilir ama kapıyı
kırmaz; kural kaybı kırar.

Kural taşıyıcı olarak sayılanlar (kullanıcının kendi işaretleri):
  1. ❌ ile başlayan yapma-listesi maddeleri
  2. KALICI / ZORUNLU / YASAK / YASAKTIR geçen satırlar
  3. Ters tırnak içindeki tanımlayıcılar (dosya yolu, sınıf, endpoint, bayrak)

Eşleştirme normalize edilerek yapılır (markdown süsü, boşluk, büyük/küçük harf
atılır) — çünkü sadeleştirme cümleyi yeniden biçimlendirebilir; ama kuralın
ÖZÜ ve içindeki tanımlayıcılar aynen durmalıdır.

Çıkış kodu: 0 = geçti, 1 = kural kaybı var (birleştirme YAPILMAZ).
"""
import re
import sys
import unicodedata

# ⚠ Bu desen MUTASYONLA doğrulandı ve bir kez GENİŞLETİLDİ. İlk hâli yalnız
# KALICI/ZORUNLU/YASAK arıyordu; "`test`/`prod`'a doğrudan push yok" gibi düz
# Türkçe yasak kipiyle yazılmış gerçek bir kuralı silen mutant kapıdan GEÇTİ.
# Kuralların çoğu büyük harfli etiket taşımaz — yükümlülük/yasak KİPİ taşır.
# Yeni bir kural kipi fark edilirse buraya eklenir; daraltma yapılmaz.
KURAL_ISARETI = re.compile(
    r"KALICI|ZORUNLU|YASAK"
    r"|\byok\b|\basla\b|\byalnız\b|\byalniz\b|\bsadece\b|\bşart\b|\bdaima\b"
    r"|\bher zaman\b|\bhiçbir\b|\bhicbir\b|\bgerekir\b|\bgerekmez\b"
    r"|\w+m[ae]z\b"          # yapılmaz, edilmez, açılmaz, dokunulmaz
    r"|\w+m[ae]li\b"         # olmalı, yazılmalı, geçmeli
    r"|\bdeğil\b|\bdegil\b",
    re.IGNORECASE,
)
# Tanımlayıcı: en az bir nokta/eğik çizgi/parantez içeren ya da CamelCase olan
# ters tırnaklı parça. "bkz" gibi düz kelimeleri elemek için.
TANIMLAYICI = re.compile(r"`([^`\n]{3,80})`")
ANLAMLI_TANIMLAYICI = re.compile(r"[./]|[a-z][A-Z]|^[A-Z][a-zA-Z]+[A-Z]|\(\)|^--|^-[A-Za-z]")


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[*_`>#\[\]()]", " ", s)     # markdown süsü
    s = re.sub(r"[^\w\s/.:-]", " ", s)        # emoji, noktalama
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def yapma_maddeleri(metin: str):
    """❌ ile işaretli yapma-listesi maddeleri."""
    out = []
    for satir in metin.splitlines():
        if "❌" in satir:
            g = normalize(satir.split("❌", 1)[1])
            if len(g) >= 12:
                out.append((satir.strip(), g))
    return out


def kural_satirlari(metin: str):
    """KALICI/ZORUNLU/YASAK taşıyan satırlar."""
    out = []
    for satir in metin.splitlines():
        if KURAL_ISARETI.search(satir):
            g = normalize(satir)
            if len(g) >= 12:
                out.append((satir.strip(), g))
    return out


def tanimlayicilar(metin: str):
    out = set()
    for m in TANIMLAYICI.finditer(metin):
        t = m.group(1).strip()
        if ANLAMLI_TANIMLAYICI.search(t):
            out.add(t)
    return out


OLUMSUZLAMA = re.compile(
    r"geçersiz|gecersiz|serbest|artık\s+\S+\s+değil|artik\s+\S+\s+degil"
    r"|kaldırıldı|kaldirildi|iptal edildi|yürürlükten|yururlukten|uygulanmaz",
    re.IGNORECASE,
)
EN_AZ_ORAN = 0.6   # yeni satir, eskisinin en az bu kadari kadar uzun olmali


def eslesen_satir(ihtiyac: str, yeni_satirlar):
    """Kuralın özünü taşıyan YENİ SATIRI döndürür (yoksa None). Tam cümle
    aranmaz (yeniden biçimlendirilmiş olabilir); anlamlı kelime pencereleri
    aranır. Eşleşen satırı döndürmek şart: uzunluk ve olumsuzlama o satır
    üzerinde ölçülür — bütün metin üzerinde ölçülemez."""
    kelimeler = ihtiyac.split()
    adaylar = [ihtiyac]
    for pencere in (10, 7, 5, 4):
        if len(kelimeler) >= pencere:
            adaylar.append(" ".join(kelimeler[:pencere]))
            orta = len(kelimeler) // 2
            adaylar.append(" ".join(kelimeler[orta:orta + pencere]))
    # ⚠️ "En uzun eslesen satiri al" YANLISTI (05/09/2026, regresyonda yakalandi):
    # kisa bir satirin penceresi, alakasiz UZUN bir maddenin icinde de gecebilir
    # ve o maddenin tarihce dilindeki "kaldirildi" yanlis olumsuzlama uretir.
    # Dogrusu: tam icerme varsa o; yoksa uzunlugu ESKISINE EN YAKIN satir.
    tam = [x for x in yeni_satirlar if ihtiyac in x]
    if tam:
        return min(tam, key=lambda x: abs(len(x) - len(ihtiyac)))
    kismi = [x for x in yeni_satirlar if any(a in x for a in adaylar)]
    if not kismi:
        return None
    return min(kismi, key=lambda x: abs(len(x) - len(ihtiyac)))


def kural_triaji():
    """md-kapi-triaj.json icindeki "kural" haritasi: {eski satirin normalize
    ILK 60 KARAKTERI: gerekce}. ⚠️ Muafiyet YOLA degil DEGERE verilir ve
    gerekceli olmak ZORUNDADIR — bos gerekce muafiyet sayilmaz. Niyetli bir
    yeniden-yazim (yanlis oldugu KODDA dogrulanan bir madde) buraya yazilir;
    aksi halde kapi onu "budanmis" diye kirar ve kirmakta haklidir."""
    import json, pathlib
    tf = pathlib.Path(__file__).with_name("md-kapi-triaj.json")
    if not tf.exists():
        return {}
    d = json.loads(tf.read_text(encoding="utf-8"))
    return {k: v for k, v in (d.get("kural") or {}).items() if isinstance(v, str) and v.strip()}


def kayip_mi(ham: str, g: str, yeni_satirlar, triaj=None):
    anahtar = g[:60]
    if triaj and anahtar in triaj:
        return None   # gerekceli, niyetli degisiklik — raporda ayrica listelenir
    """(sebep | None). ⚠️ Iki kor nokta 05/09/2026'da MUTASYONLA bulundu ve
    kapatildi: (1) kural metni duruyor ama sonuna 'ARTIK GECERSIZ / SERBEST'
    eklenmis — eski kapi yalniz VARLIGA bakiyordu, gecti. (2) ters-tirnaksiz
    bir maddenin govdesi silinip ilk 6 kelimesi birakilmis — pencere eslesmesi
    saglandi, gecti. Ikisi de kontrol degiskeniyle (tam silme yakalaniyor)
    dogrulandi."""
    satir = eslesen_satir(g, yeni_satirlar)
    if satir is None:
        return "KAYIP"
    if len(satir) < EN_AZ_ORAN * len(g):
        return "BUDANMIS (%d -> %d karakter, govde gitmis)" % (len(g), len(satir))
    yeni_isaret = set(m.group(0).lower() for m in OLUMSUZLAMA.finditer(satir))
    eski_isaret = set(m.group(0).lower() for m in OLUMSUZLAMA.finditer(g))
    fark = yeni_isaret - eski_isaret
    if fark:
        return "TERSINE CEVRILMIS OLABILIR (yeni olumsuzlama: %s)" % ", ".join(sorted(fark))
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    eski = open(sys.argv[1], encoding="utf-8").read()
    yeni = open(sys.argv[2], encoding="utf-8").read()
    # Satir satir normalize: uzunluk ve olumsuzlama SATIR uzerinde olculur.
    yeni_satirlar = [normalize(l) for l in yeni.splitlines() if normalize(l)]

    kayip_yapma, kayip_kural, kayip_tanim = [], [], []
    ktriaj = kural_triaji()
    triajli = [(ham, ktriaj[g[:60]]) for ham, g in yapma_maddeleri(eski) + kural_satirlari(eski) if g[:60] in ktriaj]

    for ham, g in yapma_maddeleri(eski):
        sebep = kayip_mi(ham, g, yeni_satirlar, ktriaj)
        if sebep:
            kayip_yapma.append((ham, sebep))

    for ham, g in kural_satirlari(eski):
        sebep = kayip_mi(ham, g, yeni_satirlar, ktriaj)
        if sebep:
            kayip_kural.append((ham, sebep))

    eski_t, yeni_t = tanimlayicilar(eski), tanimlayicilar(yeni)
    kayip_tanim = sorted(eski_t - yeni_t)

    e_sat, y_sat = len(eski.splitlines()), len(yeni.splitlines())
    e_kb, y_kb = len(eski.encode()) / 1024, len(yeni.encode()) / 1024
    print(f"satır : {e_sat} -> {y_sat}  (%{100 - y_sat * 100 // max(e_sat,1)} azaldı)")
    print(f"boyut : {e_kb:.0f} KB -> {y_kb:.0f} KB  (%{100 - int(y_kb * 100 / max(e_kb,0.01))} azaldı)")
    print(f"❌ madde   : {len(yapma_maddeleri(eski))} -> {len(yapma_maddeleri(yeni))}")
    print(f"kural satırı: {len(kural_satirlari(eski))} -> {len(kural_satirlari(yeni))}")
    print(f"tanımlayıcı : {len(eski_t)} -> {len(yeni_t)}")

    hata = False
    if triajli:
        print(f"\n· Gerekçeli niyetli değişiklik ({len(set(h for h,_ in triajli))}) — triajda:")
        for ham, ger in dict(triajli).items():
            print(f"   {ham[:90]}\n      → {ger}")
    if kayip_yapma:
        hata = True
        print(f"\n✗ KAYIP/BOZUK YAPMA MADDESİ ({len(kayip_yapma)}):")
        for x, sebep in kayip_yapma:
            print(f"   [{sebep}] " + x[:140])
    if kayip_kural:
        hata = True
        print(f"\n✗ KAYIP/BOZUK KURAL SATIRI ({len(kayip_kural)}):")
        for x, sebep in kayip_kural:
            print(f"   [{sebep}] " + x[:140])
    if kayip_tanim:
        # Tanımlayıcı kaybı da KAPIYI KIRAR. Bir kısmı meşru olabilir (bitmiş
        # göçün tablo adı, arşive taşınan eski dosya yolu) ama bu KARAR
        # GEREKTİRİR — sessizce geçmez. Muafiyet YOLA değil DEĞERE verilir ve
        # gerekçesiyle triaj dosyasına yazılır (standards/15 §13b/2 ile aynı
        # disiplin). Triaj boşaltıldığında kapı yeniden kırılmalıdır.
        triaj = {}
        try:
            import json
            import pathlib
            tf = pathlib.Path(__file__).with_name("md-kapi-triaj.json")
            if tf.exists():
                triaj = json.loads(tf.read_text(encoding="utf-8"))
        except Exception as e:  # triaj okunamıyorsa kapıyı GEVŞETME
            print(f"\n✗ Triaj dosyası okunamadı ({e}) — kapı kapalı sayılır.")
            return 1

        dosya_triaji = triaj.get(sys.argv[2], {}) or triaj.get("*", {})
        gerekceli = [x for x in kayip_tanim if x in dosya_triaji]
        gerekcesiz = [x for x in kayip_tanim if x not in dosya_triaji]

        if gerekceli:
            print(f"\n· Gerekçeli taşınan tanımlayıcılar ({len(gerekceli)}) — arşivde:")
            for x in gerekceli:
                print(f"   `{x}` — {dosya_triaji[x]}")
        if gerekcesiz:
            hata = True
            print(f"\n✗ GEREKÇESİZ DÜŞEN TANIMLAYICI ({len(gerekcesiz)}):")
            for x in gerekcesiz:
                print("   `" + x + "`")
            print("   → Ya aktif dosyada kalmalı ya da md-kapi-triaj.json'a")
            print("     'neden aktif dosyada gerekmiyor' gerekçesiyle yazılmalı.")

    if hata:
        print("\nKAPI KIRILDI — kural kaybı var, bu sadeleştirme kabul edilmez.")
        return 1
    print("\n✓ Kapı geçti: hiçbir yapma-maddesi ve kural satırı düşmedi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
