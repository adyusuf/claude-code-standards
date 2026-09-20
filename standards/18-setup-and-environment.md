# Setup, environments and the secret inventory

> **The golden rule:** bringing the project up on a clean machine must be possible
> by following `SETUP.md` **in a single sitting and without guessing**. "It works
> on my machine" is not a setup document.

## 1. Files every project must have

| File | Contents |
|---|---|
| `SETUP.md` | Prerequisites, setup steps, the secret inventory, verification |
| `.env.example` | **Every** env variable, without values, commented |
| `DEPLOY.md` | Server setup, deployment, DNS, certificates, backup jobs |
| `CLAUDE.md` | The project rules for Claude (`templates/project-claude-md.md`) |

## 2. The structure of `SETUP.md` (template: `templates/setup-md.md`)

```
1. Prerequisites (with versions)
2. Cloning the repository + installing dependencies
3. The secret and token inventory (a table)
4. Environment variables (.env.example → .env)
5. Database setup + migrations + seed
6. Running it (one command per tier)
7. Verification (how do I know it works)
8. Common errors
```

## 3. The prerequisite list — with versions

An example (kept up to date per project):

| Tool | Version | Install | Why |
|---|---|---|---|
| .NET SDK | 8.0.x | `brew install --cask dotnet-sdk` | Backend |
| Node.js | 20 LTS (`.nvmrc`) | `nvm install` | Web + mobile |
| pnpm/npm | per the lock file | corepack | Dependencies |
| Docker Desktop | current | brew cask | The Postgres + API containers |
| PostgreSQL client | 16 | `brew install libpq` | `psql`, dump/restore |
| Expo CLI / EAS CLI | current | `npm i -g eas-cli` | Mobile builds |
| Xcode / Android Studio | current | — | Simulator/emulator |
| Playwright browsers | — | `npx playwright install` | Web e2e |
| Maestro | current | `curl -Ls maestro.mobile.dev \| bash` | Mobile e2e |

- **Versions are pinned:** `.nvmrc`, `global.json`, `.tool-versions`, `package.json > engines`.
- Never write "the latest version" — today's latest breaks tomorrow.

## 4. The secret and token inventory (a MANDATORY table)

In `SETUP.md`, these six columns are filled in **for every secret**:

| Name | What it is for | Where to obtain it | Where it is stored | Owner | Rotation |
|---|---|---|---|---|---|
| `DB_CONNECTION` | Postgres connection | Docker compose (local) / server env (production) | dev: `.env`, prod: server env | <name> | Yearly |
| `JWT_SIGNING_KEY` | Token signing | Generated with `openssl rand -base64 64` | dev: User Secrets, prod: server env | <name> | Every 6 months |
| `GOOGLE_CLIENT_ID` | Sign in with Google | Google Cloud Console → APIs & Services → Credentials → OAuth client (Web) | `.env` (a public value, not a secret) | <name> | — |
| `GOOGLE_SA_JSON` | Sending through the Gmail API | GCP → IAM → Service Account → Key (JSON) + domain-wide delegation | dev: a gitignored file, prod: a server secret | <name> | Yearly |
| `CLOUDFLARE_API_TOKEN` | DNS/cache management | Cloudflare → My Profile → API Tokens → **a custom token, narrow scope** | GitHub Actions Secret | <name> | Every 6 months |
| `ANTHROPIC_API_KEY` | Claude API | console.anthropic.com → API Keys | prod: server env | <name> | Every 6 months |
| `EXPO_TOKEN` | EAS build (CI) | expo.dev → Account → Access Tokens | GitHub Actions Secret | <name> | Yearly |
| `SENTRY_DSN` | Error tracking | Sentry → Project Settings → Client Keys | `.env` (public) | <name> | — |
| `SMTP_*` / mail | Email | The provider's console | prod: server env | <name> | Yearly |

The rules:
- **The "where to obtain it" column describes the path you click** — "get it from the console" is not enough; write the menu path.
- A secret's **value** is **never** written in this table; only where to get it.
- A public value (a client id, a DSN) is marked distinctly from a real secret.
- A PR that adds a new secret **must** update this table (it is a review checklist item).
- Where the secret can be generated, show the command (`openssl rand -hex 32`).

## 5. `.env.example` rules

```bash
# --- Required ---
DB_CONNECTION=            # Postgres. E.g. Host=localhost;Port=5432;Database=app;Username=app;Password=***
JWT_SIGNING_KEY=          # Generate with openssl rand -base64 64. At least 32 bytes.
API_BASE_URL=             # Web and mobile use this. Local: http://localhost:5080

# --- Optional (the feature turns off when empty) ---
GOOGLE_CLIENT_ID=         # When empty the Google sign-in button is NOT rendered
SENTRY_DSN=               # When empty error tracking is disabled
```

- **Every variable is commented**, with its format and an example.
- The required/optional split is explicit, and what an empty optional value does is written down.
- The application validates the required settings **at start-up** and **stops with a meaningful error** when one is missing (not a mysterious 500 on the first request).
- `.env` is gitignored; `.env.example` is committed. When a new variable appears, both are updated.

## 6. Coming up with one command

The goal:

```bash
git clone <repo> && cd <repo>
cp .env.example .env      # fill in the secrets (SETUP.md §4)
make dev                  # or: docker compose up -d && npm run dev
```

- Installing dependencies, creating the database, migrating and seeding must all be **scripted**.
- If a manual step remains, it goes into `SETUP.md` as a numbered, copy-pasteable command.
- Define a single entry point such as `make dev` / `npm run dev`, and write down what runs on which port.

## 7. The port map (fixed and documented per project)

| Service | Local port | Docker port | Note |
|---|---|---|---|
| API | 5080 | 5080 | Swagger at `/swagger` |
| Web (Vite dev) | 5173 | 3000 | |
| Secondary web | 5174 | — | |
| Postgres | 5432 | 5432 | |
| Redis | 6379 | — | |

A port collision is the most common setup problem — the table belongs in `SETUP.md`.

## 8. The verification step (is the setup complete?)

At the end of `SETUP.md`, **runnable** checks:

```bash
curl -sf http://localhost:5080/health && echo "API OK"
curl -sf http://localhost:5173 > /dev/null && echo "Web OK"
dotnet test --nologo   # or npm test
```

Prefer a criterion verifiable by command over "open it in a browser and look".

## 9. New developer / new machine checklist

- [ ] The prerequisites are installed at the right versions (`node -v`, `dotnet --version` match)
- [ ] `.env` is filled in and the required secrets were obtained
- [ ] The Docker services are up
- [ ] Migrations and the seed have run
- [ ] Every tier came up and `/health` is green
- [ ] The tests pass locally
- [ ] The formatter/linter works in the editor (`.editorconfig`, the ESLint plugin)
- [ ] The git hooks are installed (pre-commit secret scan)
- [ ] Repository access plus the necessary console access (Cloudflare, GCP, the stores) were granted

## 10. When the setup changes

- If a setup step changed, `SETUP.md` is updated **in the same PR**.
- If a new dependency or tool was added, it goes into the prerequisite table.
- A new env variable → `.env.example` + the secret inventory + the start-up validation.
- For an "it used to work on my machine" situation, check in order: version differences (`node -v`, the SDK), a missing env var, a port collision, the state of Docker.
