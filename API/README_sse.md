# Server-Sent Events (SSE) with Django and Redis

> Technical guide to understanding, implementing, testing, and operating
> Server-Sent Events in a Django application.

## Table of Contents

1.  [What is SSE?](#1-what-is-sse)
2.  [How SSE Works](#2-how-sse-works)
3.  [SSE vs Polling vs WebSockets](#3-sse-vs-polling-vs-websockets)
4.  [The SSE Wire Protocol](#4-the-sse-wire-protocol)
5.  [A Minimal Django SSE Example](#5-a-minimal-django-sse-example)
6.  [Frontend: Consuming an SSE
    Stream](#6-frontend-consuming-an-sse-stream)
7.  [Production Architecture: Django + Redis +
    SSE](#7-production-architecture-django--redis--sse)
8.  [A Redis-backed Django Example](#8-a-redis-backed-django-example)
9.  [Reliability and Delivery
    Semantics](#9-reliability-and-delivery-semantics)
10. [Authentication and
    Authorization](#10-authentication-and-authorization)
11. [Deployment and Operational
    Considerations](#11-deployment-and-operational-considerations)
12. [Testing SSE](#12-testing-sse)
13. [Common Problems](#13-common-problems)
14. [When to Use SSE](#14-when-to-use-sse)
15. [Further Reading](#15-further-reading)

------------------------------------------------------------------------

## 1. What is SSE?

**Server-Sent Events (SSE)** is a browser technology and a text-based
HTTP streaming protocol that allows a server to push events to a client
over a long-lived HTTP response.

With an ordinary HTTP request, the client sends a request, the server
returns a response, and the request-response exchange finishes.

With SSE:

1.  The browser sends an HTTP `GET` request.
2.  The server responds with `Content-Type: text/event-stream`.
3.  The server keeps the response open.
4.  The server writes events to the response as they become available.
5.  The browser processes each complete event without making another
    request.

SSE is **unidirectional**: the server sends events to the browser. The
browser can still send normal HTTP requests independently, for example
to create an order or update a setting.

### Example use case: order tracking

Imagine an e-commerce application. A customer is viewing order `123`.

The order may move through these states:

``` text
Pending -> Confirmed -> Packaging -> ReadyToGo -> Delivering -> Delivered
```

Without a push mechanism, the browser might repeatedly call an endpoint
such as:

``` http
GET /api/orders/123/status/
```

With SSE, the browser opens one stream:

``` http
GET /api/orders/123/events/
Accept: text/event-stream
```

The server can then send each status change through that same response.

------------------------------------------------------------------------

## 2. How SSE Works

### 2.1 Connection lifecycle

``` text
Browser                         Django server
   |                                  |
   |---- GET /api/orders/123/events ->|
   |                                  |
   |<--- 200 OK ----------------------|
   |<--- Content-Type: text/event-stream
   |                                  |
   |<--- event: order_status ---------|
   |<--- data: {"status":"Confirmed"} |
   |                                  |
   |       Connection stays open      |
   |                                  |
   |<--- event: order_status ---------|
   |<--- data: {"status":"Packaging"} |
   |                                  |
   |       Connection stays open      |
   |                                  |
   |<--- event: order_status ---------|
   |<--- data: {"status":"Delivered"} |
   |                                  |
```

The server does not send a new HTTP response for every event. It writes
multiple event records to one open response.

### 2.2 HTTP headers

A typical request:

``` http
GET /api/orders/123/events/ HTTP/1.1
Host: example.com
Accept: text/event-stream
Cache-Control: no-cache
```

A typical response:

``` http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
```

The response body is a stream of SSE records. `Connection: keep-alive`
is not required as an application-level SSE header, and HTTP/2 does not
use the HTTP/1.1 connection-specific `Connection` header.

### 2.3 Why this is different from normal JSON

A normal Django JSON response might return:

``` json
{
  "order_id": 123,
  "status": "Confirmed"
}
```

The response is complete after this JSON document is sent.

An SSE response uses a stream of text records:

``` text
event: order_status
data: {"order_id": 123, "status": "Confirmed"}

event: order_status
data: {"order_id": 123, "status": "Packaging"}
```

The blank line separates one event from the next. The response itself
can remain open.

------------------------------------------------------------------------

## 3. SSE vs Polling vs WebSockets

  -------------------------------------------------------------------------------
  Property          HTTP polling          SSE               WebSocket
  ----------------- --------------------- ----------------- ---------------------
  Communication     Request/response      Server to client  Bidirectional
                    repeated                                

  Transport         HTTP                  HTTP              WebSocket

  Connection        Repeated requests     Long-lived        Long-lived connection
                                          response          

  Browser API       `fetch()` / XHR       `EventSource`     `WebSocket`

  Reconnection      Application-managed   Built into        Usually
                                          `EventSource`     application-managed

  Payload           Any HTTP response     UTF-8 text event  Text or binary
                    format                stream            

  Typical use       Occasional refresh    Notifications,    Chat, collaboration,
                                          progress, feeds   games
  -------------------------------------------------------------------------------

### 3.1 Polling

The browser repeatedly asks the server whether something changed:

``` javascript
async function refreshOrder() {
  const response = await fetch("/api/orders/123/status/");
  const order = await response.json();

  console.log(order.status);
}

setInterval(refreshOrder, 5000);
```

This is easy to implement, but it creates requests even when there are
no updates. An update can also be delayed until the next polling
interval.

### 3.2 SSE

The browser opens a stream once and listens:

``` javascript
const source = new EventSource("/api/orders/123/events/");

source.addEventListener("order_status", (event) => {
  const order = JSON.parse(event.data);
  console.log(order.status);
});
```

### 3.3 WebSockets

WebSockets allow both sides to send messages over the same connection.
Use them when the client also needs to send frequent real-time messages
over the persistent channel.

**Rule of thumb:**

-   Server-only updates: consider SSE.
-   Frequent two-way interaction: consider WebSockets.
-   Infrequent updates and simple implementation: polling may be
    sufficient.

------------------------------------------------------------------------

## 4. The SSE Wire Protocol

SSE is a UTF-8 text format. Each event consists of optional fields
followed by a blank line.

### 4.1 Supported fields

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `data`                              Event payload. Multiple `data:`
                                      lines are joined with newline
                                      characters.

  `event`                             Event name. Without it, the browser
                                      dispatches a normal `message`
                                      event.

  `id`                                Event identifier. The browser
                                      remembers the last event ID.

  `retry`                             Reconnection delay in milliseconds,
                                      if the value is a valid integer.
  -----------------------------------------------------------------------

Example:

``` text
id: 101
event: order_status
data: {"order_id":123,"status":"Confirmed"}
```

A comment begins with `:` and is ignored by the browser's event
dispatcher:

``` text
: keep-alive
```

Comments are useful as heartbeat traffic to keep idle connections alive
through proxies.

### 4.2 Event names

A named event:

``` text
event: order_status
data: {"status":"Confirmed"}
```

A default message event:

``` text
data: {"message":"Hello"}
```

The browser consumes these differently:

``` javascript
source.addEventListener("order_status", (event) => {
  console.log(JSON.parse(event.data));
});

source.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

### 4.3 Event IDs and reconnection

If the server sends:

``` text
id: 105
event: order_status
data: {"status":"Packaging"}
```

and the connection drops, the browser's native `EventSource`
implementation may reconnect and include:

``` http
Last-Event-ID: 105
```

The application can use this value to resume from a stored event
position. **The browser remembering an ID does not make the server
replay events automatically.** The server must implement replay using a
durable event store or another reliable mechanism.

### 4.4 Retry interval

``` text
retry: 3000
```

This asks the browser to wait approximately 3,000 milliseconds before
attempting to reconnect after a connection closes.

------------------------------------------------------------------------

## 5. A Minimal Django SSE Example

This example simulates an order progressing through several statuses. It
is useful for learning the streaming mechanics; it is not a production
order-event implementation.

### 5.1 View

``` python
# views.py

import json
import time

from django.http import StreamingHttpResponse


def order_events(request, order_id):
    def event_stream():
        statuses = [
            "Pending",
            "Confirmed",
            "Packaging",
            "ReadyToGo",
            "Delivered",
        ]

        for event_id, status in enumerate(statuses, start=1):
            payload = {
                "order_id": order_id,
                "status": status,
            }

            yield (
                f"id: {event_id}\n"
                "event: order_status\n"
                f"data: {json.dumps(payload)}\n\n"
            )

            time.sleep(3)

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response
```

### 5.2 URL configuration

``` python
# urls.py

from django.urls import path

from .views import order_events

urlpatterns = [
    path(
        "api/orders/<int:order_id>/events/",
        order_events,
        name="order-events",
    ),
]
```

### 5.3 Execution flow

1.  Django routes the request to `order_events`.
2.  The view constructs a `StreamingHttpResponse`.
3.  The response consumes the generator as it is iterated.
4.  Each `yield` produces a chunk containing one SSE event.
5.  The browser parses the event after receiving its terminating blank
    line.
6.  The generator pauses at `time.sleep(3)` and then produces the next
    event.

**Important:** `time.sleep()` blocks the executing thread. This is
acceptable for a small local demonstration, but should not be copied
into a high-concurrency production endpoint. Also, the example ends
after five events; a real subscription usually remains open until the
client disconnects or the server closes it.

------------------------------------------------------------------------

## 6. Frontend: Consuming an SSE Stream

The browser provides the native `EventSource` API.

``` javascript
const source = new EventSource(
  "http://localhost:8000/api/orders/123/events/"
);

source.addEventListener("order_status", (event) => {
  const order = JSON.parse(event.data);

  console.log("Order ID:", order.order_id);
  console.log("Status:", order.status);
});

source.onerror = (error) => {
  console.error("SSE connection error:", error);
};

// When the user leaves the tracking screen:
source.close();
```

### 6.1 Important `EventSource` behavior

-   The browser opens the connection immediately.
-   Named events are handled with `addEventListener`.
-   Unnamed events are handled with `onmessage`.
-   The browser normally retries a failed connection automatically.
-   `close()` stops the connection and prevents automatic reconnection.
-   The native API supports cookies and a `withCredentials` option, but
    does not allow arbitrary request headers such as a custom
    `Authorization` header.

Example with cross-origin cookies:

``` javascript
const source = new EventSource(
  "https://api.example.com/api/orders/123/events/",
  { withCredentials: true }
);
```

The server must also configure CORS correctly and allow credentials for
the specific frontend origin. Do not combine credentialed requests with
`Access-Control-Allow-Origin: *`.

------------------------------------------------------------------------

## 7. Production Architecture: Django + Redis + SSE

The minimal example generates events inside the HTTP request. In a real
application, order updates originate from separate business operations.

For example:

-   A support agent confirms an order.
-   A packer starts packaging.
-   A delivery agent marks the order as delivered.

A practical architecture separates business operations from event
delivery.

``` text
                    BUSINESS REQUEST
                           |
                           v
                  Django Order API
                           |
                           v
                    MySQL transaction
                           |
                           v
                 Publish order event
                           |
                           v
                     Redis Pub/Sub
                           |
                           v
                 Django SSE subscriber
                           |
                           v
                  Streaming HTTP response
                           |
                           v
                     Customer browser
```

### 7.1 Component responsibilities

  Component             Responsibility
  --------------------- ----------------------------------------------------
  Django business API   Validates and performs order operations
  MySQL                 Stores the authoritative order state
  Redis Pub/Sub         Distributes transient events to active subscribers
  SSE endpoint          Subscribes to events and streams them to browsers
  Browser               Processes events and updates the UI

### 7.2 Why use Redis?

A Django request that changes an order and a separate Django request
that streams order updates may be handled by different worker processes
or containers.

An in-memory Python variable or queue is not a reliable way to
communicate between them.

Redis provides a shared messaging layer. A publisher can publish an
event, and all active subscribers to the channel can receive it.

For example:

``` text
Channel: order:123

Payload:
{
  "order_id": 123,
  "status": "Confirmed"
}
```

### 7.3 Pub/Sub is not a database

Redis Pub/Sub distributes messages to subscribers that are listening at
publication time. It does not retain messages for disconnected
subscribers.

Therefore:

-   It is suitable for transient live notifications.
-   It is not sufficient by itself when every event must be recoverable.
-   The database should remain the source of truth for the current order
    state.
-   Use Redis Streams, Kafka, or a transactional outbox plus durable
    event storage when replay and reliable delivery are requirements.

------------------------------------------------------------------------

## 8. A Redis-backed Django Example

The following is an educational implementation of the
publisher/subscriber flow. It demonstrates the architecture, but still
requires production authentication, authorization, transaction handling,
connection management, and deployment tuning.

Install the Redis Python client:

``` bash
pip install redis
```

### 8.1 Redis client

``` python
# redis_client.py

import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)
```

### 8.2 Publish after a successful order update

``` python
# services.py

import json

from django.db import transaction

from .redis_client import redis_client


def update_order_status(order, new_status):
    order.status = new_status
    order.save(update_fields=["status"])

    payload = {
        "order_id": order.id,
        "status": order.status,
    }

    # Do not publish before the database transaction commits.
    transaction.on_commit(
        lambda: redis_client.publish(
            f"order:{order.id}",
            json.dumps(payload),
        )
    )
```

In real code, make sure this operation runs inside the intended
transaction boundary. `transaction.on_commit()` ensures the callback
runs after a successful commit, but it does not guarantee delivery if
Redis is unavailable after the database commit. A transactional outbox
is a stronger approach when losing an event is unacceptable.

### 8.3 Subscribe and stream events

``` python
# views.py

import redis

from django.http import StreamingHttpResponse
from django.views.decorators.http import require_GET

from .redis_client import redis_client


@require_GET
def order_events(request, order_id):
    def event_stream():
        pubsub = redis_client.pubsub()
        channel = f"order:{order_id}"

        try:
            pubsub.subscribe(channel)

            while True:
                message = pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15,
                )

                if message is None:
                    # SSE comment heartbeat.
                    yield ": keep-alive\n\n"
                    continue

                yield (
                    "event: order_status\n"
                    f"data: {message['data']}\n\n"
                )

        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response
```

### 8.4 End-to-end flow

Suppose order `123` changes from `Pending` to `Confirmed`.

1.  A staff member calls the order-update API.
2.  Django validates the request and updates the order in MySQL.
3.  The transaction commits.
4.  The `on_commit` callback publishes an event to Redis channel
    `order:123`.
5.  The SSE view subscribed to `order:123` receives the message.
6.  Django yields an SSE event to the open HTTP response.
7.  The browser receives the event and updates the order status UI.

The publisher does not need to know which browser is connected. Redis
distributes the event to active subscribers of the channel.

### 8.5 Important limitation of the example

The code above is intentionally small. In particular:

-   It does not authenticate the customer.
-   It does not verify that the customer owns the order.
-   It does not replay missed events.
-   It does not implement a transactional outbox.
-   It uses a synchronous Redis client and a synchronous streaming
    generator.
-   It does not implement a bounded connection lifetime or a full
    shutdown strategy.

Do not expose this endpoint publicly without adding the necessary
controls.

------------------------------------------------------------------------

## 9. Reliability and Delivery Semantics

This is one of the most important topics when designing real-time
systems.

### 9.1 What happens when the browser disconnects?

Suppose the browser receives event 101, then loses its network
connection while events 102 and 103 are published.

With Redis Pub/Sub:

``` text
Browser receives: 101
Network disconnects
Redis publishes: 102
Redis publishes: 103
Browser reconnects
```

Events 102 and 103 are lost to that subscriber because Pub/Sub does not
store them.

A reconnecting browser does not automatically recover those events.

### 9.2 Event IDs and replay

A durable event system can assign monotonically increasing IDs:

``` text
id: 101
event: order_status
data: {"status":"Confirmed"}

id: 102
event: order_status
data: {"status":"Packaging"}

id: 103
event: order_status
data: {"status":"Delivered"}
```

After reconnecting, the browser may send:

``` http
Last-Event-ID: 102
```

The server can query its durable event store for events with IDs greater
than `102`, replay them, and then continue streaming new events.

The replay mechanism must be implemented by the application.

### 9.3 Transactional outbox pattern

There is a failure window in this sequence:

``` text
1. Commit order update to MySQL
2. Publish event to Redis
```

If the process crashes between steps 1 and 2, the order is updated but
the event is never published.

A transactional outbox reduces this risk:

``` text
              One MySQL transaction
             +-----------------------+
             | Update order status   |
             | Insert outbox event   |
             +-----------------------+
                         |
                       COMMIT
                         |
                         v
              Outbox publisher worker
                         |
                         v
                   Redis / Kafka
                         |
                         v
                   SSE subscribers
```

The order update and outbox event are committed atomically in the same
database transaction. A background worker publishes pending outbox rows
and marks them as processed.

The publisher should be designed for retries and possible duplicate
delivery. Consumers should be idempotent.

### 9.4 Delivery is not exactly-once by default

SSE itself does not provide exactly-once business event processing.

A client may reconnect, an event may be replayed, or a publisher may
retry. Design consumers to tolerate duplicates, typically by using event
IDs and idempotent state updates.

------------------------------------------------------------------------

## 10. Authentication and Authorization

An order stream can expose private customer information. Protect it as
carefully as the ordinary order API.

Before subscribing:

1.  Authenticate the user.
2.  Load the requested order.
3.  Verify that the user is authorized to view it.
4.  Subscribe only to the authorized order's event channel.
5.  Avoid sending sensitive fields that the frontend does not need.

Example authorization outline:

``` python
def get_authorized_order(user, order_id):
    return MedicineOrder.objects.get(
        id=order_id,
        patient__user=user,
    )
```

Adapt the relationship names to the actual application model. Handle
missing and unauthorized orders without leaking whether another
customer's order exists.

### Token authentication caveat

Native `EventSource` does not support arbitrary custom headers. Common
options include:

-   Same-site or appropriately configured cross-site secure cookies.
-   A streaming client based on `fetch()` that supports custom headers.
-   A short-lived, narrowly scoped stream token, with care to avoid
    leaking it through URLs, logs, browser history, or referrers.

Never place a long-lived access token in a query parameter.

------------------------------------------------------------------------

## 11. Deployment and Operational Considerations

SSE can work locally but fail in production if a proxy buffers output or
a worker cannot efficiently handle long-lived connections.

### 11.1 Nginx buffering

Nginx may buffer upstream responses. Disable buffering for the SSE
route.

Example:

``` nginx
location /api/orders/ {
    proxy_pass http://django_backend;
    proxy_http_version 1.1;

    proxy_buffering off;
    proxy_cache off;

    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

The Django response can also include:

``` http
X-Accel-Buffering: no
```

Verify the actual behavior of your proxy and hosting platform; headers
and directives may differ across infrastructure.

### 11.2 Heartbeats

Send periodic comment records:

``` text
: keep-alive
```

A heartbeat is not delivered as an application event. It helps keep idle
connections active through intermediaries and can reveal broken
connections.

Choose the interval based on the shortest idle timeout in your
infrastructure.

### 11.3 WSGI vs ASGI

A synchronous streaming response under WSGI can occupy a worker for the
lifetime of the stream. A large number of simultaneous connections can
exhaust a small synchronous worker pool.

ASGI is generally a better fit for many long-lived connections, but the
application must use an appropriate asynchronous streaming
implementation and async-compatible dependencies. Simply deploying
synchronous streaming code under ASGI does not automatically make it
non-blocking.

### 11.4 Capacity planning

Monitor:

-   Active SSE connections.
-   Connection duration and disconnect rate.
-   Events published and delivered.
-   Redis subscriber count and health.
-   Worker utilization and memory.
-   Time from database commit to browser receipt.
-   Reconnection frequency and failed streams.

Set sensible connection limits, timeouts, and resource controls. Do not
assume that a persistent connection is free.

------------------------------------------------------------------------

## 12. Testing SSE

### 12.1 Run Django

``` bash
python manage.py runserver 8000
```

### 12.2 Use curl

``` bash
curl -N http://localhost:8000/api/orders/123/events/
```

`-N` disables curl's output buffering so events are displayed as they
arrive.

Expected output from the simulated example:

``` text
id: 1
event: order_status
data: {"order_id": 123, "status": "Pending"}

id: 2
event: order_status
data: {"order_id": 123, "status": "Confirmed"}

id: 3
event: order_status
data: {"order_id": 123, "status": "Packaging"}
```

### 12.3 Browser test

Open a browser page and run:

``` javascript
const source = new EventSource(
  "http://localhost:8000/api/orders/123/events/"
);

source.addEventListener("order_status", (event) => {
  console.log("Received:", JSON.parse(event.data));
});

source.onerror = () => {
  console.log("Connection state:", source.readyState);
};
```

The `readyState` values are:

  Value   Meaning
  ------- ------------
  `0`     CONNECTING
  `1`     OPEN
  `2`     CLOSED

Stop the stream:

``` javascript
source.close();
```

### 12.4 Production test checklist

-   [ ] The response has `Content-Type: text/event-stream`.
-   [ ] Events arrive incrementally, not all at the end.
-   [ ] Each event ends with a blank line.
-   [ ] Reverse-proxy buffering is disabled for the stream.
-   [ ] Heartbeats pass through the deployed infrastructure.
-   [ ] Disconnecting a browser cleans up the Redis subscription.
-   [ ] Reconnection behavior is tested.
-   [ ] Unauthorized users cannot subscribe to another customer's order.
-   [ ] Missed-event behavior is explicitly defined.
-   [ ] Concurrent connection capacity is load-tested.

------------------------------------------------------------------------

## 13. Common Problems

  -----------------------------------------------------------------------
  Problem                 Likely cause            What to check
  ----------------------- ----------------------- -----------------------
  All events arrive       Proxy or application    Nginx buffering,
  together                buffering               middleware, server
                                                  configuration

  Connection closes       Proxy/server timeout    Read timeout, heartbeat
  quickly                                         interval

  Browser repeatedly      Server closes or errors Server logs, response
  reconnects                                      status, network tab

  Events are missed after Pub/Sub is transient    Durable event storage
  reconnect                                       and replay

  Browser cannot connect  CORS configuration      Allowed origin and
  cross-origin                                    credentials

  One worker becomes busy Synchronous long-lived  WSGI worker model and
                          stream                  concurrency

  Another customer's data Missing authorization   Order ownership checks
  appears                                         and channel scoping
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 14. When to Use SSE

SSE is a good fit when the server needs to push updates to a browser and
the client does not need to send frequent messages over the same
connection.

Good examples:

-   E-commerce order status.
-   Notification feeds.
-   Admin dashboard updates.
-   Background task progress.
-   AI response token streaming.
-   Deployment or log output streaming.
-   Live monitoring metrics.

Consider WebSockets when both sides need frequent, low-latency
communication. Consider polling when updates are infrequent and
simplicity matters more than immediacy.

### Practical recommendation for an order-tracking system

For an order-tracking feature:

1.  Keep the order status in the relational database as the source of
    truth.
2.  Update the order through the normal authenticated business API.
3.  Publish an event after the transaction commits.
4.  Use Redis Pub/Sub if transient live delivery is sufficient.
5.  Use an outbox and durable event transport if missing events is
    unacceptable.
6.  Expose an authenticated SSE endpoint scoped to the customer and
    order.
7.  On page load or reconnect, fetch the latest order state through a
    normal API; use SSE for subsequent updates.

This combines a reliable state snapshot with low-latency updates.

------------------------------------------------------------------------

## 15. Further Reading

-   [MDN: Using server-sent
    events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
-   [MDN:
    EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
-   [WHATWG: Server-Sent Events
    specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
-   [Django:
    StreamingHttpResponse](https://docs.djangoproject.com/en/stable/ref/request-response/#streaminghttpresponse)
-   [Redis: Pub/Sub](https://redis.io/docs/latest/develop/pubsub/)
-   [Redis:
    Streams](https://redis.io/docs/latest/develop/data-types/streams/)

------------------------------------------------------------------------

## Key Takeaways

-   SSE is a one-way server-to-client event stream over HTTP.
-   The browser opens one long-lived request using `EventSource`.
-   The server sends UTF-8 event records separated by blank lines.
-   `StreamingHttpResponse` can stream SSE records from Django.
-   Redis Pub/Sub can distribute events between separate application
    processes.
-   Redis Pub/Sub does not retain events for disconnected subscribers.
-   Event IDs only enable recovery when the server implements replay.
-   Use a transactional outbox and durable messaging when event loss is
    unacceptable.
-   Secure every stream with authentication and resource-level
    authorization.
-   Account for reverse-proxy buffering, worker capacity, heartbeats,
    and connection cleanup.
