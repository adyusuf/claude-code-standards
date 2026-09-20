# Karar defteri — `~/.claude/CLAUDE.md`'den taşınan metin

> `standards/00-calisma-duzeni.md` §6a gereği: aktif `CLAUDE.md` bir **kural
> indeksidir**, karar günlüğü değildir. Kuralın gerekçesi, nasıl keşfedildiği,
> kullanıcı alıntısı, ölçüm tutanağı ve yürürlükten kalkmış madde metinleri
> buraya taşınır. Metin **birebir** taşınmıştır, parafraz edilmemiştir.
>
> Taşıma: 20/09/2026 — `CLAUDE.md` 41.363 → 22.518 bayt. Kural kaybı
> `scripts/md-kural-kapisi.py` ile denetlendi. Aktif dosyadaki kural cümlesi
> buraya `§<madde no>` ile bağlanır.
>
> İki bölüm var: **§N** başlıkları aktif dosyadan tamamen çıkan metni tutar;
> sondaki **Ek**, aktif dosyada kısaltılarak yeniden yazılmış satırların
> özgün hâlini tutar (kısaltmada düşen yan cümleler burada aranır).

## Global Çalışma Kuralları

> Bu dosya **her projede, her oturumda** otomatik yüklenir. Kısa tutulur.
> Detaylı standartlar `~/.claude/standards/` altındadır; ilgili görevde **oku**.

## §21 — [#27'ye devredildi — 05/09/2026] Eski hâli: review'ı ben yaparım, review ajanı s

