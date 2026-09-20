# Çalışma modları — tek kaynak

Bir görevin nasıl yürütüleceğini belirleyen **beş** mod: **A-E subagent**.
(Agent Teams modları X-Z arşivde → [`archive/README.md`](archive/README.md).) Okuma önceliği: **oturumluk seçim** (`<scratchpad>/mode`,
`/working-mode <harf> --tek` ile yazılır) → proje `.claude/mode` → **B**.
İkisi de yoksa **B** geçerlidir (18/09/2026, kullanıcı kararı; öncesinde A idi).

| Mod | Ad | Ajan | Review | Onay politikası | Maliyet çarpanı |
|---|---|---|---|---|---|
| **A** | Skill | **yok** | ben | açıkça seçilir | 1,0x (taban) |
| **B** | Seçici **(VARSAYILAN)** | `analyst`, `test-writer`, `doc-writer` | ben | varsayılan = onay | 1,15–1,35x ⚠tahmin |
| **C** | Tam takım | 9 rol ajanı (B ⊂ C) | `qa` ajanı + ben | mod seçimi = onay | 2,5–4x ⚠tahmin |
| **D** | Geniş takım | 14 rol ajanı (C ⊂ D) | `qa` + `security`/`coverage-auditor` doğrudan bana + ben | mod seçimi = onay | 4,5–7x ⚠tahmin |
| **E** | Fan-out | D + `Workflow` paralel (yalnız 14 rol) | `qa` ajanı + ben | mod seçimi = onay | 7–14x ⚠tahmin |

⚠️ **Çarpanların hiçbiri ölçülmedi** — modlar 05/09/2026'da doğdu, elimizdeki
ölçüm (33 oturum) mod karşılaştırması içermiyor. Duvar saati iddiaları (C %20–40,
E %50–70) da **ölçülmedi**. Ölçülen tek şey rol maliyetleri:
[`role-selection.md`](role-selection.md) §8 ölçüm defteri — orada `qa`/opus turu
**$4,10** ölçüldü (eski tahmin $8–20'ydi, 2-5 kat yüksek).

### Agent Teams modları — X · Y · Z → **ARŞİVDE** (20/09/2026)

Takım modları **başlatılamadığı** için `modes/archive/`'e alındı (sebep, geri
getirme koşulu ve eşlemeler: [`archive/README.md`](archive/README.md)). Bir mod
olarak teklif edilmez; kullanıcı sorarsa "bugün başlatılamıyor" denir.

## Kalıcı kural — ajan yalnız modla gelir

**A'da ajan çağrılmaz; B/C/D/E'de modu seçmek o ajan setine verilmiş onaydır.**
Çağrı öncesi ayrıca sorulmaz; tur sonunda kaç ajan koştuğu ve tahmini
maliyet **raporlanır**. Ajan gerekiyor da mod A ise: ajanı başlatmam, **mod
değiştirmeyi öneririm** (`/working-mode B`) — karar kullanıcının.

⚠️ **Otomatik yönlendirme de çağrıdır.** Claude Code ajan `description`'ına
bakıp bir ajanı kendiliğinden önerebilir; A'da buna **uyulmaz**, B/C/D'de
yalnız o modun seti içindeyse uyulur.

Tarihçe (05/09/2026, kullanıcı kararı): önce beş mod vardı; **eski E — Eski usul**
(ajan var ama her çağrıda sor, review'ı ben) A ile aynı iş olduğu için
kaldırıldı ve E'nin taşıdığı global #21/#23 mod sistemine devredildi.
Ölçüm gerekçesi: 33 oturumda ajan turları toplamın %7,7'siydi, tur başına
$6,9 — her turdaki onay sürtünmesi maliyeti değil ÖNGÖRÜLEMEZLİĞİ
azaltıyordu; mod seçimi öngörülebilirliği peşinen sağlıyor.

## Modun DIŞINDA kalan, her modda geçerli kurallar

- Geri alınamaz iş (deploy, `DROP`, force push, dış dünyaya gönderim) → **her
  modda onay ister**. Mod seçimi bunu kapsamaz.
- `test`/`prod` promosyonu → **her modda** kullanıcı açıkça söyler.
- "Tamamlandı" öncesi eksik-kontrolü (global #24) → her modda aynı.

## Mod verilmediyse — en ucuz ve en hızlıyı ÖNER (05/09/2026, kullanıcı kararı)

Proje `.claude/mode` taşımıyorsa **ve** kullanıcı bir mod söylemediyse:

1. **B'de başla** (18/09/2026'dan beri varsayılan) — `analyst`, `test-writer`
   ve `doc-writer` açık, kod ve review bende. Bu üç ajan için ayrıca sorulmaz;
   varsayılanın kendisi onaydır.
2. İş bir üst modu **gerçekten** hak ediyorsa (15+ dosyalık uçtan uca özellik
   → C; güvenlik/veri/kapsam/e2e boyutu olan iş → D; 5+ bağımsız iş → E)
   **kendin geçme**, tur başında **tek satırla öner**: hangi mod, neden,
   kabaca kaç kat (`README` çarpanları). Karar kullanıcının; cevap gelmezse
   B'de devam.
3. Öneri **en düşük yeterli** moddur: B yetiyorsa C önerilmez.
4. ⚠️ **Aşağı da önerilir:** iş B'nin üç ajanını da hak etmiyorsa (tek dosya,
   tek komut, saf düşünme işi) ajan çağırmadan yürütülür — bu A'ya geçmek
   değil, B içinde §0'ın "kendim yaparım" dalıdır. Ajan kullanmamak B'nin
   ihlali değildir; **gereksiz ajan çağırmak** ihlaldir.

