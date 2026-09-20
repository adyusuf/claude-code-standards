---
name: software-standards
description: Tüm projelerde geçerli yazılım standartlarını (ürün tasarımı, UI/UX, .NET, React, mobil, API, geriye uyumluluk, veritabanı, test, Playwright, Maestro, PR/review, DevOps, güvenlik/OWASP, performans, gözlemlenebilirlik, kurulum/sır envanteri, Cloudflare/edge, sertleştirme, yedekleme) yükler. Kod yazmadan, review yaparken, kurulum/deploy planlarken veya "best practice", "standart", "kurallar" sorulduğunda kullan.
---

# Yazılım Standartları

Standartlar `~/.claude/standards/` altında **konu başına ayrı dosya** halinde durur.
Hepsini birden okuma — **görevle ilgili olanı** oku.

## Yönlendirme

| Görev | Oku |
|---|---|
| Yeni özellik, kapsam, kabul kriteri, ADR | `01-product-design.md` |
| Ekran, bileşen, stil, erişilebilirlik, i18n | `02-ui-ux.md` |
| Genel kodlama, isimlendirme, hata yönetimi, log | `03-coding-general.md` |
| .NET endpoint/servis/EF Core/DI/config | `04-dotnet.md` |
| React sayfa/bileşen/state/veri çekme/form | `05-react.md` |
| React Native / Expo / store yayını | `06-mobile.md` |
| Endpoint sözleşmesi, hata formatı, sayfalama, idempotency | `07-api-design.md` |
| Alan/endpoint değiştirme, deprecation, expand-contract | `08-backward-compatibility.md` |
| Şema, migration, index, transaction, soft delete | `09-database.md` |
| Unit/integration/contract test, flaky politikası | `10-test-strategy.md` |
| Web e2e | `11-playwright.md` |
| Mobil e2e | `12-maestro.md` |
| Commit, branch, PR, code review | `13-pr-and-review.md` |
| Ortamlar, CI/CD, deploy, rollback, tek-origin topoloji | `14-devops.md` |
| AuthN/AuthZ, OWASP Top 10, tarama zinciri, KVKK | `15-security.md` |
| Yavaşlık, cache, bundle, Core Web Vitals, yük testi | `16-performance.md` |
| Log, metrik, trace, alarm, incident, post-mortem | `17-observability.md` |
| Kurulum, ön koşullar, **sır/token envanteri**, `.env` | `18-setup-and-environment.md` |
| Cloudflare DNS/TLS/WAF/cache/Tunnel/Workers/R2 | `19-cloudflare-and-edge.md` |
| Sunucu + uygulama sertleştirme, güvenlik başlıkları, IIS/Docker | `20-hardening.md` |
| Yedekleme, restore provası, RPO/RTO, felaket kurtarma | `21-backup-and-recovery.md` |

Şablonlar: `~/.claude/standards/templates/`
(`project-claude-md.md`, `setup-md.md`, `pr-template.md`, `adr-template.md`, `user-story-template.md`)

## Sık kombinasyonlar

- **Yeni özellik (uçtan uca):** 01 → 07 → 08 → (04 veya 05/06) → 10 → 02
- **Code review / merge:** 13 → 08 → 15
- **Yeni proje kurulumu:** 18 → 14 → 19 → 20 → 21
- **Prod'a çıkış hazırlığı:** 15 (§15 checklist) → 20 → 21 → 17 → 14
- **"Yavaş" şikâyeti:** 16 → 09 → 17
- **Güvenlik incelemesi:** 15 (OWASP §12-13) → 20 → 19

## Öncelik

Kullanıcının o anki talimatı > projenin `CLAUDE.md`'si > `~/.claude/CLAUDE.md` > bu standartlar.
Bir standardı bilinçli ihlal ediyorsan **nedenini koda/PR'a yaz** — sessiz istisna yok.
