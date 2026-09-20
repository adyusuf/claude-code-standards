---
name: working-mode
description: Bu proje için çalışma modunu (A/B/C/D/E) gösterir veya değiştirir. Modlar ajan kullanımını, review'ı ve onay politikasını belirler. Kullanıcı "/working-mode", "modu değiştir", "hangi moddayız", "tam takım çalış", "ajansız çalış" dediğinde kullan.
---

# Çalışma modu

## 1. Mevcut modu oku

Öncelik sırası: **oturumluk seçim** → proje dosyası → A.

```bash
S="<sistem prompt'taki Scratchpad Directory>"   # oturuma özel, sıkıştırmada silinmez
cat "$S/mode" 2>/dev/null || cat "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/mode" 2>/dev/null || echo B
```

Hiçbiri yoksa mod **B**'dir (18/09/2026, kullanıcı kararı; öncesinde A idi).
B'nin üç ajanı (`analyst`, `test-writer`, `doc-writer`) varsayılanla birlikte onaylıdır.
Kullanıcı mod söylemediyse **B'de başla, gerekiyorsa en düşük yeterli modu tek
satırla öner** — kendin geçme (README › "Mod verilmediyse").

⚠️ `--tek` ile seçilen mod **scratchpad'e yazılır** (`$S/mode`), `.claude/mode`'a
değil. Sebep: "yalnız bu oturumda uygula" sözü belleğe güvenirse bağlam
sıkıştırmasından sonra **unutulur** ve proje dosyasındaki moda sessizce geri
dönülür. Scratchpad oturuma özeldir ve oturum bitince gider — tam istenen ömür.

## 2. Mod tanımlarını yükle

`~/.claude/modes/README.md` matristir (tek kaynak). Aktif modun dosyasını oku:
`~/.claude/modes/<HARF>-*.md` (5 harfin her biri tek dosyaya çözülür).
**Yalnız aktif modun dosyasını oku** — beşini birden okumak boşuna bağlam yakar.
⚠️ **X/Y/Z arşivdedir** (`modes/archive/README.md`) — mod olarak teklif edilmez.

## 3. Argümansız çağrıldıysa

Mevcut modu, ne anlama geldiğini ve diğer seçenekleri **kısa** göster:
harf + ad + ajan seti + review kimde + maliyet çarpanı. Matrisin tamamını
yapıştırma; 5-6 satır yeter (A-E).

## 4. Harf verildiyse (`/working-mode B`)

1. Harfi doğrula (**A/B/C/D/E**). ⚠️ **D ve E 18/09/2026'da yer değiştirdi**: D artık 14 rollü geniş takım, E fan-out (`Workflow`). Eski oturumlardan gelen "D = fan-out" beklentisini düzelt. Geçersiz harfi reddet, listeyi göster.
2. `--tek` verilmediyse repo kökündeki `.claude/mode` dosyasına **tek harf** yaz:
   ```bash
   root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && mkdir -p "$root/.claude" && printf '%s\n' "B" > "$root/.claude/mode" && echo "yazıldı: $root/.claude/mode"
   ```
   ⚠️ Fallback zorunlu: git deposu olmayan dizinde `git rev-parse` **exit 128**
   verir ve `&&` zinciri kırılır — dosya yazılmaz. Eskiden okuma komutunda
   fallback vardı, yazmada yoktu: kullanıcıya "kalıcı yazıldı" denip aslında
   yazılmıyordu. **Yazma başarısızsa kullanıcıya söyle**, onaylama.
   `--tek` verildiyse `.claude/mode`'a **yazma**; scratchpad'e yaz: `printf '%s\n' "B" > "$S/mode"`
   (oturumluk, §1'deki öncelik sırasında proje dosyasını ezer).
3. Yeni modun dosyasını oku ve **o andan itibaren onun kurallarına uy**.
4. Kullanıcıya onayla: eski mod → yeni mod, neyin değiştiği (ajan seti,
   review kimde, onay politikası, beklenen çarpan). 4-6 satır.

## Kalıcı kurallar

- `.claude/mode` **commit edilir** — proje için varsayılanı takım/oturumlar
  arasında taşır. Kişisel geçici tercih için `--tek` kullan.
- **B/C/D/E modlarında** modu seçmek o ajan setine verilmiş
  onaydır (#27); çağrı öncesi ayrıca sorulmaz. Tur sonunda kaç ajan koştuğu ve
  tahmini maliyet **raporlanır**.
- **A modunda** ajan hiç çağrılmaz; ajan gerekiyorsa mod değiştirmeyi öner, başlatma.
- Mod **hiçbir durumda** şunları gevşetmez: geri alınamaz işlerde onay,
  `test`/`prod` promosyonunun kullanıcıya ait olması, "tamamlandı" öncesi
  eksik-kontrolü, sırların repoya girmemesi.
- Mod değişikliği **geriye dönük değildir** — önceki turlarda yapılan iş
  yeniden değerlendirilmez.
