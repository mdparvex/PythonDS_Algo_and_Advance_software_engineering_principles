# 🧭 Service Discovery - Complete Technical Documentation

## 📘 Overview

In a **distributed system** or **microservices architecture**, services are often deployed dynamically across multiple hosts, containers, or cloud regions. Since services scale up and down dynamically, their **network locations (IP and ports)** change frequently.

**Service Discovery** solves the problem of **how services find and communicate with each other** without hardcoding network locations.

## ⚙️ What Is Service Discovery?

**Service Discovery** is the process through which a service (client) automatically determines the network location (IP address and port) of another service it needs to communicate with.

It ensures that services can connect with each other **dynamically and reliably**, even as instances are **added, removed, or replaced**.

## 🧩 Why Service Discovery Matters

| **Problem** | **Without Service Discovery** | **With Service Discovery** |
| --- | --- | --- |
| Dynamic scaling | Hard to track new instance IPs | Automatically updates registry |
| Service failure | Clients keep sending requests to dead instances | Registry detects failures and removes unhealthy nodes |
| Load balancing | Manual configuration | Built-in client/server-side load balancing |
| Deployments | Hard-coded IPs require redeploys | Automatic registration/deregistration |

## 🔍 Core Concepts

### 1\. ****Service Registry****

A **central database** that maintains the mapping of **service names → network locations**.

Example entry:
```bash
auth-service → 10.0.1.12:8080
payment-service → 10.0.2.25:9090
```

The registry may be **self-hosted** (like Consul, Eureka, or etcd) or **cloud-managed** (like AWS Cloud Map).

### 2\. ****Service Registration****

When a service instance starts, it **registers** itself with the registry, providing:

- Its **name**
- Its **IP address**
- Its **port**
- (Optionally) health check URL

Example (Eureka registration JSON):

```json
{
  "instance": {
    "app": "PAYMENT-SERVICE",
    "hostName": "payment-01",
    "ipAddr": "10.0.2.25",
    "port": {"$": 9090, "@enabled": true},
    "status": "UP"
  }
}
```

### 3\. ****Service Lookup / Discovery****

When another service (client) wants to call PAYMENT-SERVICE, it queries the registry:

Example response:

```json
{
  "instances": [
    {"host": "10.0.2.25", "port": 9090},
    {"host": "10.0.2.26", "port": 9090}
  ]
}
```

The client then chooses one instance (load balancing).

### 4\. ****Health Checks****

To ensure accuracy, service registries periodically **ping** registered services using HTTP, gRPC, or TCP health endpoints to remove unhealthy nodes.

Example:

```bash
GET /health
Response: { "status": "UP" }
```

## 🧠 Types of Service Discovery

### 🔸 1. Client-Side Discovery

The **client** queries the service registry to find available service instances and then sends requests directly.

**Examples:** Netflix Eureka, Consul with client libraries.

**Architecture:**
```arduino
Client → Service Registry → Target Service
```
**Pros:**

- Load balancing logic at client side
- No extra network hop

**Cons:**

- Every client must implement discovery logic
- Tight coupling between client and registry

### 🔸 2. Server-Side Discovery

The client sends requests via a **load balancer**, which queries the registry and routes the request to an available instance.

**Examples:** AWS Elastic Load Balancer (ELB), Nginx + Consul Template, Kubernetes Services.

**Architecture:**
```arduino
Client → Load Balancer → Service Registry → Target Service
```
**Pros:**

- Client is simple
- Centralized control and policies

**Cons:**

- Extra network hop
- Load balancer becomes a single point of failure (if not highly available)

## 🧰 Popular Service Discovery Tools

| **Tool** | **Type** | **Description** |
| --- | --- | --- |
| **Consul** | Client & Server | HashiCorp's distributed, multi-datacenter registry with key-value storage |
| **Eureka** | Client-Side | Netflix OSS tool used by Spring Cloud for service registration and discovery |
| **etcd** | Server-Side | Strongly consistent key-value store used in Kubernetes |
| **Zookeeper** | Server-Side | Apache's coordination service, widely used in Hadoop and Kafka |
| **Kubernetes DNS** | Server-Side | Uses internal DNS to automatically discover pods and services |
| **AWS Cloud Map** | Server-Side | Managed service registry for AWS environments |

## 🌐 Real-World Example: Netflix Microservice Ecosystem

Netflix pioneered large-scale **microservices** (over 700 services).  
To connect these, they built **Netflix Eureka**, a **service registry** and **discovery system**.

- When a microservice (e.g., movie-service) starts, it **registers** itself in Eureka.
- Other services (e.g., user-service) **query Eureka** to find the movie-service IP/port.
- Netflix Ribbon provides **client-side load balancing**.
- Netflix Zuul (API Gateway) provides **server-side routing**.

**Flow:**
```arduino
User Service → Eureka → Movie Service
```
This enabled **dynamic scaling**, **fault tolerance**, and **zero downtime deployment**.

## 🧮 Real-World Scenario & Solution

### 🎯 Scenario

You have an **e-commerce platform** built using microservices:

- **User Service**
- **Order Service**
- **Payment Service**
- **Inventory Service**

All services run inside **Docker containers** and scale automatically based on load.

Problem:  
When containers restart or scale up, their **IP addresses change**, and services can't find each other.

### 🧩 Step-by-Step Solution Using Service Discovery (Consul Example)

#### 1\. Deploy Consul

Run a Consul server to maintain the registry:
```bash
docker run -d --name=consul -p 8500:8500 consul
```
#### 2\. Register Services Automatically

Each service runs with a Consul agent and registers itself:

Example Consul service definition (payment.json):

```json
{
  "service": {
    "name": "payment-service",
    "port": 8082,
    "check": {
      "http": "http://localhost:8082/health",
      "interval": "10s"
    }
  }
}
```

