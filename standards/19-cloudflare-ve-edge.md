# Cloudflare / Edge Katmanı

## 1. Rol dağılımı

```
Kullanıcı → Cloudflare (DNS + TLS + WAF + rate limit + cache) → Origin (IIS/Nginx/Docker)
```

Cloudflare **ilk savunma hattıdır**, tek savunma değil. Origin kendi başına da güvenli olmalı
(`20-sertlestirme.md`) — Cloudflare bypass edilebilir.

## 2. DNS

- Uygulama kayıtları **Proxied (turuncu bulut)** — origin IP'si gizlenir.
- Proxy'lenmeyen kayıtlar (mail, doğrulama TXT) bilinçli ve listeli olsun; **origin IP'sini sızdıran** kayıt (eski `direct.`, `ftp.`, cPanel kaydı) silinir.
- TTL: proxied kayıtlarda otomatik. Geçiş öncesi düşük TTL (300s), geçiş sonrası normale dön.
- DNSSEC açık.
- E-posta gönderiliyorsa: **SPF + DKIM + DMARC** kayıtları tanımlı. DMARC en az `p=quarantine` hedeflenir.
- Kullanılmayan alt alan adları silinir (subdomain takeover riski).
- Tüm DNS kayıtları `DEPLOY.md`'de tabloyla belgelenir.

## 3. TLS

