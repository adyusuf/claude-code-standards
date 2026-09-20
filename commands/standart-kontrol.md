---
description: Mevcut değişiklikleri global yazılım standartlarına karşı denetle
---

Bu depodaki **bekleyen değişiklikleri** (`git diff` + `git diff --staged`; commit yoksa
son commit'i) `~/.claude/standards/` altındaki standartlara karşı denetle.

Argüman verilmişse ($ARGUMENTS) yalnız o kapsamı incele (dosya yolu, dizin veya konu adı).

## Adımlar

1. `git status` ve `git diff` ile değişiklik kapsamını çıkar. Değişiklik yoksa söyle ve dur.
2. Kapsamdan hangi standartların ilgili olduğunu belirle ve **yalnız onları** oku:
   - Backend/.NET → `04-dotnet.md`, `09-veritabani.md`
   - Web/React → `05-react.md`, `02-ui-ux.md`
   - Mobil → `06-mobil.md`
   - Endpoint/DTO değişikliği → `07-api-tasarimi.md` + **`08-geriye-uyumluluk.md` (zorunlu)**
   - Test dosyaları → `10-test-stratejisi.md`, `11-playwright.md`, `12-maestro.md`
   - CI/deploy/altyapı → `14-devops.md`, `19-cloudflare-ve-edge.md`, `20-sertlestirme.md`
   - Auth/veri/yetki → `15-guvenlik.md`
   - Yeni env/araç/sır → `18-kurulum-ve-ortam.md`
   - Yedek/migration `DROP` → `21-yedekleme-ve-kurtarma.md`
3. Ayrıca projenin kendi `CLAUDE.md`'sini oku — **proje kuralı genel standardı ezer**.
4. `13-pr-ve-review.md` §5 checklist'ini uygula.

## Özellikle ara

- Silinen/adı değişen alan, endpoint, enum değeri; yeni zorunlu alan; sıkılaştırılan validasyon
- Hard-coded URL/IP/port/anahtar
- Yetkisiz endpoint, IDOR açığı, fail-open izin
- N+1, `SELECT *`, sayfalamasız liste
- Sessiz yutulan exception, log'a sızan PII/token
- 300+ satırlık dosya, ölü kod, yorumlanmış kod
- Eksik/gevşetilmiş test
- Güncellenmemiş `.env.example` / `SETUP.md` / Swagger / CLAUDE.md

## Çıktı

Bulguları `13-pr-ve-review.md` §6 şiddet seviyeleriyle raporla:
**Bloke / Önemli / Öneri / Not** — her bulguda `dosya:satır`, ne yanlış, neden önemli, önerilen düzeltme.

Bloke seviyesinde bulgu varsa en üstte belirgin şekilde uyar. Hiç bulgu yoksa bunu da açıkça söyle;
bulgu üretmek için zorlama.