`.claude/mode` varsa bu bölüm işlemez — o dosya açık bir karardır.

## Denetim ve maliyet görünürlüğü (07/09/2026, kullanıcı kararı)

Her modda, ajan kullanılan her turda:

1. **Denetçi sormaz — kontrol eder, eksik varsa geri gönderir.** Çıktısına
   güvenilecek her rol (`qa`, `analyst`, `devops`, `test-writer`,
   `product-manager`) ve her devirde orkestratör, raporunu **kanıt bloğuyla**
   kapatır (doğrulama komutu · madde eşlemesi · kapsanmayan → ciddi eksik
   YOK/VAR). Eksik/yanlış bulunursa iş **üretene geri döner ve düzelttirilir**,
   kullanıcıya taşınmaz; kapanış için **aynı doğrulama tekrar koşulur** —
   "düzeltildi" beyanı yetmez, sessizce düşen bulgu olmaz.
   **Devir için bir kez "ciddi eksik yok" yeter** (`✅ temiz`, 18/09/2026);
   o tek geçiş **kanıt taşımak zorundadır** — kanıtsız "temiz" geçersizdir ve
   geçiş 1'in çağrı sayısının yarısını aşmaz (+%10–20 yük).
   Aynı iş 2 kez geri gönderilip hâlâ kapanmazsa zincir durur ve kullanıcıya
   **bildirilir** — soru değil, durum raporu.
   → [`role-selection.md`](role-selection.md) §7
2. **Maliyet her devirde hatırlatılır**, tur sonuna ertelenmez:
   `↳ analiz bitti · ~$3 · tur toplamı ~$9 (2 ajan) · eşik ~$150 (C)`.
   Eşik **moda bağlı ve iki kademeli**: yarısında uyarı, tamamında durma —
   B ~$25 · C ~$150 · D ~$260 · E ~$400. Rakamların kaynağı → §8.
3. **`product-manager` çıktısı kullanıcı onayına gider**, zincire otomatik
   akmaz (§2a). **`devops` çıktısı `qa`'ya girer** (§3).

⚠️ **Kimin denetçisi kim** — boşluk bilinçlidir, sessiz değildir:

| Rol | Denetçisi |
|---|---|
| `developer` ve benim yazdığım kod | **`qa`** → kritik bulguları ben doğrularım |
| `qa`, `analyst`, `devops`, `test-writer`, `product-manager` | Kendi **eksik kontrolü** bloğu (§7) + orkestratör |
| `product-manager`nin kapsamı | **Kullanıcı** (§2a onay kapısı) |
| `architect`, `designer`, `doc-writer` | **Ayrı denetçisi yok** — eksik kontrolü bloğundan muaf, denetleyen orkestratördür |

`qa`'ya ikinci bir denetçi **ajan** eklenmedi: subagent token'ı ana konuşmadan
~4x pahalı, kazanç maliyeti karşılamıyor.

## Rol seçimi (C · D · E)

Kimin ne yapacağına **orkestratör** karar verir — ajanlar birbirini çağırmaz.
Karar ölçütleri: [`role-selection.md`](role-selection.md).

## Otonom koşum (C/D/E üstüne biner)

Uzun bir işi bırakıp gitmek: [`autonomous-run.md`](autonomous-run.md).
Onay #20 kapsamındadır ve KOŞULLUDUR — iş listesi, bitiş tanımı, bütçe tavanı,
tıkanma freni, geri alınamaz eylemde durma.

## Mod seçimi

    /working-mode           # mevcut modu göster
    /working-mode B         # bu proje için B'ye geç (kalıcı)
    /working-mode B --tek   # yalnız bu oturum, dosyaya yazma
