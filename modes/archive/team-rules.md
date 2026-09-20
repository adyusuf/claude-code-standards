# Agent Teams modları (X · Y · Z) — ortak kurallar

> X/Y/Z, B/C/D'nin **takım** karşılığıdır. Roller ve denetim aynıdır; değişen
> şey ajanın **ömrü ve iletişimi**. Rol seçimi hâlâ [`role-selection.md`](../role-selection.md)
> (§0-§8'in tamamı X/Y/Z'de de geçerlidir); bu dosya yalnız takıma özgü
> farkları yazar.

## 0. ⛔ ÖN KOŞUL — bugün X/Y/Z BAŞLATILAMAZ

İki ayrı sebeple; ikisi de düzeltilmeden mod açılmaz.

**(a) Rol tanımlarında takım araçları yok.** Dokuz rolün `tools:` allowlist'i
kapalı ve hiçbirinde `SendMessage`, `TaskList`, `TaskGet`, `TaskUpdate`,
`TaskCreate` yok (`grep -n "^tools:" ~/.claude/agents/*.md` → 9/9 kapalı,
`SendMessage` → 0 eşleşme). Teammate ayağa kalkar ama **kimse duymaz**: düz
metni görünmez, görevini `completed` yapamaz, lider onu boşta sanıp aynı işi
ikinci kez atar.
→ Roller genişletilmeden X/Y/Z **açılmaz**. Genişletme, aynı dosyalar B/C/D'de
de kullanıldığı için o modların ajan yetkilerini de büyütür.

✅ **Karar (08/09/2026, kullanıcı):** araçlar **şimdi eklenmiyor.** X/Y/Z zaten
plan kapısının arkasında; bugün eklemek B/C/D ajanlarına kullanmayacakları
yetkiyi verir, karşılığında hiçbir şey kazandırmaz. **Plan kapısı açıldığı gün**
eklenir ve o gün ayrıca kararlaştırılır: dokuz rolü olduğu yerde genişletmek mi,
yoksa takım için ayrı rol dosyaları (`qa-team.md` gibi) açıp yetki ayrımını
korumak mı — ikincisi 9 dosyayı 18 yapar, ikiz bakım yükü doğurur.
⛔ Bu karar verilene kadar §0(a) yürürlüktedir: mod açılmaz.

