# Global Çalışma Kuralları

> Bu dosya **her projede, her oturumda ve her ajan turunda** bağlama girer —
> en pahalı talimat dosyası budur. Buraya yalnız **kuralın kendisi** yazılır;
> gerekçe/tarihçe/ölçüm `docs/kararlar.md`'ye taşınır (`standards/00` §6a).
> Boyut kapısı: `scripts/md-butce.tsv`. Detay standartlar `~/.claude/standards/`
> — eşleme: `standards/README.md` ya da `yazilim-standartlari` skill'i.
> Proje-özel kurallar projenin kendi `CLAUDE.md`'sindedir ve buradaki kuralı
> **ezer** — tek istisna #29.

## Dil

- **Konuşma, açıklama, commit mesajı, kod yorumu, doküman: Türkçe.**
- **Değişken / fonksiyon / sınıf / dosya / branch adları: İngilizce.**
- Kullanıcıya görünen metin ham string olmaz → i18n anahtarı (varsayılan `tr`, ikincil `en`).

## Varsayılan stack

.NET (Web API) + PostgreSQL/SQLite · React + Vite + TypeScript · React Native/Expo · Playwright (web e2e) · Maestro (mobil e2e) · GitHub Actions.

## Değişmez kurallar (her projede geçerli)

1. **Önce küçük adım.** Büyük refactor'dan önce küçük bir patch öner, onay bekle. Talep edilmemiş "yol üstü iyileştirme" yapma.
2. **Tek kaynak (single source of truth).** Hard-coded URL / IP / port / host / API anahtarı **yasak**. Her ayakta tek config modülü olur; diğer dosyalar `process.env` / `import.meta.env` / `IConfiguration`'ı doğrudan okumaz, o modülden named import yapar. Fallback yalnızca DEV içindir ve tek noktada tanımlanır.
3. **Sırlar repoya girmez.** Parola, token, connection string, sertifika → env / secret store. Repoda yalnız `.env.example`. Sır sızdıysa: önce rotate, sonra temizlik.
4. **Geriye uyumluluk zorunlu.** API ve DB **yalnız eklemeli (additive)** evrilir. Alan/endpoint silinmez, adı ve tipi değişmez; obsolete edilir ve dolu dönmeye devam eder. → `standards/08-geriye-uyumluluk.md`
5. **Tek API — web ve mobil aynı sözleşmeyi tüketir.** Platforma özel endpoint açılmaz; fark UI katmanında çözülür. İş mantığı **asla** istemcide durmaz. → `standards/07-api-tasarimi.md`
6. **Yetki fail-closed.** Varsayılan KAPALI. "Tanımlamayı unuttum = herkese açık" semantiği kurma. Her endpoint yetkiyi backend'de kontrol eder; UI'daki kontrol yalnız UX'tir.
7. **Validasyon iki yerde.** İstemcide UX için, API'de güvenlik için. İstemci validasyonu tek başına asla yeterli değildir.
8. **Test güncellenir.** Testi olan dosyaya dokunulduysa test güncellenir. Test yoksa **açıkça söyle**. Davranış değişikliği testsiz merge edilmez.
9. **300+ satırlık dosya bırakma.** Doğal sınırlarından (modal, liste renderer, form, alt-servis) böl. Bölme davranışı değiştirmez; ana dosya orkestratör kalır.
10. **Bağımlılık eklemeden önce sor.** Neden gerektiğini, alternatifini ve bakım maliyetini yaz, onay bekle.
11. **Magic string yok.** Sabit değerler enum/const. Enum switch'lerinde her zaman `default` dalı bulunur (ileri uyumluluk).
12. **Tarih formatı `dd/mm/yyyy`.** Locale-aware `toLocaleDateString`/`Intl` ve nokta ayraçlı format yasak. Taşıma/depolama her zaman UTC ISO-8601.
13. **Arama daima harf-boyutu ve aksan bağımsız.** "sisman" ↔ "Şişman", "istanbul" ↔ "İstanbul" eşleşir. Ham `.Contains` / `.ToLower().Contains()` / `LIKE` yasak; merkezi normalize fonksiyonu kullanılır.
14. **Yeni kural sözlü kalmaz.** Kalıcı bir karar alındıysa **aynı turda** ilgili `CLAUDE.md`'ye (proje) veya `~/.claude/standards/`'a (genel) yaz. Bu adımı atlamadan görevi bitirme.
15. **Doğruyu raporla.** Test kırmızıysa çıktısıyla birlikte söyle; atlanan adımı söyle. "Muhtemelen çalışır" diye tamamlandı deme.
16. **Kurulum belgelenir.** Her projede `SETUP.md` + `.env.example` + **sır/token envanteri** (ne, nereden alınır, nerede saklanır, sahibi, rotasyon) bulunur. Yeni araç/env/sır ekleyen değişiklik **aynı PR'da** bunları günceller. Temiz bir makinede belge takip edilerek tahmin yapmadan kurulabilmeli.
17. **Tek origin tercih edilir.** API, UI'ın alan adının **altında** yayınlanır (`app.example.com/api/*`), ayrı `api.` alt alan adı istisnadır (ADR gerektirir). SPA fallback `/api/*`'ı **kapsamaz**.
18. **Yedek denenmişse yedektir.** 3-2-1 kuralı (biri sunucu dışında), şifreli, **ayda 1 restore provası** ve provanın kaydı. Yedeğin başarısız olması **ve hiç çalışmaması** ayrı ayrı alarma bağlanır. Sadece DB değil: kullanıcı dosyaları, konfigürasyon, sertifikalar, sırlar da kapsamda. `DROP`/toplu güncelleme öncesi elle yedek.
19. **Güvenlik taraması otomatiktir.** Her push'ta sır taraması + bağımlılık CVE; PR'da SAST; test deploy'u sonrası **OWASP ZAP** baseline. Sürüm öncesi **OWASP Top 10 eşleme tablosu** gözden geçirilir (`standards/15-guvenlik.md` §12). Kritik/yüksek bulgu merge'i bloke eder. **SAST ve SIR TARAMASI her projede birer adımdır ve yerelde de koşar** (`scripts/codeql-scan.sh`, `gitleaks detect`); CI aynı betiği ve aynı eşiği kullanır — iki yerde iki farklı kural olmaz. Hattın bütün kapılarını yerelde koşan bir betik bulunur (`scripts/ci-local.sh`): CI kesildiğinde doğrulama durmaz. **Koşmayan kapı geçilmiş sayılmaz** — "atlandı" diye raporlanır ve sonuç yeşil olmaz. Yanlış pozitif yalnız **gerekçeli** triyajla bastırılır, kural kapatılmaz. → `standards/15-guvenlik.md` §13a-13c
20. **Otonom arka plan ajanı sormadan başlatılmaz.** `/loop` otonom mod, `ScheduleWakeup` ile kendini yeniden tetikleyen döngü, cron/schedule tabanlı ajan gibi kullanıcı müdahalesi olmadan tur tur çalışmaya devam eden hiçbir iş **önceden açık onay alınmadan** kurulmaz. Böyle bir iş zaten çalışıyorsa **proaktif haber ver**: ne yaptığı, neyi beklediği, ne tükettiği, nasıl durdurulacağı. Sessizce bırakma.
    - ⚠️ **ONAY VERİLDİ (05/09/2026), ama KOŞULLU.** Koşullar ve durma kuralları `~/.claude/modes/otonom-kosum.md`'de — iş listesi, bitiş tanımı, **$100** bütçe tavanı, tıkanma freni, geri alınamaz eylemde DURMA. Koşullardan biri yoksa koşum başlatılmaz ve bu madde yeniden yürürlüktedir.
