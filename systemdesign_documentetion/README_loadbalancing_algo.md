Here is a **technical and well-structured documentation** on **Load Balancing Techniques in NGINX**, covering Round-Robin, Weighted Load Balancing, and Least Connections with configuration examples.

# 🧭 Load Balancing Techniques in NGINX

## 📘 Overview

Load balancing is the process of distributing incoming network traffic across multiple servers to ensure reliability, availability, and scalability. **NGINX** supports several load balancing methods, allowing users to route requests efficiently among backend servers.

## 🚀 Supported Load Balancing Techniques in NGINX

NGINX provides the following load balancing algorithms:

1. **Round-Robin** (Default)
2. **Weighted Load Balancing**
3. **Least Connections**

Each method can be implemented using the upstream module in the NGINX configuration.

## 🔁 1. Round-Robin (Default)

### ➤ Description

The default method in NGINX. Requests are distributed sequentially across the list of servers — the first request goes to the first server, the second to the next, and so on.

### ➤ Use Case

- Simple, even distribution
- When all backend servers are of equal capacity

### ➤ Configuration

```nginx
http {
    upstream backend {
        server backend1.example.com;
        server backend2.example.com;
        server backend3.example.com;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://backend;
        }
    }
}

```

🔸 No directive is needed — **Round-Robin is the default behavior** in the upstream block.

## ⚖️ 2. Weighted Load Balancing

### ➤ Description

Each server is assigned a weight (default = 1). Servers with higher weights receive a larger share of the traffic.

### ➤ Use Case

- When some backend servers have more processing power or bandwidth
- Need to control traffic distribution ratio

### ➤ Configuration

```nginx
http {
    upstream backend {
        server backend1.example.com weight=5;
        server backend2.example.com weight=2;
        server backend3.example.com weight=1;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://backend;
        }
    }
}

```

🧠 A server with weight 5 receives 5x more requests than one with weight 1.

## 📉 3. Least Connections

### ➤ Description

Requests are sent to the server with the least number of active connections at the moment.

### ➤ Use Case

- Ideal when backend requests vary in processing time
- Minimizes queuing and delays

### ➤ Configuration

```nginx
http {
    upstream backend {
        least_conn;
        server backend1.example.com;
        server backend2.example.com;
        server backend3.example.com;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://backend;
        }
    }
}


```

🟢 Useful in real-time applications like chat, live streaming, or APIs.

## 🔐 Optional Enhancements

### ➤ Health Checks

To make load balancing more resilient, configure health checks using max_fails and fail_timeout:

```nginx
upstream backend {
    server backend1.example.com max_fails=3 fail_timeout=30s;
    server backend2.example.com max_fails=3 fail_timeout=30s;
}

```

### ➤ Sticky Sessions (IP Hash)

If session persistence is needed, use IP Hash (Note: this is a different method and not compatible with least_conn):

```nginx
upstream backend {
    ip_hash;
    server backend1.example.com;
    server backend2.example.com;
}

```

## 📦 Full Example

```nginx
http {
    upstream backend {
        least_conn;
        server backend1.example.com weight=2 max_fails=3 fail_timeout=30s;
        server backend2.example.com weight=1 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://backend;
        }
    }
}

```

## 📎 Notes

- All backend servers must be reachable from NGINX.
- DNS names like backend1.example.com must resolve correctly.
- Ensure backend applications are listening on the right port (e.g., 80, 8080).

## ✅ When to Use Which Strategy?

| **Strategy** | **Best For** |
| --- | --- |
| Round-Robin | Equal-capacity servers |
| Weighted | Unequal server capacities |
| Least Connections | Requests with unpredictable processing time |

## 📚 References

- NGINX Documentation - Upstream Module
- NGINX Plus Load Balancing (Advanced)