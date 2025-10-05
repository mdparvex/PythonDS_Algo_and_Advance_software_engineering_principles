# FastAPI Authentication: Technical Documentation

This document provides a comprehensive guide to authentication in FastAPI, including different strategies, code examples, and explanations.

---

## 1. Introduction
Authentication is the process of verifying the identity of a user or client. FastAPI provides built-in support for authentication mechanisms through the `fastapi.security` module.

Common authentication methods include:
- **Basic Authentication**
- **OAuth2 with Password (and hashing)**
- **JWT (JSON Web Tokens)**

---

## 2. Basic Authentication
Basic Authentication sends the username and password with each request.

### Example
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()

@app.get("/basic-auth")
def basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == "admin" and credentials.password == "secret":
        return {"message": "Authenticated"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
```

### How it works
- Client sends `Authorization: Basic base64(username:password)` header.
- FastAPI decodes it and validates.

---

## 3. OAuth2 with Password Flow
OAuth2 is the industry standard for authentication. FastAPI provides `OAuth2PasswordBearer` for this.

### Example
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dummy users DB
users_db = {
    "john": {"username": "john", "password": "secret"}
}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    return {"access_token": user["username"], "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

### How it works
1. Client sends credentials to `/token`.
2. If valid, server returns `access_token`.
3. Client sends `Authorization: Bearer <token>` in requests.

---

## 4. JWT Authentication
JWT is widely used for stateless authentication.

### Example
```python
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

users_db = {
    "john": {"username": "john", "password": "secret"}
}

# Create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token({"sub": user["username"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### How it works
- User logs in with credentials.
- Server generates a signed JWT.
- Client sends JWT in headers.
- Server verifies and decodes the token.

---

## 5. Advanced Features

### a) Password Hashing
Always hash passwords using `bcrypt`.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

hashed_password = pwd_context.hash("secret")
print(hashed_password)

# Verify password
print(pwd_context.verify("secret", hashed_password))
```

### b) Role-Based Access Control (RBAC)
```python
from fastapi import Security
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/admin")
def admin_route(token: str = Security(oauth2_scheme)):
    # decode token and check role
    return {"message": "Admin access granted"}
```

---

## 6. Best Practices
- Use HTTPS in production.
- Always hash passwords.
- Set short-lived tokens with refresh tokens.
- Store secrets securely (e.g., environment variables).
- Implement RBAC or permissions.

---

## 7. Conclusion
FastAPI provides powerful authentication mechanisms like Basic Auth, OAuth2, and JWT. For production, JWT with password hashing and refresh tokens is the recommended approach.