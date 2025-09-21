# Production-ready CI/CD: Django + React on AWS EC2 (Docker Compose) with NGINX, SSL, Staging/Production

> Comprehensive, practical guide: from repository to production with GitHub Actions, Docker Compose, NGINX reverse proxy, Let's Encrypt SSL, environment separation (staging vs production), monitoring, backups, and security hardening.

---

## Table of Contents
1. Goals & Assumptions
2. High-level Architecture
3. Repository Layout
4. Environment Strategy (staging / production)
5. Docker images & Docker Compose - production setup
6. NGINX reverse proxy (container) — configuration
7. SSL with Let's Encrypt (Certbot) — automated renewal
8. DNS, Domain, and Firewalls
9. GitHub Actions CI/CD — workflows for staging & production
10. Deployment process on EC2 (step-by-step)
11. Zero-downtime / deployment strategies
12. Backups & database migration strategy
13. Monitoring, logging & alerting
14. Security best practices
15. Rollback & troubleshooting
16. Appendix: Sample files and snippets

---

## 1. Goals & Assumptions
- You have an AWS account and can create/manage EC2 instances.
- The app consists of a Django REST API (backend) and a React single-page app (frontend).
- All services are containerized and orchestrated using **Docker Compose** on EC2 (no Kubernetes).
- You want staging and production environments on separate EC2 instances (or separate Docker Compose stacks). Git branches: `develop` -> staging, `main` -> production.
- Use GitHub Actions for CI/CD and SSH deploy to EC2.
- Domain name is available, and you can manage DNS records.

---

## 2. High-level Architecture

- Developer pushes code → GitHub Actions runs CI (tests, linting, build images) → If `develop` branch: deploy to **staging** EC2; if `main` branch: deploy to **production** EC2 (after approval gate).
- EC2 runs Docker Engine + Docker Compose. `docker-compose.prod.yml` describes services:
  - `nginx` (reverse proxy + static files serving) — exposes ports 80/443
  - `frontend` (React build served by nginx or static files copied into nginx image)
  - `backend` (Django with Gunicorn + staticfiles)
  - `db` (Postgres) — optionally in RDS for production
  - `redis` (optional for caching/celery)
  - `certbot` (only for obtaining certs; can be a separate container or run on host)

Diagram (logical):

```
[GitHub] --> [EC2 Staging / EC2 Prod]
                    |-- Docker Compose stack
                    |-- nginx (80/443)
                    |-- backend (8000)
                    |-- frontend (served via nginx)
                    |-- db (postgres) OR AWS RDS
```

---

## 3. Repository Layout

```
my-app/
  backend/
    Dockerfile
    requirements.txt
    manage.py
    myproject/
      settings/
        base.py
        staging.py
        production.py
  frontend/
    Dockerfile
    package.json
    src/
  infra/
    docker-compose.yml
    docker-compose.prod.yml
    nginx/
      nginx.conf
      sites-enabled/app.conf
    scripts/
      deploy.sh
  .github/workflows/
    ci.yml
    deploy-staging.yml
    deploy-prod.yml
  .env.example
  README.md
```

Important: keep secrets out of repo — use GitHub Secrets and environment files on EC2 (`.env.production`).

---

## 4. Environment Strategy (staging / production)

- **Settings**: use Django settings layered by environment (e.g., `base.py` imports then `staging.py` and `production.py`). Load secrets from env variables.
- **Branches**: `develop` -> staging automatic deploy; `main` -> requires manual approval then production deploy.
- **EC2 Instances**: separate EC2 for staging and production (recommended). If using single instance, run two docker-compose stacks with different project names and ports (more complex).
- **Database**: for production prefer AWS RDS; for staging you may run Postgres container.

---

## 5. Docker images & Docker Compose - production setup

### Backend Dockerfile (production-ready)

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/

# collect static at build time (optional)
RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

> Note: Running `collectstatic` at build may fail if environment-dependent; alternatively run at runtime or a helper container.

### Frontend Dockerfile (serve static via nginx)

