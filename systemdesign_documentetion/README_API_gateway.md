
# 🧠 API Gateway: Overview and Example

An **API Gateway** is a **server that acts as a single entry point** into a system, routing requests from clients to various microservices. It handles **authentication, routing, rate limiting, logging, caching**, and more — simplifying client-side logic and centralizing cross-cutting concerns.

---

## 🧩 Why Use an API Gateway?

When using **microservices**, each service typically has its own endpoint. Without a gateway, the client would have to:

- Know the address of each service
- Manage communication with each service individually
- Handle load balancing, security, retries, etc.

An API Gateway **hides this complexity** by exposing a **unified API** to clients.

---

## 🔧 How It Works (Flow Diagram):

```scss
Client
   |
   v
[API Gateway]
   |     |     |
   v     v     v
Service A  Service B  Service C
```

---

## 🔍 Responsibilities of API Gateway

| Responsibility          | Description |
|-------------------------|-------------|
| **Request Routing**      | Forwards incoming requests to the correct service |
| **Authentication/Authorization** | Validates user credentials (e.g., JWT token) |
| **Rate Limiting**        | Prevents abuse by throttling requests |
| **Response Aggregation** | Combines results from multiple services into one response |
| **Caching**              | Speeds up frequent requests |
| **Logging & Monitoring** | Tracks request and response activity |

---

## 📦 Real-world Technologies for API Gateways

| Tool           | Description |
|----------------|-------------|
| **Amazon API Gateway** | Managed service on AWS |
| **Kong**        | Open-source & enterprise-grade |
| **NGINX**       | Reverse proxy often used as lightweight gateway |
| **Traefik**     | Modern cloud-native gateway |
| **Apigee**      | Google Cloud’s enterprise API gateway |
| **Express Gateway** | API gateway built on Node.js |

---

## ✅ Example in Django Microservices Scenario

Let’s say you have these Django microservices:

- **Auth Service** (e.g., `/login`, `/register`)
- **User Service** (e.g., `/profile`)
- **Book Service** (e.g., `/books`)

### Without API Gateway:

- Frontend must send requests to:
  - `auth.myapp.com`
  - `users.myapp.com`
  - `books.myapp.com`

### With API Gateway (e.g., NGINX):

- Frontend only talks to:  
  `api.myapp.com`

### 🔧 NGINX Config for API Gateway:

```nginx
server {
    listen 80;
    server_name api.myapp.com;

    location /auth/ {
        proxy_pass http://auth-service/;
    }

    location /users/ {
        proxy_pass http://user-service/;
    }

    location /books/ {
        proxy_pass http://book-service/;
    }
}
```

So:
- `GET api.myapp.com/auth/login/` → routed to `auth-service`
- `GET api.myapp.com/books/1/` → routed to `book-service`

---

## 🧠 Advantages

- **Centralized access control and monitoring**
- **Simplified client logic**
- **Easier service updates and scaling**

---

## 🚨 Caution / Challenges

- Becomes a **single point of failure** (should be highly available)
- Adds **latency** if not optimized
- Needs careful handling of **authentication and security**

---

## ✅ Summary

| Feature                 | Benefit                         |
|-------------------------|----------------------------------|
| Unified access point     | Simplifies client communication |
| Centralized auth/logging| Security and observability      |
| Protocol translation     | REST to gRPC, etc.              |
| Backend abstraction      | Decouples frontend/backend      |


# ✅ Real example
Great! You're now diving into **real-world API Gateway architecture**, where services run across **mixed environments** (Kubernetes & EC2). Let me walk you through a **clear, step-by-step breakdown** on how to design an **API Gateway** for your setup.

**🧭 Your Current Setup**

| **Service** | **Platform** | **Type** |
| --- | --- | --- |
| live_reading | Kubernetes | Django API |
| student_api | Kubernetes | Django API |
| payment | EC2 | Django API |

Your goal is to build an **API Gateway** that:

- Routes external traffic to the correct service.
- Hides internal service structure from clients.
- Can be extended for **rate limiting, logging, auth, etc.**

**🔧 Option 1: Use NGINX as an API Gateway**

You can use **NGINX** as a reverse proxy to route requests based on URL path.

**🧱 Architecture**

```scss
Client (Frontend / Mobile)
    |
    v
[API Gateway- NGINX]
    |
    +--> /live-reading/ --> Service on Kubernetes
    +--> /student-api/ --> Service on Kubernetes
    +--> /payment/ --> Service on EC2
```

