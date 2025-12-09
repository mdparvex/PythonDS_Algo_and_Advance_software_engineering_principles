# Deployment Without Exposing Container Ports

This document provides a clear and complete explanation of how to deploy an application in production **without exposing ports on Docker containers**, including:
- Why this approach is used
- How Docker networking works internally
- How to configure Docker and Docker Compose
- How to configure Nginx to reverse proxy to internal Docker services
- A complete deployable architecture example

---

## 1. What Does “Not Exposing Ports” Mean?
Normally, we run a Docker container and expose its internal port to the host:
```
docker run -p 8000:8000 myapp
```
This means:
- The service becomes **reachable from the host machine**
- If the server is public, the service becomes **directly reachable from the internet** unless blocked by firewall

**Not exposing ports** means:
- You do NOT publish any port to the host (no `-p`, no `expose` in production)
- The service is reachable **only inside the Docker network**
- Only Nginx (or another API gateway) can access it

This is more secure and cleaner for production deployment.

---

## 2. Why You Should Avoid Exposing Ports in Production
### ✅ **Security Benefits**
- Applications cannot be attacked directly from the internet
- Only Nginx is exposed, reducing attack surface
- Internal services (API, DB, workers) stay private

### ✅ **Cleaner Architecture**
- Only one public entry point (Nginx)
- Simple network routing
- All services communicate on Docker internal network

### ✅ **Better Scalability**
- Multiple backend containers without extra port mapping
- Load balancing possible inside Docker network

### Example of container reachable only internally
```
search-service → port 8000 (internal only)
nginx → port 80/443 (public)
```
Nginx forwards traffic to `search-service:8000` internally.

---

## 3. Docker Compose Setup (No Exposed Ports for App)
Here is a production-style `docker-compose.yml`:

```
version: "3.9"

services:
  search-service:
    build: ./search
    container_name: search-service
    environment:
      - ENV=production
    networks:
      - app-network
    # No port exposure here

  nginx:
    image: nginx:latest
    container_name: nginx
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./certificates:/etc/nginx/certificates
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - search-service
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### 🌐 Network Behavior
- `search-service` is accessible **only inside app-network**
- Nginx can reach it using: `http://search-service:8000`
- No external client can reach the service directly

---

## 4. Nginx Configuration for Reverse Proxy
Below is a clean, production-style Nginx config that forwards traffic to the internal service.

```
upstream api {
    server search-service:8000;  # Docker internal routing
}

server {
    listen 80;
    server_name search.example.com;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name search.example.com;

    ssl_certificate /etc/nginx/certificates/fullchain.pem;
    ssl_certificate_key /etc/nginx/certificates/private.key;

    location / {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### What Happens Internally?
1. Client hits `https://search.example.com`
2. Nginx receives the request
3. Nginx forwards to `http://search-service:8000`
4. Application responds internally
5. Nginx returns the response to the client

The application is never exposed to the outside world.

---

## 5. Docker Networking Explained
Docker creates a private network:
```
app-network (bridge)
```
All containers inside this network:
- Can communicate using container names
- Have private IPs (e.g., 172.18.0.4)
- Are isolated from outside world unless a port is published

This allows:
### Example
```
curl http://search-service:8000  # Works inside Docker network
curl http://localhost:8000       # Will NOT work because port is not exposed
```

---

## 6. Complete Architecture Overview
```
                    Internet
                        |
                   [ Nginx ]  ← Only exposed service (80/443)
                        |
        ————————— Docker Network —————————
        |                |                |
 [search-service]   [backend]       [database]
 (private:8000)     (private)       (private)
```

---

## 7. When You SHOULD Expose Ports
Expose ports only when:
- You need debugging locally
- You need direct access with Postman during development
- You run services outside Docker (local DB, etc.)

Never expose ports in:
- Production API services
- Databases (critical)
- Internal workers
- Message queues

---

## 8. Conclusion
Deploying without exposing ports is the **recommended production setup** for security, reliability, and clean architecture. You:
- Keep all services private and protected
- Use Nginx as the only public gateway
- Reduce attack surface significantly
- Maintain simple and scalable infrastructure

This is the correct and professional way to deploy Dockerized applications in production.