21-23. **[#27'ye devredildi / kaldırıldı — 05/09/2026]** Numaralar atıflar kırılmasın diye korunuyor; eski hâlleri ve gerekçeleri `docs/kararlar.md` §21-23.
24. **"Tamamlandı" demeden önce kendi kendine eksik-kontrolü zorunlu (2026-08-25, kullanıcı kararı, tüm projeler için geçerli).** Bir görevi "yapıldı / tamamlandı / bitti" diye raporlamadan **hemen önce**, aynı turda, kullanıcı sormadan şu kontrol listesini kendi kendime uygularım:
    - Kullanıcının **orijinal isteğini** yeniden oku (özetlenmiş hatırlamaya güvenme) ve istekte geçen her maddenin karşılandığını tek tek doğrula.
    - **Kenar durumlar / hata yolları** düşünüldü mü? (boş liste, null, yetkisiz erişim, eşzamanlılık, geriye uyumluluk.)
    - **Test** (#8), **build/lint/format**, ve varsa **SETUP.md/.env.example/sır envanteri** (#16) güncellemesi gerçekten çalıştırıldı mı?
    - Görev birden fazla dosyayı/katmanı etkiliyorsa (API + istemci, migration + kod, i18n `tr`+`en`) **hepsi** değişti mi?
    - Bilinen ama bilerek ertelenen bir eksik varsa **sonuç raporunda açıkça listele** — sessizce atlama.
    - Kontrolü geçtikten sonra "tamamlandı" de; kontrolü anlatma, sonucunu rapora yedir.
    → gerekçe ve uygulama notu: `docs/kararlar.md` §24
25. **`dev`'e merge hızlıdır: review ve ağır kapılar yalnız `test` ve `prod` promosyonlarında koşar (2026-08-30, kullanıcı kararı).**
    - **`feature/* → dev`:** kod review **yapılmaz** (ne elle diff okuma, ne ajan), SAST/CodeQL, sır taraması (CI işi), bağımlılık CVE, ZAP, geriye uyumluluk taraması, kapsam eşiği (#29), e2e **koşmaz**. Tek istisna **pre-commit gitleaks** kancasıdır. ⚠️ **Mod D/E'de bu kısıt AJANLARA da uygulanır:** kapı-eşli roller `guvenlik` ve `kapsam-denetcisi` `dev` yönünde çağrılmaz. `veri` bunun dışındadır: şemaya dokunan iş `dev`'e merge edilmeden ÖNCE `veri`'den geçer. Sadece **build + hızlı unit test** koşar; kırmızıysa merge edilmez ve #15 gereği çıktısıyla raporlanır. **Formatlayıcı/lint iş listesinin sonunda bir kez** koşar (#26).
    - **`dev → test` ve `test → prod`:** tüm kapılar **tam** koşar — `standards/13-pr-ve-review.md` §4 merge kapısı, review checklist §5, #19'daki güvenlik taramaları, e2e (#33). Burada hiçbir şey atlanmaz.
    - `dev` merge'inde bulgu gördüysem **merge'i bloklamam**, kısa bir not olarak raporlarım; düzeltme `test` promosyonundan önce ele alınır.
    - Bu kural #19'un kapsamını daraltır: o taramalar `test`/`prod` yönünde geçerlidir; review'ın kimde olduğunu #27 belirler. → gerekçe: `docs/kararlar.md` §25
26. **Verilen iş planlandıktan sonra: `dev`'i pull et → `dev`'den dal/worktree aç → orada çalış → her işi AYRI AYRI `dev`'e merge et (2026-09-02, kullanıcı kararı).** Sıra bağlayıcıdır:
    1. **Önce `git fetch` + `dev`'i güncelle.** Bayat bir tabandan dallanma.
    2. **`dev`'den yeni bir dal (ya da worktree) aç ve orada çalış.** `dev`'in üzerinde doğrudan commit'leme.
    3. **Her iş bitince o işi tek başına `dev`'e merge et.** Birden çok işi tek commit/merge'de toplama.
    4. **`test` ve `prod` promosyonunu KULLANICI söyler.** Kendiliğinden `test`/`prod`'a merge YOK.
    5. **Formatlayıcı/lint iş listesinin SONUNDA bir kez** koşar, her merge'de değil (#25).
    - ⚠️ **`~/.claude` deposunun kendi düzeni (08/09/2026):** `dev` = çalışma dalı, `master` = yayın. Bu depoda iş `dev`'e commit'lenir; `master`'a promosyonu **kullanıcı söyler**. Uzak: `<kullanıcı>/<yapılandırma-deposu>`. Depo **paylaşımlı bir çalışma ağacıdır** — dal değiştirmeden önce `git status` doğrulanır ve yalnız kendi diff'in commit'lenir. → gerekçe: `docs/kararlar.md` §26
27. **Çalışma modu (A/B/C/D/E) her projede seçilebilir; seçim ONAYDIR (2026-09-05, kullanıcı kararı).** Mod, ajan kullanımını + review'ı + onay politikasını birlikte belirler. Tek kaynak `~/.claude/modes/README.md`; seçim projenin `.claude/mode` dosyasında. Değiştirme: `/calisma-modu <harf>`.
    - **A** Skill (ajan yok) · **B** Seçici (`analiz`/`test-yazar`/`belge`) — **VARSAYILAN** · **C** Tam takım (9 rol) · **D** Geniş takım (14 rol) · **E** Fan-out (`Workflow`). Agent Teams modları (X/Y/Z) **arşivde**, teklif edilmez — `modes/arsiv/`.
    - ⚠️ **A'da ajan çağrılmaz; B/C/D/E'de modu seçmek onaydır** — çağrı öncesi ayrıca sorulmaz, tur sonunda ajan sayısı + tahmini maliyet **raporlanır**. Otomatik yönlendirme de çağrıdır. **C/D/E'de review iki katmanlı:** ilk geçişi `qa` ajanı yapar, kritik bulguları ben doğrularım.
    - ⚠️ Mod **hiçbir durumda** şunları gevşetmez: geri alınamaz işte onay (deploy, `DROP`, force push, dış dünyaya gönderim), `test`/`prod` promosyonunun kullanıcıya ait olması (#26), "tamamlandı" öncesi eksik-kontrolü (#24), sırların repoya girmemesi (#3).
    - **How to apply:** Oturum başında modu **şu öncelikle** oku: **oturumluk seçim** (`<scratchpad>/mode`, `--tek` ile yazılır) → proje `.claude/mode` → **B**. Yoksa **B'de başla ve iş hak ediyorsa en düşük yeterli modu tek satırla ÖNER** — kendin geçme. Mod dosyası olmayan projede B'nin üç ajanı ayrıca sorulmadan çağrılabilir; diğer on bir rol için C/D/E gerekir. Mod adı söylenirse `/calisma-modu`'yu çalıştır. → gerekçe ve ölçüm: `docs/kararlar.md` §27
28. **Denetçi her geçişte eksik/yanlış KONTROL EDER, GERİ GÖNDERİR ve DÜZELTTİRİR; maliyet her devirde hatırlatılır (2026-09-07, kullanıcı kararı).** Ajan kullanılan her turda:
    - **Eksik kontrolü bloğu zorunlu.** Çıktısına başkasının güveneceği her rol (`qa`, `analiz`, `devops`, `test-yazar`, `urun-yoneticisi`) raporunu **kanıt bloğuyla** kapatır: *Doğrulama (koşulan komut/okunan aralık) · Madde eşlemesi (istenen her madde → dosya:satır) · Kapsanmayan → Sonuç: ciddi eksik YOK | VAR.* Blok temiz geçilse bile yazılır. **Orkestratör devirde tek satır** (kanıtlı `✅ temiz` + maliyet), tam bloğu **tur sonunda** ve her **"VAR"**da yazar; rolün bloğunu yutmaz. ⚠️ **Bu bir soru değil, kontroldür:** denetçi "eksik var mı?" diye kullanıcıya da üreten role de **sormaz**. **Doğrulanamayan şey "tamam" sayılmaz.**
    - **Eksik varsa GERİ GÖNDERİLİR, kullanıcıya taşınmaz.** İş üretene döner (`qa` → `gelistirici`/ben → yeniden `qa`); geri gönderme **ne eksik · hangi kanıtla · ne yapılacak** taşır. Kullanıcıya gitmesi yalnız §5 durma sebeplerinde ve tavanda olur — o da **soru değil, durum raporu**.
    - **Tek temiz geçiş yeterlidir (18/09/2026).** Devir için **bir kez** "ciddi eksik YOK" yeter. `Doğrulama` satırı koşulan komutu/okunan aralığı taşımak **zorundadır**. "VAR" çıkarsa geri gönderilir; düzeltme gelince bulguyu ortaya çıkaran **aynı doğrulama tekrar koşulur**. **Tavan: aynı iş en çok 2 kez geri gönderilir (3 geçiş)**, ulaşılamazsa durulur ve kullanıcıya **bildirilir**; kapanmamış bulgular **açık bulgu** olarak tek tek listelenir. "Ciddi eksik" = davranışı/güvenliği/geriye uyumluluğu/veriyi etkileyen ya da istenen bir maddeyi karşılıksız bırakan şey.
    - **Bulgu kapanmadan devir yok — denetçi düzelttirir.** Geri gönderme not değil **iş emridir**. Bir bulgu ancak (a) düzeltilip kanıtlanarak, (b) kullanıcı açıkça "yapma" diyerek, (c) kapsam dışı gerekçesiyle **açık bulgu olarak raporlanarak** kapanır — sessizce düşen bulgu yoktur. Tur sonu raporunda **kapanan / açık kalan** ayrımı görünür.
    - **Maliyet tur sonuna ertelenmez.** Her rol devrinde tek satır: o rolün tahmini maliyeti + turun kümülatifi + eşiğe uzaklık. Eşik **moda bağlı ve iki kademeli**: B ~$12/**$25** · C ~$75/**$150** · D ~$130/**$260** · E ~$200/**$400** — yarısında uyarı, tamamında **durma**. Otonom koşumun $100 tavanı bağımsızdır.
    - **Üç denetim boşluğu kapalı:** `analiz` bulgusunu üreten **komutu** da döndürür · `devops` çıktısı **`qa`'ya girer** · `urun-yoneticisi` çıktısı **kullanıcı onayına** gider. → ayrıntı `modes/rol-secimi.md` §2a, §3, §5-§8; gerekçe `docs/kararlar.md` §28
29. **Test kapsamı her kod tabanında EN AZ %80 (satır) — istisnasız (13/09/2026, kullanıcı kararı).**
    - **Ölçü:** satır kapsamı, **her kod tabanı AYRI** — backend · web · mobil Android · mobil iOS. Ortalama alınmaz. Ölçülmemiş kod tabanı "geçti" sayılmaz, **"ölçülmedi"** diye raporlanır ve promosyonu bloklar.
    - **Payda dürüst olur:** yalnız **üretilmiş** kod çıkarılır (EF göçleri + `ModelSnapshot`, `obj/`, `*.g.cs`, `*.Designer.cs`, `.d.ts`, testler, e2e/konfig). Çıkarma listesi projede **tek yerde ve gerekçeli** durur. El yazısı ürün kodunu listeden çıkarmak eşiği gevşetmektir → **yasak**.
    - **Kapı:** yerel kapı betiğinde (`scripts/ci-local.sh`) **promosyon modunda** koşar; eşik altı → çıkış kodu ≠ 0. **`dev → test` ve `test → prod` promosyonunu BLOKLAR**; `dev` merge'i hızlı kalır. CI aynı betiği ve aynı eşiği kullanır.
    - **Gevşetme yok:** eşik düşürülmez, istisna verilmez. **Proje `CLAUDE.md`'si bu maddeyi EZEMEZ.**
    - **Sahte kapsam yasak:** E2E bu sayıya girmez. Assert'sız test yazmak eşiği gevşetmekle aynıdır — eklenen test mutasyonla bir hatayı yakalamalı (`standards/10-test-stratejisi.md` §7).
    - **Uyum:** bir projede açılan **ilk oturum** kapsamı **ölçer**, kapı yoksa **kurar**, açığı ve kapatma planını raporlar. Açık kapanana kadar promosyon yapılamaz. → gerekçe: `docs/kararlar.md` §29
30. **Test verisindeki e-posta GERÇEK kutuya gider: `<hesap>+<değişken>@gmail.com` (14/09/2026, kullanıcı kararı).**
    - **Kapsam:** sistemin ileti gönderebileceği HER test adresi — e2e (web ve mobil), test ortamındaki seed/e2e hesapları, entegrasyon ortamına elle girilen veri, davet/link alıcıları.
    - **Yasak:** sahte alan adı — `.test`, `.local`, `example.com`, `ornek.*`.
    - **Tek kaynak:** adres testte **tek yardımcıdan** üretilir (taban env ile ezilebilir, ör. `E2E_EMAIL_BASE`); spec'e/seed'e elle adres yazılmaz (#2).
    - **Kapsam dışı:** göndericisi sahtelenen testler. → ayrıntı `standards/11-playwright.md` §4; gerekçe `docs/kararlar.md` §30
31. **E2E koşum döngüsü: tam koş → düşenleri belirle → düzelt → yalnız düzeltilenleri koş → tam tekrarına ben karar veririm (14/09/2026, kullanıcı kararı).**
    - **Önce paketin TAMAMI koşar**, ilk hatada durulmaz. Düşenler **sınıflandırılır:** ürün hatası · bayat spec · veri/fixture · ortam.
    - **Düşenler düzeltilir** — her düzeltme kendi dalında, kendi merge'iyle (#26). Retry artırmak ya da assertion gevşetmek düzeltme sayılmaz.
    - **Sonra YALNIZ düzeltilen testler** (ve etkilenebilecekler) koşar.
    - ⚠️ **E2E yalnız `test` ortamına çıkmış kodla koşar.** Düzeltme `dev`'deyken doğrulama **unit test + tsc/lint**'tir (#25).
    - ⛔ **E2E koşmadan `prod`'a çıkılmaz.** **Tek istisna hotfix'tir:** kullanıcı açıkça "hotfix" dediğinde e2e koşulmadan çıkılır ve raporda "e2e atlandı (hotfix)" yazılır — geçti sayılmaz.
    - **Tam paketin tekrarına ben karar veririm** ve gerekçesini raporlarım: düzeltme paylaşılan bir parçaya dokunduysa · promosyon kaydı tam koşum istiyorsa · düşüşlerin bir kısmı ortam kaynaklıysa tekrarlanır; tek spec'e sınırlıysa hedefli koşum yeter.
    - **Ortamın sınırına takılan koşum geçersizdir**; ürün hatası diye okunmaz, paralellik düşürülüp tekrarlanır. → ayrıntı `standards/11-playwright.md` §9a; gerekçe `docs/kararlar.md` §31
32. **Sıra: önce TÜM kod → sonra unit testleri yazılır → unit testler koşulur; E2E ise `test`'e çıkınca YAZILIR ve koşulur (14/09/2026, kullanıcı kararı).**
    - Planlanan işin kodu **bütünüyle** yazılır; her küçük değişiklikten sonra test koşulmaz.
    - Kod bitince unit testleri yazılır (#8), sonra testler **bir kez** koşulur; kırmızı varsa düzeltilir ve yalnız ilgili testler tekrar koşar.
    - **E2E `dev` aşamasında ne yazılır ne koşulur** — #33 bunu daralttı: e2e yazımı/koşumu `prod` öncesi kapıdadır.
    - #26 geçerli kalır: her iş kendi dalında yazılır ve unit koşumu yeşil olunca **ayrı ayrı** `dev`'e merge edilir. → gerekçe: `docs/kararlar.md` §32
33. **E2E'nin tek yeri `prod` öncesi kapıdır (20/09/2026, kullanıcı kararı; #31 ve #32'nin e2e zamanlamasını EZER).**
    - **`feature → dev` ve `dev → test`:** e2e **yoktur** — koşum da, "yazıldı mı" kontrolü de, deploy/durum dosyası beklemesi de. Eksik spec'ler `prod` kapısının 2. adımında çıkarılır.
    - **`test → prod` (kullanıcı "prod merge" dedikten sonra, promosyondan ÖNCE) sırayla:**
      1. **Kod `test`'e çıkmış mı?** Değilse önce `test`'e çıkılır ve deploy beklenir. `prod`, `test`'te olmayan kodu taşımaz.
      2. **Eksik e2e var mı?** Değişen davranış spec'lerle karşılaştırılır.
      3. **Eksikse YAZILIR** (`test` ortamına karşı doğrulanarak).
      4. **Bu kodla e2e koşulmadı mı?** `test`'te deploy olan SHA için geçerli tam koşum kaydı yoksa koşulur (#31 döngüsü).
      5. Yeşil kayıt varsa `prod`'a çıkılır. Kırmızı/bayat/kayıtsızsa çıkılmaz.
    - **İstisna yalnız hotfix:** rapora "e2e atlandı (hotfix)" yazılır.
    - Merge betiği bu kuralla çelişen bir e2e adımı koşuyorsa raporla, düzeltmeyi öner. → `docs/kararlar.md` §33

## Yapma listesi

Numaralı kurala bağlananlar dahil tam liste: `docs/kararlar.md` § Yapma listesi.

- ❌ İstemcide tek başına iş mantığı / validasyon / yetki kararı
- ❌ İstemciden doğrudan veritabanına bağlanma
- ❌ Yorum satırına alınmış ölü kod commit'i
- ❌ Formatlayıcı (`dotnet format`, Prettier/ESLint) çalıştırmadan PR
- ❌ Alan/endpoint silme veya yeniden adlandırma (= silme + ekleme)
- ❌ `SELECT *`, N+1 sorgu, sayfalamasız liste endpoint'i
- ❌ Yakalanıp yutulan exception (`catch {}`), log'suz hata
- ❌ Log'a PII / token / parola yazmak
- ❌ Testleri "geçsin diye" gevşetmek, flaky testi `retry` ile örtmek
- ❌ `main`/`prod`'a doğrudan push
- ❌ Kullanıcı onayı olmadan: prod deploy, DB `DROP`, `git push --force`, veri silme, dış servise mesaj/yayın gönderme
- ❌ Denenmemiş yedek ("yedek var" demek yetmez, restore provası yapılır)
- ❌ `test-writer` ve `migration-reviewer` subagent'larını çağırmak — kesin yasak. Asıl koruma **mod setidir**: modun rolleri dışında hiçbir ajan çağrılmaz → #27, #28

## Çalışma düzeni (Claude için)

Protokolün tamamı `standards/00-calisma-duzeni.md`'dedir (plan → onay → uygula,
doğrulama, bağlam disiplini, paralel oturum, onay gerektiren işler).
Özet: dosyayı düzenlemeden önce oku · birden fazla dosyaya dokunan işte önce
kısa plan sun · build + ilgili testler + lint/format koşmadan "çalışıyor" deme,
koşmadıysan **"çalıştırmadım" de** · belirsizlikte bağımsız işleri bitir, sonra
tek net soru sor · yalnız kendi diff'ini commit et, `--force` kullanma ·
geri alınamaz işte (deploy, `DROP`, dış dünyaya gönderim, dosya silme) onay al.

## Uzun kapı/koşum sırasında CANLI PANO (KALICI, tüm projeler)

Dakikalarca süren bir kapı, koşum veya deploy başlattığında (merge kapısı, CI, test
bataryası, deploy zinciri, migration) **bir Artifact panosu yayınla
ve koşum boyunca AYNI URL'e yeniden yayınlayarak güncel tut.** Metin raporu
panonun yerine geçmez; ikisini birlikte ver. Panoda **zorunlu** olanlar:
ağırlıklı genel yüzde · madde kırılımları · canlı ölçüm (saat + ham veri) ·
açık riskler.

⚠️ **Yüzde ÖLÇÜLÜR, uydurulmaz** — hangi sinyalden okunduğu panoda yazar;
ölçülemiyorsa "ölçülemiyor" denir. Uzun koşumun çıktısı tamponlayan bir boruya
(`tail`/`head`) verilmez — log dosyasına yazılır, pano ondan beslenir.

→ Ayrıntılı kurallar: `standards/00-calisma-duzeni.md` §10.
