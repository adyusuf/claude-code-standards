# Gözlemlenebilirlik — Log, Metrik, Trace, Alarm

> Temel soru: **"Bir şey bozulduğunda nasıl fark ederiz ve nereye bakarız?"**
> Cevabı olmayan özellik yarım özelliktir.

## 1. Log

- **Yapılandırılmış** (JSON/key-value). String birleştirme değil, mesaj şablonu:
  `_log.LogInformation("Sipariş {OrderId} iptal edildi, üye {MemberId}", orderId, memberId)`
- Seviyeler:
  | Seviye | Ne zaman | Örnek |
  |---|---|---|
  | `Debug` | Yalnız geliştirme | Sorgu detayı |
  | `Information` | İş olayı | "Üye oluşturuldu" |
  | `Warning` | Beklenen ama istenmeyen | "Dış servis yavaş, retry" |
  | `Error` | İşlem başarısız | "Sipariş kaydedilemedi" |
  | `Critical` | Sistem tehlikede | "DB'ye bağlanılamıyor" |
- **Log'a yazılmaz:** parola, token, kart no, TCKN, tam e-posta/telefon (maskele), tam istek gövdesi, sır.
- Döngü içinde log yok — toplu özet.
- Üretimde `Information` ve üstü; `Debug` kapalı (maliyet + gizlilik).
- Log saklama süresi ve maliyeti tanımlı.

## 2. Correlation / Trace ID

- Her istek bir **correlation id** taşır (`traceparent` / `X-Correlation-Id`).
- İstemciden gelen id varsa kullanılır, yoksa üretilir; **yanıtta geri döner** ve hata gövdesinde (`traceId`) yer alır.
- Arka plan işleri ve kuyruk mesajları da id taşır (tetikleyen istekle bağlanabilsin).
- Kullanıcı "hata aldım" dediğinde ekrandaki traceId ile log'a tek sorguda ulaşılabilmeli.

## 3. Metrikler

**Altın sinyaller** (her servis için):
- **Latency** — p50/p95/p99, endpoint bazında
- **Traffic** — istek/saniye
- **Errors** — 4xx / 5xx oranı
- **Saturation** — CPU, bellek, disk, DB bağlantı havuzu, thread havuzu

**İş metrikleri** (asıl değerli olanlar):
- Giriş başarı oranı, kayıt sayısı, sipariş sayısı, ödeme başarısızlığı, e-posta gönderim başarısı
- İş metriği düşerse teknik metrik yeşil olsa bile bir şey bozuktur.

Araç: OpenTelemetry → Prometheus/Grafana veya barındırılan APM.

## 4. Trace

- OpenTelemetry ile uçtan uca: HTTP → servis → DB → dış çağrı.
- Yavaş isteğin **nerede** yavaşladığı trace'ten görülmeli.
- Örnekleme (sampling): normalde %1-10, hatalı isteklerde %100.

## 5. Hata takibi

- Sentry / benzeri: yakalanmamış exception'lar, istemci tarafı JS hataları, mobil crash'ler.
- Her hata: sürüm (commit SHA), ortam, kullanıcı id (PII değil), correlation id, breadcrumb.
- Yeni sürüm sonrası hata oranı **karşılaştırmalı** izlenir (regression tespiti).
- Gürültü temizlenir — herkesin görmezden geldiği alarm, alarm değildir.

## 6. Health check

- `/health` — liveness (süreç ayakta mı)
- `/health/ready` — readiness (DB, cache, kritik dış servis erişilebilir mi)
- `/version` — çalışan sürüm + commit SHA + build zamanı
- Deploy sonrası smoke test bunları kullanır; load balancer readiness'a bakar.

## 7. Alarmlar

**Alarm kurulması zorunlu olanlar:**
- [ ] 5xx oranı eşiği aştı
- [ ] p95 latency eşiği aştı
- [ ] Uygulama ayakta değil (uptime kontrolü, dışarıdan)
- [ ] Disk / bellek doluyor
- [ ] **Sertifika süresi < 21 gün**
- [ ] **Yedekleme işi başarısız oldu veya hiç çalışmadı**
- [ ] Kuyruk birikiyor / arka plan işi takıldı
- [ ] Kritik iş metriği anormal düştü (ör. 1 saattir hiç giriş yok)
- [ ] Güvenlik: kısa sürede çok 403/401, tek IP'den çok hesap denemesi

Kurallar:
- Alarm **eyleme çağırır**; eylem gerektirmeyen bilgi alarm değil dashboard'dur.
- Her alarmın bir **runbook**'u vardır: ne anlama gelir, ilk ne yapılır, kime haber verilir.
- Yanlış alarm (false positive) ya düzeltilir ya kaldırılır — alarm yorgunluğu gerçek olayı kaçırtır.

## 8. Dashboard

Tek ekranda görülmeli: istek hacmi, hata oranı, p95 latency, aktif kullanıcı, kritik iş metriği,
son deploy zamanı ve sürümü, yedekleme son durumu.

Deploy sonrası **ilk 30 dakika** bu ekran izlenir.

## 9. Olay (incident) yönetimi

1. **Tespit** — alarm veya kullanıcı bildirimi
2. **Değerlendirme** — etki (kaç kullanıcı, veri kaybı var mı), şiddet
3. **Durdurma** — önce kanamayı durdur: rollback / feature flag kapat / trafiği kes. Kök neden **sonra**.
4. **İletişim** — etkilenen kullanıcılara durum bildirimi (uzun sürecekse)
5. **Çözüm** ve doğrulama (metrikler normale döndü mü)
6. **Post-mortem** — 48 saat içinde, **suçlayıcı olmayan**: ne oldu, zaman çizelgesi, neden fark edilmedi, neden bu kadar sürdü, hangi 2-3 aksiyon tekrarını önler

Post-mortem çıktısı **aksiyon maddesidir**; sahibi ve tarihi olmayan madde yazılmamış sayılır.

## 10. Yeni özellik eklerken

- [ ] Kritik akışa `Information` seviyesinde iş log'u eklendi mi?
- [ ] Hata yolları `Error` ile log'lanıyor mu (correlation id ile)?
- [ ] İzlenmesi gereken bir iş metriği var mı?
- [ ] Bozulduğunda hangi alarm çalacak?
- [ ] Dashboard'a eklenecek bir şey var mı?
