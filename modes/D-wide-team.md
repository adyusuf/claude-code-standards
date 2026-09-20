# Mod D — Geniş takım (14 rol)

C'nin dokuz rolüne **beş denetçi rol** eklenir. Ben orkestratörüm (ayrı
orkestratör ajan YOK — o ikinci bir soğuk prefix demek).

## Ajan seti

**C'den gelen dokuz:** `product-manager` · `analyst` · `architect` · `designer` ·
`developer` · `test-writer` · `qa` · `devops` · `doc-writer`

**D'de açılan beş:** `security` · `data` · `coverage-auditor` · `e2e-writer` ·
`observability`

⚠️ **D, C'nin üst kümesidir** (B ⊂ C ⊂ D). Beş yeni rolün tamamı **denetçidir**:
hiçbiri ürün kodu yazmaz, ikisi (`data`, `e2e-writer`) kendi dar alanında üretir.

## Neden bu beş rol

Her biri **zaten yazılı bir global kuralın** sahipsiz kalan işidir:

| Rol | Sahipsiz kalan kural |
|---|---|
| `security` | #19 — SAST, sır taraması, CVE, ZAP, OWASP Top 10 eşlemesi |
| `data` | #4 + #9 — additive şema evrimi, migration, index, transaction |
| `coverage-auditor` | #29 — her kod tabanında %80 satır kapsamı, payda dürüstlüğü |
| `e2e-writer` | #30 + #31 + #32 — e2e verisi, koşum döngüsü, sınıflandırma |
| `observability` | #17 standardı — log, metrik, trace, alarm, performans |

C'de bu işler ya `qa`'nın bir ekseninde sıkışıyordu ya hiç kimsede değildi.

## Kural

⚠️ **Kimin ne yapacağına karar verme kuralı ayrı dosyada:**
[`role-selection.md`](role-selection.md) — ajan mı ben mi, iş tipi → rol, sıra ve
devir, atlama, çatışma hakemliği, durma, görünürlük. **Rol seçmeden önce oku.**

- Sıra sabit değil; işin gerektirdiği rolleri seçerim ve **hangilerini neden
  seçtiğimi, hangilerini neden atladığımı** tur başında yazarım. ⚠️ **On dört
  rolün hepsini her turda koşturmak D'yi kullanmak değil, israf etmektir** —
  tipik bir tur 5–8 rol açar.
- Bağımsız roller **aynı mesajda paralel** başlatılır.
- `developer` yalnız **izole, sözleşmesi net** parçalarda; çapraz-katman iş bende.
- Ajan çağrısı öncesi sormam; **her devirde** maliyet satırı geçerim
  (§6, §8). Eşik iki kademeli: **~$130'da uyarı, ~$260'ta durma**.
- Denetçi roller **sormaz, kontrol eder**: eksik/yanlış varsa iş üretene
  **geri gönderilir ve düzelttirilir**, kapanış aynı doğrulamanın yeniden
  koşulmasıyla kanıtlanır; devir için **tek temiz geçiş** yeter (§7).
  2 geri göndermede kapanmazsa zincir durur, açık bulgular listelenip sana
  **bildirilir**.

## Denetçi haritası — kim kime bağlı

D'nin C'den asıl farkı budur: **`qa` tek denetçi olmaktan çıkar.**

| Üretici | Denetçisi |
|---|---|
| `developer` · `test-writer` · `devops` | `qa` |
| `data` · `e2e-writer` · `observability` | `qa` |
| **`security`** | **orkestratör** (doğrudan) |
| **`coverage-auditor`** | **orkestratör** (doğrudan) |
| `qa` | orkestratör — kritik bulguları ben doğrularım |
| `product-manager` | **kullanıcı** (§2a kapsam kapısı) |
| `architect` · `designer` | orkestratör (§7 muafiyeti) |

⚠️ **`security` ve `coverage-auditor` neden `qa`'ya girmez:** C'de `qa`'ya üç
üretici bağlıydı; on dört rolde bu sekize çıkardı ve zincirin en yüklü düğümü
aynı zamanda en az denetlenen düğüm olurdu. Bu ikisi **kendi ekseninde
nihaidir** — `qa`'nın güvenlik ekseni `security`'te zaten daha derin işleniyor,
kapsam ölçümünü ikinci kez ölçmek katma değer üretmiyor. Kritik olan payda ve
saldırı senaryosu kararlarıdır; onları orkestratör doğrular.

⚠️ **`architect` muafiyeti D'de daha riskli:** planı artık `data`, `security` ve
`e2e-writer`'ı da besliyor — etki alanı C'ye göre üç kat. Muafiyet sürüyor ama
plan sapması çıktığında zincir **bana** döner, `architect`'a değil.