**🔄 Step-by-Step Implementation**

**✅ Step 1: Expose All Services Internally**

| **Service** | **How to Access** |
| --- | --- |
| live_reading | Kubernetes Service DNS (e.g. live-reading.default.svc.cluster.local) or LoadBalancer IP |
| student_api | Kubernetes Service DNS or LoadBalancer IP |
| payment | Public IP or domain of your EC2 machine |

If you’re using **LoadBalancer** or **Ingress**, your Kubernetes apps should be accessible via:

- <http://live-reading.domain.com>
- <http://student-api.domain.com>

Your EC2-hosted payment service could be:

- <http://ec2-3-91-1-123.compute.amazonaws.com> or
- Behind a custom domain (recommended): <http://payment.domain.com>

**✅ Step 2: Set up NGINX as the API Gateway**

You can run NGINX on a separate server, inside Kubernetes as a pod, or even on EC2.

Here’s a sample NGINX config:

```nginx
server {

listen 80;

server_name api.yourdomain.com;

\# Route to live_reading (Kubernetes)

location /live-reading/ {

  proxy_pass <http://live-reading.domain.com/>;

  proxy_set_header Host $host;

  proxy_set_header X-Real-IP $remote_addr;

}

\# Route to student_api (Kubernetes)

location /student-api/ {

  proxy_pass <http://student-api.domain.com/>;

  proxy_set_header Host $host;

  proxy_set_header X-Real-IP $remote_addr;

}

\# Route to payment (EC2)

location /payment/ {

  proxy_pass <http://ec2-3-91-1-123.compute.amazonaws.com/>;

  proxy_set_header Host $host;

  proxy_set_header X-Real-IP $remote_addr;

}

}
```

**✅ Step 3: Access All APIs via One Domain**

- GET <http://api.yourdomain.com/live-reading/lesson/1>
- POST <http://api.yourdomain.com/student-api/register/>
- POST <http://api.yourdomain.com/payment/checkout/>

Your frontend (or mobile app) only talks to one domain: api.yourdomain.com.

**🎁 BONUS Features You Can Add Later**

| **Feature** | **Tool (NGINX or Alternatives)** |
| --- | --- |
| Rate limiting | NGINX limit_req, Kong, or Envoy |
| Auth middleware | NGINX + Lua or API Gateway service |
| Load balancing | NGINX upstreams |
| Logging + monitoring | NGINX logs + Promtail + Grafana stack |
| HTTPS support | Use Let’s Encrypt (via Certbot) |

**📌 Recap**

| **Task** | **Done?** | **Notes** |
| --- | --- | --- |
| Expose all services | ✅   | Use DNS, Ingress, or EC2 IPs |
| Configure NGINX for routing | ✅   | Map paths to services |
| Use single domain | ✅   | api.yourdomain.com |
| Secure with HTTPS | 🔜  | Use Certbot + NGINX |
| Add auth/logging/rate-limit | 🔜  | Optional advanced setup |

# 🧠 API Gateway: rate limiting, auth middleware, load balancing, logging, and HTTPS support.
Absolutely! Here's an **enhanced NGINX-based API Gateway configuration** example that demonstrates how to integrate the **bonus features** you mentioned: rate limiting, auth middleware, load balancing, logging, and HTTPS support.

**✅ Full NGINX API Gateway Example with Bonus Features**

**🔧 Scenario Recap**

- /live-reading/ and /student-api/ route to services in Kubernetes via Ingress or LoadBalancer.
- /payment/ routes to a Django service running on EC2.
- Bonus features like **rate limiting**, **authentication**, **HTTPS**, **logging**, and **load balancing** are integrated.

**🧾 nginx.conf (Full API Gateway Config)**

