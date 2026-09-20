# Maestro — Mobil E2E Standartları

## 1. Kapsam

Mobil e2e web'den **daha da pahalıdır** (emülatör, build, cihaz farkı). Yalnız:

- Açılış + giriş + ana akış (smoke): uygulama açılıyor mu, giriş çalışıyor mu, ana liste geliyor mu
- Kritik iş akışı (sipariş verme, form gönderme, bildirim açma)
- Store yayını öncesi kontrol edilen çekirdek senaryolar

Hedef: **5–15 flow**, toplam koşum 10 dk altı. Her ekranı e2e ile test etme.

## 2. Flow yapısı

```
.maestro/
  config.yaml
  flows/
    00-launch.yaml        → uygulama açılıyor, splash geçiyor, çökme yok
    01-login.yaml         → giriş
    02-members-list.yaml  → liste yükleniyor, boş durum, hata durumu
    03-create-order.yaml  → kritik akış
  subflows/
    login.yaml            → runFlow ile tekrar kullanılan parçalar
```

- Tekrarlanan adımlar `runFlow` ile subflow'a çıkarılır (giriş, çıkış, seed).
- Her flow **bağımsız** başlar (`launchApp: clearState: true`) — önceki flow'un bıraktığı duruma güvenilmez.
- Flow adı ne test ettiğini söyler, numaralandırma koşum sırasını değil okuma sırasını belirtir.

## 3. Selector politikası

1. `id: "member-list-item"` → RN'de `testID` (**tercih edilen**)
2. `text: "Kaydet"` → i18n değişince kırılır, dikkatli kullan
3. Koordinat / index → **son çare**, kırılgan

Kurallar:
- Etkileşimli her öğeye **kararlı `testID`** verilir; iOS'ta `accessibilityLabel` ile birlikte.
- `testID` üretilen değil sabit olur (`member-row-${id}` kabul, `row-3` değil).
- `testID` silmek e2e kırar → değiştirilirken flow'lar da güncellenir.

## 4. Bekleme

- `assertVisible` Maestro'da zaten bekler — elle `sleep` **kullanılmaz**.
- Uzun süren işlemlerde `waitForAnimationToEnd` veya `extendedWaitUntil` ile **koşullu** bekleme.
- Sabit `sleep` gören her yer flaky adayıdır.

## 5. Veri ve ortam

- Test ortamına bağlanılır; **üretime asla**. Base URL build profili (`preview`/`development`) ile gelir.
- Kurulum verisi API'den seed edilir (Maestro `runScript` ile veya öncesinde ayrı adım).
- Sabit test kullanıcısı yerine benzersiz kullanıcı; paralel koşumda çakışmaz.
- Kimlik bilgileri `env` üzerinden geçirilir, flow dosyasına yazılmaz.

## 6. Cihaz matrisi

- Minimum: 1 Android (en düşük desteklenen API seviyesi) + 1 iOS (en düşük desteklenen sürüm).
- Ek: küçük ekran + büyük ekran (layout kırılması en çok orada).
- Cihaz farkı testte değil, kodda çözülür — flow'a `if android` dallanması serpiştirme.

## 7. CI

- Her push'ta koşmaz — build gerektirir. Tetikleme: release adayı, gecelik, veya `dev → test` promosyonu.
- Maestro Cloud veya self-hosted emülatör; hangisi olursa olsun **artifact** (video + log) saklanır.
- Store yayını öncesi smoke flow'ları **zorunlu geçer** (`06-mobil.md` §9 checklist).

## 8. Yazılırken dikkat

- İzin diyalogları (konum, bildirim, kamera) flow'da açıkça ele alınır — aksi halde takılır.
- Klavye açılışı sonrası öğe görünürlüğü değişir; `hideKeyboard` gerekebilir.
- Android geri tuşu (`back`) ve iOS swipe farkı — flow ikisinde de çalışmalı.
- Ağ yavaşsa timeout değil, gerçek bekleme koşulu.

## 9. Yapma listesi

- ❌ `sleep` ile bekleme
- ❌ Koordinat ile tıklama (son çare dışında)
- ❌ Üretim ortamına koşum
- ❌ Flow içine gömülü kullanıcı adı/parola
- ❌ Her ekran için e2e yazmak (unit/component testine ait)
- ❌ `testID`'yi habersiz değiştirmek
