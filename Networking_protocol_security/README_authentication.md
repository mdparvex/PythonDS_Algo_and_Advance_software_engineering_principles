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