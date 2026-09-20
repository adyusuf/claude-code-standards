# Güvenlik Standartları

## 1. Kimlik doğrulama (AuthN)

- Parola: **hiçbir zaman düz metin veya ters çevrilebilir şifreleme**. Argon2id (tercih) veya bcrypt (cost ≥ 12) / ASP.NET Identity varsayılanı.
- Minimum uzunluk 12; karmaşıklık dayatması yerine uzunluk + sızmış parola listesi kontrolü.
- Giriş denemesi hız limiti + hesap kilitleme (kademeli gecikme). Kullanıcı sayımı yapılamasın: "e-posta veya parola hatalı" (hangisi olduğu söylenmez).
- Parola sıfırlama token'ı: tek kullanımlık, kısa ömürlü (15–60 dk), veritabanında **hash'li** saklanır.
- MFA hassas roller için (admin) en azından TOTP.
- Token: kısa ömürlü access (5–15 dk) + refresh (rotasyonlu, kullanıldığında yenisiyle değişir, çalınma tespiti için reuse detection).
- Çıkışta refresh token sunucuda geçersizleştirilir (yalnız istemciden silmek yetmez).

## 2. Yetkilendirme (AuthZ)

- **Fail-closed:** varsayılan reddet. `[Authorize]` global politika; açık uçlar açıkça `[AllowAnonymous]`.
- **Her istekte** yetki kontrol edilir — UI'da gizlemek güvenlik değildir.
- **IDOR kontrolü:** "bu kaydı bu kullanıcı görebilir/değiştirebilir mi?" Kaynak sahipliği her erişimde doğrulanır. `GET /orders/123` — 123 kimin?
- Token claim'ine körü körüne güvenilmez; kritik yetki sunucuda taze veriyle doğrulanır.
- Yetki mantığı tek yerde toplanır (policy/handler), her controller'da `if (role == "Admin")` serpiştirilmez.
- Rol grubu ↔ kademe grubu birleşimi (union) mantığı varsa: **tabana** en düşük kademenin görmemesi gereken izin yazılmaz.
- Yetki değişikliği testle korunur ("X rolü Y kaydını göremez" testi).

## 3. Girdi doğrulama ve injection

