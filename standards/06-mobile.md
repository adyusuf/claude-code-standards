# Mobil Standartları (React Native / Expo)

## 1. Temel ilke: tek API, iki istemci

- Mobil ve web **aynı** endpoint'leri tüketir. `/api/mobile/*` gibi platforma özel API açılmaz.
- Fark UI/UX katmanında çözülür: mobil daha az alan gösterebilir, farklı sıralayabilir; **veri sözleşmesi aynıdır**.
- Mobil istemci mağazada eski sürümde takılı kalabilir → **API geriye uyumluluğu mobilde hayati**. Bkz. `08-backward-compatibility.md`.
- Ortak mantık (tarih formatı, arama normalizasyonu, yetki yardımcıları, i18n anahtarları) web ile **aynı davranışa** sahip olmalı; mümkünse paylaşılan pakette.

## 2. Yapı ve config

```
src/
  api/client.ts   → TEK kaynak: BASE_URL, SIGNALR_URL, WEB_URL, timeout, interceptor
  screens/        → ekranlar
  components/     → paylaşılan bileşenler
  navigation/     → navigator tanımları
  hooks/ lib/ i18n/
```

- Hard-coded URL/IP/port **yasak** — `api/client.ts`. Fallback yalnız DEV, tek noktada.
- Ortam ayrımı `app.config.ts` + EAS profilleri (`development` / `preview` / `production`) ile.
- Sırlar bundle'a gömülmez — mobil bundle **açılabilir**; istemci tarafında gerçek sır yoktur.

## 3. Navigasyon

- Tip güvenli navigation (typed param list). String route adı serbest yazılmaz.
- **Deep link / universal link** her ana ekrana tanımlı; web URL'iyle eşleşir.
- Geri tuşu (Android donanım) her ekranda beklendiği gibi davranır; modal'da kapatır.
- Derin stack yerine tab + stack kombinasyonu; kullanıcı 3 dokunuşta ana ekrana dönebilmeli.

## 4. Liste ve performans

- Uzun liste `FlatList`/`FlashList` — `ScrollView` içinde `map` **yasak**.
- `keyExtractor` kararlı id ile; satır bileşeni `memo`'lu ve saf.
- `getItemLayout` mümkünse verilir; `initialNumToRender` ayarlanır.
- Görseller boyutlandırılmış + cache'li (`expo-image`).
- Ağır iş JS thread'ini bloklamaz; animasyonlar Reanimated ile UI thread'inde.
- Uygulama açılış süresi ölçülür; splash arkasında gereksiz senkron iş yapılmaz.

## 5. Ağ ve offline

- Her istekte timeout + iptal.
- Bağlantı yokken: net "çevrimdışısınız" durumu + tekrar dene. Sonsuz spinner yasak.
- Kritik listeler için cache-first + arka planda tazeleme.
- Yazma işlemleri çevrimdışıyken kuyruğa alınacaksa **idempotency key** ile gönderilir (`07-api-design.md`).
- Token yenileme tek yerde (interceptor), eşzamanlı 401'lerde tek yenileme (mutex).

## 6. Depolama

- Token / hassas veri → `expo-secure-store` (Keychain/Keystore). `AsyncStorage`'a token yazılmaz.
- `AsyncStorage` yalnız hassas olmayan tercih/cache için.
- Çıkışta (logout) tüm yerel veri temizlenir.

## 7. İzinler ve platform farkları

- İzin **kullanıldığı anda** ve nedeni açıklanarak istenir (açılışta toplu izin isteme).
- İzin reddedilirse uygulama çalışmaya devam eder (bozulmuş ekran değil, açıklayıcı durum).
- iOS/Android farkları (`Platform.select`) tek yerde toplanır, ekranlara serpiştirilmez.
- Safe area her ekranda hesaba katılır; notch/gesture bar'ın altına içerik konmaz.
- Klavye açıldığında input görünür kalır (`KeyboardAvoidingView` / `keyboardVerticalOffset`).

## 8. Erişilebilirlik

- `accessibilityLabel` + `accessibilityRole` etkileşimli her öğede.
- Dokunma hedefi min 44×44.
- Dinamik font boyutuna (kullanıcı ayarı) dayanıklı layout — sabit yükseklikli metin kutusu yok.

## 9. Sürüm ve yayın

- Sürümleme: `version` (kullanıcıya görünen) + `buildNumber`/`versionCode` (her yüklemede artar).
- Yayın öncesi checklist:
  - [ ] Sürüm/build numarası arttı
  - [ ] Değişiklikler eski API ile uyumlu (eski sürüm kullanıcıları kırılmıyor)
  - [ ] Crash raporlama açık ve yeni sürüm etiketiyle
  - [ ] Store metinleri + ekran görüntüleri güncel
  - [ ] İzin açıklama metinleri (`NSCameraUsageDescription` vb.) doğru
  - [ ] Gizlilik/veri toplama beyanı (App Privacy / Data Safety) doğru
  - [ ] Maestro e2e smoke geçti (`12-maestro.md`)
- Build formatı: mağaza yüklemesi **AAB** (Android) / **IPA** (iOS); cihaza kurulum için APK ayrı bir istektir.
- Ağır build'ler **sıralı** çalıştırılır (paralel Gradle/Kotlin derlemesi OOM riski).
- OTA güncelleme (EAS Update) yalnız JS değişikliklerinde; native değişiklik store sürümü gerektirir. OTA kanalı ile store sürümü eşleştirilir.

## 10. Zorunlu güncelleme stratejisi

- API, desteklenen minimum istemci sürümünü bildirebilmeli (header veya `/config` endpoint'i).
- Desteklenmeyen sürümde uygulama "güncelleyin" ekranı gösterir — sessizce hata vermez.
- Bu mekanizma **kırıcı değişiklik lisansı değildir**: yine de additive evrim esastır.

## 11. Yapma listesi

- ❌ Platforma özel API endpoint'i açmak
- ❌ `ScrollView` + `map` ile uzun liste
- ❌ Token'ı `AsyncStorage`/bundle'da tutmak
- ❌ Sabit piksel ile ekran yerleşimi (cihaz çeşitliliği)
- ❌ Açılışta tüm izinleri istemek
- ❌ Native modül eklemeden önce onay almamak (Expo managed'dan çıkma kararı ADR gerektirir)
