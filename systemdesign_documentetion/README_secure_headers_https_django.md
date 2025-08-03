# Secure Headers and HTTPS in Django

This documentation provides a complete guide on implementing Secure Headers and HTTPS in a Django project to enhance security and protect against common vulnerabilities.

---

## ✅ 1. What Are Secure Headers?

Secure headers are HTTP response headers that enhance the **security of your web application** by controlling browser behavior to prevent attacks like:

- Cross-Site Scripting (XSS)
- Clickjacking
- MIME type sniffing
- Downgrade attacks

---

## ✅ 2. What Is HTTPS?

**HTTPS** (Hypertext Transfer Protocol Secure) is the **secure version of HTTP**, using **TLS (Transport Layer Security)** to:

- Encrypt data in transit
- Authenticate the server
- Ensure data integrity

---

## ✅ 3. Why Are These Important?

| Attack Vector     | Prevented By                     |
| ----------------- | -------------------------------- |
| Man-in-the-middle | HTTPS                            |
| XSS               | Content-Security-Policy          |
| Clickjacking      | X-Frame-Options                  |
| MIME sniffing     | X-Content-Type-Options           |
| Downgrade attacks | Strict-Transport-Security (HSTS) |

---

## 🔐 4. Important Secure Headers Explained

| Header                            | Purpose                                               |
| --------------------------------- | ----------------------------------------------------- |
| **Strict-Transport-Security**     | Enforces HTTPS                                        |
| **X-Content-Type-Options**        | Prevents MIME type sniffing                           |
| **X-Frame-Options**               | Prevents clickjacking                                 |
| **Referrer-Policy**               | Controls how much referrer data is sent               |
| **Content-Security-Policy (CSP)** | Restricts what content can be loaded                  |
| **Permissions-Policy**            | Restricts browser features (like camera, geolocation) |

---

## ⚙️ 5. Enabling HTTPS and Secure Headers in Django

### 🔹 Step 1: Use HTTPS in Production

#### a. Enable HTTPS using a Reverse Proxy (e.g., Nginx):

Use Let's Encrypt for a free SSL certificate:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx
```

#### b. Configure Django to Use HTTPS:

In `settings.py`:

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

> ⚠️ Only enable `SECURE_SSL_REDIRECT` in production.

---

### 🔹 Step 2: Add Secure Headers in Django Middleware

#### Option 1: Use `django-secure` (Deprecated)

Better use custom middleware or packages like `django-csp`, `secure`, or `djangosecureheaders`.

#### Option 2: Write Your Own Middleware

Create a file `middleware/security_headers.py`:

```python
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Secure headers
        response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=()"
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
        )

        return response
```

Add it in your `settings.py`:

```python
MIDDLEWARE = [
    ...
    'django.middleware.security.SecurityMiddleware',
    'yourapp.middleware.security_headers.SecurityHeadersMiddleware',
]
```

---

### 🔹 Step 3: Force HTTPS Redirects

Django does not serve HTTPS by itself — you must use a **web server like Nginx**.

#### Example Nginx Config:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
        proxy_redirect off;
    }
}
```

---

### 🔹 Step 4: Set `ALLOWED_HOSTS` and Secure Cookies

```python
ALLOWED_HOSTS = ['yourdomain.com']

# Optional for extra protection
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
```

---

## 🔪 6. Testing Secure Headers and HTTPS

You can test your deployed site using:

- 🔍 [https://securityheaders.com](https://securityheaders.com/)
- 💪 [https://www.ssllabs.com/ssltest/](https://www.ssllabs.com/ssltest/)

---

## ✅ Example Response Headers After Setup

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=()
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```

---

## 🛡️ 7. Best Practices

| Best Practice                     | Reason                                   |
| --------------------------------- | ---------------------------------------- |
| Always use HTTPS                  | Encrypts and authenticates communication |
| Set `Secure` and `HttpOnly` flags | Prevent cookie theft via JS or MITM      |
| Use strong CSP                    | Mitigate XSS and injection attacks       |
| Keep SSL certificates updated     | Avoid trust issues                       |
| Disable browser sniffing          | Use `X-Content-Type-Options: nosniff`    |
| Use HSTS                          | Enforce secure connections               |

---

## 📦 8. Optional Packages

| Package         | Use Case                                                   |
| --------------- | ---------------------------------------------------------- |
| `django-csp`    | CSP header management                                      |
| `django-secure` | (Legacy) multiple secure headers                           |
| `secure`        | Lightweight secure headers                                 |
| `whitenoise`    | Serve static files with secure headers (great with Heroku) |

---

## ✅ Summary

| Feature                 | Use in Django Settings or Middleware          |
| ----------------------- | --------------------------------------------- |
| HTTPS only              | Nginx + `SECURE_SSL_REDIRECT`                 |
| Secure cookies          | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| Secure headers          | Custom middleware or package                  |
| Content security        | `Content-Security-Policy`                     |
| Strong referrer control | `Referrer-Policy` header                      |

---

## ❓ Need Help?

Let me know if you want:

- A Docker + Nginx production-ready setup
- SSL with Let’s Encrypt automation
- Middleware template for any specific header
- A complete working example in GitHub repo format

