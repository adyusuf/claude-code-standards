# DevOps — Ortamlar, CI/CD, Deploy

## 1. Ortamlar

| Ortam | Amaç | Veri | Kim deploy eder |
|---|---|---|---|
| **local** | Geliştirme | Seed / sahte | Geliştirici |
| **dev** | Entegrasyon | Seed | Otomatik (her merge) |
| **test** | Kabul + e2e | Gerçekçi, maskeli | Onayla promosyon |
| **prod** | Canlı | Gerçek | **Açık kullanıcı onayı** |

- Her ortamın kendi config'i, kendi sırları, kendi veritabanı. Connection string'ler karışamaz (ortam adı bağlantı adında görünsün).
- Test ve prod aynı sunucuda barınıyorsa **ayrı worktree + ayrı site + ayrı servis + ayrı yedek görevi** olur; karıştırmak prod'a test kodu yazar.
- Ortam değişkenleri kod deposunda değil; yalnız `.env.example` (değersiz şablon) commit edilir.

## 2. Branch → ortam akışı

```
feature/* → dev → (onay) → test → (onay) → prod
```

- Yön tek: geri merge yok. Hotfix bile `dev`'den açılır, hızlı promosyon edilir.
- `test`/`prod`'a ham `git push` engellenir (branch protection + pre-push hook).
- Her **promosyon** (`dev → test`, `test → prod`) öncesi: kapı yeşil + review yapılmış + e2e sonucu taze.
- **`dev`'e merge bunun dışındadır (global kural #25):** yalnız build + hızlı unit test koşar (formatlayıcı/lint iş listesinin **sonunda bir kez**, 20/09/2026 — #26); review, güvenlik taraması ve e2e `dev`'de koşmaz.

## 3. CI hattı (hızlıdan yavaşa)

```
1. Lint + format doğrulama        (~1 dk)
2. Tip kontrolü (tsc / build)      (~2 dk)
3. Unit testler                    (~3 dk)
4. Sır taraması + bağımlılık CVE   (~1 dk)
5. Geriye uyumluluk taraması       (~1 dk)
--- buraya kadar HER PUSH ---
6. Integration testler (gerçek DB) — PR'da
7. E2E (Playwright/Maestro)        — promosyon öncesi / gecelik
8. Yük testi                       — sürüm öncesi / haftalık
```

- Hızlı kapı 10 dakikayı geçmemeli; geçiyorsa paralelleştir veya böl.
- Yavaş/state'li testler hızlı kapıya karıştırılmaz.
- CI adımları yerelde de aynı komutla koşabilmeli.
- Hosted runner kotası biterse self-hosted fallback tanımlı olsun (aynı adımlar tekrar yazılmaz — reusable workflow + `runner` parametresi).

## 4. Build ve artifact

- Build **bir kez** yapılır, aynı artifact tüm ortamlara promosyon edilir. Ortam başına yeniden build yok (aynı kod, farklı binary riski).
- Ortam farkı **konfigürasyondan** gelir, derleme zamanından değil.
- Artifact sürümlenir ve commit SHA ile etiketlenir — üretimde koşan sürümün hangi commit olduğu her zaman bilinir (`/version` endpoint'i).
- Docker: multi-stage build, non-root user, minimal base image, `.dockerignore`, sabitlenmiş base tag (`:latest` yasak), health check.

## 5. Deploy

- **Sıfır kesintili** hedef: rolling / blue-green. Kesinti gerekiyorsa önceden duyurulur.
- Migration deploy'dan **ayrı ve önce** koşulur; expand→migrate→contract (`08-backward-compatibility.md` §5) sayesinde eski kod da yeni şemayla çalışır.
- Deploy sonrası otomatik smoke test (`/health`, kritik 2-3 endpoint). Kırmızıysa otomatik rollback veya alarm.
- **Rollback planı deploy'dan önce yazılır.** "Geri alamayız" durumu varsa deploy edilmez, feature flag ile çıkılır.
- Feature flag: yeni riskli özellik kapalı çıkar, kademeli açılır. Flag'ler envanterde tutulur ve **temizlenir** (ölü flag teknik borçtur).

## 6. Sırlar ve konfigürasyon

- Sır kaynakları: GitHub Actions Secrets (CI), sunucuda env/secret store, dev'de User Secrets/`.env` (gitignore'lu).
- **Repoda sır bulunursa:** önce **rotate**, sonra geçmiş temizliği. Sadece silmek yetmez — geçmişte kalır.
- Sır taraması CI'da zorunlu (gitleaks/trufflehog) + `pre-commit` hook.
- Sır rotasyon takvimi yazılı (en az yılda 1, kişi ayrılışında hemen).
- Tüm sırların envanteri `SETUP.md`'de (bkz. `18-setup-and-environment.md`): ne, nereden alınır, nerede saklanır, kim sahibi, ne zaman yenilenir.

