# 🧩 Django Signals - The Complete Guide for Cleaner Architecture

### ****Overview****

Django **signals** are a powerful feature that allows **decoupled components** of your application to **communicate through events**. They are particularly useful for triggering side effects (such as sending emails, updating logs, or cleaning data) without cluttering your main business logic.

## ⚙️ ****Table of Contents****

- [Introduction to Django Signals](#introduction-to-django-signals)
- [How Django Signals Work](#how-django-signals-work)
- [Types of Django Signals](#types-of-django-signals)
  - [Model Signals (django.db.models.signals)](#model-signals-djangodbmodelssignals)
  - [Request/Response Signals (django.core.signals)](#requestresponse-signals-djangocoresigna)
  - [Management & Migration Signals (django.db.models.signals)](#management--migration-signals-djangodbm)
  - [Test Signals (django.test.signals)](#test-signals-djangotestsignals)
  - [Custom Application Signals](#custom-application-signals)
- [Best Practices for Using Signals](#best-practices-for-using-signals)
- [Example: Event-Driven Clean Architecture](#example-event-driven-clean-architecture)
- [Conclusion](#conclusion)

## 🧠 ****Introduction to Django Signals****

Django signals allow **different parts of a Django app to react to events** automatically. Instead of hardcoding logic inside views or models, you can **register event listeners** (called receivers) that respond when something happens - for example, when a user is created or deleted.

This approach leads to:

- Cleaner, modular code.
- Better separation of concerns.
- An event-driven design pattern.

## ⚡ ****How Django Signals Work****

### Core Components

| **Term** | **Description** |
| --- | --- |
| **Signal** | The event being broadcast. |
| **Sender** | The object that sends the signal. |
| **Receiver** | A function that listens for and reacts to the signal. |
| **Dispatcher** | Manages connections between signals and receivers. |

### Basic Example
```Python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    if created:
        print(f"New user registered: {instance.username}")

```

## 📦 ****Types of Django Signals****

Django provides multiple categories of signals based on their purpose and origin.

## 🧩 ****Model Signals**** (django.db.models.signals)

These signals are triggered when actions occur on Django models.

| **Signal** | **Trigger** | **Typical Use Case** |
| --- | --- | --- |
| **pre_init** | Before model instance initialization. | Modify or validate data before instance creation. |
| **post_init** | After model instance initialization. | Automatically compute additional fields. |
| **pre_save** | Before saving an instance. | Format fields, generate slugs, run validations. |
| **post_save** | After saving an instance. | Send emails, create related objects, update logs. |
| **pre_delete** | Before deleting an instance. | Validate or prevent deletion. |
| **post_delete** | After deleting an instance. | Clean up related files or logs. |
| **m2m_changed** | When a ManyToManyField changes. | Sync related data, analytics updates. |
| **class_prepared** | After model class is fully prepared. | Modify or inspect model classes dynamically. |

### 1️⃣ pre_init

Triggered before a model instance is initialized.

```python
from django.db.models.signals import pre_init
from django.dispatch import receiver
from .models import Book

@receiver(pre_init, sender=Book)
def log_pre_init(sender, *args, **kwargs):
    print("Book instance initialization started.")
```

### 2️⃣ post_init

Triggered after a model instance is initialized.

```python
from django.db.models.signals import post_init
from django.dispatch import receiver

@receiver(post_init, sender=Book)
def log_post_init(sender, instance, **kwargs):
    print(f"Book '{instance.title}' initialized.")
```

### 3️⃣ pre_save

Triggered before a model's save() method executes.

```python
@receiver(pre_save, sender=Book)
def set_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = instance.title.lower().replace(" ", "-")
```

### 4️⃣ post_save

Triggered after saving an instance.

```python
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
```

### 5️⃣ pre_delete

Triggered before a model instance is deleted.

```python
@receiver(pre_delete, sender=Book)
def protect_featured_books(sender, instance, **kwargs):
    if instance.is_featured:
        raise Exception("Featured books cannot be deleted.")
```

### 6️⃣ post_delete

Triggered after a model instance is deleted.

```python
@receiver(post_delete, sender=Book)
def cleanup_book_image(sender, instance, **kwargs):
    if instance.cover_image:
        instance.cover_image.delete(save=False)
```

### 7️⃣ m2m_changed

Triggered when a many-to-many relation is modified.

```python
@receiver(m2m_changed, sender=Book.categories.through)
def category_updated(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove']:
        instance.update_recommendations()
```

### 8️⃣ class_prepared

Triggered when a model class is fully loaded into memory.

```python
from django.db.models.signals import class_prepared

def model_ready(sender, **kwargs):
    print(f"Model ready: {sender.__name__}")

class_prepared.connect(model_ready)
```

## 🌐 ****Request/Response Signals**** (django.core.signals)

These signals monitor HTTP request lifecycle events.

| **Signal** | **Trigger** | **Typical Use Case** |
| --- | --- | --- |
| **request_started** | When a request starts. | Initialize timers, context tracking. |
| **request_finished** | When a request finishes. | Log performance metrics, cleanup resources. |
| **got_request_exception** | When an exception occurs. | Log errors, send alerts. |

### Example

```python
from django.core.signals import request_started, request_finished, got_request_exception
from django.dispatch import receiver
import time

@receiver(request_started)
def on_request_start(sender, **kwargs):
    sender.start_time = time.time()

@receiver(request_finished)
def on_request_finish(sender, **kwargs):
    duration = time.time() - getattr(sender, 'start_time', time.time())
    print(f"Request finished in {duration:.2f}s")

@receiver(got_request_exception)
def on_exception(sender, request, **kwargs):
    print(f"Exception occurred during {request.path}")
```

## 🧰 ****Management & Migration Signals**** (django.db.models.signals)

| **Signal** | **Trigger** | **Typical Use Case** |
| --- | --- | --- |
| **pre_migrate** | Before migrations run. | Prepare database, cleanup, or backups. |
| **post_migrate** | After migrations complete. | Seed initial data, create permissions. |

### Example

```python
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.name == 'users':
        Group.objects.get_or_create(name="Students")
        Group.objects.get_or_create(name="Teachers")
```

## 🧪 ****Test Signals**** (django.test.signals)

| **Signal** | **Trigger** | **Typical Use Case** |
| --- | --- | --- |
| **setting_changed** | When django.conf.settings change during tests. | Refresh cache or test context. |
| **template_rendered** | When a template is rendered during tests. | Assert specific templates or context values. |

### Example

```python
from django.test.signals import template_rendered
from django.dispatch import receiver

@receiver(template_rendered)
def log_template(sender, template, context, **kwargs):
    print(f"Rendered template: {template.name}")
```

## 🚀 ****Custom Application Signals****

Define and use your own domain-specific signals for clean, event-driven design.

```python
# signals.py
from django.dispatch import Signal
book_read = Signal()

# views.py
from .signals import book_read
book_read.send(sender=None, user=request.user, book=book_instance)

# receivers.py
from django.dispatch import receiver
from .signals import book_read

@receiver(book_read)
def handle_book_read(sender, user, book, **kwargs):
    user.profile.increment_books_read()
```

## 🧾 ****Best Practices for Using Signals****

| **Practice** | **Description** |
| --- | --- |
| ✅ **Use for Side Effects Only** | Keep business logic in services or models, not signals. |
| 📁 **Organize in signals.py** | Define all receivers in a dedicated file for maintainability. |
| ⚙️ **Connect in apps.py** | Import signals in AppConfig.ready() to ensure registration. |
| 🧠 **Use dispatch_uid** | Prevent duplicate registration during Django reloads. |
| 🧩 **Document Signal Flows** | Maintain a clear diagram or table of triggers and effects. |
| ⚠️ **Avoid Circular Imports** | Import models locally within receiver functions if needed. |
| 🧍 **Test Signals Separately** | Write unit tests for each receiver function. |

## 🏗 ****Example: Event-Driven Clean Architecture****

### Without Signals (Coupled)

```python
def register_user(request):
    user = User.objects.create(...)
    Profile.objects.create(user=user)
    send_welcome_email(user)
```

### With Signals (Decoupled)

```python
def register_user(request):
    User.objects.create(...)
```

Now:

- Profile creation is handled by a post_save signal.
- Welcome email sending is triggered automatically.
- The view remains **thin and maintainable**.

## 🧩 ****Conclusion****

Django Signals make your system **modular, reactive, and clean** when used correctly.  
They are best for **automation and side effects**, such as:

- Creating related data
- Sending notifications
- Logging and auditing
- Caching and cleanup

Avoid overusing them for business logic or complex workflows - signals are ideal for **event-driven system design**.