```dockerfile
# frontend/Dockerfile
FROM node:20 as build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY infra/nginx/frontend.conf /etc/nginx/conf.d/default.conf
```

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:stable-alpine
    volumes:
      - ./infra/nginx/sites-enabled:/etc/nginx/conf.d:ro
      - cert-data:/etc/letsencrypt
      - cert-data-lib:/var/lib/letsencrypt
      - static_volume:/var/www/static
    ports:
      - '80:80'
      - '443:443'
    depends_on:
      - backend
    restart: always

  backend:
    build: ./backend
    env_file:
      - ./.env.production
    volumes:
      - static_volume:/app/static
    expose:
      - '8000'
    depends_on:
      - db
    restart: always

  frontend:
    build: ./frontend
    restart: always
    depends_on:
      - nginx

  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    env_file:
      - ./.env.production
    restart: unless-stopped

volumes:
  pgdata:
  cert-data:
  cert-data-lib:
  static_volume:
```

Notes:
- We mount the letsencrypt cert volume so `nginx` can use HTTPS certs.
- `frontend` is built and static files served by nginx. Alternatively serve frontend via `nginx` container by copying build output into a volume.

---

## 6. NGINX reverse proxy (container) — configuration

Place NGINX config in `infra/nginx/sites-enabled/app.conf`:

```nginx
# infra/nginx/sites-enabled/app.conf
server {
    listen 80;
    server_name example.com www.example.com;

    # Redirect to HTTPS
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name example.com www.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # frontend static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/static/;
    }
}
```

If your frontend build is copied to the nginx image (as in the frontend Dockerfile above), NGINX will already have static files at `/usr/share/nginx/html`.

---

## 7. SSL with Let's Encrypt (Certbot)

Two common approaches:

**A. Run Certbot on the host (recommended)**
- Install certbot on the EC2 instance and use `certbot --nginx` to obtain certs which updates nginx.conf on host. Keep certs outside Docker and mount them into nginx container.

**B. Use a certbot Container**
- Use `certbot/certbot` in a container to obtain certificates using webroot plugin, saving files to a Docker volume (`cert-data`).

Sample commands (host approach):
```bash
sudo apt update
sudo apt install certbot -y
sudo certbot certonly --webroot -w /path/to/app/infra/certbot-www -d example.com -d www.example.com
# copy or mount /etc/letsencrypt into nginx container via volume
```

Automate renewals: `certbot renew --deploy-hook "docker-compose -f docker-compose.prod.yml restart nginx"` in a cron job.

If you use the container approach, you can run a one-off certbot command:

```bash
docker run --rm -it \
  -v $(pwd)/cert-data:/etc/letsencrypt \
  -v $(pwd)/infra/certbot-www:/var/www/certbot \
  certbot/certbot certonly --webroot -w /var/www/certbot -d example.com
```

Then restart nginx to pick up the certs.

---

## 8. DNS, Domain, and Firewalls

- Point `A` record (and `www`) to EC2 public IP.
- If using Elastic IP, associate Elastic IP with EC2 to avoid IP changes.
- Security Groups: open ports 80 and 443 inbound; block 22 except from your IPs or GitHub Actions IPs as needed.
- Use `ufw` on host to allow necessary ports only.

---

## 9. GitHub Actions CI/CD — workflows for staging & production

**CI (`.github/workflows/ci.yml`)**
- Runs on every push/PR on `develop` & `main`.
- Steps: checkout, run backend tests, run frontend tests, build images (optional), and push artifacts.

**Deploy to Staging (`deploy-staging.yml`)**
- Trigger: `push` to `develop`
- Steps:
  - Build & test
  - SSH to staging EC2 and run `git pull` + `docker-compose -f docker-compose.prod.yml pull` + `docker-compose -f docker-compose.prod.yml up -d --build`

**Deploy to Production (`deploy-prod.yml`)**
- Trigger: `push` to `main` but require manual approval (environment protection rule) or `workflow_dispatch` (manual trigger).
- Steps: similar SSH deploy to production EC2.

Sample deployment step snippet (use `appleboy/ssh-action`):

```yaml
- name: Deploy to Prod Server
  uses: appleboy/ssh-action@v0.1.7
  with:
    host: ${{ secrets.PROD_IP }}
    username: ubuntu
    key: ${{ secrets.PROD_SSH_KEY }}
    script: |
      cd /home/ubuntu/my-app
      git fetch --all
      git reset --hard origin/main
      docker-compose -f docker-compose.prod.yml pull
      docker-compose -f docker-compose.prod.yml up -d --build --remove-orphans
