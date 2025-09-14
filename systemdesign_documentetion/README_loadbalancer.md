**well-structured technical documentation** on Load Balancers (ALB, NLB, CLB, etc.), covering **types, internals, use cases, and real-world examples**.

# 📘 Technical Documentation: Load Balancers in Modern Architectures

## 1\. Introduction

A **Load Balancer (LB)** is a networking component that distributes incoming traffic across multiple backend servers or services to ensure **availability, scalability, and fault tolerance**.

Key benefits:

- Prevents any single server from being overloaded.
- Ensures high availability by routing around failed nodes.
- Improves performance through optimized routing.
- Supports horizontal scaling.

## 2\. Types of Load Balancers

Load balancers can operate at different layers of the OSI model.

### 🔹 2.1 Layer 4 Load Balancers (Transport Layer)

- Operates at **TCP/UDP level**.
- Makes routing decisions based on **IP address and port** only.
- Faster, lower overhead, but limited flexibility.

👉 **Example:** AWS **Network Load Balancer (NLB)**

- Handles millions of requests/sec with ultra-low latency.
- Preserves client IP.
- Best for TCP/UDP protocols (gaming, VoIP, financial apps).

**Use Case:**

- A stock trading app requiring **millisecond latency** routes TCP connections via NLB → backend trading engines.

### 🔹 2.2 Layer 7 Load Balancers (Application Layer)

- Operates at the **HTTP/HTTPS layer**.
- Makes intelligent routing decisions based on **headers, paths, hostnames, cookies**.
- Supports SSL termination, WAF, sticky sessions.

👉 **Example:** AWS **Application Load Balancer (ALB)**

- Routes /api/\* requests to API servers, /static/\* to S3/CloudFront.
- Supports WebSockets and gRPC.
- Integrates with AWS Cognito for authentication.

**Use Case:**

- An **e-learning Django app** with ALB routing:
  - /api/\* → Django REST API (ECS tasks).
  - /media/\* → CloudFront/S3.
  - /admin/\* → separate admin container.

### 🔹 2.3 Classic Load Balancer (CLB)

- Legacy AWS LB (predecessor to ALB & NLB).
- Supports Layer 4 and limited Layer 7 routing.
- Still in use for legacy apps but not recommended for new deployments.

**Use Case:**

- A **monolithic Django app** hosted on EC2 instances behind CLB.

### 🔹 2.4 Global Load Balancers (Geo / Multi-region)

- Operate at the **DNS or edge network layer**.
- Route traffic across regions or continents.
- Provide **geo-routing, latency-based routing, and failover**.

👉 **Examples:**

- **AWS Route 53** (DNS-based load balancing with health checks).
- **Google Cloud Load Balancer (Global HTTPS)**.
- **Azure Front Door**.

**Use Case:**

- A global SaaS platform directs users to the **closest AWS region** (US, EU, APAC) for lower latency.

## 3\. Load Balancer Algorithms

Load balancers use different **routing algorithms**:

- **Round Robin** → Each server in turn (default, simple).
- **Least Connections** → Send traffic to server with fewest active connections.
- **IP Hash** → Same client always goes to same backend (useful for sticky sessions).
- **Weighted Round Robin** → More powerful servers get more requests.
- **Health-based Routing** → Routes only to healthy instances.

## 4\. AWS Load Balancers in Detail

AWS provides multiple types of managed LBs:

| **Type** | **OSI Layer** | **Protocols** | **Best For** | **Example** |
| --- | --- | --- | --- | --- |
| **ALB (Application Load Balancer)** | 7   | HTTP/HTTPS, WebSockets, gRPC | Microservices, APIs, web apps | Django REST API |
| **NLB (Network Load Balancer)** | 4   | TCP, UDP, TLS | High-performance, low-latency apps | Gaming servers, chat apps |
| **CLB (Classic Load Balancer)** | 4 & 7 | HTTP, HTTPS, TCP, SSL | Legacy monolithic apps | Old EC2 apps |
| **GWLB (Gateway Load Balancer)** | 3   | IP Packets | Security appliances (firewalls, IDS) | Intrusion detection system |

## 5\. Real-world Examples

### ****Example 1: Django + ALB****
```arduino
Client → ALB → ECS Fargate Tasks (Django REST API)
```
- ALB terminates SSL.
- Routes /api/ requests to Django app.
- Routes /static/ to S3/CloudFront.

### ****Example 2: Gaming App + NLB****
```arduino
Client → NLB → EC2 Game Servers
```
- NLB preserves player IP.
- Handles UDP packets for real-time gaming.
- Ultra-low latency < 1 ms.

### ****Example 3: Global SaaS + Route 53****

User (Asia) → Route 53 DNS → Singapore ALB

User (US) → Route 53 DNS → Virginia ALB

- Latency-based routing ensures users hit nearest backend.
- Failover: if Virginia fails, Route 53 routes US users to Europe.

### ****Example 4: Security Appliance with GWLB****
```arduino
Traffic → GWLB → Firewall VPC → Private Applications
```
- GWLB routes all packets through a 3rd party IDS/IPS firewall.

## 6\. Choosing the Right Load Balancer

- **Use ALB** → Web apps, APIs, microservices, HTTPS.
- **Use NLB** → TCP/UDP workloads, low-latency, millions of connections.
- **Use CLB** → Only for legacy.
- **Use Route 53 / Global LB** → Multi-region or global apps.
- **Use GWLB** → Network-level security appliances.

## 7\. Best Practices

- Always enable **health checks**.
- Use **SSL termination** at LB level.
- Use **auto-scaling groups** with LB for elasticity.
- Use **sticky sessions** only when necessary (scales poorly).
- Log LB access for auditing & monitoring.

✅ **Summary**

- **ALB** → smart HTTP/HTTPS routing.
- **NLB** → extreme scale, TCP/UDP, low latency.
- **CLB** → legacy, avoid for new apps.
- **GWLB** → security appliances.
- **Route 53 / Global LBs** → multi-region/global routing.

Load balancers are the **backbone of scalability and availability** in modern cloud applications.