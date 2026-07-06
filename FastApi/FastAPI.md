# FastAPI — Complete Technical Documentation

> **Version:** FastAPI 0.115.x | **Python:** 3.10+ | **Author:** Md Abdulla Al Mamun  
> **Last Updated:** June 2026

---

## Table of Contents

1. [Introduction & Philosophy](#1-introduction--philosophy)
2. [How FastAPI Works Internally](#2-how-fastapi-works-internally)
3. [Installation & Project Setup](#3-installation--project-setup)
4. [Core Concepts](#4-core-concepts)
   - 4.1 [Path Operations](#41-path-operations)
   - 4.2 [Request Parameters](#42-request-parameters)
   - 4.3 [Pydantic Models & Data Validation](#43-pydantic-models--data-validation)
   - 4.4 [Response Models](#44-response-models)
5. [Dependency Injection System](#5-dependency-injection-system)
6. [Authentication & Security](#6-authentication--security)
7. [Database Integration (Async SQLAlchemy)](#7-database-integration-async-sqlalchemy)
8. [Background Tasks & Async Patterns](#8-background-tasks--async-patterns)
9. [Middleware](#9-middleware)
10. [Advanced Routing & APIRouter](#10-advanced-routing--apirouter)
11. [WebSockets](#11-websockets)
12. [Error Handling](#12-error-handling)
13. [Testing](#13-testing)
14. [Real-World Project: MedTrack API](#14-real-world-project-medtrack-api)
15. [Performance Optimization](#15-performance-optimization)
16. [Deployment](#16-deployment)

---

## 1. Introduction & Philosophy

FastAPI is a modern, high-performance Python web framework for building APIs, built on top of **Starlette** (ASGI toolkit) and **Pydantic** (data validation). It was created by Sebastián Ramírez in 2018.

### Why FastAPI?

| Feature | Flask | Django REST | FastAPI |
|---|---|---|---|
| Performance | Medium | Medium | High (async-native) |
| Auto docs | ❌ | ❌ | ✅ Swagger + ReDoc |
| Type safety | ❌ | Partial | ✅ Full Pydantic |
| Async support | Limited | Limited | ✅ Native |
| Data validation | Manual | Serializers | ✅ Automatic |
| Learning curve | Low | High | Low-Medium |

### Core Design Pillars

```
FastAPI
  │
  ├── Starlette          → ASGI framework (routing, middleware, WebSockets)
  │     └── Uvicorn      → ASGI server (built on uvloop / asyncio)
  │
  └── Pydantic           → Data validation, serialization, JSON Schema
        └── Python Types  → Type hints drive everything
```

---

## 2. How FastAPI Works Internally

Understanding the request lifecycle is critical for advanced usage.

### 2.1 ASGI Request Lifecycle

```
Client HTTP Request
       │
       ▼
  ┌──────────────┐
  │   Uvicorn    │  ← ASGI Server (receives raw TCP, parses HTTP)
  └──────┬───────┘
         │  ASGI scope/receive/send callables
         ▼
  ┌──────────────┐
  │   Starlette  │  ← Middleware Stack (CORS, Auth, Logging, etc.)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   FastAPI    │  ← Router resolves path → finds endpoint function
  │   Router     │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │  Dependency Injection Resolution     │  ← Builds dependency tree
  │  (sync deps run in threadpool)       │
  └──────┬───────────────────────────────┘
         │
         ▼
  ┌──────────────┐
  │  Pydantic    │  ← Validates & coerces request data
  │  Validation  │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Your Route  │  ← Your async/sync function executes
  │  Function    │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Response    │  ← Pydantic serializes output → JSON
  │  Serializer  │
  └──────┬───────┘
         │
         ▼
  HTTP Response sent back to client
```

### 2.2 How OpenAPI Schema Is Generated

FastAPI inspects your function signatures at **application startup** (not per-request) and builds a complete OpenAPI 3.x schema:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

# FastAPI inspects this at startup:
# - Path: /items/{item_id}
# - Method: POST
# - Path param: item_id (int)
# - Query param: q (Optional[str])
# - Body: Item model → generates JSON Schema
# - Response: dict
@app.post("/items/{item_id}")
async def create_item(item_id: int, item: Item, q: str | None = None):
    return {"item_id": item_id, "item": item, "q": q}
```

FastAPI stores this metadata in `app.openapi_schema` (cached after first call to `/openapi.json`).

### 2.3 Sync vs Async Execution

```python
# ASYNC function → runs directly on the event loop
@app.get("/async-endpoint")
async def async_handler():
    result = await some_async_db_call()
    return result

# SYNC function → FastAPI automatically runs it in a ThreadPoolExecutor
# so it doesn't block the event loop
@app.get("/sync-endpoint")
def sync_handler():
    result = slow_blocking_io()  # safe — offloaded to thread pool
    return result
```

> **Rule of thumb:** Use `async def` when your code uses `await` (async DB, HTTP clients). Use `def` for CPU-bound or legacy blocking code. Never mix blocking calls inside `async def` without `asyncio.run_in_executor`.

---

## 3. Installation & Project Setup

### 3.1 Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows

# Install FastAPI with all optional dependencies
pip install "fastapi[all]"        # includes uvicorn, pydantic, email-validator, etc.

# Or minimal install
pip install fastapi uvicorn[standard]
```

### 3.2 Recommended Project Structure

```
medtrack-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app instantiation, lifespan
│   ├── config.py                # Settings via pydantic-settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Aggregates all v1 routers
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── patients.py
│   │           ├── prescriptions.py
│   │           └── pharmacy.py
│   │
│   ├── core/
│   │   ├── security.py          # JWT, password hashing
│   │   └── exceptions.py        # Custom exception handlers
│   │
│   ├── db/
│   │   ├── base.py              # SQLAlchemy Base
│   │   ├── session.py           # Async engine & session factory
│   │   └── models/              # ORM models
│   │
│   ├── schemas/                 # Pydantic request/response models
│   │   ├── patient.py
│   │   └── prescription.py
│   │
│   ├── crud/                    # DB operations
│   │   ├── patient.py
│   │   └── prescription.py
│   │
│   └── dependencies/            # Reusable FastAPI dependencies
│       ├── auth.py
│       └── db.py
│
├── tests/
│   ├── conftest.py
│   └── test_endpoints/
│
├── alembic/                     # DB migrations
├── alembic.ini
├── pyproject.toml
├── .env
└── docker-compose.yml
```

### 3.3 Application Settings with Pydantic

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "MedTrack API"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

```ini
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/medtrack
SECRET_KEY=your-super-secret-key-change-in-production
REDIS_URL=redis://localhost:6379/0
```

---

## 4. Core Concepts

### 4.1 Path Operations

```python
from fastapi import FastAPI, status

app = FastAPI()

# GET — retrieve resource
@app.get("/patients", status_code=status.HTTP_200_OK)
async def list_patients():
    ...

# POST — create resource
@app.post("/patients", status_code=status.HTTP_201_CREATED)
async def create_patient():
    ...

# PUT — full update (replace entire resource)
@app.put("/patients/{patient_id}", status_code=status.HTTP_200_OK)
async def update_patient(patient_id: int):
    ...

# PATCH — partial update
@app.patch("/patients/{patient_id}", status_code=status.HTTP_200_OK)
async def partial_update_patient(patient_id: int):
    ...

# DELETE — remove resource
@app.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int):
    ...
```

### 4.2 Request Parameters

FastAPI automatically determines parameter source from function signature:

```python
from fastapi import FastAPI, Path, Query, Header, Cookie, Body
from typing import Annotated

app = FastAPI()

@app.get("/patients/{patient_id}/prescriptions/{rx_id}")
async def get_prescription(
    # PATH PARAMETERS — from URL segment
    patient_id: Annotated[int, Path(title="Patient ID", ge=1)],
    rx_id: Annotated[int, Path(title="Prescription ID", ge=1)],

    # QUERY PARAMETERS — from ?key=value
    include_history: bool = False,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=3, max_length=100)] = None,

    # HEADER PARAMETERS — from HTTP headers
    x_client_version: Annotated[str | None, Header()] = None,

    # COOKIE PARAMETERS — from cookies
    session_id: Annotated[str | None, Cookie()] = None,
):
    """
    FastAPI automatically:
    - Converts types (str "42" → int 42)
    - Validates constraints (ge=1 means ≥ 1)
    - Returns 422 Unprocessable Entity on validation failure
    - Documents everything in OpenAPI schema
    """
    return {
        "patient_id": patient_id,
        "rx_id": rx_id,
        "page": page,
        "per_page": per_page,
    }
```

### 4.3 Pydantic Models & Data Validation

Pydantic models are the backbone of FastAPI. They define structure, validate data, and generate JSON Schema.

```python
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Annotated
from datetime import date, datetime
from enum import Enum
import re

class BloodGroup(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    O_POS = "O+"
    O_NEG = "O-"
    AB_POS = "AB+"
    AB_NEG = "AB-"

class PatientCreate(BaseModel):
    # Field() adds validation + OpenAPI metadata
    full_name: Annotated[str, Field(min_length=2, max_length=100, examples=["John Doe"])]
    email: EmailStr
    phone: Annotated[str, Field(pattern=r"^\+?[1-9]\d{9,14}$")]
    date_of_birth: date
    blood_group: BloodGroup
    weight_kg: Annotated[float, Field(gt=0, lt=500, description="Weight in kilograms")]
    height_cm: Annotated[float, Field(gt=0, lt=300)]
    allergies: list[str] = Field(default_factory=list)
    emergency_contact: str | None = None

    # Field-level validator
    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        # Remove spaces and dashes
        return re.sub(r"[\s\-]", "", v)

    # Model-level validator (runs after all fields validated)
    @model_validator(mode="after")
    def check_age(self) -> "PatientCreate":
        today = date.today()
        age = (today - self.date_of_birth).days / 365.25
        if age < 0:
            raise ValueError("Date of birth cannot be in the future")
        if age > 150:
            raise ValueError("Invalid date of birth")
        return self

    # Computed property
    @property
    def age(self) -> int:
        today = date.today()
        return int((today - self.date_of_birth).days / 365.25)

class PatientUpdate(BaseModel):
    """Partial update — all fields optional"""
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    allergies: list[str] | None = None
    emergency_contact: str | None = None

class PatientInDB(PatientCreate):
    """Adds DB-generated fields to the base model"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    model_config = {"from_attributes": True}  # Enables ORM mode (was orm_mode in v1)

class PatientResponse(BaseModel):
    """What we return to clients — subset of PatientInDB"""
    id: int
    full_name: str
    email: str
    blood_group: BloodGroup
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 4.4 Response Models

Response models control serialization and filter sensitive data:

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

app = FastAPI()

# response_model filters output fields and validates response
@app.post(
    "/patients",
    response_model=PatientResponse,         # controls output shape
    status_code=201,
    response_description="Patient created successfully",
    summary="Create a new patient",
    tags=["patients"],
)
async def create_patient(patient: PatientCreate):
    # Even if DB returns password hash etc., response_model filters it out
    db_patient = await save_patient_to_db(patient)
    return db_patient

# Exclude/include specific fields at runtime
@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    include_email: bool = False,
):
    patient = await get_patient_from_db(patient_id)
    # Dynamic field control
    exclude_fields = set() if include_email else {"email"}
    return JSONResponse(
        content=PatientResponse.model_validate(patient).model_dump(exclude=exclude_fields)
    )

# Union response model for multiple possible returns
from fastapi.responses import Response

@app.get(
    "/patients/{patient_id}/export",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF export"},
        404: {"description": "Patient not found"},
    }
)
async def export_patient_pdf(patient_id: int):
    pdf_bytes = await generate_pdf(patient_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=patient_{patient_id}.pdf"}
    )
```

---

## 5. Dependency Injection System

FastAPI's DI system is one of its most powerful features. Dependencies are declared as function parameters with `Depends()`.

### 5.1 Basic Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException, status
from typing import Annotated

app = FastAPI()

# Simple dependency — a function FastAPI calls automatically
async def get_db_session():
    """Creates a session, yields it, then closes it after request"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Type alias for cleaner code
DBSession = Annotated[AsyncSession, Depends(get_db_session)]

@app.get("/patients")
async def list_patients(db: DBSession):
    # db is automatically injected — no need to call get_db_session()
    result = await db.execute(select(Patient))
    return result.scalars().all()
```

### 5.2 Dependency Chains

Dependencies can depend on other dependencies, forming a tree:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Level 1: Extract raw token
async def get_raw_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    return token

# Level 2: Decode token → user_id
async def get_current_user_id(
    token: Annotated[str, Depends(get_raw_token)]
) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return int(user_id)

# Level 3: Fetch actual user from DB
async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: DBSession,
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Level 4: Verify user is active
async def get_active_user(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Level 5: Verify user has required role
def require_role(*roles: str):
    """Factory function that returns a dependency"""
    async def check_role(user: Annotated[User, Depends(get_active_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role!r} does not have access. Required: {roles}"
            )
        return user
    return check_role

# Usage — dependency chain auto-resolved
CurrentUser = Annotated[User, Depends(get_active_user)]
DoctorUser = Annotated[User, Depends(require_role("doctor", "admin"))]

@app.get("/prescriptions")
async def list_prescriptions(
    db: DBSession,
    current_user: CurrentUser,
):
    # FastAPI resolved the entire dependency chain automatically
    ...

@app.post("/prescriptions")
async def write_prescription(
    db: DBSession,
    doctor: DoctorUser,  # Only doctors/admins can write prescriptions
    data: PrescriptionCreate,
):
    ...
```

### 5.3 Class-Based Dependencies

```python
from fastapi import Depends, Query

class PaginationParams:
    """Reusable pagination dependency"""
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        per_page: Annotated[int, Query(ge=1, le=100)] = 20,
        sort_by: str = "created_at",
        sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    ):
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page
        self.sort_by = sort_by
        self.sort_order = sort_order

Pagination = Annotated[PaginationParams, Depends(PaginationParams)]

@app.get("/patients")
async def list_patients(db: DBSession, pagination: Pagination):
    query = (
        select(Patient)
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .order_by(
            getattr(Patient, pagination.sort_by).desc()
            if pagination.sort_order == "desc"
            else getattr(Patient, pagination.sort_by).asc()
        )
    )
    result = await db.execute(query)
    patients = result.scalars().all()
    return {
        "data": patients,
        "page": pagination.page,
        "per_page": pagination.per_page,
    }
```

### 5.4 Application-Level Dependencies with `lifespan`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis

redis_client: aioredis.Redis | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before `yield` → runs on startup
    Code after `yield` → runs on shutdown
    """
    # Startup: initialize shared resources
    global redis_client
    redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    print("✅ Redis connected")

    # Initialize DB connection pool
    await engine.dispose(close=False)
    print("✅ Database pool initialized")

    yield  # App runs here

    # Shutdown: cleanup
    await redis_client.close()
    await engine.dispose()
    print("🔴 Connections closed")

app = FastAPI(lifespan=lifespan)
```

---

## 6. Authentication & Security

### 6.1 JWT Authentication Implementation

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: int | str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: int | str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

```python
# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
):
    # Fetch user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is deactivated")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(payload: RefreshRequest, db: DBSession):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = int(data["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
```

### 6.2 API Key Security

```python
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(
    api_key: Annotated[str | None, Security(API_KEY_HEADER)],
    db: DBSession,
) -> "APIKey":
    if not api_key:
        raise HTTPException(status_code=403, detail="API key required")

    result = await db.execute(
        select(APIKey)
        .where(APIKey.key == api_key, APIKey.is_active == True)
    )
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=403, detail="Invalid or revoked API key")

    # Update last used timestamp
    key_obj.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return key_obj
```

---

## 7. Database Integration (Async SQLAlchemy)

### 7.1 Setup

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,       # Verifies connection before use
    pool_recycle=3600,        # Recycle connections after 1 hour
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Don't expire objects after commit (important for async)
)

class Base(DeclarativeBase):
    pass
```

### 7.2 ORM Models

```python
# app/db/models/patient.py
from sqlalchemy import String, Integer, Float, Date, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.patient import BloodGroup
import enum

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    prescriptions: Mapped[list["Prescription"]] = relationship(
        back_populates="patient",
        lazy="selectin",   # Async-safe: use selectin, not lazy="dynamic"
        cascade="all, delete-orphan",
    )
```

### 7.3 CRUD Operations

```python
# app/crud/patient.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

class PatientCRUD:
    async def get(self, db: AsyncSession, patient_id: int) -> Patient | None:
        return await db.get(Patient, patient_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> Patient | None:
        result = await db.execute(select(Patient).where(Patient.email == email))
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Patient], int]:
        # Build dynamic query
        filters = []
        if search:
            filters.append(
                or_(
                    Patient.full_name.ilike(f"%{search}%"),
                    Patient.email.ilike(f"%{search}%"),
                    Patient.phone.contains(search),
                )
            )
        if is_active is not None:
            filters.append(Patient.is_active == is_active)

        # Count query
        count_query = select(func.count(Patient.id)).where(and_(*filters))
        total = (await db.execute(count_query)).scalar()

        # Data query with eager loading
        data_query = (
            select(Patient)
            .where(and_(*filters))
            .options(selectinload(Patient.prescriptions))
            .offset(skip)
            .limit(limit)
            .order_by(Patient.created_at.desc())
        )
        result = await db.execute(data_query)
        return result.scalars().all(), total

    async def create(self, db: AsyncSession, data: PatientCreate) -> Patient:
        patient = Patient(**data.model_dump())
        db.add(patient)
        await db.flush()   # Gets the ID without committing
        await db.refresh(patient)
        return patient

    async def update(
        self, db: AsyncSession, patient: Patient, data: PatientUpdate
    ) -> Patient:
        update_data = data.model_dump(exclude_unset=True)  # Only set fields
        for field, value in update_data.items():
            setattr(patient, field, value)
        await db.flush()
        await db.refresh(patient)
        return patient

    async def delete(self, db: AsyncSession, patient_id: int) -> bool:
        patient = await self.get(db, patient_id)
        if not patient:
            return False
        await db.delete(patient)
        return True

    async def bulk_create(
        self, db: AsyncSession, patients_data: list[PatientCreate]
    ) -> list[Patient]:
        patients = [Patient(**d.model_dump()) for d in patients_data]
        db.add_all(patients)
        await db.flush()
        return patients

patient_crud = PatientCRUD()
```

---

## 8. Background Tasks & Async Patterns

### 8.1 Built-in Background Tasks

```python
from fastapi import BackgroundTasks
import asyncio

async def send_welcome_email(email: str, name: str):
    """Runs after response is sent — non-blocking"""
    await asyncio.sleep(0)  # yield to event loop
    # Send email via SMTP/SendGrid etc.
    print(f"Welcome email sent to {name} at {email}")

async def audit_log(action: str, user_id: int, details: dict):
    """Log to audit table asynchronously"""
    async with AsyncSessionLocal() as db:
        log = AuditLog(action=action, user_id=user_id, details=details)
        db.add(log)
        await db.commit()

@app.post("/patients", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient_data: PatientCreate,
    db: DBSession,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
):
    patient = await patient_crud.create(db, patient_data)
    await db.commit()

    # Schedule background work — runs after response is sent
    background_tasks.add_task(send_welcome_email, patient.email, patient.full_name)
    background_tasks.add_task(audit_log, "patient.created", current_user.id, {"patient_id": patient.id})

    return patient
```

### 8.2 Celery for Heavy Background Jobs

```python
# app/worker/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "medtrack",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Dhaka",
    enable_utc=True,
    task_routes={
        "app.worker.tasks.send_email": {"queue": "email"},
        "app.worker.tasks.generate_report": {"queue": "reports"},
    },
)

# app/worker/tasks.py
from app.worker.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_patient_report(self, patient_id: int, format: str = "pdf"):
    try:
        # Heavy computation — runs in separate Celery worker process
        data = fetch_patient_data(patient_id)
        report = render_report(data, format)
        upload_to_s3(report, f"reports/patient_{patient_id}.{format}")
        return {"status": "success", "patient_id": patient_id}
    except Exception as exc:
        raise self.retry(exc=exc)

# Trigger from FastAPI endpoint
@app.post("/patients/{patient_id}/reports")
async def trigger_report(patient_id: int, format: str = "pdf"):
    task = generate_patient_report.delay(patient_id, format)
    return {"task_id": task.id, "status": "queued"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
```

### 8.3 Async Patterns — HTTP Client Pool

```python
# app/core/http_client.py
import httpx
from contextlib import asynccontextmanager

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    """Returns the shared pooled HTTP client"""
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized. Check lifespan.")
    return _http_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    yield
    await _http_client.aclose()

# Use in endpoints
@app.get("/external-data")
async def fetch_external(client: Annotated[httpx.AsyncClient, Depends(get_http_client)]):
    response = await client.get("https://api.example.com/data")
    return response.json()
```

---

## 9. Middleware

Middleware intercepts every request/response. Order matters — they stack like LIFO.

```python
# app/main.py
import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# 1. CORS — must be added first (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://medeasy.health", "https://app.medeasy.health"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# 2. Trusted Hosts (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["medeasy.health", "*.medeasy.health", "localhost"],
)

# 3. GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. Custom: Request ID + Timing middleware
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Assign unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = (time.perf_counter() - start_time) * 1000

        # Attach timing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Structured logging
        print(
            f"method={request.method} "
            f"path={request.url.path} "
            f"status={response.status_code} "
            f"duration={process_time:.2f}ms "
            f"request_id={request_id}"
        )

        return response

app.add_middleware(RequestContextMiddleware)

# 5. Custom: Rate limiting middleware
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._requests: dict[str, list[datetime]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.period)

        # Clean old requests
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        if len(self._requests[client_ip]) >= self.calls:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.period)},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware, calls=100, period=60)
```

---

## 10. Advanced Routing & APIRouter

### 10.1 Router Composition

```python
# app/api/v1/endpoints/patients.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated

router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    dependencies=[Depends(get_active_user)],  # Applied to ALL routes in this router
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)

@router.get("/", response_model=PaginatedResponse[PatientResponse])
async def list_patients(
    db: DBSession,
    pagination: Pagination,
    search: str | None = None,
    is_active: bool | None = None,
):
    patients, total = await patient_crud.list(
        db,
        skip=pagination.offset,
        limit=pagination.per_page,
        search=search,
        is_active=is_active,
    )
    return PaginatedResponse(
        data=patients,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=-(-total // pagination.per_page),  # Ceiling division
    )

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: DBSession):
    patient = await patient_crud.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    db: DBSession,
    doctor: DoctorUser,
    bg: BackgroundTasks,
):
    # Check email uniqueness
    existing = await patient_crud.get_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    patient = await patient_crud.create(db, data)
    await db.commit()
    bg.add_task(send_welcome_email, patient.email, patient.full_name)
    return patient
```

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, patients, prescriptions, pharmacy

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(prescriptions.router)
api_router.include_router(pharmacy.router)

# app/main.py
app.include_router(api_router)
```

### 10.2 Generic Response Model

```python
# app/schemas/common.py
from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool = False
    has_previous: bool = False

    def model_post_init(self, __context) -> None:
        self.has_next = self.page < self.total_pages
        self.has_previous = self.page > 1

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "OK"
    errors: list[str] = []
```

---

## 11. WebSockets

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any
import json

class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        # room_id → list of WebSocket connections
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)

    async def broadcast(self, room_id: str, message: dict[str, Any]):
        if room_id not in self.rooms:
            return
        dead = []
        for ws in self.rooms[room_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.rooms[room_id].discard(ws)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/notifications/{user_id}")
async def notification_websocket(
    websocket: WebSocket,
    user_id: int,
    token: str,  # Auth via query param for WebSocket
):
    # Validate token
    try:
        payload = decode_token(token)
        if int(payload["sub"]) != user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return
    except Exception:
        await websocket.close(code=1008, reason="Invalid token")
        return

    room_id = f"user_{user_id}"
    await manager.connect(websocket, room_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await manager.send_personal(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        print(f"User {user_id} disconnected")

# Trigger notification from any endpoint
@app.post("/notifications/send")
async def send_notification(user_id: int, notification: dict):
    await manager.broadcast(f"user_{user_id}", {
        "type": "notification",
        "payload": notification,
    })
    return {"sent": True}
```

---

## 12. Error Handling

### 12.1 Custom Exception Handlers

```python
# app/core/exceptions.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": identifier},
        )

class ConflictException(AppException):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details={"field": field} if field else {},
        )

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format Pydantic v2 validation errors nicely
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({
                "field": field or "body",
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": errors,
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database integrity error: {exc}")
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "code": "CONFLICT",
                "message": "Resource already exists or violates constraints",
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )
```

---

## 13. Testing

### 13.1 Setup

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.session import Base, get_db_session
from app.core.security import create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    # Override the real DB session with test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(client, db_session):
    """Creates a test user and returns auth headers"""
    # Create test user directly in DB
    user = User(email="test@example.com", hashed_password=hash_password("testpass123"), role="admin", is_active=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}
```

### 13.2 Endpoint Tests

```python
# tests/test_endpoints/test_patients.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestPatientEndpoints:
    async def test_list_patients_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/patients")
        assert response.status_code == 401

    async def test_list_patients_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/patients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []

    async def test_create_patient_success(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "full_name": "Test Patient",
            "email": "patient@example.com",
            "phone": "+8801700000000",
            "date_of_birth": "1990-01-15",
            "blood_group": "O+",
            "weight_kg": 70.0,
            "height_cm": 170.0,
        }
        response = await client.post("/api/v1/patients", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "patient@example.com"
        assert "id" in data
        assert "created_at" in data

    async def test_create_patient_duplicate_email(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "full_name": "Another Patient",
            "email": "patient@example.com",  # Same email
            "phone": "+8801700000001",
            "date_of_birth": "1985-05-20",
            "blood_group": "A+",
            "weight_kg": 65.0,
            "height_cm": 165.0,
        }
        response = await client.post("/api/v1/patients", json=payload, headers=auth_headers)
        assert response.status_code == 409
        assert response.json()["code"] == "CONFLICT"

    async def test_create_patient_validation_error(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "full_name": "A",       # Too short (min_length=2 but also min_length enforced)
            "email": "not-an-email",
            "phone": "123",         # Invalid phone
        }
        response = await client.post("/api/v1/patients", json=payload, headers=auth_headers)
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert len(data["errors"]) > 0

    async def test_get_patient_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/patients/99999", headers=auth_headers)
        assert response.status_code == 404
```

---

## 14. Real-World Project: MedTrack API

A complete **prescription and medication tracking system** — a real problem in digital health.

**Problem:** Patients forget medications, doctors can't track adherence, pharmacies don't know if prescriptions are already dispensed.

**Solution:** MedTrack API — connects doctors, patients, and pharmacies in real time.

### 14.1 Complete `main.py`

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import redis.asyncio as aioredis
import httpx

from app.config import settings
from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.middleware import RequestContextMiddleware, RateLimitMiddleware
from app.db.session import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    print("✅ MedTrack API started")

    yield

    # Shutdown
    await app.state.redis.close()
    await app.state.http_client.aclose()
    await engine.dispose()
    print("🔴 MedTrack API stopped")

app = FastAPI(
    title="MedTrack API",
    description="Prescription & Medication Adherence Tracking System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware (outermost first)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, calls=200, period=60)

register_exception_handlers(app)
app.include_router(api_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "MedTrack API",
    }
```

### 14.2 Prescription System

```python
# app/schemas/prescription.py
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date, datetime

class MedicationFrequency(str, Enum):
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    EVERY_8_HOURS = "every_8_hours"
    EVERY_12_HOURS = "every_12_hours"
    AS_NEEDED = "as_needed"
    WEEKLY = "weekly"

class PrescriptionStatus(str, Enum):
    ACTIVE = "active"
    DISPENSED = "dispensed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PrescribedMedication(BaseModel):
    drug_generic_name: str = Field(min_length=2, max_length=200)
    drug_brand_name: str | None = None
    strength: str = Field(examples=["500mg", "10mg/5ml"])
    dosage_form: str = Field(examples=["tablet", "capsule", "syrup", "injection"])
    frequency: MedicationFrequency
    duration_days: int = Field(gt=0, le=365)
    quantity: int = Field(gt=0)
    instructions: str | None = Field(None, max_length=500)
    is_before_food: bool = True

class PrescriptionCreate(BaseModel):
    patient_id: int
    diagnosis: str = Field(min_length=5, max_length=500)
    chief_complaint: str = Field(min_length=5, max_length=500)
    medications: list[PrescribedMedication] = Field(min_length=1, max_length=20)
    notes: str | None = None
    follow_up_date: date | None = None
    is_valid_days: int = Field(default=30, ge=1, le=180, description="Prescription validity in days")

class PrescriptionResponse(BaseModel):
    id: int
    prescription_number: str
    patient_id: int
    doctor_id: int
    diagnosis: str
    medications: list[PrescribedMedication]
    status: PrescriptionStatus
    issued_at: datetime
    expires_at: datetime
    follow_up_date: date | None
    qr_code_url: str | None

    model_config = {"from_attributes": True}
```

```python
# app/api/v1/endpoints/prescriptions.py
from fastapi import APIRouter, BackgroundTasks
import qrcode
import io
import base64
from datetime import datetime, timedelta
from sqlalchemy import select

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

def generate_prescription_number() -> str:
    import random, string
    prefix = "RX"
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{date_str}-{suffix}"

def generate_qr_code(prescription_number: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"https://medtrack.health/rx/{prescription_number}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

@router.post("/", response_model=PrescriptionResponse, status_code=201)
async def create_prescription(
    data: PrescriptionCreate,
    db: DBSession,
    doctor: DoctorUser,
    background_tasks: BackgroundTasks,
):
    # Verify patient exists
    patient = await db.get(Patient, data.patient_id)
    if not patient:
        raise NotFoundException("Patient", data.patient_id)

    prescription_number = generate_prescription_number()
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(days=data.is_valid_days)

    prescription = Prescription(
        prescription_number=prescription_number,
        patient_id=data.patient_id,
        doctor_id=doctor.id,
        diagnosis=data.diagnosis,
        chief_complaint=data.chief_complaint,
        medications=[med.model_dump() for med in data.medications],
        notes=data.notes,
        follow_up_date=data.follow_up_date,
        status=PrescriptionStatus.ACTIVE,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    db.add(prescription)
    await db.flush()
    await db.refresh(prescription)
    await db.commit()

    # Background: Generate QR code & notify patient
    background_tasks.add_task(attach_qr_code, prescription.id, prescription_number)
    background_tasks.add_task(
        notify_patient_prescription,
        patient.email,
        patient.full_name,
        prescription_number,
    )

    return prescription

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise NotFoundException("Prescription", prescription_id)

    # Check access: patient can only see their own prescriptions
    if current_user.role == "patient" and prescription.patient_id != current_user.patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return prescription

@router.patch("/{prescription_id}/dispense", response_model=PrescriptionResponse)
async def dispense_prescription(
    prescription_id: int,
    db: DBSession,
    pharmacist: Annotated[User, Depends(require_role("pharmacist", "admin"))],
    background_tasks: BackgroundTasks,
):
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise NotFoundException("Prescription", prescription_id)

    if prescription.status != PrescriptionStatus.ACTIVE:
        raise ConflictException(
            f"Prescription is already {prescription.status.value}. Cannot dispense."
        )

    if datetime.utcnow() > prescription.expires_at:
        prescription.status = PrescriptionStatus.EXPIRED
        await db.commit()
        raise ConflictException("Prescription has expired")

    prescription.status = PrescriptionStatus.DISPENSED
    prescription.dispensed_by = pharmacist.id
    prescription.dispensed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(prescription)

    # Notify doctor and patient of dispense event
    background_tasks.add_task(notify_prescription_dispensed, prescription)

    return prescription

@router.get("/verify/{prescription_number}")
async def verify_prescription(prescription_number: str, db: DBSession):
    """Public endpoint for QR code scanning — no auth required"""
    result = await db.execute(
        select(Prescription).where(Prescription.prescription_number == prescription_number)
    )
    prescription = result.scalar_one_or_none()

    if not prescription:
        return {"valid": False, "reason": "Prescription not found"}

    if datetime.utcnow() > prescription.expires_at:
        return {"valid": False, "reason": "Prescription expired", "expired_at": prescription.expires_at}

    if prescription.status != PrescriptionStatus.ACTIVE:
        return {
            "valid": False,
            "reason": f"Prescription already {prescription.status.value}",
            "dispensed_at": prescription.dispensed_at,
        }

    return {
        "valid": True,
        "prescription_number": prescription_number,
        "patient_name": prescription.patient.full_name,
        "issued_by": prescription.doctor.full_name,
        "medications_count": len(prescription.medications),
        "expires_at": prescription.expires_at,
    }
```

### 14.3 Medication Adherence Tracking

```python
# app/api/v1/endpoints/adherence.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, date, timedelta
from pydantic import BaseModel

router = APIRouter(prefix="/adherence", tags=["Medication Adherence"])

class DoseLog(BaseModel):
    prescription_id: int
    medication_index: int    # Index in prescription.medications list
    taken_at: datetime
    skipped: bool = False
    skip_reason: str | None = None

class AdherenceReport(BaseModel):
    patient_id: int
    period_days: int
    total_doses_required: int
    total_doses_taken: int
    adherence_percentage: float
    missed_doses: int
    streak_days: int
    risk_level: str           # "low", "medium", "high"

@router.post("/log-dose", status_code=201)
async def log_medication_dose(
    dose: DoseLog,
    db: DBSession,
    current_user: CurrentUser,
):
    """Patient logs when they take a medication"""
    prescription = await db.get(Prescription, dose.prescription_id)
    if not prescription or prescription.patient_id != current_user.patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    log = DosageLog(
        prescription_id=dose.prescription_id,
        patient_id=current_user.patient_id,
        medication_index=dose.medication_index,
        taken_at=dose.taken_at,
        skipped=dose.skipped,
        skip_reason=dose.skip_reason,
    )
    db.add(log)
    await db.commit()

    # Check if adherence is dropping — trigger alert
    adherence = await calculate_adherence(db, current_user.patient_id, days=7)
    if adherence < 70.0:
        await manager.broadcast(f"doctor_{prescription.doctor_id}", {
            "type": "low_adherence_alert",
            "patient_id": current_user.patient_id,
            "adherence_7day": adherence,
        })

    return {"logged": True, "message": "Dose recorded successfully"}

@router.get("/report/{patient_id}", response_model=AdherenceReport)
async def get_adherence_report(
    patient_id: int,
    db: DBSession,
    doctor: DoctorUser,
    period_days: int = 30,
):
    """Doctor views patient adherence report"""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise NotFoundException("Patient", patient_id)

    since = datetime.utcnow() - timedelta(days=period_days)

    # Fetch all prescriptions in period
    rx_result = await db.execute(
        select(Prescription)
        .where(
            Prescription.patient_id == patient_id,
            Prescription.issued_at >= since,
            Prescription.status.in_([PrescriptionStatus.ACTIVE, PrescriptionStatus.DISPENSED])
        )
    )
    prescriptions = rx_result.scalars().all()

    # Calculate expected doses
    total_expected = 0
    for rx in prescriptions:
        for med in rx.medications:
            freq_map = {
                "once_daily": 1, "twice_daily": 2, "three_times_daily": 3,
                "four_times_daily": 4, "every_8_hours": 3, "every_12_hours": 2,
                "weekly": 1/7,
            }
            daily_doses = freq_map.get(med["frequency"], 1)
            duration = min(med["duration_days"], period_days)
            total_expected += int(daily_doses * duration)

    # Count actual dose logs
    log_result = await db.execute(
        select(func.count(DosageLog.id)).where(
            DosageLog.patient_id == patient_id,
            DosageLog.taken_at >= since,
            DosageLog.skipped == False,
        )
    )
    doses_taken = log_result.scalar() or 0

    adherence_pct = (doses_taken / total_expected * 100) if total_expected > 0 else 100.0
    risk = "low" if adherence_pct >= 80 else "medium" if adherence_pct >= 60 else "high"

    return AdherenceReport(
        patient_id=patient_id,
        period_days=period_days,
        total_doses_required=total_expected,
        total_doses_taken=doses_taken,
        adherence_percentage=round(adherence_pct, 2),
        missed_doses=total_expected - doses_taken,
        streak_days=await calculate_streak(db, patient_id),
        risk_level=risk,
    )

@router.websocket("/ws/reminders/{patient_id}")
async def medication_reminder_ws(websocket: WebSocket, patient_id: int, token: str):
    """Real-time medication reminders via WebSocket"""
    try:
        payload = decode_token(token)
        if int(payload["sub"]) != patient_id:
            await websocket.close(1008)
            return
    except Exception:
        await websocket.close(1008)
        return

    room_id = f"reminders_{patient_id}"
    await manager.connect(websocket, room_id)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ack":
                # Patient acknowledged reminder
                await log_reminder_ack(patient_id, data.get("medication_id"))
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
```

### 14.4 Analytics & Reporting

```python
# app/api/v1/endpoints/analytics.py
from fastapi import APIRouter
from sqlalchemy import func, case, cast, Float

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard")
async def get_dashboard_stats(
    db: DBSession,
    admin: Annotated[User, Depends(require_role("admin"))],
    period_days: int = 30,
):
    """Admin dashboard with key metrics"""
    since = datetime.utcnow() - timedelta(days=period_days)

    # Parallel queries using asyncio.gather
    patients_task = db.execute(
        select(func.count(Patient.id)).where(Patient.created_at >= since)
    )
    rx_task = db.execute(
        select(func.count(Prescription.id)).where(Prescription.issued_at >= since)
    )
    dispensed_task = db.execute(
        select(func.count(Prescription.id)).where(
            Prescription.status == PrescriptionStatus.DISPENSED,
            Prescription.issued_at >= since,
        )
    )

    import asyncio
    patients_result, rx_result, dispensed_result = await asyncio.gather(
        patients_task, rx_task, dispensed_task
    )

    new_patients = patients_result.scalar()
    total_prescriptions = rx_result.scalar()
    dispensed_count = dispensed_result.scalar()

    return {
        "period_days": period_days,
        "new_patients": new_patients,
        "total_prescriptions": total_prescriptions,
        "dispensed_prescriptions": dispensed_count,
        "dispense_rate": round(dispensed_count / total_prescriptions * 100, 2) if total_prescriptions else 0,
        "top_diagnoses": await get_top_diagnoses(db, since),
        "top_medications": await get_top_medications(db, since),
    }

async def get_top_diagnoses(db, since) -> list[dict]:
    result = await db.execute(
        select(Prescription.diagnosis, func.count().label("count"))
        .where(Prescription.issued_at >= since)
        .group_by(Prescription.diagnosis)
        .order_by(func.count().desc())
        .limit(10)
    )
    return [{"diagnosis": row.diagnosis, "count": row.count} for row in result]
```

---

## 15. Performance Optimization

### 15.1 Caching with Redis

```python
# app/core/cache.py
import json
import hashlib
from functools import wraps
from typing import Callable, Any
import redis.asyncio as aioredis
from fastapi import Request

def cache_response(ttl: int = 300, key_prefix: str = ""):
    """Decorator that caches endpoint responses in Redis"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name + kwargs
            request: Request = kwargs.get("request") or (args[0] if args else None)
            cache_key_data = f"{key_prefix}:{func.__name__}:{json.dumps(kwargs, sort_keys=True, default=str)}"
            cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()[:32]

            # Try cache first
            redis: aioredis.Redis = request.app.state.redis
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)

            # Miss — execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await redis.setex(cache_key, ttl, json.dumps(result, default=str))
            return result

        return wrapper
    return decorator

# Usage
@router.get("/analytics/dashboard")
@cache_response(ttl=300, key_prefix="dashboard")
async def get_dashboard(request: Request, db: DBSession, admin: AdminUser):
    ...

# Manual cache invalidation
async def invalidate_patient_cache(redis: aioredis.Redis, patient_id: int):
    pattern = f"patient:{patient_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
```

### 15.2 Database Query Optimization

```python
# Use select_in loading instead of lazy (N+1 problem prevention)
from sqlalchemy.orm import selectinload, joinedload

async def get_prescriptions_with_details(db: AsyncSession, patient_id: int):
    result = await db.execute(
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .options(
            selectinload(Prescription.patient),         # Separate SELECT for patients
            joinedload(Prescription.doctor),            # JOIN for doctors (1:1)
        )
        .order_by(Prescription.issued_at.desc())
    )
    return result.unique().scalars().all()

# Bulk operations instead of individual inserts
async def bulk_insert_dose_logs(db: AsyncSession, logs: list[dict]):
    await db.execute(insert(DosageLog), logs)
    await db.commit()

# Use database-level pagination
async def paginated_query(db: AsyncSession, page: int, per_page: int):
    # Window function for total count in same query
    total_subq = select(func.count()).select_from(Patient).scalar_subquery()

    result = await db.execute(
        select(Patient, total_subq.label("total"))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()
    total = rows[0].total if rows else 0
    return [r.Patient for r in rows], total
```

### 15.3 Async Concurrent Requests

```python
import asyncio

@router.get("/patients/{patient_id}/full-profile")
async def get_full_patient_profile(patient_id: int, db: DBSession):
    """Fetch multiple related data concurrently"""

    # All queries run concurrently — NOT sequentially
    patient, prescriptions, adherence, allergies = await asyncio.gather(
        get_patient(db, patient_id),
        get_active_prescriptions(db, patient_id),
        calculate_adherence(db, patient_id, days=30),
        get_allergy_alerts(db, patient_id),
    )

    if not patient:
        raise NotFoundException("Patient", patient_id)

    return {
        "patient": patient,
        "active_prescriptions": prescriptions,
        "adherence_30day": adherence,
        "allergy_alerts": allergies,
    }
```

---

## 16. Deployment

### 16.1 Gunicorn + Uvicorn Workers

```bash
# Production command
gunicorn app.main:app \
  --workers 4 \                    # CPU count * 2 + 1
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --keepalive 5 \
  --max-requests 1000 \           # Restart workers after N requests (memory leak prevention)
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### 16.2 Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Security: don't run as root
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30"]
```

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://medtrack:secret@db:5432/medtrack
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: medtrack
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: medtrack
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medtrack"]
      interval: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5
    restart: unless-stopped

  celery_worker:
    build: .
    command: celery -A app.worker.celery_app worker --loglevel=info -Q email,reports -c 4
    environment:
      - DATABASE_URL=postgresql+asyncpg://medtrack:secret@db:5432/medtrack
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 16.3 Nginx Configuration

```nginx
# nginx.conf
upstream fastapi_backend {
    least_conn;
    server api:8000;
}

server {
    listen 80;
    server_name medtrack.health;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name medtrack.health;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Proxy to FastAPI
    location /api/ {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://fastapi_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }

    # Docs (restrict in prod)
    location ~ ^/(docs|redoc|openapi.json) {
        allow 10.0.0.0/8;
        deny all;
        proxy_pass http://fastapi_backend;
    }
}
```

### 16.4 Alembic Migrations

```bash
# Initialize
alembic init alembic

# alembic/env.py — configure async
from app.db.session import Base, engine
from app.db.models import *  # Import all models

# Generate migration
alembic revision --autogenerate -m "add_prescription_table"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

---

## Summary — FastAPI Cheat Sheet

```python
# Quick reference for common patterns

# ── Routing ──
@app.get("/items/{id}", response_model=ItemOut, status_code=200, tags=["Items"])

# ── Parameters ──
path_id: Annotated[int, Path(ge=1)]          # Path param with validation
q: Annotated[str | None, Query(max_length=50)] = None  # Optional query param
body: ItemCreate                               # Request body (Pydantic model)

# ── Dependencies ──
db: Annotated[AsyncSession, Depends(get_db)]  # Injected dependency
user: Annotated[User, Depends(get_active_user)]

# ── Errors ──
raise HTTPException(status_code=404, detail="Not found")

# ── Background Tasks ──
background_tasks.add_task(send_email, to="user@example.com")

# ── Response ──
return JSONResponse(content={...}, status_code=201)
return Response(content=bytes_data, media_type="application/pdf")
return StreamingResponse(generator(), media_type="text/event-stream")

# ── Lifespan ──
@asynccontextmanager
async def lifespan(app):
    # startup
    yield
    # shutdown

# ── Testing ──
async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    response = await client.get("/items/1", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
```

---

*Documentation compiled for MedEasy Healthcare Limited — MedTrack API system.*  
*Framework: FastAPI 0.115.x | Python 3.12 | SQLAlchemy 2.x async | Pydantic v2*
