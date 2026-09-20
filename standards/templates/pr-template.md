## Ne / Neden

<Bir paragraf: hangi problem, neden bu çözüm. Ticket/issue linki.>

## Değişiklikler

- <dosya/modül> — <ne değişti>
- ...

## Nasıl test edildi

```bash
# koşulan komutlar ve sonuçları
dotnet test        # 142 passed
npm run test       # 87 passed
npm run e2e        # 18 passed
```

- [ ] Mutlu yol denendi
- [ ] Hata yolu denendi (<hangisi>)
- [ ] Yetkisiz erişim denendi

## Ekran görüntüsü (UI değişikliği varsa)

| Öncesi | Sonrası |
|---|---|
| | |

## Geriye uyumluluk etkisi — **zorunlu alan**

- [ ] Alan/endpoint **silinmedi**, adı/tipi **değişmedi**
- [ ] Yeni input alanı **opsiyonel**
- [ ] Yeni DB kolonu **nullable**
- [ ] Validasyon **sıkılaştırılmadı** (yeni `Required`/`UNIQUE`/daraltılmış `MaxLength` yok)
- [ ] Enum sayısal sıralaması korundu
- [ ] Global serializer / route / hub payload değişmedi
- [ ] **Mobilin eski sürümü bu değişiklikle çalışır**

Etki varsa açıkla: <...>

## Veritabanı / migration

- [ ] Migration yok
- [ ] Migration var → geri alınabilir mi: <evet/hayır, nasıl>
- [ ] `DROP` içeriyor mu: <hayır / evet → yedek alındı, test ortamında denendi>

## Konfigürasyon / sır

- [ ] Yeni env değişkeni yok
- [ ] Var → `.env.example` **ve** `SETUP.md` sır envanteri güncellendi

## Güvenlik

- [ ] Yeni endpoint yetkilendirildi (kaynak sahipliği dahil)
- [ ] Girdi doğrulanıyor
- [ ] Log'a PII/token sızmıyor

## Rollback

<Bu değişiklik sorun çıkarırsa nasıl geri alınır? Feature flag var mı?>

## Doküman

- [ ] Swagger/OpenAPI güncel
- [ ] `CLAUDE.md` / `docs/` güncel
- [ ] Yeni kalıcı kural varsa MD'ye yazıldı
