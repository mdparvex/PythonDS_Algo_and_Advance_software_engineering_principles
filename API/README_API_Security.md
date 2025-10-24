# API Security - Complete, pragmatic guide (with Django examples)

Clear, focused, and practical - this guide explains **why** each control exists, **when** to use it, and **how** to implement it in Django / Django REST Framework (DRF). Copy-pasteable code snippets are included to help you get started.

# 1 - Security principles (short)

- **Least privilege:** give each client/user only the rights they need.
- **Defense in depth:** multiple, overlapping protections (TLS + auth + rate limits + validation).
- **Fail safe / fail closed:** deny by default.
- **Log & monitor:** capture auth events, errors, suspicious traffic.
- **Rotate secrets & keys** regularly and revoke access when needed.

# 2 - Transport security (TLS / HTTPS)

**Why:** Prevent eavesdropping (MITM), credential theft, header tampering.  
**When:** Always for public-facing APIs and internal APIs that travel public networks.

**How:** Terminate TLS at load balancer / reverse proxy (Nginx, AWS ALB). Configure HSTS. Use strong cipher suites.

**Notes:** Django settings: SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_HSTS_SECONDS.

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

# 3 - Authentication methods

### 3.1 Session authentication (Django built-in)

**When:** Traditional web apps where browser session cookies are used.  
**How it helps:** Uses server-validated session cookies; CSRF protection prevents cross-site attacks.

Django default - nothing special to enable beyond django.contrib.auth and middleware.

### 3.2 Token authentication (DRF TokenAuthentication)

**When:** Simple API clients (mobile apps, scripts) without OAuth complexity.  
**How it helps:** Tokens replace username/password on each request; server can revoke tokens.

Install DRF and configure:

```python
# settings.py
INSTALLED_APPS += ["rest_framework", "rest_framework.authtoken"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
}
```

Create tokens and a login endpoint:

```python
# urls.py
from rest_framework.authtoken.views import obtain_auth_token
urlpatterns = [path("api/token-auth/", obtain_auth_token)]
```

Server returns token; client sends header `Authorization: Token <token>`.

### 3.3 JWT (stateless) - djangorestframework-simplejwt

**When:** Scalable stateless APIs, microservices, single-sign-on-ish flows.  
**How it helps:** Short-lived access tokens + refresh tokens; easy to validate without DB (if you choose).

```python
# settings.py
INSTALLED_APPS += ["rest_framework"]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
```

```python
# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns += [
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

Client sends: `Authorization: Bearer <access_token>`;. Use short access TTL and rotate refresh tokens.

**Caveat:** JWT revocation requires extra work (blacklist or versioned tokens).

### 3.4 OAuth2 (Authorization Code, client credentials) - django-oauth-toolkit

**When:** Third-party delegated access, multi-service SSO, enterprise integrations.  
**How it helps:** Standardized flows, scopes, refresh tokens, consent screens.

Basic idea (install django-oauth-toolkit), then configure:

```python
# settings.py
INSTALLED_APPS += ["oauth2_provider"]
OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "SCOPES": {"read": "Read scope", "write": "Write scope"},
}
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
]
```

OAuth2 is large; prefer it when you need delegated access and standardized flows.

### 3.5 API keys (simple)

**When:** Machine-to-machine integrations where OAuth is overkill.  
**How it helps:** Simple identification of calling clients; rotate/revoke keys.

Minimal example: store keys and check header.

```python
# models.py
import secrets
from django.db import models
class ApiKey(models.Model):
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True, default=lambda: secrets.token_hex(32))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# middleware.py (or DRF auth class)
from django.http import JsonResponse
from .models import ApiKey
class ApiKeyMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        key = request.headers.get("X-API-KEY")
        if not key:
            return JsonResponse({"detail": "API key required"}, status=401)
        try:
            api = ApiKey.objects.get(key=key, is_active=True)
        except ApiKey.DoesNotExist:
            return JsonResponse({"detail": "Invalid API key"}, status=403)
        request.api_key = api
        return self.get_response(request)
```

**Security:** Store keys hashed (e.g., HMAC) if you need one-way storage.

### 3.6 Mutual TLS (mTLS)

**When:** High-security server-to-server communications (banking, internal APIs).  
**How it helps:** Both client and server present certificates - very strong authentication.

**How to implement:** Configure reverse proxy (Nginx) to request client certs; pass verified identity to Django via header or environment variable. Example Nginx:

```nginx
ssl_verify_client on;
ssl_client_certificate /etc/ssl/ca.crt;
proxy_set_header X-Client-CN $ssl_client_s_dn;
```

In Django `read request.META['HTTP_X_CLIENT_CN']` and map to a client record.

# 4 - Authorization (permissions)

### Role-Based Access Control (RBAC)

**When:** Most apps - roles like admin, editor, viewer.  
**How:** Map users to roles, check role permissions in views.

DRF example - custom permission:

```python
# permissions.py
from rest_framework.permissions import BasePermission
class IsEditor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name="Editors").exists()
```

Use in view:

```python
from rest_framework.views import APIView
from .permissions import IsEditor

class EditArticle(APIView):
    permission_classes = [IsEditor]
    def post(self, request): ...
```

### Object-level permissions

**When:** Per-object restrictions (only owner can edit).  
**How:** Use DRF has_object_permission or libraries like django-guardian.

```python
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

# 5 - Input validation & output encoding

**Why:** Protect against injection (SQL, NoSQL, template injection), XSS.  
**How:** Use serializers (DRF) for strict types; avoid raw SQL; escape output.

