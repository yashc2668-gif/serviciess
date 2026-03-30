# Staging Setup

Ye file staging deployment ko real me chalane ke liye exact guide hai.

## 1. Kya chahiye

GitHub side:

- repository admin access
- GitHub Actions enabled
- repo secrets add karne ka permission

Server side:

- Ubuntu/Linux server
- public IP ya reachable hostname
- SSH login
- sudo access

## 2. GitHub secrets jo add karne hain

Repository -> `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

Add these secrets:

- `STAGING_HOST`
  - example: `203.0.113.10`
  - ya hostname: `staging.example.com`

- `STAGING_USER`
  - example: `ubuntu`
  - ya jo server login user ho

- `STAGING_SSH_KEY`
  - private key content
  - full multi-line key paste karo

- `STAGING_TARGET_DIR`
  - server par code ka base path
  - example: `/opt/m2n-services-be`

## 3. SSH key pair generate karo

Windows PowerShell:

```powershell
ssh-keygen -t ed25519 -C "staging-deploy" -f $HOME\.ssh\m2n_staging_key
```

Isse 2 files banengi:

- private key: `$HOME\.ssh\m2n_staging_key`
- public key: `$HOME\.ssh\m2n_staging_key.pub`

Public key ko server par add karo.
Private key ka content GitHub secret `STAGING_SSH_KEY` me paste karo.

## 4. Server par public key add karo

Server me login karke:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Test:

```powershell
ssh -i $HOME\.ssh\m2n_staging_key ubuntu@your-server-ip
```

## 5. Server prepare karo

Server me login karke:

```bash
mkdir -p /opt/m2n-services-be/backend
cd /opt/m2n-services-be
```

First-time Docker install:

```bash
cd /opt/m2n-services-be/backend
sudo sh docker/bootstrap-staging-ubuntu.sh
```

## 6. `.env.staging` banao

Server par:

```bash
cd /opt/m2n-services-be/backend
cp .env.staging.example .env.staging
```

Phir `.env.staging` me at least ye real values set karo:

```env
POSTGRES_DB=m2n_staging
POSTGRES_USER=m2n_staging
POSTGRES_PASSWORD=replace-with-strong-password
SECRET_KEY=replace-with-long-random-secret
ENVIRONMENT=production
DEBUG=False
APP_PORT=8000
ALLOWED_ORIGINS=["https://staging.example.com"]
STAGING_BASE_URL=http://127.0.0.1:8000
RUN_DEMO_SEED=true
DEMO_LOGIN_EMAIL=demo-admin@example.com
DEMO_LOGIN_PASSWORD=DemoPass123!
RUN_PREDEPLOY_BACKUP=true
BACKUP_ROOT=backups
BACKUP_UPLOADS=true
```

## 7. Workflow kaun sa run hoga

GitHub Actions workflow:

- `.github/workflows/staging-deploy.yml`

Ye workflow:

- backend folder sync karta hai
- optional pre-deploy backup chalata hai jab `RUN_PREDEPLOY_BACKUP=true`
- server par deploy script run karta hai
- docker compose build/up karta hai
- readiness wait karta hai
- alembic current check karta hai
- demo seed run karta hai
- smoke verify karta hai:
  - `/health`
  - `/health/db`
  - `/docs`
  - login
  - demo project visibility

## 8. Manual first run

GitHub repo me:

- `Actions` open karo
- `Staging Deploy` choose karo
- `Run workflow` click karo

Ya `main` par backend changes push hone par workflow auto-run hoga.

## 9. Successful deploy ke baad verify

Browser me open karo:

- `http://YOUR_SERVER:8000/health`
- `http://YOUR_SERVER:8000/health/db`
- `http://YOUR_SERVER:8000/docs`

Demo login:

- email: `demo-admin@example.com`
- password: `DemoPass123!`

Backup helpers on server:

```bash
cd /opt/m2n-services-be/backend
sh docker/backup-compose-postgres.sh
RESTORE_MODE=scratch sh docker/restore-compose-postgres.sh backups/<backup-label>
```

## 10. Agar workflow fail ho

Check order:

1. GitHub secret names exact same hain ya nahi
2. SSH key server par allowed hai ya nahi
3. `STAGING_TARGET_DIR` writable hai ya nahi
4. `.env.staging` server par present hai ya nahi
5. Docker installed hai ya nahi
6. Port `8000` server par open hai ya reverse proxy configured hai ya nahi

## 11. Fast copy-paste summary

GitHub secrets:

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_SSH_KEY`
- `STAGING_TARGET_DIR`

Server commands:

```bash
mkdir -p /opt/m2n-services-be/backend
cd /opt/m2n-services-be/backend
cp .env.staging.example .env.staging
sudo sh docker/bootstrap-staging-ubuntu.sh
```

GitHub action:

- `Actions` -> `Staging Deploy` -> `Run workflow`