21. **[#27'ye devredildi — 05/09/2026]** Eski hâli: review'ı ben yaparım, review ajanı spawn edilmez (2026-08-14). Artık mod belirler: A/B'de review **ben**; C/D'de `qa` ajanı ilk geçiş, kritik bulguları **ben** doğrularım. Numara, atıflar kırılmasın diye korunuyor.

## §22 — [KALDIRILDI — 05/09/2026, kullanıcı kararı] Eski hâli: tarayıcıda canlı UI doğru

22. **[KALDIRILDI — 05/09/2026, kullanıcı kararı]** Eski hâli: tarayıcıda canlı UI doğrulaması için önce sor (2026-08-14). Artık gerekli gördüğümde sormadan doğrularım; ölçüsü işin kendisi (saf mantık/backend değişikliğinde tarayıcı açmam). Numara korunuyor.

## §23 — [#27'ye devredildi — 05/09/2026] Eski hâli: her `Agent`/`Workflow` çağrısından ö

23. **[#27'ye devredildi — 05/09/2026]** Eski hâli: her `Agent`/`Workflow` çağrısından önce haber ver, maliyet söyle, onay bekle (2026-08-14). Artık mod belirler: **A'da ajan hiç çağrılmaz** (gerekiyorsa mod değişikliği önerilir), **B/C/D'de modu seçmek onaydır**; tur sonunda ajan sayısı + tahmini maliyet raporlanır. Otomatik yönlendirme de çağrıdır — A'da uyulmaz. Numara korunuyor.

## §24 — "Tamamlandı" demeden önce kendi kendine eksik-kontrolü zorunlu (2026-08-25, kull

    - **Test** (#8), **build/lint/format**, ve varsa **SETUP.md/.env.example/sır envanteri** (#16) güncellemesi gerçekten çalıştırıldı mı, yoksa "muhtemelen çalışır" mı (#15 bunu zaten yasaklıyor — burada ayrıca kontrol listesine giriyor)?
    - Bu kontrolü geçtikten sonra "tamamlandı" de; kontrolün kendisini kullanıcıya adım adım anlatma, sonucu raporun içine kısaca yedir (ör. "X, Y, Z değişti; testler geçti; A henüz yapılmadı çünkü ...").
    Gerekçe: kullanıcı aynı görevde arka arkaya 4-5 kez "eksik var mı?" diye sormak zorunda kaldı ve her seferinde gerçekten eksik çıktı — yani "tamamlandı" raporu güvenilir değildi. Kullanıcının ayrıca sormasına gerek kalmadan bu kontrolün **her görevde otomatik** çalışması isteniyor. **How to apply:** Çok küçük/tek satırlık değişikliklerde kontrol listesi bir iki saniyelik zihinsel geçiş olarak yeterli — ayrı bir adım/rapor gerekmez. Çok adımlı, çok dosyalı veya "bitti" denip PR/merge'e gidecek işlerde kontrol listesi mutlaka bilinçli çalıştırılır.

## §25 — `dev`'e merge hızlıdır: review ve ağır kapılar yalnız `test` ve `prod` promosyon

    - Gerekçe: kullanıcı "dev'e merge ederken review ya da gate vs yapma, atla; vakit kaybı olmadan çalışalım" dedi. `dev` entegrasyon dalıdır, dışarı bir şey yayınlamaz; kalite kapısının gerçek yeri dış dünyaya çıkan `test`/`prod` promosyonudur. Bu kural #19'un kapsamını daraltır: o taramalar artık `test`/`prod` yönünde geçerlidir; review'ın kimde olduğunu #27 (mod) belirler.

## §26 — Verilen iş planlandıktan sonra: `dev`'i pull et → `dev`'den dal/worktree aç → or

    1. **Önce `git fetch` + `dev`'i güncelle.** Bayat bir tabandan dallanmak, başka oturumların commit'lerini hiç görmeden çalışmak demektir (bu repo paralel worktree'lerle kullanılıyor).
    4. **`test` ve `prod` promosyonunu KULLANICI söyler.** Kendiliğinden `test`/`prod`'a merge YOK; kullanıcı açıkça "merge" / "prod merge" demeden o dallara dokunulmaz (mevcut #25 ve proje kuralları geçerliliğini korur).
    **Why:** Kullanıcı `dev`'i temiz ve izlenebilir tutmak, her işi ayrı ayrı görebilmek ve dışarı çıkan promosyonun kontrolünü elinde tutmak istiyor. **How to apply:** Çok adımlı bir iş listesi verildiğinde, ilk kod satırından önce tabanı güncelle ve dalı aç; her maddeyi bitirdiğinde doğrula, commit'le ve `dev`'e merge et, sonra sıradakine geç.

## §27 — Çalışma modu (A/B/C/D) her projede seçilebilir; seçim ONAYDIR (2026-09-05, kulla

    - **A** Skill (ajan yok; artık varsayılan DEĞİL, açıkça seçilir) · **B** Seçici (`analiz`/`test-yazar`/`belge`) — **VARSAYILAN** · **C** Tam takım (9 rol ajanı, B ⊂ C) · **D** Geniş takım (14 rol: C + `guvenlik`/`veri`/`kapsam-denetcisi`/`e2e-yazar`/`gozlemlenebilirlik`, C ⊂ D — 18/09/2026) · **E** Fan-out (`Workflow`, D'nin üstüne biner; 18/09/2026'ya kadar D harfindeydi).
    - **Agent Teams karşılıkları (08/09/2026) — ⛔ bugün BAŞLATILAMAZ, `~/.claude/modes/takim-kurallari.md` §0:** rol tanımlarında `SendMessage`/`Task*` yok (9/9 kapalı allowlist) ve özellik `--agent-teams` / `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` + plan kapısının arkasında. **`/teams` diye bir komut yoktur.** **X** ≙ B · **Y** ≙ C · **Z** ≙ **E** (18/09/2026'dan önce D). Yeni D'nin takım karşılığı yoktur. Aynı roller, ama teammate olarak: oturum boyunca yaşarlar, `SendMessage` ile konuşurlar, paylaşılan görev listesi üzerinden yürürler. Ortak kurallar `~/.claude/modes/takim-kurallari.md`. Lider benim ve görev `owner`'ını **ben** atarım — serbest kapma kapalıdır (izlenebilirlik, #27 ile aynı gerekçe). Denetim (§7: kontrol et → geri gönder → düzelttir → tek temiz geçiş) aynen geçerli; geri gönderme = görevi yeniden açmak. **Z'de `Workflow`'u yalnız lider koşar** (gerekçe: fan-out liderde toplansın — teammate `Workflow` yasağı binary'de **doğrulanmadı**). Çarpanlar **ÖLÇÜLMEDİ**: X ~1,5–2,5x · Y ~3–6x · Z ~6–12x. Teammate'ler oturumlar arasında yaşamaz ama **görev listesi diskte kalır**.
    - ⚠️ **Teammate'e kapalı olanlar** (hepsi doğrulandı): geri alınamaz eylem — teammate liderin izin kipini devralır (`--dangerously-skip-permissions` / `acceptEdits` komut satırına geçer), o yüzden **durur ve lidere bildirir** · cron/`Monitor` kurmaz (#20) · senkron subagent çağırmaz (yolu açıktır, maliyeti görünmez) · `TaskUpdate` ile kendine görev kapmaz, `TaskCreate` ile kapsam büyütmez — **kapatma anahtarı yoktur, spawn prompt'una yazılır** · aynı dosyaya iki teammate girmez (dosya ayrımı ya da `isolation:"worktree"`) · eksik kontrolü bloğu **lidere de** gider (teammate DM'leri lidere yalnız özet düşer).
    - **Why:** Ölçüm (Proje A, 33 oturum): ajan turları toplam maliyetin %7,7'siydi, tur başına ortalama $6,9 — her turdaki onay sürtünmesi maliyeti değil ÖNGÖRÜLEMEZLİĞİ azaltıyordu. Mod seçimi öngörülebilirliği peşinen sağlıyor. **How to apply:** Oturum başında modu **şu öncelikle** oku: **oturumluk seçim** (`<scratchpad>/mode`, `--tek` ile yazılır) → proje `.claude/mode` → **B**. ⚠️ Oturumluk seçim scratchpad'dedir çünkü bağlam sıkışınca skill yeniden yüklenmez; bu satır olmazsa `--tek` kararı sessizce proje moduna döner. Yoksa **B'de başla ve iş hak ediyorsa en düşük yeterli modu tek satırla ÖNER** (kendin geçme — kullanıcı kararı 05/09/2026). ⚠️ B varsayılan olduğu için **mod dosyası olmayan bir projede `analiz`/`test-yazar`/`belge` ayrıca sorulmadan çağrılabilir** — varsayılanın kendisi o üç ajana verilmiş onaydır (18/09/2026). Diğer on bir rol için mod C/D/E gerekir. Kullanıcı bir mod adı söylerse `/calisma-modu` skill'ini çalıştır.

## §28 — Denetçi her geçişte eksik/yanlış KONTROL EDER, GERİ GÖNDERİR ve DÜZELTTİRİR; mal

    - **Tek temiz geçiş yeterlidir (18/09/2026, kullanıcı kararı: "tek bir kere eksik yoktur denmesi yeterli olsun" — eski 2/2 kuralı kaldırıldı).** Devir için **bir kez** "ciddi eksik YOK" yeter (`✅ temiz`). ⚠️ Bu, kanıt bloğunu **gevşetmez, tersine tek güvence hâline getirir**: ikinci geçiş yokken kanıtsız "temiz" hiçbir yerde yakalanmaz, o yüzden `Doğrulama` satırı koşulan komutu/okunan aralığı taşımak **zorundadır** ve doğrulanamayan şey "tamam" sayılmaz. "VAR" çıkarsa geri gönderilir; düzeltme gelince bulguyu ortaya çıkaran **aynı doğrulama tekrar koşulur** (bu ikinci geçiş değil, kapanış kanıtıdır). **Tavan: aynı iş en çok 2 kez geri gönderilir (3 geçiş)**, ulaşılamazsa durulur ve kullanıcıya **bildirilir — soru değil, durum raporu**; kapanmamış bulgular **açık bulgu** olarak tek tek listelenir. Gerekçe: 14 rollü bir turda ikinci geçiş tahmini maliyetin ~%22'siydi. "Ciddi eksik" = davranışı/güvenliği/geriye uyumluluğu/veriyi etkileyen ya da istenen bir maddeyi karşılıksız bırakan şey; kozmetik ve bilerek kapsam dışı olanlar bloklamaz.
    - **Bulgu kapanmadan devir yok — denetçi düzelttirir.** Geri gönderme not değil **iş emridir**. Denetçi düzeltmez ama takip eder ve kapanışı **kanıtlar**: düzeltme gelince bulguyu ortaya çıkaran **aynı doğrulama tekrar koşulur**, sonucu yazılır ("düzeltildi" beyanı kapanış değildir). Bir bulgu ancak (a) düzeltilip kanıtlanarak, (b) kullanıcı açıkça "yapma" diyerek, (c) kapsam dışı gerekçesiyle **açık bulgu olarak raporlanarak** kapanır — sessizce düşen bulgu yoktur. Kozmetik bulgular devri bloklamaz ama yine düzelttirilir ya da açık bulgu diye listelenir. Tur sonu raporunda **kapanan / açık kalan** ayrımı görünür.
    - **Maliyet tablosu ölçülerek düzeltilir.** `rol-secimi.md` §8'deki model kırılımı **tahmindir** (ölçülen tek sayı: tur başına $6,9). Her gerçek ajan turunda bildirimdeki `subagent_tokens` × model fiyatı hesaplanır, alt-üst sınır olarak §8'deki **ölçüm defterine** yazılır. Tablo **tek ölçümle değiştirilmez** — en az 3 kayıt ya da gerçek bir uçtan uca C/D turu gerekir.
    - **Üç denetim boşluğu kapatıldı:** `analiz` bulgusunu üreten **komutu** da döndürür (yoksa bulgu "doğrulanmadı" sayılır) · `devops` çıktısı **`qa`'ya girer** ("config, kod değil" atlama gerekçesi değildir) · `urun-yoneticisi` çıktısı zincire otomatik akmaz, **kullanıcı onayına** gider.
    **Why:** Dokuz rol ajanından yalnız `gelistirici` gerçek anlamda denetleniyordu (`qa` → ben). `analiz` yanlış sayarsa, `devops` kapıyı bozarsa, `urun-yoneticisi` kapsamı kaçırırsa hata sessizce aşağı akıyordu; `qa`'ya ikinci denetçi ajan eklemek ise subagent token'ı ~4x pahalı olduğu için karşılığını vermiyordu. **How to apply:** Ayrıntı ve rakamlar `~/.claude/modes/rol-secimi.md` §2a, §3, §5, §6, §7, §8'de. Mod A'da ajan yoktur; eksik kontrolü orada #24 ile aynı işi görür.

## §29 — Test kapsamı her kod tabanında EN AZ %80 (satır) — istisnasız (13/09/2026, kulla

    - **Payda dürüst olur:** yalnız **üretilmiş** kod çıkarılır (EF göçleri + `ModelSnapshot`, `obj/`, `*.g.cs`, `*.Designer.cs`, `.d.ts`, testlerin kendisi, e2e/konfig dosyaları). Çıkarma listesi projede **tek yerde ve gerekçeli** durur. El yazısı ürün kodunu (test etmesi zor gateway istemcisi, `Program.cs`) listeden çıkarmak eşiği gevşetmektir → **yasak**. Rapor her zaman dürüst sayıyı verir; ham sayı yanıltır (Proje B, 12/09/2026: göçler dahil %95,0 — gerçekte %83,0).
    - **Gevşetme yok:** eşik projede düşürülmez, istisna verilmez, "sonra yazarız" notuyla promosyon yapılmaz. **Proje `CLAUDE.md`'si bu maddeyi EZEMEZ** — "proje kuralı genel kuralı ezer" ilkesinin tek istisnası budur.
    - **Uyum — tez zamanda:** Bir projede açılan **ilk oturum**, kod işine başlamadan önce her kod tabanının kapsamını **ölçer**, kapı yoksa **kurar**, eşik altındaysa açığı kod tabanı bazında raporlar ve kapatma planını kullanıcıya sunar. Kullanıcı başka öncelik söylemedikçe bu plan yeni özellik işinin önüne geçer. Açık kapanana kadar o proje `test`/`prod`'a promosyon yapamaz.
    **Why:** Kullanıcı düşük kapsamla dış dünyaya çıkılmasını kesin olarak yasakladı. Ölçüm bunun gerekçesini gösterdi: Proje B frontend'inde 136 dosyanın 107'sine hiçbir test dokunmuyordu, ama pano ve raporlarda bu görünmüyordu. **How to apply:** Kapsam kapısı yoksa promosyon yok. Kurarken payda listesini üretilmiş kodla sınırla ve mutasyonla doğrula: kapsamlı bir dosyadaki testi kaldırınca kapı kırmızıya dönüyor mu? Ayrıntı ve yığın başına komutlar: `standards/10-test-stratejisi.md` §7.

## §30 — Test verisindeki e-posta GERÇEK kutuya gider: `<hesap>+<değişken>@gmail.com` (14

    - **Kapsam:** sistemin ileti gönderebileceği HER test adresi — e2e (web ve mobil), test ortamındaki seed/e2e hesapları, entegrasyon ortamına elle girilen veri, davet/link alıcıları. `<değişken>` kaydı ayıran etikettir (`musteri-<zaman>-<rastgele>`); Gmail artı adreslemesi hepsini tek kutuya düşürür.
    - **Yasak:** sahte alan adı — `.test`, `.local`, `example.com`, `ornek.*`. Gerçek SMTP'ye bağlı ortamda geri dönen her ileti gönderim hatası üretiyor ve gerçek bir e-posta arızasını o gürültünün içinde saklıyor.
    - **Kapsam dışı:** göndericisi sahtelenen (fake/mock sender) birim ve entegrasyon testleri — ileti süreçten hiç çıkmıyor.
    **Why:** Proje B test ortamı (14/09/2026): e2e'nin `@ornek-<proje>.test` adreslerine giden davet ve link iletileri sürekli gönderim hatası veriyordu. **How to apply:** ilk e2e/seed yazılırken yardımcıyı kur; var olan projede sahte alan adlarını tara (`grep -rE '@[a-z0-9.-]+\.(test|local)\b|example\.com'`) ve yardımcıya çevir. Ayrıntı: `standards/11-playwright.md` §4.

## §31 — E2E koşum döngüsü: tam koş → düşenleri belirle → düzelt → yalnız düzeltilenleri 

    - **Önce paketin TAMAMI koşar**, ilk hatada durulmaz. Düşenler tek listede toplanır ve her biri **sınıflandırılır:** ürün hatası · bayat spec · veri/fixture · ortam (istek sınırı, zaman aşımı, deploy, oturum süresi).
    - ⚠️ **E2E yalnız `test` ortamına çıkmış kodla koşar (14/09/2026, kullanıcı: "e2e leri teste geçince koşacağız").** Düzeltme `dev`'deyken doğrulama **unit test + tsc/lint**'tir (#25); düzeltilen testlerin hedefli koşumu ve tam tekrar, düzeltme `test`'e çıkıp deploy olduktan sonra yapılır. `dev` kodunu test ortamına karşı koşmak da e2e koşmaktır.
    - **Hepsi geçerse tam paketi yeniden koşup koşmamaya ben karar veririm** ve gerekçesini raporlarım. Tam koşum tekrarlanır: düzeltme paylaşılan bir parçaya dokunduysa (layout, auth, ortak bileşen, fixture, config) · promosyon kaydı geçerli bir tam koşum istiyorsa · ilk koşumdaki düşüşlerin bir kısmı ortam kaynaklıysa. Düzeltme tek spec'e ya da tek ekrana sınırlıysa hedefli koşum yeter.
    **Why:** Proje A 13-14/09/2026 — 8 worker'lık koşum API istek sınırına takıldı (48 sahte düşüş), sınıflandırmadan tekrar koşmak zaman kaybettirdi. **How to apply:** ayrıntı `standards/11-playwright.md` §9.

## §32 — Sıra: önce TÜM kod → sonra unit testleri yazılır → unit testler koşulur; E2E ise

    - **E2E `dev` aşamasında ne yazılır ne koşulur.** ⚠️ #33 bunu değiştirdi: e2e yazımı/koşumu artık `prod` öncesi kapıdadır; `dev`/`test` promosyonunda yalnız "yazıldı mı" kontrolü yapılır.
    **Why:** kullanıcı: "önce tüm kodları yaz sonra unit test yaz ve unit test koş, e2e teste çıkınca yazılır ve koşulur" — ara koşumlar zaman ve makine yükü tüketiyordu. **How to apply:** kod yazarken koşum başlatma; tsc/lint dahil doğrulamaları kod + test yazımı bittikten sonra toplu yap.

## §33 — E2E zamanlaması: `dev`/`test`'te yalnız "yazıldı mı" kontrolü, koşum ve yazım `p

    - **İstisna yalnız hotfix:** kullanıcı açıkça "hotfix" derse e2e koşulmadan çıkılır, rapora "e2e atlandı (hotfix)" yazılır.
    - **Why:** kullanıcı: e2e'yi `prod` öncesine al; `dev`/`test`'te yalnız yazıldı mı bak, koşum olmasın. `test` promosyonundaki koşum deploy ve artifact kotası gibi dış bağımlılıklarda takılıyordu (Proje A 19/09/2026: kota dolunca deploy-durum dosyası okunamadı, kapı e2e'yi hiç başlatamadı). **How to apply:** projenin merge betiği bu kuralla çelişen bir e2e adımı koşuyorsa (ör. `dev → test`'te seçimli e2e) bunu raporla ve betiği bu kurala göre güncellemeyi öner; betik güncellenene kadar kullanıcıya "kapı e2e koşacak" diye önceden söyle.

## Yapma listesi

- ❌ Test verisinde sahte alan adlı e-posta (`.test` / `.local` / `example.com`) ya da spec'e elle yazılmış adres — gerçek kutu `<hesap>+<değişken>@gmail.com`, tek yardımcıdan → #30
- ❌ Düşen e2e'leri sınıflandırmadan tekrar koşmak; ortam sınırına takılmış koşumu ürün sonucu saymak; düzeltmeden sonra tam koşum kararını gerekçesiz vermek → #31
- ❌ `test`'e geçmeden e2e koşmak — `dev`'deki düzeltmenin hedefli e2e koşumu dahil; `dev`'de doğrulama unit test + tsc/lint → #31
- ❌ `dev`/`test` promosyonunda e2e koşmak ya da e2e için deploy/durum dosyası beklemek; `prod` öncesi kapıda "kod test'te mi / eksik e2e var mı / bu kodla koşuldu mu" kontrolünü atlamak → #33
- ❌ E2E koşmadan `prod`'a çıkmak — yalnız kullanıcının açıkça "hotfix" dediği iş e2e'siz çıkar → #31
- ❌ Kod yazımı bitmeden, her küçük değişiklikten sonra test/koşum başlatmak; `test`'e çıkmadan e2e spec'i yazmak ya da koşmak — önce tüm kod, sonra unit test yaz + koş, e2e teste çıkınca → #32
- ❌ Kullanıcıya sormadan otonom arka plan ajanı/döngü başlatmak → #20
- ❌ `test-writer` ve `migration-reviewer` subagent'larını çağırmak — kesin yasak (2026-08-13). ⚠️ Yasak **ada** bağlıdır ve o adlar bugün diskte yok; asıl koruma **mod setidir**: modun 9 rolü dışında hiçbir ajan (21 etkin eklenti ajanı dahil) çağrılmaz → #27, #28
- ❌ Mod A'da ajan başlatmak; B/C/D/E'de modun seti dışında ajan çağırmak. ⚠️ Mod dosyası yokken artık **B** geçerlidir (18/09/2026) — B'nin üç ajanı serbesttir, dördüncüsü değil → #27
- ❌ Tur sonunda ajan sayısını ve tahmini maliyeti raporlamadan geçmek (B/C/D/E) → #27
- ❌ `dev`'e merge'i review/tarama kapılarıyla yavaşlatmak → #25 (ama `test`/`prod` promosyonunda kapıyı atlamak da yasak)
- ❌ `dev`'in ÜZERİNDE doğrudan çalışmak/commit'lemek, ya da birden çok işi tek merge'de `dev`'e atmak → #26
- ❌ Kullanıcı söylemeden `test`/`prod`'a merge etmek → #26
- ❌ Denetçi rolün raporunu **eksik kontrolü bloğu olmadan** kabul etmek, ya da o bloğu kullanıcıya geçirmeden yutmak → #28
- ❌ Kanıt bloğu olmadan ya da kanıtsız "temiz" diyerek devretmek — tek geçiş kaldığı için blok tek güvencedir → #28
- ❌ Denetçinin "eksik var mı, tamam mı?" diye kullanıcıya/üreten role sorması; bulduğu eksiği geri göndermek yerine yukarı taşıması → #28
- ❌ Mod A'da **takım açmak** — `TeamCreate` de ajan çağrısıdır; araç prompt'unun "şüphedeysen takım aç" telkinine A'da uyulmaz. B/C/D/E'de de takım yalnız X/Y/Z seçilmişse açılır → #27
- ❌ B/C/D/E **ve X/Y/Z**'de modun seti dışında ajan/teammate çağırmak; E ve Z'de `Workflow` script'ine modun rol seti dışında ajan (eklenti ajanları dahil) koydurmak → #27, #28
- ❌ Bulguyu rapora yazıp düzelttirmeden devretmek; "düzeltildi" beyanını doğrulama tekrar koşulmadan kapanış saymak; bir bulgunun sessizce düşmesi → #28
- ❌ `urun-yoneticisi` çıktısını kullanıcı onayı almadan zincire akıtmak → #28
- ❌ Maliyeti yalnız tur sonunda söylemek; devir satırlarını atlamak → #28
- ❌ `analiz` bulgusunu doğrulama komutu olmadan kesinmiş gibi kullanmak → #28
- ❌ `devops` çıktısını "config, kod değil" diye review'sız geçirmek → #28
- ❌ Satır kapsamı %80'in altında (ya da ölçülmemiş) bir kod tabanını `test`/`prod`'a çıkarmak; eşiği, çıkarma listesini ya da kapıyı gevşetmek; kapsam için assert'sız test yazmak → #29

## Görev → hangi standardı oku

## Görev → hangi standardı oku
| Görev | Oku |
| Yeni özellik / kapsam / kabul kriteri | `standards/01-urun-tasarimi.md` |
| Ekran, bileşen, stil, erişilebilirlik | `standards/02-ui-ux.md` |
| Genel kod yazımı, isimlendirme, hata yönetimi | `standards/03-kodlama-genel.md` |
| .NET endpoint, servis, EF Core, DI | `standards/04-dotnet.md` |
| React sayfa/bileşen/state/veri çekme | `standards/05-react.md` |
| React Native / Expo ekran, store yayını | `standards/06-mobil.md` |
| Endpoint sözleşmesi, hata formatı, sayfalama | `standards/07-api-tasarimi.md` |
| Şema, migration, index, transaction | `standards/09-veritabani.md` |
| Web e2e | `standards/11-playwright.md` |
| Mobil e2e | `standards/12-maestro.md` |
| CI/CD, branch, ortam, deploy, yedek | `standards/14-devops.md` |
| Auth, OWASP, sır yönetimi, KVKK | `standards/15-guvenlik.md` |
| Yavaşlık, cache, bundle, Core Web Vitals | `standards/16-performans.md` |
| Log, metrik, trace, alarm, incident | `standards/17-gozlemlenebilirlik.md` |
| **Kurulum, ön koşullar, sır/token envanteri, `.env`** | `standards/18-kurulum-ve-ortam.md` |
| **Cloudflare: DNS, TLS, WAF, cache, Tunnel, Workers, R2** | `standards/19-cloudflare-ve-edge.md` |
| **Sunucu/uygulama sertleştirme, güvenlik başlıkları, IIS/Docker** | `standards/20-sertlestirme.md` |
| **Yedekleme, restore provası, RPO/RTO, felaket kurtarma** | `standards/21-yedekleme-ve-kurtarma.md` |
Şablonlar: `standards/sablonlar/` — proje CLAUDE.md, **SETUP.md**, PR, ADR, user story.

## Çalışma düzeni (Claude için)

- **Bağlamı önce topla.** Dosyayı düzenlemeden önce oku; projenin kendi `CLAUDE.md`'sini ve varsa `docs/`'unu tara. Varsayımla kod yazma.
- **Plan → onay → uygula.** Birden fazla dosyaya dokunacak işte önce kısa plan (hangi dosya, ne değişecek, neden) sun.
- **Yaptığını doğrula.** Build + ilgili testler + lint/format. Çalıştırmadıysan "çalıştırmadım" de.
- **Belirsizlikte:** bağımsız işleri bitir, sonra tek net soru sor. Her varsayımda durup sorma; ama yanlış varsayım işi çöpe atacaksa sor.
- **Paralel oturum farkındalığı.** Aynı repoda başka oturumlar çalışıyor olabilir: yalnız kendi diff'ini commit et, commit öncesi `git status`/`git diff`'i doğrula, `--force` kullanma.

## Uzun kapı/koşum sırasında CANLI PANO (KALICI, tüm projeler)

### Panoda bulunması ZORUNLU olanlar

## 1. **Ağırlıklı genel yüzde.** İşleri maddelere böl, her maddeye kalan *emeğe*

1. **Ağırlıklı genel yüzde.** İşleri maddelere böl, her maddeye kalan *emeğe*
   göre ağırlık ver (toplam 100), tamamlananların ağırlığını topla. Ağırlıksız
   "5/10 madde bitti" yanıltıcıdır — 473 commit'lik bir review ile bir config
   satırı aynı şey değildir.

## 2. **Madde kırılımları.** Koşan maddenin alt adımları tek tek görünmeli; yüzde

2. **Madde kırılımları.** Koşan maddenin alt adımları tek tek görünmeli; yüzde
   kırılımdan hesaplanır, tahminden değil.

## 3. **Canlı ölçüm.** Son ölçümün saati, ölçülen ham veri (süreçler, bellek, SHA,

3. **Canlı ölçüm.** Son ölçümün saati, ölçülen ham veri (süreçler, bellek, SHA,
   dosya damgaları) ve o ölçümün hangi aşamaya karşılık geldiği.

## 4. **Açık riskler/engeller.** Karar bekleyen veya sonraki maddeyi bloklayan her

4. **Açık riskler/engeller.** Karar bekleyen veya sonraki maddeyi bloklayan her
   kalem, gerekçesiyle.
### Kalıcı kurallar
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

## Ek — aktif dosyada kısaltılarak yeniden yazılan satırların özgün hâli

### Global Çalışma Kuralları

> Proje-özel kurallar projenin kendi `CLAUDE.md`'sindedir ve **buradaki kuralı ezer**.

### §17 — Tek origin tercih edilir. API, UI'ın alan adının altında yayınlanır (`app.exampl

17. **Tek origin tercih edilir.** API, UI'ın alan adının **altında** yayınlanır (`app.example.com/api/*`), ayrı `api.` alt alan adı istisnadır (ADR gerektirir). Kazanç: CORS yok, httpOnly+SameSite cookie çalışır, tek sertifika/DNS/WAF, backend topolojisi gizli, web+mobil tek base URL. SPA fallback `/api/*`'ı **kapsamaz**.

### §19 — Güvenlik taraması otomatiktir. Her push'ta sır taraması + bağımlılık CVE; PR'da 

19. **Güvenlik taraması otomatiktir.** Her push'ta sır taraması + bağımlılık CVE; PR'da SAST; test deploy'u sonrası **OWASP ZAP** baseline. Sürüm öncesi **OWASP Top 10 eşleme tablosu** gözden geçirilir (`standards/15-guvenlik.md` §12). Kritik/yüksek bulgu merge'i bloke eder. **SAST ve SIR TARAMASI her projede birer adımdır ve yerelde de koşar** (`scripts/codeql-scan.sh`, `gitleaks detect`); CI aynı betiği ve aynı eşiği kullanır — iki yerde iki farklı kural olmaz. Hattın bütün kapılarını yerelde koşan bir betik bulunur (`scripts/ci-local.sh`): CI kesildiğinde doğrulama durmaz. **Koşmayan kapı geçilmiş sayılmaz** — "atlandı" diye raporlanır ve sonuç yeşil olmaz. Yanlış pozitif yalnız **gerekçeli** triyajla bastırılır, kural kapatılmaz; sır taramasında izin **yola değil değere** verilir ve darlığı mutasyonla doğrulanır. → `standards/15-guvenlik.md` §13a-13c

### §20 — Otonom arka plan ajanı sormadan başlatılmaz. `/loop` otonom mod, `ScheduleWakeup

20. **Otonom arka plan ajanı sormadan başlatılmaz.** `/loop` otonom mod, `ScheduleWakeup` ile kendini yeniden tetikleyen döngü, cron/schedule tabanlı ajan gibi kullanıcı müdahalesi olmadan tur tur çalışmaya devam eden hiçbir iş **önceden açık onay alınmadan** kurulmaz. Böyle bir iş zaten çalışıyorsa (kendi başlattığım veya başka bir oturumda bulduğum), kullanıcıya **proaktif haber ver**: ne yaptığı, hangi kararı/onayı beklediği, token/kaynak tükettiği, nasıl durdurulacağı. Sessizce arka planda bırakma.
    - ⚠️ **ONAY VERİLDİ (05/09/2026), ama KOŞULLU:** kullanıcı uzun işin bırakılıp bitene kadar koşmasını ve soru çıkarsa kendisine ulaşılmasını istedi. Koşullar ve durma kuralları `~/.claude/modes/otonom-kosum.md`'de — iş listesi, bitiş tanımı, **$100** bütçe tavanı, tıkanma freni, geri alınamaz eylemde DURMA. Koşullardan biri yoksa koşum başlatılmaz ve bu madde yeniden yürürlüktedir.

### §24 — "Tamamlandı" demeden önce kendi kendine eksik-kontrolü zorunlu (2026-08-25, kull

24. **"Tamamlandı" demeden önce kendi kendine eksik-kontrolü zorunlu (2026-08-25, kullanıcı kararı, tüm projeler için geçerli).** Bir görevi "yapıldı / tamamlandı / bitti" diye raporlamadan **hemen önce**, aynı turda, kullanıcı sormadan şu kontrol listesini kendi kendime uygularım ve sonucunu göz önünde bulundururum:
    - Kullanıcının **orijinal isteğini** yeniden oku (özetlenmiş/kısaltılmış hatırlamaya güvenme) ve istekte geçen her maddenin karşılandığını tek tek doğrula.
    - **Kenar durumlar / hata yolları** düşünüldü mü? (boş liste, null, yetkisiz erişim, eşzamanlılık, geriye uyumluluk — ilgili standart bu görevi kapsıyorsa.)
    - Görev birden fazla dosyayı/katmanı etkiliyorsa (API + istemci, migration + kod, i18n `tr`+`en`) **hepsi** değişti mi, yoksa biri unutuldu mu?
    - Bilinen ama bilerek ertelenen bir eksik varsa (kapsam dışı bırakıldı, zaman kısıtı vb.) **sonuç raporunda açıkça listele** — sessizce atlama.

### §25 — `dev`'e merge hızlıdır: review ve ağır kapılar yalnız `test` ve `prod` promosyon

25. **`dev`'e merge hızlıdır: review ve ağır kapılar yalnız `test` ve `prod` promosyonlarında koşar (2026-08-30, kullanıcı kararı, tüm projeler için geçerli).**
    - **`feature/* → dev`:** kod review **yapılmaz** (ne benim elle diff okumam, ne ajan), SAST/CodeQL, sır taraması (CI işi), bağımlılık CVE, ZAP, geriye uyumluluk taraması, kapsam eşiği (#29), e2e **koşmaz**. Tek istisna **pre-commit gitleaks** kancasıdır — yereldedir, saniye sürer ve sızan sır geri alınamaz (rotate gerektirir), o yüzden `dev`'de de açık kalır. ⚠️ **Mod D/E'de bu kısıt AJANLARA da uygulanır (18/09/2026):** kapı-eşli roller `guvenlik` ve `kapsam-denetcisi` `dev` yönünde çağrılmaz, yalnız promosyonda koşar — aksi hâlde kapı yasağı ajan eliyle geri gelirdi. `veri` bu kuralın dışındadır ve tersi geçerlidir: şemaya dokunan iş `dev`'e merge edilmeden ÖNCE `veri`'den geçer, çünkü migration geri alınamaz. Sadece **build + hızlı unit test + lint/format** koşar (saniyeler sürer, bozuk `dev` maliyeti daha yüksektir). Bunlar kırmızıysa merge edilmez ve #15 gereği çıktısıyla raporlanır.
    - **`dev → test` ve `test → prod`:** tüm kapılar **tam** koşar — `standards/13-pr-ve-review.md` §4 merge kapısı, review checklist §5, #19'daki güvenlik taramaları, e2e. Burada hiçbir şey atlanmaz; promosyon zaten kullanıcı onayıyla yapılır.

### §26 — Verilen iş planlandıktan sonra: `dev`'i pull et → `dev`'den dal/worktree aç → or

26. **Verilen iş planlandıktan sonra: `dev`'i pull et → `dev`'den dal/worktree aç → orada çalış → her işi AYRI AYRI `dev`'e merge et (2026-09-02, kullanıcı kararı, tüm projeler için geçerli).** Sıra bağlayıcıdır:
    3. **Her iş bitince o işi tek başına `dev`'e merge et.** Birden çok işi tek commit/merge'de toplama — her iş kendi commit'i, kendi doğrulaması, kendi merge'iyle gider.
    - ⚠️ **`~/.claude` deposunun kendi düzeni (08/09/2026):** `dev` = çalışma dalı, `master` = yayın. Bu depoda iş `dev`'e commit'lenir; `master`'a promosyonu **kullanıcı söyler**. Uzak: `<kullanıcı>/<yapılandırma-deposu>`. Depo **paylaşımlı bir çalışma ağacıdır** — paralel oturumlar aynı dizinde çalışır, o yüzden dal değiştirmeden önce `git status` doğrulanır ve yalnız kendi diff'in commit'lenir.

### §27 — Çalışma modu (A/B/C/D) her projede seçilebilir; seçim ONAYDIR (2026-09-05, kulla

27. **Çalışma modu (A/B/C/D) her projede seçilebilir; seçim ONAYDIR (2026-09-05, kullanıcı kararı).** Mod, ajan kullanımını + review'ı + onay politikasını birlikte belirler. Tek kaynak `~/.claude/modes/README.md`; seçim projenin `.claude/mode` dosyasında (**yoksa B — 18/09/2026 kullanıcı kararı; öncesinde A idi**). Değiştirme: `/calisma-modu <harf>`.
    - ⚠️ **A'da ajan çağrılmaz; B/C/D/E'de modu seçmek onaydır** — çağrı öncesi ayrıca sorulmaz, tur sonunda ajan sayısı + tahmini maliyet **raporlanır**. **C/D/E'de review iki katmanlı:** ilk geçişi `qa` ajanı yapar, kritik bulguları ben doğrularım. Eski #21/#23 bu maddeye devredildi; **eski E (Eski usul) 05/09/2026'da kaldırıldı** — A ile aynı işti; E harfi 18/09/2026'da fan-out'a verildi.

### §28 — Denetçi her geçişte eksik/yanlış KONTROL EDER, GERİ GÖNDERİR ve DÜZELTTİRİR; mal

28. **Denetçi her geçişte eksik/yanlış KONTROL EDER, GERİ GÖNDERİR ve DÜZELTTİRİR; maliyet her devirde hatırlatılır (2026-09-07, kullanıcı kararı, tüm projeler için geçerli).** Ajan kullanılan her turda:
    - **Eksik kontrolü bloğu zorunlu.** Çıktısına başkasının güveneceği her rol (`qa`, `analiz`, `devops`, `test-yazar`, `urun-yoneticisi`) ve **her devirde orkestratör**, raporunu **kanıt bloğuyla** kapatır: *Doğrulama (koşulan komut/okunan aralık) · Madde eşlemesi (istenen her madde → dosya:satır) · Kapsanmayan → Sonuç: ciddi eksik YOK | VAR.* Blok temiz geçilse bile yazılır — görünmeyen kontrol yapılmamış kontroldür. ⚠️ **Bu bir soru değil, kontroldür:** denetçi "eksik var mı?" diye kullanıcıya da üreten role de **sormaz**; bakar, kanıtı yazar, kararı kendi verir. **Doğrulanamayan şey "tamam" sayılmaz.**
    - **Eksik varsa GERİ GÖNDERİLİR, kullanıcıya taşınmaz.** İş devretmez, üretene döner (`qa` → `gelistirici`/ben → yeniden `qa`); geri gönderme **ne eksik · hangi kanıtla · ne yapılacak** taşır ve kontrol baştan başlar. Kullanıcıya gitmesi yalnız §5 durma sebeplerinde ve tavanda olur — o da **soru değil, durum raporu**.
    - **Maliyet tur sonuna ertelenmez.** Her rol devrinde tek satır: o rolün tahmini maliyeti + turun kümülatifi + eşiğe uzaklık (`↳ analiz bitti · ~$3 · tur toplamı ~$9 (2 ajan) · eşik ~$150 (C)`). Eşik **moda bağlı ve iki kademeli** (08/09/2026): B ~$12/**$25** · C ~$75/**$150** · D ~$130/**$260** · E ~$200/**$400** — yarısında uyarı satırı, tamamında **durma**. Otonom koşumun $100 tavanı bağımsızdır; hangisi önce dolarsa o durdurur.

### §29 — Test kapsamı her kod tabanında EN AZ %80 (satır) — istisnasız (13/09/2026, kulla

29. **Test kapsamı her kod tabanında EN AZ %80 (satır) — istisnasız (13/09/2026, kullanıcı kararı: "irademdir", tüm projeler için).**
    - **Ölçü:** satır kapsamı, **her kod tabanı AYRI** — backend · web · mobil Android · mobil iOS. Ortalama alınmaz: %95'lik backend %14'lük frontend'i örtemez. Ölçülmemiş kod tabanı "geçti" sayılmaz, **"ölçülmedi"** diye raporlanır ve promosyonu yine bloklar (#19).
    - **Kapı:** projenin yerel kapı betiğinde (`scripts/ci-local.sh` ya da eşdeğeri) **promosyon modunda** koşan adım; eşik altı → çıkış kodu ≠ 0. #25 gereği **`dev → test` ve `test → prod` promosyonunu BLOKLAR**; `dev` merge'i hızlı kalır. CI aynı betiği ve aynı eşiği kullanır.
    - **Sahte kapsam yasak:** E2E bu sayıya girmez (ayrı ölçü). Kapsamı artırmak için assert'sız ya da hiçbir şey yakalamayan test yazmak eşiği gevşetmekle aynıdır — eklenen test mutasyonla bir hatayı yakalamalı (`standards/10-test-stratejisi.md` §7).

### §30 — Test verisindeki e-posta GERÇEK kutuya gider: `<hesap>+<değişken>@gmail.com` (14

30. **Test verisindeki e-posta GERÇEK kutuya gider: `<hesap>+<değişken>@gmail.com` (14/09/2026, kullanıcı kararı, tüm projeler için).**

### §31 — E2E koşum döngüsü: tam koş → düşenleri belirle → düzelt → yalnız düzeltilenleri 

31. **E2E koşum döngüsü: tam koş → düşenleri belirle → düzelt → yalnız düzeltilenleri koş → tam tekrarına ben karar veririm (14/09/2026, kullanıcı kararı, tüm projeler için).**
    - **Sonra YALNIZ düzeltilen testler** (ve o düzeltmenin etkileyebileceği testler) koşar.
    - ⛔ **E2E koşmadan `prod`'a çıkılmaz (14/09/2026, kullanıcı kararı).** `test → prod` promosyonu, `test`'e çıkmış kodun geçerli e2e kaydını ister. **Tek istisna hotfix'tir:** kullanıcı açıkça "hotfix" dediğinde e2e koşulmadan çıkılır ve bu, raporda "e2e atlandı (hotfix)" diye yazılır — geçti sayılmaz.
    - **Ortamın sınırına takılan koşum geçersizdir** (ör. paralel koşum istek sınırını aştı); sonucu ürün hatası diye okunmaz, paralellik düşürülüp tekrarlanır.

### §32 — Sıra: önce TÜM kod → sonra unit testleri yazılır → unit testler koşulur; E2E ise

32. **Sıra: önce TÜM kod → sonra unit testleri yazılır → unit testler koşulur; E2E ise `test`'e çıkınca YAZILIR ve koşulur (14/09/2026, kullanıcı kararı, tüm projeler için).**
    - #26 geçerli kalır: her iş kendi dalında yazılır ve unit koşumu yeşil olunca **ayrı ayrı** `dev`'e merge edilir.

### §33 — E2E zamanlaması: `dev`/`test`'te yalnız "yazıldı mı" kontrolü, koşum ve yazım `p

33. **E2E zamanlaması: `dev`/`test`'te yalnız "yazıldı mı" kontrolü, koşum ve yazım `prod` ÖNCESİ kapıda (20/09/2026, kullanıcı kararı, tüm projeler için; #31 ve #32'nin e2e zamanlamasını EZER).**
    - **`feature → dev` ve `dev → test`:** e2e **koşmaz**. Yalnız **kontrol**: değişen davranış için e2e spec'i yazılmış mı (spec dosyası var mı, değişen akışı kapsıyor mu, projede harita/eşleme varsa ona girmiş mi)? Eksikse merge'i **bloklamaz**; eksik listesi rapora yazılır ve `prod` öncesine devredilir. Koşum, deploy bekleme, durum dosyası okuma yoktur.
      1. **Kod `test`'e çıkmış mı?** `prod`'a gidecek kod `test`'te değilse önce `test`'e çıkılır (#26/#25 kuralları, kullanıcı onayıyla) ve deploy olması beklenir. `prod`, `test`'te olmayan kodu taşımaz.
      2. **Eksik e2e var mı?** Değişen davranışlar spec'lerle karşılaştırılır; eksik liste çıkarılır.
      4. **Bu kodla e2e koşulmadı mı?** `test`'te deploy olan SHA için geçerli tam koşum kaydı yoksa koşulur (#31 döngüsü: tam koş → sınıflandır → düzelt → hedefli tekrar).

### Görev → hangi standardı oku

| Alan/endpoint değiştirme, deprecation | `standards/08-geriye-uyumluluk.md` |
| Unit/integration test yazımı | `standards/10-test-stratejisi.md` |
| Commit, PR, code review | `standards/13-pr-ve-review.md` |

### Çalışma düzeni (Claude için)

- **Geri alınamaz işlerde onay al.** Deploy, migration `DROP`, dış dünyaya gönderim, dosya silme.
- Detay: `standards/00-calisma-duzeni.md`

### Uzun kapı/koşum sırasında CANLI PANO (KALICI, tüm projeler)

Dakikalarca süren bir kapı, koşum veya deploy başlattığında (merge kapısı, CI,
test bataryası, publish/deploy zinciri, migration) **bir Artifact panosu yayınla
panonun yerine geçmez; ikisini birlikte ver.

### 4. **Açık riskler/engeller.** Karar bekleyen veya sonraki maddeyi bloklayan her

- ⚠️ **Yüzde ÖLÇÜLÜR, uydurulmaz.** Hangi sinyalden okuduğunu panoda yaz


## 20/09/2026 — token sadeleştirme turu (madde 1-5, kullanıcı onayıyla)

Kullanıcı: "kullandığımız çalışma modu yapısı ve sdlc akışında, gereksiz token
harcayan yerler var mı kontrol et, raporla" + "olmasa da olacak ya da gereksiz
yere sürekli tekrarlanan ama en sonda bir kere koşsa olacak adımlar var mı" →
ardından "1 ve 2'yi uygula", sonra "3, 4 ve 5'i de uygula".

**Ölçüm (son 30 gün, 333 oturum / 103.307 istek, liste fiyatı ~$23.500):**
sabit önek medyanı 57.756 token, payı **%18 ≈ $4.289**; 24. haftadan 38. haftaya
27.700 → 63.500 token (2,3x). 397 subagent koşumunda medyan 52.313 token.
Ölçüm yöntemi ve tekrarı: `scripts/onek-olc.py`, `standards/00` §6b.

- **§21-23 (madde 3):** X/Y/Z takım modları `modes/arsiv/`'e alındı — bugün
  başlatılamıyorlar (rol allowlist'inde `SendMessage`/`Task*` yok + özellik
  bayrak/plan kapısının arkasında) ama ~16 KB kuralları her oturumda
  yükleniyordu. Geri getirme koşulu `modes/arsiv/README.md`'de.
- **§28 (madde 4):** 14 ajan dosyasındaki "Eksik kontrolü" metni birebir
  kopyaydı (toplam ~24 KB); tek sürüme indi, tam kural `rol-secimi.md` §7'de.
  Orkestratör artık her devirde tam blok yazmıyor — devirde kanıt taşıyan tek
  satır, tam blok turun sonunda bir kez ve her "VAR" kararında. Gerekçe: rolün
  bloğu kanıtı zaten taşıyor; orkestratörün kopyası aynı kanıtı tekrar ediyordu
  ve D/E'de bu 14 bloğa çıkıyordu.
- **§33 (madde 5a):** `dev`/`test` yönündeki "e2e yazıldı mı" kontrolü
  **kaldırıldı**. Hiçbir şeyi bloklamıyordu, çıkardığı eksik listesi `prod`
  kapısının 2. adımında **yeniden** hesaplanıyordu — iki kez üretilip bir kez
  kullanılan çıktı.
- **§25/§26 (madde 5b):** formatlayıcı/lint her `feature → dev` merge'inde değil,
  **iş listesinin sonunda bir kez** koşar. `dev` merge kapısı build + hızlı unit
  testtir; bozuk `dev` riski onunla kapanıyor, formatter çıktısı ise her işte
  yeniden okunuyordu. `standards/13` §4 kapsam notu da güncellendi.

⚠️ Bu turda CLAUDE.md boyut kapısı iki commit boyunca kırmızı kaldı (22.611 ve
22.556 bayt; tavan 22.528) ve üçüncü denemede yeşile döndü — kapının kendisi
çalıştı, ama "düzeltildi" denen commit ölçülmeden yazıldı. Ders: boyut kapısı
commit'ten ÖNCE koşulur.
