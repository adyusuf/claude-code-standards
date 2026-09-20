# Mod Y — Takım: tam kadro (C'nin takım karşılığı)

Dokuz rol teammate olarak açılabilir; **lider bendim** (ayrı lider ajanı YOK).

⛔ **Ön koşul:** [`takim-kurallari.md`](takim-kurallari.md) **§0** — rol
tanımlarında takım araçları yok ve özellik kapalı; ikisi çözülmeden Y açılmaz.

⚠️ Ortak kurallar: aynı dosyanın tamamı. Rol seçimi:
[`rol-secimi.md`](rol-secimi.md) §0-§7. **İkisini de rol açmadan önce oku.**

## Kadro
`urun-yoneticisi` · `analiz` · `mimar` · `tasarimci` · `gelistirici` ·
`test-yazar` · `qa` · `devops` · `belge`

⚠️ Y, **X'in üst kümesidir**. Test yazımı `gelistirici`ye bırakılmaz.

## Kural
- **Hepsini birden açma.** Aynı anda yaşayan teammate sayısı işin gerektirdiği
  kadardır (ölçüt: `rol-secimi.md` §0 — "ajan mı ben mi").
  ⚠️ Boşta teammate'in maliyeti **ölçülmedi**; teammate idle'a düşer ve mesaj
  gelmedikçe tur üretmez (`takim-kurallari.md` §7).
  Tur başında **kimi neden açtığımı** yazarım, işi biten teammate'i **kapatırım**.
- `gelistirici` yalnız **izole, sözleşmesi net** parçalarda. Çapraz katman bende.
- Review: `qa` teammate'i ilk geçişi yapar, **kritik bulguları ben doğrularım**.
- `urun-yoneticisi` çıktısı zincire akmaz, **senin onayına** gelir (§2a).
- `devops` çıktısı `qa`'ya girer (§3, #25 kesişimi dahil).
- Görev `owner`'larını ben atarım; serbest kapma kapalıdır.

## C'den farkı — tek cümlede
C'de roller **bana** rapor eder ve biter; Y'de roller **birbirine** rapor eder
ve yaşamaya devam eder. Beklenen kazanç: geri gönderme döngüsü ucuzlar (üreten
hâlâ ayakta). ⚠️ Bu kazanç da, karşılığındaki maliyet de **ölçülmedi**.
⚠️ Roller birbirine rapor ettiği için eksik kontrolü bloğunun **lidere de**
gitmesi şarttır (`takim-kurallari.md` §4).

## Ne zaman
Uçtan uca özellik (backend + web + mobil), 15+ dosya, **ve** roller arasında
birden çok gidiş-geliş bekleniyorsa. Tek yönlü akışta **C daha ucuzdur**.

## Beklenen maliyet
**~3–6x** (ÖLÇÜLMEDİ). Eşik: ~$150 uyarı / **~$300 durma**.
