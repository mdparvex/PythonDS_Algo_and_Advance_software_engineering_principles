# Rate limiting — complete technical documentation

Scope: This document explains rate limiting concepts, algorithms, design choices, deployment considerations, and provides a concrete, production-ready design and code for implementing a **token-bucket** based rate limiter for a Django application (including Django REST Framework). It covers features, failure modes, metrics, tests, and operational guidance.

# 1\. What is rate limiting and why it matters

**Rate limiting** restricts how many requests (or actions) a client may perform in a given time window. Purposes:

- Protect backends from overload (DoS, traffic spikes).
- Enforce fair usage / quotas for tenants.
- Control costs (third-party APIs, DB).
- Throttle abusive clients / bots.
- Smooth traffic bursts while allowing short-term bursts (if algorithm supports burstiness).

Key requirements for a real system:

- **Correctness** (no easy bypass).
- **Low latency** (limit checks are fast).
- **Atomicity** (no race conditions).
- **Scalability** (works across multiple app instances).
- **Configurability** (per-user, per-IP, per-endpoint, per-API-key, different limits).
- **Observability** (metrics, logs, headers).

# 2\. Rate-limiting algorithms — overview, tradeoffs & when to use

1. **Fixed window counter**
    - Count requests per fixed time window (e.g., per minute).
    - Simple, low memory.
    - Problem: burstiness at window edges (clients can do 2× allowed in boundary cases).
    - Use when simplicity and low cost matter and burst edges acceptable.
2. **Sliding window log**
    - Store timestamps of requests; count those within a rolling window.
    - Accurate; supports arbitrary windows.
    - Memory & CPU heavy (store many timestamps per client).
    - Use when precise enforcement is required for low QPS per client.
3. **Sliding window counter (approximate)**
    - Split time into smaller windows and weight counts.
    - Balances accuracy and storage.
4. **Token bucket**
    - Tokens accumulate at a fixed rate up to a capacity (burst).
    - Each request consumes tokens; if tokens available -> allowed.
    - Supports steady rate + bursts. Very common for APIs.
    - Implementable atomically in Redis with a small state (last refill timestamp, tokens).
    - Good for per-user and global limits.
5. **Leaky bucket**
    - Similar to token bucket but models output drain; often equivalent except implementation details.
6. **Rate-limit headers and policies**
    - Return headers such as RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset or legacy X-RateLimit-\*.
    - Return HTTP 429 on limit exceeded.

# 3\. Feature list for a production-ready rate limiter

- Per-entity limits (user, API key, IP, tenant, endpoint)
- Global application limit and per-route overrides
- Support for different algorithms (token-bucket, fixed-window, sliding-window)
- Burst control (allow short bursts)
- Configurable time windows & quotas
- Atomic backend operations (Redis / memcached / database with locking)
- Distributed operation across multiple application instances
- Grace period / soft-limit vs hard-limit behavior
- Quotas and monthly/daily resets (usage tracking)
- Retry-after header support
- Rate-limit response customization (body + headers)
- Whitelisting & blacklisting
- Admin UI / dynamic config (feature flags)
- Instrumentation: metrics, logs, dashboards, alerts
- Tests & chaos handling (partial Redis failure)
- Metrics: blocked_requests, allowed_requests, remaining_tokens, approx queue depth
- Fail-open vs fail-closed policy
- Client identification logic and anti-spoofing

# 4\. Choosing the backend

- **Redis** (recommended): fast, supports atomic Lua scripts, built-in TTL. Best for distributed and high QPS.
- **Memcached**: OK for simple counters, but no atomic incrementation with expiry semantics as easily and no Lua.
- **Relational DB** (Postgres): ok for low QPS; more latency and DB load. Must use transactions and careful locking.
- **In-memory (local)**: fastest but not shared — only for single-node setups.

**Recommendation:** Use Redis (cluster or sentinel) for production. Use Lua scripts for atomic token bucket semantics.

