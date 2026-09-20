# Mod B — Seçici ajan **(VARSAYILAN)**

⚠️ **Mod dosyası olmayan her proje B'dedir** (18/09/2026, kullanıcı kararı;
öncesinde A idi). Varsayılanın kendisi bu üç ajana verilmiş onaydır — ayrıca
sormam. Ajansız çalışmak için `/calisma-modu A`.

Üç ajan açık: **`analiz`**, **`test-yazar`**, **`belge`**. Kod ve review bende.

## Kural
- İzin verilen ajanlar yalnız bu üçü. Başka ajan tipi çağırmam.
- **Kod yazan ajan YOK.** Gerekçe: ajanın yazdığı kodu ben tekrar okurum,
  sen de okursun — aynı kod iki-üç kez token olur.
- Kod review **ben** yaparım (#27: A/B'de review bende). ⚠️ **`feature/* → dev`
  yönünde review yok** — ne elle ne ajan (#25); istisnası `rol-secimi.md` §3'teki
  güvenlik/yedek/kapı kalemidir.
- Bir görevde toplam ajan turu **≤ 4**; aşarsam durur, sorarım.
- Ajan çağrısı öncesi sormam; **her devirde** maliyet satırı geçerim
  (`↳ analiz bitti · ~$3 · tur toplamı ~$3 · eşik ~$25 (B)`), tur sonunda
  toplarım. Eşik iki kademeli: ~$12'de uyarı, **~$25'te durma** (§8).
- `analiz` ve `test-yazar` raporlarını **eksik kontrolü** bloğuyla kapatır;
  eksik/yanlış varsa iş **geri gönderilir ve düzelttirilir** (kapanış = aynı
  doğrulamanın yeniden koşulması), devir için **tek temiz geçiş**
  gerekir (`rol-secimi.md` §7). 2 geri göndermede kapanmazsa durur, sana
  **bildiririm**.
- `analiz` bulgusunu üreten **komutu** da döndürür; komut yoksa bulgu
  "doğrulanmadı" sayılır.

## Ne zaman
- "Bu nasıl çalışıyor / nerede tanımlı" sorusu birden çok ayağa yayılıyorsa → `analiz`
- Davranış değişti, test yazılacak ve iş izole → `test-yazar`
- CLAUDE.md / docs güncellemesi birikmişse → `belge`

## Beklenen maliyet
**1,15–1,35x**. Ajan turu başına ölçülen ortalama $6,9; `analiz` ve `belge`
sonnet/haiku ile bunun altında kalır.