## 7. Altyapı

- Sunucu ayarı elle yapılmaz — script/IaC ile (PowerShell/bash script, Terraform, Ansible). Elle yapılan her ayar bir sonraki sunucuda kaybolur.
- Kurulum adımları `DEPLOY.md`'de; **yeni bir sunucuya sıfırdan kurulum bu dosyayla yapılabilmeli**.
- DNS, sertifika, firewall kuralları da dokümante edilir (`19-cloudflare-and-edge.md`, `20-hardening.md`).
- Sertifika otomatik yenilenir; yenileme başarısızlığı **alarm üretir** (sessizce süresi dolmasın).

## 8. Tek origin dağıtım (tercih edilen topoloji)

**API, UI'ın alan adının altında yayınlanır:** `app.example.com/api/*`
Ayrı `api.example.com` alt alan adı **istisna**, varsayılan değil.

Neden:
- **CORS yok** — preflight, header listesi, credentials karmaşası ortadan kalkar
- **Cookie same-site** çalışır → httpOnly + `SameSite=Strict/Lax` gerçekten kullanılabilir (token'ı `localStorage`'a yazmak zorunda kalmazsın)
- Tek TLS sertifikası, tek DNS kaydı, tek WAF/rate-limit politikası
- Backend'in nerede koştuğu (port, iç host, container) dışarıdan görünmez
- Mobil de aynı base URL'i kullanır → tek `BASE_URL`, tek sertifika pinleme hedefi

Nasıl:
- Reverse proxy (Cloudflare/Nginx/IIS ARR) `/api/*` → backend, kalan her şey → statik SPA
- SPA fallback: bilinmeyen yol → `index.html`, **ama `/api/*` asla fallback'e düşmez** (yoksa 404 yerine HTML döner ve istemci JSON parse hatası alır)
- `/swagger` yalnız test ortamında açık; prod'da kapalı veya kimlik korumalı
- Detay ve Cloudflare kuralları: `19-cloudflare-and-edge.md` §4

## 9. Yedekleme ve felaket kurtarma

- Günlük otomatik DB yedeği + **haftalık sunucu dışı** kopya (aynı makinede duran yedek, yedek değildir).
- **Ayda bir restore provası** — denenmemiş yedek yedek sayılmaz.
- RPO/RTO hedefi yazılı: en fazla ne kadar veri kaybı, en fazla ne kadar kesinti kabul edilebilir.
- Yedekler şifreli; erişimi sınırlı; saklama süresi tanımlı.
- Kullanıcı yüklediği dosyalar (blob/R2/S3) da yedekleme kapsamında — sadece DB yedeklemek eksik.

## 10. Gözlemlenebilirlik

`17-observability.md`. Minimum: merkezî log, hata takibi (Sentry vb.), uptime kontrolü, `/health` endpoint'i, disk/CPU/bellek alarmı, sertifika süresi alarmı.

## 11. Yapma listesi

- ❌ Sunucuya elle dosya kopyalayarak deploy
- ❌ Ortam başına ayrı build
- ❌ Prod'a onaysız deploy
- ❌ Migration'ı deploy ile aynı anda ve geri alınamaz şekilde koşmak
- ❌ Sırrı repoya, log'a, CI çıktısına yazmak
- ❌ `:latest` image tag'i
- ❌ Rollback planı olmadan riskli değişiklik
- ❌ Sadece aynı makinede duran yedek
- ❌ Prod'da açık Swagger / debug endpoint / detaylı hata sayfası
