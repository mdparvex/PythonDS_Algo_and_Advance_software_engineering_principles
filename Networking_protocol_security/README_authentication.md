# 📖 Technical Documentation on Authentication in Web Applications (with Django Examples)

## 1\. Introduction

Authentication is the process of verifying the identity of a user before granting access to a system. In web applications, authentication ensures that only authorized users can access certain resources. Django, being a robust web framework, provides built-in authentication mechanisms while also supporting custom and third-party authentication methods.

This documentation covers:

- **Session-based authentication**
- **Token-based authentication (JWT, OAuth2, API Tokens)**
- **Social authentication**
- **Custom authentication methods**

For each, we’ll discuss **how it works, where it is used, pros & cons, and Django examples**.

## 2\. Session-Based Authentication

### 🔹 How it Works

- User logs in with username and password.
- Server verifies credentials and creates a **session** stored in the database.
- A **session ID** is sent back to the client as a cookie.
- On subsequent requests, the cookie is validated to identify the user.

### 🔹 Where to Use

- Traditional web apps with server-rendered HTML.
- Applications where server manages user sessions.

### 🔹 Pros & Cons

✅ Pros:

- Secure, server-managed.
- Easy to implement with Django.
- Built-in support.

❌ Cons:

- Not ideal for stateless APIs.
- Session storage can increase database load.

### 🔹 Django Example

**settings.py**

```python
INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.auth',
    ...
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    ...
]
```

**views.py**

```python
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect

def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")
```

## 3\. Token-Based Authentication

### 🔹 How it Works

- User sends credentials to server.
- Server generates a **token** (string) and returns it.
- Client stores the token (usually in localStorage or headers).
- On every request, the token is sent in the Authorization header.
- Server validates the token to authenticate the user.

### 🔹 Where to Use

- REST APIs and mobile applications.
- Stateless systems (scalable microservices).

### 3.1 API Token Authentication

✅ Pros:

- Simple to use with REST APIs.
- Stateless, no need to store sessions.

❌ Cons:

- Tokens must be stored securely.
- If compromised, tokens can be misused.

**Django REST Framework (DRF) Example**

**settings.py**

```python
INSTALLED_APPS += [
    'rest_framework',
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ]
}
```

**views.py**

```python
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth.models import User

@api_view(["POST"])
def get_token(request):
    username = request.data['username']
    password = request.data['password']
    user = User.objects.get(username=username)
    if user.check_password(password):
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})
    return Response({"error": "Invalid credentials"}, status=400)
```

### 3.2 JWT Authentication

JWT (**JSON Web Token**) is widely used in modern APIs.

✅ Pros:

- Self-contained (stores user data inside token).
- Works across microservices.

❌ Cons:

- If token is stolen, it can’t be invalidated until expiration.
- Larger payload compared to session ID.

**Django Example with djangorestframework-simplejwt:**
```bash
pip install djangorestframework-simplejwt
```
**settings.py**

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}
```

**urls.py**

```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

**Usage**

- Get Token: POST /api/token/ { "username": "test", "password": "pass" }
- Refresh Token: POST /api/token/refresh/ { "refresh": "..." }

### 3.3 OAuth2 Authentication

OAuth2 is an authorization framework used in third-party authentication (Google, Facebook, GitHub).

✅ Pros:

- Widely used for third-party login.
- Secure and standard.

❌ Cons:

- Complex setup.
- Requires third-party integration.

**Django Example using django-oauth-toolkit:**
```bash
pip install django-oauth-toolkit
```
**settings.py**
```python
INSTALLED_APPS += ['oauth2_provider']
```

**urls.py**

```python
from django.urls import path, include

urlpatterns = [
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
```

## 4\. Social Authentication

### 🔹 How it Works

- Uses external providers (Google, Facebook, GitHub).
- User authenticates with provider → provider returns token → app verifies identity.

### 🔹 Pros & Cons

✅ Pros:

- Easy for users (no new passwords).
- Trusted providers.

❌ Cons:

- Dependency on third-party availability.
- More complex setup.

### 🔹 Django Example with social-auth-app-django
```bash
pip install social-auth-app-django
```
**settings.py**

```python
INSTALLED_APPS += ['social_django']

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '<your-client-id>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '<your-client-secret>'
```

**urls.py**

```python
urlpatterns = [
    path('auth/', include('social_django.urls', namespace='social')),
]
```

## 5\. Custom Authentication

### 🔹 How it Works

- When built-in methods don’t fit, create a **custom authentication backend**.
- For example, login with **email** instead of username.

### 🔹 Django Example

**custom_backend.py**

```python
from django.contrib.auth.models import User

class EmailAuthBackend:
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
```
**settings.py**
```python
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'myapp.custom_backend.EmailAuthBackend',
]
```

## 6\. Comparison Table