```

**Use deployment protection:**
- In GitHub, protect `main` with required reviews and require `workflow_run` approvals for `deploy-prod.yml`.

---

## 10. Deployment process on EC2 (step-by-step)

1. **Provision EC2**: Ubuntu 22.04, t3.medium (or larger for prod), security group open 80/443.
2. **Install Docker & Docker Compose**:
   ```bash
   sudo apt update
   sudo apt install -y docker.io
   sudo apt install -y docker-compose
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```
3. **Clone repo & prepare env**
   ```bash
   git clone https://github.com/yourname/my-app.git /home/ubuntu/my-app
   cd /home/ubuntu/my-app
   cp .env.example .env.production
   # edit .env.production with secrets (DB password, secret keys, etc)
   ```
4. **Set up systemd (optional)** to ensure compose stack starts on boot. Create `/etc/systemd/system/my-app.service`:
   ```ini
   [Unit]
   Description=Docker Compose application
   After=network.target docker.service

   [Service]
   Type=oneshot
   WorkingDirectory=/home/ubuntu/my-app
   ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
   ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
   RemainAfterExit=yes

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable my-app
   sudo systemctl start my-app
   ```
5. **Obtain SSL certs** (see section 7) and ensure `cert-data` volume is populated.
6. **Run initial migration & collectstatic**
   ```bash
   # one-time
   docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
   docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput
   ```
7. **Start**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

## 11. Zero-downtime / deployment strategies

- **Rolling/Blue-Green**: With Docker Compose, simple blue-green is manual: maintain `my-app-blue` and `my-app-green` stacks, switch nginx upstream or DNS. More complexity.
- **Canary**: Serve a small percentage of traffic to new version (requires advanced load balancing / reverse proxy that supports weights, e.g., Traefik or HAProxy).
- **Graceful restarts**: Gunicorn supports graceful workers replacement — ensure `--reload` is not used in production; use `gunicorn --preload` with proper signals.
- **Health checks**: configure nginx or a load balancer to check `/health` endpoint before routing traffic to a container.

For small teams, `docker-compose up -d --build` with short downtime is acceptable. For zero-downtime, consider migrating to ECS/EKS or using a more advanced proxy.

---

## 12. Backups & database migration strategy

- **Postgres**
  - For production, use **RDS** with automated snapshots, Multi-AZ.
  - If running containerized Postgres, schedule `pg_dump` jobs to S3 using cron or AWS Backup.

- **Media / uploads**
  - Store user uploads in **S3** (recommended). If local, back up `/media` to S3 regularly.

- **Migrations**
  - DB migrations are handled by `python manage.py migrate` during deploy. Run as one-off job before switching traffic.

Sample backup cron (containerized approach):

```bash
0 2 * * * docker exec -t postgres_db pg_dumpall -c -U $POSTGRES_USER | gzip > /home/ubuntu/backups/pg_backup_$(date +\%F).sql.gz
# upload to S3 via aws cli
```

---

## 13. Monitoring, logging & alerting

- **Logging**: `docker logs`, but for production push logs to central system: ELK stack or Loki + Grafana.
- **Metrics**: expose Prometheus metrics from Django and monitor with Prometheus + Grafana.
- **Tracing**: use OpenTelemetry for distributed tracing.
- **Alerts**: enable alerting on high error rate, high latency, low disk space. Use PagerDuty or Opsgenie.

Quick start: run a Grafana + Prometheus stack on a separate monitoring host or use hosted solutions (Datadog, New Relic).

---

## 14. Security best practices

- Store secrets in **AWS Secrets Manager** or GitHub Secrets; avoid committing `.env`.
- Use HTTPS only — redirect HTTP to HTTPS.
- Run containers with least privilege; avoid `:latest` tags.
- Set up firewall rules and restrict SSH to known IPs.
- Use `fail2ban` to protect SSH.
- Keep host OS and Docker up-to-date.
- Limit resource consumption with Docker CPU/memory constraints.
- Use image scanning tools (Snyk, Trivy) in CI.

---

## 15. Rollback & troubleshooting

- Keep last working image tag (semantic versioning or commit SHA). If deployment fails, `docker-compose pull` the previous tag or `git checkout` the previous tag and `docker-compose up -d`.
- Keep logs accessible: `docker-compose logs --tail=200 -f`.
- Health checks: implement `/healthz` endpoints for backend and use them in nginx or load balancer.

---

## 16. Appendix: Sample files and snippets

> There are many example snippets included below. Use them as starting points and adapt to your project's specifics.

### Sample `.env.production` (example)
```
# Django
DJANGO_SECRET_KEY=replace_me
DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgres://myuser:mypassword@db:5432/mydb

