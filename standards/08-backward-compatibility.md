# Geriye Uyumluluk — API + DB Yalnız Eklemeli Evrilir

> **Neden bu kadar katı:** mobil kullanıcı eski sürümde takılı kalır, güncellemeyi
> günlerce/haftalarca yapmayabilir. Bugün kaldırılan bir alan, yarın binlerce
> cihazda çöken bir ekrandır. Web'de deploy anında herkes yeni sürümü alır; mobilde almaz.

## 1. Altın kural

- **Yeni alan** → nullable / opsiyonel / varsayılan değerli.
- **Devreden çıkan alan** → silinmez, nullable yapılır + obsolete işaretlenir.
- **Var olan alanın adı ve tipi asla değişmez.** Yeniden adlandırma = silme + ekleme = **yasak**.
- Değişiklik gerekiyorsa: **yeni alan eklenir**, eskisi obsolete akışına girer.

## 2. Kırıcı sayılan değişiklikler (tam liste)

| # | Değişiklik | Neden kırıcı |
|---|---|---|
| 1 | Alan/endpoint silme | Eski istemci bulamaz / null patlar |
| 2 | Alan/endpoint yeniden adlandırma | Silme + ekleme ile aynı |
| 3 | Tip değişikliği (`int`→`string`, `string`→`object`) | Parse hatası |
| 4 | Nullable → non-nullable (input) | Eski istemci alanı göndermiyor olabilir |
| 5 | Non-nullable → nullable (output) | Eski istemci null kontrolü yapmıyor |
| 6 | Yeni **zorunlu** input alanı | Eski istemcinin isteği 400 döner |
| 7 | Validasyon sıkılaştırma (`MaxLength` düşürme, yeni `Required`, yeni `UNIQUE`) | Önce geçen veri artık geçmez |
| 8 | Anlam/birim değişikliği (TL→kuruş, gün→saat, yerel→UTC) | Sessiz ve en tehlikeli tür |
| 9 | Enum değerinin **sayısal** karşılığını değiştirme / araya değer ekleme | Sıralama kayar |
| 10 | Hata/durum kodu sözleşmesi değişikliği | İstemci hata yolunu yanlış işler |
| 11 | Route / HTTP metod değişikliği | 404/405 |
| 12 | Global JSON serializer ayarı (casing, null handling, tarih formatı) | Tüm yanıtları birden değiştirir |
| 13 | SignalR/WebSocket hub metod adı veya payload şekli | Canlı bağlantılar kopar |
| 14 | Varsayılan davranış değişikliği (varsayılan sıralama, varsayılan `pageSize`) | Sessiz regresyon |
| 15 | Yetki sıkılaştırma (önce görülen bir kayıt artık 403) | Ürün kararı gerektirir, sessizce yapılmaz |

## 3. Obsolete yaşam döngüsü

```
1. AKTİF        → normal kullanım
2. OBSOLETE     → yeni alan eklendi; eski alan [Obsolete] + Swagger deprecated
                  ⚠ eski alan DOLU DÖNMEYE DEVAM EDER (null dönmek = silmek)
                  ⚠ eski input alanı yeni alana KÖPRÜLENİR (bridge)
3. İZLEME       → en az 4–8 hafta; erişim log'u ile gerçek kullanım ölçülür
4. DOĞRULAMA    → grep (tüm istemciler) + üretim log'u: kullanan kalmadı mı?
                  mobilde: eski sürüm kullanıcı sayısı ihmal edilebilir mi?
5. KALDIRMA     → ayrı bir deploy'da, önce koddan, SONRAKİ deploy'da DB'den (DROP)
```

**Obsolete ≠ işlevsiz.** Obsolete bir alan çalışmaya devam eder; yalnız yenisi tercih edilir.

## 4. Envanter tablosu (her projede tutulur)

`docs/backward-compatibility.md` veya proje CLAUDE.md'sinde:

| Alan/Endpoint | Obsolete tarihi | Yerine | Kaldırma koşulu | Durum |
|---|---|---|---|---|
| `Member.phone` | 2026-07-29 | `Member.phoneNumbers[]` | mobil ≤2.3 kullanıcısı %1 altına inince | İzlemede |

Envantere yazılmayan obsolete = unutulmuş obsolete.

## 5. Veritabanı: expand → migrate → contract

```
EXPAND    Yeni kolon/tablo eklenir (nullable, varsayılanlı). Eski kod çalışmaya devam eder.
          Yeni kod hem eskiyi hem yeniyi yazar (dual write) veya trigger/uygulama katmanı köprüler.
MIGRATE   Geriye dönük veri doldurulur (batch, üretimi kilitlemeden).
          Yeni kod yeniden okumaya başlar. Eski kolon hâlâ yazılıyor.
CONTRACT  Kullanılmadığı doğrulandıktan sonra, AYRI bir deploy'da eski kolon DROP edilir.
```

Kurallar:
- Migration **geri alınabilir** olmalı; `Down` yazılır veya geri alma planı belgelenir.
- `DROP` içeren migration öncesi **elle yedek** alınır ve **önce test ortamında** denenir.
- Büyük tabloda index oluşturma `CONCURRENTLY` (Postgres) — üretimi kilitleme.
- Tek migration'da hem şema hem büyük veri taşıma yapılmaz; ayrılır.
- `NOT NULL` eklemek: önce nullable + varsayılan doldur → sonra ayrı adımda `NOT NULL`.

## 6. İstemci tarafı savunma

- Enum `switch`'lerinde **her zaman `default` dalı** — sunucu yarın yeni değer gönderebilir.
- Bilinmeyen JSON alanları yok sayılır, hata vermez (strict deserialization kapalı).
- Yeni alanlar opsiyonel tiplenir; eksikse UI çökmez.
- Sunucu yanıtı beklenmedik şekildeyse ekran boş/hata durumu gösterir, uygulama kapanmaz.

## 7. Otomatik fren (CI'da taranır)

Merge kapısı şu kalıpları tarar ve `--allow-breaking` olmadan geçirmez:

- Silinen `public` üye, `[HttpGet/Post/Put/Delete]`, `[Route]` satırları
- Yeni `[Required]` / daraltılan `[MaxLength]` / yeni `[JsonIgnore]`
- Global serializer ayar değişikliği
- DDL'de yeni `NOT NULL` / `UNIQUE` / `CHECK`, `DROP COLUMN`, `ALTER TYPE`

**Otomatik tarama yakalayamaz** (elle review şart):
- Anlam/birim değişikliği
- Enum sayısal sıra kayması
- Hub payload içeriği
- Yetki sıkılaştırma
- Varsayılan değer/sıralama değişikliği

## 8. Kırıcı değişiklik gerçekten zorunluysa

1. ADR yaz: neden kaçınılmaz, alternatifler neden yetersiz.
2. Kullanıcı onayı al (bu bir **ürün kararıdır**, teknik karar değil).
3. Yeni versiyon (`/api/v2`) veya minimum istemci sürümü zorlaması ile yap.
4. Geçiş takvimi + istemci sürüm dağılımı ölçümü + geri dönüş planı yaz.
5. Eski yolu takvim boyunca **çalışır** tut.