```nginx
worker_processes auto;

events {

worker_connections 1024;

}

http {

  include mime.types;

  default_type application/octet-stream;

  access_log /var/log/nginx/access.log;

  error_log /var/log/nginx/error.log;

  \# Enable rate limiting

  limit_req_zone $binary_remote_addr zone=api_limit:10m rate=5r/s;

  server {

    listen 80;

    server_name api.yourdomain.com;

    \# Redirect HTTP to HTTPS

    return 301 https://$host$request_uri;

  }

  server {

    listen 443 ssl;

    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    \# Rate limiting

    limit_req zone=api_limit burst=10 nodelay;

    \# Auth middleware (simple header check; you could also use Lua or JWT)

    if ($http_x_api_key != "your-secure-token") {

    return 403;

  }

  \# Load balancing for student-api (K8s has multiple replicas)

  upstream student_backend {

    server student-api-1.internal:8000;

    server student-api-2.internal:8000;

  }

  location /student-api/ {

    proxy_pass http://student_backend/;

    proxy_set_header Host $host;

    proxy_set_header X-Real-IP $remote_addr;

  }

  location /live-reading/ {

    proxy_pass <http://live-reading-service/>;

    proxy_set_header Host $host;

    proxy_set_header X-Real-IP $remote_addr;

  }

  location /payment/ {

    proxy_pass <http://ec2-3-91-1-123.compute.amazonaws.com/>;

    proxy_set_header Host $host;

    proxy_set_header X-Real-IP $remote_addr;

  }

}

}
```

**🛠️ Breakdown of Bonus Features**

| **Feature** | **Configuration** |
| --- | --- |
| ✅ Rate Limiting | limit_req_zone, limit_req – limits to 5 requests/sec |
| ✅ Auth Middleware | Simple API key via header (X-API-KEY), can extend with JWT |
| ✅ Load Balancing | upstream student_backend with two backend servers |
| ✅ HTTPS Support | listen 443 ssl with Let's Encrypt certs |
| ✅ Logging | access_log and error_log defined |

**🧪 Test With curl**

```bash

curl -H "X-API-KEY: your-secure-token" <https://api.yourdomain.com/student-api/users/>
```

**🛡 Advanced Enhancements**

| **Feature** | **Tool/Extension** |
| --- | --- |
| JWT authentication | OpenResty or Lua module |
| Dashboard monitoring | Promtail + Loki + Grafana stack |
| Kubernetes native gateway | Kong, Traefik, or Istio |

**📦 Deployment Tips**

- Run NGINX in **Docker** or install directly on EC2.
- Use **Certbot** for automatic HTTPS:

```bash

sudo certbot --nginx -d api.yourdomain.com
```

- Place .env variables securely if needed, and restrict headers in production.

# Details about Nginx as reverse proxy and Gateway. When it is real gateway, We must use cloud level gateway system. Everything explained bellow

Got it ✅ — I’ll prepare a **single production-style documentation** that brings together all the discussions we had:

- What is happening (concept)
- Step-by-step flow
- Dockerized deployment (Django + Gunicorn + Nginx)
- API Gateway features (rate limiting, auth, HTTPS, logging, load balancing)
- Full example configs (docker-compose.yml + nginx.conf)
- Testing checklist

Here’s your **one-stop reference**:

# 📘 Production API Gateway with Django, Docker, and Nginx

This document explains how to set up a **production-level API Gateway** in front of a Django application deployed with Docker. The API Gateway will handle **rate limiting, authentication, load balancing, logging, and HTTPS support**.

## 1\. 🏗️ Architecture Overview

```pgsql
   Client (Browser/Mobile)
           │
           ▼
      [EC2 Public IP / Domain]
           │
     ┌───────────────┐
     │   Nginx       │  ← API Gateway
     │ - SSL/HTTPS   │
     │ - Rate Limit  │
     │ - Logging     │
     │ - Load Balance│
     └───────┬───────┘
             │
   ┌───────────────────┐
   │ Gunicorn + Django │  ← App container
   └───────────────────┘
             │
        PostgreSQL / Redis (optional)
```

## 2\. ⚙️ Step-by-Step Flow

1. **Launch EC2 instance** (Ubuntu 22.04 recommended).
2. **Install Docker + Docker Compose**.
3. **Prepare Django App** with Dockerfile (using Gunicorn).
4. **Configure Nginx as Gateway** (inside its own container).
    - Acts as reverse proxy → forwards requests to Django
    - Adds rate limiting, auth, HTTPS, and logs
5. **Run everything with docker-compose up -d**.
6. **Access your API** via EC2 Public IP or Domain.

## 3\. 📦 Example docker-compose.yml

```yaml
version: "3.9"

services:
  web:
    build: ./app
    container_name: django_app
    command: gunicorn myproject.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - ./app:/app
    expose:
      - "8000"
    env_file:
      - .env

  nginx:
    image: nginx:latest
    container_name: nginx_gateway
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/ssl/certs
      - ./logs:/var/log/nginx
    depends_on:
      - web
```

