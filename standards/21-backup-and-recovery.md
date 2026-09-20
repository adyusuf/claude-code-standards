# Backup and disaster recovery

> **An untested backup is not a backup.** The only purpose of this file is to make
> that sentence real. "We take backups" is not an acceptable answer — "we restored
> one last month and it took X minutes" is.

## 1. The 3-2-1 rule

- **3** copies (production + two backups)
- **2** different media/environments
- **1** copy **off the server** (a different physical or cloud location)

A backup sitting on the same machine is gone when the machine is. A cloud backup
in the same account is gone when the account is compromised.

## 2. What are we backing up? (the inventory — the most common gap)

| Asset | Method | Frequency | Retention | Where |
|---|---|---|---|---|
| **The database** | `pg_dump` / native backup | Daily full + hourly WAL/log | 30 days + monthly for 12 months | Server + offsite |
| **User files** (uploads, R2/S3/blob) | Bucket replication / rsync | Daily | 30 days | A different region/account |
| **Application configuration** (env, appsettings, IIS/nginx conf) | A script + an encrypted archive | On change + weekly | 90 days | Offsite |
| **Secrets** | A password manager / secret-store backup | On change | — | Separate, encrypted |
| **Certificates** (especially the Cloudflare origin certificate) | An encrypted archive | On renewal | For their validity | Offsite |
| **Code** | A git remote (GitHub) | Per push | Indefinite | + a local mirror |
| **CI/CD configuration** (workflows, the list of secrets) | IaC / documented | On change | — | The repo + `DEPLOY.md` |
| **DNS / Cloudflare rules** | Export / Terraform state | On change | — | The repo |
| **Logs / audit** (where there is a legal retention duty) | An archive | Daily | Per regulation | Offsite |

**Backing up only the database is incomplete.** When the files a user uploaded are
gone, the database rows become empty references.

## 3. Targets — they must be written down

| Target | Definition | Example value |
|---|---|---|
| **RPO** | The maximum acceptable **data loss** | ≤ 1 hour (with hourly WAL) |
| **RTO** | The maximum acceptable **downtime** | ≤ 4 hours |

- RPO determines backup frequency; RTO determines how fast the restore procedure has to be.
- The targets are a user/product decision — never assumed technically, always **asked**.
- If a target cannot be met, that is a risk and it is accepted in writing.

## 4. Backup rules

- **Automatic.** A backup taken by hand gets forgotten. Use a scheduled job (cron / Task Scheduler / a managed backup).
- **Encrypted.** A backup file never sits unencrypted; the decryption key lives **separately** from the backup (otherwise the key is lost along with it).
- **Access-restricted.** The account with write access to the backup store should not have delete rights (ransomware deletes backups too). Use **immutable / object-lock** where possible.
- **Integrity verification.** After a backup is taken, a checksum plus an openability check (something like `pg_restore --list`).
- **Size and duration are monitored.** If the backup size suddenly drops (a lost table, say), alert.
- **Compression + retention policy:** 30 daily, 12 weekly, 12 monthly (GFS) — tuned per project.
- **A backup containing PII** is within data-protection scope too: retention, deletion requests and access records all have to be considered.

## 5. Monitoring and alerts (critical)

- [ ] An alert when the backup job **fails**
- [ ] An alert when the backup job **never ran at all** (the silent death — the most dangerous; check "last successful backup > 26 hours ago")
- [ ] The backup size is below expectations → alert
- [ ] Offsite copying failed → alert
- [ ] The backup store is filling up → alert

The sentence "we thought backups were being taken" is what you hear when
monitoring was never set up.

## 6. The restore drill — once a month, MANDATORY

The drill steps (with a record kept):

```
1. Was the latest backup downloaded from the OFFSITE copy?   (not the one on the server — offsite is what gets tested)
2. It was restored into an isolated environment (a test database / a temporary container)
3. The duration was measured   → does it meet the RTO target?
4. Verification queries        → row counts, the date of the newest record, are the critical tables populated
5. Does the application come up against this restored database?
6. The result was recorded: the date, the backup's timestamp, the duration, any problem, the action
```

- The drill result is kept **with its date** in a file such as `docs/backup-drills.md`.
- If a drill fails, that is **an incident** — the root cause is found and fixed.
- At least once a year, a **full disaster rehearsal**: a from-scratch rebuild from the "the server is completely gone" scenario (`DEPLOY.md` + the backups).

## 7. A manual backup before risky work

A manual backup is taken and verified **before** any of these:

- A migration containing `DROP` / `ALTER TYPE` / a column removal
- A bulk `UPDATE`/`DELETE`
- A large data move
- A server/OS/database version upgrade
- A risky deploy to production

The order: **take the backup → verify it → rehearse in the test environment → apply in production.**

## 8. Restore scenarios and the runbook

For every scenario there must be step-by-step commands in `DEPLOY.md`/`RUNBOOK.md`:

| Scenario | The first move |
|---|---|
| Accidentally deleted records | Point-in-time restore into a **separate** database, then copy the rows across. Never overwrite production. |
| A broken migration | Reverse the migration or restore from a backup; cut the traffic / turn off the feature flag first |
| A lost server | A new server (`DEPLOY.md` from-scratch install) + the latest backup + a DNS switch |
| Ransomware | Restore from the immutable/offsite copy; **rotate** every compromised credential |
| A lost cloud account | The copy in a different provider/account — which is exactly why offsite must not be in the same account |
| Data corruption (noticed late) | You need older backups → that is why monthly retention exists |

Runbook commands must be **copy-pasteable**; nobody improvises during an incident.

## 9. Backup setup checklist (a new project/server)

- [ ] The automatic database backup job is installed and **its first run was verified**
- [ ] Offsite copying is set up and verified
- [ ] User files (R2/S3/disk) are in scope
- [ ] Configuration + certificates + the secret inventory are backed up
- [ ] Backups are encrypted; the key lives elsewhere
- [ ] The retention policy (GFS) is defined and there is enough disk
- [ ] Alerts exist for failure **and** for never-ran
- [ ] RPO/RTO are written down and approved by the user
- [ ] The first restore drill was performed and its duration recorded
- [ ] The runbook is written (`DEPLOY.md` / `RUNBOOK.md`)
- [ ] The monthly drill is on the calendar

## 10. Never-do list

- ❌ A backup that only sits on the same server
- ❌ An unencrypted backup file
- ❌ A backup whose restore was never attempted
- ❌ A backup job with no monitoring or alert
- ❌ Giving the backup account delete rights as well
- ❌ Backing up only the database and skipping user files
- ❌ Keeping the encryption key in the same place as the backup
- ❌ Running a migration containing `DROP` without a backup
- ❌ Assuming the RPO/RTO (it is a product decision, so ask)
