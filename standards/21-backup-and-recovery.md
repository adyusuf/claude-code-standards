# Yedekleme ve Felaket Kurtarma

> **Denenmemiş yedek, yedek değildir.** Bu dosyanın tek amacı bu cümlenin
> gereğini yaptırmaktır. "Yedek alıyoruz" cevabı yeterli değil — "geçen ay
> restore ettik, X dakika sürdü" cevabı yeterlidir.

## 1. 3-2-1 kuralı

- **3** kopya (üretim + 2 yedek)
- **2** farklı ortam/medya
- **1** kopya **sunucu dışında** (farklı fiziksel/bulut konumda)

Aynı makinede duran yedek, makine gittiğinde yoktur. Aynı hesapta duran bulut yedeği,
hesap ele geçirildiğinde yoktur.

## 2. Neyi yedekliyoruz? (envanter — eksik kalan en sık hata)

| Varlık | Yöntem | Sıklık | Saklama | Nerede |
|---|---|---|---|---|
| **Veritabanı** | `pg_dump` / native backup | Günlük tam + saatlik WAL/log | 30 gün + aylık 12 ay | Sunucu + offsite |
| **Kullanıcı dosyaları** (upload, R2/S3/blob) | Bucket replikasyon / rsync | Günlük | 30 gün | Farklı bölge/hesap |
| **Uygulama konfigürasyonu** (env, appsettings, IIS/nginx conf) | Script + şifreli arşiv | Değişimde + haftalık | 90 gün | Offsite |
| **Sırlar** | Parola yöneticisi / secret store yedeği | Değişimde | — | Ayrı, şifreli |
| **Sertifikalar** (özellikle Cloudflare Origin Cert) | Şifreli arşiv | Yenilemede | Geçerlilik boyu | Offsite |
| **Kod** | Git remote (GitHub) | Push başına | Süresiz | + yerel ayna |
| **CI/CD ayarları** (workflow, secrets listesi) | IaC / dokümante | Değişimde | — | Repo + `DEPLOY.md` |
| **DNS / Cloudflare kuralları** | Export / Terraform state | Değişimde | — | Repo |
| **Log / audit** (yasal saklama varsa) | Arşiv | Günlük | Mevzuata göre | Offsite |

**Sadece DB yedeklemek eksiktir.** Kullanıcının yüklediği dosyalar gittiğinde DB'deki
kayıtlar boş referansa dönüşür.

## 3. Hedefler — yazılı olmalı

| Hedef | Tanım | Örnek değer |
|---|---|---|
| **RPO** | Kabul edilebilir maksimum **veri kaybı** | ≤ 1 saat (saatlik WAL ile) |
| **RTO** | Kabul edilebilir maksimum **kesinti** | ≤ 4 saat |

- RPO yedek sıklığını belirler; RTO restore prosedürünün hızını belirler.
- Hedefler kullanıcı/ürün kararıdır — teknik olarak varsayılmaz, **sorulur**.
- Hedefe ulaşılamıyorsa bu bir risktir ve yazılı kabul edilir.

## 4. Yedekleme kuralları

- **Otomatik.** Elle alınan yedek unutulur. Zamanlanmış görev (cron / Task Scheduler / managed backup).
- **Şifreli.** Yedek dosyası şifresiz durmaz; şifre çözme anahtarı yedekten **ayrı** yerde (yoksa anahtar da yedekle birlikte kaybolur).
- **Erişimi kısıtlı.** Yedek deposuna yazma yetkisi olan hesap, silme yetkisine sahip olmamalı (fidye yazılımı yedekleri de siler). Mümkünse **immutable / object-lock**.
- **Bütünlük doğrulaması.** Yedek alındıktan sonra checksum + açılabilirlik kontrolü (`pg_restore --list` gibi).
- **Boyut ve süre izlenir.** Yedek boyutu aniden düştüyse (ör. tablo kaybı) alarm.
- **Sıkıştırma + saklama politikası:** günlük 30 gün, haftalık 12 hafta, aylık 12 ay (GFS) — proje bazlı ayarlanır.
- **PII içeren yedek** de KVKK kapsamındadır: saklama süresi, silme talebi ve erişim kaydı düşünülür.

## 5. İzleme ve alarm (kritik)

- [ ] Yedek işi **başarısız olduğunda** alarm
- [ ] Yedek işi **hiç çalışmadığında** alarm (sessiz ölüm — en tehlikelisi; "son başarılı yedek > 26 saat önce" kontrolü)
- [ ] Yedek boyutu beklenenin altında → alarm
- [ ] Offsite kopyalama başarısız → alarm
- [ ] Yedek deposu doluyor → alarm