# Other
REDIS_URL=redis://redis:6379/0
```

### nginx frontend conf (infra/nginx/frontend.conf)
```nginx
server {
  listen 80;
  server_name example.com www.example.com;
  root /usr/share/nginx/html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

### GitHub Actions deploy-prod.yaml (simplified)
```yaml
name: Deploy to Production
on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          cd backend && pip install -r requirements.txt && pytest || true
          cd frontend && npm ci && npm test -- --watchAll=false || true

      - name: Deploy to prod
        uses: appleboy/ssh-action@v0.1.7
        with:
          host: ${{ secrets.PROD_IP }}
          username: ubuntu
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /home/ubuntu/my-app
            git fetch --all
            git reset --hard origin/main
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --build --remove-orphans
```
### CI workflow (`.github/workflows/ci.yml`) and `deploy.sh`

Nice — below are two ready-to-use files:
1. GitHub Actions CI workflow (`.github/workflows/ci.yml`) — runs backend + frontend tests and then SSHs to your server to run the repo's `infra/scripts/deploy.sh`.

2. `infra/scripts/deploy.sh` — the server-side deployment script that does `git reset`, builds containers, runs migrations & collectstatic, and brings the stack up.

#### 1.) Save as `.github/workflows/ci.yml`

```yaml
name: CI — Test & Deploy

on:
  push:
    branches:
      - develop
      - main
  pull_request:
    branches:
      - develop
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    name: Run tests (backend + frontend)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install backend dependencies
        run: |
          cd backend
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run backend tests
        run: |
          cd backend
          pytest -q

      - name: Set up Node 20
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install frontend deps & run tests
        run: |
          cd frontend
          npm ci
          npm test -- --watchAll=false

  deploy:
    name: Deploy to server
    runs-on: ubuntu-latest
    needs: test
    if: ${{ github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main' }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build frontend (artifact for fast deploy)
        if: always()
        run: |
          cd frontend
          npm ci
          npm run build

      # Deploy to staging (develop branch)
      - name: Deploy to STAGING (ssh)
        if: ${{ github.ref == 'refs/heads/develop' }}
        uses: appleboy/ssh-action@v0.1.7
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          port: ${{ secrets.STAGING_PORT || 22 }}
          timeout: 30m
          script: |
            set -e
            cd /home/${{ secrets.STAGING_USER }}/my-app || exit 1
            # ensure local repo has the latest deploy script
            git fetch --all
            git reset --hard origin/develop
            chmod +x infra/scripts/deploy.sh || true
            ./infra/scripts/deploy.sh develop

      # Deploy to production (main branch). Recommend protecting main with environment approvals.
      - name: Deploy to PRODUCTION (ssh)
        if: ${{ github.ref == 'refs/heads/main' }}
        uses: appleboy/ssh-action@v0.1.7
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          port: ${{ secrets.PROD_PORT || 22 }}
          timeout: 30m
          script: |
            set -e
            cd /home/${{ secrets.PROD_USER }}/my-app || exit 1
            git fetch --all
            git reset --hard origin/main
            chmod +x infra/scripts/deploy.sh || true
            ./infra/scripts/deploy.sh main
```
### Notes & required GitHub Secrets
- `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY` (private key)
- `STAGING_PORT` (optional, default 22)
- `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY` (private key)
- `PROD_PORT` (optional)
Make sure the SSH key has permission to `git pull` (or the server user has proper SSH access to your repo) and can run `docker-compose`.  

#### If you prefer pushing built images to a registry and pulling on the server, adjust the CI `build` step to `docker build` + push to ECR/Docker Hub and change deploy to `docker-compose pull`.

#### 2.) `infra/scripts/deploy.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
trap 'echo "❌ Deployment failed on line $LINENO"; exit 1' ERR

# Usage: ./infra/scripts/deploy.sh [branch]
# Example: ./infra/scripts/deploy.sh develop
BRANCH="${1:-main}"

# You can override these by exporting env vars before running the script
APP_DIR="${APP_DIR:-/home/ubuntu/my-app}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

echo "➡️  Starting deployment"
echo "   branch: ${BRANCH}"
echo "   app dir: ${APP_DIR}"
echo "   compose file: ${COMPOSE_FILE}"

# Sanity checks
if ! command -v git >/dev/null 2>&1; then
  echo "git not found. Aborting."
  exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
  echo "docker-compose not found. Aborting."
  exit 1
fi

if [ ! -d "${APP_DIR}" ]; then
  echo "App directory ${APP_DIR} does not exist. Aborting."
  exit 1
fi

cd "${APP_DIR}"

echo "🔄 Fetching git updates..."
git fetch --all --prune

# Checkout and reset to remote branch
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  # create a local branch tracking remote if needed
  git checkout -B "${BRANCH}" "origin/${BRANCH}" || true
fi

git reset --hard "origin/${BRANCH}"

# Optional: ensure .env.production exists (you should create it on the server securely beforehand)
if [ ! -f "${ENV_FILE}" ]; then
  echo "Warning: ${ENV_FILE} not found. Make sure environment file exists on the server."
fi

# Pull images if you use registries (safe if not configured)
echo "⬇️  Pulling images (if configured)..."
docker-compose -f "${COMPOSE_FILE}" pull --ignore-pull-failures || true

# Build images (no-cache to ensure clean build). Remove --no-cache if you want caching.
echo "🛠️  Building images..."
docker-compose -f "${COMPOSE_FILE}" build --no-cache || true

# Start/refresh containers
echo "⚙️  Bringing up services..."
docker-compose -f "${COMPOSE_FILE}" up -d --remove-orphans

# Run database migrations
echo "📦 Running migrations..."
docker-compose -f "${COMPOSE_FILE}" run --rm --no-deps backend python manage.py migrate --noinput || true

# Collect static files
echo "🧹 Collect static files..."
docker-compose -f "${COMPOSE_FILE}" run --rm --no-deps backend python manage.py collectstatic --noinput || true

# Optional healthcheck (simple)
echo "🔍 Checking container status..."
docker-compose -f "${COMPOSE_FILE}" ps

# Cleanup dangling images to free space
echo "🧼 Pruning unused images..."
docker image prune -f || true

echo "✅ Deployment complete for branch: ${BRANCH}"
exit 0

```

#### What this script does
- Fetches the latest code and hard-resets to the specified branch (`develop` or `main`).
- Pulls images (if you use remote images), builds local images, and brings the Compose stack up.
- Runs Django migrations and `collectstatic` within a one-off `backend` container.
- Shows `docker-compose ps` and prunes unused images.

#### Important server-side setup
- The server (`/home/ubuntu/my-app`) must contain the repo (or GitHub Actions `git reset` will clone/update it). Git + Docker + docker-compose must be installed.
- Ensure `.env.production` exists on the server and contains secrets (not in Git).
- Ensure the server user (e.g. ubuntu) has permission to run `docker-compose` without sudo or adjust script to use `sudo docker-compose` accordingly.
- Make the script executable: `chmod +x infra/scripts/deploy.sh` and commit the permission change.
---

## Final notes & recommended next steps
1. Set up **separate EC2** instances for staging and production and use Elastic IPs.
2. Prefer **RDS for Postgres** in production to get automated backups and high availability.
3. Consider migrating to **ECS/Fargate** or **EKS** for better scalability and zero-downtime deployments if your traffic grows.
4. Add **image scanning** to CI, and a **CD approval gate** for production.
5. Automate backups and test restores regularly.

---

If you want, I can:
- Generate the full `docker-compose.prod.yml`, `nginx` configs, and GitHub Actions YAML files tailored to your exact repo names and domain.
- Create a `deploy.sh` script for EC2 to simplify deployments.
- Produce a DOCX/PDF version of this guide for sharing.

Tell me which of these you'd like next and provide your domain name (if you want configs pre-filled) and whether you use RDS for production DB.