- SSL/TLS modu: **Full (Strict)**. `Flexible` **yasak** — Cloudflare↔origin arası şifresiz kalır.
- Origin'de geçerli sertifika: Let's Encrypt veya **Cloudflare Origin Certificate** (15 yıl, yalnız CF'den kabul).
- Minimum TLS 1.2 (tercihen 1.3). Eski cipher'lar kapalı.
- **Always Use HTTPS** açık; **HSTS** açık (`max-age=31536000; includeSubDomains`, preload'a ancak emin olunca).
- **Authenticated Origin Pulls** açık — origin yalnız Cloudflare'den gelen isteği kabul eder (bypass kapanır).
- Sertifika süresi alarma bağlı (`17-gozlemlenebilirlik.md` §7).

## 4. Tek origin topolojisi — API, UI'ın altında

**Tercih edilen:** `app.example.com/api/*` (ayrı `api.example.com` değil).

Kazanç:
- **CORS tamamen ortadan kalkar** (preflight, header whitelist, credentials sorunu yok)
- Cookie same-site çalışır → httpOnly + `SameSite=Lax/Strict` gerçekten kullanılabilir; token'ı `localStorage`'a koymak zorunda kalmazsın (XSS yüzeyi küçülür)
- Tek sertifika, tek DNS kaydı, tek WAF/rate-limit politikası
- Backend'in nerede koştuğu dışarıya sızmaz
- Mobil ve web **aynı** base URL'i kullanır

Cloudflare tarafı:
- **Origin Rules / Load Balancer:** `/api/*` → backend origin (port dahil), kalan yollar → statik/SPA origin
- SPA fallback kuralı **`/api/*` yolunu kapsamaz** — kapsarsa 404 yerine HTML döner, istemci "Unexpected token <" alır
- `/api/*` için **cache bypass** (aşağıda §5)
- `/swagger`, `/health/detail`, admin uçları: prod'da ya kapalı ya **Cloudflare Access** arkasında

Ayrı `api.` alt alan adı yalnız şu durumlarda: farklı ekip/dağıtım döngüsü, üçüncü taraf tüketiciler için public API, veya farklı ölçekleme ihtiyacı. Bu bir **ADR** gerektirir.

## 5. Cache

| Yol | Politika |
|---|---|
| `/assets/*`, hash'li dosyalar | `Cache-Control: public, max-age=31536000, immutable` — edge'de uzun |
| `index.html` | `no-cache` (her zaman revalidate) — yoksa kullanıcı eski SPA'da kalır |
| `/api/*` | **Bypass cache** (varsayılan) |
| Public, nadiren değişen GET | Kısa edge TTL + `stale-while-revalidate`, dikkatle |

Kritik kurallar:
- **Kullanıcıya özel veya yetkiye bağlı yanıt edge'de cache'lenmez** — bir kullanıcının verisi başkasına gider. `Cache-Control: private, no-store` + `Vary: Authorization, Cookie`.
- `Vary` başlığı doğru kurulmadan cache açılmaz.
- Deploy sonrası ilgili yollarda cache purge (tümünü purge etmek yerine hedefli).
- Cache açarken "bayatlarsa ne olur, kim temizler" cevabı yazılır.

## 6. WAF ve bot koruması

- Managed Ruleset (OWASP Core) açık; false positive'ler **dar kural** ile istisna edilir, ruleset kapatılmaz.
- Rate limiting kuralları (minimum):
  - `POST /api/auth/login` → IP başına 10/dk
  - `POST /api/auth/forgot-password`, OTP → 5/dk
  - `/api/*` genel → kimlik/IP başına makul üst sınır
  - Arama/export uçları → daha sıkı
- Bot Fight Mode / Super Bot Fight: **mobil ve kendi istemcin bloklanmasın** diye önce log modunda izlenir.
- Ülke/ASN bloğu ancak gerçek gerekçeyle (meşru kullanıcıyı kesme riski).
- Yönetim panelleri **Cloudflare Access** (Zero Trust) ile kimlik arkasına alınır — parola tek savunma olmasın.
- Kural değişiklikleri önce **Log** modunda, sonra **Block**.

## 7. Cloudflare Tunnel (origin'i tamamen kapatmak)

- Origin sunucuda **80/443 inbound açmadan** hizmet vermek için `cloudflared` tüneli.
- Kazanç: origin IP'si hiç ifşa olmaz, gelen port yok, firewall yalnız outbound.
- Tünel token'ı sır envanterinde; `cloudflared` servis olarak koşar ve otomatik yeniden başlar.
- Tünel kullanılmıyorsa: origin firewall'ı **yalnız Cloudflare IP aralıklarına** açılır + Authenticated Origin Pulls.

## 8. Workers / Pages / R2

- **Workers:** edge mantığı (yönlendirme, A/B, header enjeksiyonu, hafif API). İş mantığı Worker'a taşınmaz — asıl mantık backend'de kalır.
- Worker sırları `wrangler secret put` ile; `wrangler.toml` içine sır yazılmaz. `wrangler.toml` commit edilir, sırlar edilmez.
- Ortam ayrımı Worker environment'ları ile (`[env.test]`, `[env.production]`), ayrı Worker kopyalamakla değil.
- **Pages:** statik SPA dağıtımı için uygun; preview deployment'lar **arama motoruna kapalı** ve gerekiyorsa Access arkasında.
- **R2:** kullanıcı dosyaları. Bucket public yapılmaz; **imzalı URL** veya Worker proxy. Yükleme boyut/tip sınırı uygulama tarafında da doğrulanır. R2 içeriği de yedekleme kapsamındadır (`21-yedekleme-ve-kurtarma.md`).
- Cloudflare kaynakları mümkünse Terraform/wrangler ile yönetilir; panelden elle yapılan değişiklik `DEPLOY.md`'ye yazılır.

## 9. API token'ları

- Global API Key **kullanılmaz**. Dar kapsamlı **Custom Token** üretilir (yalnız gereken zone + gereken izin).
- Token'lar sır envanterinde (`18-kurulum-ve-ortam.md` §4); rotasyon 6 ay.
- CI'da yalnız gereken işlem için (cache purge, DNS kaydı) ayrı token.

## 10. Gerçek istemci IP'si

- Origin'de `CF-Connecting-IP` header'ı okunur; `X-Forwarded-For` körü körüne güvenilmez.
- .NET'te `ForwardedHeaders` middleware'i **yalnız güvenilen proxy** listesiyle çalıştırılır — aksi halde IP spoof edilir ve rate limit/log yanıltır.
- Log ve rate limit gerçek IP ile.

## 11. Kurulum kontrol listesi (yeni alan adı)

- [ ] DNS kaydı proxied; origin IP'sini sızdıran eski kayıt yok
- [ ] SSL modu **Full (Strict)**; origin'de geçerli sertifika
- [ ] Always Use HTTPS + HSTS açık
- [ ] Authenticated Origin Pulls veya Tunnel aktif
- [ ] `/api/*` origin rule doğru; SPA fallback `/api/*`'ı kapsamıyor
- [ ] `/api/*` cache bypass; `index.html` `no-cache`; statikler immutable
- [ ] WAF managed ruleset açık; rate limit kuralları tanımlı
- [ ] Yönetim uçları Access arkasında veya kapalı; prod'da Swagger kapalı
- [ ] Güvenlik başlıkları uçtan uca doğrulandı (`curl -I https://...`)
- [ ] SPF/DKIM/DMARC (mail varsa), DNSSEC açık
- [ ] Sertifika süresi ve uptime alarmı kurulu
- [ ] Tüm kayıt/kural/token `DEPLOY.md` + sır envanterinde belgelendi

## 12. Next.js / OpenNext ISR — cache deposu seçimi

Cloudflare Workers'ta OpenNext ile yayınlanan bir Next.js uygulamasında ISR
**üç parça** ister; biri eksikse sessizce bozulur:

1. `open-next.config.ts` → `incrementalCache` override'ı
2. `open-next.config.ts` → `queue` override'ı
3. Sayfalarda `export const revalidate = <saniye>`

Eksik olanın belirtisi:

| Belirti | Sebep |
|---|---|
| Her istekte `x-nextjs-cache: MISS`, TTFB yüksek | `incrementalCache` yok → "dummy" cache, sayfa her istekte render ediliyor |
| Süresiz `x-nextjs-cache: STALE`, içerik donuyor | `queue` yok → bayat sayfa hiç tazelenmiyor |
| Cache tutuyor ama içerik hiç değişmiyor | Sayfada `revalidate` yok → Next sayfayı "sonsuza kadar geçerli" sayıyor |

⚠️ Rotanın build çıktısında `○ Static` görünmesi çalışma zamanında statik
servis edildiği anlamına **gelmez**. Davranış `curl -sI` ile
`x-nextjs-cache` başlığından ölçülür, build çıktısından çıkarılmaz.

### Cache deposu: KV değil R2

İçerik yayınlandığında cache boşaltılıyorsa (CMS webhook'u → purge uç noktası)
**KV kullanılmaz**:

- **Tutarlılık:** KV eventual consistent; silme dünya geneline ~60 sn'de
  yayılır. Boşaltma yaptığınız hâlde başka bölgeler eski sayfayı servis eder.
  R2 strongly consistent — silinen nesne anında her yerden yok.
- **Kota:** KV ücretsiz katmanı **günlük** ve dar (1.000 yazma, 1.000 silme,
  1.000 list, 100.000 okuma / gün). Bir cache boşaltması yüzlerce nesne
  sildiği için pratikte **günde birkaç boşaltma** hakkı kalır. R2 ücretsiz
  katmanı **aylık**: 1M Class A (yazma/silme/list), 10M Class B (okuma), 10 GB.

Kova, hedef kitleye yakın konum ipucuyla açılır (`--location eeur` vb.).

⚠️ `withRegionalCache` sarmalayıcısı purge senaryosunda **kullanılmaz**:
R2'nin önüne veri merkezi başına Cache API koyar ve OpenNext'in kendi
uyarısına göre cache purge etkin değilken o katman depoyla senkron
olmayabilir — boşalttığınız hâlde eski sayfa servis edilir.

⚠️ **CMS istemcisindeki CDN kapatılır** (Sanity'de `useCdn: false` gibi).
ISR devredeyken istemci istek başına değil, tazeleme başına çağrılır; CDN'in
yük faydası kalmaz. Buna karşılık purge sonrası render CDN'den **eski**
veriyi okuyup onu yeniden cache'ler ve tazelik bir sonraki tura kalır.

### Doğrulama

Yerelde `wrangler dev`, sonra canlıda:
`MISS` (ilk) → `HIT` → `revalidate` süresi sonra `STALE` → `HIT` + yeni içerik.
Ayrıca **yayınla-gör süresi** ölçülür (CMS'te değişiklik → sitede görünme).

## 13. Yapma listesi

- ❌ SSL modu `Flexible`
- ❌ Global API Key kullanmak
- ❌ Origin'i tüm internete açık bırakmak (CF IP kısıtı/tunnel yokken)
- ❌ Yetkiye bağlı yanıtı edge'de cache'lemek
- ❌ `index.html`'i uzun cache'lemek
- ❌ Worker'a iş mantığı taşımak
- ❌ R2 bucket'ı public yapmak
- ❌ `X-Forwarded-For`'a güvenerek rate limit kurmak
- ❌ Panelden elle yapılan değişikliği belgelememek
- ❌ Purge yapılan bir ISR cache'ini KV'de tutmak (eventual consistency + günlük kota)
- ❌ `queue` tanımlamadan incremental cache açmak (içerik süresiz donar)
- ❌ Çalışma zamanı cache davranışını build çıktısından varsaymak — `x-nextjs-cache` ölçülür
