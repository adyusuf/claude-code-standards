# CLAUDE.md bakım araçları (kanonik kopya)

Üç araç, tek aile. **Kanonik hâlleri burada durur**; her proje kendi
`scripts/` dizinine bir **kopya** alır ve onu commit'ler.

⚠️ Projeler bu dizini **doğrudan çağırmaz**. Bir projenin kapısı repo dışı bir
yola bağlanamaz — `md-rule-gate.py` 05/09/2026'ya kadar tam bu yüzden
kayıptı: `~/ClaudeCode/.claude/` altında, hiçbir git deposunda değildi ve
`md-budget.tsv` ona yönlendirdiği hâlde hiçbir worktree'de yoktu.

| Araç | Ne yapar | Nasıl koşar |
|---|---|---|
| `md-size-gate.sh` | Her `CLAUDE.md`'nin boyutunu bir **cırcıra** bağlar: tavan yalnız iner (`--guncelle`), yükseltmek elle + `NOT` sütununda gerekçeli. Bütçesiz dosya fail-closed kırmızı. | Projenin merge kapısında **otomatik** |
| `md-rule-gate.py` | Bir sadeleştirmede **kural kaybını** ölçer: ❌ maddeleri, yasak/yükümlülük kipi taşıyan satırlar, ters-tırnaklı tanımlayıcılar. Düşen tanımlayıcı için **gerekçeli triaj** ister. | **Elle**, bölme yaparken |
| `md-split.py` | Karar günlüğünü iki katmana ayırır — **birebir taşıyarak, parafraz etmeden**. | **Elle**, bölme yaparken |

## Bir projeye kurulum

`/apply-project-standards` komutu bunu yapar. Elle yapılacaksa:

```bash
mkdir -p scripts && cp ~/.claude/scripts/md-*.sh ~/.claude/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --guncelle   # tavanlar = bugünkü boyut
```

Sonra projenin merge kapısına `bash scripts/md-size-gate.sh` adımını ekle.

## Bölme yaparken doğru sıra

```bash
python3 scripts/md-rule-gate.py <(git show origin/dev:CLAUDE.md) /tmp/yeni.md
```

Taşıma birden çok dosyaya yayıldıysa "yeni" tarafı **birleştirilerek** verilir:
`cat CLAUDE.md docs/kurallar/*.md > /tmp/yeni.md`

## ⚠️ Küçültmeden önce oku

`md-budget.tsv`'nin başlığında **ölçülmüş** bir sonuç var: 15/08/2026'da bir
`CLAUDE.md` üç yöntemle sadeleştirilmeye çalışıldı; biri **383 kural satırını
düşürdü**, biri dosyayı **büyüttü**. Cümle düzeyinde ölçüm: **%61 kural,
%9 tarihçe**. Yani bu dosyalar genelde **şişkin değil, yoğundur**.

05/09/2026'da bu bağımsız olarak doğrulandı (bir backend dosyasının arşiv
bölümünün bayt olarak yalnız **%7'si** tarihseldi) — **ama bir istisnayla:**
o ölçüm *alt* dosyalar için doğruydu, **kök `CLAUDE.md` için değildi.** Kökte
sorun yoğunluk değil, tek dosyada biriktirmeydi ve **taşıma** (özetleme değil)
%74 kazandırdı, kural kapısından temiz geçti.

**Karar kuralı:** her oturumda + her ajan turunda yüklenen **kök** dosyada
taşıma değer. Yalnız ilgili dizinde yüklenen **alt** dosyada çoğunlukla
değmez — orada cırcırlı tavan yeterlidir.

## Ölçüm ve kapı betikleri (20/09/2026)

| Dosya | Ne yapar |
|---|---|
| `pre-commit.sh` | Commit'ten ÖNCE koşan kapı: CLAUDE.md boyut bütçesi + staged içerikte gitleaks. Kırmızıysa commit'i **durdurur** (`md-hook.sh` yalnız uyarır, çıkış kodu 0). Kurulum: `bash scripts/pre-commit.sh --install`; bilinçli istisna `git commit --no-verify`. |
| `prefix-measure.py` | Oturumların **sabit öneğini** (sistem prompt + araç/skill listeleri + CLAUDE.md) listeler. Sıralama dosya damgasına değil **oturum başlangıcına** göredir. |
| `step-stats.py` | `docs/measurement-log.md`'yi üretir: önek dağılımı, kesim karşılaştırması, rol bazında koşum + maliyet, **SDLC step'lerinin koşum sayısı**. `--write`, `--days N`. |
| `measurement-cuts.tsv` | Yapılandırma değişikliklerinin tarihi (`ISO tarih<TAB>etiket`); `step-stats.py` her kesimin **öncesi/sonrası** önek medyanını kendisi hesaplar. |

⚠️ **Sayım tuzakları (ölçülerek bulundu):** heredoc **gövdesi** komut değil veridir
(gövde ayıklanır, sonrası korunur — yoksa sayım yarıya düşer) · `grep -E "dotnet|codeql"`
bir SAST koşumu değildir, bahisler `dismissed` sütununda ayrıca raporlanır ·
adım başka bir betiğin içinden koşarsa görünmez: "0" değil **"görünmedi"**.

