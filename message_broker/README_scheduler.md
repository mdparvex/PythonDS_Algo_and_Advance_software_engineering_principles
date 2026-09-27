# 📘 Scheduling in Django: Celery Beat vs APScheduler vs Crontab

## 1\. Introduction

Modern Django applications often require recurring tasks, such as clearing expired sessions, sending periodic emails, or running cleanup jobs. Python and Linux provide multiple tools to achieve this:

- Celery Beat → Django/Celery integrated task scheduler (distributed, queue-based).
- APScheduler → Pure Python in-app scheduler (lightweight, non-distributed).
- Crontab → Linux system-level scheduler (external to Django).

## 2\. Celery Beat

### 2.1 What is Celery Beat?

A scheduler that ships with Celery. Periodically sends tasks into the Celery broker (RabbitMQ/Redis). Tasks are consumed by Celery workers. Supports crontab-like schedules, intervals, and custom schedules. Fully distributed and production-ready.

### 2.2 Configuration in Django

Example configuration in settings.py:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'clear_sessions': {
        'task': 'django_celery_beat.tasks.clear_expired_sessions',
        'schedule': crontab(hour=0, minute=0),  # Runs daily at midnight
        'options': {'queue': 'maintenance_queue'}
    },
    'send_report': {
        'task': 'myapp.tasks.send_report',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
        'options': {'queue': 'report_queue'}
    },
}
```

### 2.3 Example Task

```python
# myapp/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_report():
    send_mail(
        "Daily Report",
        "Here is your scheduled report.",
        "noreply@example.com",
        ["admin@example.com"],
    )
```

### 2.4 Running Celery Beat

Start workers and beat:

```bash
# Start Celery workers
celery -A myproject worker -l info -Q report_queue,maintenance_queue

# Start Celery Beat scheduler
celery -A myproject beat -l info
```

### ✅ Best Use Cases

- Periodic jobs inside Django.
- Retryable tasks (e.g., failed payments).
- Scalable systems running on multiple servers.

## 3\. APScheduler

### 3.1 What is APScheduler?

A lightweight Python job scheduler. Runs inside the Django process. Supports interval, cron, and date-based triggers. Easy setup, no external broker required. Not distributed.

### 3.2 Installation

```bash
pip install apscheduler
```

### 3.3 Configuration in Django

```python
# myapp/apps.py
from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail

def send_reminder():
    send_mail(
        "Reminder",
        "This is your reminder email.",
        "noreply@example.com",
        ["user@example.com"],
    )

