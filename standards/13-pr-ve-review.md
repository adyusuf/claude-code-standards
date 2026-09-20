# Commit, PR ve Code Review

## 1. Branch

```
<tip>/<kısa-açıklama>     feat/member-process-status
                          fix/order-total-rounding
                          chore/upgrade-efcore
                          docs/api-contract
```

- İngilizce, kebab-case, kısa. Kişi adı/ticket no tek başına branch adı olmaz.
- Branch **entegrasyon dalından** (`dev`) açılır, oraya döner. `test`/`prod`'a doğrudan branch açılmaz.
- Uzun yaşayan branch yok — 2-3 günü geçen dal ya bölünür ya sık sık `dev`'den rebase/merge edilir.

## 2. Commit

```
<tip>(<kapsam>): <Türkçe özet, emir kipi, 72 karakter altı>

Gövde: neden bu değişiklik gerekti, hangi alternatif elendi.
Kırıcı değişiklik varsa: BREAKING CHANGE: <açıklama>
```

Tipler: `feat` `fix` `refactor` `perf` `test` `docs` `chore` `build` `ci` `revert`

- **Atomik commit:** bir commit derlenebilir ve tek bir konuyu içerir. "wip", "düzeltme", "son" yasak.
- Formatlama/rename commit'i mantıksal değişiklikten **ayrı** commit'lenir (diff okunabilir kalsın).
- Üretilen dosyalar, `node_modules`, build çıktıları commit edilmez.
- **Yalnız kendi diff'ini commit et.** `git add -A` kör kullanılmaz; paralel oturum başkasının dosyasını kapabilir.

## 3. PR boyutu ve içeriği

- Hedef **< 400 satır** değişiklik. Büyükse böl — büyük PR'da review kalitesi çöker.
- **Bir PR = bir konu.** Refactor + özellik + format aynı PR'da olmaz.
- PR açıklaması (`sablonlar/pr-sablonu.md`):
  - Ne / neden
  - Nasıl test edildi (komut + sonuç)
  - Ekran görüntüsü (UI değişikliği varsa, öncesi/sonrası)
  - Geriye uyumluluk etkisi (**zorunlu alan**: "yok" da bir cevaptır ama yazılır)
  - Migration / env değişikliği / yeni sır var mı
  - Rollback nasıl yapılır

## 4. Merge kapısı (otomatik — geçilmeden merge yok)

