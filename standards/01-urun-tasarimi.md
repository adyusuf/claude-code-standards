# Ürün Tasarımı

Kod yazmadan önce **ne** ve **neden** netleşir. Bu dosya o netliğin biçimini tanımlar.

## 1. Her özellik bir problemle başlar

Özellik talebi geldiğinde şu üçü yazılmadan kod yazılmaz:

| Soru | Çıktı |
|---|---|
| Kimin, hangi problemi? | 1–2 cümle problem tanımı + kullanıcı rolü |
| Nasıl anlarız çözüldüğünü? | Ölçülebilir başarı kriteri (metrik veya gözlem) |
| Kapsam dışı ne? | Açık "bu sürümde yok" listesi |

Kullanıcı bunları vermediyse **kısa sor**, tahmin etme. Ama tüm işi bloke etme —
netleşen kısmı yapıp belirsiz kısmı işaretle.

## 2. User story formatı

```
<Rol> olarak, <yetenek> istiyorum; böylece <fayda> elde edeyim.
```

Kötü: "Rapor sayfası ekle."
İyi: "İK sorumlusu olarak aday havuzunu süreç aşamasına göre filtreleyip dışa aktarmak istiyorum; böylece haftalık kurul toplantısına hazır listeyle gireyim."

Her story:
- **Bağımsız** olmalı (başka story bitmeden test edilebilir)
- **Küçük** olmalı (bir kişinin 1–3 günü; büyükse böl)
- **Kabul kriteri** olmalı (aşağıda)

## 3. Kabul kriteri — Given/When/Then

```
Given  aday listesinde 3 "Görüşme" ve 2 "Aktif" üye var
When   kullanıcı "Görüşme" filtresini seçer
Then   yalnız 3 kayıt listelenir ve toplam sayaç "3" gösterir
And    filtre URL'de ?status=gorusme olarak kalır (sayfa yenilenince korunur)
```

Kural:
- Kabul kriteri **davranışı** tarif eder, implementasyonu değil.
- Her kriter **doğrulanabilir** olmalı — otomatik teste birebir çevrilebilmeli.
- **Mutlu yol yetmez:** boş liste, hata, yetkisiz erişim, çok uzun metin, eşzamanlı değişiklik senaryoları da yazılır.

## 4. Kapsam disiplini

- **MVP = en küçük değerli dilim**, "yarısı yapılmış tam ürün" değil.
- Her özellik için "v1'de yok" listesi yazılır. Yazılmayan liste sonra kapsam kaymasına dönüşür.
- "Bunu da eklerken şunu da yapalım" → ayrı story, ayrı PR.
- Konfigüre edilebilirlik **talep gelmeden** eklenmez (YAGNI). Üç kez tekrar eden ihtiyaç genelleştirilir.

## 5. Domain dili tek olur

- Proje sözlüğü (`docs/sozluk.md`) tutulur: Türkçe terim ↔ İngilizce kod karşılığı.
- Aynı kavram için iki isim kullanılmaz (`Member`/`User` karışıklığı gibi).
- Kullanıcıya görünen terim ile koddaki terim ayrı olabilir; eşleme sözlükte durur.

## 6. Karar kaydı (ADR)

Geri dönüşü pahalı her karar bir ADR'ye yazılır: veritabanı seçimi, auth stratejisi,
çok kiracılılık modeli, ödeme entegrasyonu, mimari sınır değişikliği.

Şablon: `sablonlar/adr-sablonu.md`. Kısa olsun (1 sayfa), ama **reddedilen alternatifler**
ve **sonuçları** mutlaka yazılsın. ADR silinmez; iptal olursa "Superseded by ADR-00X" işaretlenir.

## 7. Ürün kararı ≠ teknik karar

Claude şu kararları **kendi başına vermez**, kullanıcıya sorar:
- Bir alanın zorunlu mu opsiyonel mi olacağı
- Silme davranışı (soft delete mi hard delete mi, kim silebilir)
- Yetki matrisi (hangi rol neyi görür)
- Para, ödeme, fatura ile ilgili her şey
- Kullanıcıya gönderilen bildirim/e-posta metni ve tetikleyicisi
- Veri saklama süresi ve anonimleştirme

## 8. Özellik bitti sayılma koşulu (Definition of Done)

- [ ] Kabul kriterlerinin hepsi karşılandı (mutlu yol + hata yolları)
- [ ] API sözleşmesi geriye uyumlu, Swagger/OpenAPI güncel
- [ ] Web + mobil paritesi gözden geçirildi (varsa fark bilinçli ve yazılı)
- [ ] Unit + gerekli e2e test yazıldı, CI yeşil
- [ ] i18n anahtarları eklendi (tr zorunlu, en yer tutucu)
- [ ] Erişilebilirlik kontrolü yapıldı (`02-ui-ux.md` §7)
- [ ] Log/metrik eklendi (yeni kritik akışsa)
- [ ] Doküman + CLAUDE.md güncellendi
- [ ] Rollback planı düşünüldü (feature flag mı, migration geri alınabilir mi)
