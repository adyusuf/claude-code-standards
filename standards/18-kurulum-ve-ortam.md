# Kurulum, Ortam ve Sır Envanteri

> **Altın kural:** Sıfırdan bir makinede projeyi ayağa kaldırmak `SETUP.md`'yi
> takip ederek **tek oturumda ve tahmin yapmadan** mümkün olmalı. "Bende çalışıyor"
> bir kurulum belgesi değildir.

## 1. Her projede zorunlu dosyalar

| Dosya | İçerik |
|---|---|
| `SETUP.md` | Ön koşullar, kurulum adımları, sır envanteri, doğrulama |
| `.env.example` | **Tüm** env değişkenleri, değersiz, açıklamalı |
| `DEPLOY.md` | Sunucu kurulumu, deploy, DNS, sertifika, yedek görevleri |
| `CLAUDE.md` | Claude için proje kuralları (`sablonlar/proje-claude-md.md`) |

## 2. `SETUP.md` yapısı (şablon: `sablonlar/setup-md.md`)

```
1. Ön koşullar (sürümleriyle)
2. Depoyu alma + bağımlılık kurulumu
3. Sır ve token envanteri (tablo)
4. Ortam değişkenleri (.env.example → .env)
5. Veritabanı kurulumu + migration + seed
6. Çalıştırma (her ayak için tek komut)
7. Doğrulama (nasıl anlarım çalıştığını)
8. Sık karşılaşılan hatalar
```

## 3. Ön koşul listesi — sürüm belirtilir

Örnek (proje bazlı güncellenir):

| Araç | Sürüm | Kurulum | Neden |
|---|---|---|---|
| .NET SDK | 8.0.x | `brew install --cask dotnet-sdk` | Backend |
| Node.js | 20 LTS (`.nvmrc`) | `nvm install` | Web + mobil |
| pnpm/npm | lock file'a göre | corepack | Bağımlılık |
| Docker Desktop | güncel | brew cask | Postgres + API konteyneri |
| PostgreSQL client | 16 | `brew install libpq` | `psql`, dump/restore |
| Expo CLI / EAS CLI | güncel | `npm i -g eas-cli` | Mobil build |
| Xcode / Android Studio | güncel | — | Simülatör/emülatör |
| Playwright tarayıcıları | — | `npx playwright install` | Web e2e |
| Maestro | güncel | `curl -Ls maestro.mobile.dev \| bash` | Mobil e2e |

- **Sürüm sabitlenir:** `.nvmrc`, `global.json`, `.tool-versions`, `package.json > engines`.
- "En son sürüm" yazılmaz — bugünün en sonu yarın kırar.

## 4. Sır ve token envanteri (ZORUNLU tablo)

`SETUP.md`'de **her sır için** şu 6 sütun doldurulur:

| Ad | Ne işe yarar | Nereden alınır | Nerede saklanır | Sahibi | Rotasyon |
|---|---|---|---|---|---|
| `DB_CONNECTION` | Postgres bağlantısı | Docker compose (local) / sunucu env (prod) | dev: `.env`, prod: sunucu env | <ad> | Yılda 1 |
| `JWT_SIGNING_KEY` | Token imzalama | `openssl rand -base64 64` ile üretilir | dev: User Secrets, prod: sunucu env | <ad> | 6 ayda 1 |
| `GOOGLE_CLIENT_ID` | Google ile giriş | Google Cloud Console → APIs & Services → Credentials → OAuth client (Web) | `.env` (public değer, sır değil) | <ad> | — |
| `GOOGLE_SA_JSON` | Gmail API gönderimi | GCP → IAM → Service Account → Key (JSON) + Domain-wide delegation | dev: gitignore'lu dosya, prod: sunucu secret | <ad> | Yılda 1 |
| `CLOUDFLARE_API_TOKEN` | DNS/cache yönetimi | Cloudflare → My Profile → API Tokens → **Custom token, dar kapsam** | GitHub Actions Secret | <ad> | 6 ayda 1 |
| `ANTHROPIC_API_KEY` | Claude API | console.anthropic.com → API Keys | prod: sunucu env | <ad> | 6 ayda 1 |
| `EXPO_TOKEN` | EAS build (CI) | expo.dev → Account → Access Tokens | GitHub Actions Secret | <ad> | Yılda 1 |
| `SENTRY_DSN` | Hata takibi | Sentry → Project Settings → Client Keys | `.env` (public) | <ad> | — |
| `SMTP_*` / mail | E-posta | Sağlayıcı paneli | prod: sunucu env | <ad> | Yılda 1 |

