# Vaka 01 — Kapsam yanılsaması: %95 nasıl %83 çıktı, %14 nasıl görünmedi

> **Özet:** Bir üretim projesinde test kapsamı %95,0 olarak raporlanıyordu.
> Paydadan üretilmiş kod çıkarılınca gerçek sayı **%83,0** oldu. Aynı projenin
> frontend'i **%14** seviyesindeydi ve 136 dosyanın **107'sine hiçbir test
> dokunmuyordu** — ama tek bir ortalama sayı bunu tamamen gizliyordu.
> Ölçüm tarihi: 12/09/2026. Proje: Proje B (adı kasten yazılmadı).

## Bağlam

Proje B; .NET backend + React (Vite) web + Android/iOS mobil istemcilerden
oluşan bir üretim sistemi. Kapsam sayısı CI çıktısında ve panoda görünüyordu ve
kimse ona itiraz etmiyordu: **%95,0**. "Test tarafı iyi" varsayımı buradan
besleniyordu.

## Ölçüm

İki şey ayrı ayrı ölçüldü — ve ayrı ölçmek zorunluydu:

**1. Payda dürüstlüğü (backend).** Coverlet çıktısı ham hâlde EF Core
göçlerini ve `ModelSnapshot`'ı da sayıyordu. Göçler testler koştuğunda
kendiliğinden çalışır, yani **test edilmiş gibi görünürler**. Paydadaki payları:

| | Satır kapsamı |
|---|---|
| Ham (göçler dahil) | **%95,0** |
| Göçler paydadan çıkarılınca | **%83,0** |

Göçler **paydanın %85'ini** oluşturuyordu. Yani raporlanan sayı, ağırlıklı
olarak el yazısı olmayan kodun kapsamını ölçüyordu.

**2. Ortalamanın gizlediği şey (frontend).** Kod tabanları ayrı ölçüldüğünde:

| Kod tabanı | Satır kapsamı |
|---|---|
| Backend (dürüst) | %83,0 |
| Web (frontend) | **~%14** |

Frontend'de **136 dosyanın 107'sine hiçbir test dokunmuyordu.** Tek bir
birleşik sayı raporlandığı sürece bu görünmüyordu; %95'lik backend %14'lük
frontend'i örtüyordu.

## Bulgu

Üç ayrı arıza aynı sayının içinde saklanmıştı:

1. **Payda şişmişti** — üretilmiş kod ürün kodu gibi sayılıyordu.
2. **Ortalama alınıyordu** — dört kod tabanı tek sayıya indiriliyordu.
3. **Kapı yoktu** — sayı raporlanıyordu ama hiçbir şeyi bloklamıyordu, yani
   düşmesi kimseyi durdurmuyordu.

⚠️ Buradaki asıl ders teknik değil: **yanlış sayı, hiç sayı olmamasından daha
tehlikeliydi.** Kapsam ölçülmüyor olsaydı "bilmiyoruz" denirdi; ölçülüyor
görünürken "iyiyiz" deniyordu.

## Müdahale

1. **Payda listesi tek dosyaya ve gerekçeyle** yazıldı. Çıkarılabilenler yalnız
   üretilmiş kod: EF göçleri + `ModelSnapshot`, `obj/`, `*.g.cs`,
   `*.Designer.cs`, `.d.ts`, testlerin kendisi, e2e/konfig dosyaları.
   ⛔ El yazısı ürün kodu listeye giremez — test etmesi zor olan dosya da
   (HTTP istemcisi, açılış kodu) dahil. Zor dosya **sahte bağımlılıkla** test
   edilir (sahte `HttpMessageHandler`, sahte saat), paydadan çıkarılmaz.
2. **Her kod tabanı ayrı ölçülür**, ortalama alınmaz. Ölçülmemiş kod tabanı
   "geçti" sayılmaz — **"ölçülmedi"** diye raporlanır ve promosyonu yine bloklar.
3. **Kapı kuruldu:** yerel kapı betiğinde promosyon modunda koşan bir adım;
   eşik altında çıkış kodu ≠ 0. CI aynı betiği çağırır — iki yerde iki farklı
   kural olmaz.
4. **Rapor her zaman hem ham hem dürüst sayıyı verir.** Ham sayının tek başına
   yazılması yasaklandı.
5. **Kapı mutasyonla doğrulandı:** kapsamlı bir dosyadaki test kaldırıldığında
   kapı gerçekten kırmızıya dönüyor mu? Dönmüyorsa kapı yok demektir.

## Sonuç

Doğan kural — `CLAUDE.md` #29, ayrıntısı `standards/10-test-stratejisi.md` §7:

> Satır kapsamı **her kod tabanında en az %80**. Ortalama alınmaz. Payda yalnız
> üretilmiş kod çıkarılarak dürüstleştirilir. Eşik projede düşürülmez, istisna
> verilmez; **proje `CLAUDE.md`'si bu maddeyi ezemez.** Kapsam için assert'sız
> test yazmak eşiği gevşetmekle aynıdır.

Bu, "proje kuralı genel kuralı ezer" ilkesinin tek istisnası olarak yazıldı —
çünkü gevşetme baskısı tam olarak proje düzeyinde ortaya çıkıyor.

## Nasıl doğrulanır

```bash
# .NET — coverlet, cobertura çıktısı
dotnet test <sln> --collect:"XPlat Code Coverage" --results-directory <dizin>
# ⚠️ iki test projesi ayrı dosya üretir; aynı satır ikisinde olabilir →
#    satırların BİRLEŞİMİ alınır, toplamı değil

# Vitest — eşik yapılandırmada, include ile payda daraltılır
#   coverage: { include: ['src/**/*.{ts,tsx}'], thresholds: { lines: 80 } }
npx vitest run --coverage

# Android — Kover;  iOS — xcodebuild -enableCodeCoverage YES
./gradlew koverVerify

# Kapının gerçek olduğunun kanıtı: kapsamlı bir dosyadaki testi kaldır,
# kapı kırmızıya dönmüyorsa kapı yoktur.
```

## Açık kalan

Dürüst olmak gerekirse iş bitmedi:

- Kural %80 diyor; **açığın kapatılması hâlâ sürüyor.** Kural açığı kapatmaz,
  yalnız promosyonu bloklar — bu bilinçli bir seçim.
- Mutasyon testi (Stryker) henüz tüm kritik modüllerde koşmuyor; bugün kapının
  gerçekliği elle doğrulanıyor.
- E2E bu sayıya girmiyor (ayrı ölçü) — yani %80 satır kapsamı "akış test
  edildi" demek değil.
