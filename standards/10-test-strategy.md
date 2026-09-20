# Test Stratejisi

## 1. Piramit

```
        /\        E2E (Playwright / Maestro)      — az, kritik akış, gerçek sistem
       /  \       Integration (API + gerçek DB)   — orta, sözleşme + veri katmanı
      /____\      Unit                            — çok, hızlı, izole
```

- Piramidin tersine dönmesi (her şeyi e2e ile test etmek) yavaş ve kırılgan CI demektir.
- Bir hata bulunduğunda: **önce hatayı gösteren test yazılır**, sonra düzeltilir (regresyon kalkanı).

## 2. Ne test edilir, ne edilmez

**Edilir:** iş kuralları, sınır değerler, hata yolları, yetki kararları, hesaplamalar,
durum makineleri, serileştirme sözleşmesi, geriye uyumluluk.

**Edilmez:** framework'ün kendisi, getter/setter, tip sisteminin zaten garantilediği şeyler,
implementasyon detayı (özel metot isimleri, çağrı sırası).

## 3. Unit test kuralları

- **AAA:** Arrange / Act / Assert — üç blok görünür olsun.
- Test adı davranışı anlatır:
  `Siparis_iptal_edildiginde_stok_geri_yuklenir` / `returns_400_when_email_is_invalid`
- **Bir test bir davranış.** Bir testte 8 assert varsa muhtemelen 3 test olmalı.
- Testte **mantık yok**: `if`, `for`, hesaplama yok. Beklenen değer elle yazılır (kodun formülünü tekrarlama).
- Testler **birbirinden bağımsız** ve **sıradan bağımsız**; paylaşılan mutable state yok.
- Deterministik: `DateTime.Now`, `Random`, `Guid.NewGuid()` doğrudan kullanılmaz → enjekte edilir/sabitlenir.
- `Thread.Sleep` yasak → gerçek bekleme yerine sahte saat / event bekleme.
- Test verisi builder/factory ile üretilir (`aMember().withStatus(Active).build()`), her testte 20 satır kurulum yok.

## 4. Test double seçimi

| Tür | Ne zaman |
|---|---|
| **Fake** (çalışan basit implementasyon) | Tercih edilen — in-memory repo, sahte saat |
| **Stub** (sabit değer döner) | Girdi sağlamak için |
| **Mock** (etkileşim doğrular) | Yalnız **dış etki** doğrulanacaksa (e-posta gönderildi mi) |

- Aşırı mock'lama testi implementasyona bağlar → refactor'da kırılır, hata yakalamaz.
- Kendi kodunu mock'lama; sınırları (dış servis, saat, ağ, dosya) mock'la.

## 5. Integration test

- Gerçek veritabanına karşı koşulur (**Testcontainers** tercih edilir).
- In-memory provider kullanılıyorsa farkları bilinerek: case-sensitivity, `unaccent`, transaction, concurrency, raw SQL, FK davranışı **farklıdır**. Kritik davranış in-memory ile doğrulanmış sayılmaz.
- Her test kendi verisini yaratır ve temizler (transaction rollback veya izole şema).
- API testi HTTP seviyesinden yapılır (`WebApplicationFactory`) — controller metodunu doğrudan çağırmak değil.

### 5a. Test sonucu makineye bağlı olamaz — sır sızıntısı taban fabrikada kesilir

Integration testi geliştirme ortamında ayağa kalkıyorsa (`Development`), yapılandırma zinciri **user-secrets'ı da yükler**. Geliştiricinin makinesinde tanımlı her sır teste sızar; temiz bir makinede sızmaz. Sonuç: aynı commit iki makinede iki farklı sonuç verir ve testin ne kanıtladığı belirsizleşir.

