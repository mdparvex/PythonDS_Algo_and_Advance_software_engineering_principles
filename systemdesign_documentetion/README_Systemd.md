# ⚙️ **Systemd - Complete Technical Documentation**

## 🧠 ****1\. What is Systemd?****

systemd is a **system and service manager** for Linux.  
It's the **init system** that boots up your OS, starts processes, and manages their lifecycle - including starting, stopping, restarting, and logging.

It replaces older systems like init.d and provides a modern, parallelized way to manage services efficiently.

In simple terms:

systemd controls how and when your applications and daemons start, stop, and restart on Linux.

## 🧩 ****2\. Why Do We Need Systemd?****

Imagine you deploy a Django application using Gunicorn and Celery. You can start them manually, but:

- They don't start automatically when the server reboots.
- If they crash, they won't restart.
- You can't easily track logs or resource usage.

### ❌ Problem

You want your web server and background worker to:

- Start automatically when the system boots.
- Restart automatically if they fail.
- Log everything cleanly.
- Be easily managed with standard Linux commands.

### ✅ Solution

Use **systemd service units** to manage and monitor your application processes.

## 🔍 ****3\. How Systemd Works****

Systemd manages services through **unit files**, usually located in:

```swift
/etc/systemd/system/
```

Each `.service` file defines:

- The command to start the process.
- The working directory.
- User permissions.
- Auto-restart rules.
- Logging and dependencies.

Systemd then allows you to control these services using the systemctl command.

## 🧰 ****4\. Common Use Cases****

| **Use Case** | **Example** |
| --- | --- |
| **Web server management** | Run and monitor Django or FastAPI via Gunicorn/Uvicorn |
| **Background jobs** | Manage Celery workers or schedulers |
| **Database management** | Start PostgreSQL, Redis, etc. on boot |
| **Custom scripts** | Run periodic data collectors or ML pipelines |
| **Production reliability** | Ensure critical services auto-restart after crash or reboot |

## 🧪 ****5\. Real-World Example****

### 🎯 Scenario

You're deploying a **Django application** using **Gunicorn** on Ubuntu 22.04.  
You want:

- The Django app to start automatically at boot.
- Gunicorn to auto-restart if it crashes.
- Logs stored in journalctl for monitoring.

### 🧱 ****Directory Setup****

```swift
/home/ubuntu/myproject/
│
├── manage.py
├── myproject/
│   ├── __init__.py
│   └── settings.py
├── venv/
└── gunicorn.conf.py
```

## 🛠️ ****6\. Create a systemd Service File****

Create a new file at:
```bash
sudo nano /etc/systemd/system/myproject.service
```

### 🧩 ****Service File Example****

```ini
[Unit]
Description=Gunicorn daemon for Django project
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/myproject
ExecStart=/home/ubuntu/myproject/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/ubuntu/myproject/myproject.sock myproject.wsgi:application

Restart=always
RestartSec=5
Environment="DJANGO_SETTINGS_MODULE=myproject.settings" "PYTHONPATH=/home/ubuntu/myproject"

[Install]
WantedBy=multi-user.target
```

### 🧩 Explanation of Each Section

| **Section** | **Purpose** |
| --- | --- |
| **\[Unit\]** | Describes the service and its dependencies. After=network.target ensures it starts after the network is up. |
| **\[Service\]** | Core configuration - defines how the process runs. |
| `User / Group` | Runs under a specific Linux user/group. |
| `WorkingDirectory` | Directory where your project is located. |
| `ExecStart` | The command to run Gunicorn (or any process). |
| `Restart=always` | Ensures it restarts if it fails. |
| `RestartSec=5` | Wait 5 seconds before restart. |
| `Environment` | Environment variables for Django. |
| **\[Install\]** | Specifies when the service should be started. |

## ⚙️ ****7\. Enable and Start the Service****

Run the following commands:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start at boot
sudo systemctl enable myproject

# Start the service immediately
sudo systemctl start myproject

# Check status
sudo systemctl status myproject
```

## 🔍 ****8\. View Logs****

Systemd automatically manages logs using journalctl.

```bash
# View real-time logs
sudo journalctl -u myproject -f

