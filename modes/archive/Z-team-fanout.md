# Mod Z — Takım + fan-out (D'nin takım karşılığı)

⚠️ **Z, subagent modu E'nin (fan-out) takım karşılığıdır** — 18/09/2026'dan
önce D'nin karşılığıydı; D harfi geniş takıma geçti.

Y'nin kadrosuna ek olarak **`Workflow` aracı açıktır** — ama önemli bir kısıtla.

⚠️ Ortak kurallar: [`team-rules.md`](team-rules.md) — **§0 ön koşulu
dahil** · rol seçimi [`role-selection.md`](../role-selection.md).

## ⚠️ Kısıt: fan-out'u LİDER koşar, teammate koşamaz

Claude Code 2.1.148'de **in-process teammate arka plan ajanı başlatamaz**
(binary'de birebir yazılı). `Workflow` arka planda koşar.

⚠️ **Buradaki çıkarım DOĞRULANMADI:** yasağın metni `Agent` aracının
`run_in_background` yoluna aittir; `Workflow` ayrı bir kapıdan koşar ve
teammate'e özel bir `Workflow` yasağı binary'de **bulunamadı**. Aşağıdaki kural
bu yüzden mekanizma tespiti değil, **bilinçli bir kısıttır** — gerekçesi
fan-out'un liderde toplanması ve maliyetin tek elde görünmesidir. Denenip aksi
görülürse gerekçesiyle birlikte yeniden değerlendirilir, kendiliğinden düşmez.

Yani:

- **`Workflow`'u ben (lider) çağırırım.** Teammate'ler çağıramaz.
- Teammate'lerin fan-out ihtiyacı varsa bana görev açar, ben koştururum.
- ⚠️ `tmux` teammate modunda bu kısıtın kalkıp kalkmadığı **doğrulanmadı** —
  varsayım yapma, denenmeden "yapılabilir" deme.

Bu yüzden Z, "D + takım" değil; **"takım çalışırken liderin paralel tarama
koşturması"**dır. Fayda: fan-out sonucu geldiğinde onu kullanacak roller zaten
ayakta ve bağlamı sıcak — D'de o an ajanları yeniden kurmak gerekir.

## Kural
- `Workflow` yalnız **5+ gerçekten bağımsız** iş varken.
- **Canlı Artifact panosu zorunlu** (global "Uzun kapı/koşum sırasında CANLI
  PANO" kuralı): ağırlıklı yüzde + ölçüm saati + riskler + **açık bulgu sayısı**.
- Koşum öncesi **teammate sayısı + workflow ajan sayısı + maliyet tahmini** yazılır.
- Review: `qa` teammate'i; kritik bulgular bende doğrulanır.
- Fan-out çıktısı da **tek temiz geçişten** geçer; eksik varsa görev yeniden açılır.

## Ne zaman
Uzun bir özellik + yanında geniş tarama/denetim aynı anda yürüyecekse. Yalnız
tarama varsa **D yeter ve ucuzdur**; yalnız özellik varsa **Y yeter**.

## Beklenen maliyet
**~6–12x** (ÖLÇÜLMEDİ — en pahalı mod). Eşik: ~$300 uyarı / **~$600 durma**.
Bu modu seçmek, ölçülmemiş bir çarpanı peşinen onaylamak demektir.
