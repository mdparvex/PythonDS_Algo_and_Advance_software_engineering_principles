# 🧠 **Supervisord - Complete Technical Documentation**

## 📘 ****1\. What is Supervisord?****

**Supervisord** is a **process control system** for UNIX-like operating systems.  
It allows you to **monitor, control, and automatically restart** background processes (like Django, Celery, Nginx, or Gunicorn) without relying on systemd or manual restarts.

Supervisord acts as a **guardian** for your applications - ensuring that critical processes are always running.

## 🧩 ****2\. Why Do We Need Supervisord?****

Imagine you deploy a Django app using **Gunicorn** and **Celery** workers.  
Everything runs perfectly - until one day, a Celery worker crashes.  
Your site is still live, but background tasks silently stop executing.

### ❌ Problem

- Your **Gunicorn server** and **Celery worker** are started manually (or via shell scripts).
- If either process **crashes** or **server restarts**, they **won't automatically restart**.
- Logs are scattered, and you can't easily monitor what's running.

### ✅ Solution

Use **Supervisord** to:

- Keep both Gunicorn and Celery running.
- Restart them automatically on failure.
- Provide an easy command-line & web interface to control processes.
- Redirect and manage logs in one place.

## ⚙️ ****3\. How Supervisord Works****

Supervisord uses two key components:

| **Component** | **Description** |
| --- | --- |
| **supervisord** | The main daemon process that starts and manages child processes. |
| **supervisorctl** | The command-line tool to interact with Supervisord - start, stop, restart, or check status of programs. |

It reads configuration from /etc/supervisord.conf or /etc/supervisor/conf.d/\*.conf.

Each program runs as a **child process** under Supervisord's control.

## 🧰 ****4\. Common Use Cases****

| **Use Case** | **Example** |
| --- | --- |
| **Web Server Monitoring** | Keep Gunicorn or Uvicorn alive for Django/FastAPI apps. |
| **Task Queue Workers** | Manage Celery or RQ workers. |
| **Log Management** | Redirect logs to files with rotation. |
| **Docker Entrypoint Management** | Run multiple processes in one container (e.g., Nginx + Django). |
| **Background Scripts** | Run custom data collection or scheduler scripts. |

## 🧪 ****5\. Real-World Example****

### 🎯 Scenario

You're deploying a **Django + Celery + Redis** app on Ubuntu or Docker.

You need:

- Gunicorn to serve Django.
- Celery Worker to process background jobs.
- Both must automatically restart if they crash or reboot.

### 🧩 ****Directory Structure****

```swift
/home/ubuntu/myproject/
│
├── manage.py
├── myproject/
│   └── settings.py
├── venv/
├── gunicorn.conf.py
└── supervisord/
    ├── gunicorn.conf
    └── celery.conf
```

## 🧱 ****6\. Supervisor Installation****

### 🧭 On Ubuntu

```bash
sudo apt update
sudo apt install supervisor -y
```

Verify installation:

```bash
supervisord -v
# Example: 4.2.5
```

## 🗂️ ****7\. Configuration Example****

### ****7.1 Gunicorn Configuration****

Create `/etc/supervisor/conf.d/gunicorn.conf` (or inside your project directory if running locally).

```ini
[program:gunicorn]
command=/home/ubuntu/myproject/venv/bin/gunicorn myproject.wsgi:application -c /home/ubuntu/myproject/gunicorn.conf.py
directory=/home/ubuntu/myproject
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/gunicorn.log
stderr_logfile=/var/log/supervisor/gunicorn_error.log
environment=DJANGO_SETTINGS_MODULE="myproject.settings",PYTHONPATH="/home/ubuntu/myproject"
```

### ****7.2 Celery Worker Configuration****

```ini
[program:celery]
command=/home/ubuntu/myproject/venv/bin/celery -A myproject worker --loglevel=info
directory=/home/ubuntu/myproject
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/celery.log
stderr_logfile=/var/log/supervisor/celery_error.log
```