```python
# serializers.py
from rest_framework import serializers
class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
```

Always validate on server side - never trust clients.

# 6 - CSRF & CORS

### CSRF

- For APIs using cookie/session auth, keep CSRF protection enabled (Django has it on by default).
- For token/JWT auth, typically @csrf_exempt or CsrfViewMiddleware bypass is used - but ensure tokens are sent in headers (Authorization) not in cookies.

```python
# views.py (token-based)
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def my_token_view(request): ...
```

Better: use DRF which handles this through authentication classes.

### CORS

**Why:** Control which origins can call your API from browsers.

Use `django-cors-headers`:

```python
# settings.py
INSTALLED_APPS += ["corsheaders"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE
CORS_ALLOWED_ORIGINS = ["https://example.com"]
```

For APIs used by many domains, set CORS carefully; avoid `CORS_ALLOW_ALL_ORIGINS = True` in production.

# 7 - Rate limiting / throttling

**Why:** Stop brute-force, abuse, and DoS.  
**How:** DRF throttling or reverse-proxy rate limits (Nginx, Cloudflare).

DRF example:

```python
# settings.py
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "rest_framework.throttling.UserRateThrottle",
    "rest_framework.throttling.AnonRateThrottle",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "user": "1000/day",
    "anon": "100/day",
}
```

For stricter, use per-endpoint throttles or Redis-based rate limiting.

# 8 - Webhook signing (HMAC) - verify payloads

**Why:** Ensure request integrity and authenticity from 3rd-party services.

Example verifying HMAC signature in Django view:

```python
import hmac, hashlib
from django.http import HttpResponseForbidden, JsonResponse

SECRET = b"supersecret"

def verify_signature(body, signature_header):
    expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def webhook(request):
    signature = request.headers.get("X-Signature")
    if not verify_signature(request.body, signature):
        return HttpResponseForbidden("Invalid signature")
    # process payload
    return JsonResponse({"status": "ok"})
```

Use `hmac.compare_digest` to avoid timing attacks.

# 9 - Logging, monitoring, and alerting

**Why:** Detect intrusion, failed auth attempts, suspicious patterns.  
**What to log:** auth success/failures, token creation/revocation, admin actions, unusual rate patterns.

Sample logging config:

```python
# settings.py
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

Integrate with ELK / Splunk / Prometheus & Grafana for metrics and alerts.

# 10 - Secrets & keys management

**Principles:**

- Do NOT commit secrets to source control.
- Use environment variables or a secrets manager (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager).
- Rotate keys often and provide revocation.

Example of reading secrets:

```python
import os
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DB_PASSWORD = os.environ.get("DB_PASSWORD")
```

Use restricted IAM/ACL policies for the secrets store.

# 11 - Data protection (encryption at rest & in transit)

**In transit:** TLS (see section 2).  
**At rest:** Use database-level encryption, disk encryption, or encrypt specific sensitive fields (Django field encryption libs). Use access controls on DB backups.

# 12 - Vulnerability mitigation (other controls)

- **Dependency management:** update packages, use pip-audit.
- **Use prepared statements / ORM** - no string concatenation for SQL.
- **Run security scans / SAST / DAST**.
- **Limit response data** (avoid leaking PII).
- **Content Security Policy (CSP)** for web UIs.

# 13 - Full small example: DRF app with JWT, rate-limit, CORS, RBAC

```python
# settings.py (snippets)
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "50/day"},
}
CORS_ALLOWED_ORIGINS = ["https://your-frontend.example"]
```

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class Profile(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({"username": request.user.username, "email": request.user.email})
```

# 14 - Best practices checklist (quick)
- Enforce TLS everywhere.
- Use proper authentication (JWT/OAuth2/API key) depending on needs.
- Short-lived tokens + refresh tokens or token revocation.
- Principle of least privilege (RBAC/ACL).
- Input validation & output escaping.
- Rate limiting + anomaly detection.
- CORS configured to allowed origins.
- CSRF enabled for cookie-based sessions.
- Log and monitor auth events and rate-limit violations.
- Secrets stored in a secure store; rotate keys.
- Third-party webhook verification (HMAC).
- Regular dependency scans & pentests.

# 15 - Quick how-to pick-a-strategy

- **Public APIs for third-party apps / delegated access →** OAuth2.
- **Mobile apps / Single-page apps →** JWT (with refresh) or token auth + HTTPS.
- **Server-to-server →** mTLS or client credentials OAuth2 or API keys (with IP whitelisting).
- **Internal microservices →** JWT with mutual trust or mTLS + network isolation.

# 16 - Useful Django/DRF snippets (copy-paste summary)

**DRF Token ->** rest_framework.authtoken + obtain_auth_token.  
**JWT ->** djangorestframework-simplejwt with TokenObtainPairView.  
**OAuth2 ->** django-oauth-toolkit.  
**CORS ->** django-cors-headers.  
**Rate limiting ->** DRF throttling classes or reverse-proxy rate limits.  
**HMAC Webhook ->** use hmac.compare_digest.  
**RBAC ->** Django groups and DRF custom BasePermission.

# 17 - Final notes & common pitfalls

- **Never** send tokens in query strings. Always use Authorization header.
- **Do not** store plain text API keys in DB - consider hashing or storing only partial fingerprints.
- **JWT:** do not embed sensitive data inside tokens. Use user id and minimal claims.
- **Revoke access:** design a revocation strategy (DB blacklists, token jti, token versioning).
- **Testing:** add unit/integration tests for auth flows and failure cases.