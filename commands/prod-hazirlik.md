---
description: Prod'a çıkış öncesi güvenlik, sertleştirme, yedek ve gözlemlenebilirlik denetimi
---

Bu projenin **canlıya çıkmaya hazır olup olmadığını** denetle. Tahmin etme — **doğrula**.
Doğrulayamadığın maddeyi "doğrulanamadı" olarak işaretle, "geçti" sayma.

Oku: `~/.claude/standards/` → `15-guvenlik.md` (§12 OWASP, §15 checklist), `20-sertlestirme.md`,
`21-yedekleme-ve-kurtarma.md`, `17-gozlemlenebilirlik.md`, `14-devops.md`, `19-cloudflare-ve-edge.md`.
Ayrıca projenin `CLAUDE.md` + `DEPLOY.md` + `SETUP.md` dosyalarını.

## 1. Güvenlik

- [ ] Yetkisiz endpoint var mı — `[AllowAnonymous]` / auth'suz route listesi çıkar ve tek tek gerekçelendir
- [ ] IDOR: kaynak sahipliği kontrol edilen/edilmeyen uçlar
- [ ] Sır taraması (repo geçmişi dahil) temiz mi
- [ ] Bağımlılık CVE taraması: `dotnet list package --vulnerable`, `npm audit`
- [ ] OWASP Top 10 eşleme tablosu (`15-guvenlik.md` §12) gözden geçirildi
- [ ] Log örneğinde PII/token var mı

## 2. Sertleştirme (mümkünse gerçek istekle doğrula)

- [ ] `curl -I https://<prod>` → HSTS, CSP, nosniff, Referrer-Policy, Permissions-Policy var mı
- [ ] `Server` / `X-Powered-By` sızıyor mu
- [ ] Prod'da Swagger / debug / detaylı hata **kapalı** mı
- [ ] TLS: minimum sürüm, sertifika süresi
- [ ] Cloudflare: SSL modu Full (Strict), `/api/*` cache bypass, WAF + rate limit kuralları
- [ ] DB portu dışarı kapalı, uygulama root olmayan kullanıcıyla koşuyor

## 3. Yedekleme

- [ ] Otomatik yedek görevi var **ve son çalıştığı zaman** biliniyor
- [ ] Offsite kopya var
- [ ] Kullanıcı dosyaları + konfigürasyon + sertifika da kapsamda
- [ ] **Son restore provası ne zaman yapıldı, ne kadar sürdü** (kaydı var mı)
- [ ] Yedek başarısızlığı **ve hiç çalışmaması** için alarm var mı
- [ ] RPO/RTO yazılı mı

## 4. Gözlemlenebilirlik

- [ ] `/health`, `/health/ready`, `/version` çalışıyor mu
- [ ] Merkezî log + hata takibi (Sentry vb.) aktif mi
- [ ] Alarmlar: 5xx oranı, latency, uptime, disk, **sertifika süresi**, yedek
- [ ] Correlation id istemciden log'a kadar izlenebiliyor mu

## 5. Sürüm ve geri dönüş

- [ ] Migration geri alınabilir mi; `DROP` var mı; yedek alındı mı
- [ ] Rollback planı yazılı mı; feature flag var mı
- [ ] E2E son koşum sonucu **taze ve yeşil** mi
- [ ] Mobil eski sürümler bu API'yle çalışıyor mu (`08-geriye-uyumluluk.md`)
- [ ] `SETUP.md`/`DEPLOY.md` güncel mi (sıfırdan kurulum bu belgeyle yapılabilir mi)

## Çıktı

**GO / NO-GO** kararı ve gerekçesi. Ardından:
- 🔴 **Bloke eden** maddeler (çıkmadan önce çözülmeli)
- 🟡 **Riskli** maddeler (kabul edilebilir ama yazılı kabul gerekir)
- ⚪ **Doğrulanamadı** (erişim/araç yok — kullanıcı manuel kontrol etmeli)

Her madde için ne yapılması gerektiğini somut yaz.