## 🚀 ****8\. Start and Manage with Supervisor****

### Reload Supervisor to apply changes

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

### Start all configured programs

```bash
sudo supervisorctl start all
```

### Check status
```bash
sudo supervisorctl status
```
### Restart a specific service
```bash
sudo supervisorctl restart gunicorn
```
### Stop all services
```bash
sudo supervisorctl stop all
```
## 🔍 ****9\. Verifying Logs****

Check logs under:
```lua
/var/log/supervisor/gunicorn.log
/var/log/supervisor/celery.log
```

You can tail them live:

```bash
sudo tail -f /var/log/supervisor/gunicorn.log
```

## 🧠 ****10\. How Supervisor Handles Failures****

| **Event** | **What Supervisor Does** |
| --- | --- |
| Process crashes | Automatically restarts it (autorestart=true) |
| Server reboots | All programs marked autostart=true are restarted |
| Error logs | Stored in the log files defined in configuration |
| Manual intervention | Use supervisorctl to manage services manually |

## 🌐 ****11\. Using Supervisor Web Dashboard (Optional)****

You can enable a web-based control panel in `/etc/supervisord.conf`:

```ini
[inet_http_server]
port=*:9001
username=admin
password=strongpassword
```

Restart Supervisor:
```bash
sudo systemctl restart supervisor
```

Visit:  
👉 `http://your-server-ip:9001`
Login and manage your processes via browser!

## 🐳 ****12\. Using Supervisor Inside Docker****

When Docker runs multiple processes (like Django + Celery + Nginx), it's **not ideal** because containers should ideally have one process - but in small setups, Supervisor can help.

### Example Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt supervisor

COPY supervisord.conf /etc/supervisord.conf
COPY supervisor/ /etc/supervisor/conf.d/

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
```

This ensures all your processes (e.g., Gunicorn and Celery) start automatically when the container starts.

## 🧭 ****13\. Key Configuration Parameters Explained****

| **Parameter** | **Description** |
| --- | --- |
| command | The exact command used to run your process. |
| directory | Working directory before executing the command. |
| autostart | Start automatically when Supervisord launches. |
| autorestart | Restart automatically if the process exits unexpectedly. |
| redirect_stderr | Merge error output into standard output log. |
| stdout_logfile | Path to standard output log file. |
| environment | Set environment variables. |
| user | User under which the process runs. |

## 🧩 ****14\. Advantages of Supervisord****

✅ Easy configuration and control.  
✅ Keeps processes alive without complex shell scripting.  
✅ Provides log management per service.  
✅ Works across distributions and Docker.  
✅ Supports both CLI and Web UI.  
✅ Can manage multiple dependent services in production.

## ⚠️ ****15\. When**** Not ****to Use Supervisor****

| **Scenario** | **Better Alternative** |
| --- | --- |
| System-wide service management | systemd |
| Kubernetes or large container orchestration | Use Kubernetes Deployments or Docker Compose |
| Simple single-process Docker containers | Use CMD or entrypoint scripts |

## 🧩 ****16\. Troubleshooting****

| **Issue** | **Solution** |
| --- | --- |
| supervisorctl status shows "FATAL" | Check log file path permissions. |
| Process not restarting | Ensure autorestart=true. |
| Log not updating | Restart supervisor or clear log file. |
| Config changes not applied | Run reread and update after editing configs. |

## 🏁 ****17\. Summary****

| **Concept** | **Description** |
| --- | --- |
| **Purpose** | Keep multiple background processes alive and monitored. |
| **Key Tools** | supervisord, supervisorctl. |
| **Core Features** | Autostart, autorestart, logging, process monitoring. |
| **Real-World Use** | Manage Gunicorn, Celery, Redis, Nginx in production or Docker. |

## ✅ ****18\. Final Takeaway****

**Supervisord** acts as the process babysitter for your production environment.  
It ensures your critical services like Gunicorn, Celery, or any Python scripts run 24/7 without interruption, automatically recover from failures, and provide easy monitoring - whether on a physical server or inside Docker.