# Mod X — Takım: seçici (B'nin takım karşılığı)

Üç rol **teammate** olarak açılır: **`analiz`**, **`test-yazar`**, **`belge`**.
Kod ve review bende. Lider bendim.

⛔ **Ön koşul:** `takim-kurallari.md` §0 — rol tanımlarında takım araçları yok
ve özellik kapalı. İkisi çözülmeden X açılmaz.

⚠️ Ortak kurallar: [`takim-kurallari.md`](takim-kurallari.md) — mekanizma, görev
listesi disiplini, denetimin takımdaki karşılığı, maliyet. **Önce onu oku.**

## Kural
- İzin verilen teammate'ler yalnız bu üçü. Başka rol açılmaz.
- **Kod yazan teammate YOK** (B'deki gerekçe aynen: aynı kod iki-üç kez token olur).
- Kod review **ben** yaparım.
- Bir görevde toplam **≤ 3 teammate** ve **≤ 8 lider→teammate mesajı**
  (`SendMessage` + spawn sayısı; teammate'in kendi iç turları değil — onları
  ölçemem). Aşarsam durur, sorarım.
- Görev `owner`'ını **ben** atarım (`takim-kurallari.md` §2).
- Devir için **tek temiz geçiş**; eksik varsa görev yeniden açılır (§3).

## Ne zaman
B ile aynı işler, **ama roller tur tur veri geçiriyorsa**: `analiz` bir şey
buluyor, ben kod yazıyorum, `test-yazar` aynı bulguya dayanarak test yazıyor,
sonra `analiz`e "şunu da doğrula" diyorum. Tek atışlık işte **B daha ucuzdur**.

## Beklenen maliyet
**~1,5–2,5x** (ÖLÇÜLMEDİ — `takim-kurallari.md` §5).
Eşik: ~$25 uyarı / **~$50 durma**.