"Yedek alınıyor sanıyorduk" cümlesi, izleme kurulmadığında duyulur.

## 6. Restore provası — ayda 1, ZORUNLU

Prova adımları (kayıt tutulur):

```
1. En son yedek offsite kopyadan indirildi mi?          (sunucudakinden değil — offsite test edilir)
2. İzole bir ortama (test DB / geçici konteyner) restore edildi
3. Süre ölçüldü          → RTO hedefine uyuyor mu?
4. Doğrulama sorguları   → kayıt sayıları, en son kayıt tarihi, kritik tablolar dolu mu
5. Uygulama bu restore edilmiş DB ile ayağa kalkıyor mu?
6. Sonuç kaydedildi: tarih, yedek zamanı, süre, sorun, aksiyon
```

- Prova sonucu `docs/backup-drills.md` gibi bir dosyada **tarihli** tutulur.
- Prova başarısızsa bu bir **olaydır (incident)** — kök nedeni bulunur ve düzeltilir.
- Yılda en az bir kez **tam felaket tatbikatı**: "sunucu tamamen yok" senaryosundan sıfırdan kurulum (`DEPLOY.md` + yedekler ile).

## 7. Riskli işlem öncesi elle yedek

Şunlardan **önce** elle yedek alınır ve alındığı doğrulanır:

- `DROP` / `ALTER TYPE` / kolon silme içeren migration
- Toplu `UPDATE`/`DELETE`
- Büyük veri taşıma
- Sunucu/OS/DB sürüm yükseltme
- Prod'a riskli deploy

Sıra: **yedek al → doğrula → önce test ortamında dene → prod'da uygula.**

## 8. Geri dönüş (restore) senaryoları ve runbook

Her senaryo için `DEPLOY.md`/`RUNBOOK.md`'de adım adım komut bulunmalı:

| Senaryo | İlk hamle |
|---|---|
| Yanlışlıkla silinen kayıtlar | Point-in-time restore'u **ayrı** bir DB'ye, ilgili satırları kopyala. Prod'un üstüne yazma. |
| Bozuk migration | Migration geri alma veya yedekten restore; önce trafiği kes/feature flag kapat |
| Sunucu kaybı | Yeni sunucu (`DEPLOY.md` sıfırdan kurulum) + son yedek + DNS yönlendirme |
| Fidye yazılımı | İmmutable/offsite kopyadan restore; ele geçmiş kimlikler **rotate** edilir |
| Bulut hesabı kaybı | Farklı sağlayıcı/hesaptaki kopya — bu yüzden offsite aynı hesapta olmamalı |
| Veri bozulması (fark edilmemiş) | Eski tarihli yedeklere ihtiyaç → aylık saklama bu yüzden var |

Runbook'ta komutlar **kopyalanabilir** olmalı; olay anında sentez yapılmaz.

## 9. Yedekleme kurulum kontrol listesi (yeni proje/sunucu)

- [ ] DB otomatik yedek görevi kuruldu ve **ilk kez çalıştığı doğrulandı**
- [ ] Offsite kopyalama kuruldu ve çalıştığı doğrulandı
- [ ] Kullanıcı dosyaları (R2/S3/disk) yedekleme kapsamında
- [ ] Konfigürasyon + sertifika + sır envanteri yedekli
- [ ] Yedekler şifreli; anahtar ayrı yerde
- [ ] Saklama politikası (GFS) tanımlı, disk yeterli
- [ ] Başarısızlık **ve** hiç-çalışmama alarmı kurulu
- [ ] RPO/RTO yazılı ve kullanıcı onaylı
- [ ] İlk restore provası yapıldı ve süresi kaydedildi
- [ ] Runbook yazıldı (`DEPLOY.md` / `RUNBOOK.md`)
- [ ] Aylık prova takvime eklendi

## 10. Yapma listesi

- ❌ Yalnız aynı sunucuda duran yedek
- ❌ Şifresiz yedek dosyası
- ❌ Restore hiç denenmemiş yedek
- ❌ İzlemesiz/alarmsız yedek işi
- ❌ Yedek alan hesabın silme yetkisinin de olması
- ❌ Sadece DB yedekleyip kullanıcı dosyalarını atlamak
- ❌ Şifreleme anahtarını yedekle aynı yerde tutmak
- ❌ `DROP` içeren migration'ı yedeksiz koşmak
- ❌ RPO/RTO'yu varsaymak (bu bir ürün kararıdır, sorulur)