# 5\. Design: Token bucket rate limiter for Django (architecture)

Components:

- **Middleware / DRF Throttle**: intercept requests, identify client, call rate limiter, and decide allow/deny.
- **Rate limiter core**: token-bucket implementation with redis backend, atomic via Lua.
- **Configuration**: global defaults + per-endpoint / per-user overrides stored in settings or dynamic store.
- **Metrics exporter**: increment counters for allowed/blocked; export to Prometheus / StatsD.
- **Response**: include 429 if blocked with Retry-After and RateLimit-\* headers.

Flow:

1. Request arrives.
2. Identify key (e.g., user:{id}, ip:{ip}, api_key:{key}).
3. Determine applicable limit configuration (limit, refill_rate, capacity).
4. Call Redis LUA script that:
    - Refill tokens based on elapsed time, up to capacity.
    - If tokens >= cost (usually 1), decrement and return allowed with remaining tokens and reset time.
    - Else return blocked with time-to-next-token (for Retry-After).
5. Middleware/Throttle adds headers and either continues or returns 429.

# 6\. Data model & keys (Redis)

For each rate-limited key, store small state (single Redis key preferably a hash or compact string):

- Key name pattern: rl:{scope}:{id}:{route_or_action}
  - e.g. rl:user:42:/api/v1/books:token
- Stored values:
  - tokens (float)
  - last (last refill timestamp in ms)
  - optionally capacity (if variable per key — otherwise stored in config)

Prefer storing compact string (two numbers) to reduce round trips and make Lua script simpler.

TTL: set TTL to max window or longer (e.g., 2× window) to auto-expire idle keys.

# 7\. Atomic Redis Lua script (token bucket)

This script refills and consumes atomically. It returns `[allowed (0/1), tokens_left (float), retry_after_seconds (float), reset_ts_ms]`.

```lua
-- ARGV[1] = now_ms
-- ARGV[2] = refill_rate (tokens per second)
-- ARGV[3] = capacity (max tokens)
-- ARGV[4] = cost (tokens to consume; default 1)
-- ARGV[5] = ttl_seconds (key TTL)
-- KEYS[1] = redis key

local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call('GET', KEYS[1])
local tokens = capacity
local last = now

if data then
  local sep = string.find(data,':')
  if sep then
    tokens = tonumber(string.sub(data,1,sep-1))
    last = tonumber(string.sub(data,sep+1))
  end
end

-- Refill
local delta_ms = math.max(0, now - last)
local refill = (delta_ms / 1000.0) * rate
tokens = math.min(capacity, tokens + refill)
last = now

local allowed = 0
local retry_after = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
else
  -- calculate time until next token available
  local needed = cost - tokens
  retry_after = needed / rate
end

-- store back as "tokens:last"
local value = tostring(tokens) .. ':' .. tostring(last)
redis.call('SET', KEYS[1], value, 'EX', ttl)

-- reset_ts_ms: estimate when tokens reach capacity (optional)
local time_to_reset = 0
if tokens < capacity then
  time_to_reset = ((capacity - tokens) / rate) -- seconds
end
local reset_ts_ms = now + math.floor(time_to_reset * 1000)

return {allowed, tostring(tokens), tostring(retry_after), tostring(reset_ts_ms)}

```

Notes:

- We store tokens:last as a single string.
- TTL should be long enough (e.g., max(window_seconds \* 2, 3600)).
- refill_rate is in tokens/sec. cost typically 1.

# 8\. Django implementation — components & code

We'll show:

- Redis client setup
- Core limiter wrapper calling Lua
- Django middleware example
- DRF throttle class example
- Settings/config

## 8.1 Dependencies (Python)

```bash
pip install redis django djangorestframework
```

## 8.2 Settings (example in settings.py)

