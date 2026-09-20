# Rol seçimi — kim, neye göre, ne zaman

> **Rol seçimi** (§0-§4) C · D · E · **Y · Z**'de geçerlidir; B ve **X**'te §0 ve §1
> uygulanır (ajan seti üç taneyle sınırlıdır). **§5 (durma), §6 (görünürlük+
> maliyet), §7 (eksik kontrolü) ve §8 (eşik + ölçüm) ajan çalışan
> HER modda geçerlidir** — B/X dahil. Daralan şey ajan seti, denetim değil.
> A'da ajan yoktur; §0'ın "kendim yaparım" dalı işler. **A'da §7 değil, global
> #24 geçerlidir** (tek geçişlik zihinsel kontrol) — §7'nin kanıt bloğu ve geri
> gönderme zinciri yalnız ajan çalışan turlar içindir. (Takım modları arşivde:
> [`arsiv/README.md`](arsiv/README.md).)

**Kararı ORKESTRATÖR verir — yani ben.** Ajanlar birbirini çağırmaz, sıradaki
rolü seçmez, kapsamı değiştirmez. Hiçbir ajan tanımında `Agent` aracı yoktur ve
bu **bilinçlidir**: rol seçimi tek bir yerde kalmazsa kimin neyi neden yaptığı
izlenemez hâle gelir ve maliyet öngörülemez büyür.

⛔ **Ajan modeli YALNIZ Claude olabilir (19/09/2026, doğrulandı).** Claude
Code'un subagent `model:` alanı Anthropic modellerini kabul eder — `sonnet`,
`opus`, `haiku` ya da tam Claude model kimliği. Kimi, Gemini, GPT, Grok gibi
modeller **rol ajanı olarak çalıştırılamaz**; onların kendi uygulamaları
(Kimi Code, Gemini CLI) ayrı oturumlardır ve §7'nin kanıt bloğu · geri gönderme ·
kapanış zinciri orada **otomatik işlemez** — elle taşınır. Üçüncü taraf model
karşılaştırmaları bu yüzden "hangi model bu işe uygun" sorusunu yanıtlar,
"bunu kurabilir miyim" sorusunu değil.

⚠️ **Maliyet karşılaştırmasında abonelik/API ayrımı:** Claude Code bir abonelik
üzerinden koşuyorsa Claude token'ları sabit ücrettedir; API fiyat tablolarıyla
yapılan model kıyasları o durumda **marjinal maliyeti abartır**. Kendi coding
uygulaması olmayan bir model (ör. Gemini 3.8 Flash) ajan olarak kullanılırsa
aboneliğin üstüne **ek fatura** biner — tabloda ucuz görünen seçenek pratikte
pahalı olabilir.

