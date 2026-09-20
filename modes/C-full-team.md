# Mod C — Tam takım

Dokuz rol ajanı açık; **ben orkestratörüm** (ayrı orkestratör ajan YOK — o
ikinci bir soğuk prefix demek).

## Ajan seti
`product-manager` · `analyst` · `architect` · `designer` · `developer` ·
`test-writer` · `qa` · `devops` · `doc-writer`

⚠️ C, **B'nin üst kümesidir** — B'de açık olan `test-writer` burada da açıktır.
Test yazımı `developer`ye bırakılmaz: ürün kodu yazan ajanın kendi testini
yazması, testi "geçsin diye" gevşetmenin en sessiz yoludur.

## Kural

⚠️ **Kimin ne yapacağına karar verme kuralı ayrı dosyada:**
[`role-selection.md`](role-selection.md) — ajan mı ben mi, iş tipi → rol, sıra ve
devir, atlama, çatışma hakemliği, durma, görünürlük. **Rol seçmeden önce oku.**
- Sıra sabit değil; işin gerektirdiği rolleri seçerim ve **hangilerini neden
  seçtiğimi tur başında yazarım**.
- Bağımsız roller **aynı mesajda paralel** başlatılır (tek tur, kısa duvar saati).
- `developer` ajanı yalnız **izole, sözleşmesi net** parçalarda kullanılır
  (tek dosya, tanımlı imza). Çapraz-katman iş bende kalır.
- Review: `qa` ajanı **ilk geçişi** yapar, kritik bulguları **ben doğrularım**.
  Review kaybolmaz, iki katmanlı olur (#27).
- Ajan çağrısı öncesi sormam; **her devirde** maliyet satırı geçerim, tur
  sonunda toplarım (`role-selection.md` §6, §8). Eşik iki kademeli:
  **~$75'te uyarı, ~$150'de durma** — modun kendi +$100–150 beklentisiyle uyumlu.
- Denetçi roller **sormaz, kontrol eder**: eksik/yanlış varsa iş üretene
  **geri gönderilir ve düzelttirilir**, kapanış aynı doğrulamanın yeniden
  koşulmasıyla kanıtlanır; devir için **tek temiz geçiş** yeter (§7).
  2 geri göndermede kapanmazsa zincir durur, açık bulgular listelenip sana
  **bildirilir**.
- `product-manager` çıktısı **senin onayına** gider (§2a); `devops` çıktısı
  `qa`'ya girer (§3).

## Ne zaman
Uçtan uca özellik (backend + web + mobil), 15+ dosya, ya da senin sürenin
token maliyetinden değerli olduğu işler.

⚠️ İşin **güvenlik, şema/migration, kapsam eşiği ya da e2e** boyutu varsa
C yetmez → [`D-wide-team.md`](D-wide-team.md) (14 rol).

## Beklenen maliyet
**2,5–4x** — özellik başına kabaca **+$100–150**. Duvar saati %20–40 kısalır.
