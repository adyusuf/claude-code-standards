# Otonom koşum — uzun işi bırakıp gitmek

> C ya da D modunun **üstüne** biner. Tek başına bir mod değildir: ajan setini
> ve review'ı alttaki mod belirler, bu dosya yalnız **durmadan çalışma** ve
> **sana ulaşma** kurallarını ekler.

## Onay kaydı (global #20)

Global kural #20 otonom arka plan işini **açık onay** olmadan yasaklar.
Onay **05/09/2026'da kullanıcı tarafından verildi**: *"bir uzun iş verip
bırakıp çalışmasını isterim, bitene kadar da durmamasını isterim, bana
soracağı varsa da mobilden vs ulaşıp sorsun."*

⚠️ Onay **bu dosyadaki koşullara bağlıdır**. Koşullardan biri sağlanmıyorsa
(iş listesi yok, bütçe yok, bitiş tanımı yok) koşum **başlatılmaz** — #20
yeniden yürürlüktedir.

## Başlamadan önce (üçü de ZORUNLU)

1. **İş listesi + bitiş tanımı.** Her madde bir **kanıta** bağlanır: koşulmuş
   komut, geçen test, ölçülmüş sayı. *"Baktım, vardır"* kanıt değildir (#15).
   Liste yoksa önce `product-manager` çıkarır, sana gösteririm, sonra başlar.
2. **Bütçe: $100 — ÖLÇÜLÜR, tahmin edilmez** (05/09/2026 kullanıcı kararı; eski
   tavan ~$50 idi). Kurallar:
   - **$100'e ulaşınca ya da ÇOK YAKLAŞINCA:** koşum durur, oturum durumu
     kaydedilir (devir notu yazılır) ve kullanıcıdan **YENİ BİR OTURUM
     AÇMASI** istenir. Aynı oturumda devam edilmez — uzun oturum hem pahalı
     hem bağlam sıkıştırmasıyla güvenilmez.
   - **Yeni bir işe başlamak için o işin tahmini maliyetinin ~2 katı kadar YER
     olmalı** (ör. tahmini $10'lık madde için ≥$20 kalan pay). Kalan pay bundan
     azsa iş başlatılmaz, izin istenir. Gerekçe: yarım bırakılan iş, hiç
     başlanmamış işten pahalıdır.
     ⚠️ Eski hâli sabit **$75**'ti ve tavanla çelişiyordu: $100 tavanda harcama
     $25'i geçtiği anda **hiçbir yeni madde başlatılamıyordu** — "bırak git,
     bitene kadar koşsun" vaadi $28'de bitiyordu (08/09/2026 denetim bulgusu).
   - ⚠️ **Bu da bir durma sebebidir** ve aşağıdaki listede sayılır.
   Her turun sonunda:
   ```bash
   python3 ~/.claude/scripts/session-cost.py <oturum-id>
   ```
   Oturum id'si sistem prompt'undaki *Scratchpad Directory* yolunun son
   parçasıdır. ⚠️ Bu komut koşulmadan "şu ana kadar ~$X" **yazılmaz** —
   ölçülmeyen tavan tavan değildir, bir sonraki oturum "aşağı yukarı" der geçer.
   Çıktı API liste fiyatıdır (abonelik faturası değil, tüketim vekili).
3. **Ulaşım yolu doğrulanır.** `PushNotification` terminale her zaman düşer;
   **telefona yalnız Remote Control bağlıysa** düşer. Bağlı değilse bunu
   koşumdan ÖNCE söylerim — "mobilden ulaşırım" diye başlayıp ulaşamamak,
   sessizce bekleyen bir iş bırakmaktır.

## Soru çıkarsa

| Karar | Davranış |
|---|---|
| **Geri alınabilir** (isim, kapsam detayı, tasarım tercihi, kütüphane seçimi) | **Varsay → devam et → bildir.** Bildirimde varsayım açıkça yazılır. Döndüğünde yanlışsa o parça yeniden yapılır. |
| **Geri alınamaz** (deploy, `DROP`, force push, dışarıya gönderim, `test`/`prod` promosyonu, dosya silme) | **DUR ve bekle.** Otonom koşum bunu **hiçbir zaman** gevşetmez. |

⚠️ Varsayımlar **birikir ve sonuç raporunda topluca listelenir** — tek tek
bildirimlerde kaybolmasınlar.

## Durma koşulları

Koşum şu durumlarda durur ve bildirim gönderir:

- İş listesindeki her madde kanıta bağlandı → **bitti**.
- **Bütçe tavanı** aşıldı.
- **Geri alınamaz** bir eyleme gelindi.
- **Tıkanma:** aynı hata **2 tur** üst üste tekrarlandıysa. Üçüncü kez denemek
  öğrenmek değil, döngüdür.
- **Kapsam değişti** — iş, istenenden başka bir şeye dönüşüyorsa.
- Çözülemeyen ajanlar-arası çatışma (`role-selection.md` §4).
- **Sıradaki madde için yeterli bütçe payı yok** (bkz. yukarıdaki 2 kat kuralı).
- **Eksik kontrolü kapanmadı** — bir bulgu 2 kez geri gönderildiği hâlde
  3 geçişte temize ulaşmadıysa (`role-selection.md` §5, §7). Kapanmamış bulgu
  **"geri alınabilir varsayım" kovasına atılmaz**; koşum durur, açık bulgular
  tek tek listelenir.

## Mod kapsamı ve takım

Otonom koşum **C/D ve Y/Z**'nin üstüne biner. **A/B/X'te `/loop` otonom koşumu
başlatılmaz** — zorunlu ilk adım (`product-manager` iş listesi çıkarır) o
modlarda uygulanamaz: A'da ajan yasak, B/X'te o rol sette yok. Kullanıcı A/B/X'te
otonom koşum isterse **önce mod değişikliği önerilir**, koşum kendiliğinden
başlatılmaz (#20).

**Y/Z (takım — arşivde) ek kuralı:** teammate'ler oturumlar arası yaşamaz ama takım ve
görev listesi **diskte kalır**. Bütçe dolup yeni oturum istendiğinde devir notu
şunları taşır: `in_progress` görev bırakılmadığı (hepsi `completed` ya da
`pending`), takım adı (aynı ad yeniden kullanılamaz), açık bulgu listesi.

## Görünürlük

- **Her tur:** ne yapıldı · o ana kadarki harcama · sıradaki madde.
- **Bildirim yalnız gerekince:** varsayım yapıldığında, durulduğunda, bittiğinde.
  Rutin ilerleme için bildirim **gönderilmez** — gereksiz bildirim, gerekli
  olanın da okunmamasını öğretir.
- **Sonuçta:** biten maddeler + kanıtları · **yapılan tüm varsayımlar** ·
  yapılmayanlar ve nedeni.

## Başlatma / durdurma

Koşumu **kullanıcı başlatır** — ben kendi kendime başlatamam (#20):

```
/loop <iş tanımı>
```

Durdurmak: `/loop` görevini iptal et, ya da bir sonraki turda "dur" de.
Koşum kendini durdurduğunda sebebini yukarıdaki listeden adıyla söyler.