```python
# settings.py

RATE_LIMIT = {
    'DEFAULT': {
        'refill_rate': 1.0,   # tokens per second
        'capacity': 5.0,      # allow bursts up to 5
        'ttl': 3600,          # redis TTL in seconds
        'cost': 1.0
    },
    'ROUTES': {
        # per-route overrides (path prefix matching)
        '/api/v1/login': {'refill_rate': 0.2, 'capacity': 1},
        '/api/v1/search': {'refill_rate': 5.0, 'capacity': 20},
    },
    'IDENTITY_PRIORITY': ['user', 'api_key', 'ip']
}

REDIS_HOST = 'localhost'  # or from env
REDIS_PORT = 6379
REDIS_DB = 0

```

## 8.3 Redis client & Lua script loader (e.g., rate_limiter/core.py)

```python
# rate_limiter/core.py
import time
import math
from redis import Redis

REDIS = Redis(host='localhost', port=6379, db=0, decode_responses=True)

# The LUA script as a string (from section 7); register it
TOKEN_BUCKET_LUA = """-- paste the Lua script here exactly as above --"""

TOKEN_BUCKET_SHA = REDIS.script_load(TOKEN_BUCKET_LUA)

def now_ms():
    return int(time.time() * 1000)

def get_route_config(path, settings):
    # precise matching or prefix matching; simple prefix for example
    routes = settings.get('ROUTES', {})
    for prefix, cfg in routes.items():
        if path.startswith(prefix):
            return {**settings.get('DEFAULT', {}), **cfg}
    return settings.get('DEFAULT', {})

def make_key(scope, identifier, route):
    # keep key short
    return f"rl:{scope}:{identifier}:{route}"

def consume_token(key, refill_rate, capacity, cost=1.0, ttl=3600):
    now = now_ms()
    # ARGV: now_ms, refill_rate, capacity, cost, ttl
    result = REDIS.evalsha(TOKEN_BUCKET_SHA, 1, key, now, refill_rate, capacity, cost, ttl)
    # result: [allowed (0/1), tokens_left, retry_after_seconds, reset_ts_ms]
    allowed = bool(int(result[0]))
    tokens_left = float(result[1])
    retry_after = float(result[2])
    reset_ts_ms = int(result[3])
    return allowed, tokens_left, retry_after, reset_ts_ms
```

**Note:** In production, use Redis connection pooling, env-configured host/port, and handle NOSCRIPT (re-register script if needed).

## 8.4 Identity extraction (how to generate the rate key)

Implement an ordered priority for identification, fallback from authenticated user -> api_key -> IP:

```python
# rate_limiter/identity.py
def identify_request(request):
    # returns (scope, identifier)
    # 1) Authenticated user id
    if getattr(request, 'user', None) and request.user.is_authenticated:
        return ('user', str(request.user.id))
    # 2) API key header
    api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
    if api_key:
        return ('api_key', api_key)
    # 3) IP
    ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', 'unknown')
    return ('ip', ip)

```

## 8.5 Django middleware example (simple)

```python
# rate_limiter/middleware.py
from django.conf import settings
from django.http import JsonResponse
from .core import get_route_config, make_key, consume_token
from .identity import identify_request

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, 'RATE_LIMIT', {})

    def __call__(self, request):
        scope, identifier = identify_request(request)
        route = request.path
        cfg = get_route_config(route, self.config)

        key = make_key(scope, identifier, route)
        allowed, tokens_left, retry_after, reset_ts_ms = consume_token(
            key,
            cfg['refill_rate'],
            cfg['capacity'],
            cfg.get('cost', 1.0),
            cfg.get('ttl', 3600)
        )

        # Add headers
        limit = cfg['capacity']
        remaining = int(math.floor(tokens_left))
        reset_seconds = max(0, int((reset_ts_ms - int(time.time()*1000)) / 1000))

        request.rate_limit = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_seconds
        }

        headers = {
            'RateLimit-Limit': str(limit),
            'RateLimit-Remaining': str(remaining),
            'RateLimit-Reset': str(reset_seconds)
        }

        if not allowed:
            headers['Retry-After'] = str(int(math.ceil(retry_after)))
            body = {
                'detail': 'Request was throttled. Expected available in {} seconds.'.format(int(math.ceil(retry_after)))
            }
            return JsonResponse(body, status=429, headers=headers)

        response = self.get_response(request)
        for k, v in headers.items():
            response[k] = v
        return response
```