Kurallar:
- **"Nereden alınır" sütunu tıklanacak yolu tarif eder** — "panelden al" yeterli değil, menü yolu yazılır.
- Sır **değeri** bu tabloda **asla** yazmaz; yalnız nereden alınacağı.
- Public değer (client id, DSN) ile gerçek sır ayrı işaretlenir.
- Yeni sır ekleyen PR bu tabloyu güncellemek **zorundadır** (review checklist maddesi).
- Sır üretimi mümkünse komutla gösterilir (`openssl rand -hex 32`).

## 5. `.env.example` kuralları

```bash
# --- Zorunlu ---
DB_CONNECTION=            # Postgres. Örn: Host=localhost;Port=5432;Database=app;Username=app;Password=***
JWT_SIGNING_KEY=          # openssl rand -base64 64 ile üret. Min 32 byte.
API_BASE_URL=             # Web/mobil bunu kullanır. Local: http://localhost:5080

# --- Opsiyonel (boşsa özellik kapanır) ---
GOOGLE_CLIENT_ID=         # Boşsa Google ile giriş butonu render EDİLMEZ
SENTRY_DSN=               # Boşsa hata takibi devre dışı
```

- **Her değişken açıklamalı**; formatı ve örneği verilir.
- Zorunlu/opsiyonel ayrımı net; opsiyonel olanın boş olması ne yapar yazılır.
- Uygulama **açılışta** zorunlu ayarları doğrular ve eksikse **anlamlı hata ile durur** (ilk istekte gizemli 500 değil).
- `.env` gitignore'da; `.env.example` commit'te. Yeni değişken eklendiğinde ikisi de güncellenir.

## 6. Tek komutla ayağa kalkma

Hedef:

```bash
git clone <repo> && cd <repo>
cp .env.example .env      # sırları doldur (SETUP.md §4)
make dev                  # veya: docker compose up -d && npm run dev
```

- Bağımlılık kurulumu, DB oluşturma, migration, seed **script'lenmiş** olmalı.
- Manuel adım kalıyorsa `SETUP.md`'de numaralı ve kopyalanabilir komutla.
- `make dev` / `npm run dev` gibi tek giriş noktası tanımlanır; hangi portta ne koştuğu yazılır.

## 7. Port haritası (projede sabit ve belgeli)

| Servis | Local port | Docker port | Not |
|---|---|---|---|
| API | 5080 | 5080 | Swagger `/swagger` |
| Web (Vite dev) | 5173 | 3000 | |
| İkincil web | 5174 | — | |
| Postgres | 5432 | 5432 | |
| Redis | 6379 | — | |

Port çakışması en sık kurulum sorunudur — tablo `SETUP.md`'de bulunur.

## 8. Doğrulama adımı (kurulum bitti mi?)

`SETUP.md` sonunda **çalıştırılabilir** kontroller:

```bash
curl -sf http://localhost:5080/health && echo "API OK"
curl -sf http://localhost:5173 > /dev/null && echo "Web OK"
dotnet test --nologo   # veya npm test
```

"Tarayıcıda aç ve bak" yerine komutla doğrulanabilir kriter tercih edilir.

## 9. Yeni geliştirici / yeni makine kontrol listesi

- [ ] Ön koşullar sürümleriyle kuruldu (`node -v`, `dotnet --version` çıktıları eşleşiyor)
- [ ] `.env` dolduruldu, zorunlu sırlar alındı
- [ ] Docker servisleri ayakta
- [ ] Migration + seed koştu
- [ ] Tüm ayaklar ayağa kalktı, `/health` yeşil
- [ ] Testler yerelde geçiyor
- [ ] Formatlayıcı/linter editörde çalışıyor (`.editorconfig`, ESLint eklentisi)
- [ ] Git hook'ları kurulu (pre-commit sır taraması)
- [ ] Repo erişimleri + gerekli panel erişimleri (Cloudflare, GCP, store) verildi

## 10. Kurulum bozulduğunda

- Kurulum adımı değiştiyse **aynı PR'da** `SETUP.md` güncellenir.
- Yeni bağımlılık/araç eklendiyse ön koşul tablosuna eklenir.
- Yeni env değişkeni → `.env.example` + sır envanteri + açılış doğrulaması.
- "Bende çalışıyordu" durumunda: sürüm farkları (`node -v`, SDK), eksik env, port çakışması, Docker durumu sırayla kontrol edilir.