## 4\. 📝 Example nginx.conf

```nginx
worker_processes auto;
events {
    worker_connections 1024;
}

http {
    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    upstream django_upstream {
        server web:8000;  # Django container
    }

    server {
        listen 80;
        server_name _;

        # Redirect all HTTP to HTTPS
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name _;

        # SSL Certificates
        ssl_certificate     /etc/ssl/certs/fullchain.pem;
        ssl_certificate_key /etc/ssl/certs/privkey.pem;

        location / {
            proxy_pass http://django_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            # Apply rate limiting
            limit_req zone=api_limit burst=20 nodelay;
        }

        # Example: Simple Auth Middleware
        location /secure/ {
            auth_basic "Restricted API";
            auth_basic_user_file /etc/nginx/.htpasswd;
            proxy_pass http://django_upstream;
        }
    }
}
```

## 5\. 🔐 Security & Authentication

- **Basic Auth**: .htpasswd file stored in nginx container.
- **JWT/OAuth**: Implemented at Django level.
- **HTTPS**: Use Let’s Encrypt or manually copy certificates into ./certs.

## 6\. 📊 Logging & Monitoring

- Logs are mounted at ./logs/.
- Use docker logs nginx_gateway to view runtime logs.
- Optionally ship logs to **CloudWatch / ELK Stack**.

## 7\. 🛠️ Testing Checklist

✅ Build & run:
```bash
docker-compose up -d --build
```
✅ Verify containers:
```bash
docker ps
```
✅ Check Nginx:
```bash
docker exec -it nginx_gateway nginx -t
```
✅ Access API:

```bash
http://<EC2-PUBLIC-IP>/
https://<EC2-PUBLIC-IP>/
```

✅ Test Rate Limiting:

```bash
ab -n 100 -c 20 https://<EC2-IP>/api/
# Should return "503 Service Temporarily Unavailable" for excess requests
```

\# Should return "503 Service Temporarily Unavailable" for excess requests

✅ Check Logs:

```bash
tail -f logs/access.log
tail -f logs/error.log
```

## 8\. 🌍 Scaling with Load Balancing

To scale Django containers:
```bash
docker-compose up --scale web=3 -d
```
Update nginx.conf:

```nginx
upstream django_upstream {
    server web:8000;
    server web_1:8000;
    server web_2:8000;
}
```

Nginx will **round-robin requests** across Django containers.

## ✅ Final Notes

- Use **Option 2 (Dockerized Nginx)** for cleaner production deployment.
- Map your **domain name** to EC2 Public IP for real API access.
- Always run **nginx -t** after config changes.
- For **HTTPS in production**, integrate **Certbot + Let’s Encrypt** automation.

👉 This is your **production-ready API Gateway reference**. You can literally docker-compose up -d, hit your EC2 IP, and test all features (rate limiting, HTTPS, logging, auth).

Would you like me to also include a **Certbot automation (for Let’s Encrypt SSL)** so that you don’t need to manually add certs in ./certs?

Great question 👍 — you’ve realized an important distinction:

👉 Running **Nginx inside Docker** (or on EC2 directly) is a **reverse proxy setup** — useful when you have **a single Django application** and you want HTTPS, logging, rate-limiting, or caching.

👉 But when you talk about an **API Gateway** and **Load Balancer**, you’re stepping into **cloud-native production architecture** on AWS. In that world, Nginx often becomes unnecessary because AWS already provides those functionalities in **managed services**.

Let’s break this into two **real-world deployment options** so you can choose what’s best for your project.

## 🚀 Option 1 — Single Application with Nginx (Simple)

- You dockerize Django, run it on EC2 (with Gunicorn/Uvicorn), and put Nginx in front of it.
- Nginx handles:
  - HTTPS termination (via Let’s Encrypt or custom certs)
  - Reverse proxy (forwarding traffic to your Django container)
  - Rate limiting (basic limit_req config)
  - Logging

✅ Good for small projects / MVPs  
❌ Not horizontally scalable (one EC2 only)

## 🚀 Option 2 — Production-Ready AWS API Gateway + Load Balancer (Recommended)

Here’s the flow for **scalable production**:

### 1\. ****Django in Docker****

