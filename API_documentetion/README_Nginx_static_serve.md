NGINX serves static files **directly from the file system** without involving your backend app (like Django). This makes it **much faster and more efficient** for serving assets like:

- CSS
- JavaScript
- Images
- Fonts
- PDFs, etc.

**✅ Why use NGINX for static files?**

- NGINX is **written in C** and optimized for high-performance.
- It can serve static files **10–100x faster** than Django or any WSGI app.
- It reduces **load** on your Django application server (Gunicorn/uvicorn/etc).

**🔧 Example NGINX config to serve static files**

Assume your static files are collected into /app/static/ using python manage.py collectstatic.

nginx
```
server {

listen 80;

server_name yourdomain.com;

    location /static/ {

        alias /app/static/; # Path where static files are stored

        autoindex off;

    }

    location /media/ {

        alias /app/media/; # Path for user-uploaded media files

        autoindex off;

    }

    location / {

        proxy_pass <http://127.0.0.1:8000>; # Django backend

        include proxy_params;

        proxy_redirect off;

    }

}
```

🔹 alias tells NGINX: “Serve files from this directory when the URL starts with /static/”

**🐍 Django + NGINX Deployment Flow**

1. Run python manage.py collectstatic — puts all static files in /app/static/
2. NGINX is configured to serve /static/ URLs from that directory.
3. Requests like <http://yourdomain.com/static/css/style.css> never reach Django — NGINX handles it directly.

**🚀 Summary**

| **Feature** | **Django** | **NGINX** |
| --- | --- | --- |
| Handles static files? | ✅ but not efficient | ✅ highly efficient |
| Preferred in prod? | ❌ (not recommended) | ✅ yes |
| Requires collectstatic? | ✅ yes | ✅ yes |