Add to `MIDDLEWARE` in settings.

## 8.6 Django REST Framework throttle integration (optional)

DRF has a throttle API — you can implement a custom throttle class that calls the same consume_token and integrates nicely.

```python
# rate_limiter/drf_throttles.py
from rest_framework.throttling import BaseThrottle
from django.conf import settings
from .core import get_route_config, make_key, consume_token
from .identity import identify_request

class RedisTokenBucketThrottle(BaseThrottle):
    def allow_request(self, request, view):
        scope, identifier = identify_request(request)
        route = request.path
        cfg = get_route_config(route, settings.RATE_LIMIT)
        self.key = make_key(scope, identifier, route)
        allowed, tokens_left, retry_after, reset_ts_ms = consume_token(
            self.key, cfg['refill_rate'], cfg['capacity'], cfg.get('cost',1.0), cfg.get('ttl',3600)
        )
        self.rate = cfg
        self.allowed = allowed
        self.tokens_left = tokens_left
        self.retry_after = retry_after
        self.reset_ts_ms = reset_ts_ms
        return allowed

    def wait(self):
        # return seconds to wait for DRF to use in Retry-After
        return self.retry_after
```

Configure in DRF settings or per-view.

# 9\. Headers & API behavior

Return these headers on allowed and blocked responses:

- `RateLimit-Limit`: the configured capacity (or limit).
- `RateLimit-Remaining`: remaining tokens (integer).
- `RateLimit-Reset`: seconds until tokens fully replenish (or next window reset).
- `Retry-After`: when blocked, how many seconds to wait before retrying.
- Optionally `X-RateLimit-*` for older clients.

Responses:

- On exceed: HTTP `429 Too Many Requests` and JSON body that explains reason and `Retry-After`.

# 10\. Testing & verification

Unit tests:

- Mock Redis or use a test Redis instance.
- Test token refill behavior:
  - Consume tokens consecutively until exhausted -> expect blocked.
  - Wait simulated time -> expect tokens refilled.
- Race condition tests: spawn parallel workers hitting same key to ensure correct atomicity (use Redis + Lua).
- TTL and key expiry tests.

Integration tests:

- Start Django with middleware and use HTTP client to simulate bursts from same identity.
- Validate returned headers and status codes.

Example pytest snippet:

```python
def test_token_bucket_allows_and_blocks(redis_client):
    key = 'rl:test:1:/api/test'
    # reset state
    redis_client.delete(key)

    cfg = {'refill_rate': 1.0, 'capacity': 3.0, 'ttl': 60, 'cost': 1.0}
    # consume 3 tokens -> allowed
    for i in range(3):
        allowed, tokens, retry, reset = consume_token(key, cfg['refill_rate'], cfg['capacity'], cfg['cost'], cfg['ttl'])
        assert allowed
    # 4th request -> blocked
    allowed, tokens, retry, reset = consume_token(key, cfg['refill_rate'], cfg['capacity'], cfg['cost'], cfg['ttl'])
    assert not allowed
```

# 11\. Operational concerns & scaling

- **Redis scaling**
  - Use Redis Cluster or Sentinel for high availability.
  - Use a single Redis instance only for small deployments.
  - Be mindful of script registration across nodes (`NOSCRIPT` fallback).
- **Latency**
  - Lua script round-trip to Redis per request — typically ~1ms; acceptable for many apps.
  - Optionally implement local caching for non-critical policies (but consistent enforcement needs central Redis).
