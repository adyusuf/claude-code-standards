---
name: yazilim-standartlari
description: Tüm projelerde geçerli yazılım standartlarını (ürün tasarımı, UI/UX, .NET, React, mobil, API, geriye uyumluluk, veritabanı, test, Playwright, Maestro, PR/review, DevOps, güvenlik/OWASP, performans, gözlemlenebilirlik, kurulum/sır envanteri, Cloudflare/edge, sertleştirme, yedekleme) yükler. Kod yazmadan, review yaparken, kurulum/deploy planlarken veya "best practice", "standart", "kurallar" sorulduğunda kullan.
---

# Yazılım Standartları

Standartlar `~/.claude/standards/` altında **konu başına ayrı dosya** halinde durur.
Hepsini birden okuma — **görevle ilgili olanı** oku.

## Yönlendirme

| Görev | Oku |
|---|---|
| Yeni özellik, kapsam, kabul kriteri, ADR | `01-urun-tasarimi.md` |
| Ekran, bileşen, stil, erişilebilirlik, i18n | `02-ui-ux.md` |
| Genel kodlama, isimlendirme, hata yönetimi, log | `03-kodlama-genel.md` |
| .NET endpoint/servis/EF Core/DI/config | `04-dotnet.md` |
| React sayfa/bileşen/state/veri çekme/form | `05-react.md` |
| React Native / Expo / store yayını | `06-mobil.md` |
| Endpoint sözleşmesi, hata formatı, sayfalama, idempotency | `07-api-tasarimi.md` |
| Alan/endpoint değiştirme, deprecation, expand-contract | `08-geriye-uyumluluk.md` |
| Şema, migration, index, transaction, soft delete | `09-veritabani.md` |
| Unit/integration/contract test, flaky politikası | `10-test-stratejisi.md` |
| Web e2e | `11-playwright.md` |
| Mobil e2e | `12-maestro.md` |
| Commit, branch, PR, code review | `13-pr-ve-review.md` |
| Ortamlar, CI/CD, deploy, rollback, tek-origin topoloji | `14-devops.md` |
| AuthN/AuthZ, OWASP Top 10, tarama zinciri, KVKK | `15-guvenlik.md` |
| Yavaşlık, cache, bundle, Core Web Vitals, yük testi | `16-performans.md` |
| Log, metrik, trace, alarm, incident, post-mortem | `17-gozlemlenebilirlik.md` |
| Kurulum, ön koşullar, **sır/token envanteri**, `.env` | `18-kurulum-ve-ortam.md` |
| Cloudflare DNS/TLS/WAF/cache/Tunnel/Workers/R2 | `19-cloudflare-ve-edge.md` |
| Sunucu + uygulama sertleştirme, güvenlik başlıkları, IIS/Docker | `20-sertlestirme.md` |
| Yedekleme, restore provası, RPO/RTO, felaket kurtarma | `21-yedekleme-ve-kurtarma.md` |

Şablonlar: `~/.claude/standards/sablonlar/`
(`proje-claude-md.md`, `setup-md.md`, `pr-sablonu.md`, `adr-sablonu.md`, `user-story-sablonu.md`)

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
