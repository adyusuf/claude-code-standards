# Playwright — Web E2E Standartları

## 1. Ne e2e'ye girer

E2E **pahalıdır** (yavaş, kırılgan). Yalnız şunlar:

- Para/veri kaybettiren kritik akışlar (giriş, kayıt, sipariş, ödeme onayı, silme)
- Birden fazla sistemi birden kanıtlayan akışlar (UI → API → DB → e-posta)
- Regresyona uğramış gerçek hatalar

**Girmez:** her form alanının validasyonu, her buton, her varyant — bunlar unit/component testidir.
Hedef: 15–40 senaryo arası, 10 dakikanın altında koşum.

## 2. Selector politikası (sırayla)

1. `getByRole('button', { name: 'Kaydet' })` — erişilebilirlik ile aynı yolu test eder
2. `getByLabel('E-posta')`
3. `getByText(...)` — kararlı, i18n'e bağımlı metinlerde dikkat
4. `getByTestId('member-row')` — **son çare**, ama karmaşık listelerde meşru

**Yasak:** CSS sınıfı, `nth-child`, XPath, üretilen class (`css-1x2y3z`), DOM yapısına bağlı zincirler.
Stil değişikliği testi kırmamalı.

`data-testid` eklenirken silinmemesi gerektiği yorumla belirtilir.

## 3. Bekleme

- **`waitForTimeout` / `sleep` yasak.** Playwright'ın auto-wait'i + web-first assertion kullanılır:
  `await expect(page.getByRole('row')).toHaveCount(3)`
- Ağ bekleniyorsa `page.waitForResponse(...)` veya sonucun UI'daki yansımasını bekle.
- Sabit timeout artırmak flaky çözümü değildir — nedeni bulunur.

## 4. Veri ve izolasyon

