# <Project> — Setup

> The goal: on a clean machine, bring the project up by following this document
> **without guessing anything**. If a step is missing, this document is wrong —
> fix it and commit the fix.

## 1. Prerequisites

| Tool | Version | Install | Verify |
|---|---|---|---|
| .NET SDK | 8.0.x | `brew install --cask dotnet-sdk` | `dotnet --version` |
| Node.js | 20 LTS (`.nvmrc`) | `nvm install && nvm use` | `node -v` |
| Docker Desktop | current | `brew install --cask docker` | `docker ps` |
| PostgreSQL client | 16 | `brew install libpq` | `psql --version` |
| <other> | | | |

Versions are pinned through `.nvmrc` / `global.json` / `package.json > engines`. Follow them.

## 2. Repository and dependencies

```bash
git clone <repo-url> && cd <repo>
# backend
dotnet restore
# web
cd web && npm ci && cd ..
# mobile
cd mobile && npm ci && cd ..
```

## 3. Secret and token inventory

> **A secret's value is NEVER written in this table** — only where to obtain it.
> Any PR that adds a new secret must update this table.

| Name | What it is for | Where to obtain it (menu path) | Where it is stored | Owner | Rotation | Secret? |
|---|---|---|---|---|---|---|
| `DB_CONNECTION` | Postgres connection | Local: the values in `docker-compose.yml`. Production: server env | dev `.env`, production server env | <name> | Yearly | ✅ |
| `JWT_SIGNING_KEY` | Token signing | Generate: `openssl rand -base64 64` | dev User Secrets, production server env | <name> | 6 months | ✅ |
| `GOOGLE_CLIENT_ID` | Sign in with Google | Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client (Web) | `.env` | <name> | — | ❌ public |
| `CLOUDFLARE_API_TOKEN` | DNS / cache purge | Cloudflare → My Profile → API Tokens → Create Custom Token (narrow scope) | GitHub Actions Secret | <name> | 6 months | ✅ |
| `ANTHROPIC_API_KEY` | Claude API | console.anthropic.com → API Keys | production server env | <name> | 6 months | ✅ |
| `EXPO_TOKEN` | EAS build (CI) | expo.dev → Account Settings → Access Tokens | GitHub Actions Secret | <name> | Yearly | ✅ |
| `SENTRY_DSN` | Error tracking | Sentry → Project Settings → Client Keys (DSN) | `.env` | <name> | — | ❌ public |

**If access is needed** (a new developer): <from whom, and how to request it>

## 4. Environment variables

```bash
cp .env.example .env
# fill in the required fields in .env from the sources in §3
```

- If a required variable is missing, the application **stops at start-up with a meaningful error**.
- If an optional variable is empty, the corresponding feature is disabled (documented in `.env.example`).

## 5. Database

```bash
docker compose up -d db          # Postgres comes up
dotnet ef database update        # migrations
dotnet run --project backend -- --seed   # seed (idempotent)
```

## 6. Running it

```bash
docker compose up -d api    # API      → http://localhost:5080
cd web && npm run dev       # Web      → http://localhost:5173
cd mobile && npx expo start # Mobile
```

### Port map

| Service | Local | Docker | Note |
|---|---|---|---|
| API | 5080 | 5080 | `/swagger` |
| Web | 5173 | 3000 | |
| Postgres | 5432 | 5432 | |

## 7. Verification — is the setup complete?

```bash
curl -sf http://localhost:5080/health && echo "API OK"
curl -sf http://localhost:5173 >/dev/null && echo "Web OK"
dotnet test --nologo
cd web && npm test
```

If all of it is green, the setup is done.

## 8. Test tooling (when needed)

```bash
npx playwright install          # web e2e browsers
curl -Ls "https://get.maestro.mobile.dev" | bash   # mobile e2e
```

## 9. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `port already in use` | Another service on 5080 | `lsof -i :5080` → stop the process |
| `role does not exist` | Migrations were not run before seeding | `dotnet ef database update` |
| A 401 loop in the web app | `API_BASE_URL` is wrong | check `.env` |
| `Unexpected token <` | An API request fell through to the SPA fallback | the proxy's `/api/*` rule |

## 10. When the setup changes

**Every PR** that adds a tool, an env variable or a secret updates this file and
`.env.example`. If it does not, it is blocked in review.
