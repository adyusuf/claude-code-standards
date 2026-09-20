# Çalışma Düzeni — Claude ile Nasıl İlerlenir

## 1. Görev alındığında

1. **Sınıflandır:** bug fix mi, yeni özellik mi, refactor mi, araştırma mı? Her birinin farklı çıktısı var.
2. **Bağlam topla:** projenin `CLAUDE.md`'si → varsa `docs/` → ilgili dosyalar. Düzenlemeden önce **oku**.
3. **Kapsamı doğrula:** talep edilen iş neyse o yapılır. Ne daraltılır ne genişletilir. "Yol üstü" iyileştirme ayrı iştir → not al, sonra öner.
4. **Belirsizlik varsa:** bağımsız kısımları bitir; kalan için tek net soru sor. Yanlış varsayım işi çöpe atacaksa **önce sor**.

## 2. Plan → onay → uygula

- Tek dosyalık küçük değişiklik: doğrudan yap.
- **Birden fazla dosya / mimari etki / şema değişikliği:** önce 5–10 satırlık plan sun — hangi dosya, ne değişecek, neden, hangi riski var. Onay al.
- Büyük işi **dikey dilimlere** böl: her dilim tek başına çalışan ve test edilebilen bir bütün olsun (API + UI + test). Yatay dilim (önce tüm DTO'lar, sonra tüm servisler) yasak.

## 3. Uygulama sırası

```
şema/model → API → sözleşme testi → istemci → e2e → doküman
```

- Her adımda derlenebilir/çalışır durumda kal. "Sonra düzeltirim" bırakma.
- Yarım bırakılan iş varsa `TODO(<ad>): ...` değil, **açıkça mesajda** raporla.

## 4. Doğrulama (bitirmeden önce zorunlu)

- [ ] Build geçiyor (`dotnet build` / `tsc --noEmit` / `expo doctor`)
- [ ] İlgili testler koşuldu ve geçti
- [ ] Formatlayıcı + linter koşuldu (`dotnet format`, `eslint --fix`, `prettier`)
- [ ] Geriye uyumluluk kontrolü (alan/endpoint silindi mi, tip değişti mi)
- [ ] Sır/PII sızıntısı yok
- [ ] Değişen davranış dokümana/CLAUDE.md'ye yazıldı

**Koşmadığın adımı "geçti" sayma.** Koşamadıysan nedenini yaz.

## 5. Raporlama biçimi

- Ne yapıldı → hangi dosyalar → nasıl doğrulandı → ne yapılmadı/kaldı.
- Test kırmızıysa çıktıyı göster. Hata varsa gizleme.
- Uzun anlatım yok; madde madde, dosya yolları tıklanabilir link olarak.

## 6. Bağlam ve token disiplini

- Tüm dosyayı okumak yerine ilgili bölümü oku (`offset`/`limit`, `grep`).
- Aynı dosyayı düzenledikten sonra doğrulamak için tekrar okuma.
- Uzun log/çıktıyı olduğu gibi yapıştırma; ilgili satırları özetle.
- Detay standardı yalnız o konuya girildiğinde aç.

### 6a. `CLAUDE.md` bir kural indeksidir, karar günlüğü değildir

Bir `CLAUDE.md`, o dizinde çalışan **her oturumda** otomatik bağlama girer:
eklenen satırın bedeli bir kez değil, dosyanın okunduğu **her oturumda** ödenir.
Bu yüzden içeriği iki sınıfa ayrılır ve yalnız biri orada durur:

| Aktif `CLAUDE.md`'de **kalır** | `docs/<ayak>-decision-log.md`'ye **taşınır** |
|---|---|
| Kural cümlesi, yasak, kapı, akış | Kuralın gerekçesi, alternatiflerin neden elendiği |
| Tuzak uyarısı (bir daha düşmemek için) | Nasıl keşfedildiğinin hikâyesi, kullanıcı alıntısı |
| Test kilidinin **adı** | O günün koşum tutanağı ("1017/1017 yeşil") |
| Bugün geçerli sözleşme | Tamamlanmış göçün adımları, `DROP` listeleri |

Taşınan her blok geriye **kural cümlesi + detay linki** bırakır. Metin
**parafraz edilmez, birebir taşınır** — parafraz kaybın en sık yoludur.

**Bu bir kapıya bağlanır.** Dosya başına bir boyut tavanı tutulur (cırcır:
tavan yalnız iner) ve merge kapısı büyümeyi reddeder. Gerekçesi ölçülmüştür:
bir projede `backend/CLAUDE.md` Haziran'da 48 KB'ken Ağustos'ta 378 KB oldu —
iki ayda 8 kat. **Tek seferlik temizlik bu sorunu çözmez**, iki ay sonra aynı
yere gelinir; çözen şey kapıdır.

⚠️ Sadeleştirme yaparken kural kaybı **mekanik olarak** denetlenir (yapma
maddeleri, yükümlülük/yasak kipi taşıyan satırlar, ters tırnaklı
tanımlayıcılar). Kapı mutasyonla doğrulanır: bilinen bir kuralı silen bir
deneme kapıyı **kırmalıdır**. Kırmıyorsa kapı dekoratiftir.

### 6b. Eklenti/MCP yüzeyi de token bütçesine dahildir (20/09/2026, kullanıcı kararı)

`CLAUDE.md` kadar pahalı ikinci kalem **etkin eklenti setidir**: her eklentinin
skill ve ajan açıklamaları, MCP araç adları ve varsa oturum başı hook çıktısı
sistem prompt'una girer — yani **her istekte** yeniden okunur ve her subagent
çağrısında tekrar ödenir.

- Etkin eklenti seti **yığınla sınırlıdır**. Projede kullanılmayan bir eklenti
  açık bırakılmaz; ihtiyaç doğunca `settings.json`'da açılır.
- Yeni eklenti açmadan önce maliyeti ölçülür:
  `find <eklenti> -name SKILL.md -exec awk '/^name:|^description:/' {} \; | wc -c`
- **Yetkilendirilmemiş MCP sunucusu açık tutulmaz** — prompt yeri tüketir,
  yetenek vermez.

Ölçüm (20/09/2026, 333 oturum / 103.307 istek): sabit önek medyanı 57.756 token,
toplam harcamanın **%18'i**; 24. haftadan 38. haftaya 27.700 → 63.500 token.
Kapatılan 10 eklentinin yalnız açıklama metni 45.333 karakterdi.

⚠️ Ölçüm yöntemi: `~/.claude/projects/**/*.jsonl` içinde bir oturumun **ilk**
isteğindeki `input + cache_creation + cache_read` toplamı = o oturumun sabit
öneği. Değişikliğin etkisi **yalnız yeni oturumda** görünür; açık oturum
yapılandırma anlık görüntüsünü başlangıçta alır (20/09/2026'da ölçülerek
doğrulandı: aynı oturumda değişiklik öncesi ve sonrası ajan öneği birebir aynı).

## 7. Paralel oturum / worktree disiplini

Aynı repo birden fazla Claude oturumunda açık olabilir:

- Commit öncesi **her zaman** `git status` + `git diff --staged` doğrula; yalnız kendi diff'ini stage'le. `git add -A` kör kullanılmaz.
- `git push --force` / `--force-with-lease` kullanıcı açıkça istemeden yapılmaz.
- Branch checkout ederken başka worktree'de checkout'lu olabileceğini varsay; hata alırsan izole clone kullan.
- Uzun süren işten önce `git fetch` + geride kalınmışsa `--ff-only` pull.

## 8. Onay gerektiren işler (istisnasız)

- Prod'a deploy / prod branch'e merge
- Migration'da `DROP`, veri silme, toplu `UPDATE`
- `git push --force`, branch silme, tag taşıma
- Dış dünyaya gönderim: e-posta, mesaj, sosyal medya paylaşımı, webhook tetikleme
- Yeni bağımlılık, yeni servis, yeni maliyet kalemi
- Kullanıcı verisi içeren dosyanın dışarı çıkması

## 9. Kural kalıcılaştırma

Kullanıcı "bundan sonra hep şöyle olsun" dediğinde:

1. Kural **projeye mi geneline mi** ait, karar ver.
2. Projeye aitse `<proje>/CLAUDE.md`, geneline aitse `~/.claude/CLAUDE.md` veya ilgili `standards/*.md`.
3. Tarih + "KALICI" etiketi + **nedeni** ile yaz. Neden yazılmayan kural sonra yanlışlıkla geri alınır.
4. Aynı turda yaz; "sonra eklerim" deme.

## 10. Canlı pano — uzun kapı/koşum sırasında (KALICI, tüm projeler)

*(20/09/2026: ayrıntı `~/.claude/CLAUDE.md`'den buraya taşındı; aktif dosyada
kural cümlesi + bu bölüme link kaldı.)*

Dakikalarca süren bir kapı, koşum veya deploy başlattığında (merge kapısı, CI,
test bataryası, publish/deploy zinciri, migration) **bir Artifact panosu yayınla
ve koşum boyunca AYNI URL'e yeniden yayınlayarak güncel tut.** Metin raporu
panonun yerine geçmez; ikisini birlikte ver.

### 10a. Panoda bulunması ZORUNLU olanlar

1. **Ağırlıklı genel yüzde.** İşleri maddelere böl, her maddeye kalan *emeğe*
   göre ağırlık ver (toplam 100), tamamlananların ağırlığını topla. Ağırlıksız
   "5/10 madde bitti" yanıltıcıdır — 473 commit'lik bir review ile bir config
   satırı aynı şey değildir.
2. **Madde kırılımları.** Koşan maddenin alt adımları tek tek görünmeli; yüzde
   kırılımdan hesaplanır, tahminden değil.
3. **Canlı ölçüm.** Son ölçümün saati, ölçülen ham veri (süreçler, bellek, SHA,
   dosya damgaları) ve o ölçümün hangi aşamaya karşılık geldiği.
4. **Açık riskler/engeller.** Karar bekleyen veya sonraki maddeyi bloklayan her
   kalem, gerekçesiyle.

### 10b. Kalıcı kurallar

- ⚠️ **Yüzde ÖLÇÜLÜR, uydurulmaz.** Hangi sinyalden okuduğunu panoda yaz
  (süreç imzası, dosya damgası, API sonucu). Ölçemiyorsan aralık ver ve
  "ölçülemiyor" de.
- ⚠️ **Fazla iyimser tahmin bir HATADIR, düzeltilir.** Kırılım çıkarınca yüzde
  düşüyorsa düşür ve neden düştüğünü söyle — sessizce yukarı yuvarlama.
- ⚠️ **Uzun koşumun çıktısını `tail`/`head` gibi tamponlayan bir boruya verme:**
  iş bitene kadar hiçbir ara ilerleme okunamaz. Log dosyasına yaz, panoyu ondan
  besle.
- ⚠️ **Aşama tespiti dolaylıysa bunu SÖYLE.** ("süreç sayısından çıkarıyorum")
  Dolaylı ölçüm yanılabilir; okuyucu neye baktığını bilmeli.
- ⚠️ **Aynı dosya yolunu yeniden yayınla** — yeni URL üretme, kullanıcı sekmeyi
  açık tutuyor.
- Ölçüm aralığını kullanıcı belirler; belirtmezse aşama değişimlerinde raporla.
  Değişmeyen turlarda da kısa bir satır geç, sessiz kalma.