- **Fail-open vs fail-closed**
  - **Fail-open:** If Redis is down, allow traffic (risk abuse).
  - **Fail-closed:** If Redis is down, deny everything (safer but causes outage).
  - Choose based on business needs; often **fail-open** is chosen with increased logging/alerting.
- **Monitoring**
  - Track metrics: `rate_limit.allowed, rate_limit.blocked, rate_limit.remaining, rate_limit.retries`.
  - Export to Prometheus/StatsD.
  - Alert on sudden spike in 429 responses.
- **Capacity planning**
  - Estimate number of distinct keys (users \* endpoints).
  - Redis memory per key is small (a few dozen bytes) but multiplied can be large.
  - Use `EXPIRE` to let idle keys evict.

# 12\. Advanced features

- **Dynamic policy changes**
  - Store per-user or per-tenant policies in DB or Redis and fetch them in middleware (cache for a short time).
- **Quota windows**
  - For daily/monthly quotas, use separate counters in Redis (incr with TTL to next reset).
- **Penalty/backoff**
  - Increase cooldown for repeated violations.
- **Rate-limiting for large payloads**
  - Cost per request >1 when heavier operations occur (e.g., file uploads cost more tokens).
- **Adaptive / demand-based limits**
  - Decrease refill rate when overall system load is high (observe CPU, queue length).
- **Ban / blacklist**
  - If repeated abuse, add to blacklist store and return 403.
- **IP hashing & geo-sensitivity**
  - Rate limit differently by geography or plan.

# 13\. Security considerations & anti-abuse

- **Spoofed IPs**: Don’t trust `X-Forwarded-For` without proper proxy config.
- **Shared IPs (NAT)**: Be careful — rate-limiting by IP can hurt users behind NAT.
- **API key identification**: Prefer API keys or tokens for accurate per-client enforcement.
- **Header size enumeration**: Protect against malicious requests trying to evade by changing headers.
- **Slow loris / connection hold**: Rate limiting request count doesn't stop connection-level attacks — use connection-level protections (nginx, load balancer).

# 14\. Logging & observability

- Log each blocked request with identity, route, and reason.
- Increment metrics for:
  - `rate_limit.allowed_total`
  - `rate_limit.blocked_total`
  - `rate_limit.blocked_by_route`
  - `rate_limit.remaining_gauge (per critical key)`
- Provide dashboards: 429-rate over time, top blocked keys, top endpoints causing blocks.
- Correlate with app errors and latencies.

# 15\. Deployment checklist

- Configure Redis cluster / sentinel and connection pooling.
- Add `RateLimitMiddleware` in `MIDDLEWARE` after authentication (if you rely on authenticated user).
- Tune default `refill_rate` and `capacity` in `settings.py`.
- Ensure correct client IP extraction (behind proxies).
- Add Prometheus/StatsD exporter for rate-limit metrics.
- Add unit and integration tests to CI.
- Roll out with canary: start with logging-only mode (don’t block) to observe rates, then enable blocking.
- Plan alerts for high 429, Redis errors.

# 16\. Example: complete minimal files

- `rate_limiter/core.py` — redis + lua wrapper (see 8.3)
- `rate_limiter/middleware.py` — hooking into Django request lifecycle (see 8.5)
- `rate_limiter/identity.py` — identity extraction (see 8.4)
- `rate_limiter/drf_throttles.py` — DRF integration (see 8.6)
- `settings.py` — configuration (see 8.2)
- Tests / CI with mocked redis.

# 17\. Common pitfalls & troubleshooting

- **Race conditions** — solved by Lua atomic script.
- **Script missing (NOSCRIPT)** — handle by re-registering script if `NOSCRIPT` error occurs.
- **Wrong time units** — keep consistent ms vs s (Lua script uses ms for timestamps).
- **Large cardinality** — too many unique keys can blow up Redis memory; set sensible TTL and aggregate policies.
- **Overly strict policy** — cause customer complaints; start conservative and tune.
- **Incorrect identity extraction** — results in per-client unfairness; ensure authentication runs before rate limiter if using user ID.

