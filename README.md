# claude-code-standards

Claude Code ile üretim yazılımı geliştirirken kullandığım çalışma kuralları,
mühendislik standartları ve ajan rolleri. Örnek olsun diye yazılmadı — günlük
kullanımdaki hâlidir, kuralların çoğu bir şey kırıldıktan sonra eklendi.

| Ne | Nerede | Adet |
|---|---|---|
| Çalışma kuralları (her oturumda yüklenen indeks) | `CLAUDE.md` | 33 madde |
| Mühendislik standartları | `standards/` | 22 doküman + 5 şablon |
| Ajan rolleri (kapsamı ve yasakları tanımlı) | `agents/` | 14 rol |
| Çalışma modları (ajan + review + onay politikası) | `modes/` | 5 mod |
| Kapı ve ölçüm betikleri | `scripts/` | 7 betik |
| Slash komutları ve skill'ler | `commands/`, `skills/` | 5 |
| Karar defteri (her kuralın gerekçesi ve ölçümü) | `docs/kararlar.md` | — |

## Neden ölçüme dayanıyor

Kuralların arkasında tahmin değil sayı var. Karar defteri her maddenin nasıl
keşfedildiğini, hangi ölçümün onu doğurduğunu ve yürürlükten kalkmış hâllerini
tutar. Birkaç örnek:

| Ölçüm | Doğan kural |
|---|---|
| Kapsam ham **%95,0** raporlanıyordu; EF göçleri paydanın **%85'iydi**, çıkarılınca gerçek sayı **%83,0** | #29 — payda dürüstlüğü, kod tabanı başına %80 eşiği |
| 8 worker'lık e2e koşumu API istek sınırına takıldı → **48 sahte düşüş** ürün hatası sanıldı | #31 — önce tam koş, sonra sınıflandır, sonra düzelt |
| Ajan turları toplam maliyetin **%7,7'si**, tur başına ortalama **~$6,9**; maliyetin %73'ü orkestratörün cache okumasıydı | Mod sistemi (A–E) — sürtünme yerine peşin seçim |
| 9 ajan rolünden yalnız **1'i** gerçekten denetleniyordu; hata sessizce aşağı akıyordu | #28 — kanıt bloğu, geri gönderme, kapanış kanıtı |

Vaka çalışmaları: [`docs/vaka-01-kapsam-yanilsamasi.md`](docs/vaka-01-kapsam-yanilsamasi.md)

## Öne çıkan kurallar

- **Geriye uyumluluk zorunlu** — API ve DB yalnız eklemeli evrilir; alan/endpoint silinmez, adı ve tipi değişmez (#4)
- **Test kapsamı en az %80, her kod tabanı ayrı, ortalama alınmaz** — ölçülmemiş kod tabanı "geçti" sayılmaz (#29)
- **`dev`'e merge hızlıdır, ağır kapılar promosyonda koşar** — kalite kapısının yeri dışarı çıkan daldır (#25)
- **Yetki fail-closed** — varsayılan kapalı; "tanımlamayı unuttum = herkese açık" semantiği kurulmaz (#6)
- **Arama daima harf-boyutu ve aksan bağımsız** — "sisman" ↔ "Şişman", ham `LIKE`/`ToLower().Contains()` yasak (#13)
- **Koşmayan kapı geçilmiş sayılmaz** — atlanan adım "atlandı" diye raporlanır, sonuç yeşil olmaz (#19)
- **Yeni kural sözlü kalmaz** — kalıcı karar aynı turda dosyaya yazılır (#14)

## Kullanım

```bash
git clone https://github.com/<kullanıcı>/claude-code-standards
cp -r claude-code-standards/{CLAUDE.md,standards,agents,modes,commands,skills,scripts} ~/.claude/
cp claude-code-standards/settings.example.json ~/.claude/settings.json   # gözden geçirerek
```

Olduğu gibi almak zorunda değilsin — `standards/` dokümanları birbirinden
bağımsız okunur. Kuralların numaraları `CLAUDE.md` ile `docs/kararlar.md`
arasında bağlıdır, o yüzden numaraları koruyarak düzenle.

## Anonimleştirme

Kurallar gerçek müşteri projelerinde ölçüldü. Proje adları **Proje A / B / C**
olarak değiştirildi, **ölçüm sayıları olduğu gibi bırakıldı** — sayılar kuralın
gerekçesi, adlar değil.

## Burada bilerek OLMAYAN şeyler

- Müşteri/proje belleği, iş mantığı, veri şeması, prompt
- Sır, token, connection string, sunucu adı/IP
- Oturum transcript'i, konuşma geçmişi, üretilen artefaktlar
- Kişisel veri ve gerçek e-posta adresleri (`<hesap>+<etiket>@gmail.com` gibi yer tutucular kullanıldı)

Bu ayrım rastgele değil: ne yayınlanmayacağına dair kural setin kendisi
`standards/15-guvenlik.md` ve `standards/18-kurulum-ve-ortam.md` içinde.

## Lisans

MIT — `LICENSE`. Standartlar Türkçedir; kod içindeki isimler İngilizcedir
(kural: dil ayrımı `CLAUDE.md` başında).
