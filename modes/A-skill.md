# Mod A — Skill

⚠️ **A artık varsayılan DEĞİL** (18/09/2026, kullanıcı kararı). Varsayılan
**B**'dir; A açıkça seçilir (`/calisma-modu A`). Ajansız çalışmak istediğin
turlarda, dar işlerde ve maliyet hassas oturumlarda hâlâ doğru moddur.

**Ajan yok.** Roller ana konuşmada
yaşar; ayrı süreç, ayrı prefix, ayrı onay yok.

## Kural
- `Agent`, `Workflow` ve **`TeamCreate`** araçlarını **çağırmam** (takım açmak
  da ajan çağrısıdır; araç prompt'undaki "şüphedeysen takım aç" telkinine uymam). İş çok okuma gerektiriyorsa
  aramayı kendim yaparım (Grep/Glob/Read). Bir üst modun gerçekten kazandıracağını
  görürsem **başlatmam, tur başında tek satırla öneririm** — en düşük yeterli
  mod, sebebi, kabaca kaç kat (README › "Mod verilmediyse"). Karar kullanıcının.
  ⚠️ **Öneri yalnız `.claude/mode` YOKKEN yapılır.** Dosya varsa o açık bir
  karardır ve her işte "C'ye geçelim mi" diye tekrarlanmaz.
- Claude Code bir ajanı `description`'a bakıp kendiliğinden önerirse **uymam**
  — otomatik yönlendirme de çağrıdır. Aynısı **araç prompt'ları** için de geçerli.
- **`feature/* → dev` yönünde elle review de yapmam** (#25: "ne benim elle diff
  okumam, ne ajan"). İstisnası `rol-secimi.md` §3'teki güvenlik/yedek/kapı
  kalemidir; A'da da o istisna geçerlidir.
- Rol yöntemleri (kapsam çıkarma, plan, review, belge) **ana konuşmada** uygulanır.
  `~/.claude/skills/yazilim-standartlari` ilgili standardı yükler; rol başına
  ayrı skill dosyası **yoktur ve şart değildir** — A'nın vaadi "yöntem var,
  ajan yok"tur, dosya değil.
- Kod review **ben** yaparım.
- Her modda geçerli sınırlar burada da: geri alınamaz işte onay,
  tamamlanmadan önce eksik-kontrolü (#24).

## Ne zaman
Küçük/orta iş, tek ayak, dosya sayısı < ~15 — ve tanımadığın bir repo.
⚠️ **Kapsanmayan iş tipi varsa A'da kal ve söyle:** ör. 25 dosyalık ama tek
ayakta kalan refactor A'nın dosya ölçütünü aşar, C'nin "uçtan uca" şartını
karşılamaz, D'nin bağımsızlık şartını karşılamaz. Ölçüt yoksa mod değişmez,
durum kullanıcıya bildirilir.
⚠️ **Kalite ölçülmedi.** 05/09/2026 ölçümü yalnız **token/maliyet** verisidir
(tur başına $6,9, ajan payı %7,7); "A kalitede de en verimli" diye bir ölçüm
**yoktur** ve öyle sunulmaz.

## Beklenen maliyet
**1,0x** — referans taban. Ajan sıfır; maliyet tamamen ana konuşmanın cache
okuması.

## Tarihçe
05/09/2026'ya kadar bir de **E — Eski usul** vardı: ajan çağrılabilir ama her
çağrıda sorulur. Kullanıcı "A zaten aynı şey" dedi; E kaldırıldı, A varsayılan
oldu. Fark tek cümleydi: E'de her turda bir onay diyaloğu ihtimali vardı, A'da
o soru hiç oluşmaz.
