# UI / UX Tasarım Standartları

## 1. Tasarım tokenları — tek kaynak

Renk, tipografi, boşluk, radius, gölge, z-index, breakpoint **tek dosyada** tanımlanır
(CSS değişkeni / theme objesi). Bileşen içinde ham `#3b82f6`, `13px`, `margin: 7px` yazılmaz.

- Boşluk ölçeği: 4px tabanlı (4, 8, 12, 16, 24, 32, 48, 64). Ara değer icat edilmez.
- Tipografi ölçeği en fazla 6 basamak. Her basamağın satır yüksekliği tanımlı.
- Renk **rolü** ile isimlendirilir (`--color-danger`), tonu ile değil (`--color-red-500` yalnız palet katmanında).
- z-index yalnız tanımlı katmanlardan seçilir (base / dropdown / sticky / modal / toast).

## 2. Bileşen disiplini

- Bileşen **tek iş** yapar. 300 satırı geçen bileşen bölünür (modal, satır renderer, form, filtre bar).
- Sunum (presentational) ve veri (container) sorumlulukları ayrılır: veri çeken bileşen JSX ağacını da yönetmez.
- Prop sayısı 7'yi geçtiyse ya obje grupla ya bileşeni böl.
- Ortak bileşen (`Button`, `Input`, `Modal`, `Table`, `EmptyState`) **bir kez** yazılır; sayfa içinde yeniden icat edilmez.
- Varyantlar prop ile (`variant="danger"`), kopyala-yapıştır bileşenle değil.

## 3. Her ekran 5 durumu tasarlar

| Durum | Gereklilik |
|---|---|
| **Loading** | Skeleton veya spinner; layout zıplaması olmaz (yer tutucu aynı boyutta) |
| **Boş** | Açıklayıcı metin + birincil eylem ("Henüz kayıt yok — İlk kaydı ekle") |
| **Hata** | İnsan dilinde ne oldu + ne yapmalı + tekrar dene butonu. Stack trace gösterilmez |
| **Kısmi/uzun** | Çok uzun metin, çok fazla kayıt, çok uzun isim → taşma kontrolü, `text-overflow` |
| **Başarı** | Geri bildirim (toast/inline). Sessiz başarı yok |

Eksik durum tasarımı = eksik özellik.

## 4. Form kuralları

- Etiket her zaman görünür (`placeholder` etiket yerine geçmez).
- Validasyon **blur'da veya submit'te**, her tuş vuruşunda değil; hata düzeltilirken anlık temizlenir.
- Hata mesajı alanın **hemen altında**, ne yapılacağını söyler ("Telefon 10 hane olmalı", "Geçersiz" değil).
- Submit sırasında buton disabled + yükleniyor göstergesi → çift gönderim engellenir.
- Kaydedilmemiş değişiklik varken sayfadan çıkışta uyarı.
- Zorunlu alan işareti tutarlı; opsiyonel alan da açıkça belirtilebilir.
- Klavye ile baştan sona doldurulabilir olmalı (tab sırası mantıklı).

## 5. Navigasyon ve URL

- Uygulama durumu **URL'de yaşar**: sekme, filtre, sayfa no, arama terimi query param'da. Sayfa yenilenince kaybolmaz.
- Geri tuşu beklendiği gibi çalışır. Modal açılışı history'yi kirletmez (ya da bilinçli olarak kirletir ve geri tuşu modalı kapatır).
- Derin link her ekrana mümkün olmalı (mobilde de — `06-mobil.md`).
- Yetkisiz sayfaya girişte 403 ekranı; boş sayfa veya sonsuz spinner değil.

## 6. Responsive

- Mobile-first yazılır. Breakpoint sayısı az (sm/md/lg/xl), token'dan gelir.
- Dokunma hedefi min 44×44px. Hover'a bağlı tek yol yok (mobilde hover yok).
- Tablo dar ekranda ya yatay kaydırılır (kendi container'ında) ya kart listesine dönüşür. **Sayfa gövdesi yatay kaymaz.**
- Görsel `max-width: 100%`; sabit piksel genişlik yok.

## 7. Erişilebilirlik (WCAG 2.1 AA — minimum)

- [ ] Semantik HTML: `button` tıklanır, `div onClick` değil. Başlık hiyerarşisi atlanmaz (h1→h2→h3).
- [ ] Her form alanının `label`'ı var (`htmlFor`/`id` eşleşmesi).
- [ ] Kontrast: normal metin 4.5:1, büyük metin 3:1, ikon/kenarlık 3:1.
- [ ] Klavye ile tüm işlevlere erişilebilir; focus göstergesi görünür (`outline: none` tek başına yasak).
- [ ] Modal açıldığında focus içeri hapsolur, kapanınca tetikleyene döner; `Esc` kapatır.
- [ ] Sadece renkle bilgi verilmez (hata = kırmızı + ikon + metin).
- [ ] Görsellerde anlamlı `alt`; dekoratifse `alt=""`.
- [ ] Dinamik içerik değişimi `aria-live` ile duyurulur (toast, arama sonucu sayısı).
- [ ] `prefers-reduced-motion` saygı görür.

## 8. Metin ve i18n

- Kullanıcıya görünen hiçbir string koda gömülmez → i18n anahtarı. Varsayılan `tr`, ikincil `en`.
- Anahtar isimlendirmesi alan bazlı: `members.list.emptyTitle`.
- Çoğul, tarih, sayı, para formatı kütüphaneye bırakılır — elle `+ " adet"` birleştirilmez.
- Metin tonu: kısa, doğrudan, suçlayıcı değil. "Hata oluştu" yerine "Kaydedilemedi — bağlantıyı kontrol edip tekrar deneyin".
- Tarih gösterimi **`dd/mm/yyyy`** (global kural). Saat 24 saat formatı.

## 9. Motion

- Süre 150–300ms; giriş çıkıştan biraz yavaş.
- Yalnız `transform` ve `opacity` animasyonu (layout tetikleyen özellik animasyonu yok).
- Animasyon bilgi taşır (nereden geldi, nereye gitti); dekorasyon için animasyon eklenmez.

## 10. Dark mode

- Renkler token üzerinden; `@media (prefers-color-scheme)` + kullanıcı tercihi override'ı.
- Sabit beyaz/siyah değer gömülmez. Görsel ve gölge dark'ta ayrıca kontrol edilir.

## 11. Tasarım gözden geçirme sorusu

Ekran bittiğinde sor: *"Bu ekranı ilk kez gören biri, ne yapması gerektiğini 5 saniyede anlar mı?"*
Anlamıyorsa hiyerarşi (birincil eylem tek ve belirgin), boşluk ve metin gözden geçirilir.