- **Her test kendi verisini yaratır.** Ortak/paylaşılan kayıt üzerinde test yapılmaz (paralel koşumda çakışır).
- Kurulum UI'dan değil **API'den** yapılır (hızlı ve sağlam); test edilen akış UI'dan.
- Benzersiz veri — sabit e-posta/isim yasak. **E-posta gerçek kutuya gider** (global kural #30, 14/09/2026):
  `<hesap>+<etiket>@gmail.com`, etiket kaydı ayırır (`musteri-${Date.now()}-${rastgele}`). Adresi fixture'daki
  **tek yardımcı** üretir (taban `E2E_EMAIL_BASE` ile ezilebilir); spec'e adres yazılmaz. `.test` / `.local` /
  `example.com` YASAK: test ortamı gerçek SMTP'ye bağlıysa her davet/link iletisi geri döner ve gönderim hatası basar.
  Örnek: `e2eEmail(\`musteri-${Date.now()}\`)` → `<hesap>+musteri-1789…@gmail.com`.
- Test sonunda temizlik (veya izole tenant/şema).
- Üretim ortamına e2e koşulmaz. Test ortamında koşulur; ortam URL'i env'den gelir, hard-coded değil.

## 5. Kimlik doğrulama

- Giriş her testte UI'dan yapılmaz → `storageState` ile bir kez giriş, tüm testler o oturumu kullanır.
- Rol bazlı fixture: `adminPage`, `memberPage`, `guestPage`.
- **Giriş akışının kendisi** ayrıca bir testle doğrulanır (o test storageState kullanmaz).

## 6. Yapı

```
e2e/
  fixtures/      → auth, test verisi, API yardımcıları
  pages/         → Page Object (yalnız karmaşık ekranlar için)
  specs/         → senaryolar, iş akışına göre gruplanmış
  userstories/   → kabul kriterlerini birebir yansıtan senaryolar
playwright.config.ts
```

- Page Object **zorunlu değil** — basit ekranda gereksiz katman. Aynı seçici 3+ testte tekrarlanıyorsa çıkarılır.
- Page Object'te assert yok; assert testte kalır.

## 7. Assertion

- Kullanıcının gördüğünü doğrula: metin, sayı, görünürlük, URL, toast.
- `expect(await page.locator(...).count()).toBe(3)` yerine `await expect(locator).toHaveCount(3)` (retry'lı).
- Tek "her şeyi kontrol eden" dev test yerine akış başına odaklı testler.
- Ekran görüntüsü karşılaştırması (visual regression) yalnız kasıtlı ve dar kapsamlı kullanılır; yoksa sürekli kırmızı yanar.

## 8. Konfigürasyon

```ts
retries: process.env.CI ? 1 : 0,   // 1'den fazla retry = flaky'yi saklamak
workers: process.env.CI ? 2 : 4,
use: {
  baseURL: process.env.E2E_BASE_URL,   // hard-coded URL yasak
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
  locale: 'tr-TR',
  timezoneId: 'Europe/Istanbul',
}
```

- Locale ve timezone **sabitlenir** — makineye göre değişen tarih testi kırar.
- `trace`/`screenshot`/`video` CI artifact olarak yüklenir; başarısızlık log okumadan anlaşılabilmeli.

## 9. Koşum politikası

- Hızlı CI kapısına (unit/lint/tsc) **karıştırılmaz** — ayrı iş akışı.
- Tetikleme: `dev → test` merge sonrası ve/veya gecelik; ayrıca `test → prod` öncesi **zorunlu** kontrol.
- Son koşumun sonucu (commit, zaman, sonuç) bir dosyaya kaydedilir; prod merge'inden önce bu kayıt **bayat mı** diye bakılır. Bayatsa veya kırmızıysa onay olmadan ilerlenmez.
- E2E kırmızıyken prod'a çıkılmaz.

### 9a. Koşum döngüsü (14/09/2026, kullanıcı kararı — CLAUDE.md #31)

1. **Tam koşum.** Paketin tamamı koşar; ilk hatada durulmaz (`--max-failures=0`). Paralellik ortamın sınırına göre seçilir: istek sınırı (rate limit), oturum/token ömrü, paylaşılan fixture'lar. Uzak test ortamında her testte giriş yapan paketler düşük paralellikle (çoğunlukla 1 worker) koşar.
2. **Sınıflandırma.** Her düşen test için kanıtla bir sınıf yazılır:
   - *ürün hatası* — davranış gerçekten bozuk;
   - *bayat spec* — ürün değişti, spec eskidi (ör. değişen sınıf/metin);
   - *veri/fixture* — test verisi eksik ya da önceki koşumdan artık kaldı;
   - *ortam* — 429 istek sınırı, zaman aşımı, deploy gecikmesi, süresi dolan oturum.
   Kanıt: hata metni, iz (`trace.zip`), sayfa görüntüsü, ağ durumları, testin önceki koşumlardaki sonucu. "Muhtemelen flaky" sınıf değildir.
3. **Düzeltme.** Her düzeltme kendi dalında (`dev`'den) ve kendi merge'iyle. Retry artırmak, bekleme süresini körlemesine büyütmek ya da assertion gevşetmek düzeltme sayılmaz. Ortam sınıfındaki düşüş için düzeltme koşum ayarıdır (paralellik, bekleme penceresi), spec değil.
4. **Hedefli koşum.** Yalnız düzeltilen testler ve düzeltmenin etkileyebileceği testler koşar (projede varsa `--only-failed`, yoksa dosya/satır filtresi).
   ⚠️ **E2E yalnız `test`'e çıkmış kodla koşar (14/09/2026, kullanıcı kararı: "teste geçmeden önce e2e koşma", "teste geçince e2e koşulur").** Düzeltme `dev`'deyken doğrulama unit test + tsc/lint'tir. Hedefli koşum ve tam tekrar, düzeltme `test`'e çıkıp deploy olduktan sonra yapılır. `dev` dalındaki spec'i test ortamına karşı koşmak da e2e koşmaktır — yasak.
   ⚠️ **Zamanlama #33 ile değişti (20/09/2026, aynı gün bir kez daha daraltıldı):** `dev` ve `test` yönünde e2e **hiç yoktur** — ne koşum, ne "yazıldı mı" kontrolü, ne deploy/durum dosyası beklemesi. Eksik spec de, koşum da `prod` ÖNCESİ kapıda: kod `test`'te mi → eksik e2e var mı → yaz → bu kodla koşulmadıysa koş → prod. Eksik listesi iki kez değil **bir kez** çıkarılır (önceki hâlinde `dev`/`test`'te çıkarılıp prod kapısında yeniden hesaplanıyordu). Bu madde ve 4. maddedeki "test'e çıkınca" ifadeleri o kurala göre okunur.
   ⛔ **E2E koşmadan `prod`'a çıkılmaz;** e2e'siz yalnız kullanıcının açıkça "hotfix" dediği iş çıkar ve rapora "e2e atlandı (hotfix)" yazılır.
5. **Tam tekrar kararı — Claude verir, gerekçesini raporlar.** Tam koşum tekrarlanır:
   - düzeltme paylaşılan bir parçaya dokunduysa (layout, auth/oturum, ortak bileşen, fixture yardımcısı, Playwright config);
   - promosyon kaydı (commit status vb.) geçerli bir tam koşum sonucu istiyorsa;
   - ilk koşumdaki düşüşlerin bir kısmı ortam kaynaklıysa (o koşum geçerli bir taban değildir).
   Düzeltme tek spec'e ya da tek ekrana sınırlıysa ve kayıt gerektirmiyorsa hedefli koşum yeterlidir.
6. **Geçersiz koşum.** Ortam sınırına takılan koşumun sonucu ürün sonucu diye raporlanmaz; paralellik düşürülüp tekrarlanır ve bu açıkça yazılır.

## 10. Yapma listesi

- ❌ `waitForTimeout`
- ❌ CSS class / XPath selector
- ❌ Testler arası paylaşılan veri veya sıra bağımlılığı
- ❌ Hard-coded URL / kullanıcı / parola (env veya fixture)
- ❌ Üretimde e2e koşumu
- ❌ Flaky testi `retries` artırarak "çözmek"
- ❌ `test.only` commit'lemek (lint kuralı ile engelle)
