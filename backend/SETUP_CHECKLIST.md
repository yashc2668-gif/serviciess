# Setup Checklist

Is file ko top-to-bottom follow karo. Har step complete hone par checkbox tick karo.

## 1. Basic tools

- [ ] `git` installed hai
- [ ] `python 3.12+` installed hai
- [ ] `postgresql` installed hai
- [ ] `docker` installed hai
- [ ] `docker compose` installed hai

Check commands:

```powershell
git --version
python --version
docker --version
docker compose version
```

## 2. Repo ready karo

- [ ] Repo cloned hai
- [ ] Backend folder open hai

Clone command:

```powershell
git clone https://github.com/yashc2668-gif/m2n-services-be.git
cd m2n-services-be\backend
```

## 3. MCP / agent tools start karo

- [ ] `agent firewall` start kiya
- [ ] `playwright` MCP server running hai
- [ ] `github-mcp-server` running hai

Expected result:

- firewall status `running`
- playwright status `running`
- github MCP status `running`

## 4. Local env file banao

- [ ] `.env.example` se `.env` copy ki
- [ ] `SECRET_KEY` set ki
- [ ] DB credentials set ki
- [ ] `ALLOWED_ORIGINS` check ki

Command:

```powershell
Copy-Item .env.example .env
```

Minimum values in `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=m2n_db
POSTGRES_USER=m2n_app
POSTGRES_PASSWORD=m2n_app_123
SECRET_KEY=replace-with-a-long-random-secret
ENVIRONMENT=development
DEBUG=True
APP_PORT=8000
```

## 5. Python environment ready karo

- [ ] virtual environment ban gaya
- [ ] venv activate hua
- [ ] requirements install hui

Commands:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 6. Database ready karo

- [ ] PostgreSQL chal raha hai
- [ ] database `m2n_db` create hai
- [ ] user `m2n_app` create hai
- [ ] `.env` credentials same hain

## 7. Migrations run karo

- [ ] Alembic head apply hua
- [ ] current revision dikha

Commands:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m alembic current
```

Expected:

- current revision should show `head`

## 8. Seed data run karo

- [ ] roles seed hue
- [ ] optional admin seed hua
- [ ] demo seed run hua

Commands:

```powershell
.\venv\Scripts\python.exe -m app.db.seed
.\venv\Scripts\python.exe -m app.db.demo_seed
```

Demo login:

- email: `demo-admin@example.com`
- password: `DemoPass123!`

## 9. App start karo

- [ ] FastAPI app start hui

Command:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 10. Local verification

- [ ] `/health` open hua
- [ ] `/health/db` open hua
- [ ] `/health/ready` open hua
- [ ] `/docs` open hua
- [ ] login worked
- [ ] demo projects visible hain

URLs:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/db`
- `http://127.0.0.1:8000/health/ready`
- `http://127.0.0.1:8000/docs`

## 11. Test run

- [ ] full test suite pass hui

Command:

```powershell
.\venv\Scripts\python.exe -m unittest discover app/tests -v
```

## 12. Staging secrets ready karo

Ye values GitHub Actions ya deploy system me chahiye hongi:

- [ ] `STAGING_HOST`
- [ ] `STAGING_USER`
- [ ] `STAGING_SSH_KEY`
- [ ] `STAGING_TARGET_DIR`

## 13. Staging env file banao

- [ ] `.env.staging.example` se `.env.staging` copy ki
- [ ] production `SECRET_KEY` set ki
- [ ] real DB password set ki
- [ ] strict CORS origin set ki

Command:

```powershell
Copy-Item .env.staging.example .env.staging
```

## 14. Staging server prepare karo

- [ ] Ubuntu/Linux server accessible hai
- [ ] Docker installed hai
- [ ] Docker Compose plugin installed hai
- [ ] target directory create hai

Server bootstrap command:

```bash
sudo sh docker/bootstrap-staging-ubuntu.sh
```

## 15. Staging deploy

- [ ] workflow files repo me pushed hain
- [ ] GitHub secrets configured hain
- [ ] deploy script run hua

Commands on staging host:

```bash
cd backend
sh docker/deploy-staging.sh
```

## 16. Staging verification

- [ ] app boot hui
- [ ] migrations run hui
- [ ] `/health` OK
- [ ] `/health/db` OK
- [ ] `/docs` open hui
- [ ] demo login worked
- [ ] demo seed data visible hai

## 17. Jab mujhe update dena ho

Ye message copy karke bhej do:

```text
Basic setup done
Repo cloned
MCP servers running
.env ready
DB ready
Migrations done
Demo seed done
App running
```

Ya agar kisi step par atak jao to sirf ye bhejo:

```text
Main step 4 par atka hoon
```

Phir main usi step ka exact solution dunga.
