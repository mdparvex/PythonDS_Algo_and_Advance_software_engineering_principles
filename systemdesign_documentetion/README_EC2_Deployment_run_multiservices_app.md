Multiple services are running same EC2 with docker-compose. Explained how they manage in EC2.

Perfect 👍 this is a very real-world situation, and I can see where the confusion is happening. Let me clear it step by step:

**🔹 1. One EC2, Many Services**

Yes — in your current setup, you’re running **many services inside a single EC2 instance** using Docker Compose.

- EC2 = one virtual server
- Inside EC2 → Docker Compose launches multiple **containers** (Postgres, Redis, Django APIs, Celery workers, etc.)
- All services share **the same EC2 public IP address**
- You expose different services by **binding different container ports → host ports** (like 8010, 8011, 8112 etc.)

👉 That’s why in your docker-compose.yaml, each service has a port mapping like "8010:80".  
So if your EC2 public IP = 3.93.12.100, then:

- <http://3.93.12.100:8010> → student service
- <http://3.93.12.100:8011> → API service
- <http://3.93.12.100:8012> → API cron
- etc.

⚠️ AWS does **not** give you a new IP per service/container. One EC2 → one public IP.  
If you want different IPs per service, you’d need **separate EC2 instances** (rarely efficient) or container orchestrators like **ECS/EKS/Kubernetes**.

**🔹 2. Mapping to DNS**

You typically don’t expose :8010, :8011, etc. directly in production. Instead, you use a **reverse proxy (Nginx or Traefik)** in front:

Example:

- api.example.com → forwards traffic to your **API container (8011)**
- student.example.com → forwards traffic to your **student container (8010)**
- teacher.example.com → forwards traffic to your **teacher container (8013)**

This way, users never see the raw port numbers. Everything goes through **port 80/443** at Nginx.

**🔹 3. Deployment Flow (from local → AWS)**

Here’s the **clean production flow** you should follow:

**🛠️ Step 1: Develop & Dockerize Locally**

- Each service has its own Dockerfile
- Test with docker-compose up locally

**🛠️ Step 2: Push to GitHub/GitLab**

- Keep all service code + docker-compose.yaml in repo

**🛠️ Step 3: Provision EC2**

- Create EC2 (Ubuntu 22.04 recommended)
- Install Docker + Docker Compose

```bash
sudo apt update && sudo apt install -y docker.io docker-compose
```

**🛠️ Step 4: Deploy**

- Clone repo into EC2
- Run:
```bash
docker-compose up -d --build
```
- All containers will run inside **one EC2**

**🛠️ Step 5: Add Nginx Reverse Proxy**

- Run **Nginx in front** of all services (like I showed earlier)
- Nginx listens on port 80/443 and routes based on **domain name**

Example Nginx config (nginx.conf):

```nginx
http {
    server {
        listen 80;
        server_name api.example.com;

        location / {
            proxy_pass http://api:8000;  # API container
        }
    }

    server {
        listen 80;
        server_name student.example.com;

        location / {
            proxy_pass http://student:80; # student container
        }
    }

    server {
        listen 80;
        server_name teacher.example.com;

        location / {
            proxy_pass http://teacher:80; # teacher container
        }
    }
}
```

**🛠️ Step 6: Point DNS to EC2**

- In your domain registrar (GoDaddy, Cloudflare, Route53, etc.):
  - Add an **A record**:

    ```php-template
    api.example.com → <EC2_PUBLIC_IP>
    student.example.com → <EC2_PUBLIC_IP>
    teacher.example.com → <EC2_PUBLIC_IP>
    ```
- Now users can call APIs directly with subdomains.

**🔹 4. When You Outgrow One EC2**

Right now:

- One EC2 = all services
- Nginx = reverse proxy for routing

Later, when traffic grows:

- Use **AWS ALB (Application Load Balancer)** or **ECS/EKS** to spread containers across **multiple EC2s**
- Use **AWS Auto Scaling** to add/remove servers automatically
- At that stage, you stop thinking about “one EC2 running everything” and move to **orchestration**

✅ **Summary**

- One EC2 = one IP → all containers share it
- Services are separated by **ports internally**
- Expose them via **Nginx reverse proxy** and **domain names** (instead of :8010)
- For production:
  - **Single EC2 + Docker Compose + Nginx** is fine for MVP/small projects
  - **ECS/EKS + ALB + multiple EC2s** is the way for scale

   

------------------------------------------------------------------------
  # Deep Dive The practical Deployment in AWS
  **Nginx configuration**

```yaml
services:
  search-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: search-service
    environment:
      - ELASTICSEARCH_HOST=http://esearch:9200
    depends_on:
      - esearch
    restart: always
    networks:
      - medeasy-network

  esearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.1.5
    build:
      context: .
      dockerfile: Dockerfile.elasticsearch
    container_name: esearch
    env_file:
      - ./core/.env
    volumes:
      - esdata:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://esearch:9200 || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 10
    restart: always
    networks:
      - medeasy-network
  nginx:
    container_name: nginx
    build:
      context: ./
      dockerfile: nginx/prod/Dockerfile
    depends_on:
      - search-service
    volumes:
      - ./certificates:/etc/nginx/certificates
    ports:
      - "80:80"
      - "443:443"
    restart: always
    networks:
      - medeasy-network

volumes:
  esdata:
networks:
  medeasy-network:
    external: true

```
```dockerfile
FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

```

