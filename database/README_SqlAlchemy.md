# SQLAlchemy Technical Documentation

## 1. Introduction
SQLAlchemy is a **Python SQL toolkit and Object Relational Mapper (ORM)**. It provides powerful abstractions for interacting with databases, combining the flexibility of raw SQL with the convenience of high-level ORM features.

SQLAlchemy has two main layers:
- **Core (SQL Expression Language)** – low-level, closer to raw SQL.
- **ORM (Object Relational Mapper)** – high-level, maps Python classes to tables.

This documentation covers **setup, core usage, ORM features, migrations, advanced queries, async support, and production best practices**.

---

## 2. Installation
```bash
pip install sqlalchemy psycopg2-binary alembic
```
For async usage with PostgreSQL:
```bash
pip install sqlalchemy[asyncio] asyncpg
```

---

## 3. Project Structure Example
```
sqlalchemy_project/
├─ app/
│  ├─ __init__.py
│  ├─ database.py
│  ├─ models.py
│  ├─ crud.py
│  ├─ main.py
├─ alembic/
├─ alembic.ini
└─ requirements.txt
```

---

## 4. Database Configuration
**app/database.py**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

---

## 5. Defining Models
**app/models.py**
```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)

    posts = relationship("Post", back_populates="owner")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="posts")
```

---

## 6. Creating Tables
```python
from app.database import engine, Base
from app import models

Base.metadata.create_all(bind=engine)
```

---

## 7. Basic CRUD Operations
**app/crud.py**
```python
from sqlalchemy.orm import Session
from . import models

def create_user(db: Session, name: str, email: str):
    user = models.User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_users(db: Session):
    return db.query(models.User).all()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_post(db: Session, user_id: int, title: str, content: str):
    post = models.Post(title=title, content=content, owner_id=user_id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post
```

---

## 8. Using Sessions in Main
**app/main.py**
```python
from app.database import SessionLocal
from app import crud

# Create a session
db = SessionLocal()

# Create a user
new_user = crud.create_user(db, name="Alice", email="alice@example.com")
print("Created User:", new_user.name)

# Create a post
post = crud.create_post(db, user_id=new_user.id, title="My First Post", content="Hello World")
print("Post Created:", post.title)

# Query users
users = crud.get_users(db)
for user in users:
    print(user.id, user.name, user.email)
```

**Output:**
```
Created User: Alice
Post Created: My First Post
1 Alice alice@example.com
```

---

## 9. Advanced Queries
### 9.1 Filtering and Ordering
```python
users = db.query(models.User).filter(models.User.name.like("A%")) \
                             .order_by(models.User.id.desc()).all()
```

### 9.2 Join Queries
```python
results = db.query(models.User.name, models.Post.title) \
             .join(models.Post, models.User.id == models.Post.owner_id).all()
for name, title in results:
    print(name, "->", title)
```

### 9.3 Aggregations
```python
from sqlalchemy import func

post_count = db.query(func.count(models.Post.id)).scalar()
print("Total posts:", post_count)
```

### 9.4 Subqueries
```python
subq = db.query(models.Post.owner_id, func.count(models.Post.id).label("post_count")) \
         .group_by(models.Post.owner_id).subquery()

results = db.query(models.User.name, subq.c.post_count).join(subq, models.User.id == subq.c.owner_id).all()
```

### 9.5 Eager Loading
```python
from sqlalchemy.orm import joinedload

users = db.query(models.User).options(joinedload(models.User.posts)).all()
for user in users:
    print(user.name, [post.title for post in user.posts])
```

---

## 10. Alembic Migrations
1. Initialize Alembic:
```bash
alembic init alembic
```
2. Configure `alembic.ini` with `DATABASE_URL`.
3. Autogenerate migration:
```bash
alembic revision --autogenerate -m "init"
```
4. Apply migration:
```bash
alembic upgrade head
```

---

## 11. Async Support
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/mydb"

async_engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def get_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute("SELECT * FROM users")
        return result.fetchall()
```

---

## 12. Best Practices
- Use **Alembic** for migrations.
- Use **scoped sessions** or dependency injection in web apps.
- Optimize queries using **eager loading**.
- Monitor queries in production with logging.
- Combine **Core + ORM** for performance-critical queries.
- For microservices or async workloads, prefer **async engine**.

---

## 13. Conclusion
SQLAlchemy is the **most powerful and flexible ORM in Python**, offering both high-level ORM features and low-level SQL control. It is production-ready, works with multiple frameworks, and supports both sync and async use cases. By combining ORM with Core expressions, developers can achieve **both developer productivity and performance optimization**.

