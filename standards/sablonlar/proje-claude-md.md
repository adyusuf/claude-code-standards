# <Proje Adı> — Claude Code Rehberi

> Bu dosya Claude Code'un her oturumda otomatik okuduğu ana giriş noktasıdır.
> **Kısa tut** (hedef < 200 satır). Detayı `docs/` klasörüne ve alt dizinlerin
> kendi `CLAUDE.md` dosyalarına bırak.
> Genel yazılım standartları `~/.claude/standards/` altında — burada **yalnız
> bu projeye özel** olanlar yazılır. Buradaki kural genel standardı ezer.

## Proje tek cümlede

<Ne yapar, kim için, hangi problemi çözer — bir cümle.>

## Temel ilkeler (proje DNA'sı)

- **<İlke>.** <Bir cümle açıklama ve sonucu.>
- **<İlke>.** ...

## Mimari

- **`backend/`** — <teknoloji>, <veritabanı>. Port `<port>`.
- **`web/`** — <teknoloji>. Port `<port>`.
- **`mobile/`** — <teknoloji>.

İstemciler yalnız API'yi tüketir. İş mantığı **asla** istemcide yapılmaz.

### Hangi API / hangi ortam

| Durum | URL |
|---|---|
| Local API | `http://localhost:<port>` |
| Test | `https://<test-domain>` |
| Prod | `https://<prod-domain>` |
| Swagger (yalnız test) | `https://<test-domain>/swagger` |

Topoloji: <tek origin mi (`/api` UI'ın altında) yoksa ayrı alt alan adı mı — ve neden>

## Kurulum

Sıfırdan kurulum: **`SETUP.md`**. Sır envanteri, ön koşullar ve port haritası orada.
Deploy ve sunucu: **`DEPLOY.md`**.

## Branch ve deploy akışı

```
özellik dalı → dev → (onay) → test → (onay) → prod
```

- `test`/`prod`'a doğrudan commit/PR **yok**; yalnız bir önceki aşamadan, **kullanıcı onayıyla**.
- "merge" komutu = <bu projede ne anlama geliyor, hangi script çalışır>
- Kapı (build + test + format + lint + geriye uyumluluk taraması) geçilmeden merge yok.

## Bağlam yönlendirmesi

| Görev türü | Önce oku |
|---|---|
| Backend endpoint / servis / migration | `backend/CLAUDE.md` |
| Web sayfa / bileşen / stil | `web/CLAUDE.md` |
| Mobil ekran / navigation | `mobile/CLAUDE.md` |
| Yeni özellik (uçtan uca) | `docs/vizyon.md`, `docs/isterler.md` |
| Domain / iş mantığı sorusu | `docs/moduller/<modul>.md` |

## Modüller

1. **<Modül>** — <bir satır>
2. ...

> ⚠️ **KALDIRILAN MODÜLLER:** <varsa — yeniden eklenmesin diye>

## Projeye özel kurallar

> Genel kurallar `~/.claude/CLAUDE.md`'de. Burada **yalnız farklı olanlar**.

1. **<Kural>.** <Neden — neden yazılmayan kural sonra yanlışlıkla geri alınır.> (<Tarih>, KALICI)
2. ...

## Yapma listesi

- ❌ <Bu projede özellikle yasak olan şey ve nedeni>
- ❌ ...

## Geriye uyumluluk envanteri

| Alan/Endpoint | Obsolete tarihi | Yerine | Kaldırma koşulu | Durum |
|---|---|---|---|---|
| | | | | |

## Otomasyon

`.claude/settings.json` hook'ları:
- `<hook>` — <ne yapar>

## Hızlı referans

- Kurulum: `SETUP.md`
- Deploy / sunucu / DNS / sertifika: `DEPLOY.md`
- Yedekleme provaları: `docs/yedekleme-provalari.md`
- Vizyon / isterler: `docs/vizyon.md`, `docs/isterler.md`
- Sözlük (TR-EN): `docs/sozluk.md`
- Kararlar: `docs/adr/`
