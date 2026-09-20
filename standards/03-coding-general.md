# Genel Kodlama Standartları (dilden bağımsız)

## 1. İsimlendirme

- Kod adları **İngilizce**, yorumlar ve dokümanlar **Türkçe**.
- İsim niyeti anlatır: `d` değil `daysUntilExpiry`; `handleData` değil `normalizeMemberRow`.
- Boolean'lar `is/has/can/should` ile başlar: `isActive`, `canEditProfile`.
- Fonksiyon adı **fiil**, sınıf/tip adı **isim**. Kısaltma yok (`usr`, `mgr`, `tmp`).
- Aynı kavram her yerde aynı kelimeyle anılır. `Member` / `User` / `Person` karışımı yasak.
- Negatif isim yok: `isNotDisabled` değil `isEnabled`.

## 2. Fonksiyon ve dosya boyutu

- Fonksiyon tek iş yapar; 40 satırı geçtiyse gözden geçir.
- **Dosya 300 satırı geçmez** — doğal sınırlarından bölünür. Bölme davranışı değiştirmez.
- İç içe geçme (nesting) 3 seviyeyi aşmaz → erken `return` / guard clause kullan.
- Parametre sayısı 4'ü geçtiyse obje/record ile grupla.
- Boolean parametre yerine ayrı fonksiyon veya enum (`render(true)` okunmaz).

## 3. Tek kaynak (single source of truth)

- URL / port / host / anahtar / sabit eşik → **tek config modülü**. Her dosyada `?? "http://localhost:5080"` gibi tekrarlanan fallback yasak.
- Aynı iş mantığı iki yerde yazılmaz. Kopyalanan üçüncü kod ortak yere taşınır (iki kez tolere edilir, üçüncüde refactor).
- Enum / sabit listesi tek yerde; istemci ve sunucu paylaşıyorsa üretilmiş tip veya paylaşılan paket kullanılır.
- Magic string/number yok: `if (status == 3)` → `if (status == MemberStatus.Active)`.

## 4. Hata yönetimi