> **Kapsam (global kural #25):** Aşağıdaki tam kapı **`dev → test` ve `test → prod` promosyonları** içindir.
> **`feature/* → dev` merge'inde** yalnız **build + hızlı unit test** koşar; review, sır/SAST/CVE taraması,
> geriye uyumluluk taraması, e2e ve kapsam eşiği **koşmaz**. **Formatlayıcı/lint de her merge'de değil,
> iş listesinin SONUNDA bir kez** koşar (20/09/2026, global #25/#26). `dev` dışarı yayın yapmaz; kapının yeri promosyondur.

- [ ] Build (backend + web + mobil)
- [ ] Unit testler yeşil
- [ ] **Satır kapsamı her kod tabanında ≥ %80** — dürüst paydayla, ölçülmemiş taban bloklar (global #29, `10-test-stratejisi.md` §7)
- [ ] `tsc --noEmit`, ESLint, `dotnet format --verify-no-changes`
- [ ] Geriye uyumluluk taraması (`08-geriye-uyumluluk.md` §7)
- [ ] Sır tarayıcı (gitleaks vb.) temiz
- [ ] Bağımlılık güvenlik taraması kritik bulgu yok
- [ ] Migration varsa geri alınabilirliği belirtilmiş

Kapı **atlatılmaz**. Kapıyı geçmek için testi gevşetmek yasak.

## 5. Review checklist (gözden geçiren için)

**Doğruluk**
- [ ] Kabul kriterlerini gerçekten karşılıyor mu?
- [ ] Sınır durumlar: boş, tek, çok, null, uzun metin, negatif, eşzamanlı
- [ ] Hata yolları ele alınmış mı? Sessiz yutulan exception var mı?

**Sözleşme / uyumluluk**
- [ ] Alan silindi/yeniden adlandırıldı/tipi değişti mi?
- [ ] Yeni zorunlu input alanı var mı?
- [ ] Enum sıralaması bozuldu mu? Global serializer ayarı değişti mi?
- [ ] Mobil eski sürüm bu değişiklikle çalışır mı?

**Güvenlik**
- [ ] Her endpoint yetkilendirilmiş mi? Kaynak sahipliği (IDOR) kontrol ediliyor mu?
- [ ] Girdi doğrulanıyor mu? Ham SQL parametreli mi?
- [ ] Sır/PII log'a veya yanıta sızıyor mu?

**Veri**
- [ ] N+1 var mı? Sayfalama var mı? Index gerekiyor mu?
- [ ] Transaction sınırı doğru mu? İçinde dış çağrı var mı?
- [ ] Migration geri alınabilir mi? `DROP` var mı?

**Okunabilirlik**
- [ ] İsimler niyeti anlatıyor mu? 300 satır kuralı?
- [ ] Ölü kod, yorum satırına alınmış kod, sahipsiz TODO var mı?
- [ ] Hard-coded URL/port/anahtar var mı?

**Test & doküman**
- [ ] Davranış değişikliğinin testi var mı? Test gevşetilmiş mi?
- [ ] Swagger/OpenAPI, CLAUDE.md, ilgili doküman güncel mi?

## 6. Bulgu şiddet seviyeleri

| Seviye | Anlam | Sonuç |
|---|---|---|
| **Bloke** | Veri kaybı, güvenlik açığı, kırıcı değişiklik, yanlış iş mantığı | Merge edilmez |
| **Önemli** | Performans sorunu, eksik test, eksik hata yolu, sözleşme riski | Bu PR'da düzeltilir |
| **Öneri** | İsimlendirme, yapı, okunabilirlik | Yazar takdirinde |
| **Not** | Bilgi paylaşımı | Aksiyon yok |

Yorum yazarken: **ne** yanlış + **neden** önemli + **öneri**. "Bu kötü" yorumu review değildir.
Öneri seviyesindeki yorum merge'i bloke etmez.

## 7. Yazar sorumluluğu

- PR açmadan önce **kendi diff'ini oku**. Kendi görebileceğin hatayı reviewer'a buldurma.
- Her yoruma cevap ver (düzelttim / şu nedenle düzeltmiyorum). Sessiz kapatma yok.
- Review sonrası büyük değişiklik yaptıysan tekrar review iste.

## 8. Merge stratejisi

- `dev`'e: **squash merge** (temiz tarih) veya rebase — proje içinde tek stil.
- `dev → test → prod`: **promosyon**, fast-forward/merge. Ters yönde merge yok.
- `test` ve `prod`'a doğrudan commit/PR **yok** — yalnız bir önceki aşamadan, kullanıcı onayıyla.
- Merge öncesi `git fetch` + geride kalınmışsa güncelle — bayat kodla koşan kapı yanlış güven verir.
- `--force` push yalnız kendi feature dalında ve açık onayla.

## 9. Claude'un review'daki rolü

- **Hedef dal `dev` ise review yapılmaz** (global kural #25): diff okunmaz, ajan çağrılmaz, tarama koşulmaz — build + hızlı test + lint yeşilse merge edilir. Yol üstünde göze çarpan bir şey varsa merge'i bloklamadan tek satır not düşülür.
  - ⚠️ **Tek istisna (08/09/2026, `modes/rol-secimi.md` §3):** değişiklik **yedeklemeyi, sır yönetimini ya da güvenlik kapısının kendisini** zayıflatıyorsa (`continue-on-error`, kapı devre dışı bırakma, gitleaks kapatma, yedek/restore bozma) `dev` yönünde de `qa` koşar ve gerekçesi yazılır. #25 hızı satın alır, geri alınamaz kaybı değil.
- "merge" komutu **`test` veya `prod` hedefliyse**: **önce diff'e review** yapılır; **bloke** seviyesinde bulgu varsa DUR ve raporla.
- Review yapılmadan merge kapısına "review yapıldı" bayrağı verilmez.
- Otomatik taramanın yakalayamadıkları (anlam değişikliği, enum kayması, yetki sıkılaştırma) **elle** kontrol edilir.