- Dış dünyadan gelen **her şey** doğrulanır: HTTP body/query/header/cookie, dosya, webhook, DB'den okunan eski veri.
- SQL: **her zaman parametreli**. String birleştirme yasak. ORM kullanılıyorsa raw SQL bölümleri özellikle incelenir.
- Sıralama/filtre alan adları **beyaz liste** ile eşlenir (`?sort=` doğrudan SQL'e gitmez).
- Komut çalıştırma (shell) mümkünse hiç yapılmaz; zorunluysa argüman dizisiyle, shell interpolation olmadan.
- Deserialization: bilinmeyen tip yükleme (polymorphic deserialization) kapalı.
- Path traversal: kullanıcıdan gelen dosya adı asla yola doğrudan eklenmez; normalize + kök dizin kontrolü.
- SSRF: kullanıcıdan gelen URL'e istek atılmaz; zorunluysa şema/host beyaz listesi + iç IP aralıkları engellenir.

## 4. XSS ve tarayıcı tarafı

- React varsayılan olarak kaçış yapar — `dangerouslySetInnerHTML` gerekçesiz kullanılmaz; kullanılırsa DOMPurify.
- Content-Security-Policy başlığı tanımlı (`default-src 'self'`, inline script'e izin yok — nonce/hash kullan).
- Token depolama: **httpOnly + Secure + SameSite cookie tercih edilir**. `localStorage` XSS'e açıktır; kullanılıyorsa risk yazılı kabul edilir. (Tek-origin dağıtım cookie'yi kolaylaştırır — `14-devops.md` §8.)
- CSRF: cookie tabanlı auth kullanılıyorsa anti-forgery token + `SameSite=Lax/Strict`.
- Açık yönlendirme (open redirect): `returnUrl` beyaz listeye/aynı origin'e sınırlanır.

## 5. Güvenlik başlıkları (minimum)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
X-Frame-Options: DENY            (CSP frame-ancestors ile birlikte)
```

- `Server`, `X-Powered-By`, `X-AspNet-Version` başlıkları kaldırılır.
- Detay ve edge tarafı: `20-hardening.md`.

## 6. Sır yönetimi

- Sır **asla** koda, `appsettings.json`'a, log'a, hata mesajına, CI çıktısına, ekran görüntüsüne girmez.
- Depolama: dev → User Secrets / gitignore'lu `.env`; CI → Actions Secrets; prod → env / secret store.
- Envanteri `SETUP.md`'de tutulur (`18-setup-and-environment.md`): ne, nereden alınır, nerede durur, sahibi kim, geçerlilik/rotasyon.
- **Sızıntı prosedürü:** 1) hemen rotate 2) etki analizi (log'da kullanım var mı) 3) geçmiş temizliği 4) neden sızdı → önlem.
- CI'da sır taraması (gitleaks) + `pre-commit` hook zorunlu.
- Mobil bundle'a sır gömülmez — mobil istemcide gerçek sır yoktur (bundle açılabilir).

## 7. Kişisel veri (KVKK / GDPR)

- **Veri minimizasyonu:** ihtiyaç olmayan kişisel veri toplanmaz, saklanmaz.
- Hassas veri (TCKN, sağlık, biyometrik) şifreli saklanır; erişim log'lanır.
- Log'a PII yazılmaz; zorunluysa maskelenir (`a***@gmail.com`, `+90 5** *** ** 34`).
- Saklama süresi tanımlı; süre dolunca silme/anonimleştirme otomatik.
- Silme talebi (unutulma hakkı) için teknik yol hazır olmalı — yedeklerdeki durum da düşünülür.
- Üretim verisi geliştirme/test ortamına **maskelenmeden** kopyalanmaz.
- Veri işleyen üçüncü taraflar (Cloudflare, e-posta sağlayıcı, AI API) envanterde ve aydınlatma metninde.
- **AI/LLM'e gönderilen veri:** müşteri PII'si sağlayıcıya gitmeden önce maskelenir veya rıza alınır; hangi verinin gittiği belgelenir.

## 8. Bağımlılıklar ve tedarik zinciri

- Lock file commit edilir; sürümler sabit.
- CI'da CVE taraması (`dotnet list package --vulnerable`, `npm audit`, Dependabot/Renovate).
- Kritik/yüksek açık → merge bloke. Yama yoksa risk kabulü yazılı ve süreli.
- Yeni paket: bakımlı mı, indirme sayısı, son commit, lisans, transitive bağımlılık sayısı.
- Typosquatting kontrolü — paket adı iki kez okunur.
- CI action'ları commit SHA ile pinlenir (`uses: actions/checkout@<sha>`), tag ile değil.

## 9. Dosya yükleme

- İzin verilen tip **beyaz liste** (uzantı **ve** içerik/magic byte kontrolü).
- Boyut sınırı; toplam kota.
- Dosya adı sanitize edilir veya yeniden üretilir (GUID); orijinal ad ayrı alanda tutulur.
- Web root dışında veya object storage'da saklanır; **doğrudan servis edilmez** — imzalı URL veya proxy endpoint.
- Kullanıcı yüklenen içerik farklı bir origin'den servis edilir (mümkünse) — XSS izolasyonu.
- Virüs taraması mümkünse.

## 10. Hız limiti ve kötüye kullanım

- Kimlik başına + IP başına hız limiti; hassas uçlarda (giriş, parola sıfırlama, OTP, arama) daha sıkı.
- Aşımda `429` + `Retry-After`.
- Bot/otomasyon koruması edge katmanında (`19-cloudflare-and-edge.md`).
- Pahalı sorgular (rapor, export) kuyruğa alınır veya limitlenir.

## 11. Loglama ve tespit

- Güvenlik olayları ayrıca log'lanır: başarısız giriş, yetki reddi, parola değişimi, rol değişimi, sır erişimi, toplu veri indirme.
- Audit log **değiştirilemez** (append-only); kim, ne zaman, ne yaptı.
- Anormal desenler alarma bağlanır (kısa sürede çok 403, tek IP'den çok hesap denemesi).

## 12. OWASP Top 10 — eşleme tablosu

Her sürüm öncesi bu tablo gözden geçirilir. "Bizde yok" cevabı da yazılı olmalı.

| # | Risk | Bizdeki karşılığı / kontrol |
|---|---|---|
| **A01** | Broken Access Control | Fail-closed politika, her endpoint `[Authorize]`, **IDOR testi** (kaynak sahipliği), yetki mantığı tek yerde, "X rolü Y'yi göremez" testleri. En sık ve en pahalı sınıf — review'da ilk bakılan. |
| **A02** | Cryptographic Failures | TLS 1.2+ uçtan uca (Full Strict), parola Argon2id/bcrypt, hassas veri şifreli, yedekler şifreli, token'lar hash'li saklanır, para/PII log'da yok |
| **A03** | Injection | Parametreli SQL, ORM, sıralama/filtre **beyaz liste**, shell çağrısı yok, XSS için React kaçışı + CSP, template injection kontrolü |
| **A04** | Insecure Design | ADR + tehdit modeli (aşağıda §13), hız limiti, iş kuralı sunucuda, kritik akışta idempotency |
| **A05** | Security Misconfiguration | `20-hardening.md` tamamı: prod'da Swagger/debug kapalı, güvenlik başlıkları, varsayılan parola yok, dizin listeleme kapalı, CORS dar |
| **A06** | Vulnerable & Outdated Components | Lock file, CI'da CVE taraması (`npm audit`, `dotnet list package --vulnerable`, Dependabot), kritik açık merge bloke, action'lar SHA pinli |
| **A07** | Identification & Auth Failures | Hız limiti + kilitleme, kullanıcı sayımına kapalı hata mesajı, refresh rotasyonu + reuse detection, MFA admin'de, oturum sunucuda sonlandırılır |
| **A08** | Software & Data Integrity Failures | Lock file + SHA pinli CI action, imzalı artifact, güvensiz deserialization kapalı, tedarik zinciri kontrolü (typosquatting) |
| **A09** | Security Logging & Monitoring Failures | `17-observability.md`: güvenlik olayları log'lanır, audit log append-only, anormal desen alarmı, correlation id |
| **A10** | Server-Side Request Forgery | Kullanıcıdan gelen URL'e istek atılmaz; zorunluysa şema+host beyaz listesi, iç IP aralıkları (169.254/10./172.16./192.168.) engelli, redirect takibi kapalı |

**API'ye özel (OWASP API Security Top 10):** BOLA/BFLA (nesne ve fonksiyon seviyesi yetki),
aşırı veri ifşası (entity yerine DTO), kaynak tüketimi (sayfalama + rate limit), kütle atama
(over-posting → ayrı input DTO). Bunlar `07-api-design.md` kurallarıyla kapatılır.

**Mobil (OWASP MASVS):** bundle'a sır gömme, güvensiz yerel depolama (token `SecureStore`'da),
zayıf TLS/sertifika doğrulaması kapatma (`trustAllCerts` **yasak**), root/jailbreak varsayımı —
mobil istemcide gerçek sır yoktur.

## 13. Tarama zinciri (CI'da otomatik)

> **Kapsam (global kural #25):** Bu zincir `dev → test` ve `test → prod` promosyonlarında **tam** koşar.
> `feature/* → dev` merge'inde **koşmaz** — tek istisna **pre-commit gitleaks** kancasıdır: yereldedir, saniye sürer
> ve sır sızması geri alınamaz (rotate gerektirir), o yüzden her dalda açık kalır.

| Tür | Ne bulur | Araç | Ne zaman |
|---|---|---|---|
| **Secret scanning** | Repoya sızmış sır | gitleaks / trufflehog | Her push + pre-commit |
| **SCA** | Açıklı bağımlılık | `dotnet list package --vulnerable`, `npm audit`, Dependabot/Renovate, OWASP Dependency-Check | Her push + haftalık |
| **SAST** | Koddaki açık desenleri | CodeQL, SonarQube (`sonar-analyze` skill'i mevcut), Roslyn analyzer, `eslint-plugin-security` | PR'da |
| **DAST** | Çalışan uygulamada açık | **OWASP ZAP** (baseline scan CI'da, full scan periyodik) | Test ortamına deploy sonrası |
| **Container** | Image'daki CVE | Trivy / Docker Scout | Image build'inde |
| **IaC/config** | Yanlış yapılandırma | Checkov / tfsec | Altyapı değişikliğinde |

Kurallar:
- **Kritik/Yüksek bulgu merge'i bloke eder.** Yama yoksa risk kabulü **yazılı ve süreli** olur.
- **SAST her projede bir adımdır ve YERELDE de koşabilmelidir.** CI'ya bağlı
  kalan bir tarama, ancak push'tan sonra ve çoğu zaman başkasının önünde
  konuşur; yerelde koşulabilen tarama commit'ten önce konuşur. Bu yüzden her
  projede `scripts/codeql-scan.sh` (ya da dilin karşılığı) bulunur; CI aynı
  betiği/aynı eşiği kullanır — iki yerde iki farklı kural olmaz.
  Ayrıntı: **§13a**.
- ZAP baseline taraması test ortamına her deploy sonrası koşar; yeni "High" alarm PR'a yorum olarak düşer.
- False positive'ler **dar** istisna ile bastırılır (kural kapatılmaz), gerekçesi yorumda.
- Tarama sonuçları saklanır — trend izlenir, "hep aynı 40 uyarı" durumu temizlenir.

### 13a. SAST'ın yerelde koşması (zorunlu adım)

Her projede SAST **iki yerde aynı şekilde** koşar: geliştiricinin makinesinde
ve CI'da. Tek kaynak ilkesi burada da geçerli — eşik, triyaj listesi ve
raporlayıcı **tek** dosyadadır, CI onu çağırır.

**Kurulum (CodeQL örneği):**

```bash
brew install --cask codeql          # macOS
codeql pack download codeql/<dil>-queries
./scripts/codeql-scan.sh            # tarama + kapı
```

**Betiğin karşılaması gereken şartlar:**

1. **Çıkış kodu kapıdır.** `sev >= 7.0` (CVSS yüksek) triyaj edilmemiş bulgu
   varsa `1` döner. "Rapor basıp 0 dönmek" kapı değildir.
2. **Yanlış pozitif dar ve GEREKÇELİ bastırılır.** Kural kapatılmaz; bulgu
   `ruleId + dosya` ile triyaj dosyasına, **neden gerçek olmadığı** yazılarak
   eklenir. Satır numarası kullanılmaz — kod kaydıkça triyaj sessizce kayar.
3. **Derleme izlenerek veritabanı kurulur.** Derlenen dillerde artımlı derleme
   hiçbir şey derlemezse veritabanı **boş** çıkar ve tarama "temiz" görünür —
   en tehlikeli yanlış negatif. `/t:Rebuild` (ya da dilin karşılığı) şart.
4. **Üretilen/ölü kod elenir** (`obj/`, `bin/`, `generated/`, `node_modules/`,
   port edilmeyi bekleyen eski uygulamalar). Aksi hâlde gerçek bulgular
   gürültüde kaybolur.
5. **Kural bilgisi okunamıyorsa tarama BAŞARISIZ sayılır.** SARIF'te kural
   listesi iki farklı yerde olabilir: `tool.driver.rules` (CodeQL CLI) ve
   `tool.extensions[].rules` (GitHub codeql-action). Yalnız birini okuyan bir
   raporlayıcı, diğer biçimde hiçbir önem derecesi bulamaz ve **her şeyi
   geçirir**; CI yeşil döner ama hiçbir şey korunmaz. İkisi de okunur, hiçbiri
   yoksa hata verilir.
6. **Kapı mutasyon testiyle doğrulanır.** Triyaj listesi boşaltıldığında kapı
   gerçekten `1` dönmelidir. Dönmüyorsa kapı dekoratiftir.

**Private repo notu (GitHub):** CodeQL **analizi ücretsiz**, ücretli olan
bulguları "Security" sekmesine **yüklemek** (GitHub Advanced Security). Private
repoda yükleme `422 Advanced security has not been purchased` ile düşer. Doğru
çözüm SAST'ı kaldırmak değil, `upload: false` ile analizi sürdürüp kapıyı kendi
raporlayıcınla uygulamaktır. `upload: false` olsa bile codeql-action Actions
API'sini okur: iş `permissions: actions: read` ister, yoksa
`Resource not accessible by integration` verir.

### 13b. Sır taramasının yerelde koşması (zorunlu adım)

SAST'ın kardeşi ve aynı disiplin: **iki yerde aynı şekilde** koşar, tek
yapılandırma dosyası, çıkış kodu kapıdır.

```bash
brew install gitleaks                                   # macOS
gitleaks detect --no-banner --redact --config .gitleaks.toml
```

**Şartlar:**

1. **Geçmişi tarar, çalışma dizinini değil.** Sır bir kez commit'lendiyse
   sonraki commit'te silinmesi onu geçmişten çıkarmaz. `detect` (geçmiş) ile
   `protect` (staged) farklı işlerdir; kapı olan `detect`'tir.
2. **Yanlış pozitif YOLA göre değil DEĞERE göre bastırılır.** "Test
   dosyalarını tarama" gibi toptan muafiyet **yasak**: sırların en kolay
   sızdığı yer tam olarak test dosyalarıdır. İzin, dizenin kendisine ve
   gerekçesiyle verilir.
3. **İznin darlığı mutasyonla doğrulanır.** İzin verilen desenin AYNISI,
   BAŞKA bir değerle hâlâ yakalanmalı. Yakalanmıyorsa izin geniştir ve
   kapıyı fiilen kapatmıştır.
4. **Araç kurulu değilse "geçti" DEĞİL "atlandı".** Koşmayan bir kapı
   geçilmiş sayılmaz; rapor bunu ayrı göstermeli ve sonuç yeşil olmamalı.
5. **Sır bulunursa sıra: önce rotate, sonra temizlik.** Geçmişten silmek
   (filter-repo/BFG) ikinci adımdır; sızmış anahtar o ana kadar zaten
   geçerlidir.

**Yaşanmış:** bir depoda iki bulgu çıktı; ikisi de test sabitiydi ve biri
"anahtar ŞİFRELİ saklanıyor mu" testinin dayanağıydı — değeri kaldırmak testi
anlamsız kılardı. Doğru çözüm kuralı kapatmak değil, o iki dizeyi gerekçesiyle
izin listesine yazmaktı.

---

### 13c. Hattın yerelde koşabilmesi

CI kesildiğinde (fatura, kota, ağ, sağlayıcı arızası) doğrulama durmamalı.
Her projede hattaki kapıların **aynısını aynı sırayla** koşan tek bir betik
bulunur (`scripts/ci-local.sh`).

- Yereldeki koşum hattakinden **zayıf olamaz**; iki yerde iki farklı kural,
  "bende çalışıyordu"nun kaynağıdır.
- Yerelde **fazla** olabilir: hatta kurulmayan bağımlılıklar (tarayıcı gibi)
  yerelde zaten varsa o testler de koşar.
- **Atlanan adım sessiz geçmez.** Rapor "ATLANDI" der ve sonuç yeşil değil
  **EKSİK** olur.

**Yaşanmış:** hat faturadan dolayı hiç koşmazken yerel betik ilk denemede
gerçek bir kırık buldu — arayüz derlemesi düşüyordu ve o hâliyle iki dala
push edilmişti.

---

**Derinlemesine kontrol listesi:** hassas/yeni modüllerde OWASP **ASVS Level 2** kontrol listesi
üzerinden elle geçilir (kimlik, oturum, erişim kontrolü, girdi doğrulama, kriptografi, hata/log,
veri koruma, iletişim, kötü niyetli kod, iş mantığı, dosya, API, yapılandırma).

## 14. Tehdit modeli (yeni modül / riskli değişiklik)

Kısa ve pratik — 4 soru:
1. **Ne koruyoruz?** (veri, para, itibar) Hangi kayıt en değerli?
2. **Kim saldırır?** (yetkisiz dış kullanıcı, yetkili ama kötü niyetli üye, ele geçirilmiş hesap, iç kullanıcı)
3. **Nasıl?** STRIDE ile hızlı geçiş: Spoofing / Tampering / Repudiation / Information disclosure / Denial of service / Elevation of privilege
4. **Nasıl fark ederiz?** Hangi log, hangi alarm?

Çıktı 10-15 satır; ADR'ye veya modül dokümanına eklenir.

## 15. Sürüm öncesi güvenlik kontrol listesi

- [ ] Tüm endpoint'ler yetkili; `AllowAnonymous` listesi gözden geçirildi
- [ ] IDOR kontrolü kritik kaynaklarda test edildi
- [ ] Sır taraması temiz; yeni sırlar envantere yazıldı
- [ ] Bağımlılık taramasında kritik açık yok
- [ ] Güvenlik başlıkları üretimde doğrulandı (gerçek `curl -I` ile)
- [ ] Prod'da Swagger/debug/detaylı hata kapalı
- [ ] Hız limiti hassas uçlarda aktif
- [ ] Log'da PII/token yok (örnek log okundu)
- [ ] TLS yapılandırması ve sertifika süresi kontrol edildi
- [ ] Yedek + restore provası güncel (`21-backup-and-recovery.md`)