## Kapı mı ajan mı — zamanlama (18/09/2026, kullanıcı kararı)

**Kapı otoritedir; ajan kapının yerine geçmez.** Kırmızı/yeşil kararını
`scripts/ci-local.sh` ve CI verir. Ajanın "temiz" demesi kapıyı geçmiş saymaz,
ve #19'un "koşmayan kapı geçilmiş sayılmaz" kuralı aynen durur.

**İkisi aynı işi yapmaz — farklı şeylere bakarlar:**

| | Kapı (betik/CI) | Ajan |
|---|---|---|
| Ne arar | Bilinen desen | Bağlam gerektiren şey |
| Örnek | `gitleaks`: "bu string AWS anahtarına benziyor" | "bu uç yetkiyi hiç kontrol etmiyor" |
| Çıktısı | Çıkış kodu | Bulgu + saldırı/veri kaybı senaryosu |
| Yanılması | Yanlış pozitif | Kaçırma |

Üçüncü ve asıl iş: **ajan kapının kendisini denetler** — `continue-on-error`,
yutulan çıkış kodu, koşmayan ama yeşil görünen adım. Bunu betik kendi kendine
bulamaz (#19: "bir taramanın temiz sonucunu, bulabildiğini kanıtlayan bir
kontrol değişkeni olmadan kabul etmezsin").

### Kapı-eşli roller `dev` yönünde KOŞMAZ

`security` ve `coverage-auditor` **yalnız `dev → test` ve `test → prod`
promosyonlarında** koşar. `feature/* → dev` yönünde çağrılmazlar.

- Gerekçe: #25 `dev` merge'ini bilinçli olarak hızlı tutuyor; oraya beş
  denetçi eklemek kuralı ajan eliyle geri getirmek olurdu. Kapıların yeri
  promosyon, ajanların yeri de orası.
- ⚠️ Bedeli kabul edildi: güvenlik ve kapsam sorunu `dev`'de değil,
  promosyon anında görünür. Karşılığında `dev` hızlı kalır.
- `dev` yönünde tek istisna, #25'in kendi istisnası: **pre-commit gitleaks**
  kancası. O bir kapıdır, ajan değildir ve açık kalır.

### Kapı-eşli OLMAYAN roller iş ne zaman gerekiyorsa koşar

`data` · `observability` bu kısıtın **dışındadır** — çünkü bunlar bir
promosyon kapısının eşi değil, **kod yazılırken** gereken denetimlerdir:

- ⚠️ **`data` özellikle `dev` ÖNCESİ koşar.** Migration `dev`'e girdikten sonra
  denetlemek geçtir: yanlış bir şema değişikliği geri alınamaz ve #4'ün
  additive kuralı ancak yazılmadan önce uygulanabilir. Şemaya dokunan bir iş
  `data`'siz `dev`'e merge edilmez.
- `observability` de kod yazılırken değer üretir — eksik log'u üretimde
  fark etmek, tanım gereği geç kalmaktır.

`e2e-writer` zaten ortam-bağlıdır: #31 gereği **yalnız `test`'e çıkmış kodla**
koşar, bu kararın kapsamı dışında.

## Ne zaman
- Uçtan uca özellik **+ güvenlik/veri boyutu olan** iş (auth, ödeme, KVKK, göç)
- `test`/`prod` promosyonu öncesi tam kapı (#19 + #29 + #31 birlikte)
- Şema değişikliği içeren özellik — `data` olmadan geriye uyumluluğu doğrulayan yok

**Ne zaman DEĞİL:** rutin özellik, tek katman iş, güvenlik/veri/kapsam boyutu
olmayan değişiklik → **C yeter**. D'yi C'nin yerine varsayılan yapmak, beş
denetçiyi boşa koşturmaktır.

## Beklenen maliyet

**4,5–7x** ⚠tahmin (C'nin 2,5–4x'i × ~1,75). Hesaplanan tam tur (Opus 5, 14 rol,
denetim dahil): **~$11,4**; C'nin dokuz rolü aynı modelle ~$6,5.

⚠️ Bu rakam **ölçüm değil**: token profilleri ve %35'lik geri gönderme
olasılığı varsayımdır. Ölçülen tek sayı ajan turu başına $6,9 ortalamasıdır
(§8). İlk gerçek D turunda **kaç bulgunun geri gönderildiğini** kaydet —
tahminin en zayıf halkası odur.

## Tarihçe
18/09/2026, kullanıcı kararı: D harfi fan-out'tan alınıp geniş takıma verildi.
Fan-out artık [`E-fanout.md`](E-fanout.md); E, D'nin üstüne biner.