```dockerfile
# Use the official Elasticsearch image as base
FROM docker.elastic.co/elasticsearch/elasticsearch:9.1.5

# Install the ICU plugin
#RUN elasticsearch-plugin install --batch analysis-icu
RUN if [ ! -d "/usr/share/elasticsearch/plugins/analysis-icu" ]; then \
      elasticsearch-plugin install --batch analysis-icu; \
    fi

# Copy stopwords/synonyms with correct owner
COPY --chown=elasticsearch:elasticsearch ./esconfig/stopwords /usr/share/elasticsearch/config/stopwords
COPY --chown=elasticsearch:elasticsearch ./esconfig/synonyms /usr/share/elasticsearch/config/synonyms

```
```dockerfile
FROM nginx
RUN apt-get update && apt-get install -y openssl

COPY ./nginx/prod/app.conf /etc/nginx/conf.d/default.conf

```

```nginx
upstream api {
    server search-service:8000;
}

server {
    listen 80;
    server_name search.medeasy.health www.search.medeasy.health;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name search.medeasy.health www.search.medeasy.health;
    server_tokens off;
    error_page 497 301 =307 https://$host$request_uri;

    ssl_certificate /etc/nginx/certificates/fullchain.pem;
    ssl_certificate_key /etc/nginx/certificates/private.key;
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:DES-CBC3-SHA:!aNULL:!MD5:!DSS';

    access_log  /var/log/nginx/example.log;

    location / {
        client_body_buffer_size     200M;
        client_max_body_size        200M;
        try_files $uri $uri/ @python_django;
    }

    location @python_django {
        client_body_buffer_size     200M;
        client_max_body_size        200M;
        proxy_pass              http://api;
        proxy_read_timeout      172800;
        proxy_connect_timeout   172800;
        proxy_send_timeout      172800;
        proxy_http_version      1.1;
        proxy_set_header Connection "";
        proxy_redirect          off;
        proxy_set_header        Host $host;
        proxy_set_header        X-Real-IP $remote_addr;
        proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Host $server_name;
    }
}

```

```sh
#!/bin/bash
set -e

timeout=180

echo "Waiting for Elasticsearch..."
elapsed=0
while ! curl -s "http://esearch:9200" >/dev/null 2>&1 && [ $elapsed -lt $timeout ]; do
  echo "Waiting for Elasticsearch... ($elapsed/$timeout)"
  sleep 2
  elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
  echo "Elasticsearch did not start within $timeout seconds."
  exit 1
fi
echo "Elasticsearch is ready!"
# echo "Running collectstatic..."
# python manage.py collectstatic --noinput

echo "Running migrations..."
#python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Creating Elasticsearch index..."
python manage.py create_index || echo "Index already exists. Skipping."

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 4 core.wsgi:application
```
# Search Service Deployment Guide

**Django + Elasticsearch + Docker + Nginx on AWS EC2**

------------------------------------------------------------------------

# 1. Overview

This document explains the architecture and deployment process of the
**Search Service** built using:

-   Django API
-   Elasticsearch
-   Docker & Docker Compose
-   Nginx Reverse Proxy
-   AWS EC2

The goal is to deploy a **secure, production-ready search API**
accessible through:

    https://search.medeasy.health

------------------------------------------------------------------------

# 2. System Architecture

## High Level Architecture

    User Browser
          │
          ▼
    DNS (search.medeasy.health)
          │
          ▼
    AWS EC2 Public IP
          │
          ▼
    Security Group (Allow 80 / 443)
          │
          ▼
    Docker Container: Nginx
          │
          ▼
    Docker Container: Django Search API
          │
          ▼
    Docker Container: Elasticsearch

Key security principle:

-   Only **Nginx** is exposed publicly
-   Django and Elasticsearch run inside **private Docker network**

------------------------------------------------------------------------

# 3. Docker Architecture

Docker Compose runs three services:

  Service          Purpose
  ---------------- ---------------------------------
  nginx            Reverse proxy + SSL termination
  search-service   Django search API
  esearch          Elasticsearch database

All containers communicate through:

    medeasy-network

Internal request flow:

    nginx → search-service → Elasticsearch

------------------------------------------------------------------------

# 4. docker-compose.yml Overview

Key components:

## Internal Docker Network

    networks:
      medeasy-network:
        external: true

Containers communicate via internal DNS.

Example:

    search-service → http://esearch:9200

Docker automatically resolves container names.

------------------------------------------------------------------------

## Public Ports

Only nginx exposes ports:

    ports:
      - "80:80"
      - "443:443"

