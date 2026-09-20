# <Proje> — Kurulum

> Hedef: temiz bir makinede bu belgeyi takip ederek **tahmin yapmadan** projeyi
> ayağa kaldırmak. Bir adım eksikse bu belge hatalıdır — düzelt ve commit et.

## 1. Ön koşullar

| Araç | Sürüm | Kurulum | Doğrulama |
|---|---|---|---|
| .NET SDK | 8.0.x | `brew install --cask dotnet-sdk` | `dotnet --version` |
| Node.js | 20 LTS (`.nvmrc`) | `nvm install && nvm use` | `node -v` |
| Docker Desktop | güncel | `brew install --cask docker` | `docker ps` |
| PostgreSQL client | 16 | `brew install libpq` | `psql --version` |
| <diğer> | | | |

Sürümler `.nvmrc` / `global.json` / `package.json > engines` ile sabitlenmiştir. Onlara uy.

## 2. Depo ve bağımlılıklar

```bash
git clone <repo-url> && cd <repo>
# backend
dotnet restore
# web
cd web && npm ci && cd ..
# mobil
cd mobile && npm ci && cd ..
```

## 3. Sır ve token envanteri

> **Sır değeri bu tabloda ASLA yazmaz** — yalnız nereden alınacağı.
> Yeni sır ekleyen PR bu tabloyu güncellemek zorundadır.

| Ad | Ne işe yarar | Nereden alınır (menü yolu) | Nerede saklanır | Sahibi | Rotasyon | Sır mı? |
|---|---|---|---|---|---|---|
| `DB_CONNECTION` | Postgres bağlantısı | Local: `docker-compose.yml`'deki değerler. Prod: sunucu env | dev `.env`, prod sunucu env | <ad> | Yılda 1 | ✅ |
| `JWT_SIGNING_KEY` | Token imzalama | Üret: `openssl rand -base64 64` | dev User Secrets, prod sunucu env | <ad> | 6 ay | ✅ |
| `GOOGLE_CLIENT_ID` | Google ile giriş | Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client (Web) | `.env` | <ad> | — | ❌ public |
| `CLOUDFLARE_API_TOKEN` | DNS / cache purge | Cloudflare → My Profile → API Tokens → Create Custom Token (dar kapsam) | GitHub Actions Secret | <ad> | 6 ay | ✅ |
| `ANTHROPIC_API_KEY` | Claude API | console.anthropic.com → API Keys | prod sunucu env | <ad> | 6 ay | ✅ |
| `EXPO_TOKEN` | EAS build (CI) | expo.dev → Account Settings → Access Tokens | GitHub Actions Secret | <ad> | Yılda 1 | ✅ |
| `SENTRY_DSN` | Hata takibi | Sentry → Project Settings → Client Keys (DSN) | `.env` | <ad> | — | ❌ public |

**Erişim gerekiyorsa** (yeni geliştirici): <kime, nasıl talep edilir>

## 4. Ortam değişkenleri

```bash
cp .env.example .env
# .env içindeki zorunlu alanları §3'teki kaynaklardan doldur
```

- Zorunlu değişken eksikse uygulama **açılışta anlamlı hata ile durur**.
- Opsiyonel değişken boşsa ilgili özellik kapanır (`.env.example` içinde yazılı).

## 5. Veritabanı

```bash
docker compose up -d db          # Postgres ayağa kalkar
dotnet ef database update        # migration
dotnet run --project backend -- --seed   # seed (idempotent)
```

## 6. Çalıştırma

```bash
docker compose up -d api    # API      → http://localhost:5080
cd web && npm run dev       # Web      → http://localhost:5173
cd mobile && npx expo start # Mobil
```

### Port haritası

| Servis | Local | Docker | Not |
|---|---|---|---|
| API | 5080 | 5080 | `/swagger` |
| Web | 5173 | 3000 | |
| Postgres | 5432 | 5432 | |

## 7. Doğrulama — kurulum bitti mi?

```bash
curl -sf http://localhost:5080/health && echo "API OK"
curl -sf http://localhost:5173 >/dev/null && echo "Web OK"
dotnet test --nologo
cd web && npm test
```

Hepsi yeşilse kurulum tamam.

## 8. Test araçları (gerekiyorsa)

```bash
npx playwright install          # web e2e tarayıcıları
curl -Ls "https://get.maestro.mobile.dev" | bash   # mobil e2e
```

## 9. Sık karşılaşılan hatalar

| Belirti | Neden | Çözüm |
|---|---|---|
| `port already in use` | Başka servis 5080'de | `lsof -i :5080` → süreci kapat |
| `role does not exist` | Seed öncesi migration koşulmadı | `dotnet ef database update` |
| Web'de 401 döngüsü | `API_BASE_URL` yanlış | `.env` kontrol |
| `Unexpected token <` | API isteği SPA fallback'e düştü | Proxy `/api/*` kuralı |

## 10. Kurulum değiştiğinde

Yeni araç, yeni env değişkeni veya yeni sır ekleyen **her PR** bu dosyayı ve
`.env.example`'ı günceller. Güncellenmemişse review'da bloke edilir.