**Orkestratörün modeli = oturumun modeli.** Ajanların `model:` alanı vardır
(sonnet/opus/haiku, maliyete göre); orkestratörün yoktur çünkü ayrı bir süreç
değildir — `/model` ne seçtiyse odur. ⚠️ En pahalı koltuk budur: bütün bağlamı
taşır, her ajan çıktısı ondan geçer, maliyeti ajanlardan değil **cache
okumasından** gelir (05/09/2026 ölçümü: toplamın %73'ü). O kalemde Fable 5.1
Opus'un yarısıdır (%2,5 vs %10) — ölçülen 0,90x; uzun bağlamlı orkestratör
için Fable ucuzdur, ajanlar için ise sonnet/haiku kalır.

## §0 — Önce: ajan mı, ben mi?

Rol seçmeden önce **o iş için ajan gerekip gerekmediğine** karar verilir.

| İşin şekli | Karar | Neden |
|---|---|---|
| **Çok okur, az döner** (arama, envanter, sınıflandırma, çapraz kontrol) | **Ajan** | Okuma yükü ajanın bağlamında kalır, bana yalnız sonuç gelir |
| **Az okur, çok yazar** (kod, metin üretimi) | **Ben** | Ajanın yazdığını ben de okurum, kullanıcı da → aynı içerik iki-üç kez token olur |
| **Kararı kullanıcıyla birlikte verilecek** | **Ben** | Ajan kullanıcıyı odadan çıkarır |
| **Tek dosya, sözleşmesi net, keşif yok** | Ajan olabilir | Çıktı dar ve doğrulanabilir |
| **Birkaç dakikalık, tek komutluk** | **Ben** | Ajan başına ~$5-40 sabit maliyet, iş ondan ucuz |

⚠️ Bu tablo maliyet ölçümünden çıktı: subagent token'ı ana konuşmadan ~4 kat
pahalı (cache okuma/yazma oranı 14:1'e karşı 53:1), çünkü her ajan prefix'i
sıfırdan yazar.

## §1 — İşin şekli → rol

| Tetikleyici | Rol |
|---|---|
| İstek belirsiz/geniş, kapsam ve kabul kriteri yok | `urun-yoneticisi` → çıktısı **kullanıcı onayına** gider (§2) |
| "Bu nasıl çalışıyor / nerede tanımlı / kaç yerde kullanılıyor" | `analiz` |
| 10+ dosyaya dokunacak, sıra ve bağımlılık belirsiz | `mimar` |
| Ekran, akış, boş/hata durumu, erişilebilirlik | `tasarimci` |
| Kod: **izole + sözleşmesi net** | `gelistirici` |
| Kod: **çapraz katman / keşif gerekli** | **ben** |
| Davranış değişti, test gerekiyor | `test-yazar` |
| Diff hazır, incelenecek (kod **veya** altyapı yapılandırması) | `qa` → kritik bulguları **ben doğrularım** |
| CI, deploy, kapı, yedek, ortam | `devops` |
| Kalıcı karar alındı, yazılacak | `belge` |
| **— aşağısı yalnız mod D/E —** | |
| Auth, sır, yetki, enjeksiyon, CVE, OWASP eşlemesi | `guvenlik` → kritik bulguları **ben doğrularım** |
| Şema, migration, index, transaction, veri göçü | `veri` → çıktısı `qa`'ya girer |
| Kapsam eşiği (#29) ölçülecek / payda denetlenecek | `kapsam-denetcisi` → **doğrudan bana** |
| E2E spec yazılacak ya da düşen koşum sınıflandırılacak | `e2e-yazar` (yalnız `test` ortamına karşı) |
| Log/metrik/trace/alarm eksiği, performans regresyonu | `gozlemlenebilirlik` → çıktısı `qa`'ya girer |

## §2 — Sıra ve devir

Sıra **sabit değil**; ama bir rol seçildiyse girdisi hazır olmalı:

```
urun-yoneticisi → kapsam + kabul kriteri + kenar durumlar
        ↓
   ⛔ KULLANICI ONAYI (otomatik akmaz — §2a)
        ↓ (bunlar olmadan mimar plan yapamaz)
mimar / tasarimci → dosya planı + akış (paralel koşabilirler)
        ↓
gelistirici | ben → kod
        ↓
test-yazar → test            qa → review (paralel)
        ↓
belge → kalıcı kararlar
```

**Bağımsız roller aynı mesajda paralel başlatılır.** Bağımlı olanlar sıraya
girer — birinin çıktısı ötekinin girdisiyse paralel başlatmak, ikincisinin
eksik veriyle çalışması demektir.

### §2a — Kapsam kapısı (07/09/2026)

`urun-yoneticisi` çıktısı zincire **kendiliğinden akmaz**: kapsam, kabul
kriterleri ve varsayımlar tek blok hâlinde **kullanıcıya sunulur ve onay
beklenir**. Onaydan önce `mimar`/`tasarimci`/kod başlatılmaz.

⚠️ Gerekçe: `urun-yoneticisi`nin denetçisi yoktur ve olamaz — `qa` "yanlış
şeyi doğru yapmışsın" demez, sözleşmeye değil koda bakar. Yanlış kapsam
zincirin tamamına yayılır ve en pahalı hatadır. Buradaki denetçi
**kullanıcıdır**; bir ajan daha eklemek hem pahalı hem yanlış olurdu.

## §3 — Atlama (skip)

Bir rol **atlanabilir**, ama atlama **sessiz olamaz**: tur başında
"`tasarimci` atlandı çünkü görünen arayüz değişmiyor" diye yazılır.

Tipik meşru atlamalar: kapsam zaten net → `urun-yoneticisi` yok · arayüz
değişmiyor → `tasarimci` yok · tek dosyalık iş → `mimar` yok · yeni kalıcı
karar yok → `belge` yok.

### Kapı-eşli roller — yön kuralı (18/09/2026, mod D/E)

`guvenlik` ve `kapsam-denetcisi` **yalnız `dev → test` ve `test → prod`
promosyonlarında** koşar; `feature/* → dev` yönünde atlanır ve bu atlama
**açıklama gerektirmez** (#25 `dev`'i hızlı tutar). Kapı otoritedir, ajan
kapının göremediğini ve kapının kendi bozukluğunu arar —
[`D-genis-takim.md`](D-genis-takim.md) › "Kapı mı ajan mı".

⚠️ `veri` bu kuralın **dışındadır ve tersi geçerlidir**: şemaya dokunan iş
`dev`'e merge edilmeden ÖNCE `veri`'den geçer. Migration geri alınamaz.

⚠️ **`qa` atlanmaz.** Kod **veya altyapı yapılandırması** değiştiyse review
vardır. Altyapı = CI iş akışı, deploy/kapı betiği, yedek betiği, Dockerfile,
IIS/nginx yapılandırması, ortam dosyası şeması, cron. "Diff kod değil, config"
bir atlama gerekçesi **değildir** — `devops` çıktısı da `qa`'ya girer.
Atlanacaksa sebebi kullanıcıya söylenir, sessizce geçilmez.

⚠️ Gerekçe (07/09/2026): `devops` denetimsiz tek riskli roldü; CI kapısına,
yedeğe ve deploy yapılandırmasına dokunuyor. Denetimin kaldırıldığı yerde
ikinci bir göz şart.

#### ⚠️ #25 ile kesişim — hangisi ezer (08/09/2026 hakemliği, §4)

Global #25 `feature/* → dev` yönünde review'ı (elle **ve** ajan) kaldırıyor;
buradaki "`qa` atlanmaz" kuralı review istiyor. Çakışma gerçektir.
**Öncelik: #25 ezer** (§4 önceliği 2 — kullanıcının açık kararı):

- **`dev` yönü:** `qa` **çağrılmaz**. Bulgu görürsem merge'i bloklamam, not
  düşerim; düzeltme `test` promosyonundan önce ele alınır (#25'in kendi kuralı).
- **`test`/`prod` promosyonu:** `qa` **atlanmaz** ve altyapı diff'i kapsamdadır.
- **Tek istisna (§4 önceliği 1 — güvenlik/veri kaybı her zaman kazanır):**
  değişiklik **yedeklemeyi, sır yönetimini ya da güvenlik kapısının kendisini**
  zayıflatıyorsa (`continue-on-error`, kapı devre dışı bırakma, gitleaks
  kapatma, yedek/restore bozma) `dev` yönünde de `qa` koşar ve gerekçesi
  yazılır. Sebep: #25 hızı satın alır, geri alınamaz kaybı değil — #25
  pre-commit gitleaks'i tam bu gerekçeyle zaten açık bırakmıştır.

## §4 — Çatışma

İki rol çelişirse **ben hakemlik ederim** ve gerekçeyi yazarım. Öncelik sırası:

1. **Güvenlik / geriye uyumluluk / veri kaybı** — her zaman kazanır.
2. **Kullanıcının açık kararı** — "şöyle olsun" dediyse tasarım tercihi tartışılmaz.
3. **Deponun mevcut deseni** — genel "best practice"i yener.
4. Kalanı benim kararım, gerekçesiyle.

⚠️ Hakem olamadığım çatışma **kullanıcıya gider** — kendi tercihimi
"ajanlar öyle dedi" diye sunmam.

## §5 — Durma

Şu **dört** durumda zincir durur ve kullanıcıya dönerim:

- **Kapsam değişti** — iş, istenenden başka bir şeye dönüşüyorsa.
- **Geri alınamaz eylem** — deploy, `DROP`, force push, dış dünyaya gönderim.
  Mod bunu **hiçbir zaman** gevşetmez.
- **Ajanlar arası çözülemeyen çatışma** (§4).
- **Maliyet durma kademesine ulaşıldı** (§8 tablosu) — uyarı kademesi durdurmaz,
  durma kademesi durdurur.
- **Mod kendi tur tavanını aştı** — B'de 4 ajan turu.
- **Eksik kontrolü kapanmadı** — §7 bloğunun `Sonuç` satırı "VAR" kalmışsa ya
  da `Kapsanmayan` alanında "doğrulanmadı" varsa **ve** iş 2 kez geri
  gönderildiği hâlde (3 geçiş) temiz sonuca ulaşılamadıysa.
  Tek bir bulgu **durma sebebi değildir**: o geri gönderilir ve düzelttirilir
  (§7), kullanıcıya taşınmaz. Belirsizlikle devam etmek, belirsizliği aşağı
  akışa taşımaktır.

## §6 — Görünürlük ve maliyet (zorunlu)

- **Tur başında:** hangi roller, hangi sırayla, hangileri **neden atlandı**.
- **Her devirde** (bir rol bitip sıradakine geçilirken): tek satır maliyet
  hatırlatması — o rolün tahmini maliyeti + turun kümülatifi + eşiğe uzaklık:

      ↳ analiz bitti · eksik kontrolü ✅ temiz · ~$3 · tur toplamı ~$9 (2 ajan) · eşik ~$150 (C)

- **Tur sonunda:** kaç ajan koştu + toplam tahmini maliyet + eşiğe göre durum.

Bu satırlar olmadan mod C/D çalıştırılmaz — onay peşinen verildiği için
görünürlük tek denetim mekanizmasıdır.

⚠️ **Maliyet hatırlatması ertelenmez** (07/09/2026, kullanıcı kararı). Yalnız
tur sonunda toplanan rakam, "devam etmeyelim" kararını verilemeyecek kadar geç
verdirir. Her devirde görünür; rakamların kaynağı ve eşik §8'dedir.

## §7 — Eksik kontrolü: denetçi **sorar değil; kontrol eder, geri gönderir, DÜZELTTİRİR**

*(07/09/2026 kararı; 08/09/2026'da iki kez netleştirildi: "denetçi eksik var mı
diye sormasın, kontrol etsin ve eksik varsa geri göndersin" + "eksik yanlış
gördüğü şeyleri **düzelttirsin**".)*

Denetçinin konusu yalnız **eksik** değil, **yanlış**tır da: hatalı davranış,
yanlış varsayım, yanlış yere yazılmış kural, yanlış kanıt. İkisi de aynı yolu
izler — bulunur, geri gönderilir, **düzeltilir**, kapanışı doğrulanır.

Çıktısına başka bir rolün ya da kullanıcının güveneceği **her rol** —
`qa`, `analiz`, `devops`, `test-yazar`, `urun-yoneticisi` ve mod D/E'de ayrıca
`guvenlik`, `veri`, `kapsam-denetcisi`, `e2e-yazar`, `gozlemlenebilirlik` —
raporunu şu **kanıt bloğuyla** kapatır:

```
## Eksik kontrolü — geçiş N
- Doğrulama      → koşulan komut / okunan satır aralığı + ham sonucu
- Madde eşlemesi → istenen her madde → karşılığı (dosya:satır)
- Kapsanmayan    → doğrulanamayan + bilerek dışarıda bırakılan
→ Sonuç: temiz YOK  |  VAR → GERİ: <kime> · <ne düzeltilecek> · <kapanış kanıtı>
```

### Orkestratör: devirde tek satır, tam blok turun SONUNDA (20/09/2026, kullanıcı kararı)

Orkestratör her devirde tam blok **yazmaz** — rolün bloğu kanıtı zaten taşıyor,
ikinci kopya aynı kanıtı tekrar eder. Orkestratörün yükümlülüğü:

- **Her devirde tek satır** (§6'daki maliyet satırıyla aynı satır):
  `↳ analiz bitti · ✅ temiz (`grep -rn X` → 3) · ~$3 · tur toplamı ~$9 · eşik ~$150 (C)`
  — "temiz" **kanıtsız yazılamaz**: satır, devri geçiren doğrulamayı taşır.
- **Tam blok iki durumda:** (a) **turun sonunda bir kez** — turun tamamı için
  madde eşlemesi + kapsanmayan; (b) **her "VAR" kararında** — geri gönderme
  neyin, hangi kanıtla, kime döndüğünü taşımak zorunda.
- Rolün kendi bloğu **yutulmaz**: devir satırının yanında kullanıcıya olduğu
  gibi geçer (aşağıdaki "Diğer kurallar").

Bu, D/E gibi 14 rollü bir turda 14 orkestratör bloğunu 1'e indirir; rolün
bloğu ve "VAR" kararları olduğu gibi durur — yani kanıt kaybı yok, kopya yok.

⚠️ **Bu bir soru listesi değil, bir kontroldür.** Denetçi "eksik var mı?" diye
kullanıcıya da üreten role de **sormaz** — bakar, kanıtı yazar, kararı kendisi
verir. "Sence tamam mı?" diye devretmek denetim değil, sorumluluğu iade
etmektir.

### Eksik bulunduğunda: GERİ GÖNDERME

İş **devretmez**, üretene geri döner. Geri gönderme şunu içerir: **ne eksik ·
hangi kanıtla · ne yapılacak.** Düzeltme gelince kontrol **baştan** başlar,
sayaç sıfırlanır.

| Denetçi | Eksik bulunca geri gönderdiği yer |
|---|---|
| `qa` | Üretene — `gelistirici` ya da ben → düzeltme → **yeniden `qa`** |
| `analiz` | Kendine: devretmez, taramasını tamamlar |
| `test-yazar` | Kendine; eksik olan ürün kodu davranışıysa **bana** |
| `devops` | Kendine; koşmayan kapıyı "doğrulanmadı" yazar, **yeşil demez** |
| `urun-yoneticisi` | Kendine; belirsizliği **varsayım** olarak yazar, soru bırakmaz |
| orkestratör (ben) | İlgili role; ben ürettiysem kendime |

**Kullanıcıya ne zaman gider?** Yalnız §5'teki durma sebeplerinde ve aşağıdaki
tavanda — ve o zaman da **soru değil, durum raporu**: "kapanmadı · şu eksik ·
şunlar denendi".

### Düzelttirme: bulgu **kapanmadan devir yok** (08/09/2026, kullanıcı kararı)

Geri gönderme bir not değil, **iş emridir**. Denetçi bulduğu eksiği/yanlışı
düzelttirmekle yükümlüdür; bulguyu rapora yazıp geçmek **kapanış sayılmaz**.

1. **Denetçi düzeltmez, düzelttirir.** `qa` hâlâ "bulur, düzeltmez" — ama
   düzeltmeyi **takip eder ve kapanışını doğrular**. Düzelten taraf üretendir
   (`gelistirici` / ben); `analiz` ve `urun-yoneticisi` kendi çıktısını kendi
   düzeltir.
2. **Kapanış kanıtla olur.** Düzeltme geldikten sonra bulguyu ortaya çıkaran
   **aynı doğrulama tekrar koşulur** ve sonucu yazılır. "Düzeltildi" beyanı
   tek başına kapanış değildir.
3. **"Sonra bakarız" ile kapanmaz.** Bir bulgu ancak üç yoldan biriyle kapanır:
   **(a)** düzeltildi + kanıtlandı · **(b)** kullanıcı açıkça "yapma" dedi ·
   **(c)** kapsam dışı olduğu gerekçesiyle **kullanıcıya bildirildi** ve
   raporda açık bulgu olarak listelendi. Sessizce düşen bulgu yoktur.
4. **Kozmetik bulgular da kaybolmaz.** Devri bloklamazlar (ciddi değiller) ama
   ya aynı turda düzelttirilir ya "açık bulgu" diye raporlanır.
5. **Açık bulgu listesi tur boyunca taşınır.** Tur sonu raporunda "kapanan / açık
   kalan" ayrımı görünür — global #24'ün eksik-kontrolüyle aynı hattır.

### Kaç geçiş? — **1 temiz** (18/09/2026, kullanıcı kararı)

Devir için **bir kez** "ciddi eksik YOK" yeterlidir (`✅ temiz`).

**"Ciddi eksik" nedir?** Davranışı değiştiren, güvenliği/geriye uyumluluğu/
veriyi etkileyen ya da **kullanıcının istediği bir maddeyi karşılıksız
bırakan** her şey. Kozmetik notlar ve bilerek kapsam dışı bırakılanlar ciddi
eksik değildir — raporda listelenir, devri bloklamaz.

⚠️ **Tek geçiş, kanıt bloğunu daha da bağlayıcı yapar.** İkinci geçiş yokken
o blok tek güvencedir: kanıtsız "temiz" artık hiçbir yerde yakalanmaz. Bu
yüzden `Doğrulama` satırı **koşulan komutu / okunan aralığı** taşımak
zorundadır ve **doğrulanamayan şey "tamam" sayılmaz** (aşağıdaki "Diğer
kurallar").

**Değişmeyenler:**

- **"VAR" çıkarsa geri gönderilir** — iş üretene döner, kullanıcıya taşınmaz (§7 başı).
- **Düzeltme geldiğinde bulguyu ortaya çıkaran doğrulama tekrar koşulur.**
  Bu bir "ikinci geçiş" değil, **kapanış kanıtıdır**: "düzeltildi" beyanı
  kapanış sayılmaz.
- **Tavan: aynı iş en çok 2 kez geri gönderilir (3 geçiş).** Sonra zincir durur
  ve kullanıcıya **bildirilir** — soru değil, durum raporu. Kapanmamış bulgular
  **açık bulgu** olarak tek tek listelenir; "denedim olmadı" diyip sessizce
  devretmek yasaktır.

<details>
<summary><b>Opsiyon: iki ardışık temiz geçiş (2/2)</b> — kapalı</summary>

Kullanıcı "iki kere baksın" derse devir için arka arkaya iki temiz sonuç
aranır. O hâlde geçiş 2 aynı kontrolün tekrarı olamaz: geçiş 1'de
kullanılmamış **en az bir bağımsız kanıt kaynağı** kullanır (başka komut,
kodun karşı ucundan okuma, ya da orijinal isteğin madde madde eşlenmesi) ve
geçiş 1'in araç çağrısı sayısının **yarısını aşmaz**, aynı turun içinde
(+%10–20 yük). Kanıtsız "temiz" ikinci geçiş 2/2'yi törene çevirir. Tavan o
hâlde 2 geri gönderme = 4 geçiş olur.

Tarihçe: 07/09/2026'da sırasıyla 2 → 1 → **2**; 08/09/2026'da geçiş 2'nin
ölçütü "sayı değil bağımsız kanıt" olarak netleştirildi; **18/09/2026'da
kullanıcı kararıyla 1'e indirildi** ("tek bir kere eksik yoktur denmesi
yeterli olsun"). Ölçülen gerekçe: 14 rollü bir turda ikinci geçiş tahmini
maliyetin **~%22'siydi**.
</details>

### Diğer kurallar

- Blok **her seferinde** yazılır; temiz geçilse bile görünür. Görünmeyen
  kontrol, yapılmamış kontroldür.
- Cevap **kanıt taşır, kalıp taşımaz.** "Evet, eminim" tek başına geçersiz;
  "3 dosyada `grep -rn X` ile doğruladım, 4. eşleşme test dosyasında" geçerli.
- **Doğrulanamayan şey "tamam" sayılmaz.** Doğrulanamıyorsa ya doğrulama yolu
  bulunur ya "doğrulanmadı" diye raporlanır — tahmin, temiz geçiş yerine geçmez.
- ⚠️ Orkestratör bu bloğu **yutmaz**. Ajanın eksik kontrolü ve geri gönderme
  kararı, devir satırıyla birlikte kullanıcıya olduğu gibi geçer.

### `analiz` için ek: sonuç doğrulanabilir olmalı

`analiz` yalnız sonucu değil, **sonucu üreten komutu** da döndürür
(`grep -rn "X" --include=*.cs`, `rg -c`, `find`). Orkestratör komutu bir
saniyede tekrar koşar ve sayıyı karşılaştırır.

⚠️ Gerekçe: `analiz` çok okuyup kısa döner; "3 yerde kullanılıyor" deyip 4.'yü
kaçırdığında bunu doğrulamanın tek yolu aynı taramayı baştan yapmaktır — ki o
da ajanı kullanma sebebini yok eder. Komutu geri döndürmek tam denetimin
büyük kısmını **sıfıra yakın maliyetle** verir. Komut döndürülmediyse bulgu
"doğrulanmadı" sayılır.

## §8 — Maliyet: rakamlar ve eşik

**Ölçülen** (05/09/2026, Proje A, 33 oturum): ajan turu başına ortalama
**$6,9**; toplam maliyetin **%73'ü** orkestratörün cache okumasından geliyor,
ajanlardan değil. Ajan turları toplamın %7,7'siydi.

| Rol | Model | Tur başına tahmin |
|---|---|---|
| `belge` | haiku | ~$0,5–2 |
| `analiz` · `tasarimci` · `urun-yoneticisi` · `test-yazar` · `devops` | sonnet | ~$2–6 |
| `qa` | opus | **~$4** (ÖLÇÜLDÜ — 3 kayıt, 08/09/2026; ort. $4,10) |
| `mimar` · `gelistirici` | opus | ~$8–20 (ÖLÇÜLMEDİ — yazan roller, `qa`'dan pahalı olması beklenir) |
| `kapsam-denetcisi` · `e2e-yazar` · `gozlemlenebilirlik` | sonnet | ~$2–6 (ÖLÇÜLMEDİ — mod D, 18/09/2026) |
| `guvenlik` · `veri` | opus | ~$4–10 (ÖLÇÜLMEDİ — `qa` sınıfı denetçiler) |
| `Workflow` (mod E) | karışık | ajan sayısı × yukarısı + orkestrasyon payı |

⚠️ Bu tablodaki tek **ölçülen** sayı $6,9 ortalamasıdır; model kırılımı
fiyat oranından çıkarılmış **tahmindir** ve öyle sunulur. Gerçek fatura
farklıysa tablo düzeltilir, tahmin savunulmaz.

### Kalibrasyon: tablo ÖLÇÜLEREK düzeltilir (08/09/2026, kullanıcı kararı)

Tablo bugün tahmindir; **her gerçek ajan turunda ölçüm kaydedilir** ve yeterli
veri birikince tablo düzeltilir. Yöntem:

1. Tur bitince görev bildirimindeki **`subagent_tokens`** okunur.
2. **Tercih edilen yol:** `python3 ~/.claude/scripts/oturum-maliyeti.py <oturum-id>`
   — transcript'teki `usage` alanlarını toplar, **ölçer**. Oturum id'si
   scratchpad yolunun son parçasıdır.
   Elde yalnız `subagent_tokens` varsa modelin MTok fiyatıyla çarpılır; güncel
   liste **bundled `claude-api` skill'indedir** (`~/.claude/skills/` altında
   değil — `Skill` aracıyla açılır). 08/09/2026: **Opus 5** $5 girdi / $25 çıktı ·
   **Sonnet 5** $2 / $10 · **Haiku 4.5** $1 / $5.
3. Girdi/çıktı kırılımı bildirimde yok, o yüzden **alt-üst sınır** yazılır
   (hepsi girdi ↔ hepsi çıktı). Gerçek değer alt sınıra yakındır: ajan turları
   okuma ağırlıklıdır.
4. Sonuç aşağıdaki deftere eklenir. **Tablo tek ölçümle değiştirilmez** — en az
   3 kayıt ya da gerçek bir uçtan uca C/D özellik turu gerekir; tek bir dar
   kapsamlı koşumdan genelleme yapmak, düzeltmeye çalıştığımız hatanın aynısıdır.

#### Ölçüm defteri

| Tarih | Rol / model | İş | Ham ölçüm | Maliyet aralığı |
|---|---|---|---|---|
| 08/09/2026 | `qa` / opus | 17 markdown kural dosyasının 10 karara karşı denetimi (20 araç çağrısı, 355 sn) | 85.682 token | **$0,43 – $2,14** |
| 08/09/2026 | `qa` / opus | A/B/C/D mod tanımları denetimi (28 çağrı, 633 sn) | 105.118 token | **$0,53 – $2,63** |
| 08/09/2026 | `qa` / opus | X/Y/Z takım modları denetimi (57 çağrı, 872 sn) | 137.942 token | **$0,69 – $3,45** |
| 08/09/2026 | **oturum toplamı** (ölçüldü, betikle) | 3 `qa` turu + orkestratör, 170 mesaj | — | **ana $26,99 + subagent $12,31 = $39,30** |
| 13/09/2026 | `test-yazar` / sonnet | Proje A: bash 3.2 e2e parça döngüsü davranış testi, 6 senaryo + 3 mutasyon (28 çağrı, 308 sn) | 99.994 token | **$0,20 – $1,00** |
| 13/09/2026 | `qa` / opus | Proje A: iki merge kapısı düzeltmesinin incelemesi — 3 kritik bulgu, simülasyon + docker bash 5.2 (18 çağrı, 444 sn) | 114.795 token | **$0,57 – $2,87** |
| 13/09/2026 | `test-yazar` / sonnet | Proje A: qa bulguları için koşucu davranış testi (sahte npx) + kilitler, 9 mutasyon (69 çağrı, 984 sn) | 193.779 token | **$0,39 – $1,94** |
| 13/09/2026 | `analiz` / sonnet | Proje A: test ortamında düşen 7 e2e testinin sınıflandırması (gerileme/bayat spec), git geçmişi (98 çağrı, 1222 sn) | 175.657 token | **$0,35 – $1,76** |
| 13/09/2026 | `qa` / opus | Proje A: kapı düzeltmelerinin 2. turu — 7 bulgunun kapanış kanıtı, 6 küçük bulgu (29 çağrı, 657 sn) | 109.862 token | **$0,55 – $2,75** |
| 13/09/2026 | `test-yazar` / sonnet | Proje A: bayat ürün sihirbazı e2e spec'leri, test ortamına karşı gerçek koşum (75 çağrı, 907 sn) | 146.706 token | **$0,29 – $1,47** |
| 13/09/2026 | `test-yazar` / sonnet | Proje A: qa küçük bulguları için 3 kilit + mutasyon (43 çağrı, 435 sn) | 91.468 token | **$0,18 – $0,91** |

| 14/09/2026 | `gelistirici` / opus | Proje B: Android Ödeme Al web eşitleme — 18 dosya, derleme+59 test (73 çağrı, 1225 sn) | 286.217 token | **$1,43 – $7,16** |
| 14/09/2026 | `gelistirici` / opus | Proje B: iOS Ödeme Al web eşitleme — 21 dosya, xcodegen, 92 test (76 çağrı, 1198 sn) | 263.389 token | **$1,32 – $6,58** |
| 14/09/2026 | `gelistirici` / opus | Proje B: Android geri gönderme düzeltmesi (Ad soyad alanı; devam turu, kümülatif 296.818) (10 çağrı, 102 sn) | ~10.600 token (fark) | **$0,05 – $0,27** |
| 14/09/2026 | `gelistirici` / opus | Proje B: iOS geri gönderme düzeltmesi (tutar doğrulaması + hata başlığı; devam turu, kümülatif 276.549) (11 çağrı, 154 sn) | ~13.200 token (fark) | **$0,07 – $0,33** |
| 14/09/2026 | `test-yazar` / sonnet | Proje B: Android Ödeme Al JVM testleri, 62 test + 4 mutasyon (59 çağrı, 561 sn) | 185.031 token | **$0,37 – $1,85** |
| 14/09/2026 | `test-yazar` / sonnet | Proje B: iOS Ödeme Al ekran+kural testleri, 34 test + 5 mutasyon (104 çağrı, 1869 sn) | 358.542 token | **$0,72 – $3,59** |
| 16/09/2026 | `qa` / opus | Proje C: `dev` öncesi 4 commit review'ı geçiş 1 — 3 yüksek bulgu, ffmpeg denemesi (26 çağrı, 216 sn) | 104.366 token | **$0,52 – $2,61** |
| 16/09/2026 | `qa` / opus | Proje C: geçiş 2, düzeltmelerin kapanışı + yeni yüksek bulgu (HLS bsf) (devam turu, kümülatif 139.045) (7 çağrı, 124 sn) | ~34.700 token (fark) | **$0,17 – $0,87** |
| 16/09/2026 | `qa` / opus | Proje C: geçiş 3, 1/2 temiz (devam turu, kümülatif 148.032) (2 çağrı, 49 sn) | ~9.000 token (fark) | **$0,04 – $0,22** |
| 16/09/2026 | `qa` / opus | Proje C: geçiş 4, istek→kod eşlemesi, 2/2 temiz (devam turu, kümülatif 153.614) (3 çağrı, 106 sn) | ~5.600 token (fark) | **$0,03 – $0,14** |

✅ **Kalibrasyon 1 yapıldı (08/09/2026):** 3 kayıt doldu ve betikle ölçülen
oturum toplamı elde edildi — 3 `qa`/opus turu için **subagent $12,31**, tur
başına **~$4,10**. Tablodaki eski `~$8–20` tahmini **2-5 kat yüksekti**;
`qa` satırı ölçümle değiştirildi.

⚠️ **Hâlâ ölçülmemiş olanlar:** `mimar`/`gelistirici` (yazan roller — üçü de
denetim turuydu), sonnet ve haiku rolleri, ve **X/Y/Z'nin tamamı**. Eşikler
değiştirilmedi: üç kayıt da aynı iş tipinden (kural dosyası denetimi) ve
gerçek bir uçtan uca özellik turu hâlâ yok. Eşik düzeltmesi için o gerekir.

⚠️ Orkestratör payı ölçümü doğruluyor: aynı oturumda **ana $26,99** vs
**subagent $12,31** — yani maliyetin çoğu hâlâ ajanlarda değil, bende.

### Eşik: **moda bağlı, iki kademeli** (08/09/2026, kullanıcı kararı)

| Mod | Uyarı (yarısı) | **Durma** |
|---|---|---|
| **A** | — (ajan yok) | — |
| **B** | ~$12 | **~$25** |
| **C** | ~$75 | **~$150** |
| **D** | ~$150 | **~$300** |
| **X** | ~$25 | **~$50** |
| **Y** | ~$150 | **~$300** |
| **Z** | ~$300 | **~$600** |

- **Uyarı kademesi:** devir satırına tek kelime eklenir (`⚠ eşiğin yarısı`),
  iş **durmaz**. Amaç sürprizi kaldırmak: tavana çarpmadan önce görürsün.
- **Durma kademesi:** zincir durur, ne harcandığı ve ne kaldığı yazılır,
  devam kararı kullanıcınındır.
- ⚠️ Eşik **modun ilan ettiği maliyetle tutarlı olmalıdır.** Önceki tek-değer
  ($40) mod C'nin kendi beklentisinin (+$100–150) dörtte birindeydi; normal
  bir C özelliğinin **ortasında** çalıyordu — yani ya her işte gereksiz soru
  ya ölü kural demekti. Fren, anormal durumda çalar; normalde değil.
- Otonom koşumun kendi **$100** tavanı bundan **bağımsız** olarak geçerlidir
  (`otonom-kosum.md`) ve hangisi önce dolarsa o durdurur.
- Eşikler kullanıcı tarafından değiştirilebilir.