- **Sessiz yutma yasak:** `catch {}`, `catch (e) { return null; }` (log'suz), `.catch(() => {})`.
- Yakalanan hata ya işlenir ya zenginleştirilip yeniden fırlatılır. Sadece log'layıp yutmak "işlenmiş" sayılmaz.
- Beklenen hata (validasyon, bulunamadı, yetkisiz) exception ile değil, tipli sonuç veya uygun HTTP durumu ile ifade edilir. Exception **istisnai** durumlar içindir.
- Kullanıcıya teknik detay gösterilmez; log'a **tam** detay + correlation id yazılır.
- Hata mesajı içine PII/token/parola konmaz.
- `finally` / `using` / `defer` ile kaynak her yolda serbest bırakılır.

## 5. Null ve sınır durumlar

- Nullable açıkça modellenir (C# nullable reference types açık, TS `strict` açık).
- Dış dünyadan gelen her şey (HTTP, dosya, DB, env) **doğrulanmadan** kullanılmaz.
- Boş liste, tek eleman, çok eleman, çok uzun metin, unicode/emoji, negatif sayı, sıfır, gelecek/geçmiş tarih senaryoları düşünülür.
- Tarih/saat **UTC** saklanır ve taşınır; yalnız gösterimde yerel saate çevrilir. Saat dilimi bilgisi kaybedilmez.
- **Tarih biçimlendirmede kültür açıkça verilir.** .NET/PowerShell'de biçim dizesindeki `/` sabit karakter değil, **kültürün tarih ayracıdır**; `:` de saat ayracıdır. Türkçe locale'li bir makinede `Get-Date -Format 'dd/MM/yyyy'` → `15.08.2026` üretir — yani global kural #12'yi (`dd/mm/yyyy`, nokta yasak) makinenin diline göre sessizce ihlal eder. Aynı tuzak okuma yönünde daha beterdir: `[datetime]::ParseExact(x, 'dd/MM/yyyy', $null)` CurrentCulture'a düşer ve `15/08/2026`'yı **ayrıştıramayıp istisna atar** — yazan ile okuyan aynı kodda bile buluşamaz. Doğrusu her iki yönde de `[cultureinfo]::InvariantCulture` geçmektir. Testi kolay: kültürü `tr-TR`'ye zorlayıp yaz→oku turunu koştur.
- Para `decimal` (C#) veya tam sayı kuruş ile tutulur; `double`/`float` ile para hesabı **yasak**. Para birimi tutarla birlikte saklanır.

## 6. Async

- Async yol boydan boya async'tir; senkron bloklama (`.Result`, `.Wait()`, `Task.Run` sarmalama) yasak.
- Her dış çağrıda **timeout** ve gerektiğinde **cancellation token** vardır.
- Yeniden deneme yalnız **idempotent** işlemlerde, exponential backoff + jitter ile, üst sınırlı.
- Paralel çalıştırılabilir bağımsız işler paralel çalıştırılır; sıralı bağımlılık varsa sıralı.
- Fire-and-forget iş yok — ya beklenir ya kalıcı bir kuyruğa yazılır.

## 7. Yorum ve doküman

- Yorum **neden**'i anlatır, **ne**'yi değil. Kodun tekrarı olan yorum silinir.
- Karmaşık iş kuralının yanına kaynağı yazılır ("mevzuat X, madde Y" / "ADR-004").
- `TODO` yazılıyorsa sahibi ve bağlamı ile: `// TODO(<ad>, 2026-07): X netleşince Y'yi kaldır`. Sahipsiz TODO yasak.
- **Yorum satırına alınmış kod commit edilmez** — git zaten hatırlıyor.
- Public API/servis metodu ne yaptığını, hangi hataları döndürdüğünü belgeler.

## 8. Ölü kod ve bağımlılık

- Kullanılmayan fonksiyon, import, dosya, feature flag, env değişkeni silinir.
- Yeni bağımlılık eklemeden önce: gerçekten gerekli mi, bakımlı mı (son commit, açık issue), lisansı uygun mu, boyutu ne, tek fonksiyon için mi ekleniyor?
- Bağımlılık sürümleri sabitlenir (lock file commit edilir).

## 9. Log

- Yapılandırılmış log (key-value), string birleştirme değil.
- Seviye: `Debug` (geliştirme), `Information` (iş olayı), `Warning` (beklenen ama istenmeyen), `Error` (işlem başarısız), `Critical` (sistem tehlikede).
- Her istek/işlem bir **correlation id** taşır; log'lar bununla eşleştirilir.
- Log'a asla: parola, token, kart no, TCKN, tam e-posta/telefon (maskele), tam istek gövdesi.
- Döngü içinde log yok; toplu özet log.

## 10. Değişmezlik ve saflık

- Mümkün olduğunca immutable veri (record, readonly, `const`). Parametre mutasyonu yapılmaz.
- Saf fonksiyonlar (yan etkisiz) tercih edilir — test edilmesi kolaydır.
- Global mutable state yok; durum ya DI ile ya açık parametre ile taşınır.

## 11. Kod inceleme öncesi kendine sor

- Bu değişikliği 6 ay sonra ben okusam anlar mıyım?
- Bir şey bozulursa **nasıl fark ederiz** (log/metrik/test var mı)?
- Bu kod yanlış kullanılabilir mi? Yanlış kullanımı derleyici veya tip sistemi engelliyor mu?
- Silinmesi gereken bir şey bıraktım mı?

## UUIDv7'den benzersizlik türetme

UUIDv7 **zaman sıralıdır**: ilk 48 bit (metin biçiminde ilk ~8 onaltılık karakter)
bir milisaniye zaman damgasıdır. Aynı milisaniyede üretilen iki kimlik bu kısmı
**paylaşır**.

Kimliğin bir parçasından kısa bir ayırt edici (önek, kısa kod, dizin adı, kiracı
etiketi) türetiliyorsa **sondan** al, baştan değil:

```csharp
// YANLIŞ — ilk 8 karakter zaman damgası; eşzamanlı iki kayıt aynı öneki alır
var prefix = $"tb-{id:N}"[..11];

// DOĞRU — rastgele kısım sondadır
var prefix = $"tb-{id.ToString("N")[^8..]}";
```

Bunun bedeli yalnız "çirkin çakışma" değil: önek verinin **sahipliğini** belirliyorsa
(temizlik neyi silecek, hangi kayıt kimin) iki paralel iş birbirinin verisini siler.
Testi kolay: aynı anda iki kimlik üret, öneklerin farklı olduğunu doğrula.
