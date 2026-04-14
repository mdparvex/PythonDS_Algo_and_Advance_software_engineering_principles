# System Design & Architectural Optimization Guide (Mid/Senior Level)

---

## 1. System Design Fundamentals

### Key Concepts
- **Scalability**: Ability to handle growth.
  - Vertical: increase CPU/RAM of one machine
  - Horizontal: add more machines (preferred at scale)
- **Availability**: System remains operational (e.g., 99.99% uptime)
- **Reliability**: System works correctly over time (no data corruption)
- **Consistency (CAP)**: All users see the same data
- **Latency vs Throughput**:
  - Latency: time per request
  - Throughput: requests per second

---

## 2. High-Level Design (HLD)

### Components
- **Client**: Browser/mobile app sending requests
- **API Layer**: Entry point (load balancer + web servers)
- **Application Layer**: Business logic
- **Database**: Persistent storage
- **Cache**: Fast data retrieval
- **Message Queue**: Async processing

👉 In interviews, start with this block diagram first.

---

## 3. Low-Level Design (LLD)

- **Database schema**: Tables, relations, indexes
- **API contracts**: Request/response format
- **Class design**: Code-level structure

👉 This is where you go deeper after HLD.

---

## 4. CAP Theorem

- **Consistency**: Same data everywhere
- **Availability**: Always responds
- **Partition Tolerance**: Works despite network failure

👉 In distributed systems, you must choose:
- CP (e.g., banking systems)
- AP (e.g., social media feeds)

---

## 5. Database Design

### SQL vs NoSQL

**SQL**:
- Strong consistency
- ACID transactions
- Structured schema

**NoSQL**:
- Flexible schema
- Horizontal scaling
- Eventual consistency

👉 Choose based on use case, not popularity.

---

## 6. Indexing & Query Optimization

- Index speeds up reads but slows writes
- Avoid full table scans

```sql
EXPLAIN SELECT * FROM users WHERE email='a@test.com';
```

👉 Always mention EXPLAIN in interviews.

---

## 7. Caching Strategies

### Types
- **Read-through**: Cache sits in front of DB
- **Write-through**: Write to cache + DB together
- **Write-back**: Write to cache first, DB later

👉 Trade-off: speed vs consistency

---

## 8. Load Balancing

- **Round Robin**: evenly distributes
- **Least Connections**: sends to least busy server
- **IP Hash**: same user → same server

👉 Improves availability and scalability

---

## 9. API Design Best Practices

- RESTful design
- Idempotency (safe retries)
- Pagination (avoid large payloads)
- Rate limiting (prevent abuse)

---

## 10. Microservices vs Monolith

### Monolith
- Simple to build
- Hard to scale later

### Microservices
- Independent services
- Complex (network, deployment)

👉 Start monolith → evolve to microservices

---

## 11. Message Queues

- Kafka, RabbitMQ

**Use cases**:
- Background jobs
- Decoupling services

👉 Example: sending email asynchronously

---

## 12. Consistency Patterns

- **Strong**: always accurate
- **Eventual**: eventually correct

👉 Eventual consistency improves scalability

---

## 13. Distributed Systems Challenges

- Network failures
- Partial outages
- Data inconsistency

👉 Always design for failure

---

## 14. Rate Limiting

- **Token Bucket**: allows bursts
- **Leaky Bucket**: smooth flow

👉 Protects APIs from abuse

---

## 15. Fault Tolerance

- Retries (with backoff)
- Circuit breaker (stop failing calls)

👉 Prevent cascading failures

---

## 16. Observability

- Logging (what happened)
- Monitoring (metrics)
- Tracing (request flow)

👉 Helps debug production issues

---

## 17. Security

- Authentication (who you are)
- Authorization (what you can do)
- HTTPS encryption

👉 Never ignore security in design

---

## 18. Scaling Techniques

- Horizontal scaling
- Read replicas
- Sharding (split DB)

👉 Scaling DB is hardest part

---

## 19. Architectural Patterns

- Layered architecture
- Event-driven (async systems)
- CQRS (separate read/write)

👉 Used in large-scale systems

---

## 20. Performance Optimization

- Reduce DB calls
- Optimize queries
- Add caching

👉 Measure before optimizing

---

## 21. Real-World System Design Examples

### URL Shortener
- Hash long URL → short code
- Store in DB
- Cache popular URLs

### Chat System
- WebSocket for real-time
- Queue for message delivery

---

## 22. Deep Critical Topics (Senior Level)

### 22.1 N+1 Problem
- Multiple DB calls instead of one
👉 Fix using joins or batching

### 22.2 Backpressure
- System overloaded with requests
👉 Use queues, rate limiting

### 22.3 Data Partitioning
- Split data across nodes
👉 Hash-based is common

### 22.4 Idempotency
- Same request → same result
👉 Important for payments

### 22.5 Distributed Transactions
- Hard to maintain consistency
👉 Use Saga pattern instead of 2PC

### 22.6 Cache Invalidation
- Keeping cache fresh is difficult
👉 TTL + write strategies

### 22.7 Thundering Herd
- Many requests hit DB at once
👉 Use caching + locking

### 22.8 Hotspots
- Uneven traffic distribution
👉 Use sharding or load balancing

### 22.9 Read vs Write Optimization
- Read-heavy → cache
- Write-heavy → batch writes

### 22.10 Trade-offs (Most Important)
- Consistency vs availability
- Cost vs performance

👉 Interviewers care most about this

---

## 23. Common Interview Questions

1. Design scalable API → talk about caching, DB, load balancer
2. Handle millions of users → horizontal scaling
3. Scale DB → replication + sharding
4. Reduce latency → caching + CDN
5. Notification system → queue + async workers

---

## 24. Interview Strategy

1. Clarify requirements
2. Define scale (users, traffic)
3. Draw HLD
4. Deep dive into bottlenecks
5. Discuss trade-offs

👉 Always think aloud and justify decisions

---

End of Guide

