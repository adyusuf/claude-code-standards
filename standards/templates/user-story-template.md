# US-<000>: <Kısa başlık>

## Hikâye

**<Rol>** olarak, **<yetenek>** istiyorum; böylece **<fayda>** elde edeyim.

## Bağlam

<Neden şimdi? Hangi gerçek durumu çözüyor? Varsa mevcut acı noktası.>

## Kapsam

**Var:**
- <...>

**Bu sürümde YOK:** (yazılmayan liste sonra kapsam kaymasına dönüşür)
- <...>

## Kabul kriterleri

### 1. Mutlu yol
```
Given  <başlangıç durumu>
When   <kullanıcı eylemi>
Then   <gözlemlenebilir sonuç>
And    <ek sonuç>
```

### 2. Boş durum
```
Given  hiç kayıt yok
When   kullanıcı sayfayı açar
Then   "Henüz <şey> yok" mesajı ve "<Ekle>" butonu görünür
```

### 3. Hata durumu
```
Given  API 500 döner
When   kullanıcı listeyi yükler
Then   hata mesajı + "Tekrar dene" butonu görünür, sayfa çökmez
```

### 4. Yetki
```
Given  kullanıcının <yetki> izni yok
When   <eylem> denenir
Then   403 döner ve UI'da işlem sunulmaz (ikisi birden)
```

### 5. Sınır durumlar
- Çok uzun metin / 1000+ kayıt / özel karakter / eşzamanlı değişiklik
- Türkçe karakterli arama (harf boyutu + aksan bağımsız)

## Teknik notlar

- **API:** <yeni/değişen endpoint — additive mi?>
- **DB:** <yeni alan — nullable mı?>
- **Web + mobil paritesi:** <aynı mı, fark varsa neden>
- **i18n:** <yeni anahtarlar>

## Definition of Done

- [ ] Tüm kabul kriterleri karşılandı
- [ ] Unit test + (gerekiyorsa) e2e yazıldı
- [ ] API geriye uyumlu, Swagger güncel
- [ ] Erişilebilirlik kontrolü yapıldı
- [ ] i18n anahtarları eklendi (tr zorunlu)
- [ ] Log/metrik eklendi (kritik akışsa)
- [ ] Doküman + CLAUDE.md güncellendi