class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"

    def ready(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(send_reminder, "interval", minutes=30)
        scheduler.start()
```

### ✅ Best Use Cases

- Small Django projects.
- Quick in-app scheduling without Celery setup.
- Local/one-server deployments.

⚠️ Limitation: If the Django process restarts, jobs may be interrupted.

## 4\. Crontab

### 4.1 What is Crontab?

System-level scheduler available on Linux/Unix. Executes shell commands or scripts on a defined schedule. Independent of Django or Python.

### 4.2 Setup
Edit crontab:
```bash
crontab -e
```
Example job:  
```bash
# Run Django management command every night at 2 AM
0 2 * * * /path/to/venv/bin/python /path/to/manage.py clearsessions
```

### 4.3 Use Cases

- System maintenance (log cleanup, backups).
- Restarting services (Gunicorn, Celery workers).
- Running Django management commands periodically.

⚠️ Limitation: Not integrated with Django app logic unless you call manage.py.

## 5\. Comparison Table

| Feature | Celery Beat | APScheduler | Crontab |
| --- | --- | --- | --- |
| Runs inside Django? | ✅ Yes (via Celery) | ✅ Yes (pure Python) | ❌ No (system-level) |
| Distributed? | ✅ Yes (with workers) | ❌ No | ❌ No |
| Retry support | ✅ Yes | ❌ No | ❌ No |

## 6\. Decision Guide

Use Celery Beat if:

- Your project already uses Celery for background tasks.
- You need retries, monitoring, or distributed scheduling.

Use APScheduler if:

- You don’t need Celery.
- Your project is small, lightweight, or single-server.

Use Crontab if:

- You need system-level scheduling (outside Django).
- You’re running maintenance scripts (e.g., database backup).

## 7\. Example: Same Job in All Three

Job: Clear expired Django sessions daily at midnight.

Celery Beat:

```python
CELERY_BEAT_SCHEDULE = {
    'clear_sessions': {
        'task': 'django_celery_beat.tasks.clear_expired_sessions',
        'schedule': crontab(hour=0, minute=0),
    }
}
```

APScheduler:

```python
scheduler.add_job(
    lambda: call_command("clearsessions"),
    "cron",
    hour=0,
    minute=0,
)
```

Crontab:

```bash
0 0 * * * /path/to/venv/bin/python /path/to/manage.py clearsessions
```

## 8\. Conclusion

- Celery Beat → Best for production Django projects with queues.  
- APScheduler → Best for lightweight apps without Celery.  
- Crontab → Best for system-level automation outside Django.  
<br/>Together, these tools cover all scheduling needs for Django applications — from app-level jobs to OS-level scripts.



Here's a complete, structured documentation comparing **three popular task scheduling tools** in Django: **Crontab**, **Celery Beat**, and **APScheduler** — with **clear explanations and Django examples** for each.

# 📘 Scheduling in Django: crontab, celery-beat, APScheduler

## 📌 Table of Contents

1. [Introduction](#introduction)
2. [1. Crontab](#1-crontab)
    - What is Crontab?
    - How to Use Crontab with Django
3. [2. Celery Beat](#2-celery-beat)
    - What is Celery Beat?
    - How to Use Celery Beat in Django
4. [3. APScheduler](#3-apscheduler)
    - What is APScheduler?
    - How to Use APScheduler in Django
5. [Comparison Table](#comparison-table)
6. [Which Should You Use?](#which-should-you-use)
7. [Conclusion](#conclusion)

## 🔰 Introduction

Scheduling in web applications is critical for:

- Sending emails
- Running background jobs
- Cleanup tasks
- Generating reports
- Periodic database updates

In Django, the three most common scheduling tools are:

- **Crontab** (system-level scheduler)
- **Celery Beat** (Django + Celery + Redis/RabbitMQ)
- **APScheduler** (in-app Python scheduler)

## 1️⃣ Crontab

### ✅ What is Crontab?

Crontab is a Linux utility for running tasks on a fixed schedule. It’s **OS-level**, **lightweight**, and doesn’t require running Python scripts continuously.

### 🛠 How to Use Crontab with Django

#### Step 1: Create a Django management command

Create a custom command:

```bash

python manage.py startapp scheduler
```
Inside scheduler/management/commands/print_hello.py:

```python
# scheduler/management/commands/print_hello.py

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Prints Hello every minute'

    def handle(self, *args, **kwargs):
        print("Hello from Django at cron schedule!")

```

#### Step 2: Add Crontab Entry

Edit crontab:

```bash

crontab -e
```
Add:

```bash

\* \* \* \* \* /path/to/venv/bin/python /path/to/project/manage.py print_hello >> /path/to/logs/cron.log 2>&1
```

✅ Done. This will run the command every minute.

## 2️⃣ Celery Beat

### ✅ What is Celery Beat?

**Celery** is an asynchronous task queue for Python.  
**Celery Beat** is a scheduler that kicks off tasks at regular intervals using Celery workers.

🔄 Ideal for **distributed periodic tasks**.

### 🛠 How to Use Celery Beat in Django

#### Step 1: Install dependencies

```bash
pip install celery redis django-celery-beat
```
#### Step 2: Configure celery.py

Create project/celery.py:

```python
# project/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

```
Update \__init_\_.py:

```python

from .celery import app as celery_app
__all__ = ['celery_app']
```

#### Step 3: Setup Redis in settings.py

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```
#### Step 4: Create a task

```python
# app/tasks.py

from celery import shared_task

@shared_task
def print_hello():
    print("Hello from Celery Beat")

```

#### Step 5: Setup Django-Celery-Beat

Add to INSTALLED_APPS:

```python
'django_celery_beat',
```
Run migrations:

```bash
python manage.py migrate
```
Start beat:

```bash
celery -A project beat -l info
```
Start worker:

```bash
celery -A project worker -l info
```
#### Step 6: Create a periodic task

You can do this from the Django admin panel (PeriodicTask) or in code:

```python
from django_celery_beat.models import PeriodicTask, IntervalSchedule

schedule, _ = IntervalSchedule.objects.get_or_create(
    every=1,
    period=IntervalSchedule.MINUTES,
)

PeriodicTask.objects.create(
    interval=schedule,
    name='Print Hello Task',
    task='app.tasks.print_hello'
)

```

✅ Done. This runs print_hello every minute via Celery worker.

## 3️⃣ APScheduler

### ✅ What is APScheduler?

APScheduler (**Advanced Python Scheduler**) is a lightweight, in-process Python scheduler.

🔄 Great for **simple jobs**, without needing Redis or RabbitMQ.

### 🛠 How to Use APScheduler in Django

#### Step 1: Install APScheduler

```bash
pip install apscheduler
```
#### Step 2: Create a Scheduler File

```python
# scheduler/apscheduler_config.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

def print_hello():
    print("Hello from APScheduler")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(print_hello, CronTrigger(minute="*"))  # Every minute
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

```

#### Step 3: Hook into Django

You can run the scheduler on startup, e.g., in apps.py:

```python
# scheduler/apps.py

from django.apps import AppConfig

class SchedulerConfig(AppConfig):
    name = 'scheduler'

    def ready(self):
        from .apscheduler_config import start
        start()

```

✅ Done. When Django starts, APScheduler runs tasks in the background.

⚠️ Note: This works only as long as Django process is alive (e.g., development or Gunicorn with 1 worker).

## 📊 Comparison Table

| **Feature** | **Crontab** | **Celery Beat** | **APScheduler** |
| --- | --- | --- | --- |
| Type | OS-Level | Distributed Task Scheduler | In-App Python Scheduler |
| Dependencies | None | Redis/RabbitMQ, Celery | Only APScheduler |
| Best Use Case | Simple scripts | Scalable task queue | Lightweight periodic jobs |
| Persistent Scheduler | Yes | Yes | No (unless using persistent APScheduler stores) |
| Django Integration | Indirect | Strong | Medium |
| Admin Panel | No  | Yes (django-celery-beat) | No  |

## ❓ Which Should You Use?

| **Scenario** | **Use This** |
| --- | --- |
| You want to run lightweight periodic tasks | **APScheduler** |
| You need scalable and distributed task queues | **Celery Beat** |
| You’re on a VPS and want OS-level automation | **Crontab** |
| You want admin panel to manage schedules | **Celery Beat** |
| You want minimal setup without Redis/RabbitMQ | **Crontab or APScheduler** |

## ✅ Conclusion

| **Tool** | **Use for...** |
| --- | --- |
| **Crontab** | Simple commands, low dependencies, external scripts |
| **Celery Beat** | Complex Django tasks, distributed workers |
| **APScheduler** | Internal jobs in Django process, fewer dependencies |

You can even **combine them**:

- Use **Celery** for heavy/async tasks
- Use **APScheduler** for startup jobs
- Use **Crontab** for DB backups, OS-level jobs