| **Authentication** | **Best Use Case** | **Pros** | **Cons** |
| --- | --- | --- | --- |
| **Session-based** | Traditional Django apps | Simple, built-in | Not stateless |
| **Token-based** | REST APIs | Stateless, simple | Token leakage risk |
| **JWT** | Mobile apps, microservices | Self-contained, scalable | Hard to revoke |
| **OAuth2** | Third-party APIs | Secure, standard | Complex |
| **Social Login** | Easy sign-in | User convenience | Dependency on providers |
| **Custom** | Special requirements | Flexible | Extra coding effort |

## 7\. Conclusion

Django offers flexibility for implementing **different authentication strategies** depending on your application type:

- Use **sessions** for traditional apps.
- Use **JWT or TokenAuth** for APIs.
- Use **OAuth2/social login** for third-party integration.
- Use **custom backends** for special business logic.

✅ This documentation should serve as a **complete guide to authentication in Django**, covering the theory, pros/cons, and code examples.


---

# 🧭 Comprehensive Technical Documentation: Authentication in Django REST Framework (DRF)

## 📘 1. Overview - What Is Authentication?

**Authentication** is the process of verifying who a user or client is.  
In Django/DRF, authentication is handled by **authentication classes**, and authorization (permissions) happens afterward.

## 🧱 2. Authentication Types Covered

| **#** | **Authentication Type** | **Description** | **Typical Use** |
| --- | --- | --- | --- |
| 1   | Basic Authentication | Username/password encoded in every request | Quick testing, internal APIs |
| 2   | Session Authentication | Uses Django login sessions and cookies | Web apps, Admin panel |
| 3   | Token Authentication | Token generated and stored per user | Mobile/REST APIs |
| 4   | JWT Authentication | Stateless, secure JSON tokens | Scalable APIs, SPAs |
| 5   | OAuth2 Authentication | Delegated access via Google/Facebook etc. | Social login |
| 6   | API Key Authentication | API key in header | Internal microservices |
| 7   | Multi-Factor Authentication | Second step after password | Banking, secure apps |
| 8   | OpenID Connect / SSO | Enterprise authentication | Organization-wide login |

## 🧩 3. Project Setup

```bash
django-admin startproject auth_demo
cd auth_demo
python manage.py startapp users
pip install djangorestframework djangorestframework-simplejwt djangorestframework-authtoken django-allauth dj-rest-auth
python manage.py migrate
```

Add in settings.py:

```python
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'allauth',
    'allauth.account',
    'users',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

# 🧩 4. Basic Authentication

### ⚙️ Configuration

```python
# settings.py
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.BasicAuthentication',
]
```

### 🧠 How It Works

- Client sends username and password on each request:
    ```pgsql
    Authorization: Basic base64(username:password)
    ```
- Server decodes credentials → verifies user → attaches user to request.user.

### 🧪 Example

```python
# users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response

class BasicAuthView(APIView):
    def get(self, request):
        return Response({
            "message": f"Authenticated as {request.user.username}",
            "method": "Basic Auth"
        })
```

### 🔗 URL

```python
# users/urls.py
from django.urls import path
from .views import BasicAuthView

urlpatterns = [path('basic-auth/', BasicAuthView.as_view())]
```

**Test in Postman**:  
Authorization → Basic Auth → Username/Password.

# 🍪 5. Session Authentication

### ⚙️ Configuration

```python
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.SessionAuthentication',
]
```

### 🧠 How It Works

- Django stores a sessionid cookie after login.
- Each request automatically includes it.
- DRF verifies session cookie and retrieves user.

### 🧪 Example

```python
from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response

class SessionLoginView(APIView):
    permission_classes = []

    def post(self, request):
        user = authenticate(
            username=request.data['username'],
            password=request.data['password']
        )
        if user:
            login(request, user)
            return Response({"message": "Login successful"})
        return Response({"error": "Invalid credentials"}, status=400)

class SessionProtectedView(APIView):
    def get(self, request):
        return Response({"message": f"Session active for {request.user.username}"})
```

### 🔗 URL

```url
urlpatterns += [
    path('session/login/', SessionLoginView.as_view()),
    path('session/protected/', SessionProtectedView.as_view()),
]
```

# 🪙 6. Token Authentication

### ⚙️ Setup

```bash
pip install djangorestframework-authtoken
python manage.py migrate
```

```python
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.TokenAuthentication',
]
```

### 🧠 How It Works

- Server creates a token for each user.
- Client stores and sends Authorization: Token &lt;key&gt; in every request.

### 🧪 Example

```python
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request):
        response = super().post(request)
        token = Token.objects.get(key=response.data['token'])
        return Response({'token': token.key, 'user_id': token.user_id})
```

### Protected Endpoint

```python
from rest_framework.views import APIView

class TokenProtectedView(APIView):
    def get(self, request):
        return Response({"message": f"Authenticated with Token as {request.user.username}"})
