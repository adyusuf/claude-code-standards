# Vaka 04 — Dokuz rolden yalnız biri denetleniyordu

> **Özet:** Ajan zincirinde dokuz rol vardı ama gerçek anlamda denetlenen tek
> rol `gelistirici`'ydi (çıktısı `qa`'ya, oradan orkestratöre gidiyordu).
> `analiz` yanlış sayarsa, `devops` kapıyı bozarsa, `urun-yoneticisi` kapsamı
> kaçırırsa hata **sessizce aşağı akıyordu**. Denetçi ajan eklemek ise subagent
> token'ı **~4x pahalı** olduğu için karşılığını vermiyordu. Çözüm ajan değil,
> **kanıt zorunluluğu** oldu.

## Bağlam

Zincir şöyle işliyordu: orkestratör işi bir role veriyor, rol raporunu
döndürüyor, orkestratör sonucu kullanıyor. `gelistirici`'nin yazdığı kod
`qa`'dan geçiyordu. Diğer sekiz rolün çıktısı ise **doğrudan** kullanılıyordu.

## Bulgu

Denetim boşluğu rollerin doğasından geliyordu:

| Rol | Boşluk |
|---|---|
| `analiz` | "3 yerde kullanılıyor" der, 4.'yü kaçırır — kimse saymaz |
| `devops` | kapıyı/CI'yı bozar, "config, kod değil" diye review'sız geçer |
| `urun-yoneticisi` | kapsamı kaçırır, çıktısı zincire kendiliğinden akar |
| `test-yazar` | assert'sız test yazar, kapsam sayısı yükselir, hata yakalanmaz |

⚠️ En sinsi olan `analiz`: **çok okuyup kısa dönmek** rolün varlık sebebiydi.
Yanlış saydığında bunu doğrulamanın tek yolu aynı taramayı baştan yapmaktı —
ki o da ajanı kullanma sebebini yok ediyordu. Yani rolün faydası ile
denetlenebilirliği doğrudan çelişiyordu.

Bariz çözüm — `qa`'ya ikinci bir denetçi ajan eklemek — ölçümde elendi:
subagent token'ı **~4x pahalı** olduğu için maliyeti faydasını aşıyordu.

## Müdahale

### 1. Kanıt bloğu (zorunlu, her rapor sonunda)

Çıktısına başkasının güveneceği her rol raporunu bununla kapatır:

```
## Eksik kontrolü — geçiş N
- Doğrulama      → koşulan komut / okunan satır aralığı + ham sonucu
- Madde eşlemesi → istenen her madde → karşılığı (dosya:satır)
- Kapsanmayan    → doğrulanamayan + bilerek dışarıda bırakılan
→ Sonuç: temiz YOK  |  VAR → GERİ: <kime> · <ne düzeltilecek> · <kapanış kanıtı>
```

- Blok **temiz geçilse bile** yazılır — görünmeyen kontrol, yapılmamış kontroldür.
- Cevap **kanıt taşır, kalıp taşımaz**: "evet, eminim" geçersiz; "3 dosyada
  `grep -rn X` ile doğruladım, 4. eşleşme test dosyasında" geçerli.
- **Doğrulanamayan şey "tamam" sayılmaz** — "doğrulanmadı" diye raporlanır.

### 2. Bedava denetim: komutu geri döndürmek

`analiz` yalnız sonucu değil, **sonucu üreten komutu** da döndürür
(`grep -rn "X" --include=*.cs`, `rg -c`, `find`). Orkestratör komutu bir
saniyede tekrar koşar ve sayıyı karşılaştırır.

Bu, tam denetimin büyük kısmını **sıfıra yakın maliyetle** verir — dört kat
pahalı bir denetçi ajanın yapacağı işi, bir satırlık sözleşme değişikliğiyle.
Komut döndürülmediyse bulgu **"doğrulanmadı"** sayılır.

### 3. Geri gönderme bir iş emridir, not değil

- Eksik varsa iş **devretmez**, üretene döner: *ne eksik · hangi kanıtla · ne
  yapılacak.*
- **Kullanıcıya taşınmaz.** Denetçi "eksik var mı?" diye ne kullanıcıya ne de
  üreten role sorar — bakar, kanıtı yazar, kararı kendisi verir. "Sence tamam
  mı?" diye devretmek denetim değil, sorumluluğu iade etmektir.
- **Kapanış kanıtı:** düzeltme gelince bulguyu ortaya çıkaran **aynı doğrulama
  tekrar koşulur.** "Düzeltildi" beyanı kapanış sayılmaz.
- **Tavan: aynı iş en çok 2 kez geri gönderilir (3 geçiş).** Sonra zincir durur
  ve kullanıcıya **bildirilir** — soru değil, durum raporu. Kapanmamış bulgular
  **açık bulgu** olarak tek tek listelenir; "denedim olmadı" deyip sessizce
  devretmek yasak.

### 4. Kapatılan iki boşluk daha

- `devops` çıktısı **`qa`'ya girer** — "config, kod değil" bir atlama gerekçesi değil.
- `urun-yoneticisi` çıktısı zincire otomatik akmaz, **kullanıcı onayına** gider.

## Ölçülen takas: iki temiz geçişten bire

Başlangıçta devir için **arka arkaya iki temiz geçiş** aranıyordu. 18/09/2026'da
bire indirildi. Gerekçe ölçüldü: 14 rollü bir turda ikinci geçiş tahmini
maliyetin **~%22'siydi**.

⚠️ Ama bu, kanıt bloğunu **gevşetmedi — tersine tek güvence hâline getirdi.**
İkinci geçiş yokken kanıtsız bir "temiz" artık hiçbir yerde yakalanmaz. Bu
yüzden `Doğrulama` satırının koşulan komutu taşıması **zorunlu** hâle geldi.

Aynı mantıkla orkestratörün kadansı da sadeleşti (20/09/2026): her devirde
**tek satır**, tam blok **tur sonunda bir kez** ve her "VAR" kararında. Bu,
14 rollü bir turdaki 14 orkestratör bloğunu 1'e indirdi — rolün kendi bloğu ve
"VAR" kararları olduğu gibi durduğu için kanıt kaybı yok.

## Sonuç

Denetim maliyeti dört kat pahalı bir ajana değil, **çıktının biçimine** yüklendi:
kanıt taşımayan rapor kabul edilmiyor, doğrulanamayan şey "tamam" sayılmıyor,
bulgu kapanmadan devir olmuyor.

## Dürüst sınırlar

- **~%22 bir tahmindir**, ölçülmedi — tek temiz geçişe inme kararı bu tahmine
  dayanıyor.
- Kanıt bloğu **biçimi** zorunlu; kanıtın **kalitesi** hâlâ orkestratörün
  okumasına bağlı. Kalıp doldurup kanıt sanmak teknik olarak mümkün.
- Tavan (3 geçiş) aşıldığında iş durur ama **açık bulgu listesi elle** tutulur;
  otomatik bir takip yok.
