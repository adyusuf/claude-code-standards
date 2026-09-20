# Sunucu ve Uygulama Sertleştirme

> Cloudflare ilk hattır ama **tek hat değildir**. Origin bypass edilebilir;
> origin kendi başına da ayakta durmalı.

## 1. Uygulama seviyesi — üretimde kapalı olacaklar

- [ ] Detaylı hata sayfası / stack trace (`ASPNETCORE_ENVIRONMENT=Production`)
- [ ] Swagger / OpenAPI UI (veya Cloudflare Access arkasında)
- [ ] Developer exception page, hot reload, source map (public erişime açık source map yok)
- [ ] Seed/demo endpoint'leri, test kullanıcıları, `/debug`, `/admin/tools`
- [ ] `Server`, `X-Powered-By`, `X-AspNet-Version` header'ları
- [ ] Directory listing
- [ ] Varsayılan parolalar (DB, panel, admin hesabı)

## 2. HTTP güvenlik başlıkları (üretimde `curl -I` ile doğrulanır)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()
Cross-Origin-Opener-Policy: same-origin
```

- CSP önce **Report-Only** ile açılır, ihlaller izlenir, sonra zorlayıcı yapılır.
- `unsafe-inline`/`unsafe-eval` kabul edilmez; gerekiyorsa nonce/hash.
- Başlıklar tek yerde (middleware veya edge) tanımlanır, sayfa sayfa değil.

## 3. TLS

- TLS 1.2 minimum, 1.3 tercih. SSLv3/TLS1.0/1.1 kapalı.
- Zayıf cipher'lar (RC4, 3DES, CBC-SHA1) kapalı.
- Sertifika otomatik yenilenir; **yenileme başarısızlığı alarm üretir**.
- HTTP → HTTPS kalıcı yönlendirme (301).
- İç ağ trafiği de (Cloudflare↔origin) şifreli (Full Strict).

## 4. Ağ / firewall

- Inbound yalnız gerekli portlar. İdeal: **hiç inbound yok** (Cloudflare Tunnel).
- Tünel yoksa 80/443 **yalnız Cloudflare IP aralıklarına** açık; IP listesi periyodik güncellenir.
- Veritabanı portu (5432/1433) **internete asla açık değil** — yalnız localhost veya özel ağ.
- Yönetim erişimi (SSH/RDP): public'e kapalı; VPN / Cloudflare Access / IP kısıtı arkasında.
- SSH: parola girişi kapalı, yalnız anahtar; root girişi kapalı; `fail2ban`.
- RDP: NLA açık, varsayılan port değişimi tek başına güvenlik değildir — erişim kısıtı esas.

## 5. İşletim sistemi

- Otomatik güvenlik güncellemeleri açık; kritik yamalar 7 gün içinde.
- Uygulama **root/Administrator olmayan** özel kullanıcı ile koşar.
- Dosya izinleri en az yetki: uygulama dizinine yazma yalnız gerektiği yerde; yükleme klasörü **çalıştırma yetkisiz**.
- Kullanılmayan servis/rol kapatılır.
- Disk şifreleme; yedek diski de şifreli.
- Zaman senkronizasyonu (NTP) — token doğrulama ve log korelasyonu buna bağlı.
- Log'lar merkezileştirilir (sunucu ele geçirilirse yerel log silinebilir).

## 6. IIS'e özel (Windows)

- Uygulama havuzu kimliği ayrı ve az yetkili; havuz izolasyonu (site başına ayrı pool).
- **Test ve prod ayrı site + ayrı pool + ayrı fiziksel dizin** — karıştırılırsa prod'a test kodu yazılır.
- `web.config`'te: `customErrors` on, `httpErrors` detay gizli, request filtering (istek boyutu, uzantı).
- Request Filtering ile gizli dosyalar engellenir (`.env`, `.git`, `appsettings*.json`, `*.bak`, `*.pdb`).
- Auto-pull/deploy görevleri hangi dizini güncellediğini log'lar; yanlış ortam koruması var.

## 7. Docker / konteyner

- Non-root user (`USER app`); read-only root filesystem mümkünse.
- Minimal base image (alpine/distroless/`-slim`); base tag **sabitlenmiş** (`:latest` yasak).
- `.dockerignore` ile `.env`, `.git`, `node_modules`, sırlar image'a girmez.
- Image güvenlik taraması (Trivy/Docker Scout) CI'da.
- Sır ortam değişkeni veya secret mount ile; **image katmanına gömülmez** (`ARG` ile gelen sır katmanlarda kalır).
- Kaynak limitleri (CPU/memory) tanımlı; konteyner kaçağı tüm makineyi düşürmesin.
- Health check tanımlı.

## 8. Veritabanı sertleştirme

- Uygulama kullanıcısı **en az yetkili** (DDL yetkisi yok; migration ayrı kullanıcıyla).
- `postgres`/`sa` süper kullanıcısıyla uygulama bağlanmaz.
- Bağlantı SSL/TLS ile; `sslmode=require` (tercihen `verify-full`).
- Dinleme adresi kısıtlı; `pg_hba.conf` dar.
- Varsayılan/örnek veritabanları ve kullanıcılar kaldırılır.
- Yedekler şifreli ve erişimi kısıtlı (`21-yedekleme-ve-kurtarma.md`).

## 9. CI/CD sertleştirme

- Actions izinleri `permissions: contents: read` varsayılan; gerekli olan iş bazında açılır.
- Third-party action'lar **commit SHA** ile pinlenir.
- `pull_request_target` ve fork'tan gelen PR'larda sırlar **erişilemez** olmalı.
- Self-hosted runner public repo'da kullanılmaz (kod çalıştırma riski).
- Deploy anahtarları dar kapsamlı; ortam bazlı ayrı.
- Build log'unda sır maskeleme doğrulanır.

## 10. Periyodik kontrol (3 ayda bir)

- [ ] Bağımlılık CVE taraması ve yükseltmeler
- [ ] OS + Docker image yamaları
- [ ] TLS yapılandırması (SSL Labs / `testssl.sh`) — hedef A
- [ ] Güvenlik başlıkları (securityheaders.com) — hedef A
- [ ] Açık port taraması (dışarıdan `nmap`)
- [ ] Erişim listesi gözden geçirme: kimin hangi panele erişimi var, ayrılanlar kaldırıldı mı
- [ ] Sır rotasyonu takvimi
- [ ] Yedek restore provası
- [ ] Log'da PII sızıntısı örneklemesi
- [ ] Kullanılmayan alt alan adı / DNS kaydı temizliği

## 11. Yapma listesi

- ❌ Uygulamayı root/Administrator ile koşturmak
- ❌ DB portunu internete açmak
- ❌ Prod'da Swagger / detaylı hata / source map
- ❌ Parola ile SSH
- ❌ `:latest` image tag'i
- ❌ Sırrı Dockerfile `ARG`/`ENV` ile image'a gömmek
- ❌ Cloudflare'e güvenip origin'i açık bırakmak
- ❌ Güvenlik başlıklarını "sonra ekleriz" diye ertelemek
- ❌ Yükleme klasörüne çalıştırma yetkisi vermek
