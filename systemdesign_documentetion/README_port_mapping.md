**✅ Why does port change for every service?**

When you're running multiple Django services inside Docker containers, they all **listen to the same internal port (8000)**, but they need **different external ports** to avoid conflict.

**🔧 Example:**

```yaml

services:
    auth-service:
        ports:
            - "8001:8000" # external:internal
    book-service:
        ports:
            - "8002:8000"
    payment-service:
        ports:
            - "8003:8000"
```

- Each Django app **runs inside the container on port 8000**.
- You’re mapping that internal 8000 to a **different external port** on the host (EC2).
- This allows you to access each service separately from the EC2 machine:

| **Service** | **Internal Port** | **Host Port** | **Access URL** |
| --- | --- | --- | --- |
| auth-service | 8000 | 8001 | http://&lt;EC2-IP&gt;:8001 |
| book-service | 8000 | 8002 | http://&lt;EC2-IP&gt;:8002 |
| payment-service | 8000 | 8003 | http://&lt;EC2-IP&gt;:8003 |

**✅ What will happen on AWS EC2?**

When you deploy to **AWS EC2**:

1. **Your EC2 instance has one public IP** (e.g., 3.123.45.67).
2. All services **share that IP**, but they are accessible via **different ports**.
3. You can access each microservice by:
    - <http://3.123.45.67:8001> for auth
    - <http://3.123.45.67:8002> for books
    - etc.

💡 **No new IP is created per service.** They share the EC2's public IP.

**❓ Why do we use different ports?**

Because only **one process can bind to a specific port** on your EC2 host. Since all Django apps use port 8000 internally, you **must expose them on different external ports**.

**✅ Bonus: Use NGINX to combine all under one port (optional)**

If you don't want to use multiple ports like :8001, :8002, etc., you can set up **NGINX as a reverse proxy** on EC2:

```

server {

listen 80;

    location /auth/ {

        proxy_pass <http://auth-service:8000/>;

    }

    location /book/ {

        proxy_pass <http://book-service:8000/>;

    }

    location /payment/ {

        proxy_pass <http://payment-service:8000/>;

    }

    }
```
Then you can access:

- <http://3.123.45.67/auth/>
- <http://3.123.45.67/book/>
- <http://3.123.45.67/payment/>

**🧠 Summary:**

| **Question** | **Answer** |
| --- | --- |
| Why different external ports? | To avoid port conflicts on EC2 (only one process per port) |
| Does each service get its own IP? | ❌ No. All share the EC2's public IP |
| Can I access each app separately? | ✅ Yes, using mapped ports or NGINX reverse proxy |
| Can I make a shared domain like /auth? | ✅ Yes, use NGINX as API Gateway / reverse proxy |