# View complete logs
sudo journalctl -u myproject
```

Logs persist across reboots and can be filtered by time or priority.

## 🧱 ****9\. Managing Your Service****

| **Command** | **Description** |
| --- | --- |
| `sudo systemctl start myproject` | Start the service |
| `sudo systemctl stop myproject` | Stop the service |
| `sudo systemctl restart myproject` | Restart the service |
| `sudo systemctl status myproject` | Check service status |
| `sudo systemctl disable myproject` | Disable auto-start at boot |
| `sudo systemctl enable myproject` | Enable auto-start at boot |

## 🧩 ****10\. Handling Dependencies****

You can define dependencies between services.  
For example, if your Django app depends on Redis:

```bash
[Unit]
Description=Django Gunicorn Service
After=network.target redis.service
Requires=redis.service
```

This ensures Redis starts before Django.

## 🐳 ****11\. Using systemd Inside Docker (Not Recommended, but Possible)****

Systemd is typically used **outside** Docker (host-level).  
Inside Docker, you should rely on process managers like **supervisord** or **s6-overlay**.

If you must use systemd in Docker, it requires privileged mode - which isn't ideal for security.

## 🧠 ****12\. Understanding How Systemd Works Internally****

Systemd works as PID 1 (the first process the kernel starts).  
It:

- Spawns other processes defined by .service files.
- Tracks their status.
- Logs their stdout/stderr via journald.
- Restarts them based on failure conditions.
- Provides dependency-based parallel startup to improve boot time.

Each service runs in a **cgroup**, isolating resource usage.

## 📚 ****13\. Advanced Features****

### ✅ Auto-Restart Policies

You can control restart behavior precisely:

```ini
Restart=on-failure
RestartSec=10
```

### ✅ Resource Limits

You can control memory/CPU usage:

```ini
MemoryLimit=500M
CPUQuota=50%
```

### ✅ Environment Files

Store environment variables separately:

```ini
EnvironmentFile=/etc/myproject.env
```

Example .env:

```ini
DJANGO_SETTINGS_MODULE=myproject.settings
SECRET_KEY=abcdef123
```

### ✅ Socket Activation

Systemd can create sockets and only start your app when requests arrive.

## 📦 ****14\. Real-World Example: Managing Multiple Services****

If you have:

- `gunicorn.service`
- `celery.service`
- `celerybeat.service`

You can manage all with:

```bash
sudo systemctl start gunicorn celery celerybeat
sudo systemctl enable gunicorn celery celerybeat
```

And check all statuses:

```bash
sudo systemctl list-units --type=service | grep myproject
```

## 🧭 ****15\. Comparison: systemd vs Supervisord****

| **Feature** | **Systemd** | **Supervisord** |
| --- | --- | --- |
| Runs on | Host system (root) | Inside container or user space |
| Boot integration | ✅ Yes | ❌ No |
| Logging | journalctl | Custom log files |
| Restart policy | Built-in | Built-in |
| Resource limits | ✅ Yes (via cgroups) | ❌ No native support |
| Docker usage | ❌ Not ideal | ✅ Common |
| Ideal for | Server-wide service management | App-level multi-process control |

## 🧱 ****16\. Troubleshooting****

| **Problem** | **Solution** |
| --- | --- |
| "Failed to start service" | Run sudo journalctl -xe for detailed logs. |
| Changes not applied | Run sudo systemctl daemon-reload. |
| Wrong path | Check ExecStart and file permissions. |
| Service not starting at boot | Ensure WantedBy=multi-user.target and systemctl enable. |

## 🧩 ****17\. Best Practices****

✅ Use absolute paths for commands.  
✅ Keep .service files under /etc/systemd/system/.  
✅ Always reload with daemon-reload after editing.  
✅ Use separate .env for secrets.  
✅ Monitor services with journalctl regularly.  
✅ Avoid running apps as root - use least privilege users.

## 🏁 ****18\. Summary****

| **Concept** | **Description** |
| --- | --- |
| **Purpose** | Manage, monitor, and control Linux services. |
| **Configuration** | Defined through .service unit files. |
| **Key Commands** | systemctl start, stop, status, enable. |
| **Core Features** | Auto-start, auto-restart, dependency control, logging. |
| **Best Fit** | Host-level production service management. |

## ✅ ****19\. Final Takeaway****

**Systemd is the backbone of modern Linux process management.**  
It ensures your critical applications like Gunicorn, Celery, and Redis are automatically started, monitored, and restarted - even after failures or system reboots.

If you want your services to run **forever**, start **automatically on boot**, and log cleanly -  
→ **Systemd is the right tool.**