# Veritabanı Standartları

## 1. İsimlendirme

- Tablo: çoğul `PascalCase` (EF varsayılanı) veya `snake_case` — **proje içinde tek stil**, karıştırılmaz.
- Kolon: alan adı net; kısaltma yok. Boolean `Is*`/`Has*`.
- Foreign key: `<Entity>Id` (`MemberId`). İndeks adı `IX_<Tablo>_<Kolonlar>`, FK adı `FK_<Tablo>_<HedefTablo>_<Kolon>`.
- Rezerve kelime kullanılmaz (`user`, `order`, `group` → `Users`, `Orders`, `MemberGroups`).

## 2. Şema kuralları

- Her tabloda **surrogate PK** (`int identity` veya `uuid`). Doğal anahtar PK yapılmaz (değişebilir).
- Her tabloda audit kolonları: `CreatedAt` (UTC), `CreatedByMemberId`, `UpdatedAt`, `UpdatedByMemberId`.
- Zaman **UTC** (`timestamptz`). Yerel saat saklanmaz.
- Para: `numeric(19,4)` + ayrı `Currency` kolonu. `float`/`real` ile para **yasak**.
- Metin: sınırsız `text` yerine iş kuralına uygun `varchar(n)` — ama sınır **daraltmak kırıcıdır** (bkz. `08-backward-compatibility.md`).
- Enum DB'de `int` veya `varchar` olarak saklanır; **`int` ise değerlerin sayısal karşılığı asla değişmez**, araya değer eklenmez.
- Referans bütünlüğü DB'de FK ile zorlanır — "uygulama nasılsa kontrol ediyor" yeterli değil.
- Silme davranışı açıkça seçilir (`Restrict` varsayılan; `Cascade` yalnız gerçek sahiplik ilişkisinde).

## 3. İndeksler

- Her FK'ye indeks (Postgres otomatik oluşturmaz).
- Sık filtrelenen/sıralanan kolonlara indeks; **sıra önemli** (eşitlik kolonları önce, aralık sonra).
- Kapsayıcı (covering) indeks büyük listelerde `INCLUDE` ile.
- Tekil kısıt iş kuralıysa `UNIQUE` — ama **var olan tabloya yeni UNIQUE eklemek kırıcıdır** (önce veri temizliği + doğrulama).
- Kullanılmayan indeks silinir (yazma maliyeti). `pg_stat_user_indexes` ile periyodik kontrol.
- Aksan/harf-boyutu bağımsız arama için `unaccent(lower(col))` üzerinde functional index veya `pg_trgm` GIN.

## 4. Migration disiplini

- **Her şema değişikliği migration ile.** Elle SQL çalıştırıp "sonra migration yazarım" yasak.
- Migration adı ne yaptığını söyler: `AddPhoneNumbersToMember`, `20260729_...`.
- Üretilen SQL **okunur** — EF'in ürettiğine körü körüne güvenilmez.
- Bir migration = bir mantıksal değişiklik. Şema + büyük veri taşıma aynı migration'da olmaz.
- `Down` yazılır veya geri alma planı belgelenir.
- Uzun süren işlem üretimi kilitler: Postgres'te `CREATE INDEX CONCURRENTLY`, kolon ekleme varsayılansız (PG11+ hızlı), `ALTER TYPE` yerine yeni kolon.
- Migration'lar **ileri doğru** birikir; geçmiş migration düzenlenmez (uygulanmış olabilir).

## 5. Sorgu kuralları

- `SELECT *` yasak — gereken kolonlar seçilir.
- **N+1 yasak**: döngü içinde sorgu yok; join/projeksiyon ile tek sorgu.
- Sayfalamasız liste sorgusu yok; `OFFSET` derinleştikçe yavaşlar → büyük setlerde keyset/cursor.
- Ham SQL **parametreli**; string birleştirme = SQL injection.
- Sorgu planı şüpheliyse `EXPLAIN ANALYZE` ile bakılır; "yavaş" tahminle optimize edilmez.
- Uzun sorgulara `statement_timeout` uygulanır.

## 6. Transaction

- Transaction sınırı = **servis metodu** (bir iş birimi). Controller'da veya repository'de değil.
- Transaction içinde **dış çağrı yapılmaz** (HTTP, e-posta, kuyruk) — kilit süresi uzar, tutarsızlık doğar. Dış etki commit sonrası (outbox pattern).
- İzolasyon seviyesi bilinçli seçilir; varsayılan `ReadCommitted`. Kayıp güncelleme riski varsa optimistic concurrency (`xmin`/`rowVersion`).
- Deadlock ihtimaline karşı kaynaklara **aynı sırada** erişilir.

## 7. Silme politikası

- Kullanıcı verisi genelde **soft delete** (`DeletedAt`, `DeletedByMemberId`) + global query filter.
- Soft delete kullanılıyorsa: unique index'ler `WHERE DeletedAt IS NULL` ile kısmi olmalı.
- Hard delete yalnız KVKK/GDPR silme talebi veya çöp veri temizliği için, **onayla**.
- Silme bir **ürün kararıdır** — kim silebilir, ne kadar süre geri alınabilir, kullanıcı sorulmadan varsayılmaz.

## 8. Çok kiracılılık (multi-tenant)

- Tenant ayrımı **her sorguda** zorunlu — global query filter + testle doğrulanır.
- Filtreyi atlayan (`IgnoreQueryFilters`) her kullanım gerekçeli yorum taşır.
- Tenant sızıntısı için otomatik test yazılır ("A tenant'ı B'nin kaydını göremez").

## 9. Yedekleme ve kurtarma

- Günlük otomatik yedek + haftalık **sunucu dışı** kopya.
- **Ayda bir restore provası.** Denenmemiş yedek, yedek değildir.
- Yedek saklama süresi ve şifreleme tanımlı.
- `DROP`/toplu `UPDATE` öncesi elle yedek + önce test ortamında deneme.
- Point-in-time recovery hedefi (RPO/RTO) yazılı olsun.

## 10. Seed ve test verisi

- Seed **idempotent** olur (iki kez çalışınca çift kayıt yok).
- Test verisi gerçekçi: Türkçe karakterli isimler, uzun metinler, sınır değerler, boş alanlar.
- Üretim verisi geliştirme ortamına **maskelenmeden** kopyalanmaz (KVKK).

## 11. Yapma listesi

- ❌ Elle şema değişikliği (migration'sız)
- ❌ `SELECT *`, N+1, sayfalamasız liste
- ❌ Para için `float`
- ❌ Yerel saat saklamak
- ❌ Enum sayısal değerini değiştirmek / araya değer eklemek
- ❌ Transaction içinde HTTP/e-posta çağrısı
- ❌ Yedek almadan `DROP`
- ❌ Test/prod veritabanını karıştırmak (connection string ortam bazlı ve kontrollü)