- Testin ayağa kaldırdığı **taban fabrikada** (`WebApplicationFactory` türevi), dış dünyaya açılan veya davranış değiştiren **her ayar açıkça sabitlenir** — tek tek, sızdığı görüldükçe değil. Tipik olanlar: LLM/API anahtarları, şifreleme anahtar halkası yolu, dış servis adresleri, tarayıcı görünürlüğü, özellik bayrakları.
- Varsayılan **"yapılandırılmadı"** (boş/kapalı) olur. Uç testlerinin çoğu bu yeteneklere ihtiyaç duymaz; ihtiyaç duyan test yeteneği **kendisi** kurar (`WithWebHostBuilder` + teste özel geçici dizin) ve bu override taban fabrikadan sonra koştuğu için kazanır.
- Sabitlemenin yanına **neden** yazılır. "Boş bırakıldı" tek başına bir sonraki kişiye anlamsız gelir ve silinir; "geliştiricinin gerçek anahtarı sızıp test para harcadı" silinmez.
- Yerel bir çözüm (tek bir alt fabrikada boşaltma) taban fabrikaya taşındığında **kaldırılır**. Yerel satır kaldırıldıktan sonra ilgili testin hâlâ geçmesi, taban ayarın gerçekten uygulandığının kanıtıdır.

Aynı kural test veritabanı için de geçerli: paylaşılan sabit adlı bir test veritabanı, paralel çalışma kopyalarında birbirinin verisini siler. Ad **çalışma kopyasından türetilir**; `[Collection]` serileştirmesi yalnız süreç içinde korur.

## 6. Sözleşme (contract) testi

- İstemcinin beklediği alanlar sunucu yanıtında var mı — **geriye uyumluluk kalkanı**.
- Her endpoint için minimum: durum kodu + zorunlu alanların varlığı ve tipi.
- Bir alan silinirse/adı değişirse bu test **kırmızı yanar** — asıl amacı budur.
- OpenAPI şemasına karşı doğrulama otomatikleştirilebilir.

## 7. Kapsam (coverage) — EŞİK %80, istisnasız (global kural #29)

**KARAR (13/09/2026, kullanıcı kararı — "irademdir"):** Her kod tabanının
satır kapsamı **en az %80**. Eskiden burada "kapsam hedef değil, teşhis
aracıdır" yazıyordu; o cümle **kaldırıldı** — artık eşik bir kapıdır ve
`dev → test` / `test → prod` promosyonunu bloklar.

### 7.1 Ne ölçülür

- **Satır kapsamı**, her kod tabanı **ayrı**: backend · web · Android · iOS.
  Birleşik ortalama alınmaz.
- Dal ve fonksiyon kapsamı **raporlanır** ama eşik satırdadır. ⚠️ v8 (Vitest)
  yalnız **yüklenen** dosyaların dallarını sayar — hiç import edilmeyen
  dosyalar dal paydasına girmez, dal yüzdesi bu yüzden şişkin görünür.
- E2E sayılmaz. Senaryoyu ölçer, satırı değil; ayrı kapıdır.

### 7.2 Payda — neyi çıkarmak serbest

Yalnız **üretilmiş ya da ürün olmayan** kod:

| Yığın | Çıkarılabilir |
|---|---|
| .NET | `Migrations/`, `*ModelSnapshot.cs`, `*.Designer.cs`, `obj/`, `*.g.cs` |
| TS/React | `*.test.ts(x)`, `*.d.ts`, `e2e/`, `*.config.ts` |
| Android | `R`, `BuildConfig`, Hilt/Room/Compose üretilmiş sınıfları |
| iOS | test hedefleri, üretilmiş kaynak erişimcileri |

Çıkarma listesi projede **tek dosyada** ve her kalıp gerekçesiyle durur.
⚠️ **El yazısı ürün kodu listeye giremez** — test etmesi zor olan dosya
(HTTP istemcisi, açılış kodu) da dahil. Zor dosya **sahte bağımlılıkla**
test edilir (sahte `HttpMessageHandler`, sahte saat), paydadan çıkarılmaz.

