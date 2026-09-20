---
description: Bu projeye standart dokümanlarını (CLAUDE.md, SETUP.md, .env.example) kur veya güncelle
---

Bu projeyi `~/.claude/standards/` düzenine uydur. **Var olanı silme, eksiği tamamla.**

## 1. Keşif (önce oku, sonra yaz)

- Kök dizin, `package.json` / `*.csproj` / `docker-compose.yml` / `.github/workflows/`
- Mevcut `CLAUDE.md`, `README.md`, `SETUP.md`, `DEPLOY.md`, `.env*`
- Gerçek portlar, gerçek servis adları, gerçek branch akışı (`git branch -a`)

**Tahmin yazma.** Bilmediğin bir alanı `<TODO: ...>` olarak bırak ve sonunda listele.

## 2. `CLAUDE.md`

- Yoksa: `~/.claude/standards/templates/project-claude-md.md` şablonundan, **gerçek** bilgilerle doldurarak oluştur.
- Varsa: silme. Yalnız eksik bölümleri ekle ve en üste şu notu koy (yoksa):

  ```
  > Genel yazılım standartları: `~/.claude/standards/` (her oturumda `~/.claude/CLAUDE.md` yüklenir).
  > Burada yalnız **bu projeye özel** kurallar bulunur; buradaki kural genel standardı ezer.
  ```

- Hedef < 200 satır. Uzun tarihsel detayı `docs/` altına taşımayı öner (kullanıcı onayıyla).

## 3. `SETUP.md`

`~/.claude/standards/templates/setup-md.md` şablonundan — kritik bölüm **§3 sır/token envanteri**:
her sır için ad, ne işe yarar, **nereden alınır (menü yolu)**, nerede saklanır, sahibi, rotasyon, sır mı public mi.

Mevcut env kullanımlarını koddan tara (`process.env`, `import.meta.env`, `IConfiguration`, `appsettings*.json`)
ve **hepsini** tabloya al. Değerleri **asla** yazma.

## 4. `.env.example`

Koddan bulunan tüm değişkenler, açıklamalı, zorunlu/opsiyonel ayrımıyla. `.env` gitignore'da mı kontrol et.

## 5. CLAUDE.md kapıları (araç kurulumu — ÖNCE SOR)

⚠️ Bu adım doküman değil **araç** kurar; kullanıcıya sor, onay almadan yapma.

`CLAUDE.md` dosyaları o dizindeki **her oturumda ve her subagent turunda**
bağlama girer; şişme hem maliyet hem **görünürlük** sorunudur (170 KB'lık bir
dosyada kural bulunmaz). İki kapı bunu tutar — kanonik kopyaları
`~/.claude/scripts/`, ayrıntı `~/.claude/scripts/README.md`:

```bash
mkdir -p scripts && cp ~/.claude/scripts/md-*.sh ~/.claude/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --guncelle   # tavan = BUGÜNKÜ boyut
```

- Araçlar **projeye kopyalanır ve orada commit'lenir** — projenin kapısı repo
  dışı bir yola bağlanamaz (bu bir kez yaşandı: araç hiçbir depoda değildi ve
  ona yönlendiren satır 3 hafta boyunca ölü bir yolu gösterdi).
- Projenin merge/CI kapısına `bash scripts/md-size-gate.sh` adımını ekle.
  Kapı yoksa **ekleme, raporla** — kapı kurmak ayrı bir istektir.
- Zaten bir boyut kapısı varsa **ikincisini kurma**; var olanı kullan. **Ölçüt
  (tahmin etme, koştur):** `grep -rlE 'md-size-gate|md-budget|claude-md-budget' scripts/ .github/ 2>/dev/null`
  boş değilse kapı vardır — kurulumu atla ve raporla. (05/09/2026'da tam bu
  atlandı: var olan kapının yanına ikincisi yazıldı, baseline'lar çelişti.)

⚠️ **Küçültme önerme.** Cırcırlı tavan büyümeyi durdurur, asıl amaç budur.
Bölme yalnız **kök** `CLAUDE.md` çok büyükse ve **taşıyarak** (özetleyerek
değil) yapılır; sonucu `md-rule-gate.py` ile doğrulanır.

## 6. Çalışma modu (opsiyonel)

Proje `.claude/mode` dosyası taşımıyorsa mod **A** (ajan yok) geçerlidir.
Ajan isteniyorsa `/working-mode <B|C|D>`.
Tanımlar `~/.claude/modes/README.md`, kural `~/.claude/CLAUDE.md` #27.
⚠️ `.claude/*` çoğu projede gitignore'ludur; mod dosyası **commit edilmeli**
(dar bir `!.claude/mode` istisnası gerekir) — o proje ayarıdır, kişisel oturum
durumu değil.

## 7. Rapor

- Oluşturulan / güncellenen dosyalar
- Doldurulamayan `<TODO>` alanları — kullanıcıya net sorularla
- Standartlara aykırı gördüğün mevcut durumlar (hard-coded URL, sır repoda, yedek yok, `SETUP.md` yok) — **düzeltme, raporla**

Kod değişikliği yapma; yalnız doküman üret — **tek istisna §5'in araç kopyalaması** ve o da kullanıcı onayıyla. Kod düzeltmesi ayrı bir istektir.