**(b) Özellik kapalı.** Etkinleştirme kapısı `--agent-teams` bayrağı ya da
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` ortam değişkenidir **ve** hesap planı
kapısı vardır (*"Agent Teams is not yet available on your plan."*).
`teammateMode` özelliği açmaz — yalnız **nasıl** koşacağını söyler
(tmux/in-process/auto). **`/teams` diye bir slash komutu yoktur**; `team` içeren
tek komut adı `team-onboarding`'dir ve ilgisizdir.

⚠️ 08/09/2026: bu masaüstü oturumunda `Agent` şemasında `team_name`/`name`/`mode`
yok — binary'de bunun koşullu metni var: *"The run_in_background, name,
team_name, and mode parameters are not available in this context."*

## 1. Mekanizma (Claude Code 2.1.148 binary'sinden doğrulandı, 08/09/2026)

| | Subagent (B/C/D) | Teammate (X/Y/Z) |
|---|---|---|
| Ömür | Tek atış | **Oturum boyunca yaşar**, her turdan sonra idle'a düşer |
| İletişim | Yalnız bana rapor | **`SendMessage`** — düz metin çıktısı diğerlerine görünmez |
| Koordinasyon | Yok — ben sıralarım | **Paylaşılan görev listesi** (`TaskList`/`TaskGet`/`TaskUpdate`/`TaskCreate`; `owner`, `status`, `blockedBy`) |
| Paralellik | Aynı mesajda başlatılan turlar | **Gerçek eşzamanlılık** |
| Yuvalama | Ajan ajan çağıramaz | **Teammate teammate çağıramaz** — ama **senkron subagent çağırabilir** (§2.3) |
| Kalıcılık | — | Oturumlar arası **yaşamaz**; takım/görev durumu **diskte kalır** |

Spawn: `Agent` aracına `team_name` + `name` (+ `mode`). Ayar `teammateDefaultModel`
varsayılan modeli verir, lider tek tek `model` ile ezer.

⚠️ **`team/` paylaşılan belleği takım mekanizması DEĞİLDİR** — proje dizininde
çalışan **tüm kullanıcılarla** paylaşılan bellek kapsamıdır ve X/Y/Z'den
bağımsız olarak zaten çalışır. Binary'nin kendi kısıtı geçerlidir: **paylaşılan
belleğe sır/API anahtarı yazılmaz** (global #3 ile aynı yön).

## 2. Teammate'e kapalı olanlar (hepsi ayrı ayrı doğrulandı)

### 2.1 İzin kipi — ⛔ geri alınamaz eylemde teammate DURUR

Teammate ayrı bir süreç olarak doğar ve **liderin izin kipi komut satırına
geçer**: `bypassPermissions` → `--dangerously-skip-permissions`, `acceptEdits`
→ `--permission-mode acceptEdits`. Yani kullanıcıya diyalog **çıkmayabilir**.

**Kural:** teammate geri alınamaz bir eyleme (deploy, `DROP`, force push, dış
dünyaya gönderim, `test`/`prod` promosyonu) geldiğinde **yapmaz**: durur,
`SendMessage` ile lidere bildirir, lider kullanıcıya sorar. Bu, teammate'in
spawn prompt'una **açıkça yazılır** — ortamdan gelmez.

⚠️ Lider oturumu `bypassPermissions`/`acceptEdits`'te ise X/Y/Z **açılmaz**;
onay kapısı zaten yoktur ve teammate onu devralamaz.

### 2.2 Otonom döngü — ⛔ teammate cron/Monitor kurmaz

Teammate kalıcı (`durable`) cron kuramaz ama **oturumluk cron kurabilir**
(`durable:false` = bellek içi, oturum bitince ölür) ve `Monitor` açabilir.
Global #20 (sormadan otonom döngü yok) X/Y/Z'de aynen geçerlidir:
**teammate `CronCreate`/`Monitor`/`ScheduleWakeup` kullanmaz**, ihtiyaç varsa
lidere bildirir.

### 2.3 Senkron subagent — sayılır ve raporlanır

Binary: *"In-process teammates cannot spawn background agents. Use
run_in_background=false for synchronous subagents."* Yani **teammate → senkron
subagent yolu açıktır**.

**Kural:** teammate subagent çağırmaz. Çağırması gereken bir iş varsa lidere
bildirir. Gerekçe: `role-selection.md`'nin "rol seçimi tek yerdedir" değişmezi ve
maliyetin tek elde görünmesi — teammate'in içinden koşan tur benim maliyet
satırımda görünmez, eşik hiç çalmadan aşılır.

## 3. Lider bendim — görev **atanır**, kapılmaz

Teammate'in yerleşik talimatı iş kapmayı **teşvik eder** (*"Claim an available
task using TaskUpdate (set `owner` to your name), or wait for leader
assignment"*) ve koşucu düzeyinde de böyle davranır (`Claimed task #`).
**Kapatma anahtarı yoktur** — bu kural ancak spawn prompt'una yazılırsa geçerlidir.

**Uygulama (yoksa mod açılmaz):**
- Her teammate'in spawn prompt'una şu satır **birebir** girer: *"Görev kapma:
  `TaskUpdate` ile kendine `owner` atama. Yalnız lider atar. `TaskCreate` ile
  yeni görev açma — kapsam değişikliği önerini `SendMessage` ile lidere yaz."*
- Lider **sahipsiz `pending` görev bırakmaz**; atanmamış işler `blockedBy` ile
  kilitli tutulur.

⚠️ Gerekçe: aksi hâlde `developer` teammate'i sırası gelince `qa` görevini
kapıp **kendi kodunu kendi review eder** — C/Y'nin "üreten kendi işini
denetlemez" ilkesi sessizce çöker.

## 4. Denetim — `role-selection.md` §7 ile AYNI, taşıyıcısı farklı

| §7 kavramı | Takımdaki hâli |
|---|---|
| Geri gönderme | Görev **yeniden açılır** (`TaskUpdate`: status → `pending`, owner → üreten) + `SendMessage` ile "ne eksik · hangi kanıtla · ne düzeltilecek · kapanış kanıtı" |
| Kapanış | "Bitti" beyanı yetmez; denetçi doğrulamayı **yeniden koşar**, ham sonucu yazar |
| Tavan | Aynı görev en çok **2 kez** geri gönderilir; sonra durur, açık bulgular listelenir, bana bildirilir |
| Eksik kontrolü bloğu | Teammate raporunu bu blokla kapatır ve **`SendMessage` ile gönderir** |

⚠️ **Blok her zaman LİDERE de gider** (`to: team-lead`). Teammate'ler arası DM'in
lidere yalnız **özeti** düşer, içeriği düşmez — yani `qa` bulgusunu doğrudan
`developer`'ye gönderip aralarında kapatırsa §7'nin "orkestratör bloğu yutmaz"
garantisi ve #28'in "kapanan / açık kalan" ayrımı kanıtsız kalır.

