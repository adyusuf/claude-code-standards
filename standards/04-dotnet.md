# .NET Standartları (Web API)

## 1. Katmanlar

```
Controllers/Endpoints  → HTTP sözleşmesi, model binding, yetki, HTTP durum kodu
Services               → iş mantığı, transaction sınırı, domain kuralları
Data (DbContext/Repo)  → sorgu, persistence
Contracts (DTO)        → dışa açılan tipler
Domain (Entity/Enum)   → model
```

Kurallar:
- Controller **ince** olur: doğrula → servisi çağır → sonucu HTTP'ye çevir. İş mantığı controller'da durmaz.
- **Entity dışarı sızmaz.** Request/response için ayrı DTO. `DbSet<Member>` doğrudan döndürülmez (lazy loading, over-posting, döngüsel referans, geriye uyumluluk riski).
- Servis DbContext'i kullanır; controller DbContext'e dokunmaz.
- Katmanlar arası bağımlılık tek yönlü. Servisin `HttpContext`'e ihtiyacı varsa arayüz arkasına alınır (`ICurrentUser`).

## 2. Proje ayarları

```xml
<Nullable>enable</Nullable>
<TreatWarningsAsErrors>true</TreatWarningsAsErrors>
<ImplicitUsings>enable</ImplicitUsings>
<AnalysisLevel>latest-recommended</AnalysisLevel>
```

- `.editorconfig` repoda; `dotnet format` PR öncesi zorunlu.
- Uyarı bastırma (`#pragma warning disable`) gerekçe yorumu olmadan yasak.

## 3. Dependency Injection

- Yaşam süreleri: `Scoped` (DbContext, servisler), `Singleton` (stateless yardımcılar, config), `Transient` (hafif, durumsuz).
- **Captive dependency yasak:** Singleton içine Scoped enjekte edilmez.
- Servis Locator anti-pattern'i (`IServiceProvider.GetService` iş kodunda) yok — constructor injection.
- Her servis bir arayüz arkasında olmak zorunda değil; **yalnız** birden fazla implementasyon veya test double gerekiyorsa arayüz açılır.

## 4. Konfigürasyon

- Güçlü tipli options: `IOptions<T>` / `IOptionsSnapshot<T>` + `ValidateOnStart()`.
- Sır asla `appsettings.json`'da değil: User Secrets (dev), env değişkeni / secret store (prod).
- `IConfiguration["x"]` iş kodunun içinde okunmaz — options sınıfına bağlanır.
- Eksik zorunlu ayar **uygulama açılışında** patlar, ilk istekte değil.

## 5. EF Core

- **Sadece okuma sorgularında `AsNoTracking()`.**
- **N+1 yasak.** İlişkili veri `Include`/`ThenInclude` veya projeksiyonla tek sorguda alınır. Loop içinde sorgu yok.
- Liste endpoint'i **her zaman** `Select` ile DTO'ya projeksiyon yapar — tüm entity çekilmez.
- `IQueryable` servis sınırının dışına çıkmaz (controller'a `IQueryable` dönmek yasak).
- Client-side evaluation'a düşen sorgu düzeltilir (log'da uyarı çıkar).
- Migration'lar isimlendirilir ve gözden geçirilir; üretilen SQL okunur. Detay: `09-veritabani.md`.
- Toplu işlemde `ExecuteUpdateAsync`/`ExecuteDeleteAsync` veya batch; tek tek `SaveChanges` döngüsü yok.
- `SaveChangesAsync` **bir iş biriminde bir kez** çağrılır (transaction sınırı = servis metodu).
- Global query filter kullanılıyorsa (tenant, soft delete) bunu atlayan sorgu bilinçli ve yorumlu olmalı.

## 6. Validasyon

- Model doğrulama DTO seviyesinde (DataAnnotations veya FluentValidation) — **tek yaklaşım** seçilir, karıştırılmaz.
- İş kuralı validasyonu serviste (ör. "bu e-posta zaten kayıtlı").
- Doğrulama hatası → `400` + `ValidationProblemDetails` (alan bazlı hata sözlüğü).
- **Yeni zorunlu alan eklemek kırıcıdır** — bkz. `08-geriye-uyumluluk.md`.

## 7. Hata yönetimi ve HTTP

- Merkezî exception handler middleware; her controller'da try/catch tekrarı yok.
- Hata gövdesi **ProblemDetails** (RFC 7807) + `traceId`.
- Durum kodları: `200/201/204`, `400` validasyon, `401` kimlik yok, `403` yetki yok, `404` bulunamadı, `409` çakışma, `422` iş kuralı, `429` limit, `500` beklenmeyen.
- Beklenen durum için exception fırlatma (kontrol akışı olarak exception yok).
- Üretimde stack trace dışarı verilmez.

## 8. Async

- Tüm I/O async; `async Task`, `void` değil (event handler hariç).
- `CancellationToken` controller'dan servise, servisten EF/HttpClient'a **taşınır**.
- `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` yasak.
- `HttpClient` **IHttpClientFactory** ile (named/typed client) — `new HttpClient()` yasak. Polly ile timeout + retry (idempotent çağrılarda) + circuit breaker.

## 9. Güvenlik (detay: `15-guvenlik.md`)

- Her endpoint `[Authorize]`; açık uçlar **açıkça** `[AllowAnonymous]`. Varsayılan politika fail-closed.
- Yetki kontrolü kaynak sahipliğini de kapsar (IDOR): "bu kaydı bu kullanıcı görebilir mi?"
- Over-posting'e karşı ayrı input DTO (entity'ye doğrudan bind yok).
- Ham SQL kullanılıyorsa **parametreli**; string birleştirme yasak.
- CORS beyaz liste; `AllowAnyOrigin` + credentials kombinasyonu yasak.
- Dosya yükleme: tip + boyut + içerik kontrolü, dosya adı sanitize, web root dışında saklama.

## 10. Arka plan işleri

- `IHostedService`/`BackgroundService`; graceful shutdown desteklenir (`stoppingToken`).
- İstek yaşam döngüsüne bağlı fire-and-forget iş yok — kalıcı kuyruk kullanılır.
- Zamanlanmış iş **idempotent** olmalı; iki kez çalışırsa bozulmamalı.
- Arka plan işinde `IServiceScopeFactory` ile kendi scope'unu aç.

## 11. Test edilebilirlik

- `DateTime.UtcNow` doğrudan kullanılmaz → `TimeProvider` / `IClock` enjekte edilir.
- `Guid.NewGuid()`, `Random`, dosya sistemi, ağ → arayüz arkasında.
- Servis testleri gerçek DB (Testcontainers) veya in-memory ile; in-memory kullanılıyorsa **relational davranış farkları** bilinir (bkz. `10-test-stratejisi.md`).

## 12. Gözlemlenebilirlik

- Serilog/`ILogger<T>` ile yapılandırılmış log; mesaj şablonu kullanılır (`_log.LogInformation("Üye {MemberId} güncellendi", id)`) — string interpolation değil.
- OpenTelemetry ile trace + metrik; `Activity` ile iş adımları işaretlenir.
- `/health` (liveness) ve `/health/ready` (readiness — DB, cache, dış servis) endpoint'leri.

## 13. Performans

- Sıcak yolda LINQ zinciri yerine tek sorgu; gereksiz materialization (`ToList()` sonra `Where`) yok.
- Büyük yanıt → sayfalama zorunlu (`07-api-tasarimi.md`).
- Response compression + output caching uygun yerlerde.
- `IAsyncEnumerable`/streaming büyük veri setleri için.
- Ölçmeden optimize etme; ölçüm için BenchmarkDotNet veya profil.