- Package your Django app in Docker (docker build -t my-django-app .).
- Push the image to **Amazon ECR** (Elastic Container Registry).

### 2\. ****Run on ECS (Elastic Container Service) or EKS****

- Use **ECS Fargate** (serverless containers) or **EKS (Kubernetes)**.
- Define a task definition for your Django container.

### 3\. ****Attach Application Load Balancer (ALB)****

- Create an **ALB** in AWS:
  - ALB listens on **80/443**.
  - Target group points to your Django containers (ECS/EKS tasks).
  - ALB does **load balancing across multiple container instances**.

### 4\. ****Add AWS API Gateway (Optional but Powerful)****

- Put **API Gateway** in front of ALB when you want:
  - Advanced **rate limiting & throttling** (requests per second, burst limits).
  - **Authentication** (Cognito, JWT, custom Lambda authorizers).
  - **Usage plans** (per-user API quotas).
  - **Custom domain + HTTPS** automatically.

Flow becomes:

```arduino
Client → API Gateway → ALB → Django Containers
```

### 5\. ****Logging & Monitoring****

- API Gateway + ALB logs → **CloudWatch**.
- Metrics: request count, latency, 4xx/5xx errors.
- You can set alarms with **CloudWatch + SNS**.

## 🔑 Why API Gateway + ALB > Nginx for Production?

- Nginx is self-managed — you configure & maintain.
- API Gateway + ALB are **fully managed** by AWS.
- You get:
  - **Scalability** (auto-scaling containers behind ALB).
  - **Security** (WAF, rate limiting).
  - **Easy HTTPS** (no need for certbot).
  - **Global availability** with CloudFront.

## 📘 Example: Deployment Flow

1. **Build & Push Image**

```bash
docker build -t my-django-app .
aws ecr create-repository --repository-name my-django-app
docker tag my-django-app:latest <account_id>.dkr.ecr.<region>.amazonaws.com/my-django-app:latest
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/my-django-app:latest
```

1. **Deploy on ECS** (with Fargate):
    - Create **Task Definition** → add Django container.
    - Create **Service** → link with **Target Group + ALB**.
2. **API Gateway Setup**:
    - Create a new **HTTP API**.
    - Set integration = **ALB endpoint**.
    - Add **rate limiting** under Usage Plan.
    - Add **JWT auth** if needed.
    - Deploy API with a custom domain.
3. **Testing**:
    - Call your API Gateway URL:
    ```bash
    curl -i https://<api_id>.execute-api.<region>.amazonaws.com/prod/books/
    ```
    - Check CloudWatch for logs.

✅ **Summary:**

- For **a single EC2 + Docker** → Nginx is fine.
- For **real production (scalable, secure, AWS-native)** → Use **API Gateway + ALB + ECS/EKS**.


You’re getting into the **difference between using Nginx as a reverse proxy for a single app vs. having a real API Gateway setup.** Let me break this down clearly:

## 🔹 1. Nginx as Reverse Proxy (Option 2 you tried)

When you put Nginx in front of your Django container via docker-compose, you’re essentially doing:

- Reverse proxy (route requests from port 80/443 to Django)
- SSL termination (HTTPS)
- Basic logging
- Some middleware-like features (rate limiting, caching)

👉 You **can** add:

- **Rate limiting** → using limit_req_zone and limit_req
- **Basic authentication / JWT verification** → possible with Lua (OpenResty) or external modules
- **Caching** → via proxy_cache
- **Circuit breaking / retries** → via proxy_next_upstream, but very limited

⚠️ However, **Nginx is not a full API Gateway**. It doesn’t provide advanced service discovery, per-API policies, centralized auth, observability, etc.

So yes, you can manage them inside Nginx, but it quickly becomes messy and limited for production-scale systems.

## 🔹 2. Better Option → Use a Real API Gateway

If you want **enterprise-level gateway features**, AWS and cloud-native options are much better:

### 🏗️ Two Common Choices

1. **AWS API Gateway + Lambda (or ECS/Fargate/EKS)**
    - Built-in **rate limiting, throttling, auth (JWT, Cognito, IAM)**, caching, logging (CloudWatch).
    - Serverless-friendly.
    - Expensive at scale but very powerful.
