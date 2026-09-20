# Performans Standartları

## 1. Önce ölç

- **Ölçmeden optimize etme.** Tahmine dayalı optimizasyon kodu karmaşıklaştırır, sorunu çözmez.
- Yavaşlık raporu geldiğinde: hangi endpoint/ekran, hangi veri boyutu, hangi kullanıcı, ne kadar sürüyor, ne bekleniyor.
- Profil araçları: sunucuda APM/trace, DB'de `EXPLAIN ANALYZE`, tarayıcıda DevTools Performance + Lighthouse.

## 2. Bütçeler (aşılırsa iş yapılır)

| Metrik | Hedef |
|---|---|
| API p95 (basit okuma) | < 200 ms |
| API p95 (liste/rapor) | < 500 ms |
| API p99 | < 1 s |
| LCP (web, 4G) | < 2.5 s |
| INP | < 200 ms |
| CLS | < 0.1 |
| İlk JS bundle (gzip) | < 250 KB |
| Mobil soğuk açılış | < 3 s |
| CI hızlı kapı | < 10 dk |

Bütçe aşımı bir **hatadır**, "sonra bakarız" değil.

## 3. Veritabanı (en sık kaynak)

- **N+1** — en yaygın sorun. Loop içinde sorgu yok; `Include`/projeksiyon.
- `SELECT *` yok; yalnız gereken kolonlar → DTO projeksiyonu.
- Sayfalama zorunlu; derin `OFFSET` yerine keyset/cursor.
- Index: sık filtre/sıralama kolonlarına. Eksik index'i `EXPLAIN` gösterir.
- Sayım (`COUNT`) pahalıdır — sonsuz kaydırmada toplam sayı gerekmiyorsa hesaplama.
- Okuma ağırlıklı sistemde read replica düşünülür.
- Uzun sorgulara `statement_timeout`.

## 4. Cache — katman katman

| Katman | Ne için | Dikkat |
|---|---|---|
| Tarayıcı/CDN | Statik varlıklar | Uzun `max-age` + içerik hash'li dosya adı |
| Edge (Cloudflare) | Statik + nadiren değişen GET | `19-cloudflare-ve-edge.md` |
| Uygulama (memory/Redis) | Hesaplaması pahalı, sık okunan | **Invalidasyon planı olmadan cache yok** |
| DB | Sorgu planı, materialized view | Tazelik stratejisi |

- Her cache'in **TTL'i ve invalidasyon yolu** yazılır. "Ne zaman bayatlar, kim temizler?" cevapsızsa cache eklenmez.
- Kullanıcıya özel veri edge'de cache'lenmez (`Cache-Control: private`). Yetkiye göre değişen yanıt paylaşılan cache'e girmez — **veri sızıntısı riski**.
- Cache anahtarına tenant/kullanıcı/dil boyutu dahil edilir.
- Cache stampede'e karşı jitter + tekil yeniden hesaplama (lock).

## 5. Backend

- Async I/O; senkron bloklama yok (thread havuzu tükenir).
- Response compression (Brotli/gzip).
- Büyük yanıt → sayfalama veya streaming (`IAsyncEnumerable`).
- Sıcak yolda gereksiz allocation, gereksiz `ToList()`, gereksiz serialization.
- Toplu iş: tek tek yerine batch; `SaveChanges` döngüsü yok.
- Dış servis çağrısı: timeout + circuit breaker; yavaş bağımlılık tüm sistemi yavaşlatmasın.
- Pahalı rapor/export → arka plan işi + `202` + durum sorgulama.

## 6. Frontend

- Route bazlı code splitting; ağır kütüphane lazy import.
- Bundle analizi düzenli yapılır; büyük bağımlılık gerekçelendirilir (moment→date-fns, lodash→tekil import).
- Uzun liste sanallaştırma veya sayfalama.
- Görsel: doğru boyut, modern format (WebP/AVIF), `loading="lazy"`, `width/height` verilerek CLS önlenir.
- Font: `font-display: swap`, preload, subset.
- Gereksiz render: önce doğru state yerleşimi, sonra memo. Context'e sık değişen değer koyma.
- Üçüncü taraf script'ler (analytics, chat) defer/async ve gerekçeli — her biri bütçeden yer alır.

## 7. Mobil

- `FlatList`/`FlashList`; `ScrollView`+`map` yasak.
- Görsel cache'li ve boyutlandırılmış (`expo-image`).
- Animasyon Reanimated ile UI thread'inde.
- Açılışta senkron ağır iş yok; ekran ihtiyaç duydukça veri çeker.
- Ağ isteği sayısı azaltılır — mobil ağ gecikmesi yüksektir; 5 küçük istek yerine 1 birleşik yanıt (ama endpoint çoğaltmadan, `?include=` ile).

## 8. Yük ve dayanıklılık testi

- Kritik endpoint'ler için k6/JMeter senaryosu: beklenen yük, 2× yük, kırılma noktası.
- Ölçülen: p95/p99, hata oranı, doygunluk (CPU/bellek/bağlantı havuzu).
- Sürüm öncesi veya haftalık koşulur; sonuç kaydedilir ve **trend** izlenir.
- Bağlantı havuzu, thread havuzu ve DB `max_connections` uyumlu ayarlanır.

## 9. Performans regresyonunu yakalama

- CI'da bundle boyutu eşiği (aşarsa uyarı/bloke).
- Üretimde p95 latency ve hata oranı dashboard'da; eşik aşımı alarm (`17-gozlemlenebilirlik.md`).
- Yeni özellik sonrası ilk 24 saat metrikler izlenir.

## 10. Yapma listesi

- ❌ Ölçmeden optimize etmek
- ❌ N+1, `SELECT *`, sayfalamasız liste
- ❌ İnvalidasyon planı olmayan cache
- ❌ Kullanıcıya özel veriyi paylaşılan cache'e koymak
- ❌ Senkron bloklama (`.Result`, `.Wait()`)
- ❌ Tek fonksiyon için ağır kütüphane eklemek
- ❌ Sanallaştırmasız 1000 satırlık liste
- ❌ Performans için doğruluğu feda etmek (yarış koşulu, eksik kilit)
