# Mod E — Workflow fan-out

D'nin ajan setine (14 rol) ek olarak **`Workflow` aracı açıktır**: deterministik,
paralel, çok ajanlı orkestrasyon.

## Kural

⚠️ **Kimin ne yapacağına karar verme kuralı ayrı dosyada:**
[`rol-secimi.md`](rol-secimi.md) — ajan mı ben mi, iş tipi → rol, sıra ve
devir, atlama, çatışma hakemliği, durma, görünürlük. **Rol seçmeden önce oku.**
- ⛔ **Workflow script'i yalnız bu modun 14 rol ajanını koşar.** Diskte 21 etkin
  eklenti ajanı var (`code-reviewer`, `test-engineer`, `code-simplifier` …);
  hiçbirinde §7 kanıt bloğu, geri gönderme ya da temiz geçiş şartı **yoktur**. Script'e
  konursa panoda "review koştu" görünür ama denetim rejimi tek satırla düşer.
- `Workflow` yalnız **5+ gerçekten bağımsız** iş varken kullanılır. Bağımlı
  zincir için Workflow yazmak, sırayla ajan çağırmanın pahalı hâlidir.
- Script `meta.phases` ile aşamalarını bildirir; ilerleme `/workflows`'tan izlenir.
- **Uzun koşum boyunca canlı Artifact panosu zorunludur** (global kural:
  "Uzun kapı/koşum sırasında CANLI PANO"). Ağırlıklı yüzde + ölçüm saati +
  riskler panoda; aynı URL'e yeniden yayınlanır.
- Workflow başlatmadan önce **ajan sayısı ve maliyet tahminini yazarım** —
  bu mod onayı ajan başına sormayı kaldırır, ölçek beyanını değil.
- Review: `qa` ajanı; kritik bulgular bende doğrulanır.
- Workflow **her fazın sonunda** maliyet satırı basar (panoda da görünür) ve
  denetçi ajanlar **eksik kontrolü** bloğunu döndürür ve **tek temiz geçiş**
  şartı aranır (`rol-secimi.md` §7). Eksik bulan faz **geri gönderir ve
  düzelttirir** (script'te retry kapısı; kapanış doğrulamanın yeniden
  koşulmasıdır); 2 geri göndermede kapanmazsa faz durur ve açık bulgular
  panoya yazılır.
- Eşik (§8) mod E'de **~$200 uyarı / ~$400 durma**; aşılacaksa koşum öncesi
  sorulur. Otonom koşumun $100 tavanı bundan bağımsızdır, hangisi önce
  dolarsa o durdurur.

## Ne zaman
Çok dosyalı tarama/denetim, N modülde aynı işin tekrarı, geniş refactor
öncesi keşif. Rutin özellik geliştirme için **fazla ağır**.

## Beklenen maliyet
**7–14x** ⚠tahmin (eski D'de 9 rol üzerine 4–8x'ti; taban artık 14 rollü D).
Duvar saati %50–70 kısalır. Bu mod süreyi satın alır, token'ı değil.

## Tarihçe
18/09/2026, kullanıcı kararı: bu mod **D iken E oldu**. D harfi 14 rollü geniş
takıma verildi ([`D-genis-takim.md`](D-genis-takim.md)); fan-out onun üstüne
biner. Takım karşılığı **Z** artık E'ye denktir (eskiden D'ye).