# 18\. Example curl test

```bash
# simulate requests (API behind middleware)
for i in {1..10}; do
  curl -i -H "X-API-KEY: mykey" http://localhost:8000/api/v1/some-endpoint
done
```

Monitor headers RateLimit-Remaining and Retry-After.

# 19\. Performance & complexity

- **Runtime per request:** O(1) Redis lua eval (constant time).
- **Space:** O(N) where N = number of active identities (keys). Each key approx small string — plan memory.
- **Throughput:** bounded by Redis throughput. Redis Cluster for horizontal scaling.

# 20\. Summary / recommended defaults

- Use **token bucket** implemented in Redis with Lua scripts for atomicity.
- Identify clients with priority: API key > authenticated user > IP.
- Include `RateLimit-\*` and `Retry-After` headers; return `429` when limit exceeded.
- Monitor & start in logging-only mode before enabling hard blocks.
- Consider fail-open on Redis failure unless business requires fail-closed.

Great question 👍 Let me explain **how this rate limiter works for an API** in a clear step-by-step way. I’ll use the **token bucket algorithm** I designed for Django in the documentation.

**1\. Idea behind token bucket (for API)**

- Think of a **bucket** that holds “tokens.”
- Each **request** costs one token.
- Tokens **refill at a steady rate** (e.g., 1 token per second).
- The bucket has a **capacity** (e.g., max 5 tokens).
- If the bucket has tokens → request is **allowed**.
- If empty → request is **blocked** (HTTP 429 Too Many Requests).

This way:

- Clients can make a **burst** of requests (up to capacity).
- But over time, they can only sustain the refill rate.

**2\. How it works in Django API (flow)**

1. **Request comes in**  
    Example: A client calls
```bash
GET /api/v1/books
```
2. **Identify the client**
    - If authenticated → use user_id.
    - If not → fallback to API key or IP.
    - Example: user:42
3. **Look up the rate limit policy**
    - Example: For /api/v1/books → capacity = 5, refill = 1/sec.
4. **Check Redis token bucket**
    - Middleware calls a **Lua script in Redis** with the client’s key:
    ```ruby
    rl:user:42:/api/v1/books
    ```
    - Redis does:
        - Refill tokens based on last timestamp.
        - If tokens ≥ 1 → subtract 1 → request allowed.
        - If tokens < 1 → request blocked.
5. **Return decision**
    - If **allowed** → API continues normally.
    - If **blocked** → return HTTP 429 Too Many Requests.
6. **Add response headers**  
    Every API response includes headers so clients know their limits:
```makefile
RateLimit-Limit: 5
RateLimit-Remaining: 3
RateLimit-Reset: 2
```

Meaning:

- - Limit = 5 requests (bucket size)
    - 3 tokens left
    - Bucket refills completely in 2 seconds

If blocked, also send:

```makefile
Retry-After: 2
```

**3\. Example with timeline**

Policy: **5 requests burst, 1 token/sec refill**

- **t=0** (bucket full = 5) → client sends 5 requests immediately → all allowed.
- **t=1** (1 token refilled) → client sends 1 request → allowed.
- **t=1.1** → another request comes, but bucket empty → blocked (429).
- **t=2** → another token refilled → client can send 1 more request.

This enforces **average 1 request/second**, but still allows **short bursts of 5**.

**4\. Why this is good for APIs**

- **Protects backend** from traffic floods.
- **Fair usage** → every client gets the same rate.
- **Burst-friendly** → doesn’t block clients who send a few quick requests.
- **Predictable** → clients can rely on headers to know when to retry.

✅ So, in short:  
Each API client has a **bucket in Redis**. Every request spends a token. Tokens refill over time. If the bucket is empty → the API immediately rejects with 429.

Excellent questions 🙌 You’ve touched on two **very important distinctions**:

