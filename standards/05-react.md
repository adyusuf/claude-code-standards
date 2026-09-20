# React + TypeScript Standartları

## 1. Klasör yapısı (özellik bazlı)

```
src/
  api/          → client.ts (TEK config: BASE_URL, SIGNALR_URL), endpoint modülleri
  components/   → paylaşılan sunum bileşenleri (Button, Modal, EmptyState, Table)
  features/<ad>/→ o özelliğe ait sayfa, bileşen, hook, tip
  hooks/        → paylaşılan hook'lar
  lib/          → saf yardımcılar (date, search normalize, format)
  i18n/         → tr.json, en.json
  types/        → paylaşılan tipler / API'den üretilen tipler
```

Teknoloji bazlı değil **özellik bazlı** gruplama. Bir özelliği silmek tek klasörü silmek olmalı.

## 2. TypeScript

- `strict: true`. `any` yasak (`unknown` + daraltma kullan). Kaçınılmazsa gerekçe yorumu.
- API tiplerini elle yazma — OpenAPI'den üret (`openapi-typescript` vb.) veya tek yerde tanımla.
- Tip assertion (`as`) yerine tip guard. `!` non-null assertion istisna, gerekçeli.
- Discriminated union ile durum modelle: `{status:'loading'} | {status:'error',error} | {status:'ok',data}` — `isLoading && !error && data` üçlemesi değil.
- `enum` yerine `as const` union tercih edilir.

## 3. Bileşen kuralları

- Fonksiyon bileşeni + hook. Class bileşen yok.
- **300 satır üstü bileşen bölünür.** Bölme sırasında props/JSX/veri çağrısı/i18n anahtarı aynen korunur.
- Bileşen içinde bileşen tanımlanmaz (her render'da yeniden yaratılır → state kaybı).
- Props destructure edilir; `props.x.y.z` zinciri yok.
- Erken `return` ile guard (`if (!data) return <Skeleton/>`), derin ternary iç içeliği yok.
- `key` olarak index kullanılmaz (liste sıralanabiliyorsa/silinebiliyorsa) — kararlı id.

## 4. State yönetimi — doğru yerde

| Durum türü | Nerede |
|---|---|
| Sunucu verisi | TanStack Query (veya eşdeğeri) — `useState`+`useEffect` ile elle çekme değil |
| URL'e ait durum (filtre, sekme, sayfa) | Query param (`useSearchParams`) |
| Form durumu | Form kütüphanesi (react-hook-form) veya lokal state |
| Kısa ömürlü UI durumu | Lokal `useState` |
| Gerçekten global (auth, tema, i18n) | Context — küçük ve bölünmüş |

- Türetilebilen değer state'te tutulmaz, render sırasında hesaplanır.
- Context'e sık değişen değer konmaz (tüm ağaç render olur) — böl veya store kullan.
- `useEffect` yalnız **dış sistemle senkronizasyon** içindir. Prop'tan state türetmek, hesap yapmak, event'e tepki vermek için `useEffect` **yanlıştır**.

## 5. Veri çekme

- Tek API client (`src/api/client.ts`) — base URL, header, auth, hata normalizasyonu orada. Bileşenler `fetch`/`axios`'u doğrudan çağırmaz.
- Her istek: loading + error + empty durumları ele alınır (`02-ui-ux.md` §3).
- İstek iptali (`AbortSignal`) — bileşen unmount olduğunda veya arama terimi değiştiğinde.
- Arama/filtre girişleri debounce (300ms civarı).
- Mutasyon sonrası ilgili sorgular invalidate edilir; optimistic update kullanılıyorsa rollback yolu yazılır.
- Hata yanıtı sunucunun ProblemDetails formatından tek yerde parse edilir; alan hataları forma bağlanır.

## 6. Performans

- Önce doğru yapı, sonra memo. `useMemo`/`useCallback`/`React.memo` **ölçülen** sorun için.
- Uzun listeler sanallaştırılır (`react-virtual` vb.) veya sayfalanır.
- Route bazlı code splitting (`React.lazy` + `Suspense`).
- Görsel: doğru boyut + `loading="lazy"` + modern format.
- Bundle bütçesi izlenir (`16-performans.md`).

## 7. Stil

- Tek yaklaşım seçilir (CSS Modules / Tailwind / CSS-in-JS) ve karıştırılmaz.
- Ham renk/ölçü değeri yok → token (`02-ui-ux.md` §1).
- Global CSS minimum; bileşen stili bileşenle birlikte durur.
- Inline style yalnız gerçekten dinamik değer için.

## 8. Form

- `react-hook-form` + şema doğrulama (zod/yup). Şema **tek kaynak**: tip de şemadan türetilir.
- Sunucu validasyon hatası alanlara bağlanır (`setError`).
- Submit sırasında disable + spinner; çift gönderim engellenir.

## 9. Yönlendirme ve yetki

- Route tanımları tek dosyada; yetki kontrolü route seviyesinde guard bileşeniyle.
- **UI'daki gizleme güvenlik değildir** — yetki her zaman API'de de kontrol edilir.
- 401 → merkezî interceptor'da oturum yenileme veya login'e yönlendirme (her bileşende değil).

## 10. Erişilebilirlik

- `eslint-plugin-jsx-a11y` açık.
- Etkileşimli öğe `button`/`a`; `div onClick` yasak.
- Modal: focus trap + `Esc` + `aria-modal` + arka plan inert.
- Detay: `02-ui-ux.md` §7.

## 11. Test

- **React Testing Library** — kullanıcı davranışını test et, implementasyonu değil.
- Sorgu önceliği: `getByRole` > `getByLabelText` > `getByText` > `getByTestId` (son çare).
- Ağ MSW ile taklit edilir; `fetch` global mock'lamak yerine gerçek istek/yanıt seviyesinde.
- Snapshot testi kural olarak kullanılmaz (kırılgan, gözden geçirilmeden onaylanır).
- Detay: `10-test-stratejisi.md`.

## 12. Yapma listesi

- ❌ `useEffect` içinde state set edip aynı state'e bağımlılık vermek (sonsuz döngü)
- ❌ `dangerouslySetInnerHTML` (zorunluysa DOMPurify ile sanitize + gerekçe)
- ❌ `localStorage`'a token yazmak (XSS'e açık — httpOnly cookie tercih; edilemiyorsa risk yazılı kabul edilir)
- ❌ `window.location` ile router yerine yönlendirme
- ❌ Ortam değişkenini bileşen içinde okumak (`import.meta.env` yalnız `api/client.ts`'te)
- ❌ Sunucu verisini Redux/Context'e elle kopyalamak
- ❌ Prop drilling 3 seviyeden derin (compose veya context)
