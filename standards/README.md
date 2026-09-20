# Yazılım Standartları — İndeks

Bu klasör `~/.claude/CLAUDE.md`'nin detay katmanıdır. **Otomatik yüklenmez** —
görev hangi konuya giriyorsa yalnız o dosya okunur (token maliyeti bu yüzden düşük).

| Dosya | Konu |
|---|---|
| `00-working-method.md` | Claude ile çalışma protokolü: plan, onay, doğrulama, bağlam yönetimi |
| `01-product-design.md` | Problem tanımı, user story, kabul kriteri, kapsam, MVP, ADR |
| `02-ui-ux.md` | Tasarım sistemi, durum tasarımı, responsive, erişilebilirlik, i18n |
| `03-coding-general.md` | İsimlendirme, dosya boyutu, hata yönetimi, log, ölü kod, yorum |
| `04-dotnet.md` | .NET Web API katmanları, DI, EF Core, async, validation, config |
| `05-react.md` | React + TS yapı, state, veri çekme, form, performans, test |
| `06-mobile.md` | React Native / Expo, web-mobil paritesi, offline, store yayını |
| `07-api-design.md` | REST sözleşmesi, tek API, sayfalama, hata formatı, idempotency |
| `08-backward-compatibility.md` | Additive evrim, deprecation yaşam döngüsü, expand/contract |
| `09-database.md` | Şema, migration, index, transaction, audit, soft delete |
| `10-test-strategy.md` | Test piramidi, unit test kuralları, contract test, flaky politikası |
| `11-playwright.md` | Web e2e: selector, fixture, izolasyon, CI |
| `12-maestro.md` | Mobil e2e: flow yapısı, testID, cihaz matrisi |
| `13-pr-and-review.md` | Commit, branch, PR boyutu, review checklist ve şiddet seviyeleri |
| `14-devops.md` | Ortamlar, branch akışı, CI/CD, container, deploy, rollback, yedek |
| `15-security.md` | AuthN/AuthZ, OWASP, sır yönetimi, KVKK/PII, bağımlılık taraması |
| `16-performance.md` | Bütçeler, N+1, cache, bundle, Core Web Vitals, yük testi |
| `17-observability.md` | Log, metrik, trace, correlation id, alarm, incident |
| `18-setup-and-environment.md` | Ön koşullar, `SETUP.md`, **sır/token envanteri**, `.env`, port haritası |
| `19-cloudflare-and-edge.md` | DNS, TLS, WAF, rate limit, cache, **tek-origin `/api`**, Tunnel, Workers, R2 |
| `20-hardening.md` | Güvenlik başlıkları, firewall, SSH/RDP, IIS, Docker, DB, CI sertleştirme |
| `21-backup-and-recovery.md` | 3-2-1, neyi yedekliyoruz envanteri, RPO/RTO, **restore provası**, runbook |
| `../docs/decision-log.md` | **Karar defteri** — `CLAUDE.md`'den taşınan gerekçe, tarihçe, ölçüm, yürürlükten kalkmış madde metinleri |
| `templates/` | Proje CLAUDE.md, **SETUP.md**, PR, ADR, user story şablonları |

## Öncelik sırası (çakışma olursa)

1. Kullanıcının o anki açık talimatı
2. Projenin kendi `CLAUDE.md`'si (alt dizin > kök)
3. `~/.claude/CLAUDE.md`
4. Bu klasördeki standartlar

Bir standardı bilinçli olarak ihlal ediyorsan **nedenini koda/PR'a yaz**. Sessiz istisna yok.
