Let's **fix this properly** and **use the _exact_ approach you were confused about**:

**APISettings + DEFAULTS + IMPORT_STRINGS pattern**  
(the same one you pasted earlier)

This time:

- We will **build a small Django REST project**
- Use **that SAME settings pattern**
- Wire it into **signup + login**
- And I'll explain **how the pieces connect at runtime**

No shortcuts. No alternative patterns.

**🎯 Goal (re-stated clearly)**

You want to understand **this pattern**:

```python
USER_SETTINGS
DEFAULTS
IMPORT_STRINGS
api_settings = APISettings(...)
```

And see it used in a **real signup/login flow**.

**📁 Project Structure (VERY IMPORTANT)**

```css
jwt_demo/
├── manage.py
├── jwt_demo/
│   ├── settings.py
│   └── urls.py
│
├── accounts/
│   ├── jwt_settings.py   👈 THE PATTERN (your confusion)
│   ├── jwt_utils.py      👈 uses api_settings
│   ├── serializers.py
│   ├── views.py
│   └── urls.py

```

**1️⃣ settings.py (user overrides)**

```python
# jwt_demo/settings.py
from datetime import timedelta

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': timedelta(minutes=10),
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
}
```

👉 User overrides only what they want.

**2️⃣ jwt_settings.py (THE CONFUSING PART - NOW CLEAR)**

```python
# accounts/jwt_settings.py
import datetime
from django.conf import settings
from rest_framework.settings import APISettings

USER_SETTINGS = getattr(settings, 'JWT_AUTH', None)

DEFAULTS = {
    'JWT_SECRET_KEY': settings.SECRET_KEY,
    'JWT_ALGORITHM': 'HS256',
    'JWT_EXPIRATION_DELTA': datetime.timedelta(minutes=5),

    'JWT_ENCODE_HANDLER':
        'accounts.jwt_utils.jwt_encode_handler',

    'JWT_DECODE_HANDLER':
        'accounts.jwt_utils.jwt_decode_handler',
}

IMPORT_STRINGS = (
    'JWT_ENCODE_HANDLER',
    'JWT_DECODE_HANDLER',
)

api_settings = APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)
```

🧠 **Key idea**  
This file does **NOT generate tokens**.  
It only defines **HOW things should behave**.

**3️⃣ jwt_utils.py (handlers referenced as STRINGS)**

```python
# accounts/jwt_utils.py
import jwt
from datetime import datetime
from django.contrib.auth.models import User
from .jwt_settings import api_settings


def jwt_encode_handler(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA,
    }

    return jwt.encode(
        payload,
        api_settings.JWT_SECRET_KEY,
        algorithm=api_settings.JWT_ALGORITHM,
    )


def jwt_decode_handler(token):
    return jwt.decode(
        token,
        api_settings.JWT_SECRET_KEY,
        algorithms=[api_settings.JWT_ALGORITHM],
    )
```

**🔥 IMPORTANT CONNECTION**

```python
api_settings.JWT_ENCODE_HANDLER
```

➡️ is **not a string anymore**  
➡️ it is **this function**:
```python
jwt_encode_handler
```
That's the magic of IMPORT_STRINGS.

**4️⃣ Serializers (unchanged, just validation)**

```python
# accounts/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
```

**5️⃣ Views (NOW using api_settings handlers)**

```python
# accounts/views.py
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import SignupSerializer, LoginSerializer
from .jwt_settings import api_settings
from django.contrib.auth.models import User
```

**🔹 Signup**

```python
class SignupAPIView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "User created"},
            status=status.HTTP_201_CREATED
        )
```

**🔹 Login (THIS IS WHERE YOUR CONFUSION GETS CLEARED)**

```python
class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(**serializer.validated_data)
        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 🔥 THIS is the pattern in action
        token = api_settings.JWT_ENCODE_HANDLER(user)

        return Response({"token": token})
```

**🧠 What happens here internally?**

- api_settings.JWT_ENCODE_HANDLER
- APISettings sees this is in IMPORT_STRINGS
- Imports accounts.jwt_utils.jwt_encode_handler
- Caches it
- Returns **function object**
- You call it like a normal function

NO MAGIC. Just delayed import.

**6️⃣ Protected API (decode handler)**

```python
class ProfileAPIView(APIView):
    def get(self, request):
        auth = request.headers.get("Authorization")
        if not auth:
            return Response({"error": "No token"}, status=401)

        token = auth.split(" ")[1]

        try:
            payload = api_settings.JWT_DECODE_HANDLER(token)
            user = User.objects.get(id=payload["user_id"])
        except Exception:
            return Response({"error": "Invalid token"}, status=401)

        return Response({
            "id": user.id,
            "username": user.username
        })
```

**7️⃣ URLs**

```python
# accounts/urls.py
from django.urls import path
from .views import SignupAPIView, LoginAPIView, ProfileAPIView

urlpatterns = [
    path("signup/", SignupAPIView.as_view()),
    path("login/", LoginAPIView.as_view()),
    path("profile/", ProfileAPIView.as_view()),
]
```

**🔁 COMPLETE FLOW (VERY IMPORTANT)**

```css
settings.py
  ↓
USER_SETTINGS (overrides)
  ↓
APISettings merges DEFAULTS + USER_SETTINGS
  ↓
IMPORT_STRINGS auto-import handlers
  ↓
Views call api_settings.JWT_ENCODE_HANDLER
  ↓
Actual function executes

```

**🧠 ONE-SENTENCE TAKEAWAY**

**APISettings lets you configure behavior using strings, override it safely from settings.py, and access everything as real Python objects at runtime.**