⚠️ Teammate'ler uzun yaşadığı için "sonra bakarım" burada kolaylaşır: tur
sonunda **açık bulgu sayısı** raporlanır, sıfır değilse görünür.

## 5. Eşzamanlı düzenleme — aynı dosyaya iki teammate girmez

"Gerçek eşzamanlılık"ın bedeli budur. İki kuraldan biri seçilir ve tur başında
**yazılır**:

- **Dosya ayrımı:** her teammate'in dokunacağı yol öbeği görevinde tanımlıdır;
  kesişen iş tek teammate'e verilir.
- **İzolasyon:** `Agent` çağrısında `isolation: "worktree"` — teammate kendi
  worktree'sinde çalışır, birleştirme lidere aittir.

⚠️ Kural yoksa ikinci `Edit` birincinin yazdığını görmeden yazar; #26'nın "her
iş ayrı commit, izlenebilir" düzeni tek bir karışmış çalışma ağacına döner.

## 6. Görev listesi disiplini

- Her görev **tek bir role** aittir ve **kabul kriteri** taşır.
- Bağımlılık `blockedBy` ile yazılır, sözle değil.
- Görev kapanınca **kanıtı yorum olarak** eklenir (koşulan komut + sonucu).
- ⚠️ Liste, `role-selection.md` §6'daki tur başı/sonu raporunun **yerine geçmez** —
  liste takımın içi, rapor senin.

## 7. Maliyet

| Mod | Tahmini çarpan | Karşılığı |
|---|---|---|
| **X** | ~1,5–2,5x | B (~1,15–1,35x) |
| **Y** | ~3–6x | C (2,5–4x) |
| **Z** | ~6–12x | D (4–8x) |

⚠️ **Çarpanların hiçbiri ölçülmedi**; B/C/D tahminlerinden türetildi.
⚠️ **Mekanizma gerekçesi de doğrulanmadı.** "Teammate her turda bağlamını
yeniden okur / boşta beklerken para yakar" **denenmemiş bir hipotezdir** ve
binary aksini düşündürüyor: teammate her turdan sonra **idle**'a düşer (mesaj
gelmedikçe tur üretmez) ve geçmişini gerektiğinde **sıkıştırır**. Ölçüm gelene
kadar bu cümleler karar gerekçesi olarak kullanılmaz.

**Ölçüm:** `python3 ~/.claude/scripts/session-cost.py <oturum-id>` — tahmin
değil, transcript'ten ölçer. İlk gerçek X/Y/Z turunda koşulur ve
`role-selection.md` §8 ölçüm defterine yazılır.

**Eşikler** §8'in X/Y/Z satırlarındadır (iki kademeli: yarısında uyarı,
tamamında durma).

## 8. Ne zaman takım, ne zaman subagent?

| Durum | Seç |
|---|---|
| İş **tek atışlık** (araştır, raporla, bitir) | **B/C/D** |
| Roller **tur tur birbirine veri geçirecek** | **X/Y/Z** |
| Aynı işi N modülde tekrarlamak | **D** (Workflow) |
| Oturum kapanınca sürmesi gereken iş | **Hiçbiri** — teammate oturumlar arası yaşamaz |

⚠️ **En düşük yeterli mod**: X yetiyorsa Y, B yetiyorsa X önerilmez.

## 9. Oturum bitişi ve devir

Teammate'ler ölür ama **takım ve görev listesi diskte kalır**
(`~/.claude/teams/<takım>/`, `~/.claude/tasks/<takım>/`). Bu yüzden:

- Oturum kapanmadan önce **`in_progress` görev bırakılmaz** — ya `completed`
  ya `pending`'e döner; aksi hâlde sonraki oturumda sahipsiz "devam ediyor"
  görünür.
- Devir notu **görev listesi durumunu** taşır.
- Aynı `team_name` yeniden kullanılamaz (*"Choose a different team_name"*) —
  yeni oturum yeni ad alır.

## 10. Mod dışında kalan, X/Y/Z'de de gevşemeyen kurallar

Geri alınamaz işte onay (§2.1) · `test`/`prod` promosyonunun kullanıcıya ait
olması (#26) · "tamamlandı" öncesi eksik-kontrolü (#24) · sırların repoya ve
paylaşılan belleğe girmemesi (#3) · otonom koşum onayı (#20, §2.2).
**Teammate'ler bunları benim adıma devralamaz.**