2. **AWS ALB (Application Load Balancer) + Django containers**
    - Use **ALB** in front of ECS/EKS/EC2.
    - Handles load balancing, HTTPS termination, health checks.
    - For API Gateway–like features → integrate **AWS WAF (Web Application Firewall)**:
        - Rate limiting
        - IP blocking
        - Security filtering
    - Use **Cognito or custom auth** for authentication.
    - Use **CloudFront** in front if you need caching/CDN.

## 🔹 3. When to Stick with Nginx (Option 2)

- **Single service / small project**
- Low traffic (< few 1000 requests/sec)
- You want a lightweight reverse proxy + SSL + logs
- Don’t need complex per-API policies

Example:

```nginx
http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name myapi.com;

        location / {
            proxy_pass http://django:8000;
            limit_req zone=api_limit burst=20 nodelay;
        }
    }
}
```

## 🔹 4. When to Use API Gateway / ALB

- **Multiple microservices**
- Need per-service auth, rate limiting, caching policies
- Want observability (metrics, tracing, logs per API)
- Scaling with AWS infra
- Multi-region or high-availability setup

Example Flow (AWS Production-ready):

```rust
Client -> CloudFront (caching/CDN + HTTPS)
       -> API Gateway (auth, throttling, request validation)
       -> ALB (load balancing to ECS/EKS containers)
       -> Django App
```

✅ **In summary:**

- If you’re only running **one Django app** → Nginx (Option 2) is enough. Add rate limiting/caching in Nginx config.
- If you want **gateway-level features at scale** → better to use **AWS API Gateway + ALB + WAF**.
- **Don’t over-engineer**: Use Nginx for small/medium projects; move to API Gateway + ALB when scaling/multiple services.

👉 Do you want me to prepare **two side-by-side configuration examples**:

- (A) Nginx-based API gateway with rate limiting + caching
- (B) AWS-native API Gateway + ALB setup (diagram + config steps)?

That way, you’ll have a **clear comparison and deployment guide** for both paths.



Let’s carefully break this down because **“load balancing” can live at multiple layers**:

## 🔹 Option 1: ****Cloud-Level Load Balancer (Recommended for Production)****

If you’re running a **production Django API in AWS**, the best option is to use a **managed load balancer (AWS ALB or NLB)**.

### Why?

- **Scalability**: Can distribute traffic across multiple EC2 instances (not just containers on one instance).
- **High Availability**: Works across multiple availability zones (AZs).
- **TLS Termination**: Can handle HTTPS certificates for you.
- **Health Checks**: Automatically removes unhealthy instances from rotation.
- **Integration**: Works seamlessly with **Auto Scaling Groups** (EC2 can scale up/down automatically).

### Example Flow

```lua
User → AWS ALB → EC2 instances (running Docker + Nginx reverse proxy → Django app)
```

## 🔹 Option 2: ****Nginx Load Balancer (Good for Small Scale / Single Instance)****

If you have **one EC2 instance only**, you can still load balance at the **container level** using Nginx.

- Run **multiple Django containers** on the same EC2 instance.
- Nginx acts as a **reverse proxy + load balancer**.
- If one Django container crashes, Docker can restart it.

### Example Nginx Upstream Config

```nginx
http {
    upstream django_backend {
        server web1:8000;
        server web2:8000;
        server web3:8000;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://django_backend;
        }
    }
}
```

Here:

- web1, web2, web3 are Django containers (defined in docker-compose).
- Nginx distributes requests between them (round robin by default).

## 🔹 Which Should You Choose?

- **For a single EC2 & simple setup (testing, MVP, or internal tool)** → Nginx load balancing is enough.
- **For production with expected traffic growth, multiple EC2s, and HA** → **Use AWS ALB (Application Load Balancer)**.

👉 You can **combine both**:

- **AWS ALB** (global scale + TLS termination + failover between EC2s)
- Inside each EC2, **Nginx** load balances across multiple Django containers

## 🔹 Gateway-Level Features (Where to Put Them?)

- **Rate Limiting / Caching / Auth / Circuit Breaking** → Better at **gateway level**.
  - If you want full control in Dockerized setup → add to Nginx (or Kong / Traefik).
  - If you want **managed solution** → AWS API Gateway (or ALB with WAF).

✅ **Summary**

- For **serious production**, use **AWS ALB (or API Gateway + Lambda/ECS)**.
- For **one EC2 server**, Nginx is enough, but not scalable.
- Best hybrid → **AWS ALB → Nginx → Django containers**.