```

### 🔗 URL

```python
urlpatterns += [
    path('token/login/', CustomObtainAuthToken.as_view()),
    path('token/protected/', TokenProtectedView.as_view()),
]
```

# 🧾 7. JWT Authentication

### ⚙️ Setup

```bash
pip install djangorestframework-simplejwt
```
```python
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
]
```

### 🧠 How It Works

- JWT = digitally signed token with payload (username, exp).
- Client gets `access` and `refresh` tokens.
- Sends access token in header for every request.

### 🧪 Example

```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response

class JWTProtectedView(APIView):
    def get(self, request):
        return Response({"message": f"JWT valid for {request.user.username}"})
```

### 🔗 URL

urlpatterns += \[

```python
urlpatterns += [
    path('jwt/token/', TokenObtainPairView.as_view()),
    path('jwt/refresh/', TokenRefreshView.as_view()),
    path('jwt/protected/', JWTProtectedView.as_view()),
]
```

# 🔐 8. OAuth2 (Social Authentication)

### ⚙️ Setup

```python
INSTALLED_APPS += [
    'dj_rest_auth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]
```

Run:
```bash
python manage.py migrate
```
### 🧠 How It Works

- Redirect user to Google/Facebook for login.
- After consent, provider returns token.
- Django exchanges token for user data → logs user in.

### 🧪 Example

```python
urlpatterns += [
    path('auth/google/', include('allauth.socialaccount.providers.google.urls')),
]
```

**Flow:**  
Frontend → /auth/google/login/ → redirects to Google → callback to /auth/google/callback/ → login success.

# 🤝 9. API Key Authentication (Custom)

### ⚙️ Custom Class

```python
# users/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.headers.get('X-API-Key')
        if key == 'mysecret123':
            user = User.objects.first()
            return (user, None)
        raise AuthenticationFailed('Invalid API Key')
```

### 🧪 Example

```python
# settings.py
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'users.authentication.APIKeyAuthentication',
]
```

```python
class APIKeyProtectedView(APIView):
    def get(self, request):
        return Response({"message": f"Access granted for {request.user.username}"})
```
### Test

Header:

```bash
X-API-Key: mysecret123
```

# 🔄 10. Multi-Factor Authentication (MFA)

### ⚙️ Flow

- User logs in with password.
- Server generates OTP.
- User submits OTP to verify.

### 🧪 Example

```python
from django.core.mail import send_mail
from rest_framework.views import APIView

class SendOTPView(APIView):
    def post(self, request):
        import random
        otp = random.randint(100000, 999999)
        request.session['otp'] = otp
        send_mail('OTP', f'Your OTP is {otp}', 'no-reply@app.com', [request.data['email']])
        return Response({"message": "OTP sent"})

class VerifyOTPView(APIView):
    def post(self, request):
        if int(request.data['otp']) == request.session.get('otp'):
            return Response({"message": "OTP verified"})
        return Response({"error": "Invalid OTP"}, status=400)
```

# 🧭 11. OpenID Connect / SSO Example

Used with **Keycloak**, **Auth0**, **Azure AD**, etc.

### ⚙️ Setup


```python
SOCIALACCOUNT_PROVIDERS = {
    'openid_connect': {
        'SERVERS': [
            {
                'id': 'keycloak',
                'name': 'Keycloak',
                'server_url': 'https://keycloak.example.com/realms/myrealm',
                'claims': ['email', 'profile'],
            }
        ]
    }
}
```

Users authenticate via external provider → token returned → DRF verifies via OIDC discovery.

# 🧰 12. Combined Authentication Example

```python
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.BasicAuthentication',
]
```

✅ DRF checks each class in order → first successful one authenticates.

# 📚 Summary Table

| **Type** | **Stateful** | **Setup Difficulty** | **Ideal For** | **Security** | **Example Header** |
| --- | --- | --- | --- | --- | --- |
| Basic | ❌   | 🔹 Easy | Testing, internal APIs | Low | Authorization: Basic ... |
| Session | ✅   | 🔹 Easy | Web apps | Medium | Cookie sessionid |
| Token | ❌   | ⚙️ Medium | Mobile APIs | Medium | Authorization: Token &lt;key&gt; |
| JWT | ❌   | ⚙️ Medium | Scalable APIs | High | Authorization: Bearer &lt;token&gt; |
| OAuth2 | ❌   | ⚙️⚙️ Complex | Social logins | Very High | Provider Token |
| API Key | ❌   | ⚙️ Medium | Internal service | Medium | X-API-Key: ... |
| MFA | ✅   | ⚙️⚙️ Complex | Secure systems | Very High | OTP |
| OIDC/SSO | ❌   | ⚙️⚙️ Complex | Enterprise login | Very High | Bearer Token |

# 🚀 Real-World Recommendations

| **Scenario** | **Best Auth Type** |
| --- | --- |
| Public API for mobile app | **JWT Authentication** |
| Internal API between services | **API Key Authentication** |
| Web App with Django templates | **Session Authentication** |
| Admin or quick testing | **Basic Authentication** |
| Corporate login (Google, Azure AD) | **OIDC / OAuth2** |
| Financial or medical systems | **JWT + MFA** |