1. **Application-level rate limiting (inside Django)**
2. **Gateway-level rate limiting (before requests hit Django)**

Let’s break it down carefully.

**1\. Application-level rate limiting (inside Django)**

**✅ How it works**

- Implemented in **Django middleware or DRF throttle classes**.
- Runs **after the request reaches your app** (inside Python).
- Each request is checked using Redis + Lua (or DB, cache, etc).
- Can be **fine-grained** (per-user, per-API-key, per-view).
- Developers have **full control** — you can change rules in Python code.

**⚠️ Limitations**

- Requests already **consume server/network resources** (they reach Django before being blocked).
- High-volume malicious traffic may still overwhelm your app if not stopped earlier.
- Scaling depends on Django + Redis performance.

**Example:**

The implementation I gave you earlier (middleware/DRF throttle).  
That will work for **all endpoints** unless you configure per-route overrides.

**2\. Gateway-level rate limiting (outside Django)**

**✅ How it works**

- Implemented at the **API gateway / reverse proxy / load balancer** layer.
- Common tools: **Nginx, Kong, Envoy, AWS API Gateway, Traefik**.
- Requests are **blocked before they hit Django**.
- Very **efficient** — written in C/Go, closer to network edge.
- Ideal for **global limits** (per IP, per domain, per API key).

**⚠️ Limitations**

- Less flexible for **application-specific rules** (like “user 42 can make 10 requests/minute but premium users get 100”).
- You need to integrate gateway config with your app DB if you want per-user customization.

**Example: Nginx gateway rate limiting**

```nginx
http {
    # Define a rate limit zone (10 MB shared memory for counters)
    limit_req_zone $binary_remote_addr zone=per_ip:10m rate=1r/s;

    server {
        listen 80;

        location /api/ {
            limit_req zone=per_ip burst=5 nodelay;
            proxy_pass http://django_app;
        }
    }
}

```

- This allows **1 request per second per IP**.
- Bursts up to 5 requests allowed.
- If exceeded → Nginx returns 503 Service Temporarily Unavailable.

**3\. Comparison — Django vs Gateway rate limiting**

| **Feature** | **Django-level (App)** | **Gateway-level (Nginx/Kong/etc.)** |
| --- | --- | --- |
| **Where enforced** | Inside Django (Python) | At network edge (proxy/load balancer) |
| **Flexibility** | Very flexible (per user, per plan, per endpoint, custom logic) | Mostly per-IP or per-API-key, more generic |
| **Performance** | Slower (Python + Redis call per request) | Faster (C/Go native, in-memory counters) |
| **Resource usage** | Request reaches Django before being blocked | Blocked before Django → saves CPU/memory |
| **Integration with app logic** | Easy (can use Django user model, permissions, plans) | Hard (must sync limits from DB → gateway config) |
| **Best for** | Application-specific quotas, premium plans, API keys, business logic | Protecting backend from floods, global per-IP throttling, DDoS mitigation |
| **Example** | RateLimitMiddleware in Django | limit_req_zone in Nginx |

**4\. Hybrid approach (best practice)**

Most **real-world systems** use **both**:

- **Gateway-level rate limiting** (coarse-grained, cheap):
  - Per-IP limits (e.g., 100 req/min per IP).
  - DDoS protection.
  - Stops bots/attackers before they hit Django.
- **Application-level rate limiting** (fine-grained, business rules):
  - Per-user limits (e.g., free users 10/min, premium users 100/min).
  - Per-endpoint logic (e.g., /login is stricter).
  - Quotas (daily/monthly usage).

✅ **In your case (Django app with API)**:

- If you only implement the Django middleware I gave → yes, it will work for **all endpoints** (unless excluded).
- But for **production best practice** → combine:
  - **Nginx (gateway-level)**: protect the app from floods per IP.
  - **Django (app-level)**: enforce per-user/per-plan quotas.