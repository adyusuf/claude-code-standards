# Vaka 02 — 48 sahte düşüş: ortam sınırını ürün hatası sanmak

> **Özet:** Uzak test ortamına karşı 8 worker ile koşan Playwright paketi API
> istek sınırına takıldı ve **48 test düştü.** Hiçbiri ürün hatası değildi.
> Düşüşler sınıflandırılmadan koşum tekrarlandığı için zaman iki kez kaybedildi.
> Tarih: 13-14/09/2026. Proje: Proje A.

## Bağlam

Proje A'nın e2e paketi uzak bir test ortamına karşı koşuyor: her test kendi
verisini API'den yaratıyor, akış UI'dan sürülüyor. Paralellik performans için
8 worker'a çıkarılmıştı.

## Ölçüm

**48 test kırmızı.** Ama hata dağılımı ürün hatası desenine benzemiyordu:
düşüşler farklı modüllere yayılmıştı, tekil bir davranışta toplanmıyordu.
Gerçek sebep koşumun kendisiydi — 8 worker aynı anda giriş yapıp API'yi
dövünce **istek sınırı (429)** devreye girdi.

İkinci gürültü kaynağı aynı dönemde ortaya çıktı: e2e test verisi
`@ornek-<proje>.test` gibi **sahte alan adlı** e-postalar kullanıyordu. Test
ortamı gerçek SMTP'ye bağlı olduğu için her davet ve link iletisi geri döndü ve
sürekli gönderim hatası bastı. Yani **gerçek bir e-posta arızası bu gürültünün
içinde görünmez hâle geliyordu.**

## Bulgu

Asıl arıza teknik değil, **okuma biçimiydi**:

1. **Koşum geçersizdi, ama sonucu geçerli gibi okundu.** Ortamın sınırına
   takılmış bir koşum, ürün hakkında hiçbir şey söylemez.
2. **Sınıflandırma yoktu.** 48 düşüş tek bir yığın olarak görüldü; hangisinin
   ürün, hangisinin ortam kaynaklı olduğu ayrılmadan koşum tekrarlandı.
3. **"Muhtemelen flaky" bir teşhis sayılıyordu.** Sayılmaz — ölçülmemiş bir
   tahmindir ve altındaki gerçek hatayı örter.

⚠️ Kritik nokta: en pahalı hamle testleri tekrar koşmak değil, **yanlış
sınıflandırılmış bir koşumu taban almaktı.** O tabanın üstüne kurulan her
karar da yanlış oluyordu.

## Müdahale

Koşum döngüsü kurala bağlandı (#31, `standards/11-playwright.md` §9a):

1. **Tam koşum** — paketin tamamı koşar, ilk hatada durulmaz
   (`--max-failures=0`). Paralellik **ortamın sınırına göre** seçilir: istek
   sınırı, oturum/token ömrü, paylaşılan fixture'lar. Her testte giriş yapan
   uzak paketler düşük paralellikle, çoğunlukla **1 worker** ile koşar.
2. **Sınıflandırma — her düşen test için kanıtla bir sınıf:**
   - *ürün hatası* — davranış gerçekten bozuk
   - *bayat spec* — ürün değişti, spec eskidi
   - *veri/fixture* — test verisi eksik ya da önceki koşumdan artık kaldı
   - *ortam* — 429, zaman aşımı, deploy gecikmesi, süresi dolmuş oturum

   Kanıt zorunlu: hata metni, `trace.zip`, sayfa görüntüsü, ağ durumları,
   testin önceki koşumlardaki sonucu. **"Muhtemelen flaky" sınıf değildir.**
3. **Düzeltme** — her düzeltme kendi dalında ve kendi merge'iyle.
   ⛔ Retry artırmak, beklemeyi körlemesine büyütmek, assertion gevşetmek
   **düzeltme sayılmaz.** Ortam sınıfındaki düşüşün düzeltmesi koşum ayarıdır
   (paralellik, bekleme penceresi), spec değil.
4. **Hedefli koşum** — yalnız düzeltilenler ve etkilenebilecekler.
5. **Tam tekrar kararı gerekçelendirilir.** Tekrarlanır: düzeltme paylaşılan
   bir parçaya dokunduysa (layout, auth, ortak bileşen, fixture, config) ·
   promosyon kaydı geçerli bir tam koşum istiyorsa · **ilk koşumdaki
   düşüşlerin bir kısmı ortam kaynaklıysa** (o koşum geçerli bir taban değil).
6. **Geçersiz koşum ürün sonucu diye raporlanmaz** — paralellik düşürülüp
   tekrarlanır ve bu açıkça yazılır.

Ayrıca test verisi e-postası tek bir yardımcıdan üretilir ve **gerçek bir
kutuya** gider (#30); `.test` / `.local` / `example.com` yasaklandı.

## Sonuç

- Sahte düşüşler ürün hatası olarak raporlanmıyor; koşumun geçerliliği
  sonucundan önce sorgulanıyor.
- Paralellik artık bir performans ayarı değil, **ortam kısıtının fonksiyonu**.
- Gönderim hatası gürültüsü kesildiği için gerçek e-posta arızası görünür hâle
  geldi.

## Sonraki dönüş: kapı, koşamadığı zaman ne yapar?

19/09/2026'da aynı zincirde başka bir arıza çıktı: `test` promosyonundaki e2e
adımı, artifact kotası dolduğu için **deploy-durum dosyasını okuyamadı** ve
e2e'yi hiç başlatamadı. Yani kapı, koştuğunu sanarken hiçbir şey koşmamıştı.

Bunun üzerine zamanlama değişti (#33): `dev` ve `test` yönünde e2e yoktur —
ne koşum, ne deploy beklemesi. Eksik spec de, koşum da **`prod` öncesi kapıda**:
kod `test`'te mi → eksik e2e var mı → yaz → bu kodla koşulmadıysa koş → `prod`.
E2E koşmadan `prod`'a çıkılmaz; tek istisna açıkça "hotfix" denen iştir ve
rapora **"e2e atlandı (hotfix)"** diye yazılır — geçti sayılmaz.

## Nasıl doğrulanır

```bash
# Tam koşum, ilk hatada durmadan, ortamın sınırına göre paralellik
npx playwright test --max-failures=0 --workers=1

# Ortam kaynaklı düşüşün kanıtı: 429 / zaman aşımı izleri
npx playwright show-trace test-results/**/trace.zip

# Sahte alan adlı test e-postası taraması
grep -rE '@[a-z0-9.-]+\.(test|local)\b|example\.com' e2e/
```

## Açık kalan

- Sınıflandırma **elle** yapılıyor; kanıt toplama otomatik değil.
- `--only-failed` benzeri hedefli koşum her projede yok; dosya/satır filtresiyle
  idare ediliyor.
- Kapının "koştu mu" sorusu (19/09 arızası) zamanlama değiştirilerek çözüldü,
  **kapı içi sağlık kontrolü eklenerek değil.** Aynı sınıf arıza başka bir
  adımda tekrar çıkabilir.
