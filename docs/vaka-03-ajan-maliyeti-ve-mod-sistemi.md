# Vaka 03 — Yanlış yerden tasarruf: ajan maliyetinin ölçülmesi

> **Özet:** Her ajan çağrısı öncesi onay isteniyordu, gerekçe maliyetti.
> 33 oturum ölçüldüğünde ajan turlarının **toplam maliyetin %7,7'si** olduğu,
> maliyetin **%73'ünün orkestratörün cache okumasından** geldiği çıktı. Yani
> sürtünme maliyeti azaltmıyordu; azalttığı şey **öngörülemezlikti** — ve bunun
> için onay sormak yanlış araçtı. İkinci ölçüm, kendi tahminimin **2-5 kat**
> yüksek olduğunu gösterdi.

## Bağlam

Zincirde 9 (sonra 14) rol ajanı var: `analiz`, `qa`, `gelistirici`,
`test-yazar`, `devops`, `mimar`, `urun-yoneticisi`, `guvenlik`, `veri`,
`kapsam-denetcisi` gibi. Eski kural her `Agent` çağrısından önce haber verip
**onay beklemeyi** zorunlu tutuyordu. Gerekçe açıkça maliyetti.

## Ölçüm 1 — oran (05/09/2026, 33 oturum)

| Ne | Sonuç |
|---|---|
| Ajan turlarının toplam maliyete oranı | **%7,7** |
| Ajan turu başına ortalama | **~$6,9** |
| Maliyetin orkestratörün cache okumasından gelen kısmı | **%73** |

Yani maliyetin ezici çoğunluğu ajanlarda değil, **ana oturumun kendisinde**
birikiyordu. Her çağrıda onay sormak, faturanın %7,7'lik dilimini kontrol etmek
için turun tamamını yavaşlatıyordu.

⚠️ Ölçüm, sürtünmenin **bir işe yaradığını** da gösterdi: onay istemek maliyeti
düşürmüyordu ama turun ne kadar pahalıya çıkacağının **önceden bilinmesini**
sağlıyordu. Sorun aracın kendisiydi, amacın değil.

## Ölçüm 2 — kalibrasyon (08/09/2026, betikle)

Tahmin tablosundaki `qa` satırı `~$8–20` yazıyordu. Aynı oturum betikle
ölçüldü (transcript'teki `usage` alanları toplanarak):

| Ne | Ölçülen |
|---|---|
| Ana oturum | **$26,99** |
| Subagent (3 `qa`/opus turu, 170 mesaj) | **$12,31** |
| Oturum toplamı | **$39,30** |
| `qa` turu başına | **~$4,10** |

Tahmin **2-5 kat yüksekti.** `qa` satırı ölçümle değiştirildi ve tahmin
savunulmadı.

İkinci gözlem ölçüm 1'i doğruladı: aynı oturumda ana $26,99'a karşı subagent
$12,31 — maliyetin çoğu hâlâ ajanlarda değil, orkestratörde.

## Müdahale

1. **Mod sistemi (A–E).** Ajan kullanımı, review'ın kimde olduğu ve onay
   politikası tek bir harfle **peşin** seçiliyor. **Modu seçmek onaydır** —
   çağrı başına ayrıca sorulmuyor. Böylece öngörülebilirlik korunuyor, sürtünme
   kalkıyor.
2. **İki kademeli eşik, moda bağlı.** Yarısında uyarı, tamamında **durma**:
   B ~$12/**$25** · C ~$75/**$150** · D ~$130/**$260** · E ~$200/**$400**.
3. **Maliyet tur sonuna ertelenmiyor.** Her rol devrinde tek satır:
   `↳ analiz bitti · ✅ temiz (grep -rn X → 3) · ~$3 · tur toplamı ~$9 · eşik ~$150 (C)`
4. **Ölçüm defteri.** Her gerçek ajan turunda `subagent_tokens` × model fiyatı
   hesaplanıp deftere yazılıyor (rol, model, iş tarifi, çağrı sayısı, süre,
   token, alt-üst maliyet). Tablo **tek ölçümle değiştirilmiyor** — en az 3 kayıt
   ya da gerçek bir uçtan uca tur gerekiyor.
5. **Tabloda ÖLÇÜLDÜ / ÖLÇÜLMEDİ etiketi.** Tahmin, ölçüm gibi sunulmuyor.

## Sonuç

Kural değişti: A'da ajan yok; B/C/D/E'de **modu seçmek onaydır**, tur sonunda
ajan sayısı ve tahmini maliyet raporlanır. Eski "her çağrı öncesi onay" maddesi
bu maddeye devredildi.

## Dürüst sınırlar

Bu vakanın en önemli kısmı burası:

- Tabloda **ölçülen yalnız iki sayı var**: tur başına ~$6,9 ortalaması ve
  `qa` için ~$4,10. Geri kalan bütün satırlar model fiyat oranından çıkarılmış
  **tahmin** ve tabloda öyle etiketli.
- **`mimar` ve `gelistirici` (yazan roller) hiç ölçülmedi** — üç kalibrasyon
  kaydının hepsi denetim turuydu.
- Takım modları (X/Y/Z) için **hiçbir ölçüm yok**; oradaki çarpanlar açıkça
  "ÖLÇÜLMEDİ" yazıyor.
- **Eşikler bu kalibrasyonla değiştirilmedi**, çünkü üç kayıt da aynı iş
  tipinden (kural dosyası denetimi) geliyordu ve gerçek bir uçtan uca özellik
  turu hâlâ yok.

## Nasıl doğrulanır

```bash
# Oturumun gerçek maliyeti (transcript'teki usage alanları toplanır)
python3 ~/.claude/scripts/oturum-maliyeti.py <oturum-id>

# Elde yalnız subagent_tokens varsa: token × güncel MTok fiyatı
```

## Ders

Bir kontrolü savunurken gerekçesini ölçmek gerekiyor. Burada gerekçe ("maliyet")
yanlıştı ama kontrolün sağladığı fayda ("öngörülebilirlik") gerçekti — ölçüm
ikisini ayırdı ve aynı faydayı daha ucuz veren bir araca geçilebildi.
