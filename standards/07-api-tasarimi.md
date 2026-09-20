# API Tasarımı — Tek Sözleşme, İki İstemci

## 1. Temel ilke

**Tek API; web ve mobil aynı sözleşmeyi tüketir.** Platforma özel endpoint açılmaz.
İstemciler farklı alanlar gösterebilir ama aynı yanıtı alır.

Bunun sonuçları:
- Yanıt **her istemcinin ihtiyacını karşılayacak kadar zengin**, ama gereksiz veri taşımayacak kadar dar olmalı.
- İstemciye özel varyasyon gerekiyorsa: aynı endpoint + opsiyonel `?include=` / `?fields=` parametresi. Yeni endpoint değil.
- Sözleşme değişikliği **iki istemciyi birden** etkiler; mobil eski sürümde takılı kalabilir → `08-geriye-uyumluluk.md` zorunlu okuma.

## 2. Kaynak ve URL

- Çoğul isim, küçük harf, kebab-case: `/api/members`, `/api/work-orders`.
- Fiil URL'de olmaz; HTTP metodu fiildir. İstisna: gerçek aksiyonlar → `POST /api/orders/{id}/cancel`.
- Hiyerarşi 2 seviyeyi geçmez: `/api/members/{id}/orders` tamam, daha derini query param.
- Kaynak id'si `{id}` path'te; filtre/sıralama/sayfalama query'de.

| Metod | Anlam | Idempotent |
|---|---|---|
| GET | Okuma, yan etkisiz | ✅ |
| POST | Oluşturma / aksiyon | ❌ |
| PUT | Tam değiştirme | ✅ |
| PATCH | Kısmi güncelleme | ✅ (öyle tasarlanmalı) |
| DELETE | Silme | ✅ |

## 3. Durum kodları

| Kod | Ne zaman |
|---|---|
| 200 | Başarılı okuma/güncelleme |
| 201 | Oluşturuldu (+ `Location` header + oluşan kayıt) |
| 202 | Kabul edildi, asenkron işlenecek (+ durum sorgulama linki) |
| 204 | Başarılı, gövde yok (DELETE) |
| 400 | Şekilsel/validasyon hatası |
| 401 | Kimlik yok/geçersiz |
| 403 | Kimlik var, yetki yok |
| 404 | Kaynak yok **veya** kullanıcı görmemeli (bilgi sızdırmamak için) |
| 409 | Çakışma (eşzamanlı değişiklik, tekrarlı kayıt) |
| 422 | Şekil doğru ama iş kuralı ihlali |
| 429 | Hız limiti (+ `Retry-After`) |
| 5xx | Sunucu hatası — istemci tekrar deneyebilir |

## 4. Hata formatı — tek biçim

RFC 7807 ProblemDetails:

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Doğrulama hatası",
  "status": 400,
  "detail": "Gönderilen alanlardan bazıları geçersiz.",
  "traceId": "00-8f3c...-01",
  "errors": { "email": ["Geçerli bir e-posta girin."] }
}
```

- Her hata yanıtında **`traceId`** bulunur — kullanıcı destek talebinde bunu verir, log'da bulunur.
- Hata metni kullanıcıya gösterilebilir olmalı; teknik detay/stack trace **asla**.
- İstemci hataları **kod** ile ayırt edebilmeli (`type` veya `errorCode`), metinle değil (metin i18n ile değişir).

## 5. Sayfalama, filtreleme, sıralama

- **Sayfalamasız liste endpoint'i yasak.** Varsayılan `pageSize=20`, üst sınır `100` (sunucu zorlar).
- Standart yanıt zarfı:

```json
{ "items": [...], "page": 1, "pageSize": 20, "totalCount": 137, "totalPages": 7 }
```

- Çok büyük/sürekli akan veri için cursor tabanlı sayfalama (`?after=<cursor>`) tercih edilir.
- Filtre: `?status=active&departmentId=3`. Sıralama: `?sort=createdAt:desc`. Beyaz liste ile doğrulanır (SQL injection ve indexsiz sıralama riski).
- Arama: `?q=...` — **harf boyutu ve aksan bağımsız** (global kural #13).

## 6. Sözleşme detayları

- Tarih/saat: **ISO-8601 UTC** (`2026-07-29T10:15:00Z`). Yerel format yalnız gösterimde.
- Para: tutar + para birimi ayrı alan; `decimal`/string, float değil.
- Enum: **string** olarak taşınır (`"Active"`), sayı değil — sayı sıralama değişince sessizce bozulur.
- Boolean alan adı `is/has/can` ile.
- Null vs eksik alan farkı bilinçli: PATCH'te "alanı temizle" ile "dokunma" ayrımı netleşmeli (JSON Merge Patch veya explicit `null` semantiği yazılır).
- Alan adları `camelCase`, tüm API'de tutarlı. Serializer ayarı **global** ve değiştirilmesi kırıcıdır.

## 7. Idempotency

- `POST` ile yaratılan ve tekrar edilmemesi gereken işlemler (sipariş, ödeme, bildirim) `Idempotency-Key` header'ı kabul eder.
- Aynı anahtarla gelen ikinci istek **aynı sonucu** döner, ikinci kayıt yaratmaz.
- Mobil offline kuyruğu ve retry mekanizmaları bu olmadan güvenli değildir.

## 8. Eşzamanlılık

- Güncellemede kayıp yazma (lost update) riski varsa `ETag` + `If-Match` veya `rowVersion` alanı.
- Çakışma → `409` + hangi alanın değiştiği bilgisi.

## 9. Auth

- Bearer JWT (kısa ömürlü access + refresh) veya httpOnly cookie. Karışık kullanılmaz; her istemci aynı akışı kullanır.
- Token'da yalnız kimlik + kaba rol; **yetki kararı sunucuda** verilir (token'daki claim'e körü körüne güvenilmez).
- Yenileme akışı tek yerde; eşzamanlı 401'lerde tek yenileme.
- Detay: `15-guvenlik.md`.

## 10. Dokümantasyon

- OpenAPI/Swagger **kod ile birlikte** güncellenir; PR'da eksikse review'da bloke edilir.
- Her endpoint: ne yapar, hangi yetki gerekir, hangi hataları döner, örnek istek/yanıt.
- Deprecated endpoint/alan Swagger'da `deprecated` işaretlenir + yerine ne kullanılacağı yazılır.

## 11. Versiyonlama

- Tercih: **versiyonsuz + additive evrim** (`08-geriye-uyumluluk.md`). Bu neredeyse her zaman yeterlidir.
- Gerçekten kaçınılmaz bir kırılma varsa `/api/v2/...` açılır ve **v1 en az 6 ay + tüm mobil sürümler emekliye ayrılana dek** yaşar.
- Versiyon açmak bir ADR gerektirir.

## 12. Hız limiti ve boyut

- Kimlik başına hız limiti; aşımda `429` + `Retry-After`.
- İstek gövdesi boyut sınırı; dosya yükleme ayrı endpoint + streaming.
- Toplu (bulk) endpoint'lerde üst sınır tanımlı ve belgeli.

## 13. Yapma listesi

- ❌ Platforma özel endpoint (`/api/mobile/...`)
- ❌ Sayfalamasız liste
- ❌ Entity'yi doğrudan döndürmek
- ❌ Hata için `200 + {success:false}` dönmek
- ❌ Enum'u sayı olarak taşımak
- ❌ Alan/endpoint silmek veya yeniden adlandırmak
- ❌ Global serializer ayarını değiştirmek (tüm istemcileri kırar)
- ❌ Yetkiyi yalnız token claim'ine bakarak vermek
- ❌ GET ile yan etki yaratmak