Register with:
```bash
consul services register payment.json
```
#### 3\. Discover from Client (Python Example)

```python
import requests

def get_service_address(service_name):
    url = f"http://localhost:8500/v1/catalog/service/{service_name}"
    response = requests.get(url).json()
    if response:
        service = response[0]
        return f"{service['ServiceAddress']}:{service['ServicePort']}"
    return None

payment_address = get_service_address("payment-service")
print("Payment service running at:", payment_address)
```

#### 4\. Send Request to Payment Service

```python
import requests

payment_url = f"http://{payment_address}/process"
response = requests.post(payment_url, json={"order_id": 123})
print(response.json())
```

✅ Result:

- The **Order Service** automatically finds the **Payment Service**.
- If a payment instance fails, Consul removes it from the registry.
- Scaling happens seamlessly without configuration changes.

## 🧩 Integration with Kubernetes

In Kubernetes, service discovery is built-in.

When you create a Service object:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: payment-service
spec:
  selector:
    app: payment
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
```

Kubernetes automatically creates a **DNS entry**:

```bash
http://payment-service.default.svc.cluster.local
```

Any pod can access the service using this DNS name - no registry setup needed.

## 🚀 Best Practices

- **Use Health Checks:** Keep registry entries up-to-date with live status.
- **Enable Heartbeats:** Allow services to renew their presence periodically.
- **Secure Communication:** Protect registry APIs with ACLs or mutual TLS.
- **Cache Locally:** Use short-lived caches to reduce registry lookups.
- **Graceful Deregistration:** Deregister services cleanly during shutdown.
- **Monitor & Visualize:** Use dashboards (like Consul UI or Eureka dashboard).

## 🧾 Summary

| **Aspect** | **Description** |
| --- | --- |
| **Goal** | Enable dynamic service-to-service communication |
| **Core Components** | Registry, Registration, Lookup, Health Checks |
| **Types** | Client-side and Server-side |
| **Common Tools** | Consul, Eureka, etcd, Kubernetes DNS |
| **Benefit** | Resilience, scalability, fault tolerance, automation |

## 💡 Final Thought

Service Discovery is the **heart of distributed systems**. Without it, microservices would collapse under configuration complexity and network uncertainty.

In modern ecosystems - whether **Docker Swarm**, **Kubernetes**, or **cloud-native** - **Service Discovery enables automatic scaling, resilience, and simplicity**, making your infrastructure truly **self-aware and adaptive**.

---
**📘 What is Service Discovery?**

**Service Discovery** is the process by which microservices (or distributed systems) automatically detect and communicate with each other without needing manual configuration of IP addresses or ports.

In microservice architecture, services are **dynamic** — they can scale up/down, restart, or move to different nodes. Manual IP/port management becomes impossible. **Service discovery solves this by providing an automatic way for services to find each other.**

**🔍 Types of Service Discovery**

| **Type** | **Description** |
| --- | --- |
| **Client-Side** | The client queries a service registry and picks an instance. |
| **Server-Side** | The client sends a request to a load balancer, which routes to the service. |
| **DNS-Based** | Services are discoverable via DNS names. Kubernetes uses this. |

**🚀 How It Works in Kubernetes (your case)**

Kubernetes uses **built-in DNS-based service discovery**.

**🧱 Your Setup:**

You mentioned:

- live_reading running in Kubernetes
- student_api running in Kubernetes
- payment running on **EC2**

Let’s explore each case.

**✅ In-Kubernetes Services (DNS-Based)**

When you create a Kubernetes **Service** for your deployment, K8s automatically gives it a **DNS name** like:

```bash
http://&lt;service-name&gt;.&lt;namespace&gt;.svc.cluster.local
```
For example:

```bash
live-reading-service.default.svc.cluster.local
```
This means from **inside any other pod**, you can call:

```bash
<http://live-reading-service:8000>
```
So:

- student_api can call live_reading
- live_reading can call student_api

**without needing IPs**.

✅ This is **automatic service discovery via DNS** in Kubernetes.

**❌ External Services (EC2-Based)**

Your payment service runs on EC2, so it's **outside the cluster**. Kubernetes can’t auto-discover this.

**Solution**: You must do **manual service discovery** or use a tool like:

- Register it with **Consul**, **Eureka**, or **etcd**
- Use **environment variables** or **config maps** in Kubernetes to store the external payment service URL
- You may expose EC2 with a **Load Balancer**, then access via fixed domain/IP

**🔄 Example Flow**

Let's say:

- live_reading (on K8s) wants to call student_api (also K8s)
- student_api wants to call payment (on EC2)

**Code in live_reading:**

```python

import requests

# Service discovery in K8s

STUDENT_API_URL = "<http://student-api-service:8000/student/info>"

res = requests.get(STUDENT_API_URL)
```
**Code in student_api:**

```python

# Service discovery to EC2 via environment/config

PAYMENT_URL = os.environ.get("PAYMENT_URL", "<https://api.payment.com>")

res = requests.post(PAYMENT_URL, data=payment_data)
```

**🧠 Summary**

| **Concept** | **Kubernetes Services** | **External Services (e.g., EC2)** |
| --- | --- | --- |
| DNS Discovery | ✅ Built-in | ❌ Not available |
| Service Registry | 🔄 Internal Kube DNS | ❌ Manual or use Consul |
| Needs IP config? | ❌ No | ✅ Yes (via config/env) |

**🛠 Tools for Service Discovery (if scaling)**

| **Tool** | **Used For** |
| --- | --- |
| **Kube-DNS / CoreDNS** | Kubernetes internal services |
| **Consul** | Microservices across clusters |
| **Eureka** | Java/Spring Boot-based systems |
| **etcd** | Core to Kubernetes’ own internal discovery |