External access:

    Internet → EC2 → Nginx

------------------------------------------------------------------------

# 5. AWS Infrastructure Setup

## Step 1 --- Launch EC2

Recommended configuration:

  Component       Value
  --------------- --------------
  AMI             Ubuntu 22.04
  Instance Type   t3.medium
  Storage         30--50 GB
  Key Pair        .pem file

------------------------------------------------------------------------

## Step 2 --- Configure Security Group

Allow inbound traffic:

  Type    Port
  ------- ------
  SSH     22
  HTTP    80
  HTTPS   443

Do NOT expose:

    9200 (Elasticsearch)
    8000 (Django)

------------------------------------------------------------------------

# 6. Install Docker on EC2

SSH into the server:

    ssh -i key.pem ubuntu@EC2_PUBLIC_IP

Install docker:

    sudo apt update
    sudo apt install docker.io docker-compose -y
    sudo systemctl enable docker
    sudo usermod -aG docker ubuntu

Re-login to apply permissions.

Verify installation:

    docker --version

------------------------------------------------------------------------

# 7. Create Docker Network

Because the compose file uses an external network:

    docker network create medeasy-network

------------------------------------------------------------------------

# 8. Deploy Application

Clone repository:

    git clone <repository-url>
    cd project

Run containers:

    docker-compose up -d --build

Verify:

    docker ps

Expected containers:

-   nginx
-   search-service
-   esearch

------------------------------------------------------------------------

# 9. Nginx Reverse Proxy Configuration

The nginx configuration performs four major tasks:

1.  Redirect HTTP → HTTPS
2.  Terminate SSL
3.  Route requests to Django
4.  Forward real client IP headers

------------------------------------------------------------------------

# 10. Upstream Configuration

    upstream api {
        server search-service:8000;
    }

Defines the backend service.

Inside Docker network:

    search-service:8000

Nginx forwards requests here.

------------------------------------------------------------------------

# 11. HTTP to HTTPS Redirect

    server {
        listen 80;
        server_name search.medeasy.health;
        return 301 https://$host$request_uri;
    }

Purpose:

Force secure HTTPS connections.

------------------------------------------------------------------------

# 12. HTTPS Server Configuration

    server {
        listen 443 ssl;
    }

Handles encrypted traffic using SSL certificates.

Certificates mounted via:

    volumes:
      - ./certificates:/etc/nginx/certificates

------------------------------------------------------------------------

# 13. SSL Configuration

    ssl_certificate /etc/nginx/certificates/fullchain.pem;
    ssl_certificate_key /etc/nginx/certificates/private.key;

These files are typically generated using:

    certbot

------------------------------------------------------------------------

# 14. Request Routing

    location / {
        try_files $uri $uri/ @python_django;
    }

Logic:

1.  Check if file exists
2.  If not → send to Django API

------------------------------------------------------------------------

# 15. Django Proxy Block

    location @python_django {
        proxy_pass http://api;
    }

This forwards request to:

    http://search-service:8000

------------------------------------------------------------------------

# 16. Proxy Headers

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

Purpose:

Allow Django to know:

-   Original client IP
-   Original host

Without this Django would only see Docker IP.

------------------------------------------------------------------------

# 17. Elasticsearch Connection

Inside Django container:

Environment variable:

    ELASTICSEARCH_HOST=http://esearch:9200

Because both containers share the same Docker network.

------------------------------------------------------------------------

# 18. Production Best Practices

### Elasticsearch Memory

Add:

    ES_JAVA_OPTS=-Xms1g -Xmx1g

Set system limit:

    sudo sysctl -w vm.max_map_count=262144

------------------------------------------------------------------------

### Use Gunicorn

Run Django with:

    gunicorn core.wsgi:application --bind 0.0.0.0:8000

Never use:

    runserver

in production.

------------------------------------------------------------------------

### Enable Gzip

In nginx:

    gzip on;
    gzip_types application/json;

Improves API response size.

------------------------------------------------------------------------

# 19. Final Request Flow

    User
     │
     ▼
    search.medeasy.health
     │
     ▼
    DNS → EC2
     │
     ▼
    Nginx (80/443)
     │
     ▼
    Django Search API
     │
     ▼
    Elasticsearch

------------------------------------------------------------------------

# 20. Deployment Checklist

Before production deployment verify:

-   EC2 security group configured
-   Docker installed
-   Docker network created
-   SSL certificates available
-   Containers running
-   Domain DNS pointing to EC2

------------------------------------------------------------------------

# 21. Useful Commands

View containers:

    docker ps

View logs:

    docker logs nginx
    docker logs search-service

Restart services:

    docker-compose restart

Stop containers:

    docker-compose down

------------------------------------------------------------------------

# 22. Future Improvements

For large scale systems consider:

-   AWS Load Balancer
-   Auto Scaling
-   Managed OpenSearch
-   CI/CD pipelines
-   Container orchestration (ECS / Kubernetes)

------------------------------------------------------------------------

# End of Documentation