⚠️ **Ham sayı yanıltır.** Proje B backend'i (12/09/2026): göçler dahil
%95,0 — göçler çıkarılınca **%83,0**. EF göçleri testlerde kendiliğinden
çalışır ve paydanın %85'ini oluşturuyordu.

### 7.3 Kapı

- Projenin yerel kapı betiğinde, **promosyon modunda** koşan adım; eşik
  altında çıkış kodu ≠ 0. CI aynı betiği çağırır (#19).
- Ölçülemeyen kod tabanı **"ölçülmedi"** diye raporlanır ve promosyonu
  **yine bloklar** — koşmayan kapı geçilmiş sayılmaz.
- Eşik projede düşürülmez; proje `CLAUDE.md`'si bu eşiği ezemez.

### 7.4 Yığın başına komut

```bash
# .NET — coverlet (xunit şablonunda hazır gelir), cobertura çıktısı
dotnet test <sln> --collect:"XPlat Code Coverage" --results-directory <dizin>
# iki test projesi ayrı dosya üretir; aynı satır ikisinde olabilir →
# satırların BİRLEŞİMİ alınır, toplam değil

# Vitest — @vitest/coverage-v8; eşik yapılandırmada
#   coverage: { include: ['src/**/*.{ts,tsx}'], thresholds: { lines: 80 } }
npx vitest run --coverage

# Android — Kover (Gradle eklentisi; eklemeden önce sor, global #10)
./gradlew koverVerify          # koverVerify { rule { minBound(80) } }

# iOS
xcodebuild test ... -enableCodeCoverage YES -resultBundlePath <yol>
xcrun xccov view --report --json <yol>.xcresult
```

### 7.5 Kapsam için yazılan testin kalitesi

- Assert'sız, yalnız "çalıştırıp geçen" test **yasak** — eşiği gevşetmekle
  aynıdır.
- Eklenen her testin bir şey yakaladığı **mutasyonla** doğrulanır: test
  ettiği satır bozulunca kırmızıya dönmeli. Dönmüyorsa test sayılmaz.
- Kritik iş mantığında (para, yetki, durum makinesi) %80 **taban**dır,
  hedef değil — orada daha yükseği beklenir.
- Mutation testing (Stryker) kritik modüllerde değerlidir — "test var ama
  hiçbir şey yakalamıyor" durumunu ortaya çıkarır.

## 8. Flaky test politikası

- Flaky test **derhal** ya düzeltilir ya karantinaya alınır (issue açılarak). Sessizce `retry` eklemek yasak.
- Yaygın nedenler: zamanlama (`sleep`), paylaşılan veri, sıra bağımlılığı, gerçek ağ, saat dilimi, rastgelelik.
- Karantinadaki test 2 hafta içinde çözülmezse silinir veya sahiplenilir; sonsuza dek görmezden gelinmez.

## 9. Testler ne zaman değişir

- Davranış değiştiyse test değişir — **bu normaldir**.
- Yalnız refactor yapıldıysa test değişmemelidir. Refactor'da test kırılıyorsa test implementasyona fazla bağlıdır.
- **Testi "geçsin diye" gevşetmek yasak** — assert silmek, `Skip` eklemek, eşiği düşürmek. Neden kırıldığı anlaşılmadan dokunulmaz.
- Obsolete edilen alanın testi, alan gerçekten kaldırılana dek yaşar.

## 10. CI'da testler

- Hızlı kapı (unit + tsc + lint) **her push'ta**.
- Yavaş/state'li testler (canlı DB, e2e) ayrı iş akışında veya elle tetiklenir — hızlı kapıya karıştırılmaz.
- Test çıktısı okunabilir olmalı; başarısız testin **neden** başarısız olduğu log'dan anlaşılmalı.
- Testler yerelde de aynı komutla koşabilmeli (`npm test`, `dotnet test`) — CI'ya özel sihir yok.
